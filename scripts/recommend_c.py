"""独立、可测试的 C 模块推荐规则；尚未接入 D 的线上接口。"""
from __future__ import annotations

from collections import defaultdict

CATEGORIES = (
    "成分残缺", "成分赘余", "搭配不当", "语序不当",
    "结构混乱", "表意不明", "不合逻辑", "关联词使用不当",
)


def category_profile(attempts: list[dict]) -> list[dict]:
    """最近作答优先输入；使用平滑错误率，避免一次作答就断言掌握程度。"""
    totals = defaultdict(lambda: {"attempts": 0, "errors": 0})
    for attempt in attempts:
        cat = attempt.get("category")
        if cat not in CATEGORIES:
            continue
        stats = totals[cat]
        stats["attempts"] += 1
        stats["errors"] += int(attempt.get("is_correct") is False)
    profile = []
    for cat in CATEGORIES:
        n = totals[cat]["attempts"]
        e = totals[cat]["errors"]
        # Laplace 平滑，样本少时不会得到极端的 0/1 错误率
        smoothed_error_rate = (e + 1) / (n + 2)
        # 轻微鼓励未练过的类别，避免长期只推荐一种病句
        exploration_bonus = 0.15 / (n + 1)
        profile.append({
            "category": cat, "attempts": n, "errors": e,
            "accuracy": (n - e) / n if n else None,
            "priority_score": round(smoothed_error_rate + exploration_bonus, 6),
        })
    return sorted(profile, key=lambda x: (-x["priority_score"], x["category"]))


def recommend_next(
    questions: list[dict],
    attempts: list[dict],
    *,
    allow_pending_demo: bool = False,
    recent_limit: int = 5,
) -> dict | None:
    """根据历史记录推荐可用题；默认只推荐审核通过且启用的题目。"""
    eligible = [
        q for q in questions
        if q.get("category") in CATEGORIES and (
            allow_pending_demo or (q.get("review_status") == "approved" and q.get("is_active") is True)
        )
    ]
    if not eligible:
        return None
    recent_ids = {a.get("question_id") for a in attempts[-recent_limit:]}
    fresh = [q for q in eligible if q["id"] not in recent_ids]
    pool = fresh or eligible
    scores = {s["category"]: s["priority_score"] for s in category_profile(attempts)}
    selected = min(pool, key=lambda q: (-scores[q["category"]], q["id"]))
    return {
        "question_id": selected["id"],
        "category": selected["category"],
        "priority_score": scores[selected["category"]],
        "reason": "根据近期分类作答的平滑错误率与探索奖励进行排序；避开最近练过的题。",
    }
