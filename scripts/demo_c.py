"""使用模拟作答展示推荐逻辑，不会写入数据库。"""
from scripts.recommend_c import category_profile, recommend_next
from scripts.validate_c_questions import load_questions


def main() -> None:
    questions = load_questions("data/questions.json")
    attempts = (
        [{"question_id": f"demo_error_{i}", "category": "搭配不当", "is_correct": False} for i in range(4)]
        + [{"question_id": f"demo_right_{i}", "category": "成分残缺", "is_correct": True} for i in range(5)]
    )
    print("模拟学生练习记录：搭配不当错误 4 次，成分残缺正确 5 次")
    print("分类画像（前 3）：", category_profile(attempts)[:3])
    print("推荐结果：", recommend_next(questions, attempts, allow_pending_demo=True))
    print("注意：仅演示使用待审核题；正式推荐默认禁止使用待审核题。")


if __name__ == "__main__":
    main()
