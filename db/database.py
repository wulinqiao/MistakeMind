from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "mistakemind.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


class Database:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or os.getenv("DATABASE_PATH", DEFAULT_DB))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        return con

    def init_db(self) -> None:
        with self.connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS users (
              id TEXT PRIMARY KEY, nickname TEXT NOT NULL DEFAULT '', grade TEXT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS questions (
              id TEXT PRIMARY KEY, sentence TEXT NOT NULL, mode TEXT NOT NULL,
              category TEXT NOT NULL, error_types_json TEXT NOT NULL DEFAULT '[]',
              references_json TEXT NOT NULL DEFAULT '[]', difficulty TEXT NOT NULL,
              source TEXT NOT NULL DEFAULT 'unknown', is_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS attempts (
              id TEXT PRIMARY KEY, user_id TEXT NOT NULL, question_id TEXT NOT NULL,
              answer_json TEXT NOT NULL, is_correct INTEGER NOT NULL,
              hint_level_used INTEGER NOT NULL DEFAULT 0, attempt_number INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id),
              FOREIGN KEY(question_id) REFERENCES questions(id)
            );
            CREATE TABLE IF NOT EXISTS diagnoses (
              id TEXT PRIMARY KEY, attempt_id TEXT, original_sentence TEXT NOT NULL,
              has_error INTEGER NOT NULL, error_types_json TEXT NOT NULL DEFAULT '[]',
              error_span TEXT, explanation TEXT NOT NULL, corrections_json TEXT NOT NULL DEFAULT '[]',
              review_status TEXT NOT NULL, created_at TEXT NOT NULL,
              FOREIGN KEY(attempt_id) REFERENCES attempts(id)
            );
            CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts(user_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category, is_active);
            """)

    def ensure_user(self, user_id: str, grade: str | None = None) -> None:
        with self.connect() as c:
            c.execute("INSERT OR IGNORE INTO users(id, grade, created_at) VALUES (?, ?, ?)", (user_id, grade, now_iso()))
            if grade:
                c.execute("UPDATE users SET grade = COALESCE(grade, ?) WHERE id = ?", (grade, user_id))

    def user_exists(self, user_id: str) -> bool:
        with self.connect() as c:
            return c.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is not None

    def insert_diagnosis(self, result: dict[str, Any], attempt_id: str | None = None) -> None:
        with self.connect() as c:
            c.execute("""INSERT INTO diagnoses
              (id, attempt_id, original_sentence, has_error, error_types_json, error_span, explanation, corrections_json, review_status, created_at)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                result["diagnosis_id"], attempt_id, result["original_sentence"], int(result["has_error"]),
                json.dumps(result.get("error_types", []), ensure_ascii=False), result.get("error_span"),
                result["explanation"], json.dumps(result.get("corrections", []), ensure_ascii=False),
                result["review_status"], now_iso()))

    def list_questions(self, category=None, difficulty=None, mode=None, count=1, user_id=None):
        clauses, args = ["is_active = 1"], []
        for col, value in (("category", category), ("difficulty", difficulty), ("mode", mode)):
            if value:
                clauses.append(f"{col} = ?"); args.append(value)
        recent = set()
        if user_id:
            with self.connect() as c:
                recent = {r[0] for r in c.execute("SELECT question_id FROM attempts WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (user_id,))}
        query = f"SELECT * FROM questions WHERE {' AND '.join(clauses)} ORDER BY RANDOM() LIMIT ?"
        with self.connect() as c:
            rows = c.execute(query, (*args, max(count * 3, count))).fetchall()
        selected = [r for r in rows if r["id"] not in recent][:count] or list(rows)[:count]
        return [dict(r) for r in selected]

    def get_question(self, question_id):
        with self.connect() as c:
            row = c.execute("SELECT * FROM questions WHERE id = ? AND is_active = 1", (question_id,)).fetchone()
        return dict(row) if row else None

    def insert_attempt(self, attempt_id, user_id, question_id, answer, is_correct, hint_level, attempt_number):
        self.ensure_user(user_id)
        with self.connect() as c:
            c.execute("""INSERT INTO attempts(id,user_id,question_id,answer_json,is_correct,hint_level_used,attempt_number,created_at)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (attempt_id, user_id, question_id, json.dumps(answer, ensure_ascii=False), int(is_correct), hint_level, attempt_number, now_iso()))

    def history(self, user_id, page, page_size, category=None):
        clauses, args = ["a.user_id = ?"], [user_id]
        if category:
            clauses.append("q.category = ?"); args.append(category)
        where = " AND ".join(clauses)
        with self.connect() as c:
            total = c.execute(f"SELECT COUNT(*) FROM attempts a JOIN questions q ON q.id=a.question_id WHERE {where}", args).fetchone()[0]
            rows = c.execute(f"""SELECT a.*, q.category, d.error_types_json FROM attempts a JOIN questions q ON q.id=a.question_id
              LEFT JOIN diagnoses d ON d.attempt_id=a.id WHERE {where} ORDER BY a.created_at DESC LIMIT ? OFFSET ?""", (*args, page_size, (page-1)*page_size)).fetchall()
        return total, [dict(r) for r in rows]

    def profile(self, user_id):
        with self.connect() as c:
            rows = c.execute("SELECT q.category, a.is_correct FROM attempts a JOIN questions q ON q.id=a.question_id WHERE a.user_id=?", (user_id,)).fetchall()
        stats = {}
        for row in rows:
            s = stats.setdefault(row[0], {"attempts": 0, "correct": 0}); s["attempts"] += 1; s["correct"] += int(row[1])
        result = []
        for category, s in stats.items():
            accuracy = s["correct"] / s["attempts"]
            result.append({"category": category, **s, "accuracy": accuracy, "mastery": accuracy, "priority": "high" if accuracy < .6 else "medium" if accuracy < .8 else "low"})
        result.sort(key=lambda x: (x["accuracy"], -x["attempts"]))
        total = len(rows)
        return {"user_id": user_id, "total_attempts": total, "overall_accuracy": sum(int(r[1]) for r in rows)/total if total else 0.0,
                "category_stats": result, "recommended_categories": [x["category"] for x in result[:2]],
                "next_review_at": (datetime.now(timezone.utc).astimezone() + timedelta(days=2)).isoformat()}


_db: Database | None = None
def get_database() -> Database:
    global _db
    if _db is None: _db = Database()
    return _db

