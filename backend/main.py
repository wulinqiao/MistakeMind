from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.agents import diagnose, ModelInvalidJSON, ModelTimeout
from db.database import get_database
from schemas.models import *

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("mistakemind")
app = FastAPI(title="MistakeMind API", version="1.0.0")


def envelope(request_id: str, data=None, error: ErrorBody | None = None, status: int = 200):
    body = ApiResponse(success=error is None, request_id=request_id, data=data, error=error, meta=Meta(timestamp=datetime.now(timezone.utc).astimezone()))
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


@app.middleware("http")
async def request_context(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:12]}")
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("request failed request_id=%s", request.state.request_id)
        return envelope(request.state.request_id, error=ErrorBody(code="INTERNAL_ERROR", message="服务内部错误"), status=500)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return envelope(request.state.request_id, error=ErrorBody(code="VALIDATION_ERROR", message="请求参数校验失败", details={"errors": exc.errors()}), status=400)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/diagnose")
def diagnose_sentence(payload: DiagnoseRequest, request: Request):
    rid = request.state.request_id
    db = get_database(); db.ensure_user(payload.user_id, payload.grade.value if payload.grade else None)
    try:
        result = diagnose(payload.sentence, payload.need_hints)
    except ModelTimeout:
        return envelope(rid, error=ErrorBody(code="MODEL_TIMEOUT", message="模型请求超时"), status=504)
    except ModelInvalidJSON:
        return envelope(rid, error=ErrorBody(code="MODEL_INVALID_JSON", message="模型返回无法解析"), status=502)
    db.insert_diagnosis(result.model_dump(mode="json"))
    return envelope(rid, result.model_dump(mode="json"))


@app.get("/api/questions")
def questions(request: Request, category: Category | None = None, difficulty: Difficulty | None = None, mode: PracticeMode | None = None, count: int = Query(1, ge=1, le=10), user_id: str | None = None):
    rows = get_database().list_questions(category.value if category else None, difficulty.value if difficulty else None, mode.value if mode else None, count, user_id)
    out = [QuestionOut(question_id=r["id"], sentence=r["sentence"], mode=PracticeMode(r["mode"]), difficulty=Difficulty(r["difficulty"]), category=Category(r["category"]), options=json.loads(r.get("references_json", "[]")) if r["mode"] in ("判断题", "选择题") else []).model_dump(mode="json") for r in rows]
    return envelope(request.state.request_id, {"questions": out})


@app.post("/api/submit-answer")
def submit_answer(payload: SubmitAnswerRequest, request: Request):
    db = get_database(); q = db.get_question(payload.question_id)
    if not q: return envelope(request.state.request_id, error=ErrorBody(code="QUESTION_NOT_FOUND", message="题目不存在"), status=404)
    expected = json.loads(q["references_json"] or "[]")
    if payload.answer_type in ("choice", "判断题", "选择题"):
        is_correct = str(payload.answer).strip() in {str(x).strip() for x in expected} if expected else False
    else:
        is_correct = str(payload.answer).strip() in {str(x.get("text", x)).strip() for x in expected} if expected else False
    attempt_id = f"attempt_{uuid.uuid4().hex[:12]}"
    db.insert_attempt(attempt_id, payload.user_id, payload.question_id, payload.answer, is_correct, payload.hint_level_used, payload.attempt_number)
    stats = db.profile(payload.user_id); cat = q["category"]
    catstat = next((x for x in stats["category_stats"] if x["category"] == cat), None)
    recommended = None
    recs = db.list_questions(category=(stats["recommended_categories"] or [cat])[0], count=1, user_id=payload.user_id)
    if recs: recommended = recs[0]["id"]
    data = {"attempt_id": attempt_id, "is_correct": is_correct, "feedback_level": "basic" if is_correct else "guided", "feedback": "判断正确。" if is_correct else f"请复习“{cat}”相关知识点。", "next_action": "show_explanation", "recommended_question_id": recommended, "mastery_update": {"category": cat, "before": max(0, (catstat["accuracy"] if catstat else 0) - (1 / (catstat["attempts"] if catstat else 1))), "after": catstat["accuracy"] if catstat else (1.0 if is_correct else 0.0)}}
    return envelope(request.state.request_id, data)


@app.get("/api/history/{user_id}")
def history(user_id: str, request: Request, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), category: Category | None = None):
    db = get_database()
    if not db.user_exists(user_id):
        return envelope(request.state.request_id, error=ErrorBody(code="USER_NOT_FOUND", message="用户不存在"), status=404)
    total, rows = db.history(user_id, page, page_size, category.value if category else None)
    items = []
    for r in rows:
        items.append({"attempt_id": r["id"], "question_id": r["question_id"], "answer": json.loads(r["answer_json"]), "is_correct": bool(r["is_correct"]), "error_types": json.loads(r["error_types_json"] or "[]"), "created_at": r["created_at"]})
    return envelope(request.state.request_id, {"items": items, "page": page, "page_size": page_size, "total": total})


@app.get("/api/profile/{user_id}")
def profile(user_id: str, request: Request):
    db = get_database()
    if not db.user_exists(user_id):
        return envelope(request.state.request_id, error=ErrorBody(code="USER_NOT_FOUND", message="用户不存在"), status=404)
    return envelope(request.state.request_id, db.profile(user_id))

