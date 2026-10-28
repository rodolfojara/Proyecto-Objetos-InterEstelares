import sqlite3

db = r'C:/Users/user/Documents/Proyecto Objetos InterEstelares/data/db/iso.db'
patch = r'C:/Users/user/Documents/Proyecto Objetos InterEstelares/config/schema_fase4_patch.sql'
with open(patch, encoding='utf-8') as f:
    schema = f.read()

conn = sqlite3.connect(db)
conn.executescript(schema)
conn.commit()
conn.close()
print('patched_fase4')
