from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.models import Category, Correction, DiagnoseRequest, Difficulty, Hint


class DiagnosisInputV1(DiagnoseRequest):
    """Public request fields, including context and teaching preferences."""


class StrictOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiagnosisOutputV1(StrictOutput):
    has_error: bool = Field(strict=True)
    error_types: list[Category]
    error_span: str | None
    explanation: str = Field(min_length=1, max_length=2000)
    corrections: list[Correction] = Field(max_length=5)
    hints: list[Hint] = Field(max_length=3)
    confidence: float = Field(ge=0, le=1)
    needs_context: bool = Field(strict=True)

    @model_validator(mode="after")
    def consistency(self):
        if len(set(self.error_types)) != len(self.error_types) or Category.其他 in self.error_types:
            raise ValueError("use unique eight-class error_types, never 其他")
        if not self.has_error and (self.error_types or self.error_span is not None or self.corrections):
            raise ValueError("normal sentence must have empty errors/corrections and null span")
        if self.has_error and not self.needs_context and (not self.error_types or not self.error_span or not self.corrections):
            raise ValueError("definite error needs types, span and corrections")
        if self.has_error and self.error_span is not None and not self.error_span.strip():
            raise ValueError("blank span")
        levels = [h.level for h in self.hints]
        if levels and levels != [1, 2, 3]:
            raise ValueError("hints must be empty or three ordered levels")
        if not self.explanation.strip() or any(not c.text.strip() or not c.reason.strip() for c in self.corrections):
            raise ValueError("blank explanation or correction")
        return self


class ReviewOutputV1(StrictOutput):
    approved: bool = Field(strict=True)
    reason: str = Field(min_length=1, max_length=1000)


class AnswerAnalysisV1(StrictOutput):
    is_correct: bool | None = Field(strict=True)
    feedback: str = Field(min_length=1, max_length=2000)
    meaning_preserved: bool = Field(strict=True)
    error_resolved: bool = Field(strict=True)
    no_new_error: bool = Field(strict=True)
    needs_context: bool = Field(strict=True)
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def consistency(self):
        if self.is_correct is True and not (self.meaning_preserved and self.error_resolved and self.no_new_error):
            raise ValueError("correct answer must satisfy all correction criteria")
        if self.is_correct is False and self.meaning_preserved and self.error_resolved and self.no_new_error:
            raise ValueError("incorrect answer needs a failed correction criterion")
        if not self.feedback.strip():
            raise ValueError("blank feedback")
        return self


class AnswerReviewV1(ReviewOutputV1):
    """Approve or reject the student's answer analysis, not the student answer."""


class QuestionEvidenceV1(StrictOutput):
    sentence: str = Field(min_length=1, max_length=500)
    error_types: list[Category]
    references: list[str]


class AnswerInputV1(StrictOutput):
    question: QuestionEvidenceV1
    student_answer: str = Field(min_length=1, max_length=500)
    grade: Difficulty | None = None
    optional_context: str | None = None
    history_summary: list[dict] = Field(default_factory=list)


class ReviewInputV1(StrictOutput):
    input: dict
    candidate: DiagnosisOutputV1


class AnswerReviewInputV1(StrictOutput):
    input: AnswerInputV1
    assessment: AnswerAnalysisV1
