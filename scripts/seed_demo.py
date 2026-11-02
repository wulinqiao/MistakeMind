"""Create an isolated development demo database from existing fixed Mock cases."""
import argparse
import json
from contextlib import closing
from pathlib import Path

from agents.demo import ERRORS, NORMALS
from db.database import Database, DEFAULT_DB, ROOT


def seed(path=ROOT / "data" / "demo.db"):
    path = Path(path).resolve()
    if path == DEFAULT_DB.resolve():
        raise ValueError("演示种子不能写入正式数据库；请使用 data/demo.db。")
    db = Database(path)
    cases = [(s, types, span, reason, refs) for s, types, span, reason, refs in ERRORS
             if types != ["表意不明"]]
    cases += [(s, [], None, "句子成分完整，不需要修改。", [s]) for s in NORMALS]
    with closing(db.connect()) as con, con:
        for i, (sentence, types, span, reason, refs) in enumerate(cases, 1):
            for j, mode in enumerate(("判断题", "选择题", "修改题"), 1):
                qid = f"demo_{i:02d}_{j}"
                con.execute("""INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(id) DO UPDATE SET sentence=excluded.sentence,
                    category=excluded.category, error_types_json=excluded.error_types_json,
                    references_json=excluded.references_json, is_active=1""",
                    (qid, sentence, mode, "成分残缺" if "成分残缺" in types else types[0] if types else "其他", json.dumps(types, ensure_ascii=False),
                     json.dumps([{"text": t} for t in refs], ensure_ascii=False), "初中",
                     "开发演示固定样例，不是人工审核题库或正式评测数据", 1))
                con.execute("INSERT OR REPLACE INTO question_details VALUES (?,?,?)", (qid, "[开发演示] " + reason, span))
    return len(cases) * 3


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "demo.db")
    args = parser.parse_args()
    print(f"已准备 {seed(args.db)} 道开发演示题。未修改候选审核状态，未导入正式评测集。")


if __name__ == "__main__":
    main()
