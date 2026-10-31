"""校验新题交付的一致性及审核保护；语文教学正确性仍需教师复核。"""
import json
from pathlib import Path

import pytest

from scripts.import_c_questions import import_approved
from scripts.list_question_banks import inventory
from scripts.validate_c_questions import CATEGORIES, load_questions

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data/school_questions.json"


def test_school_bank_schema_and_honest_attribution():
    rows = load_questions(BANK)
    assert len(rows) == 44
    assert {q["category"] for q in rows if q["has_error"]} == set(CATEGORIES)
    assert {q["difficulty"] for q in rows} == {"初中", "高中"}
    sources = json.loads((ROOT / "data/school_sources.json").read_text(encoding="utf-8"))
    known_urls = {s["url"] for s in sources["sources"]}
    for row in rows:
        meta = row["source_metadata"]
        assert meta["source_type"] == "project_authored_teaching_pattern_variant"
        assert meta["ai_assisted"] is True
        assert meta["type_reference_urls"] and set(meta["type_reference_urls"]) <= known_urls
        assert "非中高考原题" in row["source"]
        if row["has_error"]:
            assert all(ref["text"] != row["sentence"] for ref in row["references"])
        else:
            assert row["references"] == [{"text": row["sentence"], "edit": "无需修改，保留原句。"}]


@pytest.mark.parametrize("qid", ["school_025", "school_026", "school_027", "school_028"])
def test_ambiguous_items_preserve_two_explicit_interpretations(qid):
    row = next(q for q in load_questions(BANK) if q["id"] == qid)
    assert row["category"] == "表意不明"
    assert len(row["references"]) >= 2
    assert len({r["text"] for r in row["references"]}) == len(row["references"])
    assert all(r.get("interpretation") for r in row["references"])
    assert row["source_metadata"].get("review_focus")


def test_new_school_bank_does_not_bypass_review_or_create_database(tmp_path):
    assert all(q["review_status"] == "pending" and not q["is_active"] for q in load_questions(BANK))
    db_path = tmp_path / "not_approved.db"
    assert import_approved(BANK, db_path) == 0
    assert not db_path.exists()


def test_current_inventory_excludes_withdrawn_cs2w_and_evaluation_sets():
    catalog = json.loads((ROOT / "data/question_banks.json").read_text(encoding="utf-8"))
    current = {e["path"] for e in inventory()}
    withdrawn = {e["path"] for e in catalog["withdrawn_banks"]}
    assert "data/school_questions.json" in current
    assert "data/external/cs2w_grammar_candidates.json" in withdrawn
    assert current.isdisjoint(withdrawn)
    assert current.isdisjoint(catalog["evaluation_only"])


def test_readable_preview_includes_every_sentence_answer_and_explanation():
    preview = (ROOT / "data/SCHOOL_QUESTIONS_PREVIEW.md").read_text(encoding="utf-8")
    for row in load_questions(BANK):
        assert f"### {row['id']} · {row['difficulty']}" in preview
        assert row["sentence"] in preview
        assert row["explanation"] in preview
        assert all(ref["text"] in preview for ref in row["references"])
