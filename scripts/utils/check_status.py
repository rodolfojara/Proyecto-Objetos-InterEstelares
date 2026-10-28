#!/usr/bin/env python3
"""
Status checker for ISO Tracker
"""
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(r"C:/Users/user/Documents/Proyecto Objetos InterEstelares/data/db/iso.db")

def check():
    print("=" * 50)
    print("ISO TRACKER - STATUS CHECK")
    print("=" * 50)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    if not DB_PATH.exists():
        print("ERROR: Base de datos no encontrada")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Objects
    cur.execute("SELECT designation, discovery_date FROM objects ORDER BY discovery_date")
    print("OBJETOS INTERESTELARES:")
    for r in cur.fetchall():
        print(f"  - {r['designation']} (descubierto: {r['discovery_date']})")
    print()
    
    # Tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    print(f"TABLAS EN BD: {len(tables)}")
    print(f"  {', '.join(tables)}")
    print()
    
    # Papers count
    cur.execute("SELECT COUNT(*) as c FROM publications")
    pubs = cur.fetchone()['c']
    print(f"PUBLICACIONES EN BD: {pubs}")
    
    # Retro candidates
    cur.execute("SELECT COUNT(*) as c FROM retro_candidates")
    retro = cur.fetchone()['c']
    print(f"CANDIDATOS RETROSPECTIVOS: {retro}")
    
    # Provenance entries
    cur.execute("SELECT COUNT(*) as c FROM provenance_log")
    prov = cur.fetchone()['c']
    print(f"ENTRADAS EN PROVENANCE_LOG: {prov}")
    print()
    
    conn.close()
    print("=" * 50)

if __name__ == '__main__':
    check()
