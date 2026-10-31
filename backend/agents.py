from __future__ import annotations

import json
import os
import re
import time
import uuid
from typing import Any

import httpx
from dotenv import load_dotenv

from schemas.models import Category, Correction, DiagnosisResult, Hint, ReviewStatus

load_dotenv()


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
    # Keep local demos deterministic when no provider is configured.
    if not os.getenv("LLM_API_KEY"):
        return mock_diagnose(sentence, need_hints)

    started = time.perf_counter()
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    try:
        timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {os.environ['LLM_API_KEY']}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "你是中文病句诊断器。只返回 JSON，不要 Markdown。"
                            "JSON 必须包含 original_sentence, has_error, error_types, error_span, "
                            "explanation, corrections, hints, confidence, review_status。"
                            "error_types 只能使用：成分残缺、成分赘余、搭配不当、语序不当、结构混乱、表意不明、"
                            "不合逻辑、关联词使用不当、其他。"
                            "corrections 是包含 text、kind、reason 的数组；hints 是包含 level(1-3)、text 的数组；"
                            "review_status 使用 passed、needs_review 或 failed。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {"sentence": sentence, "need_hints": need_hints}, ensure_ascii=False
                        ),
                    },
                ],
            },
            timeout=timeout,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise ModelTimeout() from exc
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        raise ModelInvalidJSON() from exc

    try:
        content = response.json()["choices"][0]["message"]["content"]
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
        payload = json.loads(content)
        payload["diagnosis_id"] = payload.get("diagnosis_id", f"diag_{uuid.uuid4().hex[:12]}")
        payload["original_sentence"] = sentence
        payload["hints"] = payload.get("hints", []) if need_hints else []
        payload["trace"] = [_trace("diagnosis_agent", "llm_call", "success", started)]
        return DiagnosisResult.model_validate(payload)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ModelInvalidJSON() from exc

