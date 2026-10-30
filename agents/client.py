from __future__ import annotations

import json
import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from agents.config import Settings
from agents.errors import ModelInvalidJSON, ModelTimeout, ModelUnavailable
from prompts.templates import VERSION

logger = logging.getLogger("mistakemind.agent")
T = TypeVar("T", bound=BaseModel)


class Budget:
    def __init__(self, settings: Settings):
        self.deadline = time.monotonic() + settings.total_timeout
        self.max_calls = settings.max_calls
        self.calls = 0
        self.network_retries = 0
        self.repairs = 0

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ModelTimeout()
        return remaining

    def take(self):
        self.remaining()
        if self.calls >= self.max_calls:
            raise ModelUnavailable()
        self.calls += 1


def event(trace, request_id, agent, action, status, started, *, mode, model="", **extra):
    item = dict(agent=agent, action=action, status=status,
                started_at=datetime.now(timezone.utc).isoformat(),
                duration_ms=round((time.monotonic() - started) * 1000),
                input_schema=extra.pop("input_schema", "DiagnosisInputV1"),
                output_schema=extra.pop("output_schema", "DiagnosisOutputV1"),
                request_id=request_id, mode=mode, model=model, prompt_version=VERSION, **extra)
    # started_at is a wall-clock start, reconstructed from the elapsed duration.
    item["started_at"] = (datetime.now(timezone.utc) - timedelta(milliseconds=item["duration_ms"])).isoformat()
    trace.append(item)
    logger.info(json.dumps(item, ensure_ascii=False))


class LLMClient:
    """Inject httpx.AsyncClient for offline tests; synchronous business interface."""
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None):
        self.settings = settings
        self.http = http

    def complete(self, system: str, payload: dict, output: type[T], *, budget: Budget,
                 trace: list, request_id: str, stage: str) -> T:
        settings = self.settings
        if settings.resolved_mode != "live":
            raise ModelUnavailable()
        input_schema = {"answer_agent": "AnswerInputV1", "review_agent":
                        "AnswerReviewInputV1" if output.__name__ == "AnswerReviewV1" else "ReviewInputV1"}.get(stage, "DiagnosisInputV1")
        messages = [
            {"role": "system", "content": system + "\nJSON schema:\n" + json.dumps(output.model_json_schema(), ensure_ascii=False)},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        while True:
            started = time.monotonic()
            usage = {}
            budget.take()
            try:
                raw, usage = self._request(messages, min(settings.timeout, budget.remaining()))
                budget.remaining()
                # Never echo an invalid response into prompts, logs, or exceptions.
                try:
                    result = output.model_validate_json(raw)
                except (ValueError, ValidationError):
                    raise ModelInvalidJSON() from None
            except ModelInvalidJSON:
                event(trace, request_id, stage, "llm_call", "invalid_json", started,
                      mode="live", model=settings.model, call_number=budget.calls, input_schema=input_schema, output_schema=output.__name__, usage=usage)
                if budget.repairs == 0 and budget.calls < budget.max_calls:
                    budget.repairs += 1
                    messages.append({"role": "user", "content": "上次输出未通过格式或一致性校验。请重新分析原始数据，只返回完全符合 schema 的 JSON。"})
                    continue
                raise
            except (ModelUnavailable, ModelTimeout) as exc:
                event(trace, request_id, stage, "llm_call", exc.code, started,
                      mode="live", model=settings.model, call_number=budget.calls, input_schema=input_schema, output_schema=output.__name__)
                raise
            except (httpx.TransportError, RetryableResponse) as exc:
                event(trace, request_id, stage, "llm_call", "retryable_error", started,
                      mode="live", model=settings.model, call_number=budget.calls, input_schema=input_schema, output_schema=output.__name__)
                if budget.network_retries == 0 and budget.calls < budget.max_calls:
                    budget.network_retries += 1
                    continue
                if isinstance(exc, httpx.TimeoutException):
                    raise ModelTimeout() from None
                raise ModelUnavailable() from None
            event(trace, request_id, stage, "llm_call", "success", started,
                  mode="live", model=settings.model, call_number=budget.calls,
                  input_schema=input_schema, output_schema=output.__name__, usage=usage)
            return result

    def _request(self, messages, timeout):
        # Bound the whole HTTP operation, including slow trickle reads.
        async def bounded():
            return await asyncio.wait_for(self._async_request(messages, timeout), timeout=timeout)
        try:
            return asyncio.run(bounded())
        except TimeoutError:
            raise httpx.ReadTimeout("request deadline exceeded") from None

    async def _async_request(self, messages, timeout):
        body = {"model": self.settings.model, "messages": messages, "stream": False}
        if self.settings.json_mode:
            body["response_format"] = {"type": "json_object"}
        owned = self.http is None
        client = self.http or httpx.AsyncClient(follow_redirects=False)
        try:
            response = await client.post(self.settings.base_url.rstrip("/") + "/chat/completions",
                                   headers={"Authorization": "Bearer " + self.settings.api_key},
                                   json=body, timeout=timeout)
            if response.status_code == 429 or response.status_code >= 500:
                raise RetryableResponse()
            if not 200 <= response.status_code < 300:
                raise ModelUnavailable()
            try:
                obj = response.json()
                choice = obj["choices"][0]
                raw = choice["message"]["content"]
                if choice.get("finish_reason") not in {None, "stop"} or not isinstance(raw, str) or not raw.strip():
                    raise ValueError()
                usage = {k: v for k, v in (obj.get("usage") or {}).items()
                         if k in {"prompt_tokens", "completion_tokens", "total_tokens"} and type(v) is int and v >= 0}
            except (ValueError, KeyError, IndexError, TypeError, AttributeError):
                raise ModelInvalidJSON() from None
            return raw, usage
        finally:
            if owned:
                await client.aclose()


class RetryableResponse(Exception):
    pass
