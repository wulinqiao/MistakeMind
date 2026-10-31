# MistakeMind API

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

未配置 `LLM_API_KEY` 时诊断使用确定性 Mock，便于前后端联调；配置 DeepSeek 或其他 OpenAI 兼容服务的密钥和地址后，诊断会请求 `/chat/completions` 并校验结构化 JSON。模型超时、HTTP 错误和非法 JSON 分别映射到统一错误，不会把原始模型响应返回给前端。

## 错误码

`VALIDATION_ERROR`（400）、`QUESTION_NOT_FOUND`（404）、`USER_NOT_FOUND`（404）、`MODEL_TIMEOUT`（504）、`MODEL_INVALID_JSON`（502）、`MODEL_LOW_CONFIDENCE`（200）、`DATABASE_ERROR`（500）、`INTERNAL_ERROR`（500）。

