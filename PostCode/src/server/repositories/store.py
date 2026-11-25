import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def transaction():
    path = Path(os.environ.get("POSTCODE_DB", Path(__file__).resolve().parents[3] / "db" / "premium.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS profiles (sid TEXT PRIMARY KEY, data TEXT NOT NULL)")
        conn.execute("CREATE TABLE IF NOT EXISTS events (sid TEXT, event TEXT, at TEXT DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    finally:
        conn.close()

def read(conn, sid):
    row = conn.execute("SELECT data FROM profiles WHERE sid=?", (sid,)).fetchone()
    return json.loads(row[0]) if row else None

def save(conn, sid, state):
    conn.execute("INSERT OR REPLACE INTO profiles VALUES (?,?)", (sid,json.dumps(state,ensure_ascii=False)))

def event(conn, sid, name):
    conn.execute("INSERT INTO events(sid,event) VALUES (?,?)", (sid,name))
