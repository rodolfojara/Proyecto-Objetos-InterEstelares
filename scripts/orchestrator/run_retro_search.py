#!/usr/bin/env python3
"""
Fase 4 - Búsqueda retrospectiva (resumable)
Escanea archivos raw en busca de candidatos hiperbólicos (e > 1) con checkpoint/reanudación.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'db', 'iso.db')
RAW_DIR = os.path.join(BASE_DIR, 'data', 'raw')
REPORT_DIR = os.path.join(BASE_DIR, 'reports')
CHECKPOINT_DIR = os.path.join(BASE_DIR, '.metadata_checkpoints')
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, 'fase4_retro_checkpoint.json')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'fase4_retro.log')


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
        "done_files": [],
        "candidates_inserted": 0,
        "hits_found": 0,
        "last_file": None,
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


def scan_file_for_hyperbolic(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    except Exception:
        return []
    results = []
    for m in re.finditer(r'\be\s*[=:]\s*(1\.[0-9]+|[2-9][0-9]*\.[0-9]+)', text, re.IGNORECASE):
        try:
            e_val = float(m.group(1))
            if e_val > 1.0:
                start = max(0, m.start() - 120)
                end = min(len(text), m.end() + 120)
                results.append({
                    'e': e_val,
                    'context': text[start:end].replace('\n', ' ')
                })
        except Exception:
            pass
    return results


def candidate_exists(conn, source_file, e_val, context):
    cur = conn.cursor()
    # Try to avoid exact duplicates by same file and similar e and nearby context snippet
    try:
        cur.execute(
            "SELECT id FROM retro_candidates WHERE source_file = ? AND ABS(COALESCE(e,0) - ?) < 1e-9 LIMIT 1",
            (source_file, e_val)
        )
        row = cur.fetchone()
        if row:
            return True
    except Exception:
        pass
    return False


def main():
    parser = argparse.ArgumentParser(description='Fase 4 - Búsqueda retrospectiva resumable')
    parser.add_argument('--reanudar', action='store_true', help='Reanudar desde checkpoint')
    parser.add_argument('--force', action='store_true', help='Forzar re-ejecución desde cero')
    args = parser.parse_args()

    start_time = time.time()
    log("=" * 60)
    log("INICIO FASE 4 - BÚSQUEDA RETROSPECTIVA")
    log(f"DB: {DB_PATH}")
    log(f"RAW_DIR: {RAW_DIR}")
    log(f"Checkpoint: {CHECKPOINT_FILE}")
    log("=" * 60)

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

    if args.force and os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        log("Checkpoint eliminado por --force")

    cp = load_checkpoint()
    if not args.reanudar and not args.force and cp.get('status') == 'completed':
        log("Ya completado según checkpoint. Usa --force para re-ejecutar o --reanudar para verificar.")
        sys.exit(0)

    conn = get_conn()
    cur = conn.cursor()

    try:
        # Collect all files
        all_files = []
        for root, dirs, files in os.walk(RAW_DIR):
            for fn in files:
                fpath = os.path.join(root, fn)
                all_files.append(fpath)
        all_files.sort()
        log(f"Archivos encontrados en raw: {len(all_files)}")

        done_files = set(cp.get('done_files', []))
        candidates_inserted = cp.get('candidates_inserted', 0)
        hits_found = cp.get('hits_found', 0)
        candidates_found_report = []

        for fpath in all_files:
            if fpath in done_files and not args.force:
                log(f"Saltando (ya procesado): {fpath}")
                continue
            log(f"Escaneando: {fpath}")
            hits = scan_file_for_hyperbolic(fpath)
            if hits:
                log(f"  -> {len(hits)} hit(s) con e>1")
            for h in hits:
                hits_found += 1
                candidates_found_report.append({
                    'file': fpath,
                    'e': h['e'],
                    'context': h['context']
                })
                if candidate_exists(conn, fpath, h['e'], h['context']):
                    log(f"  ~ Duplicado ignorado (e={h['e']}) en {fpath}")
                    continue
                try:
                    cur.execute('''INSERT INTO retro_candidates(provisional_designation, e, source_file, found_by, status, confidence)
                                   VALUES(?,?,?,?,?,?)''',
                                (None, h['e'], fpath, 'historiador', 'pending', 2))
                    conn.commit()
                    candidates_inserted += 1
                    log(f"  + Insertado candidato (e={h['e']}) en retro_candidates")
                except Exception as e:
                    log(f"  ! Error insertando candidato: {e}")
                    conn.rollback()

            done_files.add(fpath)
            cp['done_files'] = sorted(list(done_files))
            cp['candidates_inserted'] = candidates_inserted
            cp['hits_found'] = hits_found
            cp['last_file'] = fpath
            cp['status'] = 'in_progress'
            save_checkpoint(cp)

        cp['status'] = 'completed'
        cp['finished_at'] = datetime.utcnow().isoformat() + 'Z'
        save_checkpoint(cp)

        now = datetime.now()
        report_path = os.path.join(REPORT_DIR, f"retro_search_{now.strftime('%Y-%m-%d_%H-%M-%S')}.md")
        lines = []
        lines.append(f"# Búsqueda retrospectiva - Candidatos hiperbólicos (e > 1)")
        lines.append(f"**Fecha:** {now.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Agente:** historiador (Fase 4 - resumable)")
        lines.append(f"")
        lines.append(f"## Resumen")
        lines.append(f"- Archivos escaneados en: {RAW_DIR}")
        lines.append(f"- Archivos procesados: {len(done_files)}")
        lines.append(f"- Hits encontrados (e>1): {hits_found}")
        lines.append(f"- Nuevos candidatos insertados en BD: {candidates_inserted}")
        lines.append(f"")
        lines.append(f"## Candidatos (muestra)")
        if candidates_found_report:
            for i, c in enumerate(candidates_found_report[:50], 1):
                lines.append(f"### Candidato {i}")
                lines.append(f"- Archivo: {c['file']}")
                lines.append(f"- e: {c['e']}")
                lines.append(f"- Contexto: {c['context']}")
                lines.append(f"")
        else:
            lines.append(f"_Sin candidatos encontrados en archivos raw actuales._")
            lines.append(f"")
        lines.append(f"## Notas")
        lines.append(f"- Ejecución resumable con checkpoint en `.metadata_checkpoints/fase4_retro_checkpoint.json`")
        lines.append(f"- Uso: `python scripts/orchestrator/run_retro_search.py --reanudar` o `--force`")
        lines.append(f"- Todo queda registrado en `retro_candidates` con status='pending'.")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        elapsed = time.time() - start_time
        log("=" * 60)
        log("FIN FASE 4 - BÚSQUEDA RETROSPECTIVA")
        log(f"Tiempo transcurrido: {elapsed:.1f}s")
        log(f"Archivos procesados: {len(done_files)}")
        log(f"Hits encontrados: {hits_found}, insertados nuevos: {candidates_inserted}")
        log(f"Reporte: {report_path}")
        log("=" * 60)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
