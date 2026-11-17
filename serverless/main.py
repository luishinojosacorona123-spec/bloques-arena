"""API de resultados: almacenamiento SQLite local o Firestore en Cloud Run.
Cloud Run se despliega privado: el llamador necesita roles/run.invoker e ID token.
No acepta puntajes del cliente web. API para servicios de confianza/laboratorio.
"""
import os, re, sqlite3, hashlib
from contextlib import contextmanager
from threading import Lock
from flask import Flask, request, jsonify
app=Flask(__name__)
schema_lock = Lock()
initialized_databases = set()

@contextmanager
def connection():
    database = os.path.abspath(os.getenv('SCORES_DB', 'scores.db'))
    con = sqlite3.connect(database, timeout=15)
    try:
        with schema_lock:
            if database not in initialized_databases:
                con.execute('PRAGMA journal_mode=WAL')
                con.execute('CREATE TABLE IF NOT EXISTS results (match TEXT, player TEXT, score INTEGER, PRIMARY KEY(match,player))')
                initialized_databases.add(database)
        with con:
            yield con
    finally:
        con.close()

@app.post('/score')
def score():
    d=request.get_json(silent=True)
    if not isinstance(d,dict): return jsonify(error='JSON requerido'),400
    match,player,points=d.get('match'),d.get('player'),d.get('score')
    if (not isinstance(match,str) or not isinstance(player,str)
        or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',match)
        or not re.fullmatch(r'[a-zA-Z0-9_-]{1,32}',player)
        or type(points) is not int or not 0<=points<=10_000_000):
        return jsonify(error='Resultado inválido'),400
    if os.getenv('STORAGE')=='firestore':
        from google.cloud import firestore
        key=hashlib.sha256((match+'\0'+player).encode()).hexdigest()
        db=firestore.Client(); ref=db.collection('results').document(key)
        # create es atómico: evita doble conteo ante reintentos de la misma partida.
        from google.api_core.exceptions import AlreadyExists
        try: ref.create(dict(player=player,score=points,match=match))
        except AlreadyExists: return jsonify(status='duplicate'),200
    else:
        with connection() as con:
            cur=con.execute('INSERT OR IGNORE INTO results VALUES(?,?,?)',(match,player,points))
            if not cur.rowcount: return jsonify(status='duplicate'),200
    return jsonify(status='created'),201

@app.get('/top')
def top():
    # Clasificación por mejor resultado individual (no suma histórica).
    if os.getenv('STORAGE')=='firestore':
        from google.cloud import firestore
        docs=firestore.Client().collection('results').order_by('score',direction=firestore.Query.DESCENDING).limit(10).stream()
        rows=[d.to_dict() for d in docs]
    else:
        with connection() as con:
            rows=[dict(player=p,score=s,match=m) for m,p,s in con.execute('SELECT match,player,score FROM results ORDER BY score DESC,player LIMIT 10')]
    return jsonify(rows)

@app.get('/health')
def health(): return jsonify(ok=True)

if __name__=='__main__': app.run(host='127.0.0.1',port=8080)
