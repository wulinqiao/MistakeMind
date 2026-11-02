from collections import Counter
from contextlib import closing

from db.database import Database
from scripts.import_c_questions import import_approved
from scripts.validate_c_questions import load_questions


def test_approval_exports_preserve_content_and_record_user_confirmation():
    for name in ('questions', 'school_questions'):
        original = load_questions(f'data/{name}.json')
        reviewed = load_questions(f'data/{name}.reviewed.json')
        assert len(original) == len(reviewed)
        for source, accepted in zip(original, reviewed):
            assert source['review_status'] == 'pending' and not source['is_active']
            assert accepted['review_status'] == 'approved' and accepted['is_active']
            for key in source.keys() - {'review', 'review_status', 'is_active'}:
                assert accepted[key] == source[key]
            assert '聊天' in accepted['review']['reviewer']
            assert '确认审核通过所有题目' in accepted['review']['notes']


def test_import_all_modes_keeps_one_sentence_and_references(tmp_path):
    dbpath = tmp_path / 'approved.db'
    assert import_approved('data/questions.reviewed.json', dbpath, all_modes=True) == 60
    assert import_approved('data/school_questions.reviewed.json', dbpath, all_modes=True) == 132
    db = Database(dbpath)
    with closing(db.connect()) as con:
        rows = [dict(r) for r in con.execute('SELECT * FROM questions')]
        assert len({r['sentence'] for r in rows}) == 64
        assert Counter(r['mode'] for r in rows) == {'判断题': 64, '选择题': 64, '修改题': 64}
        assert len({r['id'] for r in rows}) == 192
        assert all(r['is_active'] == 1 for r in rows)
        assert con.execute('SELECT count(*) FROM question_details').fetchone()[0] == 192
    for r in rows:
        stem = r['id'].split('__')[0]
        original = db.get_question(stem)
        assert r['sentence'] == original['sentence']
        assert r['references_json'] == original['references_json']


def test_all_modes_cannot_enable_unapproved_content(tmp_path):
    dbpath = tmp_path / 'must_not_exist.db'
    assert import_approved('data/questions.json', dbpath, all_modes=True) == 0
    assert not dbpath.exists()
