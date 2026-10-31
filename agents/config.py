from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from agents.errors import ModelUnavailable

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)
    mode: str = "auto"
    api_key: str = Field(default="", repr=False)
    base_url: str = "https://api.openai.com/v1"
    model: str = ""
    timeout: float = Field(default=20, gt=0, le=60)
    total_timeout: float = Field(default=60, gt=0, le=300)
    max_calls: int = Field(default=4, ge=1, le=4)
    threshold: float = Field(default=.7, ge=0, le=1)
    json_mode: bool = True

    @model_validator(mode="after")
    def configuration(self):
        if self.mode not in {"auto", "mock", "live"}:
            raise ValueError("AGENT_MODE must be auto/mock/live")
        url = urlsplit(self.base_url)
        if url.scheme not in {"http", "https"} or not url.netloc or url.username or url.password or url.query or url.fragment:
            raise ValueError("LLM_BASE_URL must be a plain HTTP(S) base URL")
        if self.resolved_mode == "live" and (not self.api_key.strip() or not self.model.strip()):
            raise ValueError("live requires LLM_API_KEY and LLM_MODEL")
        return self

    @property
    def resolved_mode(self) -> str:
        return ("live" if self.api_key.strip() else "mock") if self.mode == "auto" else self.mode

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env", override=False)
        try:
            json_mode = os.getenv("LLM_JSON_MODE", "true").lower()
            if json_mode not in {"true", "false", "1", "0"}:
                raise ValueError("invalid JSON mode")
            return cls(mode=os.getenv("AGENT_MODE", "auto"), api_key=os.getenv("LLM_API_KEY", ""),
                       base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
                       model=os.getenv("LLM_MODEL", ""), timeout=os.getenv("LLM_TIMEOUT_SECONDS", "20"),
                       total_timeout=os.getenv("LLM_TOTAL_TIMEOUT_SECONDS", "60"),
                       max_calls=os.getenv("LLM_MAX_CALLS", "4"),
                       threshold=os.getenv("LLM_CONFIDENCE_THRESHOLD", "0.7"),
                       json_mode=json_mode in {"true", "1"})
        except (ValueError, ValidationError):
            raise ModelUnavailable() from None
