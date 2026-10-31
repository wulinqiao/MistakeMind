from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(str, Enum):
    成分残缺 = "成分残缺"
    成分赘余 = "成分赘余"
    搭配不当 = "搭配不当"
    语序不当 = "语序不当"
    结构混乱 = "结构混乱"
    表意不明 = "表意不明"
    不合逻辑 = "不合逻辑"
    关联词使用不当 = "关联词使用不当"
    其他 = "其他"


class Difficulty(str, Enum):
    小学高年级 = "小学高年级"
    初中 = "初中"
    高中 = "高中"
    综合 = "综合"


class PracticeMode(str, Enum):
    判断题 = "判断题"
    选择题 = "选择题"
    修改题 = "修改题"


class ReviewStatus(str, Enum):
    passed = "passed"
    needs_review = "needs_review"
    failed = "failed"


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


T = TypeVar("T")


class Meta(BaseModel):
    timestamp: datetime
    version: str = "v1.1"


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    request_id: str
    data: T | None = None
    error: ErrorBody | None = None
    meta: Meta


class DiagnoseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sentence: str = Field(min_length=1, max_length=500)
    user_id: str = Field(default="anonymous", min_length=1, max_length=100)
    grade: Difficulty | None = None
    optional_context: str | None = Field(default=None, max_length=1000)
    need_hints: bool = True

    @field_validator("sentence")
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("sentence 不能为空")
        return value.strip()


class Correction(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    kind: str = Field(min_length=1, max_length=50)
    reason: str = Field(min_length=1, max_length=500)


class Hint(BaseModel):
    level: int = Field(ge=1, le=3)
    text: str = Field(min_length=1, max_length=500)


class DiagnosisResult(BaseModel):
    diagnosis_id: str
    original_sentence: str
    has_error: bool
    error_types: list[Category] = Field(default_factory=list)
    error_span: str | None = None
    explanation: str
    corrections: list[Correction] = Field(default_factory=list)
    hints: list[Hint] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    review_status: ReviewStatus
    needs_context: bool = False
    trace: list[dict[str, Any]] = Field(default_factory=list)


class QuestionOut(BaseModel):
    question_id: str
    sentence: str
    mode: PracticeMode
    difficulty: Difficulty
    category: Category
    options: list[str] = Field(default_factory=list)


class QuestionsQuery(BaseModel):
    category: Category | None = None
    difficulty: Difficulty | None = None
    mode: PracticeMode | None = None
    count: int = Field(default=1, ge=1, le=10)
    user_id: str | None = None


class SubmitAnswerRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    question_id: str = Field(min_length=1, max_length=100)
    answer: Any
    answer_type: str = Field(default="choice", min_length=1, max_length=30)
    hint_level_used: int = Field(default=0, ge=0, le=3)
    attempt_number: int = Field(default=1, ge=1)


class HistoryQuery(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    category: Category | None = None


class AgentContext(BaseModel):
    request_id: str
    user_id: str
    task: str
    grade: Difficulty | None = None
    sentence: str | None = None
    optional_context: str | None = None
    need_hints: bool = True
    student_answer: Any | None = None
    question_id: str | None = None
    history_summary: list[dict[str, Any]] = Field(default_factory=list)
    current_result: DiagnosisResult | None = None
    trace: list[dict[str, Any]] = Field(default_factory=list)

