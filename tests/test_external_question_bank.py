import copy
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

from scripts.import_c_questions import import_approved
from scripts.prepare_cs2w_questions import (
    EXCLUDED_SOURCE_IDS, LICENSE_NAME, SOURCE_FILE, SOURCE_GIT_BLOB,
    SOURCE_REVISION, SOURCE_SHA256, SOURCE_URL, candidate_label, load_source, prepare_questions,
)
from scripts.validate_c_questions import validate_questions

ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "data" / "external" / "cs2w_grammar_candidates.json"


@pytest.fixture()
def source_rows():
    # 自编的两个小样本用于验证筛选，不依赖网络或未提交的完整原始语料。
    pairs = [
        (10001, "小河边边的柳树已经发芽了", "小河边的柳树已经发芽了", "1", "边边"),
        (10002, "小河边的柳树已经发了", "小河边的柳树已经发芽了", "2", "发了"),
    ]
    result = []
    for source_id, sentence, reference, label, anchor in pairs:
        position = sentence.index(anchor) + (1 if label == "1" else 0)
        grammar = "0" * position + label + "0" * (len(sentence) - position - 1)
        result.append({
            "id": source_id, "content": sentence, "ref": reference,
            "grammatical_error_label": grammar, "grammatical_error_num": 1,
            "disfluency_label": "0" * len(sentence), "disfluency_num": 0,
            "colloquial_word_label": "0" * len(sentence), "colloquial_word_num": 0,
            "asr_error_label": "0" * len(sentence), "asr_error_num": 0,
        })
    return result


def test_published_candidates_count_categories_and_uniqueness():
    rows = json.loads(BANK.read_text(encoding="utf-8"))
    assert len(rows) == 100
    assert Counter(row["category"] for row in rows) == {"成分残缺": 30, "成分赘余": 70}
    assert len({row["id"] for row in rows}) == len(rows)
    assert len({row["sentence"] for row in rows}) == len(rows)
    assert all(row["review_status"] == "pending" and row["is_active"] is False for row in rows)
    assert validate_questions(rows) == []


def test_published_source_attribution_preserves_training_split():
    for row in json.loads(BANK.read_text(encoding="utf-8")):
        metadata = row["source_metadata"]
        assert metadata["dataset"] == "CS2W"
        assert metadata["source_split"] == "train"
        assert metadata["source_file"] == SOURCE_FILE == "data/train.jsonl"
        assert metadata["source_url"] == SOURCE_URL
        assert metadata["source_revision"] == SOURCE_REVISION
        assert metadata["source_sha256"] == SOURCE_SHA256
        assert metadata["source_git_blob"] == SOURCE_GIT_BLOB
        assert metadata["license"] == LICENSE_NAME == "CC-BY-SA-4.0"
        assert metadata["category_mapping_status"] == "provisional"
        assert metadata["annotation_origin"] == "external_corpus"
        assert metadata["source_id"] not in EXCLUDED_SOURCE_IDS
        assert row["id"] == f"cs2w_train_{metadata['source_id']:06d}"
        assert row["mode"] == "修改题" and row["difficulty"] == "综合"
        assert row["sentence"] != row["references"][0]["text"]
        for key in ("original_disfluency_num", "original_colloquial_word_num", "original_asr_error_num"):
            assert metadata[key] == 0
        label = metadata["original_grammatical_error_label"]
        assert len(label) == len(row["sentence"])
        if row["category"] == "成分赘余":
            assert set(label) - {"0"} == {"1"}
            assert "".join(c for c, flag in zip(row["sentence"], label) if flag != "1") == row["references"][0]["text"]
        else:
            assert set(label) - {"0"} == {"2"}


def test_pending_external_candidates_never_create_database(tmp_path):
    db_path = tmp_path / "must_not_exist.db"
    assert import_approved(BANK, db_path) == 0
    assert not db_path.exists()


def test_converter_preserves_original_sentences_references_and_labels(source_rows):
    assert [candidate_label(row) for row in source_rows] == ["1", "2"]
    converted = prepare_questions(source_rows)
    assert len(converted) == 2
    assert validate_questions(converted) == []
    for row, source in zip(converted, source_rows):
        assert row["sentence"] == source["content"]
        assert row["references"] == [{"text": source["ref"]}]
        assert row["source_metadata"]["original_grammatical_error_label"] == source["grammatical_error_label"]
        assert row["source_metadata"]["source_id"] == source["id"]


def test_selection_is_deterministic_and_deduplicates(source_rows):
    duplicate_sentence = {**source_rows[0], "id": 99999}
    expanded = source_rows + [copy.deepcopy(source_rows[0]), duplicate_sentence]
    assert prepare_questions(expanded) == prepare_questions(list(reversed(expanded)))
    assert len(prepare_questions(expanded)) == 2
    assert len(prepare_questions(expanded, limit=1)) == 1
    assert prepare_questions(expanded, limit=1)[0]["category"] == "成分残缺"


@pytest.mark.parametrize("field", ["disfluency_num", "colloquial_word_num", "asr_error_num"])
def test_other_conversion_counts_are_rejected(source_rows, field):
    source_rows[0][field] = 1
    assert candidate_label(source_rows[0]) is None


@pytest.mark.parametrize("field", ["disfluency_label", "colloquial_word_label", "asr_error_label"])
def test_other_conversion_labels_are_rejected_even_if_count_is_zero(source_rows, field):
    source_rows[0][field] = "1" + source_rows[0][field][1:]
    assert candidate_label(source_rows[0]) is None


@pytest.mark.parametrize("field,value", [
    ("id", True), ("id", "1"), ("grammatical_error_num", 0),
    ("grammatical_error_label", "111"), ("grammatical_error_label", None),
    ("ref", "不属于原句的另一条参考"), ("content", "太短"),
    ("disfluency_num", False), ("disfluency_label", ""),
])
def test_malformed_or_nonmatching_source_records_are_rejected(source_rows, field, value):
    source_rows[0][field] = value
    assert candidate_label(source_rows[0]) is None


def test_mixed_grammar_types_are_not_forced_into_one_category(source_rows):
    row = source_rows[0]
    row["grammatical_error_label"] = "2" + row["grammatical_error_label"][1:]
    assert candidate_label(row) is None


def test_unchanged_reference_is_not_an_error_candidate(source_rows):
    source_rows[0]["ref"] = source_rows[0]["content"]
    assert candidate_label(source_rows[0]) is None


def test_redundancy_label_must_reconstruct_reference_exactly(source_rows):
    row = source_rows[0]
    row["grammatical_error_label"] = "1" + "0" * (len(row["content"]) - 1)
    assert candidate_label(row) is None


def test_missing_words_must_be_pure_insertion_and_small_edit(source_rows):
    row = source_rows[1]
    row["ref"] = row["content"] + "新增内容超过八个字符的长串"
    assert candidate_label(row) is None
    row["ref"] = row["content"].replace("小河", "大海") + "是"
    assert candidate_label(row) is None


@pytest.mark.parametrize("source_id", sorted(EXCLUDED_SOURCE_IDS))
def test_known_questionable_references_are_excluded(source_rows, source_id):
    source_rows[0]["id"] = source_id
    assert candidate_label(source_rows[0]) is None


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_limits_are_rejected(source_rows, limit):
    with pytest.raises(ValueError, match="limit"):
        prepare_questions(source_rows, limit=limit)


def test_offline_input_must_match_official_fixed_source():
    with pytest.raises(ValueError, match="SHA256"):
        load_source(b'{"not": "the fixed official train file"}\n')
    assert len(SOURCE_SHA256) == 64
    assert SOURCE_REVISION in SOURCE_URL


def test_source_checksum_success_path_and_jsonl_parse(source_rows, monkeypatch):
    # 校验器成功路径用本地自编 JSONL 及其校验值，测试本身不请求网络。
    from scripts import prepare_cs2w_questions as module

    raw = ("\n".join(json.dumps(row, ensure_ascii=False) for row in source_rows) + "\n").encode("utf-8")
    monkeypatch.setattr(module, "SOURCE_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(module, "SOURCE_GIT_BLOB", hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest())
    assert load_source(raw) == source_rows


def test_cli_output_uses_utf8_lf_and_matches_converter(source_rows, tmp_path, monkeypatch):
    from scripts import prepare_cs2w_questions as module

    input_path, output_path = tmp_path / "fixture.jsonl", tmp_path / "candidates.json"
    input_path.write_bytes(b"fixture")
    monkeypatch.setattr(module, "load_source", lambda raw: source_rows if raw == b"fixture" else [])
    monkeypatch.setattr(sys, "argv", ["prepare_cs2w_questions", "--input", str(input_path), "--output", str(output_path)])
    assert module.main() == 0
    output = output_path.read_bytes()
    assert b"\r\n" not in output and output.endswith(b"\n")
    assert json.loads(output.decode("utf-8")) == prepare_questions(source_rows)
