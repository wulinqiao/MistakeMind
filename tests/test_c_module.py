import copy
import gc
import json
from contextlib import closing

from db.database import Database
from scripts import import_questions

import pytest

from evaluation.metrics import evaluate
from scripts.import_c_questions import import_approved
from scripts.recommend_c import CATEGORIES, category_profile, recommend_next
from scripts.validate_c_questions import load_questions, validate_questions


@pytest.fixture()
def questions():
    return load_questions("data/questions.json")


def test_candidate_count_and_distribution(questions):
    assert len(questions) == 20
    assert sum(not q["has_error"] for q in questions) == 4
    for category in CATEGORIES:
        assert sum(q["category"] == category for q in questions) == 2


def test_all_candidates_inactive_before_review(questions):
    assert all(q["review_status"] == "pending" and not q["is_active"] for q in questions)


def test_invalid_category_is_rejected(questions):
    bad = copy.deepcopy(questions)
    bad[0]["category"] = "主语残缺"
    assert any("category" in e for e in validate_questions(bad))


def test_duplicate_id_is_rejected(questions):
    bad = copy.deepcopy(questions)
    bad[1]["id"] = bad[0]["id"]
    assert any("id 重复" in e for e in validate_questions(bad))


def test_pending_cannot_be_active(questions):
    bad = copy.deepcopy(questions)
    bad[0]["is_active"] = True
    assert any("未审核" in e for e in validate_questions(bad))


def test_import_skips_pending(questions, tmp_path):
    qpath = tmp_path / "questions.json"
    dbpath = tmp_path / "isolated.db"
    qpath.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
    assert import_approved(qpath, dbpath) == 0
    assert not dbpath.exists()


def test_import_approved_candidate(questions, tmp_path):
    from db.database import Database

    questions[0]["review_status"] = "approved"
    questions[0]["is_active"] = True
    qpath = tmp_path / "questions.json"
    dbpath = tmp_path / "isolated.db"
    qpath.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
    assert import_approved(qpath, dbpath) == 1
    with Database(dbpath).connect() as con:
        row = con.execute("SELECT references_json FROM questions WHERE id=?", (questions[0]["id"],)).fetchone()
    assert json.loads(row[0])[0]["text"] == questions[0]["references"][0]["text"]


def test_recommend_prefers_weak_category(questions):
    attempts = [
        {"question_id": f"a{i}", "category": "搭配不当", "is_correct": False}
        for i in range(4)
    ] + [
        {"question_id": f"b{i}", "category": "成分残缺", "is_correct": True}
        for i in range(5)
    ]
    assert recommend_next(questions, attempts) is None  # 候选题不能进正式推荐
    rec = recommend_next(questions, attempts, allow_pending_demo=True)
    assert rec["category"] == "搭配不当"
    assert rec["question_id"] not in {a["question_id"] for a in attempts[-5:]}


def test_profile_requires_multiple_samples_to_estimate(questions):
    stats = category_profile([{"category": "搭配不当", "is_correct": False}])
    match = next(x for x in stats if x["category"] == "搭配不当")
    assert match["attempts"] == 1
    assert match["accuracy"] == 0.0
    assert 0 < match["priority_score"] < 1


def test_metrics_known_example():
    gold = [
        {"id": "a", "has_error": True, "category": "成分残缺"},
        {"id": "b", "has_error": True, "category": "搭配不当"},
        {"id": "c", "has_error": False, "category": "其他"},
    ]
    pred = [
        {"id": "a", "has_error": True, "category": "成分残缺"},
        {"id": "b", "has_error": False, "category": "其他"},
        {"id": "c", "has_error": True, "category": "不合逻辑"},
    ]
    result = evaluate(gold, pred)
    assert result["detection"]["tp"] == 1
    assert result["detection"]["fp"] == 1
    assert result["detection"]["fn"] == 1
    assert result["detection"]["f1"] == 0.5


def test_metrics_requires_matching_ids():
    with pytest.raises(ValueError, match="题号不一致"):
        evaluate([{"id":"a","has_error":False,"category":"其他"}],
                 [{"id":"b","has_error":False,"category":"其他"}])


def _approved_recommend_questions():
    return [
        {"id": question_id, "category": "搭配不当", "review_status": "approved", "is_active": True}
        for question_id in ("a", "b", "c")
    ]


def test_recommend_zero_recent_window_disables_avoidance():
    history = [{"question_id": "a", "category": "搭配不当", "is_correct": False}]
    assert recommend_next(_approved_recommend_questions(), history, recent_limit=0)["question_id"] == "a"


def test_recommend_uses_newest_history_at_end():
    history = [
        {"question_id": "a", "category": "搭配不当", "is_correct": False},
        {"question_id": "b", "category": "搭配不当", "is_correct": False},
    ]
    assert recommend_next(_approved_recommend_questions(), history, recent_limit=1)["question_id"] == "a"


@pytest.mark.parametrize("limit", [-1, True, 1.5, "5", None])
def test_recommend_rejects_invalid_recent_window(limit):
    with pytest.raises(ValueError, match="recent_limit"):
        recommend_next(_approved_recommend_questions(), [], recent_limit=limit)


@pytest.mark.parametrize("flag", [False, 0, True, 1])
def test_profile_accepts_boolean_and_sqlite_integer(flag):
    result = category_profile([{"category": "搭配不当", "is_correct": flag}])
    category = next(item for item in result if item["category"] == "搭配不当")
    assert category["accuracy"] == int(bool(flag))
    assert category["errors"] == int(not flag)


@pytest.mark.parametrize("flag", [None, "false", "true", 2, -1, 0.0, 1.0, [], {}])
def test_profile_rejects_invalid_correctness(flag):
    with pytest.raises(ValueError, match="is_correct"):
        category_profile([{"category": "搭配不当", "is_correct": flag}])


def test_profile_rejects_missing_correctness():
    with pytest.raises(ValueError, match="is_correct"):
        category_profile([{"category": "搭配不当"}])


def test_demo_keeps_rejected_and_inactive_approved_questions_out():
    candidates = [
        {"id": "a", "category": "搭配不当", "review_status": "rejected", "is_active": True},
        {"id": "b", "category": "搭配不当", "review_status": "approved", "is_active": False},
        {"id": "c", "category": "搭配不当", "review_status": "pending", "is_active": False},
    ]
    assert recommend_next(candidates, [], allow_pending_demo=True)["question_id"] == "c"
    assert recommend_next(candidates[:2], [], allow_pending_demo=True) is None


@pytest.mark.parametrize("invalid", [
    None,
    {},
    [],
    [None],
    ["row"],
    [{}],
    [{"id": "", "has_error": False, "category": "其他"}],
    [{"id": " ", "has_error": False, "category": "其他"}],
    [{"id": 1, "has_error": False, "category": "其他"}],
    [{"id": [], "has_error": False, "category": "其他"}],
    [{"id": "a", "has_error": 0, "category": "其他"}],
    [{"id": "a", "has_error": "false", "category": "其他"}],
    [{"id": "a", "has_error": False}],
    [{"id": "a", "has_error": False, "category": "成分残缺"}],
    [{"id": "a", "has_error": True, "category": "其他"}],
    [{"id": "a", "has_error": False, "category": "其他"}] * 2,
])
@pytest.mark.parametrize("side", ["gold", "predicted"])
def test_metrics_rejects_invalid_records_on_both_sides(invalid, side):
    valid = [{"id": "a", "has_error": False, "category": "其他"}]
    with pytest.raises(ValueError):
        evaluate(invalid, valid) if side == "gold" else evaluate(valid, invalid)


def test_metrics_aligns_reordered_rows_by_id():
    rows = [
        {"id": "a", "has_error": False, "category": "其他"},
        {"id": "b", "has_error": True, "category": "搭配不当"},
    ]
    result = evaluate(rows, list(reversed(rows)))
    assert result["detection"]["f1"] == 1.0
    assert result["classification"]["macro_f1_eight_classes"] == 0.125


@pytest.mark.parametrize("field", ["mode", "difficulty", "review_status"])
@pytest.mark.parametrize("value", [[], {}])
def test_validator_reports_invalid_enum_types(questions, field, value):
    row = copy.deepcopy(questions[0])
    row[field] = value
    assert any(field in error for error in validate_questions([row]))


@pytest.mark.parametrize("value", [[], [{"text": ""}]])
def test_validator_reports_bad_references(questions, value):
    row = copy.deepcopy(questions[0])
    row["references"] = value
    assert any("references" in error for error in validate_questions([row]))


def test_old_import_entry_skips_pending_candidates(questions, tmp_path, monkeypatch):
    qpath = tmp_path / "pending.json"
    dbpath = tmp_path / "untouched.db"
    qpath.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("DATABASE_PATH", str(dbpath))
    assert import_questions.main(str(qpath)) == 0
    assert not dbpath.exists()


def test_old_import_entry_cannot_activate_pending(questions, tmp_path, monkeypatch):
    questions[0]["is_active"] = True
    qpath = tmp_path / "bad_pending.json"
    dbpath = tmp_path / "untouched.db"
    qpath.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("DATABASE_PATH", str(dbpath))
    with pytest.raises(ValueError, match="未审核"):
        import_questions.main(str(qpath))
    assert not dbpath.exists()


def test_old_import_entry_rejects_mixed_review_metadata(questions, tmp_path, monkeypatch):
    rows = questions[:2]
    rows[0]["review_status"] = "approved"
    rows[0]["is_active"] = True
    del rows[1]["review_status"]
    qpath = tmp_path / "mixed.json"
    dbpath = tmp_path / "untouched.db"
    qpath.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("DATABASE_PATH", str(dbpath))
    with pytest.raises(ValueError, match="review_status"):
        import_questions.main(str(qpath))
    assert not dbpath.exists()


@pytest.mark.parametrize("entry", ["c", "legacy"])
def test_import_again_keeps_existing_attempts(questions, tmp_path, monkeypatch, entry):
    row = questions[0]
    row["review_status"] = "approved"
    row["is_active"] = True
    if entry == "legacy":
        for field in import_questions.C_REVIEW_FIELDS:
            row.pop(field, None)
    qpath = tmp_path / "approved.json"
    dbpath = tmp_path / "practice.db"
    monkeypatch.setenv("DATABASE_PATH", str(dbpath))

    def import_rows():
        qpath.write_text(json.dumps([row], ensure_ascii=False), encoding="utf-8")
        if entry == "c":
            return import_approved(qpath, dbpath)
        return import_questions.main(str(qpath))

    assert import_rows() == 1
    db = Database(dbpath)
    db.insert_attempt("keep-attempt", "keep-user", row["id"], "answer", False, 0, 1)
    row["source"] = "重复导入更新来源"
    assert import_rows() == 1
    with closing(db.connect()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM attempts WHERE id='keep-attempt'").fetchone()[0] == 1
        assert conn.execute("SELECT source FROM questions WHERE id=?", (row["id"],)).fetchone()[0] == row["source"]
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    # D 模块 Database.init_db 的既有连接由垃圾回收释放，避免 Windows 清理临时目录时占用文件。
    gc.collect()


def test_old_import_entry_rejects_removed_review_metadata(questions, tmp_path, monkeypatch):
    for row in questions:
        del row["review_status"]
        row["is_active"] = True
    qpath = tmp_path / "missing_review.json"
    dbpath = tmp_path / "untouched.db"
    qpath.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("DATABASE_PATH", str(dbpath))
    with pytest.raises(ValueError, match="review_status"):
        import_questions.main(str(qpath))
    assert not dbpath.exists()


def test_import_dry_run_does_not_create_database(questions, tmp_path):
    questions[0]["review_status"] = "approved"
    questions[0]["is_active"] = True
    qpath = tmp_path / "approved.json"
    dbpath = tmp_path / "untouched.db"
    qpath.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
    assert import_approved(qpath, dbpath, dry_run=True) == 1
    assert not dbpath.exists()


def test_import_validates_full_batch_before_creating_database(questions, tmp_path):
    questions[0]["review_status"] = "approved"
    questions[0]["is_active"] = True
    questions[1]["references"] = []
    qpath = tmp_path / "invalid_batch.json"
    dbpath = tmp_path / "untouched.db"
    qpath.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="references"):
        import_approved(qpath, dbpath)
    assert not dbpath.exists()
