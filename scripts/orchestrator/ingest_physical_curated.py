#!/usr/bin/env python3
"""
Ingesta acotada: dimensiones/tamaño estimado (curado desde fuentes públicas) -> physical_params.
Valores con rango/incertidumbre y procedencia explícita. Idempotente por (object_id, param, source_url).
"""
import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'db', 'iso.db')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'ingest_physical_curated.log')


def log(msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


# Registros curados (conservadores, con incertidumbre). Fuentes: NASA Science, JPL, literatura citada.
# object_id: 1=1I, 2=2I, 3=3I
CURATED = [
    # 1I/'Oumuamua
    dict(object_id=1, param='size_estimate', value=None,
         value_text='Longitud estimada ~100–1000 m (altamente incierta); forma muy elongada.',
         unit='m', method='Síntesis de estimaciones fotométricas/modelado (rango amplio por forma/albedo desconocidos).',
         source_url='https://science.nasa.gov/solar-system/comets/oumuamua/', confidence=3),
    dict(object_id=1, param='dimensions_estimate', value=None,
         value_text='Hasta ~400 m de largo; relación de ejes posiblemente ~10:1 (estimación, incierta).',
         unit='m', method='Estimación divulgada por NASA/JPL basada en curva de luz (incertidumbre significativa).',
         source_url='https://science.nasa.gov/solar-system/comets/oumuamua/', confidence=3),
    dict(object_id=1, param='albedo_estimate', value=None,
         value_text='Desconocido/incierto; superficies oscuras tipo asteroidal/cometario han sido propuestas.',
         unit='', method='No medido directamente; inferencias indirectas.',
         source_url='https://science.nasa.gov/solar-system/comets/oumuamua/', confidence=2),
    # 2I/Borisov
    dict(object_id=2, param='nucleus_radius_estimate', value=None,
         value_text='Radio del núcleo estimado ~0.2–0.5 km (límite superior ~≤0.5 km en algunos estudios).',
         unit='km', method='Restricciones por fotometría/HST y actividad (coma dificulta medición directa).',
         source_url='https://science.nasa.gov/solar-system/comets/2i-borisov/', confidence=3),
    dict(object_id=2, param='size_estimate', value=None,
         value_text='Núcleo pequeño, orden sub-km a ~1 km de diámetro equivalente (incierto por coma).',
         unit='km', method='Estimación indirecta; actividad cometaria complica tamaño nuclear.',
         source_url='https://science.nasa.gov/solar-system/comets/2i-borisov/', confidence=3),
    # 3I/ATLAS
    dict(object_id=3, param='nucleus_size_estimate', value=None,
         value_text='Tamaño del núcleo incierto; estimaciones tempranas con rango amplio (sub-km a varios km) sujetas a revisión por observaciones (HST/JWST/sondas).',
         unit='km', method='Restricciones preliminares; coma/actividad y datos en evolución.',
         source_url='https://science.nasa.gov/solar-system/comets/3i-atlas/', confidence=2),
    dict(object_id=3, param='size_estimate', value=None,
         value_text='Diámetro efectivo del núcleo no consolidado; se reportan límites/estimaciones preliminares con alta incertidumbre.',
         unit='km', method='Síntesis preliminar a partir de observaciones tempranas; pendiente de consolidación.',
         source_url='https://science.nasa.gov/solar-system/comets/3i-atlas/', confidence=2),
]


def insert_param(conn, r):
    cur = conn.cursor()
    retrieved_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    try:
        cur.execute(
            """INSERT OR IGNORE INTO physical_params
               (object_id, param, value, value_text, unit, error, method, source_url, retrieved_at, confidence)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (r['object_id'], r['param'], r.get('value'), r.get('value_text'), r.get('unit'),
             None, r.get('method'), r['source_url'], retrieved_at, r.get('confidence', 3))
        )
        conn.commit()
        return cur.rowcount
    except Exception as e:
        log(f"  ! error {r['param']} obj {r['object_id']}: {e}")
        conn.rollback()
        return 0


def main():
    ap = argparse.ArgumentParser(description='Ingesta física curada (dimensiones/tamaño estimado)')
    ap.add_argument('--force', action='store_true', help='Eliminar params curados (source_url science.nasa.gov) para estos objetos y reinsertar')
    args = ap.parse_args()

    start = time.time()
    log("=" * 60)
    log("INICIO INGESTA FÍSICA CURADA (dimensiones/tamaño)")
    log("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    try:
        if args.force:
            cur = conn.cursor()
            cur.execute("DELETE FROM physical_params WHERE source_url LIKE 'https://science.nasa.gov/%' AND param IN ('size_estimate','dimensions_estimate','albedo_estimate','nucleus_radius_estimate','nucleus_size_estimate')")
            conn.commit()
            log(f"Eliminados {cur.rowcount} registros curados previos (--force)")

        total = 0
        for r in CURATED:
            rc = insert_param(conn, r)
            if rc:
                log(f"  + obj {r['object_id']} {r['param']}")
                total += rc
            else:
                log(f"  = obj {r['object_id']} {r['param']} (skip)")
        log(f"FIN | insertados={total} | {time.time()-start:.1f}s")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
