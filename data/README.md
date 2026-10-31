# 题库入口：120 道练习候选题

仓库中不是只有一个句子。练习候选题分成两个文件保存，文件第一条只是其中一道题。

| 文件 | 数量 | 内容与状态 |
| --- | ---: | --- |
| [questions.json](questions.json) | 20 | 自编候选：八类病句各 2 道，另有 4 道正常句；待审核、未启用 |
| [external/cs2w_grammar_candidates.json](external/cs2w_grammar_candidates.json) | 100 | CS2W 训练集语法候选补充：成分残缺与成分赘余；待项目教学审核、未启用 |

共 120 条不同的候选题；**“候选题已入仓库”与“已经通过教学审核、导入正式数据库”是不同状态**。

## 一条命令查看完整数量

在项目根目录运行：

```powershell
python -m scripts.list_question_banks
```

脚本会读取 [question_banks.json](question_banks.json)，逐库校验格式、数量和跨库重复，并显示每个题库的文件路径和审核状态，不写数据库。

## 新增数据来自哪里

新增 100 道来自 [CS2W 官方仓库](https://github.com/guozishan/CS2W)，这是中文口语转书面语数据集。本项目只抽取其训练集中纯语法缺失/赘余样本，保留原文与原参考修改，转换为 C 模块格式。**它不是中高考八类病句的全面扩充，也不是本组已经人工审核的正式测试集。**

来源、作者、固定版本、筛选规则、可复现命令与 CC BY-SA 4.0 许可见 [external/README.md](external/README.md)。`val`、`test` 不用于本次练习扩充。

## 审核后如何导入

先逐条复核参考修改、分类和教学适用性，再把通过的题目设为 `review_status="approved"` 且 `is_active=true`。预览和导入继续使用已有的保护入口，例如：

```powershell
python -m scripts.import_c_questions data/external/cs2w_grammar_candidates.json --dry-run
```

当前全是 pending，因此结果应为 0 道可导入。仓库题库数量与网页可练题数不相同，网页接口从数据库读取已启用题目。

## 其他数据文件

- `b_development_regressions.json`：B 模块开发回归样例。
- `b_evaluation_*.json`：B 模块候选/审核评测数据，保持与练习题库隔离，不拿来充当练习题。
- `evaluation/example_gold.json`、`evaluation/example_pred.json`：固定评测计算示例，不是完整题库。
