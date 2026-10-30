"""Coverage-aware B metrics. Failed and declined requests stay in the denominator."""
from __future__ import annotations

from evaluation.metrics import evaluate, _prf
from scripts.validate_c_questions import CATEGORIES


def summarize(gold, records, all_attempts=None):
    by_id = {row["id"]: row for row in records}
    accepted, paired_gold, paired_pred = [], [], []
    tp = fp = fn = correct = 0
    classes = {cat: [0, 0, 0] for cat in CATEGORIES}
    multi_tp = multi_fp = multi_fn = 0
    for item in gold:
        row = by_id.get(item["id"], {})
        ok = row.get("status") == "success"
        result = row.get("result") if ok else None
        gt = set(item["error_types"])
        pt = set(result["error_types"]) if result else set()
        if result:
            accepted.append(row)
            pred_error = result["has_error"]
            primary = result["error_types"][0] if pred_error else "其他"
            paired_gold.append({"id": item["id"], "has_error": item["has_error"], "category": item["category"]})
            paired_pred.append({"id": item["id"], "has_error": pred_error, "category": primary})
            tp += int(item["has_error"] and pred_error)
            fp += int(not item["has_error"] and pred_error)
            fn += int(item["has_error"] and not pred_error)
            correct += int(item["has_error"] == pred_error and (not pred_error or primary == item["category"]))
        else:
            primary = None
            # Abstentions penalize diseased positives as FN and normal negatives as FP.
            # This is a conservative end-to-end score, not a standard binary confusion matrix.
            fn += int(item["has_error"])
            fp += int(not item["has_error"])
        for cat, counts in classes.items():
            counts[0] += int(item["category"] == cat and primary == cat)
            counts[1] += int(item["category"] != cat and primary == cat)
            counts[2] += int(item["category"] == cat and primary != cat)
        multi_tp += len(gt & pt)
        multi_fp += len(pt - gt)
        multi_fn += len(gt - pt)
    total = len(gold)
    per_class = {cat: _prf(*counts) for cat, counts in classes.items()}
    ledger = all_attempts if all_attempts is not None else records
    calls = [event for row in ledger for event in row.get("trace", []) if event.get("action") == "llm_call"]
    usage = {key: sum(event.get("usage", {}).get(key, 0) for event in calls)
             for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    statuses = {s: sum(r.get("status") == s for r in by_id.values()) for s in ("success", "needs_review", "failed")}
    hit_scenarios = {r.get("recommendation_scenario", r["id"]): r["recommendation_hit"]
                     for r in records if r.get("recommendation_hit") is not None}
    hits = list(hit_scenarios.values())
    return {
        "samples": total, "statuses": statuses, "missing": total - len(by_id),
        "attempts_including_retries": len(ledger),
        "success_rate_all_requests": round(len(accepted) / total, 4) if total else 0,
        "review_rate_all_requests": round(statuses["needs_review"] / total, 4) if total else 0,
        "failure_rate_all_requests": round((statuses["failed"] + total - len(by_id)) / total, 4) if total else 0,
        "primary_accuracy_all_requests": round(correct / total, 4) if total else 0,
        "conservative_detection_all_requests": {**_prf(tp, fp, fn), "tp": tp, "fp": fp, "fn": fn,
            "note": "拒判/失败的病句计 FN，正常句计 FP；这是端到端保守分数，不是标准混淆矩阵。"},
        "classification_all_requests": {"macro_f1_eight_classes": round(sum(x["f1"] for x in per_class.values()) / 8, 4), "per_class": per_class},
        "multilabel_micro_all_requests": _prf(multi_tp, multi_fp, multi_fn),
        "accepted_only_diagnostic_metrics": evaluate(paired_gold, paired_pred) if paired_gold else None,
        "mean_latency_ms_all_requests": round(sum(r.get("latency_ms", 0) for r in by_id.values()) / total, 2) if total else 0,
        "external_calls": len(calls), "reported_usage": usage,
        "elapsed_ms_including_retries": sum(row.get("latency_ms", 0) for row in ledger),
        "usage_note": "缺失用量按未报告处理；仅累计上游成功解析响应的用量，不代表完整账单。费用需按实际服务价格人工核算。",
        "recommendation_hit_rate": sum(hits) / len(hits) if hits else None,
        "recommendation_samples": len(hits),
        "manual_modification_quality": None,
        "note": "人工修改质量另填 ratings.json；拒判和失败均保留。仅接受结果的指标不可作为整体能力。",
    }
