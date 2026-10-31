# MistakeMind 成员 B 模块交接说明

本次交付包含核心诊断 Agent、Prompt、模型适配器、学生答案评判、质量控制、必要的后端集成，以及测试和评测材料。代码与离线工程验证已完成，真实模型实验和浏览器联调仍需团队接续。本文供 A、C、D 接入和验收使用。

交付分支为 `feature/agents`。接口基线为 v1.1，Prompt 版本为 `b-1.0.0`，当前人工审核数据版本为 `b-reviewed-1.1`。

## 从哪里开始

| 阅读入口 | 内容 |
| --- | --- |
| [B 模块说明](../agents/README.md) | 运行、配置、Agent 阶段、判分和评测命令 |
| [统一协作规范](../TEAM_ASSIGNMENT_AND_API_SPEC.md) / [API 文档](api.md) | 共享字段、错误码和职责边界 |
| [工程验证记录](B_VERIFICATION_REPORT.md) | 测试覆盖、离线验证及未验证范围 |
| [人工审核报告](B_HUMAN_REVIEW_REPORT.md) | 79 条正式样本、淘汰项及用户修订 |
| [实现报告与讲解稿](B_IMPLEMENTATION_REPORT.md) | 课程报告素材和 B 的展示讲解 |

主要实现位于 `agents/` 与 `prompts/`；`backend/agents.py` 保留后端调用入口。共享 Schema、API 和数据库改动已包含在同一分支，不需要 D 再手工复制一份 Agent。前端代码与 C 的原始题库、推荐算法未改动。

组员先在自己的 checkout 检查 `git status --short`，保存已有工作，再 `git fetch origin`。首次查看本分支可用 `git switch --track origin/feature/agents`；已有同名本地分支时用 `git switch feature/agents`，再 `git pull --ff-only origin feature/agents`。如有分叉或冲突，检查差异后再集成。

## 运行与离线验收

以下命令均在项目根目录执行。Windows 直接调用虚拟环境解释器，无需先修改 PowerShell 执行策略。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider
.\.venv\Scripts\python.exe -X utf8 -m scripts.demo_b
```

已取得 158 项自动化测试通过记录。默认 pytest 强制使用 Mock，模型协议与异常分支通过注入响应测试，不产生真实模型调用。demo_b 在临时数据库中跑通诊断、取题、答题、关联诊断保存、推荐、历史和画像，结束后清理，正式数据库保持不变。

启动页面需要两个终端：

```powershell
# 终端一：项目根目录
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

# 终端二：进入 frontend
cd frontend
npm.cmd install
npm.cmd run dev
```

前端为 <http://127.0.0.1:5173>，API 文档为 <http://127.0.0.1:8000/docs>。前端开发代理已经指向后端 8000 端口。

离线体验时在本地 `.env` 设 `AGENT_MODE=mock`。诊断页可使用固定样例：“通过开展此次活动，使同学们提高了环保意识。”未覆盖的句子会提示复核，不把 Mock 当作通用诊断模型。

当前 C 的 20 道练习题仍为 pending、未启用，因此普通练习页面可能没有题目。C 审核独立练习题并启用后，由 D 导入；B 的 79 条正式测试句保持隔离，不用于填充练习库。

## 接口和业务行为

五个 API 路径、响应外层和旧请求保持兼容，`meta.version` 更新为 v1.1。六个逻辑阶段共用确定性主控：路由、诊断、学生答案分析、提示、最小修改和复核；诊断、提示与修改通常共用一次生成，另一次调用做语义复核。

| 接口或行为 | 接入要点 |
| --- | --- |
| `POST /api/diagnose` | grade、optional_context、need_hints 和 request_id 传入 Agent；新增 needs_context，保留 review_status |
| 自由诊断待复核 | HTTP 200、success=true，data.review_status=needs_review；返回暂定解释，不作为通过结果保存 |
| `GET /api/questions` | 判断题为固定两项，类别选择题为统一类别；参考修改不再混入 options |
| `POST /api/submit-answer` | 判断/选择用 choice，修改用 text；空答案、错误类型或模式不匹配返回 VALIDATION_ERROR |
| 修改题评分 | 参考修改可精确通过，其他表达走语义评分和复核；原病句原样提交不能判对 |
| 作答无法可靠评分 | HTTP 200、success=false、data=null、error.code=MODEL_LOW_CONFIDENCE；不写成绩、不更新画像 |
| 成绩保存 | 作答和关联诊断同事务保存；数据库失败回滚，历史返回关联错误类型 |
| 模型故障 | MODEL_TIMEOUT 为 504；MODEL_INVALID_JSON、MODEL_UNAVAILABLE 为 502；真实调用失败不切回 Mock |

正常句返回 `has_error=false`、空 error_types、空 corrections 和 null error_span。置信度为自评门槛，不是校准概率。前端仍兼容暂定的布尔判断，A 应连同解释、needs_context 和 review_status 展示不确定性。

原有 category 字段因兼容继续返回，因此练习 API 不是隐藏标签的正式盲测接口。正式评测只向模型传句子和必要上下文。trace 记录模式、Prompt 版本、模型、阶段、耗时和已报告用量，不包含密钥或供应商原始响应。

## A C D 接续事项

| 成员 | 接下来需要完成 | 验收依据 |
| --- | --- | --- |
| A | 浏览器联调诊断、提示、答题、历史与画像；确认低置信度不会展示为普通答错，待复核结论有提示 | 页面演示或录屏、错误分支和刷新后的历史记录 |
| C | 审核独立练习/工具题库，准备 full 组的题库与历史场景；主责真实对照实验和人工修改质量评分 | 审核元数据、与测试集隔离的题库、实验表和失败案例 |
| D | 在运行环境私下配置模型，启动服务并导入 C 已审核启用题；验证真实服务、事务保存及部署环境 | 真实冒烟、接口调用轨迹、持久化与异常记录 |
| B | 配合模型兼容性与误判排查，根据真实结果维护 Prompt 和失败案例，完成个人展示 | Prompt 变更记录、实际实验结果和 60—90 秒讲解 |

真实服务配置写入本地 `.env`，进程环境变量优先。必填 `AGENT_MODE=live`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`，模型和地址按实际服务商填写。密钥不提交 Git。服务不支持 JSON 模式时可配置 `LLM_JSON_MODE=false`，本地 Schema 校验仍保留。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.smoke_b_live --live
```

该命令会调用真实服务。默认单次 HTTP 请求上限 20 秒，一次业务总预算 60 秒、最多四次外部请求；网络、429、5xx 最多重试一次，格式最多修复一次。

## 数据版本与正式实验

| 文件 | 当前用途和状态 |
| --- | --- |
| `data/b_development_regressions.json` | 17 条固定开发样例，不作为正式测试金标准 |
| `data/b_evaluation_candidates.json` | 原始 80 条 pending 候选，保留原貌用于审计 |
| `data/b_evaluation_reviewed_full.json` | 全量审核档案，79 approved、1 rejected |
| `data/b_evaluation_reviewed.json` | 正式集 79 条：61 条病句、18 条正常句，八类覆盖、8 条多标签；全部未启用 |

`b_eval_038` 已淘汰；`b_eval_043`、`b_eval_047` 按用户确认改为正常句，旧标注保留在 review.revisions。当前审核数据版本为 `b-reviewed-1.1`，旧版输出不能直接当作新版成绩或跨数据哈希恢复。

完成真实配置后先运行普通模型和结构化组：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run_b --group baseline --live --data data/b_evaluation_reviewed.json --output evaluation/runs/live_baseline_v11.jsonl
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run_b --group structured --live --data data/b_evaluation_reviewed.json --output evaluation/runs/live_structured_v11.jsonl
```

full 组还需要 C 提供 `data/b_context_reviewed.json`，含独立已审核启用的 questions、从旧到新的 attempts，以及可选人工标注的 target_weak_categories。题目使用既有完整 JSON 结构并带 review.reviewer、带时区的 review.reviewed_at；正式 full 拒绝空工具库、同题或高相似文本，详情见 B 模块说明。

```powershell
.\.venv\Scripts\python.exe -X utf8 -m evaluation.run_b --group full --live --data data/b_evaluation_reviewed.json --context data/b_context_reviewed.json --output evaluation/runs/live_full_v11.jsonl
```

输出包含 JSONL、summary.json 和人工评分模板 ratings.json。相同数据与配置可加 `--resume` 恢复；需要重试失败/拒判时再加 `--retry-failed`，旧尝试保留。人工逐条填写 effective、meaning_preserved 和 reviewer 后运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m evaluation.score_b_ratings evaluation/runs/live_structured_v11.jsonl evaluation/runs/live_structured_v11.ratings.json
```

报告应同时给出样本规模、成功/拒判/失败比例、检测与分类指标、修改评分覆盖率、典型失败案例、耗时及调用用量。仅成功结果的指标不能代替整体成绩。推荐继续使用现有 C/D 规则，其质量不归因于 B 的诊断模型。

本次推送不包含 `.env`、虚拟环境、node_modules、数据库及 evaluation/runs 生成结果；拉取后需要各自在本地配置和运行。当前已完成工程与数据审核，尚无真实模型精度、修改有效率、延时或费用结论，最终课程报告需在实际实验后补齐。
