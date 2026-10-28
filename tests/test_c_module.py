import copy
import json

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
