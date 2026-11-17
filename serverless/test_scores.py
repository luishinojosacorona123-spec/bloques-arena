import main

def test_validation_duplicate_and_top(tmp_path,monkeypatch):
    monkeypatch.setenv('SCORES_DB',str(tmp_path/'scores.db'))
    monkeypatch.delenv('STORAGE',raising=False)
    c=main.app.test_client()
    assert c.post('/score',json={'score':-1}).status_code==400
    d=dict(match='match1',player='ana',score=500)
    assert c.post('/score',json=d).status_code==201
    assert c.post('/score',json=d).json['status']=='duplicate'
    assert c.get('/top').json==[d]
