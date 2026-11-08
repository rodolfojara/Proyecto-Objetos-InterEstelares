#!/usr/bin/env python3
"""
Agente validador de referencias web (v1, basado en reglas; "aprendizaje" iterativo controlado por el usuario).
- NO decide la calidad final del contenido: señala/flaggea y sugiere; la decisión final es del curador humano.
- Lee config/web_references.json + config/web_reference_rules.json, genera sugerencias (agent_review,
  agent_suggested_status/value) y las escribe de vuelta en el config para revisión.
- El usuario revisa, ajusta status/value/evaluation_note y amplía filtros/reglas en web_reference_rules.json
  ("entrenamiento" por refinamiento de reglas). Luego ejecuta curate_web_references.py para ingestar.
"""
import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.request
from datetime import datetime
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REF_LIST = os.path.join(BASE_DIR, 'config', 'web_references.json')
RULES = os.path.join(BASE_DIR, 'config', 'web_reference_rules.json')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'validate_web_references.log')


def log(msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def domain_of(url):
    try:
        host = (urlparse(url).hostname or '').lower()
        return host[4:] if host.startswith('www.') else host
    except Exception:
        return ''


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def http_ok(url, timeout=12):
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'ISO-Tracker/1.0 (validator)'})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return True, getattr(r, 'status', 200), None
    except Exception:
        try:
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(url, headers={'User-Agent': 'ISO-Tracker/1.0 (validator)'})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return True, getattr(r, 'status', 200), None
        except Exception as e:
            return False, None, str(e)


def main():
    parser = argparse.ArgumentParser(description='Validador (agente) de referencias web - sugerencias basadas en reglas')
    parser.add_argument('--skip-http', action='store_true', help='Omitir verificación HTTP')
    parser.add_argument('--only-pending', action='store_true', help='Solo procesar status=pending (default: todas sin decisión final revisada)')
    args = parser.parse_args()

    if not os.path.exists(REF_LIST):
        log(f"No existe {REF_LIST}"); return
    rules = {}
    if os.path.exists(RULES):
        rules = json.load(open(RULES, encoding='utf-8'))
    data = json.load(open(REF_LIST, encoding='utf-8'))
    links = data.get('links') or data.get('references') or []
    trusted = set((rules.get('trusted_domains') or []))
    caution = set((rules.get('caution_domains') or []))
    keywords = [k.lower() for k in (rules.get('relevance_keywords') or [])]
    exclude_pats = [re.compile(p, re.I) for p in (rules.get('title_exclude_patterns') or []) if p]

    log("=" * 60)
    log("INICIO VALIDADOR (AGENTE) REFERENCIAS WEB - sugerencias, NO decisión final")
    log(f"Refs: {len(links)} | Reglas: {RULES}")
    changed = 0
    for i, item in enumerate(links):
        url = (item.get('url') or '').strip()
        if not url:
            continue
        status = (item.get('status') or 'pending').lower()
        if args.only_pending and status != 'pending':
            continue
        # si ya está aceptado/rejected con nota de evaluación humana explícita, igual podemos sugerir pero no forzar; procesamos todos salvo solo-pending
        title = item.get('title') or ''
        summary = item.get('summary') or ''
        eval_note = item.get('evaluation_note') or item.get('evaluation') or ''
        dom = domain_of(url)
        text = ' '.join([url, title, summary, eval_note, ' '.join(item.get('tags') or [])]).lower()
        flags = []
        score = int(rules.get('min_value_suggestion') or 5)
        trusted_hit = any(dom == d or dom.endswith('.' + d) for d in trusted)
        caution_hit = any(dom == d or dom.endswith('.' + d) for d in caution)
        if trusted_hit:
            flags.append('trusted_domain'); score += 1
        if caution_hit:
            flags.append('caution_domain'); score -= 1
        rel = any(k in text for k in keywords)
        if rel:
            flags.append('relevance_match')
        else:
            flags.append('relevance_weak'); score -= 1
        for p in exclude_pats:
            if p.search(title) or p.search(summary):
                flags.append(f'exclude_pattern:{p.pattern}'); score -= 2
        if not summary:
            flags.append('missing_summary'); score -= 1
        if not eval_note:
            flags.append('missing_evaluation_note')
        http_status = None
        if not args.skip_http:
            ok, code, err = http_ok(url)
            http_status = {'ok': ok, 'code': code, 'error': err}
            if not ok:
                flags.append('http_unreachable'); score -= 1
            else:
                flags.append('http_ok')
        score = max(1, min(10, score))
        suggested_status = 'accepted' if ('relevance_match' in flags and 'http_unreachable' not in flags and score >= 6) else ('watch' if rel else 'pending')
        if any(f.startswith('exclude_pattern') for f in flags):
            suggested_status = 'watch'
        review = {
            'ts': datetime.utcnow().isoformat() + 'Z',
            'domain': dom, 'flags': flags, 'http': http_status,
            'suggested_status': suggested_status, 'suggested_value': score,
            'note': 'Sugerencia automática (reglas). La decisión final de calidad/aceptación y la "goyita" la define el curador humano.'
        }
        item['agent_review'] = review
        item['agent_suggested_status'] = suggested_status
        item['agent_suggested_value'] = score
        changed += 1
        log(f"  [{i}] {dom} -> suggest {suggested_status} value={score} flags={flags}")

    data['links'] = links
    with open(REF_LIST, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"FIN. {changed} refs con sugerencias escritas en {REF_LIST}")
    log("Revisa/ajusta status, value_score, evaluation_note; amplía reglas en config/web_reference_rules.json; luego ejecuta curate_web_references.py")
    log("=" * 60)


if __name__ == '__main__':
    main()
