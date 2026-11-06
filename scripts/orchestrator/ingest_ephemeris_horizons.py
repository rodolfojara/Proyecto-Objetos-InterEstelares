#!/usr/bin/env python3
"""
Ingesta acotada (paso 2): efeméride OBSERVER desde JPL Horizons -> observations.
Agrega columnas si faltan (ra, dec, mag, mag_type, delta_au, r_au, notes). Idempotente básica por (object_id, observation_date, type='ephemeris', source_url).
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
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'db', 'iso.db')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'ingest_ephemeris_horizons.log')

TARGETS = [
    (1, "1I/'Oumuamua", "'1I'"),
    (2, "2I/Borisov", "'2I'"),
    (3, "3I/ATLAS", "'3I'"),
]

EXTRA_COLS = [
    ("ra", "TEXT"),
    ("dec", "TEXT"),
    ("mag", "TEXT"),
    ("mag_type", "TEXT"),
    ("delta_au", "REAL"),
    ("r_au", "REAL"),
    ("notes", "TEXT"),
]


def log(msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def ensure_columns(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(observations)")
    existing = {r[1] for r in cur.fetchall()}
    for name, typ in EXTRA_COLS:
        if name not in existing:
            try:
                cur.execute(f"ALTER TABLE observations ADD COLUMN {name} {typ}")
                conn.commit()
                log(f"Columna agregada: observations.{name} {typ}")
            except Exception as e:
                log(f"! No se pudo agregar columna {name}: {e}")
                conn.rollback()


def fetch_horizons(command, date_str):
    # stop must be after start
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        stop = (d + timedelta(days=1)).strftime('%Y-%m-%d')
    except Exception:
        stop = date_str
    params = {
        'format': 'json',
        'COMMAND': command,
        'OBJ_DATA': 'NO',
        'MAKE_EPHEM': 'YES',
        'EPHEM_TYPE': 'OBSERVER',
        'CENTER': "'500@399'",
        'START_TIME': f"'{date_str}'",
        'STOP_TIME': f"'{stop}'",
        'STEP_SIZE': "'1 d'",
        'QUANTITIES': "'1,9,19,20'",
        'CSV_FORMAT': 'YES',
    }
    url = 'https://ssd.jpl.nasa.gov/api/horizons.api?' + urllib.parse.urlencode(params)
    ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={'User-Agent': 'ISO-Tracker/1.0 (educational/research)'})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        return json.loads(r.read().decode('utf-8')), url


def parse_result(result_text):
    # find header and data between $$SOE/$$EOE
    if '$$SOE' not in result_text or '$$EOE' not in result_text:
        return None, None
    pre = result_text.split('$$SOE')[0]
    data_block = result_text.split('$$SOE')[1].split('$$EOE')[0]
    # header: last non-empty line before SOE that looks like CSV header containing Date
    header = None
    for line in reversed(pre.splitlines()):
        s = line.strip()
        if not s:
            continue
        if 'Date' in s and ',' in s:
            header = [h.strip().strip('*').strip() for h in s.split(',')]
            break
    data_lines = [l.strip() for l in data_block.splitlines() if l.strip()]
    if not data_lines:
        return header, None
    row = [c.strip() for c in data_lines[0].split(',')]
    return header, row


def pick(row, header, *keys):
    if not header or not row:
        return None
    hl = [h.lower() for h in header]
    for k in keys:
        kl = k.lower()
        for i, h in enumerate(hl):
            if kl in h:
                if i < len(row):
                    v = row[i].strip()
                    return v if v not in ('', 'n.a.', 'n.a', '--') else None
    return None


def to_float(v):
    if v is None: return None
    try: return float(str(v).strip())
    except: return None


def main():
    ap = argparse.ArgumentParser(description='Ingesta efeméride Horizons (ubicación/magnitud aprox)')
    ap.add_argument('--date', default=datetime.now(timezone.utc).strftime('%Y-%m-%d'), help='Fecha UTC YYYY-MM-DD (default: hoy)')
    ap.add_argument('--force', action='store_true', help='Eliminar efemérides (type=ephemeris) de esa fecha para estos objetos')
    args = ap.parse_args()

    start = time.time()
    log("=" * 60)
    log(f"INICIO INGESTA EFEMÉRIDES HORIZONS | fecha={args.date}")
    log("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_columns(conn)
        cur = conn.cursor()
        if args.force:
            cur.execute("DELETE FROM observations WHERE type='ephemeris' AND observation_date=? AND source_url LIKE '%horizons.api%'", (args.date,))
            conn.commit()
            log(f"Eliminadas {cur.rowcount} efemérides previas (--force)")

        inserted = 0
        for object_id, designation, command in TARGETS:
            log(f"Consultando Horizons: {designation} @ {args.date}")
            try:
                data, src = fetch_horizons(command, args.date)
            except Exception as e:
                log(f"  ! Error: {e}")
                continue
            if data.get('error'):
                log(f"  ! Horizons error: {data.get('error')}")
                continue
            result = data.get('result', '')
            header, row = parse_result(result)
            if not row:
                log("  ! Sin datos SOE/EOE")
                continue
            ra = pick(row, header, 'R.A.', 'RA')
            dec = pick(row, header, 'DEC', 'Dec')
            mag = pick(row, header, 'APmag', 'T-mag', 'N-mag')
            mag_type = 'APmag (efeméride)' if mag else None
            delta = to_float(pick(row, header, 'delta'))
            rhel = None
            if header:
                for i, h in enumerate(header):
                    hl = h.lower().replace('_', ' ').strip()
                    # heliocentric range often labeled 'r' or 'helio range' (qty 19)
                    if hl in ('r', 'r (au)') or ('helio' in hl and 'range' in hl):
                        rhel = to_float(row[i]) if i < len(row) else None
                        if rhel is not None:
                            break
            if rhel is None:
                rhel = to_float(pick(row, header, 'helio. range', 'heliocentric'))
            notes = f"Efeméride OBSERVER geocéntrica (Horizons) para {args.date} UTC; ubicación aproximada (no observación astrométrica registrada)."
            retrieved_at = datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
            try:
                cur.execute(
                    """INSERT OR IGNORE INTO observations
                       (object_id, telescope, instrument, observation_date, type, data_uri, source_url, retrieved_at, ra, dec, mag, mag_type, delta_au, r_au, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (object_id, 'JPL Horizons', 'ephemeris', args.date, 'ephemeris', None, src, retrieved_at, ra, dec, mag, mag_type, delta, rhel, notes)
                )
                conn.commit()
                if cur.rowcount:
                    inserted += 1
                    log(f"  + RA={ra} Dec={dec} mag={mag} delta={delta} r={rhel}")
                else:
                    log("  = ya existe (skip)")
            except Exception as e:
                log(f"  ! insert: {e}")
                conn.rollback()
        elapsed = time.time() - start
        log("=" * 60)
        log(f"FIN INGESTA EFEMÉRIDES | insertados={inserted} | {elapsed:.1f}s")
        log("=" * 60)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
