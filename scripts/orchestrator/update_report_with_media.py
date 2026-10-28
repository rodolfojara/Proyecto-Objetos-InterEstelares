#!/usr/bin/env python3
"""
Update/generate report with multimedia resources section
"""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares/data/db/iso.db")
REPORT_DIR = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares/reports/weekly")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate():
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d_%H-%M-%S')
    
    # Get media with objects
    cur.execute('''
        SELECT m.url, m.title, m.channel, m.relevance_score, m.notes, o.designation
        FROM media_resources m
        LEFT JOIN media_object_links mol ON m.id = mol.media_id
        LEFT JOIN objects o ON mol.object_id = o.id
        ORDER BY m.relevance_score DESC, m.added_at DESC
    ''')
    media = cur.fetchall()
    
    report_path = REPORT_DIR / f"ISO_Report_with_Media_{date_str}.md"
    lines = []
    lines.append(f"# ISO Tracker Report - Con Recursos Audiovisuales")
    lines.append(f"")
    lines.append(f"**Fecha de generación:** {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")
    
    lines.append(f"## Recursos audiovisuales complementarios (YouTube)")
    lines.append(f"")
    lines.append(f"Estos vídeos han sido añadidos por el **curador_multimedia** para complementar la información del sistema.")
    lines.append(f"")
    
    if media:
        lines.append(f"| URL | Objeto(s) | Título/Notas | Relevancia |")
        lines.append(f"| :-- | :-- | :-- | :--: |")
        for m in media:
            title = m['title'] or m['notes'] or 'N/A'
            obj = m['designation'] or 'General/Comparativo'
            lines.append(f"| [{m['url']}]({m['url']}) | {obj} | {title} | {m['relevance_score']} |")
        lines.append(f"")
    else:
        lines.append(f"_No hay vídeos añaddidos aún. Edita `config/media_links.json` y ejecuta `scripts/orchestrator/curate_media.py`._")
        lines.append(f"")
    
    lines.append(f"---")
    lines.append(f"")
    lines.append(f"## Complemento con datos del sistema")
    lines.append(f"")
    cur.execute("SELECT designation, discovery_date FROM objects ORDER BY discovery_date")
    for o in cur.fetchall():
        lines.append(f"- **{o['designation']}** - Descubierto: {o['discovery_date']}")
    lines.append(f"")
    lines.append(f"_Los vídeos enlazados se complementan con los datos orbitales, actividad y evolución registrados en la base de datos._")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    conn.close()
    print(f'Report with media generated: {report_path}')

if __name__ == '__main__':
    generate()
