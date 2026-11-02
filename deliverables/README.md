# MistakeMind 交付材料

| 文件或目录 | 用途 |
| --- | --- |
| 课程报告.md | 系统设计、核心算法、工程实现、真实实验及局限 |
| MistakeMind课堂汇报.pptx | 10 页可编辑课堂汇报，含实际浏览器截图与真实对照表 |
| 课堂演示脚本.md | 约 5 分钟，按 A/B/C/D 四个环节组织 |
| browser/ | 固定 Mock 演示截图与约 9 分 39 秒原始备用录屏 |
| experiment_records/ | 两组各 79 条真实实验逐题记录、汇总、人工评分表及运行时源码 |

代码与运行入口仍在项目根目录。`../docs/PROJECT_ACCEPTANCE.md` 说明启动、部署、题库审核和未完成的人工验收；`../docs/EXPERIMENT_RESULTS.md` 给出指标与失败案例。

source_at_start.zip 的源码哈希已核对与两组 manifest 一致。后续界面和演示文案修复不改变本次实验的原始记录。ratings 中空值表示尚未人工评分，不能当成有效修改率为 0 或 100%。

题库人工审核表在 `../docs/review_forms/`，填好后通过 review_practice 导出已审版本，再使用 import_c_questions 导入正式数据库。64 道候选未被自动批准。
