from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from contextlib import closing

from fastapi import FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from agents.config import Settings

from backend.agents import diagnose, grade_answer, ModelError
from agents.errors import AnswerValidationError
from agents.client import event
from db.database import get_database
from schemas.models import *

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("mistakemind")
app = FastAPI(title="MistakeMind API", version="1.2.0")


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
    errors = jsonable_encoder(exc.errors(), custom_encoder={Exception: str})
    return envelope(request.state.request_id, error=ErrorBody(code="VALIDATION_ERROR", message="请求参数校验失败", details={"errors": errors}), status=400)


@app.exception_handler(ModelError)
async def model_error(request: Request, exc: ModelError):
    return envelope(request.state.request_id, error=ErrorBody(code=exc.code, message=exc.message), status=exc.status)


@app.exception_handler(AnswerValidationError)
async def answer_error(request: Request, exc: AnswerValidationError):
    return envelope(request.state.request_id, error=ErrorBody(code="VALIDATION_ERROR", message=str(exc)), status=400)


@app.exception_handler(sqlite3.Error)
async def database_error(request: Request, exc: sqlite3.Error):
    logger.error("database operation failed request_id=%s", request.state.request_id)
    return envelope(request.state.request_id, error=ErrorBody(code="DATABASE_ERROR", message="数据库操作失败，未完成保存"), status=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def runtime_status(request: Request):
    db = get_database()
    with closing(db.connect()) as con:
        count = con.execute("SELECT count(*) FROM questions WHERE is_active=1").fetchone()[0]
        demo = con.execute("SELECT count(*) FROM questions WHERE is_active=1 AND source LIKE '开发演示%'").fetchone()[0]
    return envelope(request.state.request_id, {"agent_mode": Settings.from_env().resolved_mode,
        "active_questions": count, "demo_dataset": bool(demo), "api_version": "v1.2"})


@app.post("/api/diagnose")
def diagnose_sentence(payload: DiagnoseRequest, request: Request):
    rid = request.state.request_id
    result = diagnose(payload.sentence, payload.need_hints, grade=payload.grade,
                      optional_context=payload.optional_context, request_id=rid, user_id=payload.user_id)
    if result.review_status == ReviewStatus.passed:
        db = get_database()
        db.ensure_user(payload.user_id, payload.grade.value if payload.grade else None)
        started = time.monotonic()
        db.insert_diagnosis(result.model_dump(mode="json"))
        event(result.trace, rid, "record_tool", "save_diagnosis", "success", started,
              mode=result.trace[0]["mode"] if result.trace else "unknown")
    return envelope(rid, result.model_dump(mode="json"))


@app.get("/api/questions")
def questions(request: Request, category: Category | None = None, difficulty: Difficulty | None = None, mode: PracticeMode | None = None, count: int = Query(1, ge=1, le=10), user_id: str | None = None):
    db = get_database()
    rows = db.list_questions(category.value if category else None, difficulty.value if difficulty else None, mode.value if mode else None, count, user_id)
    if user_id and category is None:
        rec = db.recommend(user_id, mode.value if mode else None, difficulty.value if difficulty else None)
        if rec:
            chosen = db.get_question(rec["question_id"])
            rows = [chosen] + [r for r in rows if r["id"] != chosen["id"]]
    out = [public_question(r) for r in rows[:count]]
    return envelope(request.state.request_id, {"questions": out})


def public_question(row):
    return QuestionOut(question_id=row["id"], sentence=row["sentence"], mode=row["mode"],
        difficulty=row["difficulty"], options=["是病句", "不是病句"] if row["mode"] == "判断题"
        else [c.value for c in Category] if row["mode"] == "选择题" else []).model_dump(mode="json")


@app.get("/api/questions/{question_id}")
def question_by_id(question_id: str, request: Request):
    row = get_database().get_question(question_id)
    if not row:
        return envelope(request.state.request_id, error=ErrorBody(code="QUESTION_NOT_FOUND", message="题目不存在或已下线"), status=404)
    return envelope(request.state.request_id, {"question": public_question(row)})


@app.post("/api/submit-answer")
def submit_answer(payload: SubmitAnswerRequest, request: Request):
    db = get_database(); q = db.get_question(payload.question_id)
    if not q: return envelope(request.state.request_id, error=ErrorBody(code="QUESTION_NOT_FOUND", message="题目不存在"), status=404)
    ctx = AgentContext(request_id=request.state.request_id, user_id=payload.user_id, task="submit_answer",
                       sentence=q["sentence"], grade=q["difficulty"], question_id=q["id"],
                       student_answer=payload.answer, history_summary=db.recent_summary(payload.user_id))
    graded = grade_answer(ctx, q, payload.answer_type)
    is_correct = graded.is_correct
    before_stats = db.profile(payload.user_id)
    before = next((s["accuracy"] for s in before_stats["category_stats"] if s["category"] == q["category"]), 0.0)
    attempt_id = f"attempt_{uuid.uuid4().hex[:12]}"
    started = time.monotonic()
    db.save_graded_attempt(attempt_id, payload.user_id, payload.question_id, payload.answer,
                          is_correct, payload.hint_level_used, payload.attempt_number, graded.diagnosis.model_dump(mode="json"))
    event(ctx.trace, request.state.request_id, "record_tool", "save_graded_attempt", "success", started,
          mode=ctx.trace[0]["mode"] if ctx.trace else "unknown")
    stats = db.profile(payload.user_id); cat = q["category"]
    catstat = next((x for x in stats["category_stats"] if x["category"] == cat), None)
    started = time.monotonic()
    rec = db.recommend(payload.user_id, mode=q["mode"], difficulty=q["difficulty"], exclude_id=q["id"])
    event(ctx.trace, request.state.request_id, "recommend_tool", "recommend_next", "success", started,
          mode=ctx.trace[0]["mode"] if ctx.trace else "unknown",
          question_id=rec["question_id"] if rec else None)
    data = {"attempt_id": attempt_id, "is_correct": is_correct, "feedback_level": "basic" if is_correct else "guided", "feedback": graded.feedback, "next_action": "show_explanation", "recommended_question_id": rec["question_id"] if rec else None, "mastery_update": {"category": cat, "before": before, "after": catstat["accuracy"] if catstat else 0.0}, "diagnosis": graded.diagnosis.model_dump(mode="json"), "trace": ctx.trace}
    return envelope(request.state.request_id, data)


@app.get("/api/history/{user_id}")
def history(user_id: str, request: Request, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), category: Category | None = None, wrong_only: bool = False):
    db = get_database()
    if not db.user_exists(user_id):
        return envelope(request.state.request_id, error=ErrorBody(code="USER_NOT_FOUND", message="用户不存在"), status=404)
    total, rows = db.history(user_id, page, page_size, category.value if category else None, wrong_only)
    items = []
    for r in rows:
        diagnosis = {"original_sentence": r["original_sentence"], "explanation": r["explanation"],
                     "has_error": bool(json.loads(r["error_types_json"] or "[]")),
                     "error_types": json.loads(r["error_types_json"] or "[]"), "error_span": r["error_span"],
                     "corrections": json.loads(r["corrections_json"] or "[]"), "review_status": r["review_status"]} if r["diagnosis_id"] else None
        items.append({"attempt_id": r["id"], "question_id": r["question_id"], "answer": json.loads(r["answer_json"]), "is_correct": bool(r["is_correct"]), "error_types": json.loads(r["error_types_json"] or "[]"), "created_at": r["created_at"], "original_sentence": r["original_sentence"], "diagnosis": diagnosis})
    return envelope(request.state.request_id, {"items": items, "page": page, "page_size": page_size, "total": total})


@app.get("/api/profile/{user_id}")
def profile(user_id: str, request: Request):
    db = get_database()
    if not db.user_exists(user_id):
        return envelope(request.state.request_id, error=ErrorBody(code="USER_NOT_FOUND", message="用户不存在"), status=404)
    return envelope(request.state.request_id, db.profile(user_id))


# Serve the built Vue application on the same origin as the API.
DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if (DIST / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{page}", include_in_schema=False)
    @app.get("/practice/{sub}", include_in_schema=False)
    def frontend_page(request: Request, page: str = "", sub: str = ""):
        path = request.url.path.strip("/")
        allowed = {"", "practice", "diagnose", "history", "profile"}
        # Nested practice routes (e.g. /practice/question) share the SPA shell.
        if path in allowed or path.startswith("practice/"):
            return FileResponse(DIST / "index.html")
        return envelope(request.state.request_id, error=ErrorBody(code="NOT_FOUND", message="页面不存在"), status=404)

