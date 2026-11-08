#!/usr/bin/env python3
"""
Curador de referencias web (complemento a YouTube/papers) - resumable.
Ingesta curada/manual: fuentes confiables primero, luego evaluación referencia por referencia.
Guarda lo que aporta sobre el promedio ("goyita"), incluso si está desactualizado pero bien informado.
Registra TODAS las referencias; las rechazadas quedan con nota/motivo pero NO se muestran en reportes.
NO realiza búsqueda/scraping abierto: solo ingesta URLs listadas/evaluadas en config/web_references.json.
"""
import argparse
import json
import os
import re
import sqlite3
import ssl
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'db', 'iso.db')
REF_LIST = os.path.join(BASE_DIR, 'config', 'web_references.json')
CHECKPOINT_DIR = os.path.join(BASE_DIR, '.metadata_checkpoints')
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, 'web_references_checkpoint.json')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'web_references.log')


def log(msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    line = f"[{ts}] {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        try:
            sys.stdout.buffer.write((line + '\n').encode(sys.stdout.encoding or 'utf-8', 'replace'))
        except Exception:
            print(line.encode('ascii', 'replace').decode('ascii'))
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"Error cargando checkpoint: {e}")
    return {"started_at": datetime.utcnow().isoformat() + 'Z', "done_urls": [], "added": 0, "updated": 0, "linked": 0, "last_url": None, "status": "in_progress"}


def save_checkpoint(cp):
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    cp['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cp, f, indent=2, ensure_ascii=False)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def domain_of(url):
    try:
        host = (urlparse(url).hostname or '').lower()
        return host[4:] if host.startswith('www.') else host
    except Exception:
        return ''


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def fetch_page_meta(url, timeout=15):
    """Validación ligera: accesibilidad + título (sin scraping masivo)."""
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'ISO-Tracker/1.0 (curated reference validation)'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            status = getattr(r, 'status', 200)
            ctype = (r.headers.get('Content-Type') or '').lower()
            body = b''
            if 'text/html' in ctype or 'application/xhtml' in ctype or not ctype:
                body = r.read(65536)
        title = ''
        if body:
            m = re.search(r'<title[^>]*>(.*?)</title>', body.decode('utf-8', 'ignore'), re.I | re.S)
            if m:
                title = re.sub(r'\s+', ' ', m.group(1)).strip()
        return {'ok': True, 'status': status, 'title': title}
    except Exception as e:
        return {'ok': False, 'error': str(e), 'title': ''}


OBJ_HINTS = {
    "1I/'Oumuamua": ['oumuamua', '1i', '1i/2017'],
    '2I/Borisov': ['borisov', '2i', '2i/2019'],
    '3I/ATLAS': ['atlas', '3i', '3i/2025'],
}


def resolve_objects(cur, item, url, title):
    explicit = item.get('objects') or item.get('designations') or []
    if isinstance(explicit, str):
        explicit = [explicit]
    resolved = []
    cur.execute('SELECT id, designation FROM objects')
    objs = cur.fetchall()
    by_des = {str(o[1]).lower(): o[0] for o in objs}
    for d in explicit:
        oid = by_des.get(str(d).lower())
        if oid and oid not in resolved:
            resolved.append(oid)
    if resolved:
        return resolved
    hay = norm(' '.join([url or '', title or '', item.get('summary') or '', item.get('notes') or '', ' '.join(item.get('tags') or [])]))
    for desig, keys in OBJ_HINTS.items():
        if any(k.replace("'", '').replace('/', ' ') in hay or k in (url or '').lower() for k in keys):
            oid = by_des.get(desig.lower())
            if oid and oid not in resolved:
                resolved.append(oid)
    return resolved


def clamp_score(v, lo=1, hi=10):
    if v is None or v == '':
        return None
    try:
        n = int(v)
    except Exception:
        try:
            n = int(float(v))
        except Exception:
            return None
    return max(lo, min(hi, n))


def main():
    parser = argparse.ArgumentParser(description='Curador de referencias web (resumable)')
    parser.add_argument('--reanudar', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--skip-validate', action='store_true', help='Omitir validación HTTP/título')
    args = parser.parse_args()

    start_time = time.time()
    log("=" * 60)
    log("INICIO CURADOR REFERENCIAS WEB")
    log(f"DB: {DB_PATH} | Lista: {REF_LIST}")
    log("=" * 60)

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REF_LIST), exist_ok=True)
    if not os.path.exists(REF_LIST):
        with open(REF_LIST, 'w', encoding='utf-8') as f:
            json.dump({"instructions": "Agregar referencias evaluadas.", "links": []}, f, indent=2, ensure_ascii=False)
        log(f"Creado {REF_LIST}. Agrega referencias evaluadas y vuelve a ejecutar.")
        return

    if args.force and os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        log("Checkpoint eliminado por --force")
    cp = load_checkpoint()
    if not args.reanudar and not args.force and cp.get('status') == 'completed':
        log("Completado según checkpoint. Usa --force o --reanudar.")
        return

    with open(REF_LIST, 'r', encoding='utf-8') as f:
        data = json.load(f)
    links = data.get('links') or data.get('references') or []
    done_urls = set(cp.get('done_urls', []))
    added = cp.get('added', 0)
    updated = cp.get('updated', 0)
    linked_total = cp.get('linked', 0)
    log(f"Elementos en config: {len(links)}")

    conn = get_conn()
    cur = conn.cursor()
    try:
        for item in links:
            url = (item.get('url') or '').strip()
            if not url:
                continue
            if url in done_urls and not args.force:
                continue
            meta = {'ok': None, 'title': ''}
            if not args.skip_validate:
                meta = fetch_page_meta(url)
                if meta.get('ok'):
                    log(f"  [ok] {url} -> {meta.get('title') or '(sin título)'}")
                else:
                    log(f"  ! No accesible/verificable: {url} ({meta.get('error','')})")
            title = item.get('title') or meta.get('title') or ''
            source = item.get('source') or item.get('publisher') or ''
            source_date = item.get('source_date') or item.get('date') or item.get('published_at') or ''
            ref_type = item.get('ref_type') or item.get('type') or 'web'
            summary = item.get('summary') or ''
            evaluation_note = item.get('evaluation_note') or item.get('evaluation') or item.get('why') or ''
            value_score = clamp_score(item.get('value_score') if item.get('value_score') is not None else item.get('value'))
            confidence = clamp_score(item.get('confidence'), 1, 5) or 3
            hist = 1 if item.get('historical_well_informed') or item.get('historical_ok') else 0
            status = (item.get('status') or 'pending').strip().lower()
            if status not in ('pending', 'accepted', 'watch', 'rejected'):
                status = 'pending'
            tags = item.get('tags')
            if isinstance(tags, (list, tuple)):
                tags = ', '.join(str(t) for t in tags)
            notes = item.get('notes') or ''
            dom = domain_of(url)
            prov = item.get('provenance_url') or url
            now = datetime.utcnow().isoformat() + 'Z'
            agent_review = item.get('agent_review')
            if isinstance(agent_review, (dict, list)):
                agent_review = json.dumps(agent_review, ensure_ascii=False)
            agent_suggested_status = item.get('agent_suggested_status')
            agent_suggested_value = clamp_score(item.get('agent_suggested_value'))

            # upsert
            cur.execute('SELECT id FROM curated_references WHERE url=?', (url,))
            row = cur.fetchone()
            if row:
                cur.execute('''UPDATE curated_references SET title=?, source=?, domain=?, source_date=?, ref_type=?, summary=?,
                               evaluation_note=?, value_score=?, confidence=?, historical_well_informed=?, status=?, tags=?,
                               agent_review=COALESCE(?, agent_review), agent_suggested_status=COALESCE(?, agent_suggested_status),
                               agent_suggested_value=COALESCE(?, agent_suggested_value), provenance_url=?, last_checked_at=?, notes=?
                               WHERE url=?''',
                            (title, source, dom, source_date, ref_type, summary, evaluation_note, value_score, confidence, hist, status, tags,
                             agent_review, agent_suggested_status, agent_suggested_value, prov, now if meta.get('ok') else None, notes, url))
                updated += 1
                log(f"  ~ Actualizada: {url} [{status}]")
            else:
                cur.execute('''INSERT INTO curated_references(url,title,source,domain,source_date,ref_type,summary,evaluation_note,value_score,
                               confidence,historical_well_informed,status,tags,agent_review,agent_suggested_status,agent_suggested_value,
                               added_by,provenance_url,retrieved_at,last_checked_at,notes)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                            (url, title, source, dom, source_date, ref_type, summary, evaluation_note, value_score, confidence, hist, status, tags,
                             agent_review, agent_suggested_status, agent_suggested_value, 'curador_referencias_web', prov, now, now if meta.get('ok') else None, notes))
                added += 1
                log(f"  + Agregada: {url} [{status}] value={value_score}")

            obj_ids = resolve_objects(cur, item, url, title)
            for oid in obj_ids:
                cur.execute('INSERT OR IGNORE INTO curated_reference_object_links(ref_id, object_id, relation, confidence) VALUES((SELECT id FROM curated_references WHERE url=?), ?, ?, ?)',
                            (url, oid, item.get('relation') or 'mentions', confidence))
                if cur.rowcount > 0:
                    linked_total += 1
            conn.commit()

            done_urls.add(url)
            cp['done_urls'] = sorted(done_urls)
            cp['added'] = added; cp['updated'] = updated; cp['linked'] = linked_total
            cp['last_url'] = url; cp['status'] = 'in_progress'
            save_checkpoint(cp)

        cp['status'] = 'completed'; cp['finished_at'] = datetime.utcnow().isoformat() + 'Z'
        save_checkpoint(cp)
        log("=" * 60)
        log(f"FIN. {len(done_urls)} procesadas, +{added} nuevas, ~{updated} actualizadas, +{linked_total} vínculos. {time.time()-start_time:.1f}s")
        log("Nota: referencias con status=rejected se guardan (con nota) pero no se muestran en reportes.")
        log("=" * 60)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
