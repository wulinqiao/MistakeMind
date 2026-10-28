import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from db.database import Database
import db.database as database_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db = Database(tmp_path / "test.db")
    monkeypatch.setattr(database_module, "_db", db)
    with db.connect() as c:
        c.execute("INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?)", ("q_001", "通过这次活动，使我受到了教育。", "判断题", "成分残缺", "[\"成分残缺\"]", "[\"是病句\"]", "初中", "test", 1))
    return TestClient(app)


def test_diagnose_and_envelope(client):
    r = client.post("/api/diagnose", json={"sentence": "通过开展此次活动，使同学们提高了环保意识。"})
    assert r.status_code == 200
    body = r.json(); assert body["success"] is True
    assert "结构混乱" in body["data"]["error_types"]
    assert body["data"]["trace"]


def test_validation(client):
    r = client.post("/api/diagnose", json={"sentence": "   "})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_full_practice_flow(client):
    q = client.get("/api/questions", params={"count": 1}).json()["data"]["questions"]
    assert q[0]["question_id"] == "q_001"
    result = client.post("/api/submit-answer", json={"user_id":"u1","question_id":"q_001","answer":"是病句"}).json()
    assert result["data"]["is_correct"] is True
    history = client.get("/api/history/u1").json()["data"]
    assert history["total"] == 1
    profile = client.get("/api/profile/u1").json()["data"]
    assert profile["overall_accuracy"] == 1.0

