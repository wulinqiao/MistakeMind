# MistakeMind API

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
