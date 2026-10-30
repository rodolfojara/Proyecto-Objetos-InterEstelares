"""Pase inicial de metadatos bibliograficos (OpenAlex -> publications + object_publications).

Alcance: ventana de un ano desde la designacion I de cada objeto (config/metadata_scope.json).
Solo metadatos: no escribe en orbital_elements, physical_params, composition, activity ni
object_aliases. Deja publications.processed = 0 y publication_class NULL para que la Fase 2/3
normalice y clasifique sin rehacer trabajo.

Uso:
    python scripts/orchestrator/collect_metadata_openalex.py --dry-run
    python scripts/orchestrator/collect_metadata_openalex.py
"""

import difflib
try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    try:
        import msvcrt
        _HAS_FCNTL = False
        _HAS_MSVCRT = True
    except ImportError:
        _HAS_FCNTL = False
        _HAS_MSVCRT = False
import json
import os
import re
import sqlite3
import ssl
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

from metadata_discovery import limpiar_abstract, limpiar_titulo

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE = r'C:/Users/user/Documents/Proyecto Objetos InterEstelares'
DB = BASE + '/data/db/iso.db'
CONFIG = BASE + '/config/metadata_scope.json'
CA_BUNDLE = r'C:/Program Files/Git/usr/ssl/certs/ca-bundle.crt'
API = 'https://api.openalex.org/works'
MAILTO = 'rodolfojara@users.noreply.github.com'
TIPOS_VALIDOS = {'article', 'preprint', 'review'}
MAX_AUTORES = 25
MAX_ABSTRACT = 4000
COMMIT_CADA = 10  # Commit every N records for resumability

CTX = ssl.create_default_context(cafile=CA_BUNDLE) if os.path.exists(CA_BUNDLE) else ssl.create_default_context()

# cache opcional de respuestas API (util para reintentar sin volver a paginar)
CACHE_DIR = None
CHECKPOINT_DIR = None
REANUDAR = False
for i, arg in enumerate(sys.argv):
    if arg == '--cache-dir' and i + 1 < len(sys.argv):
        CACHE_DIR = sys.argv[i + 1]
    elif arg.startswith('--cache-dir='):
        CACHE_DIR = arg.split('=', 1)[1]
    elif arg == '--checkpoint-dir' and i + 1 < len(sys.argv):
        CHECKPOINT_DIR = sys.argv[i + 1]
    elif arg.startswith('--checkpoint-dir='):
        CHECKPOINT_DIR = arg.split('=', 1)[1]
    elif arg == '--reanudar':
        REANUDAR = True
    elif arg == '--commit-cada' and i + 1 < len(sys.argv):
        try:
            COMMIT_CADA = int(sys.argv[i + 1])
        except ValueError:
            pass
    elif arg.startswith('--commit-cada='):
        try:
            COMMIT_CADA = int(arg.split('=', 1)[1])
        except ValueError:
            pass


def http_json(url, intentos=8):
    ultimo = None
    for i in range(intentos):
        req = urllib.request.Request(url, headers={'User-Agent': 'ISO-Tracker/0.1 (metadata pass)'})
        try:
            with urllib.request.urlopen(req, timeout=90, context=CTX) as r:
                return json.loads(r.read())
        except Exception as e:
            ultimo = e
            espera = min(50, 5 * (i + 1))
            print('    reintento en %ds: %r' % (espera, e))
            time.sleep(espera)
    raise ultimo


def normalizar(texto):
    texto = unicodedata.normalize('NFKD', texto or '')
    texto = ''.join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', ' ', texto.lower()).strip()


def abstract_de(work):
    if work.get('_abstract'):
        return work['_abstract']
    inv = work.get('abstract_inverted_index')
    if not inv:
        return ''
    pos = {}
    for palabra, idxs in inv.items():
        for i in idxs:
            pos[i] = palabra
    return ' '.join(pos[i] for i in sorted(pos))


def arxiv_id_de(work):
    for loc in work.get('locations') or []:
        for clave in ('landing_page_url', 'pdf_url'):
            url = loc.get(clave) or ''
            m = re.search(r'arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})', url)
            if m:
                return m.group(1)
    return None


def revista_de(work):
    src = ((work.get('primary_location') or {}).get('source') or {})
    if src.get('type') == 'journal':
        return src.get('display_name')
    for loc in work.get('locations') or []:
        src = loc.get('source') or {}
        if src.get('type') == 'journal' and src.get('issn_l'):
            return src.get('display_name')
    return None


def doi_limpio(work):
    doi = work.get('doi') or ''
    return doi.replace('https://doi.org/', '').replace('http://dx.doi.org/', '') or None


def fuente_confiable(work):
    """arXiv, o revista con ISSN. Excluye repositorios genericos (Zenodo, viXra, blogs)."""
    for loc in work.get('locations') or []:
        src = loc.get('source') or {}
        if src.get('display_name') == 'arXiv (Cornell University)':
            return 'arxiv'
        if src.get('type') == 'journal' and src.get('issn_l'):
            return 'journal'
    return None


def buscar(ventana):
    """Descarga todos los candidatos de la ventana.

    metodo = openalex (por defecto): busqueda directa en OpenAlex.
    metodo = arxiv+crossref: descubrimiento por DOI cuando OpenAlex limita las
    busquedas; luego se enriquece con `filter=doi:` y se aplican los mismos filtros.
    """
    cache = None
    if CACHE_DIR:
        os.makedirs(CACHE_DIR, exist_ok=True)
        nombre = re.sub(r'[^A-Za-z0-9]+', '_', ventana['designation']) + '_' + ventana['desde'] + '.json'
        cache = os.path.join(CACHE_DIR, nombre)
        if os.path.exists(cache):
            with open(cache, encoding='utf-8') as f:
                print('    cache: %s' % cache)
                return json.load(f)

    if ventana.get('metodo', 'openalex') == 'openalex':
        resultados = _buscar_openalex(ventana)
    else:
        resultados = _buscar_por_doi(ventana)

    if cache:
        with open(cache, 'w', encoding='utf-8') as f:
            json.dump(resultados, f)
    return resultados


def _buscar_openalex(ventana):
    filtro = 'from_publication_date:%s,to_publication_date:%s,title_and_abstract.search:%s' % (
        ventana['desde'], ventana['hasta'], ventana['query'])
    resultados = []
    pagina = 1
    while True:
        url = API + '?' + urllib.parse.urlencode({
            'filter': filtro,
            'per-page': 200,
            'page': pagina,
            'select': ('id,doi,title,publication_date,type,primary_location,locations,'
                       'authorships,abstract_inverted_index,language,primary_topic'),
            'mailto': MAILTO,
        })
        datos = http_json(url)
        lote = datos.get('results') or []
        resultados.extend(lote)
        print('    pagina %d: %d registros (total %s)' % (pagina, len(lote), datos['meta'].get('count')))
        if len(lote) < 200:
            break
        pagina += 1
        time.sleep(4)
    return resultados


def _buscar_por_doi(ventana):
    import metadata_discovery as D

    print('    descubrimiento: arxiv + crossref (sin busquedas OpenAlex)')
    encontrados = D.descubrir_arxiv(ventana) + D.descubrir_crossref(ventana)

    # pre-filtro barato por relevancia antes de gastar llamadas a la API
    patron = re.compile(ventana['regex'], re.IGNORECASE)
    patron_titulo = (re.compile(ventana['regex_titulo'], re.IGNORECASE)
                     if ventana.get('regex_titulo') else None)

    def plausible(r):
        titulo = r.get('title') or ''
        if patron.search(titulo + ' ' + (r.get('_abstract') or '')):
            return True
        return bool(patron_titulo and patron_titulo.search(titulo))

    filtrados = [r for r in encontrados if plausible(r)]
    print('    candidatos descubiertos: %d | plausibles: %d' % (len(encontrados), len(filtrados)))

    if ventana.get('enriquecer_openalex'):
        return D.enriquecer_por_doi(filtrados, tam_lote=10)
    return filtrados


def _fusionar(a, b):
    """Vuelca b sobre a conservando lo mas completo de cada uno."""
    if len(b['title']) > len(a['title']):
        a['title'] = b['title']
    if len(b['abstract']) > len(a['abstract']):
        a['abstract'] = b['abstract']
    a['arxiv_id'] = a['arxiv_id'] or b['arxiv_id']
    if not a['doi']:
        a['doi'] = b['doi']
    elif b['doi'] and a['doi'].startswith('10.48550/') and not b['doi'].startswith('10.48550/'):
        a['doi'] = b['doi']
    a['journal'] = a['journal'] or b['journal']
    a['fechas'] = a['fechas'] + b['fechas']
    a['openalex_ids'] = a['openalex_ids'] + b['openalex_ids']
    a['confiable'] = a['confiable'] or b['confiable']
    a['authors'] = a['authors'] or b['authors']
    a['idiomas'] = a['idiomas'] | b['idiomas']
    a['dominios'] = a['dominios'] | b['dominios']
    return a


def fusionar_similares(registros, umbral=0.95):
    """Une titulos casi identicos (preprint vs version de revista, ortografia)."""
    finales = []
    for g in sorted(registros, key=lambda r: min(r['fechas']) if r['fechas'] else ''):
        norm = normalizar(g['title'])
        for f in finales:
            if abs(len(norm) - len(f['_norm'])) > 0.2 * max(len(norm), len(f['_norm'])):
                continue
            if difflib.SequenceMatcher(None, norm, f['_norm']).ratio() >= umbral:
                _fusionar(f, g)
                f['_norm'] = normalizar(f['title'])
                break
        else:
            g['_norm'] = norm
            finales.append(g)
    return finales, len(registros) - len(finales)



def fusionar_por_identificador(registros):
    """Une registros que comparten arXiv o DOI (mismo paper con dos titulos)."""
    total_antes = len(registros)
    while True:
        por_arxiv, por_doi, finales = {}, {}, []
        for g in registros:
            destino = None
            if g['arxiv_id'] and g['arxiv_id'].lower() in por_arxiv:
                destino = por_arxiv[g['arxiv_id'].lower()]
            if destino is None and g['doi'] and g['doi'].lower() in por_doi:
                destino = por_doi[g['doi'].lower()]
            if destino is None:
                finales.append(g)
                if g['arxiv_id']:
                    por_arxiv[g['arxiv_id'].lower()] = g
                if g['doi']:
                    por_doi[g['doi'].lower()] = g
            else:
                _fusionar(destino, g)
                if destino['arxiv_id']:
                    por_arxiv[destino['arxiv_id'].lower()] = destino
                if destino['doi']:
                    por_doi[destino['doi'].lower()] = destino
        if len(finales) == len(registros):
            return finales, total_antes - len(finales)
        registros = finales


def filtrar(ventana, candidatos):
    """Agrupa por titulo normalizado, fusiona identificadores y luego valida.

    Fusionar antes de filtrar evita perder papers reales cuyo registro de OpenAlex
    esta partido en dos (preprint sin DOI y version de revista sin arXiv).
    """
    patron = re.compile(ventana['regex'], re.IGNORECASE)
    patron_titulo = (re.compile(ventana['regex_titulo'], re.IGNORECASE)
                     if ventana.get('regex_titulo') else None)

    def coincide(registro):
        if patron.search(registro['title'] + ' ' + registro['abstract']):
            return True
        return bool(patron_titulo and patron_titulo.search(registro['title']))

    descartes = {'tipo': 0, 'regex': 0, 'sin_identificador': 0, 'sin_abstract': 0,
                 'sin_fuente': 0, 'idioma': 0, 'dominio': 0, 'mismo_id': 0,
                 'titulo_similar': 0}

    grupos = {}
    for w in candidatos:
        if w.get('type') not in TIPOS_VALIDOS:
            descartes['tipo'] += 1
            continue
        titulo = limpiar_titulo(w.get('title') or '')
        if not titulo:
            continue
        clave = normalizar(titulo)
        g = grupos.setdefault(clave, {
            'title': titulo, 'abstract': '', 'arxiv_id': None, 'doi': None,
            'journal': None, 'fechas': [], 'openalex_ids': [], 'confiable': None,
            'authors': None, 'idiomas': set(), 'dominios': set(),
        })
        if len(titulo) > len(g['title']):
            g['title'] = titulo
        ab = limpiar_abstract(abstract_de(w))
        if len(ab) > len(g['abstract']):
            g['abstract'] = ab
        g['arxiv_id'] = g['arxiv_id'] or arxiv_id_de(w)
        doi = doi_limpio(w)
        # preferir DOI de revista sobre el DOI de arXiv (10.48550/...)
        if doi and (not g['doi'] or g['doi'].startswith('10.48550/')):
            g['doi'] = doi
        g['journal'] = g['journal'] or revista_de(w)
        if w.get('publication_date'):
            g['fechas'].append(w['publication_date'])
        if w.get('id'):
            wid = w['id']
            if not wid.startswith(('doi:', 'arxiv:')):
                wid = wid.rsplit('/', 1)[-1]
            g['openalex_ids'].append(wid)
        g['confiable'] = g['confiable'] or fuente_confiable(w)
        if w.get('language'):
            g['idiomas'].add(w['language'])
        dom = ((w.get('primary_topic') or {}).get('domain') or {}).get('display_name')
        if dom:
            g['dominios'].add(dom)
        if not g['authors']:
            g['authors'] = '; '.join(
                (a.get('author') or {}).get('display_name', '')
                for a in (w.get('authorships') or [])[:MAX_AUTORES]) or None

    registros, por_id = fusionar_por_identificador(list(grupos.values()))
    registros, por_titulo = fusionar_similares(registros)
    descartes['mismo_id'] = por_id
    descartes['titulo_similar'] = por_titulo

    validos = []
    for g in registros:
        if not coincide(g):
            descartes['regex'] += 1
            continue
        if not g['arxiv_id'] and not g['doi']:
            descartes['sin_identificador'] += 1
            continue
        if not g['abstract'] and not g['arxiv_id']:
            descartes['sin_abstract'] += 1
            continue
        if not g['confiable']:
            descartes['sin_fuente'] += 1
            continue
        if g['idiomas'] and 'en' not in g['idiomas']:
            descartes['idioma'] += 1
            continue
        if g['dominios'] and 'Physical Sciences' not in g['dominios']:
            descartes['dominio'] += 1
            continue

        if g['doi'] and g['doi'].startswith('10.48550/'):
            g['doi'] = None
        g['published_at'] = min(g['fechas']) if g['fechas'] else None
        if g['doi']:
            g['source_url'] = 'https://doi.org/' + g['doi']
        elif g['arxiv_id']:
            g['source_url'] = 'https://arxiv.org/abs/' + g['arxiv_id']
        else:
            g['source_url'] = None
        g['relevance'] = 5 if (patron.search(g['title']) or
                               (patron_titulo and patron_titulo.search(g['title']))) else 4
        g['abstract'] = limpiar_abstract(g['abstract'])[:MAX_ABSTRACT] or None
        g['openalex_id'] = ','.join(g['openalex_ids'][:3])
        validos.append(g)

    validos.sort(key=lambda r: r['published_at'] or '')
    return validos, descartes


def guardar(con, oid, ventana, registro):
    """Upsert por identificador. No toca processed ni publication_class."""
    cur = con.cursor()
    fila = None
    if registro['arxiv_id']:
        fila = cur.execute('SELECT id FROM publications WHERE arxiv_id = ?', (registro['arxiv_id'],)).fetchone()
    if not fila and registro['doi']:
        fila = cur.execute('SELECT id FROM publications WHERE doi = ?', (registro['doi'],)).fetchone()

    if fila:
        pid = fila[0]
        # no pisar identificadores ya asignados a otra fila (UNIQUE)
        doi_ok = registro['doi']
        if doi_ok:
            otro = cur.execute('SELECT id FROM publications WHERE doi = ? AND id <> ?',
                               (doi_ok, pid)).fetchone()
            if otro:
                doi_ok = None
        arxiv_ok = registro['arxiv_id']
        if arxiv_ok:
            otro = cur.execute('SELECT id FROM publications WHERE arxiv_id = ? AND id <> ?',
                               (arxiv_ok, pid)).fetchone()
            if otro:
                arxiv_ok = None
        cur.execute(
            'UPDATE publications SET doi = COALESCE(doi, ?), arxiv_id = COALESCE(arxiv_id, ?), '
            'journal = COALESCE(journal, ?), '
            "abstract = CASE WHEN length(coalesce(?, '')) > length(coalesce(abstract, '')) "
            'THEN ? ELSE abstract END WHERE id = ?',
            (doi_ok, arxiv_ok, registro['journal'], registro['abstract'],
             registro['abstract'], pid))
        accion = 'update'
    else:
        cur.execute(
            'INSERT INTO publications (doi, arxiv_id, title, authors, journal, published_at, '
            'abstract, source_url, processed) VALUES (?,?,?,?,?,?,?,?,0)',
            (registro['doi'], registro['arxiv_id'], registro['title'], registro['authors'],
             registro['journal'], registro['published_at'], registro['abstract'],
             registro['source_url']))
        pid = cur.lastrowid
        accion = 'insert'

    cur.execute(
        'INSERT OR IGNORE INTO object_publications (object_id, publication_id, relevance_score) '
        'VALUES (?,?,?)', (oid, pid, registro['relevance']))

    detalles = 'openalex metadata pass | ventana %s..%s | openalex:%s' % (
        ventana['desde'], ventana['hasta'], registro['openalex_id'])
    ya = cur.execute(
        "SELECT id FROM provenance_log WHERE entity='publications' AND entity_id=? "
        "AND details=?", (pid, detalles)).fetchone()
    if not ya:
        cur.execute(
            "INSERT INTO provenance_log (entity, entity_id, action, source_url, agent, details) "
            "VALUES ('publications', ?, ?, ?, 'recolector', ?)",
            (pid, accion, registro['source_url'], detalles))
    return accion


def normalizar_db(con, dry=False):
    """Limpia titulos y abstracts ya cargados.

    Quita el prefijo `Abstract` que agrega Crossref y normaliza el espaciado de la
    designacion (`3I / ATLAS` -> `3I/ATLAS`). Solo actualiza las filas que cambian.
    """
    cur = con.cursor()
    filas = cur.execute('SELECT id, title, abstract, source_url FROM publications').fetchall()
    cambios = 0
    for pid, titulo, abstract, url in filas:
        nuevo_titulo = limpiar_titulo(titulo)
        nuevo_abstract = limpiar_abstract(abstract) or None
        if nuevo_titulo == titulo and nuevo_abstract == abstract:
            continue
        cambios += 1
        if dry:
            if cambios <= 5:
                print('    ~ %s' % nuevo_titulo[:80])
            continue
        cur.execute('UPDATE publications SET title = ?, abstract = ? WHERE id = ?',
                    (nuevo_titulo, nuevo_abstract, pid))
        cur.execute(
            "INSERT INTO provenance_log (entity, entity_id, action, source_url, agent, details) "
            "VALUES ('publications', ?, 'update', ?, 'recolector', ?)",
            (pid, url, 'normalizacion de metadatos (titulo/abstract)'))
    if not dry:
        con.commit()
    print('  normalizados: %d de %d' % (cambios, len(filas)))
    return cambios


def _duracion(segundos):
    minutos, seg = divmod(int(segundos), 60)
    if minutos >= 60:
        horas, minutos = divmod(minutos, 60)
        return '%dh %02dmin' % (horas, minutos)
    return '%dmin %02ds' % (minutos, seg)


def _checkpoint_path(ventana):
    base_dir = CHECKPOINT_DIR or (CACHE_DIR if CACHE_DIR else os.path.join(BASE, '.metadata_checkpoints'))
    os.makedirs(base_dir, exist_ok=True)
    nombre = re.sub(r'[^A-Za-z0-9]+', '_', ventana['designation']) + '_' + ventana['desde'] + '.json'
    return os.path.join(base_dir, nombre)


def _lock_path(ventana):
    base_dir = CHECKPOINT_DIR or (CACHE_DIR if CACHE_DIR else os.path.join(BASE, '.metadata_checkpoints'))
    os.makedirs(base_dir, exist_ok=True)
    nombre = re.sub(r'[^A-Za-z0-9]+', '_', ventana['designation']) + '_lock'
    return os.path.join(base_dir, nombre)


def _cargar_checkpoint(ventana):
    if not REANUDAR:
        return None
    path = _checkpoint_path(ventana)
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                chk = json.load(f)
            print('    checkpoint encontrado: %s' % path)
            return chk
        except Exception as e:
            print('    ! error leyendo checkpoint: %r' % e)
    return None


def _guardar_checkpoint(ventana, chk):
    path = _checkpoint_path(ventana)
    chk['ultima_actualizacion'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    try:
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(chk, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        print('    ! error guardando checkpoint: %r' % e)


def _adquirir_lock(ventana):
    lock_path = _lock_path(ventana)
    try:
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
        if _HAS_FCNTL:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                os.close(fd)
                raise
        elif _HAS_MSVCRT:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            except IOError:
                os.close(fd)
                raise
        try:
            os.write(fd, str(os.getpid()).encode())
        except Exception:
            pass
        return fd
    except Exception as e:
        print('  ! no se pudo adquirir lock para %s: %r' % (ventana['designation'], e))
        print('    Si la ejecucion anterior fue interrumpida, elimine %s' % lock_path)
        raise


def _liberar_lock(fd, ventana):
    try:
        if _HAS_FCNTL:
            fcntl.flock(fd, fcntl.LOCK_UN)
        elif _HAS_MSVCRT:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            except Exception:
                pass
        os.close(fd)
    except Exception:
        pass
    try:
        lock_path = _lock_path(ventana)
        if os.path.exists(lock_path):
            os.unlink(lock_path)
    except Exception:
        pass


def _verificar_ventana(con, oid, ventana, esperados):
    cur = con.cursor()
    total = cur.execute(
        'SELECT COUNT(*) FROM object_publications WHERE object_id = ?', (oid,)
    ).fetchone()[0]
    # Verificar duplicados por publication_id
    duplicados = cur.execute(
        'SELECT publication_id, COUNT(*) as c FROM object_publications WHERE object_id = ? GROUP BY publication_id HAVING c > 1',
        (oid,)
    ).fetchall()
    # Verificar integridad referencial basica
    huerfanos = cur.execute(
        '''SELECT COUNT(*) FROM object_publications op 
           WHERE op.object_id = ? AND NOT EXISTS (SELECT 1 FROM publications p WHERE p.id = op.publication_id)''',
        (oid,)
    ).fetchone()[0]
    ok = True
    if duplicados:
        print('  ! ADVERTENCIA: duplicados encontrados: %s' % duplicados)
        ok = False
    if huerfanos:
        print('  ! ADVERTENCIA: enlaces huerfanos: %d' % huerfanos)
        ok = False
    print('  verificacion: total_vinculos=%d | duplicados=%d | huerfanos=%d' % (total, len(duplicados), huerfanos))
    return ok


def main():
    dry = '--dry-run' in sys.argv
    solo = None
    for i, arg in enumerate(sys.argv):
        if arg == '--solo' and i + 1 < len(sys.argv):
            solo = sys.argv[i + 1]
        elif arg.startswith('--solo='):
            solo = arg.split('=', 1)[1]
    with open(CONFIG, encoding='utf-8') as f:
        cfg = json.load(f)

    con = sqlite3.connect(DB)
    con.execute('PRAGMA journal_mode=WAL;')
    con.execute('PRAGMA synchronous=NORMAL;')

    if '--normalizar' in sys.argv:
        print('== Normalizacion de metadatos ya cargados ==')
        normalizar_db(con, dry)
        con.close()
        if dry:
            print('\n(dry-run: no se escribio nada)')
        return

    resumen = []
    inicio_pase = time.time()

    for ventana in cfg['ventanas']:
        if solo and solo.lower() not in ventana['designation'].lower():
            continue
        print('\n== %s | %s a %s ==' % (ventana['designation'], ventana['desde'], ventana['hasta']))
        fila = con.execute('SELECT id FROM objects WHERE designation = ?', (ventana['designation'],)).fetchone()
        if not fila:
            print('  ! objeto no encontrado en la DB')
            continue
        oid = fila[0]
        inicio_ventana = time.time()

        lock_fd = None
        if not dry:
            try:
                lock_fd = _adquirir_lock(ventana)
                print('  lock adquirido')
            except Exception:
                con.close()
                raise

        try:
            checkpoint = _cargar_checkpoint(ventana)
            if checkpoint and checkpoint.get('completado'):
                print('  ventana ya completada segun checkpoint, omitiendo')
                resumen.append((ventana['designation'], checkpoint.get('validos', 0)))
                print('  duracion ventana: %s' % _duracion(time.time() - inicio_ventana))
                continue

            candidatos = buscar(ventana)
            validos, descartes = filtrar(ventana, candidatos)
            print('  candidatos=%d | validos=%d | descartes=%s' % (len(candidatos), len(validos), descartes))

            if checkpoint:
                # Filtrar ya procesados
                procesados = set(checkpoint.get('procesados_ids', []))
                validos_orig = len(validos)
                validos = [v for v in validos if v.get('arxiv_id') not in procesados and v.get('doi') not in procesados]
                print('  reanudando: %d ya procesados, %d pendientes' % (validos_orig - len(validos), len(validos)))

            if dry:
                for r in validos[:12]:
                    print('    - [%s] %s | %s' % (r['relevance'], r['title'][:75], r['published_at']))
            else:
                acciones = {'insert': 0, 'update': 0}
                chk = checkpoint or {
                    'ventana': ventana['designation'],
                    'desde': ventana['desde'],
                    'hasta': ventana['hasta'],
                    'etapa': 'guardando',
                    'procesados_ids': [],
                    'validos': 0,
                    'completado': False
                }
                for idx, r in enumerate(validos):
                    acciones[guardar(con, oid, ventana, r)] += 1
                    pid_key = r.get('arxiv_id') or r.get('doi')
                    if pid_key and pid_key not in chk['procesados_ids']:
                        chk['procesados_ids'].append(pid_key)
                    chk['validos'] = len(chk['procesados_ids'])
                    if (idx + 1) % COMMIT_CADA == 0:
                        con.commit()
                        _guardar_checkpoint(ventana, chk)
                        print('    commit parcial %d/%d' % (idx + 1, len(validos)))
                con.commit()
                _verificar_ventana(con, oid, ventana, len(validos))
                chk['completado'] = True
                chk['acciones'] = acciones
                _guardar_checkpoint(ventana, chk)
                print('  guardados: %d nuevos, %d actualizados' % (acciones['insert'], acciones['update']))

            resumen.append((ventana['designation'], len(validos)))
            print('  duracion ventana: %s' % _duracion(time.time() - inicio_ventana))
        finally:
            if lock_fd is not None:
                _liberar_lock(lock_fd, ventana)

    con.close()
    print('\nResumen del pase:')
    for d, n in resumen:
        print('  %-14s %d papers' % (d, n))
    print('Duracion total: %s' % _duracion(time.time() - inicio_pase))
    if dry:
        print('\n(dry-run: no se escribio nada)')


if __name__ == '__main__':
    main()
