import argparse
import copy
import json
from pathlib import Path

import pytest

from agents.config import Settings
from agents.demo import ERRORS, NORMALS
from agents.pipeline import AgentService
from evaluation.b_metrics import summarize
from evaluation.run_b import retrieve, run
from evaluation.score_b_ratings import score
from scripts.validate_c_questions import load_questions
from tests.test_b_agents import live_service, normal


def args(tmp_path, **kw):
    values = dict(data="data/b_evaluation_candidates.json", group="structured", output=str(tmp_path / "run.jsonl"),
                  context=None, development=True, live=False, resume=False, retry_failed=False)
    values.update(kw)
    return argparse.Namespace(**values)


def tiny_dataset(tmp_path, *, reviewed=False):
    row = copy.deepcopy(load_questions("data/b_evaluation_candidates.json")[-1])
    if reviewed:
        row.update(review_status="approved", review={"reviewer": "test-fixture-only", "reviewed_at": "2026-10-30T10:00:00+08:00"})
    path = tmp_path / "tiny.json"
    path.write_text(json.dumps([row], ensure_ascii=False), encoding="utf-8")
    return path


def test_evaluation_candidates_separate_and_pending():
    rows = load_questions("data/b_evaluation_candidates.json")
    assert len(rows) == 80 and sum(q["has_error"] for q in rows) == 64
    assert sum(len(q["error_types"]) > 1 for q in rows) == 8
    assert all(q["review_status"] == "pending" and not q["is_active"] for q in rows)
    assert len({q["sentence"] for q in rows}) == 80
    assert not ({q["sentence"] for q in rows} & ({x[0] for x in ERRORS} | set(NORMALS)))
    for cat in {q["category"] for q in rows if q["has_error"]}:
        assert sum(q["category"] == cat for q in rows) == 8


def test_formal_rejects_pending_before_any_output(tmp_path):
    options = args(tmp_path, development=False)
    with pytest.raises(ValueError, match="人工审核"):
        run(options)
    assert not Path(options.output).exists()


@pytest.mark.parametrize("group", ["baseline", "structured", "full"])
def test_each_offline_group_reports_declines_without_fake_quality(tmp_path, group):
    options = args(tmp_path, group=group, data=str(tiny_dataset(tmp_path)))
    report = run(options)
    assert report["samples"] == 1 and report["statuses"]["needs_review"] == 1
    assert report["mode"] == "mock" and not report["real_diagnostic_experiment"]
    assert report["primary_accuracy_all_requests"] == 0
    assert report["conservative_detection_all_requests"]["fp"] == 1


def test_resume_does_not_repeat_and_rejects_changed_data(tmp_path):
    options = args(tmp_path, data=str(tiny_dataset(tmp_path)))
    run(options)
    original = Path(options.output).read_text(encoding="utf-8")
    options.resume = True
    run(options)
    assert Path(options.output).read_text(encoding="utf-8") == original
    rows = json.loads(Path(options.data).read_text(encoding="utf-8"))
    rows[0]["sentence"] += "不同版本"
    Path(options.data).write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="恢复被拒绝"):
        run(options)


def test_declined_rows_retry_is_explicit_and_appends_audit_record(tmp_path):
    options = args(tmp_path, data=str(tiny_dataset(tmp_path)))
    run(options)
    options.resume = options.retry_failed = True
    run(options)
    lines = [json.loads(x) for x in Path(options.output).read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 3 and lines[-1]["attempt"] == 2


def test_live_prediction_never_receives_gold_and_shared_protocol(tmp_path):
    options = args(tmp_path, data=str(tiny_dataset(tmp_path, reviewed=True)), development=True, live=True)
    service, seen = live_service([normal(), {"approved": True, "reason": "一致"}])
    report = run(options, service=service)
    payload = json.loads(seen[0]["messages"][1]["content"])
    assert set(payload) == {"sentence", "grade", "optional_context", "need_hints"}
    assert report["success_rate_all_requests"] == 1 and report["external_calls"] == 2
    assert not report["real_diagnostic_experiment"]


def test_formal_reviewed_dataset_still_needs_minimum_size_and_coverage(tmp_path):
    options = args(tmp_path, data=str(tiny_dataset(tmp_path, reviewed=True)), development=False)
    with pytest.raises(ValueError, match="至少 60"):
        run(options)


def test_failures_stay_in_denominator(tmp_path):
    gold = load_questions("data/b_evaluation_candidates.json")[:2]
    row = dict(id=gold[0]["id"], status="success", result=dict(has_error=True, error_types=[gold[0]["category"]]), latency_ms=10)
    report = summarize(gold, [row, dict(id=gold[1]["id"], status="failed", latency_ms=20)])
    assert report["success_rate_all_requests"] == .5
    assert report["primary_accuracy_all_requests"] == .5
    assert report["conservative_detection_all_requests"]["recall"] == .5
    assert report["accepted_only_diagnostic_metrics"]["detection"]["recall"] == 1.0


def test_retrieval_does_not_reveal_same_sentence_or_close_paraphrase():
    q = load_questions("data/b_evaluation_candidates.json")[0]
    assert retrieve(q["sentence"], [q]) == []


def test_human_ratings_require_real_reviewer_and_correction_alignment(tmp_path):
    runpath, ratings = tmp_path / "run.jsonl", tmp_path / "ratings.json"
    runpath.write_text(json.dumps(dict(kind="result", id="x", status="success", result={"corrections": [{"text": "x"}]})) + "\n", encoding="utf-8")
    row = dict(id="x", correction_index=0, effective=True, meaning_preserved=True, reviewer=None)
    ratings.write_text(json.dumps([row]), encoding="utf-8")
    with pytest.raises(ValueError, match="审核人"):
        score(runpath, ratings)
    row["reviewer"] = "human reviewer"
    ratings.write_text(json.dumps([row]), encoding="utf-8")
    assert score(runpath, ratings)["jointly_valid_ratio"] == 1
    row["correction_index"] = 3
    ratings.write_text(json.dumps([row]), encoding="utf-8")
    with pytest.raises(ValueError, match="未知"):
        score(runpath, ratings)
