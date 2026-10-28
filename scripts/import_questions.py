import json
import sys
from contextlib import closing
from pathlib import Path

from db.database import Database
from scripts.import_c_questions import import_approved


C_REVIEW_FIELDS = {"review_status", "has_error", "explanation", "error_span", "knowledge_tags"}


def main(path: str) -> int:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list) or any(not isinstance(item, dict) for item in rows):
        raise ValueError("题库必须是 JSON 对象数组")
    # 保留旧格式兼容；含 C 元数据就完整校验，误删审核字段也不能绕过。
    if any(C_REVIEW_FIELDS.intersection(item) for item in rows):
        return import_approved(path)
    db = Database()
    with closing(db.connect()) as c, c:
        for item in rows:
            c.execute("""INSERT OR REPLACE INTO questions
              (id,sentence,mode,category,error_types_json,references_json,difficulty,source,is_active)
              VALUES (?,?,?,?,?,?,?,?,?)""", (item["id"], item["sentence"], item["mode"], item["category"], json.dumps(item.get("error_types", []), ensure_ascii=False), json.dumps(item.get("references", item.get("options", [])), ensure_ascii=False), item.get("difficulty", "综合"), item.get("source", "import"), int(item.get("is_active", True))))
    print(f"imported {len(rows)} questions")
    return len(rows)

if __name__ == "__main__":
    main(sys.argv[1])

