"""离线评测：病句检测 P/R/F1、八类单标签 Macro-F1；输入按 id 对齐。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.recommend_c import CATEGORIES


def _prf(tp: int, fp: int, fn: int) -> dict[str, float]:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4)}


def evaluate(gold: list[dict], predicted: list[dict]) -> dict:
    """gold/predicted 每条均为 {id,has_error,category}；category 为主类别。"""
    if len({x["id"] for x in gold}) != len(gold):
        raise ValueError("gold 中存在重复 id")
    if len({x["id"] for x in predicted}) != len(predicted):
        raise ValueError("predicted 中存在重复 id")
    g = {x["id"]: x for x in gold}
    p = {x["id"]: x for x in predicted}
    if set(g) != set(p):
        raise ValueError(f"题号不一致：missing={sorted(set(g)-set(p))}, extra={sorted(set(p)-set(g))}")
    for item in gold + predicted:
        if type(item.get("has_error")) is not bool:
            raise ValueError(f"{item['id']}: has_error 必须是布尔值")
        if item.get("has_error") and item.get("category") not in CATEGORIES:
            raise ValueError(f"{item['id']}: 病句 category 不是八类标签之一")
    tp = sum(g[i]["has_error"] and p[i]["has_error"] for i in g)
    fp = sum(not g[i]["has_error"] and p[i]["has_error"] for i in g)
    fn = sum(g[i]["has_error"] and not p[i]["has_error"] for i in g)
    per_class = {}
    for cat in CATEGORIES:
        class_tp = sum(
            g[i]["has_error"] and p[i]["has_error"]
            and g[i]["category"] == cat and p[i]["category"] == cat for i in g
        )
        class_fp = sum(p[i]["has_error"] and p[i]["category"] == cat and
                       not (g[i]["has_error"] and g[i]["category"] == cat) for i in g)
        class_fn = sum(g[i]["has_error"] and g[i]["category"] == cat and
                       not (p[i]["has_error"] and p[i]["category"] == cat) for i in g)
        per_class[cat] = _prf(class_tp, class_fp, class_fn)
    return {
        "samples": len(g),
        "detection": {**_prf(tp, fp, fn), "tp": tp, "fp": fp, "fn": fn},
        "classification": {
            "macro_f1_eight_classes": round(sum(v["f1"] for v in per_class.values()) / 8, 4),
            "per_class": per_class,
        },
        "note": "单标签主类别演示；完整数据集的多标签分类应另行设计评测。",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="离线病句检测与分类评测")
    parser.add_argument("gold", help="人工标注的 {id,has_error,category} JSON 数组")
    parser.add_argument("predicted", help="模型预测的同格式 JSON 数组")
    args = parser.parse_args()
    result = evaluate(
        json.loads(Path(args.gold).read_text(encoding="utf-8")),
        json.loads(Path(args.predicted).read_text(encoding="utf-8")),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
