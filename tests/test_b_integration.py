import json
import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

import backend.main as api
import db.database as database_module
from agents.errors import ModelInvalidJSON, ModelTimeout, ModelUnavailable
from agents.pipeline import AgentService
from agents.config import Settings
from db.database import Database
from tests.test_b_agents import live_service


@pytest.fixture
def setup(tmp_path, monkeypatch):
    db = Database(tmp_path / "isolated.db")
    monkeypatch.setattr(database_module, "_db", db)
    with closing(db.connect()) as conn, conn:
        for qid, mode, category, types, refs in [
            ("edit", "修改题", "成分残缺", ["成分残缺"], [{"text": "经过训练，他学会了游泳。"}]),
            ("choice", "选择题", "成分残缺", ["成分残缺"], [{"text": "经过训练，他学会了游泳。"}]),
            ("judge", "判断题", "其他", [], ["不是病句"]),
        ]:
            conn.execute("INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?)", (qid, "经过训练，使他学会了游泳。" if types else "他学会了游泳。", mode,
                         category, json.dumps(types), json.dumps(refs), "初中", "reviewed-test-fixture", 1))
    return TestClient(api.app), db


def submit(client, answer, **kw):
    return client.post("/api/submit-answer", json=dict(user_id="learner", question_id=kw.pop("question_id", "edit"),
                                                     answer=answer, answer_type=kw.pop("answer_type", "text"), **kw))


def counts(db):
    with closing(db.connect()) as conn:
        return [conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in ("attempts", "diagnoses", "users")]


def test_exact_reference_history_and_previous_accuracy(setup):
    client, db = setup
    first = submit(client, "经过训练，他学会了游泳。").json()
    assert first["data"]["is_correct"] and first["meta"]["version"] == "v1.1"
    second = submit(client, "搭配不当", question_id="choice", answer_type="choice").json()
    assert not second["data"]["is_correct"]
    assert second["data"]["mastery_update"] == {"category": "成分残缺", "before": 1.0, "after": .5}
    history = client.get("/api/history/learner").json()["data"]
    assert history["total"] == 2 and all(r["error_types"] == ["成分残缺"] for r in history["items"])
    assert counts(db) == [2, 2, 1]


def test_choices_never_contain_reference_modifications(setup):
    client, _ = setup
    rows = client.get("/api/questions", params={"count": 10}).json()["data"]["questions"]
    assert next(q for q in rows if q["question_id"] == "judge")["options"] == ["是病句", "不是病句"]
    choices = next(q for q in rows if q["question_id"] == "choice")["options"]
    assert len(choices) == 9 and "成分残缺" in choices
    assert "经过训练，他学会了游泳。" not in str(rows)


@pytest.mark.parametrize("answer,extra", [(" ", {}), ({"text": "改"}, {}), ("改", {"answer_type": "choice"}), ("改", {"answer_type": "unknown"}), ("x"*501, {})])
def test_invalid_answers_do_not_write(setup, answer, extra):
    client, db = setup
    response = submit(client, answer, **extra)
    assert response.status_code == 400 and response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert counts(db) == [0, 0, 0]


def test_unknown_mock_answer_requires_review_without_score(setup):
    client, db = setup
    response = submit(client, "训练让他掌握了游泳技能。")
    assert response.status_code == 200 and not response.json()["success"]
    assert response.json()["error"]["code"] == "MODEL_LOW_CONFIDENCE"
    assert counts(db) == [0, 0, 0]


@pytest.mark.parametrize("correct", [True, False])
def test_semantic_grading_accepts_alternative_and_rejects_bad_change(setup, monkeypatch, correct):
    client, db = setup
    assessment = dict(is_correct=correct, feedback="修改保留原意。" if correct else "修改改变原意。",
                      meaning_preserved=correct, error_resolved=True, no_new_error=True, needs_context=False, confidence=.9)
    service, seen = live_service([assessment, {"approved": True, "reason": "同意本次评分"}])
    monkeypatch.setattr(api, "grade_answer", service.grade)
    response = submit(client, "训练让他掌握了游泳技能。" if correct else "他不会游泳。")
    assert response.json()["data"]["is_correct"] is correct
    assert len(seen) == 2 and counts(db) == [1, 1, 1]


@pytest.mark.parametrize("assessment,review", [
    (dict(is_correct=None, feedback="缺少上下文", meaning_preserved=False, error_resolved=False, no_new_error=True, needs_context=True, confidence=.9), True),
    (dict(is_correct=True, feedback="合理", meaning_preserved=True, error_resolved=True, no_new_error=True, needs_context=False, confidence=.2), True),
    (dict(is_correct=False, feedback="不合理", meaning_preserved=False, error_resolved=True, no_new_error=True, needs_context=False, confidence=.9), False),
])
def test_uncertain_semantic_grading_does_not_update_profile(setup, monkeypatch, assessment, review):
    client, db = setup
    service, _ = live_service([assessment, {"approved": review, "reason": "待复核"}])
    monkeypatch.setattr(api, "grade_answer", service.grade)
    response = submit(client, "另一个修改。")
    assert response.json()["error"]["code"] == "MODEL_LOW_CONFIDENCE" and counts(db) == [0, 0, 0]


@pytest.mark.parametrize("error,status", [(ModelTimeout, 504), (ModelInvalidJSON, 502), (ModelUnavailable, 502)])
def test_api_model_errors_are_safe_and_unpersisted(setup, monkeypatch, error, status):
    client, db = setup
    def broken(*args, **kwargs): raise error("secret upstream body")
    monkeypatch.setattr(api, "diagnose", broken)
    response = client.post("/api/diagnose", json={"sentence": "输入。"})
    assert response.status_code == status and "secret upstream body" not in response.text
    assert counts(db) == [0, 0, 0]


def test_unreviewed_free_diagnosis_is_not_stored(setup):
    client, db = setup
    data = client.post("/api/diagnose", json={"sentence": "未知演示句。"}).json()["data"]
    assert data["review_status"] == "needs_review" and data["needs_context"]
    assert counts(db) == [0, 0, 0]


def test_atomic_rollback_on_diagnosis_failure(setup, monkeypatch):
    client, db = setup
    def fail(*args): raise sqlite3.IntegrityError("failed link")
    monkeypatch.setattr(db, "_insert_linked_diagnosis", fail)
    response = submit(client, "经过训练，他学会了游泳。")
    assert response.status_code == 500 and response.json()["error"]["code"] == "DATABASE_ERROR"
    assert counts(db) == [0, 0, 0]


def test_grade_and_context_forwarded_at_api(setup, monkeypatch):
    client, _ = setup
    seen = {}
    def capture(sentence, need_hints, **kwargs):
        seen.update(kwargs, need_hints=need_hints)
        return AgentService(Settings(mode="mock")).diagnose(__import__("schemas.models", fromlist=["AgentContext"]).AgentContext(
            request_id=kwargs["request_id"], user_id=kwargs["user_id"], task="diagnose", sentence=sentence, need_hints=need_hints))
    monkeypatch.setattr(api, "diagnose", capture)
    r = client.post("/api/diagnose", headers={"X-Request-ID": "forwarded"}, json={
        "sentence": "今天的天空很蓝。", "grade": "初中", "optional_context": "气象观察", "need_hints": False})
    assert r.status_code == 200 and seen["optional_context"] == "气象观察" and seen["request_id"] == "forwarded"
    assert seen["grade"].value == "初中" and seen["need_hints"] is False


def test_database_public_operations_release_windows_file_handles(tmp_path):
    db = Database(tmp_path / "release.db")
    db.ensure_user("u")
    assert db.user_exists("u")
    db.list_questions()
    db.profile("u")
    db.history("u", 1, 10)
    db.get_question("absent")
    db.recent_summary("u")
    # This fails on Windows if any Database-owned connection is left open.
    db.path.unlink()
    assert not db.path.exists()


def test_unmodified_error_is_wrong_even_without_model(setup):
    client, db = setup
    response = submit(client, "经过训练，使他学会了游泳。")
    assert response.json()["data"]["is_correct"] is False
    assert counts(db) == [1, 1, 1]


@pytest.mark.parametrize("answer,correct", [("不是病句", True), ("是病句", False)])
def test_normal_judgment_uses_gold_not_mock_sentence_detection(setup, answer, correct):
    client, _ = setup
    response = submit(client, answer, question_id="judge", answer_type="choice")
    assert response.json()["data"]["is_correct"] is correct


def test_passed_free_diagnosis_returns_persistence_trace(setup):
    client, db = setup
    response = client.post("/api/diagnose", json={"sentence": "今天的天空很蓝。", "need_hints": False})
    assert response.json()["data"]["hints"] == []
    assert response.json()["data"]["trace"][-1]["action"] == "save_diagnosis"
    assert counts(db) == [0, 1, 1]
