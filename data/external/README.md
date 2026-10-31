# 外部题库候选：CS2W

`cs2w_grammar_candidates.json` 是从 **CS2W 的 train 划分**筛选并转换的 100 道口语修改候选题，目标为 30 道词语缺失、70 道词语赘余。原句 `content` 和参考 `ref` 完整保留；不是项目组新编或新完成人工审核的题目。所有记录均为 `pending`、`is_active=false`，须逐题审核后才能进入正式题目接口。

CS2W 是口语转书面语语料，包含口语省略、赘词及其他转换现象，**不能视为覆盖八类的中高考标准病句题库**。有些表达在对话中可接受；当前参考改写只用于候选复核，不应作为唯一合理答案。

## 来源和数据许可

- 原项目：[guozishan/CS2W](https://github.com/guozishan/CS2W)。
- 作者：Zishan Guo、Linhao Yu、Minghui Xu、Renren Jin、Deyi Xiong，EMNLP 2023。
- 固定 revision：`be6e0519b433cfa9d8388b23308f1380716254fd`。
- 仅使用 `data/train.jsonl`；未把 val/test 题目加入练习候选。
- [固定文件下载地址](https://raw.githubusercontent.com/guozishan/CS2W/be6e0519b433cfa9d8388b23308f1380716254fd/data/train.jsonl)。
- 原始文件 SHA256：`acf249f7e8077337fc8e4029e7c381e117f3bc780fef48c820e4f328e78f563a`。
- 原始 Git blob：`2cb49b442e1bd225c0a00f241772fb57d671c075`；2,619,946 字节、5,789 条训练记录。
- 官方 README 的 **Data License** 明确指定数据为 [CC BY-SA 4.0](https://github.com/guozishan/CS2W#data-license)。本候选 JSON 作为改编数据继续采用同一许可；分享时保留作者、来源、许可链接和修改说明。详见 [LICENSE-CS2W.txt](LICENSE-CS2W.txt)。

这次改编包括筛选、去重、字段转换、暂定课程类别与来源元数据；未改写原句或参考句，也不暗示原作者认可本项目的教学标注。

## 筛选及字段映射

只取 `grammatical_error_num>0`，且 `disfluency_num`、`colloquial_word_num`、`asr_error_num` 均为 0、对应字符标签也全为 0 的记录。语法字符标签必须与原句等长，只含一种非零类型；句长为 8–65 字符，修改为不超过 8 字符的纯插入或删除。对于赘余记录，精确删除标为 `1` 的字符必须得到上游参考句。按原始 id 排序，按 id 和原句去重，确定性选取 30 条缺失和 70 条赘余；不足时按实际可用记录补足并报告，不生成虚构题目。

该固定版本按以上规则及下述排除项筛选后有 205 条记录，去重后为 204 条（34 条缺失、170 条赘余），因此实际可生成所列的 100 条候选。生成文件固定使用 UTF-8 和 LF 换行，便于跨系统重现。

| CS2W 字段/标签 | 本项目字段/暂定类别 |
| --- | --- |
| `content` | `sentence`，原文不变 |
| `ref` | `references[0].text`，参考不变 |
| `grammatical_error_label` 非零类型 `1`（Redundant Words） | `成分赘余`，暂定映射 |
| `grammatical_error_label` 非零类型 `2`（Missing Words） | `成分残缺`，暂定映射 |
| 原始 id、train、revision、字符标签 | `source_metadata`，逐题保留 |

上游的“词语缺失/赘余”不等于已经完成本课程八类病句教学判定，`category_mapping_status=provisional` 明确记录这一点；没有自动推断其余六类。三条参考明显仍有疑问的记录（id 1202、2426、5477）另行排除，原因保留在生成脚本中；仍需对其余候选进行完整人工审核。

## 重现和校验

在项目根目录运行：

```powershell
python -m scripts.prepare_cs2w_questions
python -m scripts.validate_c_questions data/external/cs2w_grammar_candidates.json
python -m scripts.import_c_questions data/external/cs2w_grammar_candidates.json --dry-run
python -m pytest tests/test_external_question_bank.py -q
```

下载受限时，将同一固定版本的原始 `train.jsonl` 保存到本地，再离线重现。两种方式都会校验相同的 SHA256 和 Git blob：

```powershell
python -m scripts.prepare_cs2w_questions --input C:\path\to\train.jsonl
```

当前候选均未审核，导入预览应为 **0**；此文件不会自动替换正式数据库。外部来源及其 train 标识须一直保留，未来评测集也应另行划分并记录来源，不能把练习候选伪称为未见测试集。
