from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass

from agents.client import Budget, LLMClient, event
from agents.config import Settings
from agents.demo import mock_output
from agents.errors import AnswerValidationError, ModelLowConfidence
from agents.models import AnswerAnalysisV1, AnswerInputV1, AnswerReviewInputV1, AnswerReviewV1, DiagnosisOutputV1, ReviewInputV1, ReviewOutputV1
from prompts import templates
from schemas.models import AgentContext, Category, Correction, DiagnosisResult, ReviewStatus


@dataclass
class GradedAnswer:
    is_correct: bool
    feedback: str
    diagnosis: DiagnosisResult


class AgentService:
    def __init__(self, settings: Settings | None = None, client: LLMClient | None = None):
        self.settings = settings or Settings.from_env()
        self.client = client or LLMClient(self.settings)

    def _event(self, ctx, stage, action, started, status="success", **extra):
        event(ctx.trace, ctx.request_id, stage, action, status, started,
              mode=self.settings.resolved_mode, model=self.settings.model, **extra)

    def _route(self, ctx):
        if ctx.task not in {"diagnose", "diagnose_and_practice", "submit_answer"}:
            raise AnswerValidationError("不支持的任务类型")
        self._event(ctx, "routing_agent", "route:" + ctx.task, time.monotonic())

    def diagnose(self, ctx: AgentContext, *, baseline: bool = False, tools: dict | None = None):
        self._route(ctx)
        started = time.monotonic()
        budget = Budget(self.settings)
        if self.settings.resolved_mode == "mock":
            out = mock_output(ctx.sentence or "", ctx.need_hints)
            self._event(ctx, "diagnosis_agent", "mock_fixture", started)
            approved = not out.needs_context
        else:
            payload = {"sentence": ctx.sentence, "grade": ctx.grade, "optional_context": ctx.optional_context,
                       "need_hints": ctx.need_hints}
            if tools is not None:
                payload["tools"] = tools
                payload["history_summary"] = ctx.history_summary
                self._event(ctx, "routing_agent", "read_question_tools", started)
            out = self.client.complete(templates.BASELINE if baseline else templates.DIAGNOSIS, payload,
                DiagnosisOutputV1, budget=budget, trace=ctx.trace, request_id=ctx.request_id, stage="diagnosis_agent")
            if baseline:
                approved = not out.needs_context
            else:
                review_payload = ReviewInputV1(input=payload, candidate=out).model_dump(mode="json")
                review = self.client.complete(templates.REVIEW, review_payload,
                    ReviewOutputV1, budget=budget, trace=ctx.trace, request_id=ctx.request_id, stage="review_agent")
                approved = review.approved
                if not approved:
                    out.explanation += " 复核提示：" + review.reason
        if not ctx.need_hints:
            out.hints = []
        self._event(ctx, "hint_agent", "select_hints", started)
        self._event(ctx, "correction_agent", "select_minimal_corrections", started)
        reliable = approved and not out.needs_context and out.confidence >= self.settings.threshold
        if any(c.text.strip() == (ctx.sentence or "").strip() for c in out.corrections):
            reliable = False
            out.explanation += " 修改与原句相同，需要人工复核。"
        if ctx.need_hints and out.has_error and not out.needs_context and len(out.hints) != 3:
            reliable = False
            out.explanation += " 分层提示不完整，需要复核。"
        self._event(ctx, "review_agent", "final_gate", started, "passed" if reliable else "needs_review")
        if not reliable:
            out.explanation = "暂定结论，尚未通过复核。" + out.explanation
        result = DiagnosisResult(diagnosis_id="diag_" + uuid.uuid4().hex[:12], original_sentence=ctx.sentence or "",
            **out.model_dump(), review_status=ReviewStatus.passed if reliable else ReviewStatus.needs_review,
            trace=ctx.trace.copy())
        ctx.current_result = result
        return result

    def grade(self, ctx: AgentContext, question: dict, answer_type: str) -> GradedAnswer:
        self._route(ctx)
        mode = question["mode"]
        answer = ctx.student_answer
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 500:
            raise AnswerValidationError("answer 必须为 1–500 字符的非空字符串")
        answer = answer.strip()
        if mode == "修改题":
            if answer_type not in {"text", "修改题"}:
                raise AnswerValidationError("修改题必须使用 text 或 修改题 answer_type")
        elif answer_type not in {"choice", mode}:
            raise AnswerValidationError("answer_type 与题目模式不匹配")
        refs = json.loads(question.get("references_json") or "[]")
        types = [Category(t) for t in json.loads(question.get("error_types_json") or "[]")]
        has_error = bool(types)
        started = time.monotonic()
        texts = [x["text"] if isinstance(x, dict) else x for x in refs]
        if mode == "判断题":
            if answer not in {"是病句", "不是病句"}:
                raise AnswerValidationError("判断题答案必须为 是病句 或 不是病句")
            correct = answer == ("是病句" if has_error else "不是病句")
        elif mode == "选择题":
            if answer not in {c.value for c in Category}:
                raise AnswerValidationError("选择题答案必须为统一类别标签")
            labels = [x for x in texts if x in {c.value for c in Category}]
            correct = answer in (labels or [t.value for t in types] or ["其他"])
        elif mode == "修改题":
            if has_error and answer == question["sentence"].strip():
                return self._graded(ctx, question, types, texts, False,
                    "本次提交与原病句相同，尚未消除题目标注的语病。", started, "unchanged_error_sentence")
            if answer in {t.strip() for t in texts}:
                correct = True
            elif self.settings.resolved_mode == "mock":
                self._event(ctx, "answer_agent", "mock_uncovered", started, "needs_review", output_schema="AnswerAnalysisV1")
                raise ModelLowConfidence()
            else:
                payload = {"question": {"sentence": question["sentence"], "error_types": [t.value for t in types],
                                       "references": texts}, "student_answer": answer, "grade": ctx.grade,
                           "optional_context": ctx.optional_context, "history_summary": ctx.history_summary}
                payload = AnswerInputV1.model_validate(payload).model_dump(mode="json")
                budget = Budget(self.settings)
                assessment = self.client.complete(templates.ANSWER, payload, AnswerAnalysisV1,
                    budget=budget, trace=ctx.trace, request_id=ctx.request_id, stage="answer_agent")
                review_payload = AnswerReviewInputV1(input=payload, assessment=assessment).model_dump(mode="json")
                review = self.client.complete(templates.ANSWER_REVIEW, review_payload, AnswerReviewV1,
                    budget=budget, trace=ctx.trace, request_id=ctx.request_id, stage="review_agent")
                if not review.approved or assessment.needs_context or assessment.is_correct is None or assessment.confidence < self.settings.threshold:
                    self._event(ctx, "review_agent", "grading_gate", started, "needs_review")
                    raise ModelLowConfidence()
                return self._graded(ctx, question, types, texts, assessment.is_correct, assessment.feedback, started, "semantic_review")
        else:
            raise AnswerValidationError("不支持的题目模式")
        feedback = ("作答正确。" if correct else "本次作答尚不正确。") + (
            "题库标注的知识点为“" + "、".join(t.value for t in types) + "”。" if has_error else "此题为正常句，不需要修改。")
        return self._graded(ctx, question, types, texts, correct, feedback, started, "audited_reference")

    def _graded(self, ctx, q, types, refs, correct, feedback, started, action):
        self._event(ctx, "answer_agent", action, started, output_schema="AnswerAnalysisV1")
        self._event(ctx, "review_agent", "grading_gate", started, "passed", output_schema="AnswerReviewV1")
        corrections = [Correction(text=t, kind="参考修改", reason="来自已审核启用题目的参考修改。")
                       for t in refs if t not in {"是病句", "不是病句", *[c.value for c in Category]}] if types else []
        diagnosis = DiagnosisResult(diagnosis_id="diag_" + uuid.uuid4().hex[:12], original_sentence=q["sentence"],
            has_error=bool(types), error_types=types, error_span=None,
            explanation=feedback + " 关联诊断依据题库标准标签；本字段不代表重新检测原句。",
            corrections=corrections, hints=[], confidence=1.0, review_status=ReviewStatus.passed,
            trace=ctx.trace.copy())
        ctx.current_result = diagnosis
        return GradedAnswer(correct, feedback, diagnosis)
