#!/usr/bin/env python3
"""
Ingesta acotada (paso 1): parámetros físicos desde JPL SBDB API -> physical_params.
Idempotente por (object_id, param, source_url). No modifica esquema.
"""
import argparse
import json
import os
import sqlite3
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'db', 'iso.db')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'ingest_physical_sbdb.log')

TARGETS = [
    (1, "1I/'Oumuamua", "1I"),
    (2, "2I/Borisov", "2I"),
    (3, "3I/ATLAS", "3I"),
]

# Mapeo SBDB phys_par name -> (param, unit_fallback, title_fallback)
FIELD_MAP = {
    'H': ('absolute_magnitude_H', 'mag', 'absolute magnitude'),
    'G': ('phase_slope_G', '', 'phase slope parameter'),
    'diameter': ('diameter', 'km', 'diameter'),
    'extent': ('extent', 'km', 'dimensions/extent'),
    'albedo': ('albedo', '', 'geometric albedo'),
    'rot_per': ('rotation_period', 'h', 'rotation period'),
    'GM': ('GM', 'km^3/s^2', 'standard gravitational parameter'),
    'density': ('density', 'g/cm^3', 'bulk density'),
    'M1': ('comet_total_magnitude_M1', 'mag', 'comet total magnitude parameter'),
    'M2': ('comet_nuclear_magnitude_M2', 'mag', 'comet nuclear magnitude parameter'),
    'K1': ('comet_total_mag_slope_K1', '', 'comet total magnitude slope'),
    'K2': ('comet_nuclear_mag_slope_K2', '', 'comet nuclear magnitude slope'),
    'PC': ('photometric_correction_PC', 'mag', 'photometric correction'),
}


def log(msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def fetch_sbdb(sstr):
    url = 'https://ssd-api.jpl.nasa.gov/sbdb.api?sstr=' + urllib.parse.quote(sstr) + '&phys-par=1'
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={'User-Agent': 'ISO-Tracker/1.0 (educational/research)'})
    with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
        return json.loads(r.read().decode('utf-8')), url


def insert_param(conn, object_id, param, value, value_text, unit, method, source_url, confidence):
    cur = conn.cursor()
    retrieved_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    try:
        cur.execute(
            """INSERT OR IGNORE INTO physical_params
               (object_id, param, value, value_text, unit, error, method, source_url, retrieved_at, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (object_id, param, value, value_text, unit, None, method, source_url, retrieved_at, confidence)
        )
        conn.commit()
        return cur.rowcount
    except Exception as e:
        log(f"  ! insert error {param}: {e}")
        conn.rollback()
        return 0


def parse_numeric(val):
    if val is None:
        return None
    try:
        return float(str(val).strip())
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description='Ingesta física acotada desde JPL SBDB')
    ap.add_argument('--force', action='store_true', help='Eliminar params de fuente SBDB para estos objetos y reinsertar')
    args = ap.parse_args()

    start = time.time()
    log("=" * 60)
    log("INICIO INGESTA FÍSICA (JPL SBDB)")
    log("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    try:
        if args.force:
            cur = conn.cursor()
            cur.execute("DELETE FROM physical_params WHERE source_url LIKE 'https://ssd-api.jpl.nasa.gov/sbdb.api%'")
            conn.commit()
            log(f"Eliminados {cur.rowcount} registros SBDB previos (--force)")

        total = 0
        for object_id, designation, sstr in TARGETS:
            log(f"Consultando SBDB: {designation} (sstr={sstr})")
            try:
                data, src = fetch_sbdb(sstr)
            except Exception as e:
                log(f"  ! Error fetch {sstr}: {e}")
                continue
            obj = data.get('object') or {}
            fullname = obj.get('fullname') or obj.get('des') or sstr
            phys = data.get('phys_par') or []
            log(f"  Respuesta: {fullname} | phys_par campos: {len(phys)}")
            if not phys:
                log("  (sin phys_par)")
                continue
            inserted = 0
            for p in phys:
                name = p.get('name')
                if not name or name not in FIELD_MAP:
                    continue
                param, unit_fb, title_fb = FIELD_MAP[name]
                raw_val = p.get('value')
                unit = p.get('units') or unit_fb
                title = p.get('title') or title_fb
                num = parse_numeric(raw_val)
                method = f"JPL SBDB phys_par: {title}"
                # store both numeric (if parseable) and text for fidelity
                rc = insert_param(conn, object_id, param, num, str(raw_val) if raw_val is not None else None, unit, method, src, 4)
                if rc:
                    inserted += rc
                    log(f"  + {param} = {raw_val} {unit}")
                else:
                    log(f"  = {param} ya existe (skip)")
            total += inserted
            log(f"  Insertados para {designation}: {inserted}")
        elapsed = time.time() - start
        log("=" * 60)
        log(f"FIN INGESTA FÍSICA | insertados={total} | {elapsed:.1f}s")
        log("=" * 60)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
