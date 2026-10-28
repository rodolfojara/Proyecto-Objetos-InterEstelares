import sqlite3, json
from datetime import datetime

db = r'C:/Users/user/Documents/Proyecto predeterminado/data/db/iso.db'
data_path = r'C:/Users/user/Documents/Proyecto predeterminado/data/objects.json'

with open(data_path, encoding='utf-8') as f:
    data = json.load(f)

conn = sqlite3.connect(db)
cur = conn.cursor()

for o in data['objects']:
    cur.execute('INSERT OR IGNORE INTO objects(designation,name,type,discovery_date,status,notes) VALUES(?,?,?,?,?,?)',
                (o['designation'], o['name'], o['type'], o['discovery_date'], o['status'], o['notes']))
    cur.execute('SELECT id FROM objects WHERE designation=?', (o['designation'],))
    row = cur.fetchone()
    if not row:
        continue
    oid = row[0]
    for el in o.get('orbital_elements', []):
        cur.execute('INSERT INTO orbital_elements(object_id,epoch,e,q,i,e_hyperbolic_v_inf,source_url,confidence) VALUES(?,?,?,?,?,?,?,?)',
                    (oid, el.get('epoch'), el.get('e'), el.get('q'), el.get('i'), el.get('e_hyperbolic_v_inf'), el.get('source_url'), el.get('confidence', 3)))
    for act in o.get('activity', []):
        cur.execute('INSERT INTO activity(object_id,rh,activity_detected,coma_detected,dust_detected,source_url,confidence) VALUES(?,?,?,?,?,?,?)',
                    (oid, act.get('rh'), act.get('activity_detected'), act.get('coma_detected'), act.get('dust_detected'), act.get('source_url'), act.get('confidence', 3)))
    cur.execute("INSERT INTO provenance_log(entity,entity_id,action,agent,details) VALUES('objects',?, 'insert', 'system', 'initial ingest fase0/1')", (oid,))

conn.commit()
conn.close()
print('ingest done')
