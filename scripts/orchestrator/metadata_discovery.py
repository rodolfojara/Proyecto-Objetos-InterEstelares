"""Descubrimiento alternativo de candidatos cuando OpenAlex limita las busquedas.

OpenAlex aplica un presupuesto diario a las consultas de tipo `search`. Cuando se
agota (HTTP 429 con `Retry-After` de horas), este modulo descubre DOIs por dos vias
primarias y luego deja que el colector los enriquezca con OpenAlex usando filtros
por DOI, que no consumen ese presupuesto:

- arXiv (buscador HTML avanzado): preprints de la ventana.
- Crossref (API REST): articulos de revista, proceedings y preprints registrados.

Todas las funciones devuelven registros con la misma forma que un `work` de OpenAlex
para que los filtros del colector se apliquen sin cambios.
"""

import html
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

CA_BUNDLE = r'C:/Program Files/Git/usr/ssl/certs/ca-bundle.crt'
CTX = ssl.create_default_context(cafile=CA_BUNDLE) if os.path.exists(CA_BUNDLE) else ssl.create_default_context()
MAILTO = 'rodolfojara@users.noreply.github.com'
UA = 'ISO-Tracker/0.1 (metadata pass; mailto:%s)' % MAILTO

TIPOS_CROSSREF = {
    'journal-article': 'article',
    'posted-content': 'preprint',
    'proceedings-article': 'article',
}
PREFIJOS_DESCARTADOS = ('10.5281/',)  # Zenodo

# Cache parcial por página para reanudación
PARTIAL_CACHE_DIR = None
for i, arg in enumerate(__import__('sys').argv):
    if arg == '--cache-dir' and i + 1 < len(__import__('sys').argv):
        PARTIAL_CACHE_DIR = __import__('sys').argv[i + 1]
    elif arg.startswith('--cache-dir='):
        PARTIAL_CACHE_DIR = arg.split('=', 1)[1]


def _get(url, intentos=5, cabeceras=None):
    ultimo = None
    for i in range(intentos):
        req = urllib.request.Request(url, headers=cabeceras or {'User-Agent': UA})
        try:
            with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
                return r.read()
        except Exception as e:
            ultimo = e
            espera = min(60, 5 * (i + 1))
            print('    reintento en %ds: %r' % (espera, e))
            time.sleep(espera)
    raise ultimo


def _get_json(url, intentos=5):
    return json.loads(_get(url, intentos))


def limpiar_html(texto):
    texto = re.sub(r'<[^>]+>', ' ', texto or '')
    texto = html.unescape(texto)
    return re.sub(r'\s+', ' ', texto).strip()


def limpiar_titulo(titulo):
    """Normaliza espacios y el espaciado de la designacion (``3I / ATLAS`` -> ``3I/ATLAS``)."""
    titulo = re.sub(r'\s+', ' ', titulo or '').strip()
    titulo = re.sub(r'\b(\dI)\s*/\s*', r'\1/', titulo)
    return re.sub(r'\s+', ' ', titulo).strip()


def limpiar_abstract(texto):
    """Quita el prefijo ``Abstract`` y los restos del buscador de arXiv."""
    texto = re.sub(r'\s+', ' ', texto or '').strip()
    texto = re.sub(r'^(abstract|resumen|summary)\s*[:.\-–]?\s*', '', texto, flags=re.I)
    texto = re.sub(r'\s*(△ Less|less)\s*$', '', texto, flags=re.I)
    return texto.strip()


# Palabras funcionales que delatan un titulo no ingles cuando Crossref no informa idioma.
PISTAS_IDIOMA = {
    'es': ('el', 'los', 'las', 'una', 'para', 'con', 'por', 'del', 'que', 'sobre', 'desde'),
    'pt': ('dos', 'das', 'uma', 'para', 'com', 'por', 'que', 'não', 'sobre', 'dos', 'nas'),
    'fr': ('les', 'des', 'une', 'pour', 'avec', 'dans', 'sur', 'aux', 'est', 'du'),
    'de': ('der', 'die', 'das', 'und', 'von', 'mit', 'für', 'ein', 'eine', 'zur', 'im'),
    'it': ('gli', 'della', 'delle', 'una', 'per', 'con', 'che', 'nel', 'sul', 'dei'),
}


def idioma_probable(titulo):
    """Devuelve el idioma probable del titulo; 'en' si no hay pistas claras."""
    palabras = re.findall(r"[a-zà-ÿ']+", (titulo or '').lower())
    if not palabras:
        return 'en'
    conteo = {}
    for idioma, pistas in PISTAS_IDIOMA.items():
        aciertos = sum(1 for p in palabras if p in pistas)
        if aciertos >= 2:
            conteo[idioma] = aciertos
    if not conteo:
        return 'en'
    return max(conteo, key=conteo.get)


def _work_sintetico(doi, titulo, abstract, fecha, autores, tipo, idioma,
                    revista=None, issn=None, arxiv_id=None):
    titulo = limpiar_titulo(titulo)
    abstract = limpiar_abstract(abstract)
    locations = []
    if arxiv_id:
        locations.append({
            'landing_page_url': 'http://arxiv.org/abs/%s' % arxiv_id,
            'pdf_url': None,
            'source': {'display_name': 'arXiv (Cornell University)', 'type': 'repository',
                       'issn_l': None},
        })
    if revista:
        locations.append({
            'landing_page_url': ('https://doi.org/' + doi) if doi else None,
            'pdf_url': None,
            'source': {'display_name': revista, 'type': 'journal', 'issn_l': issn},
        })
    return {
        'id': ('doi:' + doi) if doi else ('arxiv:' + (arxiv_id or '')),
        'doi': ('https://doi.org/' + doi) if doi else None,
        'title': titulo,
        '_abstract': abstract or '',
        'publication_date': fecha,
        'type': tipo,
        'primary_location': locations[0] if locations else {},
        'locations': locations,
        'authorships': [{'author': {'display_name': a}} for a in (autores or [])],
        'language': idioma,
        'primary_topic': None,
    }


# ---------------------------------------------------------------- arXiv (HTML)

def descubrir_arxiv(ventana, termino=None, maximo=400):
    termino = termino or ventana.get('query_arxiv') or ventana['query']
    cache_base = PARTIAL_CACHE_DIR
    if cache_base:
        os.makedirs(cache_base, exist_ok=True)
        cache_prefijo = os.path.join(cache_base, 'arxiv_' + re.sub(r'[^A-Za-z0-9]+', '_', ventana['designation']) + '_' + ventana['desde'])
    else:
        cache_prefijo = None

    resultados, start = [], 0
    while start < maximo:
        if cache_prefijo:
            cache_p = cache_prefijo + '_start' + str(start) + '.json'
            if os.path.exists(cache_p):
                try:
                    with open(cache_p, encoding='utf-8') as f:
                        cached = json.load(f)
                    print('    arxiv start=%d: cache %d resultados' % (start, len(cached)))
                    resultados.extend(cached)
                    start += 200
                    continue
                except Exception:
                    pass

        params = {
            'advanced': '',
            'terms-0-operator': 'AND',
            'terms-0-term': termino,
            'terms-0-field': 'all',
            'classification-physics_archives': 'all',
            'classification-include_cross_list': 'include',
            'date-filter_by': 'date_range',
            'date-from_date': ventana['desde'],
            'date-to_date': ventana['hasta'],
            'date-date_type': 'submitted_date',
            'abstracts': 'show',
            'size': 200,
            'order': '-announced_date_first',
            'start': start,
        }
        url = 'https://arxiv.org/search/advanced?' + urllib.parse.urlencode(params)
        pagina = _get(url, cabeceras={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ISO-Tracker/0.1'}).decode('utf-8', 'replace')
        bloques = re.findall(r'<li class="arxiv-result">(.*?)</li>', pagina, re.S)
        print('    arxiv start=%d: %d resultados' % (start, len(bloques)))
        if not bloques:
            break
        page_results = []
        for b in bloques:
            m = re.search(r'arxiv\.org/abs/([0-9]{4}\.[0-9]{4,5})', b)
            if not m:
                continue
            aid = m.group(1)
            mt = re.search(r'<p class="title is-5 mathjax">(.*?)</p>', b, re.S)
            titulo = limpiar_html(mt.group(1)) if mt else ''
            ma = re.search(r'<p class="authors">(.*?)</p>', b, re.S)
            autores = []
            if ma:
                limpio = limpiar_html(ma.group(1))
                limpio = re.sub(r'^Authors:\s*', '', limpio)
                autores = [a.strip() for a in limpio.split(',') if a.strip()]
            # el abstract contiene <span class="search-hit"> anidados: cortar en el
            # enlace "Less" y no en el primer </span>
            mab = re.search(r'class="abstract-full[^"]*"[^>]*>(.*?)<a class="is-size-7"', b, re.S)
            abstract = limpiar_abstract(limpiar_html(mab.group(1))) if mab else ''
            mf = re.search(r'Submitted</span>\s*([0-9]{1,2} \w+?,? [0-9]{4})', b)
            fecha = None
            if mf:
                try:
                    fecha = time.strftime('%Y-%m-%d', time.strptime(
                        re.sub(r'(\d) (\w)', r'\1 \2', mf.group(1)).replace(',', ''), '%d %B %Y'))
                except Exception:
                    fecha = None
            wr = _work_sintetico(
                doi='10.48550/arxiv.' + aid, titulo=titulo, abstract=abstract, fecha=fecha,
                autores=autores, tipo='preprint', idioma='en', arxiv_id=aid)
            page_results.append(wr)
        resultados.extend(page_results)
        if cache_prefijo:
            try:
                with open(cache_prefijo + '_start' + str(start) + '.json', 'w', encoding='utf-8') as f:
                    json.dump(page_results, f, ensure_ascii=False)
            except Exception:
                pass
        start += 200
        if len(bloques) < 200:
            break
        time.sleep(3)
    return resultados


# ------------------------------------------------------------------ Crossref

def descubrir_crossref(ventana, maximo_paginas=5, tam=200):
    """Crossref ordena por relevancia; los aciertos se concentran en las primeras paginas.

    Admite varias consultas (lista en `query_crossref`) para no depender de una sola
    formulacion del nombre del objeto.
    """
    consultas = ventana.get('query_crossref') or [ventana['query']]
    if isinstance(consultas, str):
        consultas = [consultas]
    resultados = []
    cache_base = PARTIAL_CACHE_DIR
    if cache_base:
        os.makedirs(cache_base, exist_ok=True)
    for consulta in consultas:
        print('    crossref consulta: %s' % consulta)
        for pagina in range(maximo_paginas):
            cache_p = None
            if cache_base:
                cache_p = os.path.join(cache_base, 'crossref_' + re.sub(r'[^A-Za-z0-9]+', '_', ventana['designation']) + '_' + re.sub(r'[^A-Za-z0-9]+', '_', consulta) + '_p' + str(pagina) + '.json')
                if os.path.exists(cache_p):
                    try:
                        with open(cache_p, encoding='utf-8') as f:
                            cached = json.load(f)
                        print('      pagina %d: cache %d resultados' % (pagina, len(cached)))
                        resultados.extend(cached)
                        continue
                    except Exception:
                        pass

            params = {
                'query.bibliographic': consulta,
                'filter': ('from-pub-date:%s,until-pub-date:%s,type:journal-article,'
                           'type:posted-content,type:proceedings-article'
                           % (ventana['desde'], ventana['hasta'])),
                'rows': tam,
                'offset': pagina * tam,
                'mailto': MAILTO,
            }
            datos = _get_json('https://api.crossref.org/works?' + urllib.parse.urlencode(params))
            items = datos['message']['items']
            if pagina == 0:
                print('      %d resultados totales' % datos['message']['total-results'])
            if not items:
                break
            page_results = []
            for it in items:
                doi = (it.get('DOI') or '').lower()
                if not doi or doi.startswith(PREFIJOS_DESCARTADOS):
                    continue
                tipo = TIPOS_CROSSREF.get(it.get('type'))
                if not tipo:
                    continue
                titulo = limpiar_html((it.get('title') or [''])[0])
                if not titulo:
                    continue
                abstract = limpiar_html(it.get('abstract') or '')
                revista = limpiar_html((it.get('container-title') or [''])[0]) or None
                issn = (it.get('ISSN') or [None])[0]
                fecha = None
                partes = ((it.get('issued') or {}).get('date-parts') or [[None]])[0]
                if partes and partes[0]:
                    fecha = '-'.join(str(p).zfill(2) for p in partes if p)
                autores = []
                for a in it.get('author') or []:
                    nombre = ' '.join(x for x in (a.get('given'), a.get('family')) if x)
                    if nombre:
                        autores.append(nombre)
                arxiv_id = None
                if doi.startswith('10.48550/arxiv.'):
                    arxiv_id = doi.split('arxiv.', 1)[1]
                page_results.append(_work_sintetico(
                    doi=doi, titulo=titulo, abstract=abstract, fecha=fecha, autores=autores,
                    tipo=tipo, idioma=(it.get('language') or idioma_probable(titulo)),
                    revista=revista, issn=issn, arxiv_id=arxiv_id))
            resultados.extend(page_results)
            if cache_p:
                try:
                    with open(cache_p, 'w', encoding='utf-8') as f:
                        json.dump(page_results, f, ensure_ascii=False)
                except Exception:
                    pass
            if len(items) < tam:
                break
            time.sleep(2)
    return resultados


# --------------------------------------------- enriquecimiento por DOI (OpenAlex)

def enriquecer_por_doi(registros, tam_lote=40, campos=None):
    """Sustituye los registros sinteticos por el work de OpenAlex cuando exista.

    Usa `filter=doi:...`, que no consume el presupuesto de busquedas.
    """
    campos = campos or ('id,doi,title,publication_date,type,primary_location,locations,'
                        'authorships,abstract_inverted_index,language,primary_topic')
    por_doi = {}
    for r in registros:
        doi = (r.get('doi') or '').lower()
        if doi.startswith('https://doi.org/'):
            doi = doi[len('https://doi.org/'):]
        if doi:
            por_doi.setdefault(doi, r)

    enriquecidos = {}
    lista = list(por_doi)
    for i in range(0, len(lista), tam_lote):
        lote = lista[i:i + tam_lote]
        filtro = 'doi:' + '|'.join(lote)
        url = 'https://api.openalex.org/works?' + urllib.parse.urlencode({
            'filter': filtro, 'per-page': tam_lote, 'select': campos, 'mailto': MAILTO})
        try:
            datos = _get_json(url)
        except Exception as e:
            print('    ! enriquecimiento fallo en el lote %d: %r' % (i // tam_lote, e))
            continue
        for w in datos.get('results') or []:
            doi = ((w.get('doi') or '').lower().replace('https://doi.org/', '')).strip()
            if doi:
                enriquecidos[doi] = w
        print('    openalex doi lote %d: %d/%d encontrados' % (
            i // tam_lote + 1, len(datos.get('results') or []), len(lote)))
        time.sleep(2)

    salida, faltan = [], 0
    for doi, original in por_doi.items():
        if doi in enriquecidos:
            salida.append(enriquecidos[doi])
        else:
            salida.append(original)
            faltan += 1
    print('    enriquecidos: %d | sin OpenAlex: %d' % (len(salida) - faltan, faltan))
    return salida
