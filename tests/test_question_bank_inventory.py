import copy
import json
from pathlib import Path

import pytest

import scripts.list_question_banks as bank_module
from scripts.validate_c_questions import load_questions


def test_catalog_includes_both_practice_banks_outside_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    entries = bank_module.inventory()
    assert [e["count"] for e in entries] == [20, 100]
    assert sum(e["pending"] for e in entries) == 120
    assert sum(e["approved_active"] for e in entries) == 0


def test_inventory_rejects_cross_bank_duplicate_id(tmp_path, monkeypatch):
    row = load_questions(bank_module.ROOT / "data/questions.json")[0]
    other = copy.deepcopy(row)
    other["sentence"] = "另一条测试句子，用于验证题号冲突。"
    for name, item in (("first.json", row), ("second.json", other)):
        (tmp_path / name).write_text(json.dumps([item], ensure_ascii=False), encoding="utf-8")
    catalog = {"practice_banks": [
        {"path": "first.json", "name": "first", "expected_count": 1},
        {"path": "second.json", "name": "second", "expected_count": 1},
    ]}
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    monkeypatch.setattr(bank_module, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="跨题库 id 重复"):
        bank_module.inventory(catalog_path)
