# MistakeMind C 模块：从零运行与协作指南

## 本次提交的范围
仅负责 C：八类语病候选题、题库校验、审核后导入、个性化推荐原型、离线评测与单元测试。
验证修复还涉及旧导入入口 scripts/import_questions.py 的审核保护，以及 backend/main.py 的参数校验错误序列化；schemas/ 和 db/ 保持不变。实际验证记录见 [C_VERIFICATION_REPORT.md](C_VERIFICATION_REPORT.md)。
**20 道题全部为项目组自编的待人工审核样本，不代表已通过教学审核，不得直接作为正式标准答案。**
正常句 4 道，使用 category="其他"、error_types=[]、has_error=false。
当前所有候选题 is_active=false，所以正式 GET /api/questions 仍然不会显示这些题。

## Windows / VS Code：将远程 C 模块取回本地
你本地已经克隆了 wulinqiao/MistakeMind，且在 feature/data-eval 分支。
在 VS Code 中另开一个 PowerShell 终端（保留正在运行的 uvicorn 终端）：

    cd D:\GitHubProjects\MistakeMind
    git status --short
    git branch --show-current
    git remote -v

确认 status 没有列出未提交文件、当前分支为 feature/data-eval。
原来的 origin 应继续指向 wulinqiao/MistakeMind。只在没有 fork 远端时添加：

    git remote add fork https://github.com/zsk-67/MistakeMind.git

如果 fork 已存在，先运行 git remote get-url fork，确认它指向 zsk-67/MistakeMind；不要直接跳过地址检查。
确认后执行：

    git fetch fork
    git switch feature/data-eval
    git merge --ff-only fork/feature/data-eval

若本地有尚未提交的改动，先用 git status 检查，勿强行覆盖。
如果 merge --ff-only 失败，请停止并检查分支差异，不要 force push。
这里的 merge 只把远程 feature/data-eval 更新到当前同名本地分支，不会切换或修改 main，也不会向 GitHub 推送。

## 依赖
已在项目根目录创建并激活 .venv 后：

    python -m pip install -r requirements.txt

## 第 1 个实验：检查题库
    python -m scripts.validate_c_questions data/questions.json

## 第 2 个实验：推荐原型（只用模拟作答，不写数据库）
    python -m scripts.demo_c

## 第 3 个实验：查看可导入题目
    python -m scripts.import_c_questions data/questions.json --dry-run

待项目组逐题复核后，将选定题目设为 review_status="approved" 且 is_active=true，
然后才可用下面的正式导入命令：

    python -m scripts.import_c_questions data/questions.json

注意：导入命令使用 D 的数据库接口并操作数据库；正式操作前先备份数据库，
并确认题目参考修改和所属类别均已审核。
旧命令 python -m scripts.import_questions data/questions.json 也会对含 C 元数据的题库执行同样校验。
任意题含 review_status、has_error、explanation、error_span 或 knowledge_tags 时，整批题必须符合 C 格式；误删 review_status 会被拒绝。
仅含旧入口原有字段的题库仍兼容旧格式。审核保护不是对任意手动改写数据的权限控制。

## 第 4 个实验：计算离线评测指标（示例数据，不是模型效果）
    python -m evaluation.metrics evaluation/example_gold.json evaluation/example_pred.json

## 第 5 个实验：运行 C 模块测试
    python -m pytest tests/test_c_module.py -q

本次修复后实际结果为 82 passed；python -m pytest -q 为 85 passed, 1 warning。
warning 是测试客户端依赖的弃用提示，不是测试失败；详细环境与范围见验证记录。

## 接口对接注意事项（必须与 D 同学确认）
- C 的题库 references 是 [{"text": "..."}]，配合 D 当前修改题的判分逻辑。
- 全部用“修改题”模式：D 目前会把判断题/选择题的 references 当选项返回，
  存在提前泄露答案的风险，须 D 修正后再加入判断/选择题。
- D 当前 /api/submit-answer 自己计算薄弱类别和下一题；C 的推荐模块是独立函数，
  **尚未接入现有 API**。需由 D 调用 recommend_next 并传入真实历史与审核题库。
- D 的 /api/profile 目前使用原有简易计算规则，尚未接入 C 的平滑统计。
- 推荐历史须按从旧到新排列，末尾为最近记录；is_correct 接受布尔值或 SQLite 整数 0/1，其他值会被拒绝。recent_limit=0 表示不避开历史题；演示开关仅额外放行 pending，不放行 rejected。
- C 的评测只支持八类单一主标签 Macro-F1；多标签、有效修改与 LLM 对照实验待加入。
- 某些病句存在不同修改可能改变原意的情况，尤其表意不明，需要人工校对。

## 下一轮要做的工作
1. 与 B 确认多标签判定与“正常句/其他”的约定。
2. 和语文老师或可靠教学资料逐题核验 20 道候选题。
3. 扩充 60–100 道人工审核题，区分开发集/最终测试集。
4. 与 D 联调推荐服务及题库入库流程，保证修改题不泄露答案。
5. 与 B 联调真实模型预测输出，完成 Baseline / 结构化 / 全闭环评测。
6. 后续是否向小组仓库提交 PR，由用户与组员另行决定；本次验证不创建 PR、不合并 main。
