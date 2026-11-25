import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
conn = sqlite3.connect(str(ROOT / 'data/db/iso.db'))
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print([r[0] for r in cur.fetchall()])
conn.close()
