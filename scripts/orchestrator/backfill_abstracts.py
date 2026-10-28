"""Completa o refresca abstracts de publications ya cargadas.

Solo escribe `publications.abstract`; no toca ningun otro campo.
Fuentes: arXiv (pagina abs) y, si no hay arXiv, Crossref (registro del DOI).

Uso:
    python scripts/orchestrator/backfill_abstracts.py --dry-run
    python scripts/orchestrator/backfill_abstracts.py
    python scripts/orchestrator/backfill_abstracts.py --refrescar-cortos 200
"""

import json
import os
import re
import sqlite3
import ssl
import sys
import time
import urllib.parse
import urllib.request

from metadata_discovery import limpiar_abstract, limpiar_html

BASE = r'C:/Users/user/Documents/Proyecto Objetos InterEstelares'
DB = BASE + '/data/db/iso.db'
CA_BUNDLE = r'C:/Program Files/Git/usr/ssl/certs/ca-bundle.crt'
CTX = ssl.create_default_context(cafile=CA_BUNDLE) if os.path.exists(CA_BUNDLE) else ssl.create_default_context()
MAILTO = 'rodolfojara@users.noreply.github.com'
MAX_ABSTRACT = 4000


def get(url, cabeceras=None, intentos=4):
    ultimo = None
    for i in range(intentos):
        req = urllib.request.Request(url, headers=cabeceras or {
            'User-Agent': 'ISO-Tracker/0.1 (abstract backfill; %s)' % MAILTO})
        try:
            with urllib.request.urlopen(req, timeout=90, context=CTX) as r:
                return r.read()
        except Exception as e:
            ultimo = e
            time.sleep(3 * (i + 1))
    raise ultimo


def abstract_arxiv(arxiv_id):
    pagina = get('https://arxiv.org/abs/%s' % arxiv_id, cabeceras={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ISO-Tracker/0.1'})
    texto = pagina.decode('utf-8', 'replace')
    m = re.search(r'<blockquote class="abstract[^"]*">(.*?)</blockquote>', texto, re.S)
    if not m:
        return None
    return limpiar_abstract(limpiar_html(m.group(1)))[:MAX_ABSTRACT] or None


def abstract_crossref(doi):
    url = 'https://api.crossref.org/works/' + urllib.parse.quote(doi) + '?' + urllib.parse.urlencode({
        'mailto': MAILTO})
    datos = json.loads(get(url))
    abstract = limpiar_abstract(limpiar_html((datos.get('message') or {}).get('abstract') or ''))
    return abstract[:MAX_ABSTRACT] or None


def obtener(doi, arxiv_id):
    """Devuelve (abstract, origen) probando arXiv y luego Crossref."""
    if arxiv_id:
        try:
            abstract = abstract_arxiv(arxiv_id)
            if abstract:
                return abstract, 'https://arxiv.org/abs/%s' % arxiv_id
        except Exception as e:
            print('  ! arXiv fallo (%s): %r' % (arxiv_id, e))
    if doi and not doi.startswith('10.48550/'):
        try:
            abstract = abstract_crossref(doi)
            if abstract:
                return abstract, 'https://doi.org/' + doi
        except Exception as e:
            print('  ! Crossref fallo (%s): %r' % (doi, e))
    return None, None


def guardar(con, dry, pid, abstract, origen, detalle):
    if dry:
        return
    con.execute('UPDATE publications SET abstract = ? WHERE id = ?', (abstract, pid))
    con.execute(
        "INSERT INTO provenance_log (entity, entity_id, action, source_url, agent, details) "
        "VALUES ('publications', ?, 'update', ?, 'recolector', ?)",
        (pid, origen, detalle))


def rellenar_vacios(con, dry):
    filas = con.execute(
        "SELECT id, doi, arxiv_id, title FROM publications "
        "WHERE abstract IS NULL OR trim(abstract) = ''").fetchall()
    print('publications sin abstract: %d' % len(filas))

    cambios = 0
    for pid, doi, arxiv_id, titulo in filas:
        abstract, origen = obtener(doi, arxiv_id)
        if not abstract:
            print('  - sin datos: %s' % (titulo or '')[:70])
            continue
        print('  + %-40s %s' % ((titulo or '')[:40], abstract[:60] + '...'))
        guardar(con, dry, pid, abstract, origen, 'abstract completado (pase de metadatos)')
        cambios += 1
        time.sleep(2)
    return cambios


def refrescar_cortos(con, dry, minimo=200):
    """Reemplaza abstracts truncados por la version completa de arXiv o Crossref."""
    filas = con.execute(
        "SELECT id, doi, arxiv_id, title, abstract FROM publications "
        "WHERE abstract IS NOT NULL AND length(trim(abstract)) < ?", (minimo,)).fetchall()
    print('publications con abstract < %d caracteres: %d' % (minimo, len(filas)))

    cambios = 0
    for pid, doi, arxiv_id, titulo, actual in filas:
        abstract, origen = obtener(doi, arxiv_id)
        if not abstract or len(abstract) <= len(actual or ''):
            print('  - sin mejora (%d car.): %s' % (len(actual or ''), (titulo or '')[:60]))
            continue
        print('  + %-40s %d -> %d caracteres' % ((titulo or '')[:40], len(actual or ''), len(abstract)))
        guardar(con, dry, pid, abstract, origen,
                'abstract refrescado (truncado: %d -> %d caracteres)'
                % (len(actual or ''), len(abstract)))
        cambios += 1
        time.sleep(2)
    return cambios


def main():
    dry = '--dry-run' in sys.argv
    minimo = None
    for i, arg in enumerate(sys.argv):
        if arg == '--refrescar-cortos' and i + 1 < len(sys.argv):
            minimo = int(sys.argv[i + 1])
        elif arg.startswith('--refrescar-cortos='):
            minimo = int(arg.split('=', 1)[1])

    con = sqlite3.connect(DB)
    if minimo is not None:
        cambios = refrescar_cortos(con, dry, minimo)
        etiqueta = 'refrescados'
    else:
        cambios = rellenar_vacios(con, dry)
        etiqueta = 'completados'

    if not dry:
        con.commit()
    con.close()
    print('\n%s: %d%s' % (etiqueta, cambios, ' (dry-run: no se escribio nada)' if dry else ''))


if __name__ == '__main__':
    main()
