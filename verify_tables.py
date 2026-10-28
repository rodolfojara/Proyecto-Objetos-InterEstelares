import sqlite3
conn = sqlite3.connect(r'C:/Users/user/Documents/Proyecto Objetos InterEstelares/data/db/iso.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print([r[0] for r in cur.fetchall()])
conn.close()
