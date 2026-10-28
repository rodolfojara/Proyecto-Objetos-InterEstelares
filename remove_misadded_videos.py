#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:/Users/user/Documents/Proyecto predeterminado/data/db/iso.db")
VIDEO_IDS = ['UTJk2ZGaxaA', 'WjDVFJobYTY', 'dlali9WWqDI']

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Remove links first
for vid in VIDEO_IDS:
    cur.execute('''DELETE FROM media_object_links 
                   WHERE media_id IN (SELECT id FROM media_resources WHERE video_id = ?)''', (vid,))
    cur.execute('DELETE FROM media_resources WHERE video_id = ?', (vid,))

conn.commit()
conn.close()
print('Removed incorrectly added videos')
