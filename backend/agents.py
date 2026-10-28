from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any

from schemas.models import Category, Correction, DiagnosisResult, Hint, ReviewStatus


class ModelTimeout(Exception): pass
class ModelInvalidJSON(Exception): pass


def _trace(agent, action, status, started, input_schema="DiagnosisInputV1", output_schema="DiagnosisOutputV1"):
    return {"agent": agent, "action": action, "status": status, "started_at": started, "duration_ms": int((time.perf_counter()-started)*1000), "input_schema": input_schema, "output_schema": output_schema}


def mock_diagnose(sentence: str, need_hints: bool = True) -> DiagnosisResult:
    started = time.perf_counter(); lower = sentence
    if "通过" in lower and "使" in lower:
        types, span, explanation = [Category.结构混乱, Category.成分残缺], "通过……使……", "“通过”和“使”同时使用，造成句子结构混乱。"
        corrections = [Correction(text=lower.replace("通过", "", 1), kind="最小修改", reason="删除“通过”，保留“使”字句式"), Correction(text=lower.replace("使", "", 1), kind="另一种合理修改", reason="删除“使”，补出主语")]
        hints = [Hint(level=1, text="请检查句子的主语是否明确。"), Hint(level=2, text="注意“通过……使……”这一结构。"), Hint(level=3, text="可以删除“通过”或删除“使”。")] if need_hints else []
        has_error = True
    else:
        types, span, explanation, corrections, hints, has_error = [], None, "句子结构完整，暂未发现明显病句。", [], [], False
    return DiagnosisResult(diagnosis_id=f"diag_{uuid.uuid4().hex[:12]}", original_sentence=sentence, has_error=has_error, error_types=types, error_span=span, explanation=explanation, corrections=corrections, hints=hints, confidence=.94 if has_error else .82, review_status=ReviewStatus.passed, trace=[_trace("diagnosis_agent", "mock_call", "success", started)])


def diagnose(sentence: str, need_hints: bool = True) -> DiagnosisResult:
    # The adapter is deliberately provider-agnostic. A configured provider can return the same JSON shape.
    if not os.getenv("LLM_API_KEY"):
        return mock_diagnose(sentence, need_hints)
    # Keep network integration optional for local demos; callers can replace this function with an adapter.
    return mock_diagnose(sentence, need_hints)

