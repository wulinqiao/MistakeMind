# MistakeMind 团队分工与统一接口规范

本文档是 MistakeMind 的开发协作基线。所有成员在编写前端、后端、Agent、题库和评测代码时，必须以本文档中的接口、字段和状态定义为准。

## v1.1 B 模块兼容增补（2026-10-30）

- 路径和旧字段不变；meta.version=v1.1。DiagnosisResult 增加 needs_context（默认 false），grade、optional_context、need_hints 传入 Agent。
- auto 模式有密钥时使用真实 Chat Completions，否则使用明确标识的固定演示样例；live 失败不回退 Mock。无模型支持的未知演示句需要复核，不宣称无病句。
- MODEL_UNAVAILABLE：HTTP 502，模型配置、鉴权、限流或服务不可用；MODEL_TIMEOUT 504、MODEL_INVALID_JSON 502 保持原约定。
- 自由诊断待复核时 success=true、review_status=needs_review，返回解释但不存为通过结果。学生作答待复核时 HTTP 200、success=false、data=null、error.code=MODEL_LOW_CONFIDENCE，不写成绩或画像。
- 判断题固定返回“是病句/不是病句”选项；类别选择题返回统一标签选项，references 不作为选项公开。category 字段因旧契约兼容继续保留，正式盲测不能依靠前端练习接口隔离标签。
- 修改题接受参考修改及经语义复核的其他合理修改。作答和诊断在同一事务保存；只有 passed 结果可以计分。
- 单次模型调用默认 20 秒，业务总预算 60 秒/4 次请求；网络/429/5xx 最多一次重试，格式最多一次修复。置信度阈值 0.7 为可配自评门槛，不是校准概率。
- 内部类型为 DiagnosisInputV1、DiagnosisOutputV1、ReviewOutputV1、AnswerAnalysisV1、AnswerReviewV1；类型定义见 agents/models.py。trace 使用 ISO 8601 时间，附模式、Prompt 版本、模型与用量，不含密钥或原始响应。
- 正式评测仅使用人工 approved 测试样本；候选开发结果必须标记非正式。新数据不自动审核、启用或导入 C 题库。

## 1. 协作原则

1. 先冻结 Schema，再开发具体模块。
2. 所有跨模块数据使用 JSON，不直接依赖自然语言文本。
3. 所有接口使用统一响应格式和统一错误码。
4. Agent 可以内部迭代，但对外输出必须符合 Schema。
5. 任何接口字段变更必须先更新本文档，再提交代码。
6. 每个模块必须提供一个最小可运行示例和一条失败案例。
7. 前端不得猜测字段含义；后端不得返回未记录的字段。

## 2. 成员分工

### A：前端与学生训练流程

负责目录：`frontend/`

负责内容：

- 训练首页和题目展示；
- 判断题、选择题、自主修改题交互；
- 分层提示和诊断结果页面；
- 历史记录页面；
- 学习画像和统计图表；
- API 联调和前端异常提示；
- 课堂展示流程和演示数据准备。

不得负责：

- 直接调用 LLM；
- 自行定义病句类型；
- 修改数据库字段；
- 在前端写死推荐逻辑。

交付物：

- `frontend/README.md`；
- 页面截图或录屏；
- API Mock 数据；
- 前端联调记录；
- 至少 5 条交互测试用例。

### B：Agent、Prompt 与诊断逻辑

负责目录：`agents/`、`prompts/`

负责内容：

- 任务路由 Agent；
- 病句诊断 Agent；
- 学生答案分析 Agent；
- 分层提示 Agent；
- 最小修改 Agent；
- 复核 Agent；
- LLM Prompt 和结构化输出；
- 模型超时、空结果和非法 JSON 的处理。

不得负责：

- 直接修改前端页面；
- 自行改变 API 路径；
- 将未经复核的模型结果直接写入数据库；
- 在 Prompt 中使用未定义的字段名。

交付物：

- 每个 Agent 的输入输出 Schema；
- Prompt 版本号和变更说明；
- 正常案例、边界案例和失败案例；
- Agent 调用日志示例；
- 单元测试或固定回归样例。

### C：题库、知识库、推荐与评测

负责目录：`data/`、`evaluation/`、`scripts/`

负责内容：

- 题目 JSON 数据；
- 病句类型标签和知识点标签；
- 参考修改和可接受修改；
- 难度标注；
- 规则知识库；
- 相似题和推荐逻辑；
- 测试集、Baseline 和对照实验；
- 评测报告和失败案例统计。

不得负责：

- 修改后端 API 字段；
- 在题库中混用不同标签名称；
- 直接把未经审核的大模型生成题目作为标准答案。

交付物：

- 至少 60—100 道人工审核题目；
- 每道题的完整标签；
- 题库导入脚本；
- 评测脚本；
- 实验结果表格；
- 题目来源和许可说明。

### D：后端、数据库、工具调用与部署

负责目录：`backend/`、`schemas/`、`db/`

负责内容：

- FastAPI 服务；
- Pydantic Schema；
- SQLite 数据库；
- Agent 工具接口；
- 学生状态读写；
- 推荐结果持久化；
- 日志、异常处理和接口文档；
- 本地启动和部署说明。

不得负责：

- 私自修改前端需要的字段名称；
- 将 API Key 写入代码或提交到 Git；
- 把模型原始响应直接暴露给前端；
- 绕过 Schema 校验写入数据库。

交付物：

- API 实现；
- `schemas/` 中的统一模型；
- 数据库初始化脚本；
- `docs/api.md`；
- `.env.example`；
- 接口测试和启动说明。

## 3. 统一技术约定

### 3.1 基础约定

- API 前缀：`/api`
- 数据格式：`application/json`
- 字符编码：UTF-8
- 时间格式：ISO 8601，例如 `2026-10-28T12:30:00+08:00`
- 用户标识：字符串 `user_id`
- 题目标识：字符串 `question_id`
- 诊断标识：字符串 `diagnosis_id`
- 布尔值：JSON `true` / `false`
- 空值：JSON `null`，不得使用空字符串代替

### 3.2 病句类型枚举

所有模块必须使用以下中文标签，不得自造同义词：

```text
成分残缺
成分赘余
搭配不当
语序不当
结构混乱
表意不明
不合逻辑
关联词使用不当
其他
```

### 3.3 难度枚举

```text
小学高年级
初中
高中
综合
```

### 3.4 练习模式枚举

```text
判断题
选择题
修改题
```

## 4. 统一响应格式

所有 API 都必须返回以下外层结构：

```json
{
  "success": true,
  "request_id": "req_20261028_000001",
  "data": {},
  "error": null,
  "meta": {
    "timestamp": "2026-10-28T12:30:00+08:00",
    "version": "v1"
  }
}
```

成功时：

- `success` 为 `true`；
- `data` 放业务结果；
- `error` 必须为 `null`。

失败时：

```json
{
  "success": false,
  "request_id": "req_20261028_000002",
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "sentence 不能为空",
    "details": {
      "field": "sentence"
    }
  },
  "meta": {
    "timestamp": "2026-10-28T12:31:00+08:00",
    "version": "v1"
  }
}
```

## 5. API 接口规范

### 5.1 `POST /api/diagnose`

用途：诊断一条句子，返回病句类型、错误位置、解释和修改方案。

请求：

```json
{
  "sentence": "通过开展此次活动，使同学们提高了环保意识。",
  "user_id": "user_001",
  "grade": "初中",
  "optional_context": null,
  "need_hints": true
}
```

字段要求：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `sentence` | string | 是 | 待诊断句子，长度 1—500 |
| `user_id` | string | 否 | 未登录时使用 `anonymous` |
| `grade` | enum | 否 | 用于控制解释难度 |
| `optional_context` | string/null | 否 | 学生补充说明 |
| `need_hints` | boolean | 否 | 是否返回分层提示 |

响应 `data`：

```json
{
  "diagnosis_id": "diag_001",
  "original_sentence": "通过开展此次活动，使同学们提高了环保意识。",
  "has_error": true,
  "error_types": ["结构混乱", "成分残缺"],
  "error_span": "通过……使……",
  "explanation": "“通过”和“使”同时使用，造成句子结构混乱。",
  "corrections": [
    {
      "text": "通过开展此次活动，同学们提高了环保意识。",
      "kind": "最小修改",
      "reason": "删除“使”，补出明确主语"
    },
    {
      "text": "开展此次活动，使同学们提高了环保意识。",
      "kind": "另一种合理修改",
      "reason": "删除“通过”"
    }
  ],
  "hints": [
    {
      "level": 1,
      "text": "请检查句子的主语是否明确。"
    },
    {
      "level": 2,
      "text": "注意“通过……使……”这一结构。"
    },
    {
      "level": 3,
      "text": "可以删除“通过”或删除“使”。"
    }
  ],
  "confidence": 0.94,
  "review_status": "passed"
}
```

### 5.2 `GET /api/questions`

用途：获取训练题。

请求参数：

```text
category：可选，病句类型
difficulty：可选，难度
mode：可选，判断题/选择题/修改题
count：可选，默认 1，最大 10
user_id：可选，用于个性化避让和推荐
```

响应 `data`：

```json
{
  "questions": [
    {
      "question_id": "q_001",
      "sentence": "通过这次活动，使我受到了很大的教育。",
      "mode": "判断题",
      "difficulty": "初中",
      "category": "成分残缺",
      "options": ["是病句", "不是病句"]
    }
  ]
}
```

注意：训练题接口不得返回 `reference_corrections`、`explanation` 等答案字段，防止前端提前泄露答案。

### 5.3 `POST /api/submit-answer`

用途：提交学生答案，判断结果并生成反馈。

请求：

```json
{
  "user_id": "user_001",
  "question_id": "q_001",
  "answer": "是病句",
  "answer_type": "choice",
  "hint_level_used": 1,
  "attempt_number": 1
}
```

响应 `data`：

```json
{
  "attempt_id": "attempt_001",
  "is_correct": true,
  "feedback_level": "basic",
  "feedback": "判断正确。该句属于成分残缺。",
  "next_action": "show_explanation",
  "recommended_question_id": "q_017",
  "mastery_update": {
    "category": "成分残缺",
    "before": 0.42,
    "after": 0.50
  }
}
```

### 5.4 `GET /api/history/{user_id}`

用途：查询历史答题记录。

请求参数：

```text
page：页码，默认 1
page_size：每页数量，默认 20，最大 100
category：可选，按病句类型筛选
```

响应 `data`：

```json
{
  "items": [
    {
      "attempt_id": "attempt_001",
      "question_id": "q_001",
      "answer": "是病句",
      "is_correct": true,
      "error_types": ["成分残缺"],
      "created_at": "2026-10-28T12:30:00+08:00"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1
}
```

### 5.5 `GET /api/profile/{user_id}`

用途：获取学生错误画像和推荐知识点。

响应 `data`：

```json
{
  "user_id": "user_001",
  "total_attempts": 20,
  "overall_accuracy": 0.75,
  "category_stats": [
    {
      "category": "搭配不当",
      "attempts": 8,
      "correct": 4,
      "accuracy": 0.50,
      "mastery": 0.42,
      "priority": "high"
    }
  ],
  "recommended_categories": ["搭配不当", "成分残缺"],
  "next_review_at": "2026-10-30T19:00:00+08:00"
}
```

## 6. Agent 内部接口

Agent 之间使用统一的上下文对象：

```json
{
  "request_id": "req_20261028_000001",
  "user_id": "user_001",
  "task": "diagnose_and_practice",
  "grade": "初中",
  "sentence": "通过开展此次活动，使同学们提高了环保意识。",
  "student_answer": null,
  "question_id": null,
  "history_summary": [],
  "current_result": null,
  "trace": []
}
```

每个 Agent 必须遵循：

1. 读取上下文，不修改无关字段；
2. 只负责自己的字段；
3. 将调用结果写入 `current_result`；
4. 将开始、成功或失败事件追加到 `trace`；
5. 失败时返回明确错误，不得静默吞错。

标准轨迹事件：

```json
{
  "agent": "diagnosis_agent",
  "action": "llm_call",
  "status": "success",
  "started_at": "2026-10-28T12:30:00+08:00",
  "duration_ms": 842,
  "input_schema": "DiagnosisInputV1",
  "output_schema": "DiagnosisOutputV1"
}
```

## 7. 数据库表结构

### `users`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | 用户 ID |
| `nickname` | TEXT | 昵称 |
| `grade` | TEXT | 年级 |
| `created_at` | TEXT | 创建时间 |

### `questions`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | 题目 ID |
| `sentence` | TEXT | 原句 |
| `mode` | TEXT | 题目模式 |
| `category` | TEXT | 主错误类型 |
| `error_types_json` | TEXT | 错误类型数组 |
| `references_json` | TEXT | 参考修改数组 |
| `difficulty` | TEXT | 难度 |
| `source` | TEXT | 来源 |
| `is_active` | INTEGER | 是否启用 |

### `attempts`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | 作答记录 ID |
| `user_id` | TEXT | 用户 ID |
| `question_id` | TEXT | 题目 ID |
| `answer_json` | TEXT | 学生答案 |
| `is_correct` | INTEGER | 是否正确 |
| `hint_level_used` | INTEGER | 使用提示等级 |
| `attempt_number` | INTEGER | 第几次作答 |
| `created_at` | TEXT | 作答时间 |

### `diagnoses`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | TEXT PRIMARY KEY | 诊断 ID |
| `attempt_id` | TEXT | 作答记录 ID，可为空 |
| `original_sentence` | TEXT | 原句 |
| `has_error` | INTEGER | 是否有病句 |
| `error_types_json` | TEXT | 错误类型数组 |
| `error_span` | TEXT | 错误片段 |
| `explanation` | TEXT | 解释 |
| `corrections_json` | TEXT | 修改建议 |
| `review_status` | TEXT | 复核状态 |
| `created_at` | TEXT | 创建时间 |

## 8. 统一错误码

| 错误码 | HTTP | 使用场景 |
| --- | ---: | --- |
| `VALIDATION_ERROR` | 400 | 请求字段缺失或格式错误 |
| `QUESTION_NOT_FOUND` | 404 | 题目不存在或已下线 |
| `USER_NOT_FOUND` | 404 | 用户不存在 |
| `MODEL_TIMEOUT` | 504 | 模型请求超时 |
| `MODEL_INVALID_JSON` | 502 | 模型返回无法解析 |
| `MODEL_LOW_CONFIDENCE` | 200 | 模型置信度低，需要人工或二次确认 |
| `DATABASE_ERROR` | 500 | 数据库读写失败 |
| `INTERNAL_ERROR` | 500 | 未分类的服务端错误 |

## 9. Git 分支与提交规范

分支：

```text
main                  # 可展示、可运行版本
feature/frontend      # A
feature/agents        # B
feature/data-eval     # C
feature/backend       # D
```

提交信息格式：

```text
feat: add diagnosis endpoint
fix: handle invalid model json
data: add category labels
test: add diagnosis regression cases
docs: update api contract
refactor: simplify agent context
```

Pull Request 必须包含：

- 改动目的；
- 修改文件；
- 接口是否变化；
- 测试命令和结果；
- 页面截图或 API 示例；
- 是否需要其他成员同步修改。

## 10. 联调顺序

### 第一步：D 冻结 Schema 和空接口

D 先提供：

- Pydantic 模型；
- FastAPI 路由；
- Mock 响应；
- SQLite 初始化脚本。

此时 A、B、C 可以并行开发，不等待真实 LLM。

### 第二步：A 使用 Mock 完成页面

A 只根据本文档中的请求和响应字段开发，不直接依赖 B 的模型实现。

### 第三步：B 接入 Agent

B 将 Mock 逻辑替换为真实 Agent，保证响应外层格式不变。

### 第四步：C 接入题库和评测

C 提供题目导入脚本和固定测试集，D 负责导入接口，B 负责诊断，A 负责展示。

### 第五步：全链路验收

使用以下完整流程：

```text
获取题目
→ 提交学生答案
→ 诊断答案
→ 写入历史
→ 更新学生画像
→ 推荐下一题
→ 前端展示结果
```

## 11. 接口变更流程

任何字段变化必须按以下顺序处理：

1. 在本文件中提交接口变更说明；
2. 增加版本号，例如 `v1` → `v1.1`；
3. D 更新 Pydantic Schema 和 API 文档；
4. A 更新前端调用和页面；
5. B 更新 Agent 输出映射；
6. C 更新评测脚本或题库导入；
7. 使用至少一条旧数据进行兼容性测试；
8. 在 PR 中明确写出迁移影响。

禁止直接删除已有字段。字段废弃时先保留并标记 deprecated，至少经过一次完整演示后再删除。

## 12. 联调验收标准

### P0 必须通过

- `POST /api/diagnose` 能返回合法 JSON；
- 前端能展示病句类型、错误位置、解释和修改建议；
- 学生答案能写入数据库；
- 历史记录可以查询；
- 推荐结果来自学生实际薄弱类型；
- 模型超时和非法 JSON 不会导致服务崩溃；
- Agent 轨迹能够展示至少一次完整调用链。

### P1 建议通过

- 支持分层提示；
- 支持多个合理修改；
- 支持学习画像图表；
- 支持错误类型筛选；
- 支持评测结果导出；
- 支持匿名用户训练。

## 13. 每周协作检查表

每周结束前，所有成员在 PR 或项目看板中更新：

- 本周完成的功能；
- 实际修改的文件；
- 新增或修改的接口；
- 已通过的测试；
- 当前阻塞；
- 下周需要其他成员配合的事项。

每位成员都必须准备一个自己负责模块的 60—90 秒讲解，用于最终课堂展示。

## 14. 第一轮开发任务

第一轮只做接口和最小闭环，不追求界面完整：

- D：完成 `schemas/`、`POST /api/diagnose` 空接口、数据库初始化和统一响应格式；
- B：完成 `DiagnosisInputV1`、`DiagnosisOutputV1`、诊断 Prompt 和三个固定回归案例；
- C：准备 20 道带完整标签的题目和导入脚本；
- A：使用 Mock 接口完成诊断结果页面和答题提交页面。

第一轮验收标准是：从前端提交一句话，到后端返回结构化诊断，再到页面展示结果，能够完整跑通。

