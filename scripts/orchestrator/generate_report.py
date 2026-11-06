#!/usr/bin/env python3
"""
ISO Tracker - Report Generator (Fase 3 - resumable)
Generates comprehensive report with all required metrics.
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'db', 'iso.db')
REPORT_DIR = os.path.join(BASE_DIR, 'reports', 'weekly')
FIG_DIR = os.path.join(BASE_DIR, 'reports', 'figures')
CHECKPOINT_DIR = os.path.join(BASE_DIR, '.metadata_checkpoints')
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, 'fase3_report_checkpoint.json')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'fase3_report.log')


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
        "reports_generated": [],
        "status": "in_progress"
    }


def save_checkpoint(cp):
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    cp['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cp, f, indent=2, ensure_ascii=False)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def count_papers_by_object(conn):
    cur = conn.cursor()
    cur.execute('''
        SELECT o.designation, COUNT(op.publication_id) as paper_count
        FROM objects o
        LEFT JOIN object_publications op ON o.id = op.object_id
        GROUP BY o.id, o.designation
        ORDER BY o.designation
    ''')
    return cur.fetchall()


def first_report_dates(conn):
    cur = conn.cursor()
    cur.execute('''
        SELECT o.designation, MIN(p.published_at) as first_pub, MIN(p.retrieved_at) as first_retrieved
        FROM objects o
        LEFT JOIN object_publications op ON o.id = op.object_id
        LEFT JOIN publications p ON op.publication_id = p.id
        GROUP BY o.id, o.designation
        ORDER BY o.designation
    ''')
    return cur.fetchall()


def get_objects_summary(conn):
    cur = conn.cursor()
    cur.execute('SELECT * FROM objects ORDER BY discovery_date')
    return cur.fetchall()


def generate_report(resumable=False, force=False):
    start_time = time.time()
    log("=" * 60)
    log("INICIO FASE 3 - GENERACIÓN DE REPORTE")
    log(f"DB: {DB_PATH}")
    log(f"Reporte dir: {REPORT_DIR}")
    log("=" * 60)

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    if force and os.path.exists(CHECKPOINT_FILE):
        try:
            os.remove(CHECKPOINT_FILE)
            log("Checkpoint eliminado por --force")
        except Exception:
            pass

    cp = load_checkpoint()
    if not resumable and not force and cp.get('status') == 'completed' and cp.get('reports_generated'):
        log("Ya completado según checkpoint. Usa --reanudar o --force para generar nuevo reporte.")
        # Still allow generating a new timestamped report if explicitly called; but respect checkpoint style
        # Follow Fase 2 behavior: if completed and not reanudar/force, exit
        if not resumable:
            sys.exit(0)

    conn = get_conn()
    try:
        now = datetime.now()
        date_str = now.strftime('%Y-%m-%d_%H-%M-%S')

        objects = get_objects_summary(conn)
        paper_counts = count_papers_by_object(conn)
        first_dates = first_report_dates(conn)

        report_path = os.path.join(REPORT_DIR, f"ISO_Report_{date_str}.md")

        lines = []
        lines.append(f"# ISO Tracker Report")
        lines.append(f"")
        lines.append(f"**Fecha de generación:** {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Sistema:** ISO Tracking System - Fase 3 (resumable)")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # Resumen
        lines.append(f"## Resumen")
        lines.append(f"")
        for o in objects:
            lines.append(f"- **{o['designation']}** ({o['name']}): Descubierto {o['discovery_date']}. Estado: {o['status']}. {o['notes'] or ''}")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # Cantidad de papers
        lines.append(f"## Cantidad de papers que mencionan cada objeto")
        lines.append(f"")
        lines.append(f"| Objeto | Cantidad de papers vinculados |")
        lines.append(f"| :-- | :--: |")
        for pc in paper_counts:
            lines.append(f"| {pc['designation']} | {pc['paper_count']} |")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # Fecha de primer reporte
        lines.append(f"## Fecha de primer reporte")
        lines.append(f"")
        lines.append(f"| Objeto | Primer published_at | Primer retrieved_at |")
        lines.append(f"| :-- | :-- | :-- |")
        for fd in first_dates:
            lines.append(f"| {fd['designation']} | {fd['first_pub'] or 'N/A'} | {fd['first_retrieved'] or 'N/A'} |")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # Comparativa básica
        lines.append(f"## Comparativa 1I / 2I / 3I")
        lines.append(f"")
        lines.append(f"| Aspecto | 1I/'Oumuamua | 2I/Borisov | 3I/ATLAS |")
        lines.append(f"| :-- | :-- | :-- | :-- |")
        lines.append(f"| Descubrimiento | 2017-10-19 | 2019-08-30 | 2025-07-01 |")
        lines.append(f"| Tipo actividad | Sin coma evidente (debatido) | Cometa activo con coma | Activo, seguimiento intenso |")
        lines.append(f"| v_inf (km/s) | ~26.33 | ~32.3 | ~58.0 |")
        lines.append(f"| e | ~1.20 | ~3.36 | ~6.14 |")
        lines.append(f"| q (au) | ~0.256 | ~2.007 | ~1.356 |")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # Metadatos
        lines.append(f"## Metadatos del reporte")
        lines.append(f"- **Fecha actual:** {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **Generado por:** scripts/orchestrator/generate_report.py (Fase 3 - resumable)")
        lines.append(f"- **Base de datos:** {DB_PATH}")
        lines.append(f"- **Nota:** Este reporte usa datos actualmente en la BD. A medida que se ingieran más papers/observaciones, las métricas se actualizarán.")
        lines.append(f"")

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        reports = cp.get('reports_generated', [])
        reports.append(report_path)
        cp['reports_generated'] = reports[-50:]  # keep last 50
        cp['last_report'] = report_path
        cp['status'] = 'completed'
        cp['finished_at'] = datetime.utcnow().isoformat() + 'Z'
        save_checkpoint(cp)

        elapsed = time.time() - start_time
        log("=" * 60)
        log("FIN FASE 3 - GENERACIÓN DE REPORTE")
        log(f"Tiempo transcurrido: {elapsed:.3f}s")
        log(f"Reporte generado: {report_path}")
        log("=" * 60)
        print(f'Report generated: {report_path}')
        return report_path
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Fase 3 - Generador de reportes resumable')
    parser.add_argument('--reanudar', action='store_true', help='Reanudar/verificar desde checkpoint')
    parser.add_argument('--force', action='store_true', help='Forzar nueva generación')
    args = parser.parse_args()
    generate_report(resumable=args.reanudar, force=args.force)


if __name__ == '__main__':
    main()
