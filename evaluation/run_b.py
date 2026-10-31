"""Explicit offline/live B experiments, immutable manifests and resumable JSONL."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from agents.config import ROOT, Settings
from agents.errors import ModelError
from agents.pipeline import AgentService
from evaluation.b_metrics import summarize
from prompts.templates import VERSION
from schemas.models import AgentContext
from scripts.recommend_c import recommend_next
from scripts.validate_c_questions import load_questions, validate_questions


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def source_digest():
    return digest({str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for folder in ("agents", "prompts", "schemas", "backend", "db", "evaluation", "scripts")
                   for p in sorted((ROOT / folder).glob("*.py"))})


def vetted(rows):
    for q in rows:
        review = q.get("review")
        if q.get("review_status") != "approved" or not isinstance(review, dict):
            return False
        if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
            return False
        try:
            timestamp = datetime.fromisoformat(review.get("reviewed_at", ""))
            if timestamp.tzinfo is None:
                return False
        except (ValueError, TypeError):
            return False
    return True


def load_context(path):
    obj = json.loads(Path(path).read_text(encoding="utf-8")) if path else {"questions": [], "attempts": []}
    if not isinstance(obj, dict) or not isinstance(obj.get("questions"), list) or not isinstance(obj.get("attempts"), list):
        raise ValueError("context 必须含 questions 和 attempts 数组")
    errors = validate_questions(obj["questions"])
    if errors:
        raise ValueError(errors)
    if any(q["review_status"] != "approved" or not q["is_active"] for q in obj["questions"]):
        raise ValueError("工具题库只允许已审核且启用的样本")
    # Validate historical correctness even if the question pool is empty.
    from scripts.recommend_c import category_profile
    category_profile(obj["attempts"])
    return obj


def bigrams(text):
    return {text[i:i+2] for i in range(max(0, len(text)-1))}


def retrieve(sentence, bank):
    query = bigrams(sentence)
    scored = []
    for row in bank:
        other = bigrams(row["sentence"])
        similarity = len(query & other) / max(1, len(query | other))
        # Avoid disclosing the same item or a close paraphrase as a retrieved example.
        if similarity < .45:
            scored.append((similarity, row["id"], row))
    return [dict(sentence=q["sentence"], error_types=q["error_types"], explanation=q["explanation"],
                 references=q["references"]) for _, _, q in sorted(scored, key=lambda x: (-x[0], x[1]))[:3]]


def read_run(path, manifest):
    lines = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines or lines[0] != {"kind": "manifest", **manifest}:
        raise ValueError("恢复被拒绝：数据、模型、上下文或代码版本与原运行不一致")
    latest = {}
    for row in lines[1:]:
        if row.get("id") not in manifest["ids"] or row.get("kind") != "result":
            raise ValueError("运行文件含无效记录")
        previous = latest.get(row["id"])
        if previous and (previous["status"] == "success" or row.get("attempt") != previous.get("attempt", 1) + 1):
            raise ValueError("重复记录不符合失败重试规则")
        latest[row["id"]] = row
    return latest


def run(args, *, service=None):
    rows = load_questions(args.data)
    if not rows:
        raise ValueError("评测集不能为空")
    if not args.development and not vetted(rows):
        raise ValueError("正式评测要求所有题目 approved 且填写人工审核人和时间；候选试跑请加 --development")
    if not args.development and (len(rows) < 60 or not any(not q["has_error"] for q in rows)
                                or len({q["category"] for q in rows if q["has_error"]}) < 8):
        raise ValueError("正式评测至少 60 条，且必须覆盖八类病句及正常句")
    context = load_context(args.context)
    if args.group == "full" and not args.development and (not context["questions"] or not vetted(context["questions"])):
        raise ValueError("正式 full 组需要独立、已人工审核的工具题库与审核元数据")
    if not args.development and args.group == "full":
        for q in rows:
            query = bigrams(q["sentence"])
            for reference in context["questions"]:
                other = bigrams(reference["sentence"])
                if q["id"] == reference["id"] or len(query & other) / max(1, len(query | other)) >= .45:
                    raise ValueError("正式工具题库与测试集存在同题或近似文本，请先隔离")
        if any(a.get("question_id") in {q["id"] for q in rows} for a in context["attempts"]):
            raise ValueError("历史场景不得包含最终测试题的作答记录")
    if service is None:
        settings = Settings.from_env() if args.live else Settings(mode="mock")
        if args.live and settings.resolved_mode != "live":
            raise ValueError("--live 需要本地真实服务配置")
        service = AgentService(settings)
    settings = service.settings
    manifest = dict(group=args.group, development=args.development, data_hash=digest(rows),
        context_hash=digest(context), code_hash=source_digest(), prompt_version=VERSION,
        settings=settings.model_dump(exclude={"api_key"}), python=platform.python_version(), ids=[q["id"] for q in rows])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not args.resume:
        raise ValueError("输出已存在；使用 --resume 恢复，或指定新输出路径")
    latest = read_run(output, manifest) if output.exists() else {}
    if not output.exists():
        output.write_text(json.dumps({"kind": "manifest", **manifest}, ensure_ascii=False) + "\n", encoding="utf-8")
    for q in rows:
        previous = latest.get(q["id"])
        if previous and (previous["status"] == "success" or not args.retry_failed):
            continue
        ctx = AgentContext(request_id="eval_" + q["id"], user_id="evaluation", task="diagnose_and_practice" if args.group == "full" else "diagnose",
                           sentence=q["sentence"], grade=q["difficulty"], need_hints=False,
                           history_summary=context["attempts"] if args.group == "full" else [])
        row = dict(kind="result", id=q["id"], attempt=previous.get("attempt", 1)+1 if previous else 1,
                   timestamp=datetime.now(timezone.utc).isoformat(), result=None, error=None)
        started = time.monotonic()
        try:
            result = service.diagnose(ctx, baseline=args.group == "baseline",
                                      tools={"examples": retrieve(q["sentence"], context["questions"])} if args.group == "full" else None)
            row.update(status="success" if result.review_status.value == "passed" else "needs_review",
                       result=result.model_dump(mode="json"))
            if args.group == "full":
                rec = recommend_next(context["questions"], context["attempts"])
                row["recommendation"] = rec
                row["recommendation_scenario"] = manifest["context_hash"]
                targets = context.get("target_weak_categories")
                row["recommendation_hit"] = rec["category"] in targets if rec and targets else None
                row["recommendation_note"] = "沿用 C 规则和提供的历史场景，不使用评测 gold 更新历史，也不把本指标归因于诊断模型。"
        except ModelError as exc:
            row.update(status="failed", error=exc.code)
        row["latency_ms"] = round((time.monotonic() - started) * 1000)
        row["trace"] = ctx.trace
        with output.open("a", encoding="utf-8") as file:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")
            file.flush()
        latest[q["id"]] = row
    records = list(latest.values())
    audit = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
    report = summarize(rows, records, all_attempts=audit)
    report.update(group=args.group, formal=not args.development, mode=settings.resolved_mode,
                  real_diagnostic_experiment=not args.development and settings.resolved_mode == "live",
                  data_hash=manifest["data_hash"], code_hash=manifest["code_hash"], prompt_version=VERSION)
    report["validation_scope"] = "真实服务、人工审核数据的诊断实验；修改质量仍需人工评分。" if report["real_diagnostic_experiment"] else "开发性流程验证，不代表真实模型精度。"
    output.with_suffix(".summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ratings_path = output.with_suffix(".ratings.json")
    ratings = json.loads(ratings_path.read_text(encoding="utf-8")) if ratings_path.exists() else []
    rated_keys = {(r["id"], r["correction_index"]) for r in ratings}
    for r in records:
        if r.get("status") == "success":
            for i, _ in enumerate(r["result"]["corrections"]):
                if (r["id"], i) not in rated_keys:
                    ratings.append(dict(id=r["id"], correction_index=i, effective=None,
                                        meaning_preserved=None, reviewer=None, notes=""))
    ratings_path.write_text(json.dumps(ratings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default="data/b_evaluation_candidates.json")
    parser.add_argument("--group", choices=["baseline", "structured", "full"], required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--context", help="独立工具题库和历史 JSON，含 questions/attempts")
    parser.add_argument("--development", action="store_true", help="允许未审核候选，明确不作正式结论")
    parser.add_argument("--live", action="store_true", help="显式允许付费真实请求")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry-failed", action="store_true", help="恢复时重试失败/拒判项；保留旧记录")
    args = parser.parse_args()
    try:
        report = run(args)
    except (ValueError, OSError, ModelError) as exc:
        parser.exit(2, f"评测未执行完成：{exc}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
