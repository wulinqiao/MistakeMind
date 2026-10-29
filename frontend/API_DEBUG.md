# 前端联调记录

联调用户：`user_001`  
前端：`http://127.0.0.1:5173`  
后端：`http://127.0.0.1:8000`（Vite 代理 `/api`）  
规范：`TEAM_ASSIGNMENT_AND_API_SPEC.md`

## 环境

| 项 | 值 |
| --- | --- |
| 前端命令 | `npm run dev`（`frontend/`） |
| 后端命令 | `uvicorn backend.main:app --reload` |
| LLM | 未配置 `LLM_API_KEY` 时诊断走后端 Mock |
| 日期 | 2026-10-29 |

## 接口核对

| 接口 | 前端入口 | 请求要点 | 结果 |
| --- | --- | --- | --- |
| `POST /api/diagnose` | DiagnoseView / PracticeView 提示与讲解 | `sentence`、`user_id`、`grade`、`optional_context`、`need_hints` | 展示 `error_types` / `error_span` / `explanation` / `corrections` / `hints` |
| `GET /api/questions` | PracticeView | `mode` / `difficulty` / `category` / `count` / `user_id` | 只展示题面与选项，不展示答案字段 |
| `POST /api/submit-answer` | PracticeView | `answer_type`：`choice` 或 `text`；带 `hint_level_used`、`attempt_number` | 展示反馈、掌握度、推荐题 ID |
| `GET /api/history/{user_id}` | HistoryView | `page` / `page_size` / `category` | 列表 + 分页 |
| `GET /api/profile/{user_id}` | ProfileView | path 中 `user_id` | 统计、推荐类型、掌握度条 |

## 异常路径

| 场景 | 期望错误码 | 前端表现 |
| --- | --- | --- |
| 诊断空句子 | `VALIDATION_ERROR` | `ErrorAlert` |
| 后端未启动 | `NETWORK_ERROR` | 「无法连接后端…」 |
| 无匹配题目 | `QUESTION_NOT_FOUND` | 「暂无符合条件的题目」 |
| 用户尚无数据 | `USER_NOT_FOUND`（若后端返回） | 引导先答题/诊断 |
| 低置信度诊断 | `review_status` / 低 `confidence` | DiagnoseView 顶部提示「仅供参考」 |

## 已知依赖（非 A 范围）

- 推荐下一题只能展示 `recommended_question_id`；规范未提供按 ID 拉题接口，实际下一题仍走 `GET /api/questions` + `user_id`。
- 题库为空时练习页无法演示，需成员 C 导入题目、成员 D 完成库初始化。
- 真实 LLM 诊断质量由成员 B 负责；前端只消费结构化 JSON。

## 演示建议顺序

1. 诊断示例句 → 展开三级提示  
2. 首页筛选进练习 → 提交 → 看反馈与画像变化  
3. 历史页按类型筛选  
4. （可选）关掉后端演示 `NETWORK_ERROR`
