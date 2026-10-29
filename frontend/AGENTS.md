# MistakeMind 前端 AI 上下文（成员 A）

后续让 AI 做前端时，先读本文件，并以仓库根目录的 `TEAM_ASSIGNMENT_AND_API_SPEC.md`、`README.md`、`docs/api.md` 为接口真源。字段以规范为准，禁止猜测未记录字段。

## 一句话目标

面向中学生的病句诊断 / 练习 / 历史 / 画像前端。只消费后端 `/api` 的结构化 JSON，不调 LLM、不写死推荐、不自造病句类型。

## 技术栈

- Vue 3（`<script setup>`）+ Vue Router + Vite
- Element Plus 可用，现有视觉以 `src/style.css` 的 `neu-*` 新拟态类为主
- 后端：`http://127.0.0.1:8000`（无 `LLM_API_KEY` 时走 Mock，可联调）

## 目录与职责

```text
frontend/src/
├── App.vue                 # 壳：顶栏、导航、router-view
├── main.js / router/       # 入口与路由
├── style.css               # 全局 neu-* 样式
├── views/                  # 一页一个文件
│   ├── HomeView.vue        # 训练首页：选难度/类型/模式 → 进入练习
│   ├── PracticeView.vue    # 答题（判断/选择/修改三种题型共用）
│   ├── DiagnoseView.vue    # 句子诊断 + 结果
│   ├── HistoryView.vue     # 历史记录
│   └── ProfileView.vue     # 学习画像
└── components/             # 多页复用
    ├── DiagnosisCard.vue   # 类型 / 错误位置 / 解释 / 修改
    ├── HintPanel.vue       # 分层提示（level 1→2→3）
    └── ErrorAlert.vue      # 统一错误码提示
```

建议另建 `src/api/`：统一请求、解析 `{ success, data, error, meta }`，把 `error.code` 映射给 `ErrorAlert`。

## 页面 ↔ API

| 页面/组件 | API | 要点 |
| --- | --- | --- |
| DiagnoseView + DiagnosisCard + HintPanel | `POST /api/diagnose` | 展示 `error_types` / `error_span` / `explanation` / `corrections` / `hints` |
| PracticeView | `GET /api/questions` + `POST /api/submit-answer` | 拉题不得含答案字段；按 `mode` 分支作答 |
| HistoryView | `GET /api/history/{user_id}` | 分页、可按 `category` 筛 |
| ProfileView | `GET /api/profile/{user_id}` | `category_stats`、`recommended_categories` 只展示后端结果 |
| HomeView | （路由跳转为主） | 把筛选条件带进 Practice，不在前端写推荐算法 |
| ErrorAlert | 全部失败路径 | 使用规范错误码文案，不吞错 |

## 必须遵守的约定

- 响应外层：`success` / `request_id` / `data` / `error` / `meta`
- 病句类型枚举（勿自造同义词）：成分残缺、成分赘余、搭配不当、语序不当、结构混乱、表意不明、不合逻辑、关联词使用不当、其他
- 难度：小学高年级 / 初中 / 高中 / 综合
- 练习模式：判断题 / 选择题 / 修改题
- 空值用 `null`；时间 ISO 8601；`user_id` 未登录可用 `anonymous`
- 训练题接口禁止提前展示 `reference_corrections`、`explanation` 等答案字段
- 推荐与掌握度只渲染接口返回值，前端不算

## 推荐实现顺序

1. `api/` 客户端 + `ErrorAlert` 接入
2. `App.vue` 壳与路由可用
3. `DiagnoseView`（第一轮 P0：提交一句 → 结构化诊断 → 展示）
4. `PracticeView`（三题型共用一页，`mode` 分支）
5. `HomeView` 入口筛选
6. `HistoryView` → `ProfileView`

## 交付物（成员 A）

- 本目录 `README.md`（运行与联调说明）
- Mock 数据 / 联调记录
- 页面截图或录屏
- ≥5 条交互测试用例

## 禁止事项

- 直接调用 LLM 或把模型原始响应当 UI 数据
- 修改数据库字段、后端 Schema、病句标签名
- 在前端硬编码推荐逻辑或发明 API 字段
- 字段变更不先改 `TEAM_ASSIGNMENT_AND_API_SPEC.md`

## 给 AI 的默认工作方式

1. 改接口相关代码前先核对规范文档字段名与类型
2. 优先复用 `components/`，Views 只做编排与状态
3. 先 Mock / 本地后端联调跑通，再美化
4. 只改任务需要的文件；不擅自大范围重构或新增无关文档
5. 分支约定：`feature/frontend`；提交前缀如 `feat:` / `fix:` / `docs:`
