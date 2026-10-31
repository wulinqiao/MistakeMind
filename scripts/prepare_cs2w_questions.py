"""从固定版本的 CS2W train 生成待审核候选题；不读取验证集或测试集。"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

SOURCE_REPOSITORY = "https://github.com/guozishan/CS2W"
SOURCE_REVISION = "be6e0519b433cfa9d8388b23308f1380716254fd"
SOURCE_FILE = "data/train.jsonl"
SOURCE_URL = f"https://raw.githubusercontent.com/guozishan/CS2W/{SOURCE_REVISION}/{SOURCE_FILE}"
SOURCE_SHA256 = "acf249f7e8077337fc8e4029e7c381e117f3bc780fef48c820e4f328e78f563a"
SOURCE_GIT_BLOB = "2cb49b442e1bd225c0a00f241772fb57d671c075"
LICENSE_NAME = "CC-BY-SA-4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "external" / "cs2w_grammar_candidates.json"
LABEL_CATEGORIES = {"1": "成分赘余", "2": "成分残缺"}
# 明显有疑问的原始参考保留在上游，不纳入本候选子集；不自行改写答案。
EXCLUDED_SOURCE_IDS = {
    1202: "原参考把唯一一个改为唯一个，需进一步复核",
    2426: "原参考的尤为惊喜的表现搭配仍需复核",
    5477: "原参考的安卓手机个插头仍需复核",
}


def load_source(raw: bytes) -> list[dict]:
    """无论在线下载还是 --input，都核对同一文件的完整字节校验值。"""
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"CS2W train SHA256 不匹配：{digest}；请使用固定版本的原始文件")
    blob = hashlib.sha1(f"blob {len(raw)}\0".encode("ascii") + raw).hexdigest()
    if blob != SOURCE_GIT_BLOB:
        raise ValueError("CS2W train Git blob 不匹配")
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("CS2W train 必须为非空的 JSONL 对象序列")
    return rows


def _is_subsequence(shorter: str, longer: str) -> bool:
    iterator = iter(longer)
    return all(any(character == candidate for candidate in iterator) for character in shorter)


def candidate_label(row: object) -> str | None:
    """仅保留单类语法标注、其他转换计数为零且编辑方向一致的短句。"""
    if not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] <= 0:
        return None
    if row["id"] in EXCLUDED_SOURCE_IDS:
        return None
    if any(type(row.get(key)) is not int or row[key] != 0
           for key in ("disfluency_num", "colloquial_word_num", "asr_error_num")):
        return None
    if type(row.get("grammatical_error_num")) is not int or row["grammatical_error_num"] < 1:
        return None
    sentence, reference = row.get("content"), row.get("ref")
    if (not isinstance(sentence, str) or not 8 <= len(sentence) <= 65
            or not isinstance(reference, str) or not reference.strip() or sentence == reference):
        return None
    for key in ("disfluency_label", "colloquial_word_label", "asr_error_label"):
        labels = row.get(key)
        if not isinstance(labels, str) or len(labels) != len(sentence) or set(labels) - {"0"}:
            return None
    labels = row.get("grammatical_error_label")
    if not isinstance(labels, str) or len(labels) != len(sentence) or set(labels) - {"0", "1", "2"}:
        return None
    types = set(labels) - {"0"}
    if len(types) != 1:
        return None
    label = next(iter(types))
    if label == "1":
        if not 1 <= len(sentence) - len(reference) <= 8:
            return None
        # 删除标为赘余的字符必须精确得到上游 ref，不采用含其他改动的记录。
        if "".join(character for character, flag in zip(sentence, labels) if flag != "1") != reference:
            return None
    elif not (1 <= len(reference) - len(sentence) <= 8 and _is_subsequence(sentence, reference)):
        return None
    return label


def prepare_questions(rows: list[dict], *, limit: int = 100) -> list[dict]:
    """按原始 id 确定性抽样；默认优先取 30 条缺失、70 条赘余。"""
    if type(limit) is not int or limit < 1:
        raise ValueError("limit 必须是正整数")
    pool = []
    seen_ids, seen_sentences = set(), set()
    ordered = sorted(
        (row for row in rows if isinstance(row, dict) and type(row.get("id")) is int),
        key=lambda row: (row["id"], str(row.get("content", "")), str(row.get("ref", ""))),
    )
    for row in ordered:
        label = candidate_label(row)
        if label is None or row["id"] in seen_ids or row["content"] in seen_sentences:
            continue
        seen_ids.add(row["id"])
        seen_sentences.add(row["content"])
        pool.append((row, label))
    missing_quota = min(30, limit)
    selected = [entry for entry in pool if entry[1] == "2"][:missing_quota]
    selected += [entry for entry in pool if entry[1] == "1"][:limit - len(selected)]
    if len(selected) < limit:
        selected_ids = {row["id"] for row, _ in selected}
        selected += [entry for entry in pool if entry[0]["id"] not in selected_ids][:limit - len(selected)]
    result = []
    for row, label in sorted(selected, key=lambda entry: entry[0]["id"]):
        category = LABEL_CATEGORIES[label]
        result.append({
            "id": f"cs2w_train_{row['id']:06d}",
            "sentence": row["content"],
            "mode": "修改题", "category": category, "error_types": [category], "has_error": True,
            "error_span": None,
            "references": [{"text": row["ref"]}],
            "difficulty": "综合",
            "explanation": (
                f"CS2W 原始语料将此口语句标为{'词语赘余' if label == '1' else '词语缺失'}，"
                "参考改写直接保留自原始 ref。课程类别为暂定映射，尚待本组人工教学审核；"
                "不代表原句在所有口语语境中均不可接受。"
            ),
            "knowledge_tags": ["外部语料候选", "口语转书面", category],
            "source": f"CS2W (EMNLP 2023), train, original id={row['id']}, CC BY-SA 4.0",
            "review_status": "pending", "is_active": False,
            "source_metadata": {
                "dataset": "CS2W", "source_id": row["id"], "source_split": "train",
                "source_revision": SOURCE_REVISION, "source_file": SOURCE_FILE,
                "source_url": SOURCE_URL, "source_sha256": SOURCE_SHA256,
                "source_git_blob": SOURCE_GIT_BLOB, "license": LICENSE_NAME,
                "license_url": LICENSE_URL,
                "attribution": "Zishan Guo, Linhao Yu, Minghui Xu, Renren Jin, Deyi Xiong (EMNLP 2023)",
                "original_grammatical_error_label": row["grammatical_error_label"],
                "original_grammatical_error_num": row["grammatical_error_num"],
                "original_disfluency_num": row["disfluency_num"],
                "original_colloquial_word_num": row["colloquial_word_num"],
                "original_asr_error_num": row["asr_error_num"],
                "category_mapping_status": "provisional",
                "annotation_origin": "external_corpus",
                "adaptation": "筛选、去重和字段转换；原文及参考改写未改动；未经过本组人工教学审核",
            },
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="可选：固定版本原始 train.jsonl，用于离线重现")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    try:
        if args.input:
            raw = args.input.read_bytes()
        else:
            with urlopen(SOURCE_URL, timeout=60) as response:
                raw = response.read(4_000_001)
            if len(raw) > 4_000_000:
                raise ValueError("下载超过预期大小")
        source_rows = load_source(raw)
        questions = prepare_questions(source_rows, limit=args.limit)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(questions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    except (ValueError, OSError) as exc:
        parser.exit(1, f"生成失败：{exc}\n")
    counts = Counter(question["category"] for question in questions)
    print(f"来源：CS2W train {len(source_rows)} 条；生成 {len(questions)} 道待审核候选题；{dict(counts)}")
    print(f"输出：{args.output}")
    if len(questions) < args.limit:
        print(f"可用记录不足目标 {args.limit}，已按实际数量生成，未补造题目。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
