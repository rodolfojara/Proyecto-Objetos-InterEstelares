#!/usr/bin/env python3
"""
Fase 2 corta - Solo aliases
Poblado idempotente de object_aliases siguiendo patrón batch/checkpoint/reanudación
Solo escribe en object_aliases. No toca tablas científicas.
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'db', 'iso.db')
OBJECTS_JSON = os.path.join(BASE_DIR, 'data', 'objects.json')
CHECKPOINT_DIR = os.path.join(BASE_DIR, '.metadata_checkpoints')
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, 'fase2_aliases_checkpoint.json')
FASE2_PLAN = os.path.join(CHECKPOINT_DIR, 'fase2_plan.json')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'fase2_aliases.log')

# Aliases conocidos para los 3 objetos interestelares
KNOWN_ALIASES = {
    "1I/'Oumuamua": [
        "1I/2017 U1",
        "1I/2017 U1 ('Oumuamua)",
        "A/2017 U1",
        "C/2017 U1 (PANSTARRS)",
        "2017 U1",
    ],
    "2I/Borisov": [
        "2I/2019 Q4",
        "2I/2019 Q4 (Borisov)",
        "C/2019 Q4 (Borisov)",
        "2019 Q4",
        "gb00234",
    ],
    "3I/ATLAS": [
        "3I/2025 N1",
        "3I/2025 N1 (ATLAS)",
        "C/2025 N1 (ATLAS)",
        "A11pl3Z",
        "2025 N1",
    ],
}


def log(msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"Error cargando checkpoint: {e}")
    return {
        "started_at": datetime.utcnow().isoformat() + 'Z',
        "done_object_ids": [],
        "done_designations": [],
        "aliases_inserted": 0,
        "last_object_id": None,
        "status": "in_progress"
    }


def save_checkpoint(cp):
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    cp['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cp, f, indent=2, ensure_ascii=False)


def load_fase2_plan():
    if os.path.exists(FASE2_PLAN):
        try:
            with open(FASE2_PLAN, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_fase2_plan(plan):
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    with open(FASE2_PLAN, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)


def get_objects(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, designation, name FROM objects ORDER BY id")
    return cur.fetchall()


def add_alias(conn, object_id, alias, source_url=None):
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT OR IGNORE INTO object_aliases (object_id, alias, source_url, notes, retrieved_at) VALUES (?, ?, ?, ?, ?)",
            (object_id, alias, source_url, 'fase2_corta_aliases', datetime.utcnow().isoformat() + 'Z')
        )
        conn.commit()
        return cur.rowcount
    except Exception as e:
        log(f"Error insertando alias {alias} para object_id={object_id}: {e}")
        conn.rollback()
        return 0


def main():
    parser = argparse.ArgumentParser(description='Fase 2 corta - solo aliases')
    parser.add_argument('--reanudar', action='store_true', help='Reanudar desde checkpoint')
    parser.add_argument('--force', action='store_true', help='Forzar re-ejecución desde cero')
    args = parser.parse_args()

    start_time = time.time()
    log("=" * 60)
    log("INICIO FASE 2 CORTA - SOLO ALIASES")
    log(f"DB: {DB_PATH}")
    log(f"Checkpoint: {CHECKPOINT_FILE}")
    log("=" * 60)

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    if args.force and os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        log("Checkpoint eliminado por --force")

    cp = load_checkpoint()
    if not args.reanudar and not args.force and cp.get('status') == 'completed':
        log("Ya completado según checkpoint. Usa --force para re-ejecutar o --reanudar para verificar.")
        sys.exit(0)

    plan = load_fase2_plan()
    if plan:
        plan['status'] = 'in_progress'
        plan['started_at'] = plan.get('started_at') or datetime.utcnow().isoformat() + 'Z'
        save_fase2_plan(plan)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        objects = get_objects(conn)
        log(f"Objetos encontrados: {len(objects)}")
        for oid, desig, name in objects:
            log(f"  - [{oid}] {desig} ({name})")

        total_inserted = cp.get('aliases_inserted', 0)
        done_ids = set(cp.get('done_object_ids', []))

        for oid, desig, name in objects:
            if oid in done_ids and not args.force:
                log(f"Saltando [{oid}] {desig} (ya procesado)")
                continue

            log(f"Procesando [{oid}] {desig}...")
            aliases_to_add = []

            # Añadir aliases conocidos para esta designación
            if desig in KNOWN_ALIASES:
                for a in KNOWN_ALIASES[desig]:
                    aliases_to_add.append(a)

            # También añadir la designación completa como alias por si acaso (idempotente)
            if name and name != desig:
                aliases_to_add.append(name)

            inserted_for_obj = 0
            for alias in aliases_to_add:
                rows = add_alias(conn, oid, alias)
                if rows > 0:
                    inserted_for_obj += 1
                    total_inserted += 1
                    log(f"  + Insertado alias: {alias}")

            log(f"  [{oid}] {desig}: {inserted_for_obj} alias(es) nuevo(s) insertados")

            done_ids.add(oid)
            cp['done_object_ids'] = list(done_ids)
            cp['done_designations'] = [o[1] for o in objects if o[0] in done_ids]
            cp['aliases_inserted'] = total_inserted
            cp['last_object_id'] = oid
            cp['status'] = 'in_progress'
            save_checkpoint(cp)

            if plan:
                plan['objects_processed'] = len(done_ids)
                plan['aliases_inserted'] = total_inserted
                save_fase2_plan(plan)

        cp['status'] = 'completed'
        cp['finished_at'] = datetime.utcnow().isoformat() + 'Z'
        save_checkpoint(cp)

        if plan:
            plan['status'] = 'completed'
            plan['executed'] = ['aliases']
            # aliases done, rest pending
            plan['pending'] = ['physical_params', 'composition', 'activity']
            plan['finished_at'] = datetime.utcnow().isoformat() + 'Z'
            plan['objects_processed'] = len(objects)
            plan['aliases_inserted'] = total_inserted
            save_fase2_plan(plan)

        elapsed = time.time() - start_time
        log("=" * 60)
        log("FIN FASE 2 CORTA - SOLO ALIASES")
        log(f"Tiempo transcurrido: {elapsed:.1f}s")
        log(f"Objetos procesados: {len(objects)}")
        log(f"Aliases insertados (nuevos): {total_inserted}")
        log("=" * 60)

        # Verificación final
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM object_aliases")
        total_aliases = cur.fetchone()[0]
        log(f"Total aliases en BD: {total_aliases}")

    finally:
        conn.close()


if __name__ == '__main__':
    main()
