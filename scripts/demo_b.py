"""Offline API/SQLite demonstration in a temporary database, no model calls."""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import closing
from pathlib import Path

from fastapi.testclient import TestClient

import db.database as database_module
from backend.main import app
from db.database import Database


def main():
    old_db = database_module._db
    old_mode = os.environ.get("AGENT_MODE")
    os.environ["AGENT_MODE"] = "mock"
    try:
        with tempfile.TemporaryDirectory(prefix="mistakemind-b-") as folder:
            db = Database(Path(folder) / "demo.db")
            database_module._db = db
            with closing(db.connect()) as con, con:
                for qid in ("demo1", "demo2"):
                    con.execute("INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?)", (qid,
                        "通过开展此次活动，使同学们提高了环保意识。", "修改题", "成分残缺", '["成分残缺"]',
                        json.dumps([{"text": "通过开展此次活动，同学们提高了环保意识。"}], ensure_ascii=False),
                        "初中", "隔离工程演示固定样例，不是正式题库", 1))
            with TestClient(app) as client:
                diagnosis = client.post("/api/diagnose", json={"sentence": "通过开展此次活动，使同学们提高了环保意识。"}).json()
                assert diagnosis["data"]["review_status"] == "passed"
                assert client.get("/api/questions").json()["data"]["questions"]
                answer = dict(user_id="b_demo", question_id="demo1", answer_type="text")
                passed = client.post("/api/submit-answer", json={**answer, "answer": "通过开展此次活动，同学们提高了环保意识。"}).json()
                assert passed["data"]["is_correct"] and passed["data"]["recommended_question_id"] == "demo2"
                declined = client.post("/api/submit-answer", json={**answer, "answer": "活动可能有一些作用。"}).json()
                assert declined["error"]["code"] == "MODEL_LOW_CONFIDENCE"
                history = client.get("/api/history/b_demo").json()["data"]
                profile = client.get("/api/profile/b_demo").json()["data"]
                assert history["total"] == 1 and history["items"][0]["error_types"] == ["成分残缺"]
                assert profile["total_attempts"] == 1
                reopened = Database(db.path)
                assert reopened.history("b_demo", 1, 10)[0] == 1
                print(json.dumps(dict(mode="mock", api_version=diagnosis["meta"]["version"],
                    diagnosis_trace=diagnosis["data"]["trace"], persisted_attempts=history["total"],
                    linked_error_types=history["items"][0]["error_types"],
                    next_question=passed["data"]["recommended_question_id"], uncertain_attempt_scored=False,
                    reopened_database_verified=True, formal_database_modified=False), ensure_ascii=False, indent=2))
    finally:
        database_module._db = old_db
        if old_mode is None:
            os.environ.pop("AGENT_MODE", None)
        else:
            os.environ["AGENT_MODE"] = old_mode


if __name__ == "__main__":
    main()
