#!/usr/bin/env python3
"""
Skill: parse_mpec
Purpose: Parse MPEC pages to detect new ISO candidates and extract designations/aliases
Deterministic pattern matching where possible.
"""
import re
import json
from pathlib import Path

ISO_PATTERN = re.compile(r'(1I|2I|3I|A\/\d{4}\s*[A-Z]\d*|\d{4}\s*[A-Z]{2}\d*)', re.IGNORECASE)
HYPERBOLIC_HINT = re.compile(r'(hyperbolic|e\s*>\s*1|v_\infty|interstellar)', re.IGNORECASE)

def parse_mpec_text(text: str):
    results = []
    # Look for lines with ISO hints
    for line in text.splitlines():
        if HYPERBOLIC_HINT.search(line):
            m = ISO_PATTERN.findall(line)
            if m:
                results.append({
                    'line': line.strip(),
                    'candidates': list(set([x.strip() for x in m]))
                })
    return results

if __name__ == '__main__':
    # Example usage
    sample = "MPEC 2025-N12 : 3I/ATLAS is hyperbolic with e>1"
    print(json.dumps(parse_mpec_text(sample), indent=2))
