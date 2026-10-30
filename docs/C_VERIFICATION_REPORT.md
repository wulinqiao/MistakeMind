# C 模块真实运行与修复记录

验证日期：2026-10-28（北京时间）。目标：zsk-67/MistakeMind 的 feature/data-eval 分支；起始提交为 765be461c80ee99f070539f8e9052d3b6a086a18。

## 验证方法与环境

在 Windows 的独立临时副本中实际执行 Python。由于 Git 下载连接失败，通过 GitHub 连接读取固定提交的 28 个文本源文件，并逐一核对 Git blob SHA，一致后运行。未使用用户 D 盘项目或正式数据库；未执行真实模型请求。

环境：Python 3.10.11、pytest 8.4.2、FastAPI 0.162.0、Pydantic 2.14.1、Starlette 1.7.0、httpx 0.28.1。依赖装在本次验证的隔离环境中。

## 测试结果

| 阶段 / 命令 | 实际结果 |
| --- | --- |
| 原始代码：python -m pytest tests/test_c_module.py -q | 11 passed in 0.17s |
| 原始代码：python -m pytest -q | 1 failed, 13 passed；全空格输入错误返回 500 |
| 修复后：python -m pytest tests/test_c_module.py -q | 82 passed in 0.36s |
| 修复后：python -m pytest -q | 85 passed, 1 warning in 0.91s |

增加了 71 个参数化用例实例，覆盖非法题库值、导入审核与批次保护、重复导入、推荐边界、评测输入校验等。全量测试包含 3 项已有 API 测试；同时加强了全空格输入测试对错误详情的检查。

唯一 warning 来自 Starlette 测试客户端对 httpx 的弃用提示，不影响本次断言通过。未通过屏蔽警告或跳过用例改变结果。

## 实际演示

1. `python -m scripts.validate_c_questions data/questions.json`：结构校验通过，共 20 道；16 道病句覆盖八类、每类 2 道，另有 4 道正常句；20 道均待审核，0 道已审核。
2. `python -m scripts.demo_c`：模拟“搭配不当答错 4 次，成分残缺答对 5 次”，推荐 c_005，类别为搭配不当，priority_score=0.863333。不写数据库。正式推荐默认不会选这些待审核题。
3. `python -m scripts.import_c_questions data/questions.json --dry-run`：可导入 0 道。
4. C 导入命令指定隔离 --db 路径、旧导入命令指定隔离 DATABASE_PATH：均返回没有已审核启用题、不修改数据库；两条数据库路径的 Test-Path 实际结果均为 False。
5. `python -m evaluation.metrics evaluation/example_gold.json evaluation/example_pred.json`：4 条固定示例，TP=2、FP=0、FN=1；Precision=1.0、Recall=0.6667、F1=0.8，八类 Macro-F1=0.125。八类均计入宏平均，未出现类别的 F1 计 0。这些数字仅说明示例计算跑通，不代表模型实际能力。

## 发现并修复的问题

- 题库校验遇到数组或对象形式的枚举值时抛出 TypeError；错误 references 的提示字符串还会触发格式化异常。现在返回可读的校验错误。
- 旧导入入口能绕过 C 审核。现在识别 C 元数据后整批转入审核校验，混合或缺失审核字段的题库在建库前拒绝。旧标准格式继续兼容。两个入口显式关闭导入连接。
- 推荐的 recent_limit=0 错把全部历史当作近期；SQLite 的 0 被统计为答对；字符串等非法正确性值被默认为答对；演示开关会放行 rejected。上述行为已修复，并明确历史顺序为从旧到新。
- 评测对缺失/非法题号、空输入、非对象记录或正常句错误分类缺少一致校验。现在统一抛出 ValueError，保留原计算公式。
- 原有 API 参数错误详情含 ValueError 对象，无法序列化，导致全空格句子返回 500。现在把异常转成文本，已有测试验证返回 400 和 VALIDATION_ERROR。

实际重复导入同一已审核题时，现有 SQLite 外键约束下作答仍保留、foreign_key_check 为空，因此保留了原有 INSERT OR REPLACE 行为，没有为了假设中的故障改写数据库层。

## 范围与下一步

题库通过的是结构校验，20 道内容仍需人工教学审核；本次未把题目改为 approved 或启用。推荐是独立原型，尚未接入线上 API。评测是八类单标签离线演示，尚无真实模型对照实验。

修复仅提交到个人 Fork 的 feature/data-eval；不修改 main，不自动合并，不向原仓库创建 PR。Windows 本地取回步骤见 [C_DEVELOPMENT_GUIDE.md](C_DEVELOPMENT_GUIDE.md)，保留原 origin，额外使用 fork 远端。
