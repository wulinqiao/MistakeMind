# MistakeMind Frontend（成员 A）

Vue 3 + Vite 训练端。视觉为 Neumorphism（`neu-*` / `#e0e5ec`）。接口字段以仓库根目录 `TEAM_ASSIGNMENT_AND_API_SPEC.md` 为准。

## v1.2 集成更新

推荐按钮精确获取推荐题；提交后直接展示本次保存的关联解析；分类题面不显示 category；历史页支持只看错题、展开解析、再练此题；画像展示样本不足提示和平滑表现及每日趋势。诊断待复核时明确显示“暂无法确认”。顶部说明当前运行模式和演示题库状态。

在项目根目录执行 `./start.ps1 -Demo` 可通过同一个地址访问完整应用。开发仍可使用下方 Vite 双进程方式。前端构建使用已提交的 package-lock.json 和 `npm ci`。

## 启动

```powershell
# 终端 1：后端（无 LLM_API_KEY 时走 Mock）
cd ..
uvicorn backend.main:app --reload

# 终端 2：前端
cd frontend
npm install
npm run dev
```

本地地址：`http://127.0.0.1:5173`。开发服务器将 `/api`、`/health` 代理到 `http://127.0.0.1:8000`。

默认联调用户：`user_001`（见 `src/constants.js`）。

## 页面

| 路由 | 说明 | 主要 API |
| --- | --- | --- |
| `/` | 训练首页，筛选后进入答题 | 路由跳转 |
| `/practice` | 判断 / 选择 / 修改题 + 分层提示 + 提交反馈 | `GET /api/questions`、`POST /api/submit-answer`、`POST /api/diagnose`（提示/讲解） |
| `/diagnose` | 句子诊断 + 分层提示 | `POST /api/diagnose` |
| `/history` | 历史记录（类型筛选、分页） | `GET /api/history/{user_id}` |
| `/profile` | 学习画像与掌握度条形图 | `GET /api/profile/{user_id}` |

## Mock 数据

`mock/` 目录存放与规范一致的成功/失败示例 JSON，用于对照字段和课堂演示，**不**在前端写死推荐逻辑：

- `diagnose.success.json` / `diagnose.validation_error.json`
- `questions.success.json`
- `submit-answer.success.json`
- `history.success.json`
- `profile.success.json`

联调时请直接打真实后端；Mock 文件仅作契约样例。

## 交互测试用例（≥5）

| # | 步骤 | 期望 |
| ---: | --- | --- |
| 1 | 打开「句子诊断」，保留示例句，点「开始诊断」 | 展示病句类型、错误位置、解释、修改建议；可逐级展开提示 |
| 2 | 清空句子后点「开始诊断」 | `ErrorAlert` 显示 `VALIDATION_ERROR` |
| 3 | 首页选「判断题 / 初中 / 成分残缺」→「开始答题」→ 选择「是病句」→ 提交 | 出现对错反馈；历史页能查到该次作答 |
| 4 | 答题页点「加载分层提示」→「查看提示」→「下一级提示」→ 再提交 | 请求带上 `hint_level_used`；反馈正常 |
| 5 | 停止后端后任意页发起请求 | `NETWORK_ERROR` 提示「无法连接后端」 |
| 6 | 打开「学习画像」 | 显示总正确率、推荐类型芯片、掌握度条；点击类型进入对应练习 |

更细的联调记录见 `API_DEBUG.md`。

## 交付清单（成员 A）

- [x] 页面与 API 联调代码（`src/`）
- [x] `README.md`（本文件）
- [x] API Mock 数据（`mock/`）
- [x] 前端联调记录（`API_DEBUG.md`）
- [x] ≥5 条交互测试用例（见上表）
- [x] 页面截图与浏览器验收记录（见 ../docs/BROWSER_VERIFICATION.md）
- [x] 课堂演示讲解稿（见 ../deliverables/课堂演示脚本.md，仍需成员彩排）
- [ ] 在 `feature/frontend` 分支开 PR（含改动说明与是否需他人同步）

## 禁止事项

- 不直接调用 LLM
- 不自造病句类型 / 难度 / 模式枚举
- 不修改数据库字段或后端 Schema
- 不在前端写死推荐算法（只渲染 `recommended_categories` / `recommended_question_id`）
