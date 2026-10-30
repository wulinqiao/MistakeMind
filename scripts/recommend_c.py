"""独立、可测试的 C 模块推荐规则；尚未接入 D 的线上接口。"""
from __future__ import annotations

from collections import defaultdict

CATEGORIES = (
    "成分残缺", "成分赘余", "搭配不当", "语序不当",
    "结构混乱", "表意不明", "不合逻辑", "关联词使用不当",
)


def category_profile(attempts: list[dict]) -> list[dict]:
    """历史按从旧到新排列；使用平滑错误率，避免一次作答就断言掌握程度。"""
    if not isinstance(attempts, list):
        raise ValueError("attempts 必须是按从旧到新排列的列表")
    totals = defaultdict(lambda: {"attempts": 0, "errors": 0})
    for index, attempt in enumerate(attempts):
        if not isinstance(attempt, dict):
            raise ValueError(f"attempts[{index}] 必须是对象")
        correct = attempt.get("is_correct")
        # JSON 使用 bool；SQLite 的 INTEGER 列读出为 0/1。
        if type(correct) is not bool and not (type(correct) is int and correct in (0, 1)):
            raise ValueError(f"attempts[{index}]: is_correct 必须是布尔值或整数 0/1")
        cat = attempt.get("category")
        if cat not in CATEGORIES:
            continue
        stats = totals[cat]
        stats["attempts"] += 1
        stats["errors"] += int(not correct)
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
    """历史按从旧到新排列；默认只推荐审核通过且启用的题目。

    recent_limit=0 表示不避开历史题。演示开关额外允许 pending 候选题，
    不会放行 rejected 题目或审核通过但未启用的题目。
    """
    if type(recent_limit) is not int or recent_limit < 0:
        raise ValueError("recent_limit 必须是非负整数")
    scores = {s["category"]: s["priority_score"] for s in category_profile(attempts)}
    eligible = [
        q for q in questions
        if q.get("category") in CATEGORIES and (
            (q.get("review_status") == "approved" and q.get("is_active") is True)
            or (allow_pending_demo and q.get("review_status") == "pending")
        )
    ]
    if not eligible:
        return None
    recent_attempts = attempts[-recent_limit:] if recent_limit else []
    recent_ids = {a.get("question_id") for a in recent_attempts}
    fresh = [q for q in eligible if q["id"] not in recent_ids]
    pool = fresh or eligible
    selected = min(pool, key=lambda q: (-scores[q["category"]], q["id"]))
    return {
        "question_id": selected["id"],
        "category": selected["category"],
        "priority_score": scores[selected["category"]],
        "reason": "根据分类作答历史的平滑错误率与探索奖励排序；优先避开最近练过的题，题目不足时允许复练。",
    }
