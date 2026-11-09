#!/usr/bin/env python3
"""
Genera "contribution graph" (actividad de referencias) tipo GitHub:
- 3 mini-grids apiladas: Papers, YouTube, Referencias web.
- Fecha usada: publicación/origen (papers=published_at, youtube=published_at|added_at, web=source_date|retrieved_at; web solo accepted/watch).
- Rango completo cubierto en ventanas de 12 meses, navegables (prev/next) vía páginas markdown estáticas.
Salidas:
  docs/images/ref_activity/refact_<YYYY-MM>_<YYYY-MM>.svg  (por ventana)
  docs/images/ref_activity_latest.svg                        (última ventana)
  docs/REFERENCE_ACTIVITY.md                                 (navegador, entra a última ventana)
  docs/ref_activity/<YYYY-MM>_<YYYY-MM>.md                  (página por ventana con flechas ←/→ y límites)
"""
import argparse
import calendar
import os
import sqlite3
from collections import defaultdict
from datetime import date, datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'db', 'iso.db')
IMG_DIR = os.path.join(BASE_DIR, 'docs', 'images', 'ref_activity')
LATEST_SVG = os.path.join(BASE_DIR, 'docs', 'images', 'ref_activity_latest.svg')
NAV_MD = os.path.join(BASE_DIR, 'docs', 'REFERENCE_ACTIVITY.md')
WIN_MD_DIR = os.path.join(BASE_DIR, 'docs', 'ref_activity')

TYPES = [
    ("Papers (publicación)", "papers", ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]),
    ("YouTube (publicación)", "youtube", ["#ebedf0", "#f9a8a8", "#f87171", "#dc2626", "#991b1b"]),
    ("Referencias web (origen)", "web", ["#ebedf0", "#93c5fd", "#60a5fa", "#2563eb", "#1e40af"]),
]
BINS = [0, 1, 2, 5, 10]  # thresholds -> levels 0-4


def get_conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def parse_day(s):
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    # take date part
    m = None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass
    try:
        # ISO with time
        return datetime.fromisoformat(s.replace('Z', '+00:00')).date()
    except Exception:
        return None


def month_add(y, m, delta):
    # delta in months
    n = (y * 12 + (m - 1)) + delta
    return n // 12, n % 12 + 1


def month_start(y, m):
    return date(y, m, 1)


def month_end(y, m):
    last = calendar.monthrange(y, m)[1]
    return date(y, m, last)


def fetch_counts():
    counts = {k: defaultdict(int) for _, k, _ in TYPES}
    conn = get_conn()
    cur = conn.cursor()
    # papers
    cur.execute("SELECT published_at FROM publications WHERE published_at IS NOT NULL AND published_at!=''")
    for r in cur.fetchall():
        d = parse_day(r[0])
        if d:
            counts['papers'][d] += 1
    # youtube
    cur.execute("SELECT COALESCE(published_at, substr(added_at,1,10)) as d FROM media_resources")
    for r in cur.fetchall():
        d = parse_day(r[0])
        if d:
            counts['youtube'][d] += 1
    # web (accepted/watch)
    try:
        cur.execute("SELECT COALESCE(source_date, substr(retrieved_at,1,10)) as d FROM curated_references WHERE status IN ('accepted','watch')")
        for r in cur.fetchall():
            d = parse_day(r[0])
            if d:
                counts['web'][d] += 1
    except Exception:
        pass
    conn.close()
    return counts


def level(n):
    if n <= 0: return 0
    if n == 1: return 1
    if n <= 4: return 2
    if n <= 9: return 3
    return 4


def windows_for_range(dmin, dmax):
    # 12-month windows, last window = trailing 12 months ending at end of dmax's month (capped),
    # stepping back by 12 months to cover full range. First window truncated at dmin if needed.
    end_anchor = month_end(dmax.year, dmax.month)
    wins = []
    ey, em = dmax.year, dmax.month
    while True:
        sy, sm = month_add(ey, em, -11)
        s = month_start(sy, sm)
        e = month_end(ey, em)
        if e > end_anchor:
            e = end_anchor
        if e < dmin:
            break
        if s < dmin:
            s = dmin
        wins.append((s, e))
        if s <= dmin:
            break
        # step back 12 months from start
        py, pm = month_add(sy, sm, -1)
        ey, em = month_add(py, pm, -11)  # previous window ends month before s
        # simpler: move end to month before current start
        ey, em = month_add(sy, sm, -1)
        if month_end(ey, em) < dmin:
            break
    wins.reverse()
    # merge/sanity: ensure contiguous coverage
    return wins


def week_grid(start, end):
    # align to sunday
    # GitHub: rows Sun(0)-Sat(6), cols weeks
    d = start
    # back to Sunday
    d = d - timedelta(days=(d.weekday() + 1) % 7)
    cells = []  # (col, row, date) for dates within [start,end]
    col = 0
    while d <= end + timedelta(days=6):
        for row in range(7):
            dd = d + timedelta(days=row)
            if start <= dd <= end:
                cells.append((col, row, dd))
        col += 1
        d += timedelta(days=7)
        if d > end + timedelta(days=7):
            break
    return cells, col  # num cols


def render_svg(start, end, counts):
    # layout
    cell = 11
    gap = 2
    step = cell + gap
    left = 46
    top0 = 24
    panel_h = 7 * step + 26
    panels = len(TYPES)
    width = left + 54 * step + 20
    height = top0 + panels * panel_h + 34
    # precompute grids (same window => same cols)
    cells, ncols = week_grid(start, end)
    width = left + max(ncols, 1) * step + 20

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="Segoe UI, Arial, sans-serif">']
    parts.append(f'<rect width="100%" height="100%" fill="#ffffff"/>')
    title = f"Actividad de referencias ({start.isoformat()} a {end.isoformat()}) — fecha de publicación/origen"
    parts.append(f'<text x="{left}" y="14" font-size="12" font-weight="600" fill="#24292f">{_esc(title)}</text>')

    day_labels = ['D','L','M','X','J','V','S']
    month_names = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic']

    for pi, (label, key, palette) in enumerate(TYPES):
        oy = top0 + pi * panel_h
        parts.append(f'<text x="2" y="{oy+14}" font-size="11" font-weight="600" fill="#57606a">{_esc(label.split(" (")[0])}</text>')
        for r, dl in enumerate(day_labels):
            if r % 2 == 1:
                parts.append(f'<text x="2" y="{oy+24 + r*step}" font-size="9" fill="#8c959f">{dl}</text>')
        # month labels
        last_m = None
        for col, row, dd in cells:
            mk = (dd.year, dd.month)
            if mk != last_m and dd.day <= 7:
                parts.append(f'<text x="{left + col*step}" y="{oy+9}" font-size="9" fill="#57606a">{month_names[dd.month-1]}</text>')
                last_m = mk
        # cells
        for col, row, dd in cells:
            n = counts[key].get(dd, 0)
            lv = level(n)
            color = palette[lv]
            x = left + col * step
            y = oy + 16 + row * step
            tip = f"{label}: {dd.isoformat()} = {n}"
            parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" ry="2" fill="{color}"><title>{_esc(tip)}</title></rect>')
        # total in window
        tot = sum(n for d,n in counts[key].items() if start <= d <= end)
        parts.append(f'<text x="{left}" y="{oy + 16 + 7*step + 12}" font-size="9" fill="#57606a">Total ventana: {tot}</text>')

    # legend
    ly = top0 + panels * panel_h + 6
    parts.append(f'<text x="{left}" y="{ly+10}" font-size="9" fill="#57606a">Menos</text>')
    # show paper palette as reference + note
    for i, c in enumerate(["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]):
        parts.append(f'<rect x="{left+34 + i*(cell+2)}" y="{ly}" width="{cell}" height="{cell}" rx="2" fill="{c}"/>')
    parts.append(f'<text x="{left+34 + 5*(cell+2)+4}" y="{ly+10}" font-size="9" fill="#57606a">Más (intensidad por tipo: papers azul=no, usa su propio tono; ver celdas)</text>')
    parts.append('</svg>')
    return '\n'.join(parts)


def _esc(s):
    return (str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;'))


def win_name(s, e):
    return f"{s.year}-{s.month:02d}_{e.year}-{e.month:02d}"


def win_label(s, e):
    return f"{s.year}-{s.month:02d} a {e.year}-{e.month:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    args = ap.parse_args()

    os.makedirs(IMG_DIR, exist_ok=True)
    os.makedirs(WIN_MD_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LATEST_SVG), exist_ok=True)

    counts = fetch_counts()
    all_days = [d for k in counts for d in counts[k].keys()]
    if not all_days:
        print('no data'); return
    dmin = min(all_days)
    dmax = max(max(all_days), date.today())
    wins = windows_for_range(dmin, dmax)
    if not wins:
        print('no windows'); return

    for i, (s, e) in enumerate(wins):
        name = win_name(s, e)
        svg_path = os.path.join(IMG_DIR, f"refact_{name}.svg")
        svg = render_svg(s, e, counts)
        with open(svg_path, 'w', encoding='utf-8') as f:
            f.write(svg)
        # per-window markdown with arrows (bounds)
        prev_md = next_md = None
        if i > 0:
            ps, pe = wins[i-1]; prev_md = f"{win_name(ps,pe)}.md"
        if i < len(wins)-1:
            ns, ne = wins[i+1]; next_md = f"{win_name(ns,ne)}.md"
        nav = []
        if prev_md:
            nav.append(f"[← 12 meses anteriores]({prev_md})")
        else:
            nav.append("← 12 meses anteriores *(límite inicial)*")
        nav.append(f"**{win_label(s,e)}** (ventana {i+1}/{len(wins)})")
        if next_md:
            nav.append(f"[12 meses siguientes →]({next_md})")
        else:
            nav.append("12 meses siguientes → *(límite final)*")
        rel_svg = f"../images/ref_activity/refact_{name}.svg"
        md = [
            f"# Actividad de referencias — {win_label(s,e)}",
            "",
            " | ".join(nav),
            "",
            f"![Actividad de referencias {win_label(s,e)}]({rel_svg})",
            "",
            "- 3 mini-grids apiladas (Papers, YouTube, Referencias web), 12 meses por ventana.",
            "- Fecha = **publicación/origen**: papers `published_at`; YouTube `published_at` (fallback `added_at`); web `source_date` (fallback `retrieved_at`, solo aceptadas/en observación).",
            "- Rango completo cubierto por ventanas. Navega con las flechas (con límites al inicio/fin).",
            "",
            f"[Índice / ventana actual](../REFERENCE_ACTIVITY.md) · [Dashboard](../reports/dashboard_latest.md) · [README](../README.md)",
            "",
        ]
        with open(os.path.join(WIN_MD_DIR, f"{name}.md"), 'w', encoding='utf-8') as f:
            f.write('\n'.join(md))

    # latest
    ls, le = wins[-1]
    lname = win_name(ls, le)
    import shutil
    shutil.copyfile(os.path.join(IMG_DIR, f"refact_{lname}.svg"), LATEST_SVG)

    # navigator/index
    nav_lines = [
        "# Actividad de referencias (tipo contribution graph)",
        "",
        f"Rango completo de datos: **{dmin.isoformat()}** a **{dmax.isoformat()}** · {len(wins)} ventanas de 12 meses · 3 tipos apilados (Papers, YouTube, Referencias web).",
        "Fecha usada = **publicación/origen** (ver nota en cada ventana).",
        "",
        f"**Ventana actual (últimos 12 meses del rango): [{win_label(ls,le)}](ref_activity/{lname}.md)**",
        "",
        f"![Actividad de referencias — última ventana](images/ref_activity_latest.svg)",
        "",
        "## Todas las ventanas (rango completo)",
        "",
    ]
    for i, (s, e) in enumerate(wins):
        name = win_name(s, e)
        mark = " ← actual" if i == len(wins)-1 else ""
        nav_lines.append(f"- [{'**' if mark else ''}{win_label(s,e)}{'**' if mark else ''}](ref_activity/{name}.md){mark}")
    nav_lines += ["", "[Dashboard](../reports/dashboard_latest.md) · [README](../README.md)", ""]
    with open(NAV_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(nav_lines))

    print(f"ok windows={len(wins)} latest={win_label(ls,le)} -> {LATEST_SVG}, {NAV_MD}")


if __name__ == '__main__':
    main()
