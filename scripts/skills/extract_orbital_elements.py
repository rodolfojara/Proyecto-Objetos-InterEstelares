#!/usr/bin/env python3
"""
Skill: extract_orbital_elements
Purpose: Extract orbital elements from text/tables (a,e,i,q,epoch,v_inf)
"""
import re
import json

PATTERNS = {
    'e': re.compile(r'\be\s*[=:]\s*([0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?)'),
    'q': re.compile(r'\bq\s*[=:]\s*([0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?)'),
    'i': re.compile(r'\bi\s*[=:]\s*([0-9]*\.?[0-9]+(?:[eE][+-]?[0-9]+)?)'),
    'epoch': re.compile(r'\bepoch\s*[=:]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|\d+\.?\d*)', re.IGNORECASE),
    'v_inf': re.compile(r'v[_\s]*inf(?:inity)?\s*[=:]\s*([0-9]*\.?[0-9]+)', re.IGNORECASE),
}

def extract_orbital_elements(text: str):
    out = {}
    for k, pat in PATTERNS.items():
        m = pat.search(text)
        if m:
            try:
                # keep as string/float as appropriate
                val = m.group(1)
                if k in ['e','q','i','v_inf']:
                    # try float
                    try:
                        out[k if k != 'v_inf' else 'e_hyperbolic_v_inf'] = float(val)
                    except:
                        out[k if k != 'v_inf' else 'e_hyperbolic_v_inf'] = val
                else:
                    out[k] = val
            except:
                pass
    return out

if __name__ == '__main__':
    s = "e = 6.14, q = 1.356, i = 175.11, epoch 2025-07-01, v_inf = 58.0"
    print(json.dumps(extract_orbital_elements(s), indent=2))
