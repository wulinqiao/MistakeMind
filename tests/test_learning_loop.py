import copy
import json
import sqlite3
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

import db.database as database_module
from backend.main import app
from db.database import Database
from scripts.seed_demo import seed
from scripts.review_practice import export_review, apply_review
from scripts.import_c_questions import import_approved
from scripts.validate_c_questions import load_questions


@pytest.fixture
def setup(tmp_path, monkeypatch):
    path = tmp_path / "demo.db"
    assert seed(path) == 36
    db = Database(path)
    monkeypatch.setattr(database_module, "_db", db)
    return TestClient(app), db


def answer(client, qid, value):
    return client.post('/api/submit-answer', json={"user_id": "test_learner", "question_id": qid,
        "answer": value, "answer_type": "choice"}).json()


def test_recommendation_is_retrievable_and_blind(setup):
    client, db = setup
    result = answer(client, 'demo_02_2', '语序不当')
    assert result['success'] and not result['data']['is_correct']
    rec = result['data']['recommended_question_id']
    row = client.get(f'/api/questions/{rec}').json()['data']['question']
    assert row['question_id'] == rec and row['category'] is None
    assert row['mode'] == '选择题' and row['difficulty'] == '初中'
    assert 'references' not in row and 'explanation' not in row
    assert result['data']['diagnosis']['error_span']
    assert result['data']['trace'][-1]['agent'] == 'recommend_tool'
    assert db.get_question(rec)['category'] == '成分残缺'


def test_personalized_questions_respect_filters(setup):
    client, db = setup
    for _ in range(4):
        answer(client, 'demo_03_2', '搭配不当')
    rows = client.get('/api/questions', params={'user_id': 'test_learner', 'mode': '选择题'}).json()['data']['questions']
    assert rows[0]['mode'] == '选择题'
    assert db.get_question(rows[0]['question_id'])['category'] == '成分赘余'


def test_history_contains_saved_explanation_and_wrong_filter(setup):
    client, db = setup
    answer(client, 'demo_02_2', '语序不当')
    answer(client, 'demo_03_2', '成分赘余')
    history = client.get('/api/history/test_learner', params={'wrong_only': True}).json()['data']
    assert history['total'] == 1 and not history['items'][0]['is_correct']
    item = history['items'][0]
    assert item['original_sentence'] == db.get_question('demo_02_2')['sentence']
    assert item['diagnosis']['corrections'] and '[开发演示]' in item['diagnosis']['explanation']
    # Reopening reads persisted records rather than frontend memory.
    assert Database(db.path).history('test_learner', 1, 20, wrong_only=True)[0] == 1


def test_recent_profile_is_smoothed_and_marks_small_samples(setup):
    client, _ = setup
    answer(client, 'demo_02_2', '成分残缺')
    profile = client.get('/api/profile/test_learner').json()['data']
    stat = profile['category_stats'][0]
    assert stat['accuracy'] == 1 and stat['mastery'] == pytest.approx(2/3)
    assert not stat['sample_sufficient'] and stat['priority'] == 'insufficient'
    assert stat['errors'] == 0 and profile['trend'][0]['attempts'] == 1
    assert profile['minimum_samples'] == 3 and profile['recent_window'] == 50


def test_recent_profile_does_not_treat_old_errors_as_current(setup):
    client, db = setup
    with closing(db.connect()) as con, con:
        con.execute("INSERT INTO users VALUES ('long_user','','初中','2026-01-01')")
        for i in range(70):
            con.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)", (f'a{i}', 'long_user', 'demo_02_2',
                '"成分残缺"', int(i >= 20), 0, 1, f'2026-10-{i//24+1:02d}T{i%24:02d}:00:00+08:00'))
    stat = db.profile('long_user')['category_stats'][0]
    assert stat['attempts'] == 70 and stat['errors'] == 20
    assert stat['recent_attempts'] == 50 and stat['recent_accuracy'] == 1
    assert stat['mastery'] == pytest.approx(51/52)


def test_missing_inactive_question_and_status(setup):
    client, db = setup
    with closing(db.connect()) as con, con:
        con.execute("UPDATE questions SET is_active=0 WHERE id='demo_02_2'")
    assert client.get('/api/questions/demo_02_2').status_code == 404
    status = client.get('/api/status').json()['data']
    assert status == {'agent_mode': 'mock', 'active_questions': 35, 'demo_dataset': True, 'api_version': 'v1.2'}


def test_review_form_requires_individual_human_evidence(tmp_path):
    form = tmp_path / 'form.json'
    out = tmp_path / 'reviewed.json'
    export_review('data/questions.json', form)
    rows = json.loads(form.read_text(encoding='utf-8'))
    rows[0]['decision'] = 'approved'
    form.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    with pytest.raises(ValueError, match='审核人'):
        apply_review('data/questions.json', form, out)
    assert not out.exists()
    rows[0].update(reviewer='test-only', reviewed_at='2026-11-01T12:00:00+08:00', notes='test-only approval')
    form.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    assert apply_review('data/questions.json', form, out) == 1
    dbpath = tmp_path / 'reviewed.db'
    assert import_approved(out, dbpath) == 1
    assert Database(dbpath).get_question(rows[0]['id'])['explanation'] == rows[0]['explanation']
    assert all(q['review_status'] == 'pending' for q in load_questions('data/questions.json'))


def test_demo_does_not_modify_candidates_or_evaluation_set(setup):
    client, _ = setup
    for path in ('data/questions.json', 'data/school_questions.json'):
        assert all(q['review_status'] == 'pending' and not q['is_active'] for q in load_questions(path))
    assert len(load_questions('data/b_evaluation_reviewed.json')) == 79
