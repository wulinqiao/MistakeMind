"""Build a comparison and failure-case report from completed experiment files."""
import argparse
import json
from pathlib import Path


def generate(paths, output, data='data/b_evaluation_reviewed.json'):
    from scripts.validate_c_questions import load_questions
    from evaluation.run_b import digest
    dataset = load_questions(data)
    gold = {r['id']: r for r in dataset}
    reports = []
    failures = []
    for path in map(Path, paths):
        summary = json.loads(path.with_suffix('.summary.json').read_text(encoding='utf-8'))
        rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        manifest = rows[0]
        latest = {r['id']: r for r in rows[1:]}
        # Record refused/failed cases as well as accepted but wrong predictions.
        if manifest['data_hash'] != digest(dataset) or summary['missing'] or len(latest) != len(gold):
            raise ValueError('运行文件不完整或指定数据集与实验哈希不符')
        for r in latest.values():
            expected = gold.get(r['id'])
            if expected is None:
                continue
            result = r.get('result') or {}
            wrong = result.get('has_error') != expected['has_error'] or set(result.get('error_types', [])) != set(expected['error_types'])
            if r['status'] != 'success' or wrong:
                failures.append(f"| {summary['group']} | {r['id']} | {r['status']} | {expected['sentence']} | {'、'.join(expected['error_types']) or '正常句'} | {'、'.join(result.get('error_types', [])) or r.get('error') or '未接受/正常句'} |")
        reports.append((summary, manifest))
    lines = ['# 真实模型对照实验结果', '',
             '本报告由运行文件生成。指标覆盖全部请求，拒判和失败不会从分母中删除。检测采用运行器定义的保守计分，不能将其当作标准混淆矩阵。', '',
             '| 组别 | 样本数 | 接受率 | 拒判率 | 失败率 | 主类别准确率 | 八类 Macro-F1 | 平均耗时 ms |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for s, _ in reports:
        lines.append(f"| {s['group']} | {s['samples']} | {s['success_rate_all_requests']:.3f} | {s['review_rate_all_requests']:.3f} | {s['failure_rate_all_requests']:.3f} | {s['primary_accuracy_all_requests']:.3f} | {s['classification_all_requests']['macro_f1_eight_classes']:.3f} | {s['mean_latency_ms_all_requests']:.2f} |")
    lines += ['', '## 实验依据', '']
    for s, m in reports:
        lines += [f"- {s['group']}：model={m['settings']['model']}，Prompt={m['prompt_version']}，formal={s['formal']}，mode={s['mode']}。数据哈希 `{m['data_hash']}`，代码哈希 `{m['code_hash']}`。外部调用 {s['external_calls']} 次，已报告 token {s['reported_usage']['total_tokens']}，多标签 micro-F1={s['multilabel_micro_all_requests']['f1']:.4f}。"]
    lines += ['', '## 结论边界', '',
              '这些数据衡量固定测试集上的单次真实调用表现，不代表跨模型或跨人群结论。基线也使用相同 JSON 输出契约，以便解析和比较；结构化组额外使用标签定义、教学约束和独立复核。', '',
              '修改有效率和原意保持率须填写各组 ratings.json 后由人工评分脚本计算，当前不自动给分。费用须按供应商账单核算，token 用量保存在 summary。尚未审核的练习题不能用作正式 full 组工具题库。', '',
              '## 待复核与错误案例', '',
              '| 组别 | 题号 | 状态 | 原句 | 标准标签 | 预测标签或错误 |',
              '| --- | --- | --- | --- | --- | --- |', *failures]
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='+')
    parser.add_argument('--output', required=True)
    parser.add_argument('--data', default='data/b_evaluation_reviewed.json')
    args = parser.parse_args()
    generate(args.runs, args.output, args.data)
