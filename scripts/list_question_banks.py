"""列出并校验练习候选题库，不修改审核状态或数据库。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.validate_c_questions import load_questions

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "question_banks.json"


def inventory(catalog_path: str | Path = DEFAULT_CATALOG) -> list[dict]:
    catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    entries = []
    ids: set[str] = set()
    sentences: set[str] = set()
    for bank in catalog["practice_banks"]:
        rows = load_questions(ROOT / bank["path"])
        if len(rows) != bank["expected_count"]:
            raise ValueError(f"{bank['path']}: 题目数与目录声明不一致")
        for row in rows:
            if row["id"] in ids:
                raise ValueError(f"跨题库 id 重复: {row['id']}")
            if row["sentence"] in sentences:
                raise ValueError(f"跨题库句子重复: {row['id']}")
            ids.add(row["id"])
            sentences.add(row["sentence"])
        entries.append({
            "path": bank["path"], "name": bank["name"], "count": len(rows),
            "pending": sum(q["review_status"] == "pending" for q in rows),
            "approved_active": sum(q["review_status"] == "approved" and q["is_active"] for q in rows),
        })
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="显示全部练习候选题库的路径、数量与审核状态")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    try:
        entries = inventory(args.catalog)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"题库目录校验失败: {exc}")
        return 1
    for item in entries:
        print(f"{item['path']}: {item['count']} 道；待审核 {item['pending']}；已审核启用 {item['approved_active']}")
    print(f"合计 {sum(item['count'] for item in entries)} 道练习候选题；评测专用文件不计入练习题库。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
