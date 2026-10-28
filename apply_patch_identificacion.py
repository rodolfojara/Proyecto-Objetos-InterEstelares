"""Aplica el patch de cronologia de identificacion y carga data/identification_timeline.json.

Idempotente: se puede ejecutar varias veces sin duplicar filas.

Uso:
    python apply_patch_identificacion.py
"""

import json
import sqlite3

BASE = r'C:/Users/user/Documents/Proyecto Objetos InterEstelares'
DB = BASE + '/data/db/iso.db'
PATCH = BASE + '/config/schema_identificacion_patch.sql'
VIEW = BASE + '/config/schema_identificacion_view.sql'
DATA = BASE + '/data/identification_timeline.json'

CAMPOS = (
    'earliest_observation_date',
    'discovery_date',
    'announcement_date',
    'iso_confirmation_date',
    'iso_designation_date',
    'designations_pre_iso',
    'discoverer',
    'discovery_site',
    'mpc_code',
    'reference_id',
    'source_url',
    'notes',
    'confidence',
)

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 1. Tabla object_identification
with open(PATCH, encoding='utf-8') as f:
    cur.executescript(f.read())

# 2. Columna editorial en object_publications (idempotente)
cols = [r[1] for r in cur.execute('PRAGMA table_info(object_publications)')]
if 'publication_class' not in cols:
    cur.execute('ALTER TABLE object_publications ADD COLUMN publication_class TEXT')
    print('  + columna object_publications.publication_class agregada')
else:
    print('  = columna object_publications.publication_class ya existe')

# 3. Vista de clasificacion por epoca
with open(VIEW, encoding='utf-8') as f:
    cur.executescript(f.read())

# 4. Carga de la cronologia
with open(DATA, encoding='utf-8') as f:
    data = json.load(f)

insertados, omitidos = 0, 0
for o in data['objects']:
    row = cur.execute('SELECT id FROM objects WHERE designation = ?', (o['designation'],)).fetchone()
    if not row:
        print('  ! objeto no encontrado en la DB:', o['designation'])
        omitidos += 1
        continue
    oid = row[0]

    placeholders = ', '.join(['?'] * len(CAMPOS))
    updates = ', '.join('%s = excluded.%s' % (c, c) for c in CAMPOS)
    cur.execute(
        'INSERT INTO object_identification (object_id, %s) VALUES (?, %s) '
        'ON CONFLICT(object_id) DO UPDATE SET %s' % (', '.join(CAMPOS), placeholders, updates),
        (oid, *[o.get(c) for c in CAMPOS]),
    )
    cur.execute(
        "INSERT INTO provenance_log (entity, entity_id, action, source_url, agent, details) "
        "VALUES ('object_identification', ?, 'upsert', ?, 'normalizador', ?)",
        (oid, o.get('source_url'), 'cronologia de identificacion; ref: %s' % o.get('reference_id')),
    )
    insertados += 1
    print('  + %-14s deteccion=%s  confirmacion=%s  designacion=%s' % (
        o['designation'], o['earliest_observation_date'],
        o['iso_confirmation_date'], o['iso_designation_date']))

conn.commit()

print('\nResumen')
for r in cur.execute(
    'SELECT o.designation, i.discovery_date, i.iso_confirmation_date, i.iso_designation_date '
    'FROM object_identification i JOIN objects o ON o.id = i.object_id ORDER BY o.id'
):
    print('  %-14s descubrimiento=%s  confirmacion=%s  designacion I=%s' % r)

print('\nFilas cargadas: %d | omitidas: %d' % (insertados, omitidos))
conn.close()
