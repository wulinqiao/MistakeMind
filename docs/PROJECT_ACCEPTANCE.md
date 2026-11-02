# 项目完善与验收说明

## 2026-11-02 题库启用更新

用户已明确确认当前练习目录全部 64 条内容审核通过。确认依据、审核时间和用户身份说明已写入 data/*.reviewed.json 及 docs/review_forms/*.approved_20261102.json；不声称新增教师逐题复审。原始候选保留待审核状态供追溯，目录通过 reviewed_path 指向已审导出。

正式 data/mistakemind.db 已导入 64 个不同句子、三种形式共 192 条练习记录，现有用户与作答保留，导入前已备份数据库。运行 `./start.ps1` 后刷新页面即可取题。重新部署可使用 import_c_questions 的 --all-modes 参数导入两个 reviewed 文件。

本轮回归 213 passed。下方 2026-11-01 的“练习题待审核”描述为当时状态，现已完成；模型修改质量评分、full 组独立工具题库与历史场景审核、实际服务稳定性和现场彩排仍是后续事项。练习题获批不自动构成与最终测试集无近似泄漏的 full 工具题库。

本次完善以《项目计划》中的完整学习闭环为验收主线。核心工程已实现；正式练习题人工审核、修改质量人工评分及完整方案工具题库验收需要真实人工依据，不能由程序替代。

## 运行

Windows 推荐 Python 3.12。进入项目目录后：

```powershell
./start.ps1 -Demo
```

打开 http://127.0.0.1:8000。默认提供前后端同源服务，刷新子页面仍可正常打开。首次运行安装依赖并构建页面，之后启动复用现有构建。修改前端后加 `-Build`。

演示使用独立的 data/demo.db 和固定 Mock。36 道题是 12 个固定开发句子的三种交互形式，不是 36 条独立人工审核语料。所有页面都显示演示说明；未知自由输入返回待复核。演示库不混入正式题库或正式评测。

真实模式使用本地 .env，不带 -Demo 启动。进程环境变量优先于 .env。如果之前在同一终端手工设置过 AGENT_MODE 或 DATABASE_PATH，应先检查它们。不要覆盖已有 .env。

## 功能验收矩阵

| 计划项 | 实现与验收方法 |
| --- | --- |
| F01 句子诊断 | 正常句/病句、错误位置、类型、理由；未知 Mock 句或低置信度显示待复核 |
| F02 修改建议 | 结构化修改、原意保持复核、多解支持；真实修改质量另行人工评分 |
| F03 作答评判 | 判断/分类/自由修改；参考答案及语义判分，待复核不记成绩 |
| F04 题库训练 | 题型与难度筛选；题面不公开分类答案，练习和评测隔离 |
| F05 历史错题 | 作答和诊断同事务保存；历史原题、错误类型、解析、只看错题和再练 |
| F06 针对性推荐 | 近期平滑错误率与探索规则，优先选类型后避近期题；推荐 ID 精确打开 |
| F07 知识画像 | 累计正确率与错误次数、最近 50 次平滑表现、最小样本数 3、每日趋势 |
| Agent 工具链 | 返回诊断、判分、保存、推荐执行事件；页面可展开查看 |
| F08 追问/生成题 | 可选扩展，未列入当前必做验收；不自动生成未经审核的标准题 |

## 练习题审核与导入

64 道候选保留待审核、未启用。逐题审核表已准备在 docs/review_forms/，包含原句、类别、参考改法和解释。审核人填写每条 decision、reviewer、带时区的 reviewed_at、notes。若需要改题先修订源题，再重新导出表，防止审核了旧版本却启用新内容。

```powershell
./.venv/Scripts/python.exe -m scripts.review_practice apply data/questions.json docs/review_forms/questions.review.json data/questions.reviewed.json
./.venv/Scripts/python.exe -m scripts.import_c_questions data/questions.reviewed.json --dry-run
./.venv/Scripts/python.exe -m scripts.import_c_questions data/questions.reviewed.json
```

新 44 题使用 school_questions 对应的源文件和审核表。审核脚本不覆盖原题库，不默认为任何题目批准。B 的 79 条评测样本不导入训练库。正式 full 对照还需一份与最终测试句无同题、无近似泄漏的已审工具题库及独立历史场景。

## 测试

```powershell
./.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp .audit_tmp/check
cd frontend
npm ci
npm run build
```

--basetemp 使用可写工作区目录，避免当前 Windows 沙箱系统临时目录权限限制。pytest 强制 Mock，真实服务协议分支使用注入响应，不产生付费调用。不要把测试通过率当作真实模型准确率。

最新完整回归为 210 项通过。前端生产构建已通过；真实模型单句冒烟已完成。浏览器及真实实验的最终结果补充于本文末尾及 EXPERIMENT_RESULTS.md。

## Docker 与持久化

```powershell
docker compose up --build -d
```

Docker 多阶段构建 Vue 页面并由 FastAPI 提供；.dockerignore 排除 .env、数据库、Git 和测试产物。compose 在运行时读取本地 .env，挂载 data，数据库位于 /app/data/mistakemind.db。正式运行前必须导入已审核启用题。可用 `docker compose exec app python -m scripts.import_c_questions data/questions.reviewed.json` 导入已审文件。

需要离线容器演示时：先将环境改为 AGENT_MODE=mock、DATABASE_PATH=/app/data/demo.db，再运行 seed_demo。演示数据库不覆盖正式数据库。Docker 实际构建是否通过，以当前环境验证结果为准，不能由 Dockerfile 存在推断。

## 交付材料

完整设计和实现说明见 deliverables/课程报告.md，演示流程见 deliverables/课堂演示脚本.md。个人贡献按实际提交记录、测试和展示环节填写，不将计划中 25% 的比例当作已验证贡献。

## 仍需人工完成

1. 64 道练习候选的逐题教学审核、启用与正式导入。
2. 各真实模型输出修改的有效性与原意保持人工评分。
3. 正式 full 组工具题库、独立历史场景及推荐质量人工目标审核。
4. 团队成员实际贡献核对和课堂现场彩排。

## 最终实测结果

最终后端回归 210 passed，保留一条测试客户端依赖弃用提示；前端生产构建通过。浏览器完整应用验收见 BROWSER_VERIFICATION.md，已完成独立演示、推荐精确跳转、刷新持久化及小屏检查。Docker 未安装，未宣称容器实际构建通过。

真实基线与结构化组各评测 79 条，分别为 71/2/6 和 61/10/8 条接受/待复核/失败。全样本主类别准确率分别为 83.54% 与 72.15%，本次结果不支持结构化组整体优于基线。模型表现与服务超时仍是后续改进项；详见 EXPERIMENT_RESULTS.md。待复核计为有效流程结果时，流程完成率为 92.41% 与 89.87%，仍未达到计划 95% 的参考目标；此口径不同于模型接受率。

本地模型配置已移入被 Git 忽略的 .env，.env.example 的密钥为空。真实实验经用户明确授权，原始输出和运行时源码快照保存在 deliverables/experiment_records/，不包含 .env 或密钥。调用总数 269，已报告 token 合计 330089，实际金额以供应商账单为准。
