#!/usr/bin/env python3
"""
Fase 6 - Multimedia curator
Add YouTube links manually or from search results
"""
import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs

DB_PATH = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares/data/db/iso.db")
MEDIA_LIST = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares/config/media_links.json")

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
    except:
        pass
    return None

def main():
    conn = get_conn()
    cur = conn.cursor()
    
    # Create default config if not exists
    if not MEDIA_LIST.exists():
        default = {
            "links": [
                {"url": "https://www.youtube.com/results?search_query=1I+Oumuamua+explained", "note": "search example - replace with actual video URLs"},
                {"url": "https://www.youtube.com/results?search_query=2I+Borisov+comet", "note": "search example"},
                {"url": "https://www.youtube.com/results?search_query=3I+ATLAS+interstellar+object", "note": "search example"}
            ],
            "instructions": "Replace search result pages with actual video URLs (https://www.youtube.com/watch?v=...)"
        }
        MEDIA_LIST.parent.mkdir(parents=True, exist_ok=True)
        with open(MEDIA_LIST, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=2)
        print(f"Created {MEDIA_LIST}. Edit with actual video URLs and run again.")
        conn.close()
        return
    
    with open(MEDIA_LIST, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    added = 0
    for item in data.get('links', []):
        url = item.get('url','').strip()
        if not url or 'results?search_query' in url:
            continue  # skip search pages
        if 'youtube.com/watch' not in url and 'youtu.be' not in url:
            continue
        vid = extract_video_id(url)
        try:
            cur.execute('''INSERT OR IGNORE INTO media_resources(type,url,video_id,title,channel,relevance_score,added_by,provenance_url,notes)
                           VALUES(?,?,?,?,?,?,?,?,?)''',
                        ('youtube', url, vid, item.get('title'), item.get('channel'), item.get('relevance_score',3), 
                         'curador_multimedia', url, item.get('notes','')))
            if cur.rowcount > 0:
                added += 1
                # Try to link to objects based on keywords
                cur.execute('SELECT id, designation FROM objects')
                for obj in cur.fetchall():
                    desc = (url + ' ' + str(item.get('title','')) + ' ' + str(item.get('notes',''))).lower()
                    desig = obj[1].lower()
                    if 'oumuamua' in desc and 'oumuamua' in desig or 'borisov' in desc and 'borisov' in desig or 'atlas' in desc and 'atlas' in desig or '1i' in desc and '1i' in desig or '2i' in desc and '2i' in desig or '3i' in desc and '3i' in desig:
                        cur.execute('INSERT OR IGNORE INTO media_object_links(media_id, object_id, relation, confidence) VALUES((SELECT id FROM media_resources WHERE url=?), ?, ?, ?)',
                                    (url, obj[0], 'mentions', 3))
        except Exception as e:
            print(f'ERR {url}: {e}')
    
    conn.commit()
    conn.close()
    print(f'Media curation done. Added {added} new videos.')

if __name__ == '__main__':
    main()
