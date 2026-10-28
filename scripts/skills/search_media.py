#!/usr/bin/env python3
"""
Skill: search_media
Purpose: Search/normalize YouTube links for interstellar objects
Note: Uses websearch if available. Manual entry also supported.
"""
import re
import json
from urllib.parse import urlparse, parse_qs

YOUTUBE_PATTERNS = [
    re.compile(r'(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+(?:&[^\s]+)?)'),
    re.compile(r'(https?://youtu\.be/[\w-]+)'),
]

ISO_KEYWORDS = ["1I", "Oumuamua", "2I", "Borisov", "3I", "ATLAS", "interstellar object", "objeto interestelar"]

def extract_video_id(url):
    try:
        if 'youtu.be' in url:
            return url.split('/')[-1].split('?')[0]
        parsed = urlparse(url)
        if parsed.hostname in ['www.youtube.com', 'youtube.com']:
            qs = parse_qs(parsed.query)
            if 'v' in qs:
                return qs['v'][0]
    except:
        pass
    return None

def extract_youtube_links(text):
    links = []
    for pat in YOUTUBE_PATTERNS:
        for m in pat.findall(text):
            vid = extract_video_id(m)
            links.append({
                'url': m,
                'video_id': vid
            })
    # deduplicate
    seen = set()
    out = []
    for l in links:
        if l['url'] not in seen:
            seen.add(l['url'])
            out.append(l)
    return out

def is_iso_related(text):
    t = text.lower()
    return any(k.lower() in t for k in ISO_KEYWORDS)

if __name__ == '__main__':
    sample = "https://www.youtube.com/watch?v=UTJk2ZGaxaA 1I Oumuamua explanation"
    print(json.dumps(extract_youtube_links(sample), indent=2))
    print(is_iso_related(sample))
