# MistakeMind API

## v1.2 学习闭环

当前版本为 v1.2；下方 v1.1 节保留为历史兼容说明。

| 接口 | 新增行为 |
| --- | --- |
| GET /api/status | 返回 agent_mode、active_questions、demo_dataset、api_version，不包含凭据 |
| GET /api/questions/{question_id} | 返回 data.question，精确获取已启用的推荐题，未启用返回 404 |
| GET /api/questions | 未指定 category 且提供 user_id 时按画像推荐；mode、difficulty 条件继续生效 |
| POST /api/submit-answer | 增加 diagnosis、trace；返回保存的同一诊断及持久化、推荐过程 |
| GET /api/history/{user_id} | 新增 wrong_only 布尔筛选，items 新增 original_sentence、diagnosis |
| GET /api/profile/{user_id} | 增加近期平滑表现、样本数保护、错误次数及每日趋势 |

题面中的 category 字段保留为 null，不再提前泄露分类答案；参考修改和解析仅在作答后返回。推荐优先选择薄弱类别，再避开该类别近期题；同类题量不足时允许复练。推荐保持本次题型和难度，前端用精确取题接口打开推荐 ID。

profile.category_stats 保留累计 accuracy。mastery 使用最近 50 次作答中的分类正确次数 c 和题数 n 计算 (c+1)/(n+2)，sample_sufficient 表示 n>=3；不足时 priority=insufficient。priority_score 沿用 C 的平滑错误率与探索奖励。trend 为最近 14 个有作答日期的题数和正确率。mastery_update.before/after 为兼容旧客户端，仍表示累计分类正确率。

生产构建后可直接通过 FastAPI 同源访问首页及 /practice、/diagnose、/history、/profile；刷新这些页面可返回前端入口。Vite 代理仅用于开发。

## v1.1 B 模块

所有旧路径和旧请求兼容，meta.version 为 v1.1；诊断增加 needs_context=false。配置与运行参见 ../agents/README.md。
grade、optional_context、need_hints 参与诊断。模型返回不直接外传，先做结构校验与复核。
MODEL_UNAVAILABLE (502) 表示配置/鉴权/服务不可用；非法 JSON (502)、超时 (504) 保持原错误码。
自由诊断 needs_review 仍返回 success=true，解释为暂定结论且不入库；判题 needs_review 返回 HTTP 200、success=false、data=null、MODEL_LOW_CONFIDENCE，不写成绩。
判断题 options 固定为两项；类别选择题 options 为统一标签，参考修改不再作为选项。category 字段仍兼容保留。
作答与关联诊断原子保存；历史 error_types 来自关联诊断。不变更数据库表结构。

## 启动

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn backend.main:app --reload
```

也可以构建容器：`docker build -t mistakemind . && docker run --rm -p 8000:8000 mistakemind`。
服务健康检查为 `GET /health`，OpenAPI 文档为 `/docs`。

## 统一响应

每个 `/api` 接口返回 `success`、`request_id`、`data`、`error` 和 `meta`。请求可通过 `X-Request-ID` 传入调用链 ID；未传入时由服务生成。

## 接口示例

```bash
curl -X POST http://localhost:8000/api/diagnose -H 'Content-Type: application/json' \
  -d '{"sentence":"通过开展此次活动，使同学们提高了环保意识。","user_id":"user_001","need_hints":true}'
curl 'http://localhost:8000/api/questions?count=1'
curl -X POST http://localhost:8000/api/submit-answer -H 'Content-Type: application/json' \
  -d '{"user_id":"user_001","question_id":"q_001","answer":"是病句","answer_type":"choice"}'
curl 'http://localhost:8000/api/history/user_001'
curl 'http://localhost:8000/api/profile/user_001'
```

未配置 `LLM_API_KEY` 时使用明确标识的固定 Mock；未知句提示复核。配置 OpenAI 兼容服务的密钥、基础地址和模型名后即可使用真实适配器，无需修改源码。模型超时、非法 JSON 和低置信度分别映射到统一错误/复核状态，不会把原始模型响应返回给前端。

## 错误码

`VALIDATION_ERROR`（400）、`QUESTION_NOT_FOUND`（404）、`USER_NOT_FOUND`（404）、`MODEL_TIMEOUT`（504）、`MODEL_INVALID_JSON`（502）、`MODEL_LOW_CONFIDENCE`（200）、`DATABASE_ERROR`（500）、`INTERNAL_ERROR`（500）。


DeepSeek 配置示例：LLM_BASE_URL=https://api.deepseek.com、LLM_MODEL=deepseek-chat。未配置密钥时使用 Mock；配置密钥后由 agents/client.py 通过 OpenAI 兼容的 /chat/completions 接口调用模型。
