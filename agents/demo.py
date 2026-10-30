"""Fixed development fixtures; never read the held-out evaluation candidates."""
from agents.models import DiagnosisOutputV1

ERRORS = [
    ("通过开展此次活动，使同学们提高了环保意识。", ["结构混乱", "成分残缺"], "通过……使……", "介词结构与使令结构连用，主语缺失。", ["开展此次活动，使同学们提高了环保意识。", "通过开展此次活动，同学们提高了环保意识。"]),
    ("经过医生的治疗，使病人恢复了健康。", ["成分残缺"], "经过……使……", "介词结构掩盖了主语。", ["经过医生的治疗，病人恢复了健康。"]),
    ("他忍俊不禁地笑了起来。", ["成分赘余"], "忍俊不禁地笑", "忍俊不禁已包含笑的意思。", ["他忍俊不禁。"]),
    ("我们要提高阅读的习惯。", ["搭配不当"], "提高阅读的习惯", "提高不能搭配习惯。", ["我们要养成阅读的习惯。"]),
    ("这本书对我很感兴趣。", ["语序不当"], "这本书对我", "感兴趣的主体与对象位置颠倒。", ["我对这本书很感兴趣。"]),
    ("这项工作能成功的原因是大家合作的结果。", ["结构混乱"], "原因是……的结果", "原因是与是……的结果两种句式杂糅。", ["这项工作能成功的原因是大家合作。"]),
    ("小张告诉小李，他的书丢了。", ["表意不明"], "他的书", "他可能指小张，也可能指小李。", ["小张告诉小李，小张的书丢了。", "小张告诉小李，小李的书丢了。"]),
    ("全班所有同学基本上都到齐了。", ["不合逻辑"], "所有……基本上", "所有与基本上限定范围冲突。", ["全班所有同学都到齐了。"]),
    ("虽然天气晴朗，所以我们出发了。", ["关联词使用不当"], "虽然……所以……", "转折关联词与因果关联词搭配不当。", ["因为天气晴朗，所以我们出发了。"]),
]
NORMALS = ["通过学习，他能够熟练使用这台机器。", "我们通过努力，使计划顺利完成。", "今天的天空很蓝。", "同学们认真地完成了作业。"]
AMBIGUOUS = ["这件事情就是这样。", "他比我更喜欢她。", "请结合上文判断这句话。", "照他说的办。"]


def mock_output(sentence: str, need_hints: bool):
    for text, types, span, reason, corrections in ERRORS:
        if sentence == text:
            ambiguous = types == ["表意不明"]
            return DiagnosisOutputV1(has_error=True, error_types=types, error_span=span,
                explanation="[Mock 演示样例] " + reason,
                corrections=[dict(text=t, kind="最小修改" if i == 0 else "另一种合理修改", reason=reason) for i, t in enumerate(corrections)],
                hints=[dict(level=1, text="观察“" + span + "”。"), dict(level=2, text="检查" + types[0] + "。"), dict(level=3, text=reason)] if need_hints else [],
                confidence=.5 if ambiguous else 1.0, needs_context=ambiguous)
    known = sentence in NORMALS
    return DiagnosisOutputV1(has_error=False, error_types=[], error_span=None,
        explanation="[Mock 演示样例] 该固定样例为正常句。" if known else "[Mock 未覆盖] 当前是离线演示，无法判断此句；请配置真实模型或人工复核。",
        corrections=[], hints=[], confidence=1.0 if known else 0.0, needs_context=not known)
