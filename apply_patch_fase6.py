import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
db = str(ROOT / 'data/db/iso.db')
patch = str(ROOT / 'config/schema_fase6_patch.sql')
with open(patch, encoding='utf-8') as f:
    schema = f.read()

conn = sqlite3.connect(db)
conn.executescript(schema)
conn.commit()
conn.close()
print('patched_fase6')
