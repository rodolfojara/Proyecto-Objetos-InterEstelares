#!/usr/bin/env python3
"""
Fase 4 - Retrospective search orchestrator (skeleton)
Scans raw files for hyperbolic candidates (e > 1)
"""
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime

DB_PATH = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares/data/db/iso.db")
RAW_DIR = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares/data/raw")
REPORT_DIR = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def scan_file_for_hyperbolic(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    except:
        return []
    results = []
    for m in re.finditer(r'\be\s*[=:]\s*(1\.[0-9]+|[2-9][0-9]*\.[0-9]+)', text, re.IGNORECASE):
        try:
            e_val = float(m.group(1))
            if e_val > 1.0:
                start = max(0, m.start()-120)
                end = min(len(text), m.end()+120)
                results.append({
                    'e': e_val,
                    'context': text[start:end].replace('\n',' ')
                })
        except:
            pass
    return results

def main():
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.now()
    candidates_found = []
    
    # Scan all files in data/raw
    for root, dirs, files in os_walk(RAW_DIR):
        for fn in files:
            fpath = Path(root) / fn
            hits = scan_file_for_hyperbolic(fpath)
            for h in hits:
                candidates_found.append({
                    'file': str(fpath),
                    'e': h['e'],
                    'context': h['context']
                })
                # Insert candidate if not duplicate (simple check)
                cur.execute('''INSERT INTO retro_candidates(provisional_designation, e, source_file, found_by, status, confidence)
                               VALUES(?,?,?,?,?,?)''',
                            (None, h['e'], str(fpath), 'historiador', 'pending', 2))
    
    conn.commit()
    report_path = REPORT_DIR / f"retro_search_{now.strftime('%Y-%m-%d_%H-%M-%S')}.md"
    lines = []
    lines.append(f"# Búsqueda retrospectiva - Candidatos hiperbólicos (e > 1)")
    lines.append(f"**Fecha:** {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Agente:** historiador (Fase 4)")
    lines.append(f"")
    lines.append(f"## Resumen")
    lines.append(f"- Archivos escaneados en: {RAW_DIR}")
    lines.append(f"- Candidatos encontrados (hits): {len(candidates_found)}")
    lines.append(f"")
    lines.append(f"## Candidatos")
    if candidates_found:
        for i, c in enumerate(candidates_found[:50], 1):
            lines.append(f"### Candidato {i}")
            lines.append(f"- Archivo: {c['file']}")
            lines.append(f"- e: {c['e']}")
            lines.append(f"- Contexto: {c['context']}")
            lines.append(f"")
    else:
        lines.append(f"_Sin candidatos encontrados en archivos raw actuales._")
        lines.append(f"")
    lines.append(f"## Notas")
    lines.append(f"- Muchos candidatos con e>1 son artefactos o errores de cálculo. Requiere revisión manual.")
    lines.append(f"- Si se identifica un candidato viable, seguir lógica Fase 2: verificar aliases y crear objeto si no existe.")
    lines.append(f"- Todo queda registrado en `retro_candidates` con status='pending'.")
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    conn.close()
    print(f'Retro search done. Report: {report_path}. Candidates: {len(candidates_found)}')

def os_walk(path):
    import os
    return os.walk(path)

if __name__ == '__main__':
    main()
