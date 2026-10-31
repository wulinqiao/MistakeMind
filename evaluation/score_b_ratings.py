"""Validate human modification ratings against accepted generated corrections."""
import argparse
import json
from pathlib import Path


def score(run_path, ratings_path):
    latest = {}
    for line in Path(run_path).read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("kind") == "result":
            latest[row["id"]] = row
    expected = {(r["id"], i) for r in latest.values() if r["status"] == "success"
                for i, _ in enumerate(r["result"]["corrections"])}
    ratings = json.loads(Path(ratings_path).read_text(encoding="utf-8"))
    if not isinstance(ratings, list):
        raise ValueError("ratings 必须为数组")
    seen, reviewed = set(), []
    for row in ratings:
        if not isinstance(row, dict) or type(row.get("correction_index")) is not int:
            raise ValueError("评分条目必须含 id 和整数 correction_index")
        key = (row.get("id"), row["correction_index"])
        if key not in expected or key in seen:
            raise ValueError("评分包含未知或重复的修改")
        seen.add(key)
        values = (row.get("effective"), row.get("meaning_preserved"))
        if values == (None, None):
            continue
        if any(type(value) is not bool for value in values) or not isinstance(row.get("reviewer"), str) or not row["reviewer"].strip():
            raise ValueError("已填写的评分必须有两项布尔评分和审核人")
        reviewed.append(row)
    n = len(reviewed)
    return dict(total_corrections=len(expected), reviewed=n, pending=len(expected)-n,
                effective_modification_ratio=sum(r["effective"] for r in reviewed)/n if n else None,
                meaning_preservation_ratio=sum(r["meaning_preserved"] for r in reviewed)/n if n else None,
                jointly_valid_ratio=sum(r["effective"] and r["meaning_preserved"] for r in reviewed)/n if n else None,
                note="仅对已人工评分的修改统计，必须同时报告覆盖率；不把精确匹配或模型自评当人工评分。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run")
    parser.add_argument("ratings")
    args = parser.parse_args()
    print(json.dumps(score(args.run, args.ratings), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
