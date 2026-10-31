# 中学书面语题库替换记录（2026-10-31）

## 问题与处理

此前 100 道 CS2W 口语转书面语候选含口语转写噪声，选材不适合初高中语文病句教学。它们已从 `practice_banks` 撤下，列为 `withdrawn_banks`；历史文件和许可保留用于追溯，不计入当前练习数，不应直接启用。

新增 `data/school_questions.json` 44 道题，采用校园、阅读、文化活动与研究学习等普通书面语场景。前四类病句各 5 道，后四类各 4 道，正常句 8 道；建议初中 28 道、高中 16 道，以基础辨析为主。加上原有 20 道候选，当前目录共 64 道。

这些题是参考公开教学资料后由项目 AI 辅助自编的题型变式，不是中高考原题、不是教材原题。来源清单只支持语法规则或教学目标，不表示句子出自原材料或获得原机构认可。四道歧义题均列出两种原意及对应改法。全部保留 `pending` / `is_active=false`，须教师或组内教学审核后才能启用。

- 人类可读的全题、改法及解析：`data/SCHOOL_QUESTIONS_PREVIEW.md`。
- 准确来源链接与用途：`data/school_sources.json`。
- 当前候选目录：`data/question_banks.json`。

本次没有调整模型、网页、接口、用户本地数据库或 B 模块评测集。

## 实际验证

环境：Windows、Python 3.10.11、pytest 8.4.2；测试使用模拟模型，不调用付费接口。

| 验证 | 结果 |
| --- | --- |
| 新题结构校验 | 44 题通过；36 病句、8 正常句，8 类齐全 |
| 练习题库目录检查 | 20 + 44 = 64；无跨库题号或原句重复 |
| 新题导入预览 | 0 道可导入，待审核保护有效 |
| `python -m pytest tests/test_c_module.py tests/test_external_question_bank.py tests/test_question_bank_inventory.py tests/test_school_question_bank.py -q` | 126 passed in 0.74s |
| `python -m pytest tests -q --tb=short` | 201 passed, 1 failed, 1 warning in 4.21s |

全套唯一失败仍为原有 `tests/test_b_agents.py::test_wall_clock_deadline_cancels_slow_response`：Python 3.10 中 `asyncio.exceptions.TimeoutError` 没有被 B 模块的 `except TimeoutError` 捕获。替换前同一环境同一失败项已存在（193 passed, 1 failed；更早未扩充题库的主分支为 157 passed, 1 failed）。本次未修改、跳过或屏蔽该用例，不能把全套结果说成全通过。

自动测试能验证数据结构、来源记录、预览一致性、重复检查和导入保护，不能代替语文教师对题目、答案和教学难度的审核。
