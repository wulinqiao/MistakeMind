# 题库入口：64 道练习候选题

当前练习目录采用普通初高中语文书面语场景。先看 [44 道新题完整预览](SCHOOL_QUESTIONS_PREVIEW.md)：逐题包含病句、类别、参考修改与解释，无须阅读 JSON。

| 文件 | 数量 | 内容与状态 |
| --- | ---: | --- |
| [questions.json](questions.json) | 20 | 原有自编候选：八类病句各 2 道，另有 4 道正常句；待审核、未启用 |
| [school_questions.json](school_questions.json) | 44 | 初高中常见题型变式：36 道病句、8 道正常句；待审核、未启用 |

合计 **64 道**不同候选。新题分布：前四类各 5 道，后四类各 4 道，另有正常句 8 道；建议初中阶段 28 道、高中阶段 16 道。年级是项目建议训练阶段，不表示原卷年级。

## 来源与选材

参考人教社教学资料、教育局刊载的初中病句教研文章、北师大病句分类讲解和学校教师的分类辨析，整理常见病因。准确链接及各材料用途见 [教学参考来源](school_sources.json)。

44 道题的题干、改法、解释均为本项目 **AI 辅助自编的题型变式，不是历年中高考原题，也不是教材原题**。参考链接支持语法规则或教学方向，不是这道新句子的原始出处，也不代表来源机构认可本题。题库结构校验通过仍不等于已通过教师的教学审核。

此前的 [CS2W 口语转写样本](external/README.md) 已因不符合中学书面语教学场景撤出练习目录。其历史文件和许可仅用于追溯，不计入 64 道候选，不应直接启用。

## 查看数量与校验

在项目根目录运行：

```powershell
python -m scripts.list_question_banks
```

脚本读取 [question_banks.json](question_banks.json)，逐库校验格式、数量与跨库重复；只统计 `practice_banks`，不统计撤回材料或评测集，不写数据库。

```powershell
python -m scripts.validate_c_questions data/school_questions.json
```

## 人工审核后导入

逐题复核病因、改法、原意及难度。表意不明题提供两种解释，应结合作者意图消歧，不能只接受其中一种。通过后才可设 `review_status="approved"` 和 `is_active=true`。

```powershell
python -m scripts.import_c_questions data/school_questions.json --dry-run
```

当前全部待审核，因此应显示 **0 道可导入**。网页读取数据库中的已启用题目，仓库候选数量与网页可练题数不同。

## 评测数据

`b_development_regressions.json` 是 B 模块开发回归样例；`b_evaluation_*.json` 是 B 模块评测数据；`evaluation/example_*.json` 是评测计算示例。它们保持评测用途，不用于凑练习题数量。
