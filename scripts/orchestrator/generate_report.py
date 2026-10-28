#!/usr/bin/env python3
"""
ISO Tracker - Report Generator (Fase 3)
Generates comprehensive report with all required metrics.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares/data/db/iso.db")
REPORT_DIR = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares/reports/weekly")
FIG_DIR = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares/reports/figures")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

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
    # Try to find earliest publication date per object
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

def generate_report():
    conn = get_conn()
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d_%H-%M-%S')
    
    objects = get_objects_summary(conn)
    paper_counts = count_papers_by_object(conn)
    first_dates = first_report_dates(conn)
    
    report_path = REPORT_DIR / f"ISO_Report_{date_str}.md"
    
    lines = []
    lines.append(f"# ISO Tracker Report")
    lines.append(f"")
    lines.append(f"**Fecha de generación:** {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Sistema:** ISO Tracking System - Fase 3")
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
    lines.append(f"- **Generado por:** scripts/orchestrator/generate_report.py (Fase 3)")
    lines.append(f"- **Base de datos:** {DB_PATH}")
    lines.append(f"- **Nota:** Este reporte usa datos actualmente en la BD. A medida que se ingieran más papers/observaciones, las métricas se actualizarán.")
    lines.append(f"")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    conn.close()
    print(f'Report generated: {report_path}')
    return report_path

if __name__ == '__main__':
    generate_report()
