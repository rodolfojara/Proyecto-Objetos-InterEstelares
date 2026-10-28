#!/usr/bin/env python3
"""
Skill: search_hyperbolic
Purpose: Scan text/files for hyperbolic elements (e > 1)
"""
import re
import json

def find_hyperbolic(text):
    results = []
    # Look for e > 1 patterns
    for m in re.finditer(r'\be\s*=\s*(1\.[0-9]+|[2-9]\.[0-9]+)', text, re.IGNORECASE):
        try:
            e_val = float(m.group(1))
            if e_val > 1.0:
                # grab context
                start = max(0, m.start()-80)
                end = min(len(text), m.end()+80)
                results.append({
                    'e': e_val,
                    'context': text[start:end]
                })
        except:
            pass
    return results

if __name__ == '__main__':
    sample = "Object 1995 X1 e = 1.002 q = 0.5"
    print(json.dumps(find_hyperbolic(sample), indent=2))
