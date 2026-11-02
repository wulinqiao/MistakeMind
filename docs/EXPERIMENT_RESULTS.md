# 真实模型对照实验结果

本报告由运行文件生成。指标覆盖全部请求，拒判和失败不会从分母中删除。检测采用运行器定义的保守计分，不能将其当作标准混淆矩阵。

| 组别 | 样本数 | 接受率 | 拒判率 | 失败率 | 主类别准确率 | 八类 Macro-F1 | 平均耗时 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 79 | 0.899 | 0.025 | 0.076 | 0.835 | 0.806 | 12874.80 |
| structured | 79 | 0.772 | 0.127 | 0.101 | 0.722 | 0.733 | 18929.18 |

## 实验依据

- baseline：model=deepseek-v4-1-flash-260910，Prompt=b-1.0.0，formal=True，mode=live。数据哈希 `c04bbf03d45d9ba479858b97c504f968764132daac1c0a49d39e177bdccbb383`，代码哈希 `014e44fd39a3cd5a739dc4ef4dccb5fb04ac306cc9ce78d1393d04fa92d943b7`。外部调用 96 次，已报告 token 110281，多标签 micro-F1=0.8504。
- structured：model=deepseek-v4-1-flash-260910，Prompt=b-1.0.0，formal=True，mode=live。数据哈希 `c04bbf03d45d9ba479858b97c504f968764132daac1c0a49d39e177bdccbb383`，代码哈希 `014e44fd39a3cd5a739dc4ef4dccb5fb04ac306cc9ce78d1393d04fa92d943b7`。外部调用 173 次，已报告 token 219808，多标签 micro-F1=0.7797。

## 结论边界

本次结构化组全样本主类别准确率 72.15%，低于基线 83.54%；其接受率为 77.22%，基线为 89.87%。复核增加了拒判和调用开销，本次实验没有证明整体效果优于基线。两组失败分别为 6 次和 8 次，均为 MODEL_TIMEOUT。若将待复核视为有效流程结果、只将失败视为未完成，则流程完成率为 92.41% 和 89.87%，仍低于计划 95% 的参考目标；该口径不同于模型结论接受率。结果保持原样，不选择性删除失败样本，也不在本测试集上调参后重新宣称独立验证。

两组共 269 次外部调用，已报告 330089 token。逐题 JSONL、summary、待人工填写的 ratings 和与运行哈希完全一致的源码快照位于 ../deliverables/experiment_records/。

这些数据衡量固定测试集上的单次真实调用表现，不代表跨模型或跨人群结论。基线也使用相同 JSON 输出契约，以便解析和比较；结构化组额外使用标签定义、教学约束和独立复核。

修改有效率和原意保持率须填写各组 ratings.json 后由人工评分脚本计算，当前不自动给分。费用须按供应商账单核算，token 用量保存在 summary。尚未审核的练习题不能用作正式 full 组工具题库。

## 待复核与错误案例

| 组别 | 题号 | 状态 | 原句 | 标准标签 | 预测标签或错误 |
| --- | --- | --- | --- | --- | --- |
| baseline | b_eval_007 | failed | 这份倡议书向全校同学发出了。 | 成分残缺 | MODEL_TIMEOUT |
| baseline | b_eval_013 | failed | 听完这个故事，她的心里感到十分欣慰和高兴极了。 | 成分赘余 | MODEL_TIMEOUT |
| baseline | b_eval_024 | success | 我们要增加实验水平，先写结论再做实验。 | 搭配不当、语序不当 | 搭配不当、不合逻辑 |
| baseline | b_eval_026 | failed | 我们必须把这件事的来龙去脉清楚地调查。 | 语序不当 | MODEL_TIMEOUT |
| baseline | b_eval_027 | failed | 他把已经完成的作业认真地又检查了一遍。 | 语序不当 | MODEL_TIMEOUT |
| baseline | b_eval_028 | failed | 这次调查既包括乡村，也包括山区的几个偏远村落。 | 语序不当 | MODEL_TIMEOUT |
| baseline | b_eval_030 | success | 他对自己能否完成任务十分相信。 | 语序不当 | 搭配不当 |
| baseline | b_eval_040 | success | 获胜的原因是合作的结果，所有队员几乎都参加了训练。 | 结构混乱、不合逻辑 | 结构混乱 |
| baseline | b_eval_041 | needs_review | 李明陪赵强去取他的证件。 | 表意不明 | 表意不明 |
| baseline | b_eval_044 | failed | 我们三个学校的学生参加了比赛。 | 表意不明 | MODEL_TIMEOUT |
| baseline | b_eval_045 | needs_review | 他走了一个多小时了。 | 表意不明 | 表意不明 |
| baseline | b_eval_046 | success | 新来的老师的朋友也到了。 | 表意不明 | 未接受/正常句 |
| baseline | b_eval_048 | success | 孙宁告诉陈浩他要参赛，虽然时间充足，所以不必着急。 | 表意不明、关联词使用不当 | 关联词使用不当 |
| baseline | b_eval_050 | success | 我校到场人数至少有一百人以上。 | 不合逻辑 | 成分赘余 |
| baseline | b_eval_053 | success | 能否坚持锻炼，是身体保持健康的关键。 | 不合逻辑 | 搭配不当 |
| structured | b_eval_007 | needs_review | 这份倡议书向全校同学发出了。 | 成分残缺 | 成分残缺 |
| structured | b_eval_013 | failed | 听完这个故事，她的心里感到十分欣慰和高兴极了。 | 成分赘余 | MODEL_TIMEOUT |
| structured | b_eval_015 | failed | 我亲眼目睹了候鸟迁徙的壮观场面。 | 成分赘余 | MODEL_TIMEOUT |
| structured | b_eval_016 | needs_review | 大家再次重复练习，以提高认真检查的习惯。 | 成分赘余、搭配不当 | 搭配不当、成分赘余 |
| structured | b_eval_018 | needs_review | 我们应当端正学习目的。 | 搭配不当 | 搭配不当 |
| structured | b_eval_021 | failed | 春天的校园是一个美丽的季节。 | 搭配不当 | MODEL_TIMEOUT |
| structured | b_eval_022 | needs_review | 这位队员具有顽强的毅力和敏捷的速度。 | 搭配不当 | 搭配不当 |
| structured | b_eval_027 | needs_review | 他把已经完成的作业认真地又检查了一遍。 | 语序不当 | 未接受/正常句 |
| structured | b_eval_028 | needs_review | 这次调查既包括乡村，也包括山区的几个偏远村落。 | 语序不当 | 不合逻辑 |
| structured | b_eval_030 | success | 他对自己能否完成任务十分相信。 | 语序不当 | 搭配不当 |
| structured | b_eval_040 | success | 获胜的原因是合作的结果，所有队员几乎都参加了训练。 | 结构混乱、不合逻辑 | 结构混乱 |
| structured | b_eval_042 | needs_review | 张老师看见王老师正在整理自己的讲义。 | 表意不明 | 表意不明 |
| structured | b_eval_044 | failed | 我们三个学校的学生参加了比赛。 | 表意不明 | MODEL_TIMEOUT |
| structured | b_eval_045 | needs_review | 他走了一个多小时了。 | 表意不明 | 表意不明 |
| structured | b_eval_046 | failed | 新来的老师的朋友也到了。 | 表意不明 | MODEL_TIMEOUT |
| structured | b_eval_047 | failed | 我借了妹妹的书。 | 正常句 | MODEL_TIMEOUT |
| structured | b_eval_048 | failed | 孙宁告诉陈浩他要参赛，虽然时间充足，所以不必着急。 | 表意不明、关联词使用不当 | MODEL_TIMEOUT |
| structured | b_eval_050 | success | 我校到场人数至少有一百人以上。 | 不合逻辑 | 成分赘余 |
| structured | b_eval_051 | needs_review | 参加活动的有青年、老人和教师。 | 不合逻辑 | 不合逻辑 |
| structured | b_eval_053 | success | 能否坚持锻炼，是身体保持健康的关键。 | 不合逻辑 | 搭配不当 |
| structured | b_eval_056 | failed | 全体队员大部分到了，周航告诉林涛他的球鞋在门外。 | 不合逻辑、表意不明 | MODEL_TIMEOUT |
| structured | b_eval_076 | needs_review | 他是否参加比赛，还需要征求教练的意见。 | 正常句 | 未接受/正常句 |
