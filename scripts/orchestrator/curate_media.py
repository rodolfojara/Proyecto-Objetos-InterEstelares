#!/usr/bin/env python3
"""
Fase 6 - Multimedia curator (resumable)
Add YouTube links manually or from search results with checkpoint/reanudación
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
from pathlib import Path
from urllib.parse import urlparse, parse_qs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'db', 'iso.db')
MEDIA_LIST = os.path.join(BASE_DIR, 'config', 'media_links.json')
CHECKPOINT_DIR = os.path.join(BASE_DIR, '.metadata_checkpoints')
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, 'fase6_media_checkpoint.json')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'fase6_media.log')


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
        "done_urls": [],
        "added": 0,
        "linked": 0,
        "last_url": None,
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


def extract_video_id(url):
    try:
        if 'youtu.be' in url:
            return url.split('/')[-1].split('?')[0]
        parsed = urlparse(url)
        if parsed.hostname in ['www.youtube.com', 'youtube.com']:
            qs = parse_qs(parsed.query)
            if 'v' in qs:
                return qs['v'][0]
    except Exception:
        pass
    return None


def fetch_oembed(url, timeout=20):
    """Obtiene metadatos reales del video vía YouTube oEmbed (validación)."""
    try:
        api = 'https://www.youtube.com/oembed?format=json&url=' + urllib.parse.quote(url, safe='')
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(api, headers={'User-Agent': 'ISO-Tracker/1.0 (media validation)'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            data = json.loads(r.read().decode('utf-8'))
        return {
            'title': (data.get('title') or '').strip(),
            'author_name': (data.get('author_name') or '').strip(),
            'provider': data.get('provider_name') or '',
        }
    except Exception as e:
        log(f"  ! oEmbed no disponible para {url}: {e}")
        return None


def _norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def relevance_hint(text):
    t = _norm(text)
    keys = ['oumuamua', 'borisov', 'atlas', '1i', '2i', '3i', 'interstellar', 'interestelar', 'comet', 'asteroid']
    return any(k in t for k in keys)


def main():
    parser = argparse.ArgumentParser(description='Fase 6 - Multimedia curator resumable')
    parser.add_argument('--reanudar', action='store_true', help='Reanudar desde checkpoint')
    parser.add_argument('--force', action='store_true', help='Forzar re-ejecución desde cero')
    parser.add_argument('--skip-validate', action='store_true', help='Omitir validación oEmbed (no recomendado)')
    args = parser.parse_args()

    start_time = time.time()
    log("=" * 60)
    log("INICIO FASE 6 - CURADOR MULTIMEDIA")
    log(f"DB: {DB_PATH}")
    log(f"Media list: {MEDIA_LIST}")
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

    conn = get_conn()
    cur = conn.cursor()

    try:
        # Create default config if not exists
        if not os.path.exists(MEDIA_LIST):
            os.makedirs(os.path.dirname(MEDIA_LIST), exist_ok=True)
            default = {
                "links": [
                    {"url": "https://www.youtube.com/results?search_query=1I+Oumuamua+explained", "note": "search example - replace with actual video URLs"},
                    {"url": "https://www.youtube.com/results?search_query=2I+Borisov+comet", "note": "search example"},
                    {"url": "https://www.youtube.com/results?search_query=3I+ATLAS+interstellar+object", "note": "search example"}
                ],
                "instructions": "Replace search result pages with actual video URLs (https://www.youtube.com/watch?v=...)"
            }
            with open(MEDIA_LIST, 'w', encoding='utf-8') as f:
                json.dump(default, f, indent=2)
            log(f"Creado {MEDIA_LIST}. Edita con URLs reales y vuelve a ejecutar.")
            cp['status'] = 'completed'
            cp['finished_at'] = datetime.utcnow().isoformat() + 'Z'
            save_checkpoint(cp)
            conn.close()
            return

        with open(MEDIA_LIST, 'r', encoding='utf-8') as f:
            data = json.load(f)

        done_urls = set(cp.get('done_urls', []))
        added = cp.get('added', 0)
        linked_total = cp.get('linked', 0)

        links = data.get('links', [])
        log(f"Elementos en media_links.json: {len(links)}")

        for item in links:
            url = (item.get('url') or '').strip()
            if not url:
                continue
            if url in done_urls and not args.force:
                log(f"Saltando (ya procesado): {url}")
                continue
            if 'results?search_query' in url:
                log(f"Omitiendo página de resultados: {url}")
                done_urls.add(url)
                cp['done_urls'] = sorted(list(done_urls))
                cp['last_url'] = url
                cp['status'] = 'in_progress'
                save_checkpoint(cp)
                continue
            if 'youtube.com/watch' not in url and 'youtu.be' not in url:
                log(f"Omitiendo URL no soportada: {url}")
                done_urls.add(url)
                cp['done_urls'] = sorted(list(done_urls))
                cp['last_url'] = url
                cp['status'] = 'in_progress'
                save_checkpoint(cp)
                continue

            vid = extract_video_id(url)
            oembed = None
            if not args.skip_validate:
                oembed = fetch_oembed(url)
            cfg_title = item.get('title') or ''
            cfg_channel = item.get('channel') or ''
            real_title = (oembed.get('title') if oembed else '') or cfg_title
            real_channel = (oembed.get('author_name') if oembed else '') or cfg_channel
            notes = item.get('notes', '') or ''
            if oembed:
                log(f"  [validado] título real: {real_title} | canal: {real_channel}")
                if not relevance_hint(real_title + ' ' + real_channel):
                    log(f"  ! ALERTA: el título/canal no parece relacionado con objetos interestelares. Revisar: {url}")
                if cfg_title and _norm(cfg_title) and _norm(cfg_title) not in _norm(real_title) and _norm(real_title) not in _norm(cfg_title):
                    # if config had a specific (non-generic) title that doesn't match, warn
                    if 'video relacionado' not in _norm(cfg_title):
                        log(f"  ! ALERTA: título config difiere del real. Config='{cfg_title}' Real='{real_title}'")
            elif not args.skip_validate:
                log(f"  ! Validación oEmbed falló; se usará metadata del config (revisar manualmente).")
            try:
                cur.execute('''INSERT OR IGNORE INTO media_resources(type,url,video_id,title,channel,relevance_score,added_by,provenance_url,notes)
                               VALUES(?,?,?,?,?,?,?,?,?)''',
                            ('youtube', url, vid, real_title, real_channel, item.get('relevance_score', 3),
                             'curador_multimedia', url, notes))
                if cur.rowcount > 0:
                    added += 1
                    log(f"  + Añadido media_resource: {url}")
                else:
                    log(f"  ~ Ya existe en media_resources: {url}")
                    # refrescar metadata validada
                    if oembed:
                        cur.execute('UPDATE media_resources SET title=?, channel=? WHERE url=? AND (title IS NULL OR title!=? OR channel IS NULL OR channel!=?)',
                                    (real_title, real_channel, url, real_title, real_channel))
                # Try to link to objects based on keywords (usar título/canal verificados)
                cur.execute('SELECT id, designation FROM objects')
                for obj in cur.fetchall():
                    desc = (url + ' ' + str(real_title) + ' ' + str(real_channel) + ' ' + str(notes)).lower()
                    desig = str(obj[1]).lower()
                    linked = False
                    if ('oumuamua' in desc and 'oumuamua' in desig) or ('borisov' in desc and 'borisov' in desig) or \
                       ('atlas' in desc and 'atlas' in desig) or ('1i' in desc and '1i' in desig) or \
                       ('2i' in desc and '2i' in desig) or ('3i' in desc and '3i' in desig):
                        cur.execute('INSERT OR IGNORE INTO media_object_links(media_id, object_id, relation, confidence) VALUES((SELECT id FROM media_resources WHERE url=?), ?, ?, ?)',
                                    (url, obj[0], 'mentions', 3))
                        if cur.rowcount > 0:
                            linked_total += 1
                            linked = True
                    if linked:
                        pass
                conn.commit()
            except Exception as e:
                log(f"ERR {url}: {e}")
                conn.rollback()

            done_urls.add(url)
            cp['done_urls'] = sorted(list(done_urls))
            cp['added'] = added
            cp['linked'] = linked_total
            cp['last_url'] = url
            cp['status'] = 'in_progress'
            save_checkpoint(cp)

        cp['status'] = 'completed'
        cp['finished_at'] = datetime.utcnow().isoformat() + 'Z'
        save_checkpoint(cp)

        elapsed = time.time() - start_time
        log("=" * 60)
        log("FIN FASE 6 - CURADOR MULTIMEDIA")
        log(f"Tiempo transcurrido: {elapsed:.1f}s")
        log(f"URLs procesadas: {len(done_urls)}")
        log(f"Nuevos añadidos: {added}, nuevos enlaces: {linked_total}")
        log("=" * 60)
    finally:
        conn.close()


if __name__ == '__main__':
    main()
