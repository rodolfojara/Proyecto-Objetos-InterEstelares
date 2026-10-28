#!/usr/bin/env python3
"""
Skill: normalize_units
Purpose: Normalize common units (au, km, km/s)
"""
import re

def normalize_distance(val_str, unit_hint=None):
    # very simple normalizer placeholder
    try:
        v = float(val_str)
        u = (unit_hint or '').lower()
        if 'km' in u and 'au' not in u:
            # rough placeholder - not for precise calc
            return v, 'km'
        if 'au' in u:
            return v, 'au'
        return v, u or 'unknown'
    except:
        return val_str, unit_hint

def normalize_velocity(val_str, unit_hint=None):
    try:
        v = float(val_str)
        u = (unit_hint or '').lower()
        if 'km/s' in u:
            return v, 'km/s'
        return v, u or 'km/s'
    except:
        return val_str, unit_hint

if __name__ == '__main__':
    print(normalize_distance('1.356', 'au'))
    print(normalize_velocity('58.0', 'km/s'))
