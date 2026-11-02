"""Export per-question review forms and apply explicitly recorded human decisions."""
import argparse
import json
from datetime import datetime
from pathlib import Path

from scripts.validate_c_questions import load_questions, validate_questions


def export_review(source, output):
    rows = load_questions(source)
    form = [{"id": q["id"], "sentence": q["sentence"], "category": q["category"],
             "references": q["references"], "explanation": q["explanation"],
             "decision": "pending", "reviewer": "", "reviewed_at": "", "notes": ""} for q in rows]
    with Path(output).open("x", encoding="utf-8") as file:
        file.write(json.dumps(form, ensure_ascii=False, indent=2) + "\n")


def apply_review(source, form_path, output):
    rows = load_questions(source)
    forms = json.loads(Path(form_path).read_text(encoding="utf-8"))
    if not isinstance(forms, list) or any(not isinstance(x, dict) for x in forms):
        raise ValueError("审核表必须是对象数组")
    ids = [r.get("id") for r in forms]
    if len(set(ids)) != len(ids) or set(ids) != {q["id"] for q in rows}:
        raise ValueError("审核表题号必须与原题库一一对应")
    by_id = {r["id"]: r for r in forms}
    for q in rows:
        review = by_id[q["id"]]
        if any(review.get(k) != q[k] for k in ("sentence", "category", "references", "explanation")):
            raise ValueError("审核内容与源题不一致；如需修订标注，先修订源题并重新导出审核表")
        decision = review.get("decision")
        if decision not in {"pending", "approved", "rejected"}:
            raise ValueError("decision 必须为 pending/approved/rejected")
        if decision != "pending":
            if not all(isinstance(review.get(k), str) and review[k].strip() for k in ("reviewer", "reviewed_at", "notes")):
                raise ValueError("审核决定必须包含审核人、时间和逐题说明")
            timestamp = datetime.fromisoformat(review["reviewed_at"])
            if timestamp.tzinfo is None:
                raise ValueError("审核时间必须包含时区")
            q["review"] = {k: review[k] for k in ("reviewer", "reviewed_at", "notes")}
        q["review_status"] = decision
        q["is_active"] = decision == "approved"
    errors = validate_questions(rows)
    if errors:
        raise ValueError(errors)
    with Path(output).open("x", encoding="utf-8") as file:
        file.write(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    return sum(q["is_active"] for q in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    export = sub.add_parser("export")
    export.add_argument("source")
    export.add_argument("output")
    apply = sub.add_parser("apply")
    apply.add_argument("source")
    apply.add_argument("form")
    apply.add_argument("output")
    args = parser.parse_args()
    if args.action == "export":
        export_review(args.source, args.output)
        print("已导出逐题审核表；请人工填写 decision/reviewer/reviewed_at/notes。")
    else:
        print(f"已生成审核结果，{apply_review(args.source, args.form, args.output)} 道启用。原题库保持不变。")


if __name__ == "__main__":
    main()
