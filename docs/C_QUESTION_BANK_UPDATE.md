# C 题库补充记录（2026-10-31）

## 交付内容

在最新小组主仓库 `331edca4e95555375cd09001ed30ff06ac58b5ea` 基础上补充真实外部候选题；原有 `data/questions.json` 的 20 道题保持不变。

- 新增 `data/external/cs2w_grammar_candidates.json`：100 道，成分残缺 30、成分赘余 70。
- 新增来源、作者、许可说明和确定性生成脚本。
- 新增 `data/README.md`、`data/question_banks.json` 与仓库首页入口，明确两库共 120 道练习候选。
- 新增 `python -m scripts.list_question_banks`，一次列出所有题库、题数与审核状态，并检查跨库重复。

CS2W 是口语转书面语数据集，补充题并非覆盖八类的考试标准答案。所有新题保持 pending / is_active=false，须组内完成教学审核后才可启用；不改网页、接口、数据库或模型实现，也不改 B 模块评测数据。

## 来源与重现

仅使用 CS2W 训练集，固定版本 `be6e0519b433cfa9d8388b23308f1380716254fd`；原句和参考修改原样保留，逐题记录来源与暂定映射。

官方数据许可为 CC BY-SA 4.0，改编候选数据保留同一许可，详见 `data/external/README.md` 和 `LICENSE-CS2W.txt`。未把 FCGEC、NaSGEC 等限制再分发的数据复制到公开仓库。

从校验过 SHA256 和 Git blob 的原始训练文件离线重生成，输出与提交的候选 JSON 逐字节一致：202,510 字节，SHA256 `3b01580f51db22fea3842ef91c335fe492340c4e810a4fa42e409a788a1c9714`。

## 实际验证

环境：Windows，Python 3.10.11，pytest 8.4.2；测试默认模拟模型，不发送付费请求。

| 验证 | 结果 |
| --- | --- |
| `python -m scripts.list_question_banks` | 20 + 100 = 120 道候选，无跨库重复，全部待审核 |
| `python -m scripts.validate_c_questions data/external/cs2w_grammar_candidates.json` | 100 道结构校验通过，30 缺失 / 70 赘余 |
| `python -m scripts.import_c_questions data/external/cs2w_grammar_candidates.json --dry-run` | 0 道可导入，审核保护保持有效 |
| `python -m pytest tests/test_c_module.py tests/test_external_question_bank.py tests/test_question_bank_inventory.py -q` | 118 passed in 0.41s |
| `python -m pytest tests -q --tb=short` | 193 passed, 1 failed, 1 warning in 2.05s |

全套失败项为 `tests/test_b_agents.py::test_wall_clock_deadline_cancels_slow_response`：Python 3.10 的 `asyncio.exceptions.TimeoutError` 未被 B 模块中 `except TimeoutError` 捕获。**未做任何题库改动时，同一环境原始主分支为 157 passed, 1 failed**，失败项相同。本次没有修改 B 模块实现或屏蔽/跳过用例；该兼容问题需另行处理，不能把全套结果描述成全部通过。

warning 为测试客户端依赖的弃用提示。

## 组长查看入口

先看仓库首页“题库在哪里”，或直接打开 `data/README.md`；两个候选文件都为完整 JSON 数组，而不是只有第一条示例句子。评测专用样本不计入 120 道练习候选，也没有被搬入练习题库。
