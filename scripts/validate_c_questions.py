"""C 模块题库结构校验；运行: python -m scripts.validate_c_questions data/questions.json"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

CATEGORIES = (
    "成分残缺", "成分赘余", "搭配不当", "语序不当",
    "结构混乱", "表意不明", "不合逻辑", "关联词使用不当",
)
DIFFICULTIES = {"小学高年级", "初中", "高中", "综合"}
MODES = {"判断题", "选择题", "修改题"}
STATUSES = {"pending", "approved", "rejected"}


def validate_questions(rows: object) -> list[str]:
    """返回错误列表，空列表代表通过。正常句使用 category='其他' 且 error_types=[]。"""
    errors: list[str] = []
    if not isinstance(rows, list):
        return ["顶层 JSON 必须是数组"]
    ids: set[str] = set()
    sentences: set[str] = set()
    for i, item in enumerate(rows, start=1):
        prefix = f"第{i}题"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: 必须是对象")
            continue
        qid = item.get("id")
        sentence = item.get("sentence")
        if not isinstance(qid, str) or not qid.strip():
            errors.append(f"{prefix}: id 必须是非空字符串")
        elif qid in ids:
            errors.append(f"{prefix}: id 重复 {qid}")
        else:
            ids.add(qid)
        if not isinstance(sentence, str) or not sentence.strip() or len(sentence) > 500:
            errors.append(f"{prefix}: sentence 必须是 1–500 字符")
        elif sentence in sentences:
            errors.append(f"{prefix}: 句子重复")
        else:
            sentences.add(sentence)
        if not isinstance(item.get("mode"), str) or item["mode"] not in MODES:
            errors.append(f"{prefix}: mode 不是有效枚举")
        if not isinstance(item.get("difficulty"), str) or item["difficulty"] not in DIFFICULTIES:
            errors.append(f"{prefix}: difficulty 不是有效枚举")
        if type(item.get("has_error")) is not bool:
            errors.append(f"{prefix}: has_error 必须是布尔值")
        category = item.get("category")
        types = item.get("error_types")
        if not isinstance(types, list) or any(not isinstance(t, str) or t not in CATEGORIES for t in types) or len(set(types)) != len(types):
            errors.append(f"{prefix}: error_types 必须是无重复的八类标签数组")
        elif item.get("has_error") is True and (category not in CATEGORIES or category not in types):
            errors.append(f"{prefix}: 病句的 category 必须在 error_types 中")
        elif item.get("has_error") is False and (category != "其他" or types):
            errors.append(f"{prefix}: 正常句须使用 category='其他' 和空 error_types")
        references = item.get("references")
        if not isinstance(references, list) or not references or any(
            not isinstance(ref, dict) or not isinstance(ref.get("text"), str) or not ref["text"].strip()
            for ref in references
        ):
            errors.append(f"{prefix}: references 必须是非空的 [{{'text': '...'}}] 数组")
        if not isinstance(item.get("explanation"), str) or not item["explanation"].strip():
            errors.append(f"{prefix}: explanation 不能为空")
        if not isinstance(item.get("source"), str) or not item["source"].strip():
            errors.append(f"{prefix}: source 不能为空")
        if not isinstance(item.get("review_status"), str) or item["review_status"] not in STATUSES:
            errors.append(f"{prefix}: review_status 必须是 pending/approved/rejected")
        if type(item.get("is_active")) is not bool:
            errors.append(f"{prefix}: is_active 必须是布尔值")
        if item.get("is_active") is True and item.get("review_status") != "approved":
            errors.append(f"{prefix}: 未审核通过的题目不能设为 is_active=true")
    return errors


def load_questions(path: str | Path) -> list[dict]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_questions(rows)
    if errors:
        raise ValueError("\n".join(errors))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 C 模块题库")
    parser.add_argument("path", nargs="?", default="data/questions.json")
    args = parser.parse_args()
    try:
        rows = load_questions(args.path)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"校验失败:\n{exc}")
        return 1
    counts = Counter(x["category"] for x in rows)
    approved = sum(x["review_status"] == "approved" for x in rows)
    print(f"结构校验通过：{len(rows)} 道候选题；正常句 {counts.get('其他',0)} 道")
    print("八类分布：" + "；".join(f"{c} {counts.get(c,0)}" for c in CATEGORIES))
    print(f"审核通过 {approved} 道；待审核 {sum(x['review_status']=='pending' for x in rows)} 道")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
