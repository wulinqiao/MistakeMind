"""仅导入审核通过的题目，不更改 D 的原始导入脚本。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from db.database import Database
from scripts.validate_c_questions import load_questions


def import_approved(path: str | Path, db_path: str | Path | None = None, dry_run: bool = False) -> int:
    rows = load_questions(path)
    approved = [r for r in rows if r["review_status"] == "approved" and r["is_active"]]
    if dry_run:
        print(f"预览：{len(approved)} 道已审核且启用的题目可以导入（共 {len(rows)} 道）")
        return len(approved)
    if not approved:
        print("没有已审核且启用的题目；不修改数据库。")
        return 0
    db = Database(db_path)
    with db.connect() as conn:
        for item in approved:
            conn.execute(
                """INSERT OR REPLACE INTO questions
                (id,sentence,mode,category,error_types_json,references_json,difficulty,source,is_active)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    item["id"], item["sentence"], item["mode"], item["category"],
                    json.dumps(item["error_types"], ensure_ascii=False),
                    json.dumps(item["references"], ensure_ascii=False),
                    item["difficulty"], item["source"], 1
                ),
            )
    print(f"成功导入 {len(approved)} 道已审核题目。")
    return len(approved)


def main() -> None:
    parser = argparse.ArgumentParser(description="审核通过后导入 MistakeMind SQLite 题库")
    parser.add_argument("path", nargs="?", default="data/questions.json")
    parser.add_argument("--db", default=None, help="可选：数据库路径；默认采用 D 模块配置")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    import_approved(args.path, args.db, args.dry_run)


if __name__ == "__main__":
    main()
