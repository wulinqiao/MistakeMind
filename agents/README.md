# B 模块使用说明

本模块实现病句诊断、分层提示、最小修改、学生答案评判与复核，并接入既有 FastAPI 和 SQLite。八类标签沿用团队规范；正常句不强制修改。当前交付验证了离线工程行为，尚未进行真实服务精度实验。

## 快速运行

在项目根目录运行，使用已安装 requirements.txt 的 Python 环境：

```powershell
python -m pytest -q
python -X utf8 -m scripts.demo_b
uvicorn backend.main:app --reload
```

demo_b 使用临时 SQLite 和固定样例，验证 HTTP 诊断、取题、作答、关联诊断、推荐、历史、画像和重新连接后的记录；结束后清理，不改正式数据库。示例轨迹直接打印为 JSON，既包含 Agent 阶段，也包含保存工具事件。

默认 pytest 强制 mock；真实接口协议测试通过 httpx.MockTransport 注入响应，不发送外部请求。pytest 通过不能证明语文诊断精度或前端实际交互效果。

## 真实服务配置

将根目录 .env.example 复制为 .env，在本地填写密钥、服务商提供的基础地址和模型名。不要在聊天、源码或日志中粘贴密钥。

```text
AGENT_MODE=live
LLM_API_KEY=本地填写
LLM_BASE_URL=服务商提供的兼容基础地址（通常以 /v1 结尾）
LLM_MODEL=服务商支持的模型名
LLM_JSON_MODE=true
LLM_TIMEOUT_SECONDS=20
LLM_TOTAL_TIMEOUT_SECONDS=60
LLM_MAX_CALLS=4
LLM_CONFIDENCE_THRESHOLD=0.7
```

进程环境变量优先于 .env。AGENT_MODE=auto 时，有密钥进入 live，无密钥进入 mock；显式 live 缺少密钥或模型会返回 MODEL_UNAVAILABLE。正式展示建议显式选择模式。

适配器向基础地址追加 /chat/completions，发送非流式 messages。若服务不支持 response_format，可将 LLM_JSON_MODE=false；不会自动改协议或切回 Mock。JSON 模式并不代替 Schema 校验，当前实现始终在本地校验类型与一致性。[官方结构化输出说明](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat)是协议参考，第三方服务的支持情况需要实际验证。

配置后显式进行一次真实诊断冒烟测试：

```powershell
python -X utf8 -m scripts.smoke_b_live --live
```

该命令会产生模型调用费用。默认一次生成加一次复核；网络、限流和服务错误最多重试一次，格式最多修复一次，共享四次调用和 60 秒总预算。单次整段 HTTP 操作使用异步取消控制 20 秒墙钟时限。鉴权或协议 4xx 不重试。

## 模块接口与六个阶段

backend/agents.py 保留 diagnose(sentence, need_hints=True, *, grade, optional_context, request_id, user_id) 兼容入口，并提供 grade_answer(ctx, question, answer_type)。内部依赖可注入 AgentService(settings, client)，便于离线测试。

| 阶段 | 输入 | 输出或效果 |
| --- | --- | --- |
| 路由 | AgentContext.task | 诊断或作答路径及 trace；不调用模型 |
| 诊断 | 句子、年级、上下文、need_hints | DiagnosisOutputV1 |
| 提示 | 诊断中的 hints 和请求偏好 | 空列表或 1、2、3 级提示 |
| 修改 | 诊断中的 corrections | 保留原意的候选修改；与原句相同需复核 |
| 答案分析 | 题目模式、审核标签和参考、学生答案、历史 | 确定性答案或 AnswerAnalysisV1 |
| 复核 | 原始输入与候选诊断/判分 | ReviewOutputV1/AnswerReviewV1 及最终可靠性门槛 |

生成阶段同时产出诊断、修改和提示，复核另用一次调用。普通诊断通常两次外部调用；标准选择和参考修改精确匹配不调用模型；非参考修改使用语义评分加独立复核。Prompt 版本见 prompts/CHANGELOG.md，schema 由 agents/models.py 生成并附入系统消息。

## 判分与保存规则

- 判断题用“是病句/不是病句”；类别选择题用统一类别；修改题 answer_type 为 text 或 修改题。模式不匹配、空白或非字符串答案返回 400。
- 已审核参考修改可精确通过；其他修改不要求逐字相同，但必须消除原语病、基本保留原意且无新语病。反对评分的复核不是“学生答错”。
- 任一不确定、低置信度或复核冲突返回 MODEL_LOW_CONFIDENCE，HTTP 200、success=false，提示人工复核，不保存成绩，也不更新画像。
- 通过结果的作答与关联诊断在同一事务保存；失败回滚。关联诊断以题库标签为依据，解释说明其来源，不伪装成新模型检测。旧表结构不变。
- 自由诊断 needs_review 时返回暂定结果和 needs_context，不存作通过结果。现有页面仍会展示暂定 has_error，必须连同解释及复核状态理解；未新增三态前端。
- 原有 category 字段因兼容保留，因此练习接口不是标签隐藏的盲测接口。正式评测直接从独立数据只向模型发送句子与必要上下文。
- Mock 只覆盖 demo.py 的固定开发样例；其他句子一律需要复核，不能用 Mock 候选集分数说明模型能力。

轨迹包含 request_id、模式、模型、Prompt 版本、阶段、状态、ISO 时间、耗时、外部调用次数和已报告 token 用量。不记录密钥、供应商原始错误正文或原始响应；学生数据仅通过受控结构化字段进入服务。

## 数据审核与三组实验

data/b_evaluation_candidates.json 是 AI 辅助编写的 80 条独立候选：八类各 8 条，另有 16 条正常句，其中 8 条病句包含多标签。全部 pending、is_active=false。data/b_development_regressions.json 为 17 条独立开发回归样例，不作为人工金标准。未修改 C 的 20 条候选题。

人工审核已完成，详见 docs/B_HUMAN_REVIEW_REPORT.md：全量审核档案为 data/b_evaluation_reviewed_full.json，正式集 data/b_evaluation_reviewed.json 包含 79 条 approved（61 条病句、18 条正常句），版本 b-reviewed-1.1，保留八类覆盖和 8 条多标签。b_eval_038 已淘汰，b_eval_043、b_eval_047 按用户确认改为正常句；原标注保留在 review.revisions。测试集不启用、不导入练习库。后续修订仍按审核清单保留人员、时间和依据，提升数据版本并重新运行实验。

开发性试跑不需要模型、不需要批准候选：

```powershell
python -X utf8 -m evaluation.run_b --group baseline --development --output evaluation/runs/dev_baseline.jsonl
python -X utf8 -m evaluation.run_b --group structured --development --output evaluation/runs/dev_structured.jsonl
python -X utf8 -m evaluation.run_b --group full --development --output evaluation/runs/dev_full.jsonl
```

这些命令默认 mock，80 条未覆盖候选会被拒判；这是对“不能用 Mock 冒充真实精度”的正确验证。baseline 与 structured 共享输出 Schema 以免引入不同抽取器；baseline 仅有普通诊断指令，无专用定义、提示策略和语义复核，仍保留公共结构校验。full 为结构化诊断加真实题库读取及提供的历史上下文，不是训练了新模型。

人工审核和本地模型配置完成后：

```powershell
python -X utf8 -m evaluation.run_b --group baseline --live --data data/b_evaluation_reviewed.json --output evaluation/runs/live_baseline.jsonl
python -X utf8 -m evaluation.run_b --group structured --live --data data/b_evaluation_reviewed.json --output evaluation/runs/live_structured.jsonl
python -X utf8 -m evaluation.run_b --group full --live --data data/b_evaluation_reviewed.json --context data/b_context_reviewed.json --output evaluation/runs/live_full.jsonl
```

full 的 context JSON 结构如下；questions 使用 C 题目完整结构，只允许 approved、is_active=true 且有人工审核元数据的独立工具题库。attempts 按旧到新排序，使用虚构用户场景。正式工具题库与测试集不得同题或近似；程序做二元片段 Jaccard≥0.45 的排除检查，仍需人工核对语义泄漏。

```json
{
  "questions": [],
  "attempts": [{"question_id": "外部工具题号", "category": "搭配不当", "is_correct": false}],
  "target_weak_categories": ["搭配不当"]
}
```

正式 full 不接受空工具题库。推荐沿用 C 的独立 recommend_next，标明提供的历史场景，不使用测试 gold 回写历史，不把推荐质量归因于 B。生产 API 继续沿用 D 的现有推荐行为，未替换算法。

每次运行保存 JSONL、summary.json 和 ratings.json。恢复使用相同参数加 --resume；重试失败/拒判另加 --retry-failed。数据、上下文、模型配置、代码或 Prompt 变化会拒绝恢复。已完成成功项不重跑；旧失败尝试保留，调用次数和已报告用量包含重试。新成功项的人工评分模板自动补充，保留已填写评分。

报告包括全请求成功率、拒判率、失败率、主类别准确率、八类 Macro-F1、多标签 micro-F1、耗时、调用次数和已报告 token 用量；仅接受结果的 C 指标另列，不作为整体成绩。保守检测分数将失败/拒判的病句计 FN、正常句计 FP，明确不是标准混淆矩阵。费用需按供应商实际账单和价格核算，未报告 token 不视为免费。

人工填写 ratings.json 的 effective、meaning_preserved 和 reviewer，再运行：

```powershell
python -X utf8 -m evaluation.score_b_ratings evaluation/runs/live_structured.jsonl evaluation/runs/live_structured.ratings.json
```

## 尚待真实验收

目前人工审核的正式测试集已就绪，真实服务尚未配置和验证，因此尚不能报告模型精度、有效修改率、真实延时或费用。本轮完成的是工程交付和数据审核；前端浏览器联调、服务商兼容性和真实质量实验分别需要实际运行后记录。组员接续事项见 ../docs/B_HANDOFF.md。
