"""仅导入审核通过的题目；供 C 模块和原有导入入口共用。"""
from __future__ import annotations

import argparse
import json
from contextlib import closing
from pathlib import Path

from db.database import Database
from scripts.validate_c_questions import load_questions


def import_approved(path: str | Path, db_path: str | Path | None = None, dry_run: bool = False, *, all_modes: bool = False) -> int:
    rows = load_questions(path)
    approved = [r for r in rows if r["review_status"] == "approved" and r["is_active"]]
    if all_modes:
        # Reuse the same reviewed sentence, labels and references in each UI mode.
        # These are presentation variants, not additional independent examples.
        expanded = []
        suffixes = {"判断题": "judge", "选择题": "choice", "修改题": "edit"}
        for row in approved:
            for mode, suffix in suffixes.items():
                expanded.append(dict(row, id=row["id"] if mode == row["mode"] else row["id"] + "__" + suffix, mode=mode))
        if len({r["id"] for r in expanded}) != len(expanded):
            raise ValueError("题型派生后的题号冲突；未修改数据库。")
        approved = expanded
    if dry_run:
        print(f"预览：{len(approved)} 道已审核且启用的题目可以导入（共 {len(rows)} 道）")
        return len(approved)
    if not approved:
        print("没有已审核且启用的题目；不修改数据库。")
        return 0
    db = Database(db_path)
    with closing(db.connect()) as conn, conn:
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
            conn.execute("INSERT OR REPLACE INTO question_details(question_id,explanation,error_span) VALUES (?,?,?)",
                         (item["id"], item["explanation"], item.get("error_span")))
    print(f"成功导入 {len(approved)} 道已审核题目。")
    return len(approved)


def main() -> None:
    parser = argparse.ArgumentParser(description="审核通过后导入 MistakeMind SQLite 题库")
    parser.add_argument("path", nargs="?", default="data/questions.json")
    parser.add_argument("--db", default=None, help="可选：数据库路径；默认采用 D 模块配置")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--all-modes", action="store_true", help="同一已审核内容提供判断、分类选择、修改三种答题形式")
    args = parser.parse_args()
    import_approved(args.path, args.db, args.dry_run, all_modes=args.all_modes)


if __name__ == "__main__":
    main()
