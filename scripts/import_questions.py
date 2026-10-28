import json
import sys
from db.database import Database, now_iso

def main(path: str):
    rows = json.loads(open(path, encoding="utf-8").read())
    db = Database()
    with db.connect() as c:
        for item in rows:
            c.execute("""INSERT OR REPLACE INTO questions
              (id,sentence,mode,category,error_types_json,references_json,difficulty,source,is_active)
              VALUES (?,?,?,?,?,?,?,?,?)""", (item["id"], item["sentence"], item["mode"], item["category"], json.dumps(item.get("error_types", []), ensure_ascii=False), json.dumps(item.get("references", item.get("options", [])), ensure_ascii=False), item.get("difficulty", "综合"), item.get("source", "import"), int(item.get("is_active", True))))
    print(f"imported {len(rows)} questions")

if __name__ == "__main__":
    main(sys.argv[1])

