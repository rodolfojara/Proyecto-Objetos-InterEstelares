#!/usr/bin/env python3
"""
ISO Tracker - Dashboard generator (evolutivo)
Genera una página/resumen completo con características, ubicación observacional (si disponible),
análisis recientes y enlaces. Diseñado para actualizarse a medida que llega más información.
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, 'data', 'db', 'iso.db')
OUT_DIR = os.path.join(BASE_DIR, 'reports')
CHECKPOINT_DIR = os.path.join(BASE_DIR, '.metadata_checkpoints')
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, 'dashboard_checkpoint.json')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'dashboard.log')


def log(msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"Error cargando checkpoint: {e}")
    return {"started_at": datetime.utcnow().isoformat() + 'Z', "status": "in_progress", "generated": []}


def save_checkpoint(cp):
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    cp['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cp, f, indent=2, ensure_ascii=False)


def conn_db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def q(cur, sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()


def fmt(v, default="N/D"):
    if v is None or v == "":
        return default
    return str(v)


def is_placeholder_text(s):
    if s is None:
        return False
    s = str(s).lower()
    return "placeholder" in s


def pick_best_activity(rows):
    # prefer highest confidence, then most recent retrieved_at
    if not rows:
        return None
    def key(r):
        conf = r['confidence'] if r['confidence'] is not None else -1
        rt = r['retrieved_at'] or ""
        # avoid placeholders (confidence 2 from fase2 rest) if better exists
        placeholder_penalty = 1 if conf <= 2 and (r['source_url'] and 'minorplanetcenter.net/db_search' in r['source_url']) else 0
        return (placeholder_penalty, -conf, rt)
    return sorted(rows, key=key)[0]


def generate_dashboard(resumable=False, force=False):
    start = time.time()
    log("=" * 60)
    log("INICIO DASHBOARD - RESUMEN COMPLETO")
    log(f"DB: {DB_PATH}")
    log("=" * 60)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    if force and os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
        log("Checkpoint eliminado por --force")

    cp = load_checkpoint()
    # Por defecto regenerar (útil en ejecución normal/orquestador) salvo --reanudar explícito.
    if resumable and not force and cp.get('status') == 'completed' and cp.get('last_dashboard'):
        log("Ya completado según checkpoint (reanudar). Usa --force para regenerar.")
        sys.exit(0)

    now = datetime.now()
    out_path = os.path.join(OUT_DIR, f"dashboard_objetos_interestelares_{now.strftime('%Y-%m-%d_%H-%M-%S')}.md")

    conn = conn_db()
    cur = conn.cursor()
    try:
        objects = q(cur, "SELECT * FROM objects ORDER BY discovery_date, id")
        lines = []
        lines.append("# Dashboard: Objetos Interestelares (ISO Tracker)")
        lines.append("")
        lines.append(f"**Actualizado:** {now.strftime('%Y-%m-%d %H:%M:%S')}  ")
        lines.append("**Estado:** Evolutivo (se actualiza con nuevos datos/observaciones/análisis).  ")
        lines.append("**Nota:** Los campos sin datos suficientes se marcan como *N/D* o *pendiente*. Se priorizan registros con mayor confianza.")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Resumen general")
        lines.append("")
        for o in objects:
            lines.append(f"- **{o['designation']}** ({o['name']}): descubierto {o['discovery_date']} — {o['status']}. {o['notes'] or ''}")
        traj_img = os.path.join(BASE_DIR, 'docs', 'images', '1i 2i 3i Trayectoria plana.png')
        if os.path.exists(traj_img):
            lines.append("")
            lines.append("![Trayectorias y posición aproximada actual de 1I, 2I y 3I](../docs/images/1i%202i%203i%20Trayectoria%20plana.png)")
            lines.append("")
            lines.append("*Esquema de trayectorias/posición aproximada (referencial). Para posiciones precisas: efemérides JPL Horizons (ver “Última observación / ubicación aproximada” por objeto).*")
        # counts
        counts = {}
        for t in ['publications','object_aliases','physical_params','composition','activity','orbital_elements','observations','media_resources']:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
            except Exception:
                counts[t] = 'ERR'
        lines.append("")
        lines.append(f"**BD:** {counts.get('publications',0)} publicaciones, {counts.get('observations',0)} observaciones, {counts.get('physical_params',0)} parámetros físicos, {counts.get('composition',0)} registros de composición, {counts.get('activity',0)} registros de actividad, {counts.get('media_resources',0)} recursos multimedia.")
        lines.append("")
        lines.append("---")
        lines.append("")

        for o in objects:
            oid = o['id']
            des = o['designation']
            lines.append(f"## {des} ({o['name']})")
            lines.append("")
            lines.append(f"- **Descubrimiento:** {o['discovery_date']}")
            lines.append(f"- **Estado:** {o['status']}")
            if o['notes']:
                lines.append(f"- **Notas:** {o['notes']}")

            # aliases
            aliases = q(cur, "SELECT alias FROM object_aliases WHERE object_id=? ORDER BY alias", (oid,))
            if aliases:
                lines.append(f"- **Aliases/designaciones:** {', '.join([a['alias'] for a in aliases])}")
            else:
                lines.append("- **Aliases/designaciones:** N/D")

            # orbital
            orb = q(cur, "SELECT * FROM orbital_elements WHERE object_id=? ORDER BY confidence DESC, retrieved_at DESC", (oid,))
            lines.append("")
            lines.append("### Parámetros orbitales (última solución conocida en BD)")
            if orb:
                r = orb[0]
                lines.append(f"- Época: {fmt(r['epoch'])}")
                lines.append(f"- Excentricidad (e): {fmt(r['e'])}")
                lines.append(f"- Perihelio (q, au): {fmt(r['q'])}")
                lines.append(f"- Inclinación (i, °): {fmt(r['i'])}")
                lines.append(f"- Velocidad hiperbólica v∞ (km/s): {fmt(r['e_hyperbolic_v_inf'])}")
                lines.append(f"- Fuente: {fmt(r['source_url'])} (confianza {fmt(r['confidence'])})")
            else:
                lines.append("- N/D")

            # activity
            act_rows = q(cur, "SELECT * FROM activity WHERE object_id=? ORDER BY confidence DESC, retrieved_at DESC", (oid,))
            lines.append("")
            lines.append("### Actividad / coma / polvo")
            best = pick_best_activity(act_rows)
            if best and not (best['confidence'] is not None and best['confidence'] <= 2 and best['source_url'] and 'minorplanetcenter.net/db_search' in best['source_url']):
                def yn(x):
                    return "Sí" if x else "No"
                lines.append(f"- Actividad detectada: {yn(best['activity_detected'])}")
                lines.append(f"- Coma detectada: {yn(best['coma_detected'])}")
                lines.append(f"- Polvo detectado: {yn(best['dust_detected'])}")
                lines.append(f"- Distancia heliocéntrica (rh, au): {fmt(best['rh'])}")
                lines.append(f"- Fuente: {fmt(best['source_url'])} (confianza {fmt(best['confidence'])})")
            else:
                lines.append("- N/D (pendiente de consolidación con fuentes de alta confianza)")

            # physical
            phys = q(cur, "SELECT * FROM physical_params WHERE object_id=? ORDER BY confidence DESC, retrieved_at DESC", (oid,))
            lines.append("")
            lines.append("### Características físicas (tamaño, dimensiones, magnitud, etc.)")
            real_phys = [r for r in phys if not is_placeholder_text(r['value_text']) and r['param'] != 'notes']
            if real_phys:
                for r in real_phys:
                    val = r['value_text'] if r['value_text'] is not None else r['value']
                    lines.append(f"- {r['param']}: {fmt(val)} {fmt(r['unit'], '')} (fuente: {fmt(r['source_url'])})")
            else:
                lines.append("- **Tamaño estimado:** N/D")
                lines.append("- **Dimensiones/forma:** N/D")
                lines.append("- **Magnitud absoluta (H) / magnitud observada reciente:** N/D (sin observaciones con magnitud registradas en BD)")
                lines.append("- **Volumen/masa/albedo/rotación:** N/D")
                lines.append("- *Pendiente de ingestión detallada desde fuentes consolidadas (MPC/JPL/papers).*")

            # composition
            comp = q(cur, "SELECT * FROM composition WHERE object_id=? ORDER BY confidence DESC, retrieved_at DESC", (oid,))
            lines.append("")
            lines.append("### Composición")
            real_comp = [r for r in comp if r['production_rate'] is not None or r['ratio_to_water'] is not None or (r['method'] and not is_placeholder_text(r['method']))]
            if real_comp:
                for r in real_comp:
                    lines.append(f"- {r['species']}: tasa={fmt(r['production_rate'])} {fmt(r['production_rate_unit'],'')}, ratio H2O={fmt(r['ratio_to_water'])}, método={fmt(r['method'])} (fuente: {fmt(r['source_url'])})")
            else:
                lines.append("- N/D / pendiente de consolidación de mediciones espectroscópicas y tasas de producción.")

            # last observation / location / ephemeris
            obs = q(cur, "SELECT * FROM observations WHERE object_id=? ORDER BY observation_date DESC, retrieved_at DESC LIMIT 1", (oid,))
            lines.append("")
            lines.append("### Última observación / ubicación aproximada")
            if obs:
                r = obs[0]
                rdict = dict(r)
                lines.append(f"- Fecha: {fmt(rdict.get('observation_date'))}")
                lines.append(f"- Tipo/Fuente instrumental: {fmt(rdict.get('type'))} / {fmt(rdict.get('telescope'))} {fmt(rdict.get('instrument'),'')}")
                mag = rdict.get('mag')
                mag_type = rdict.get('mag_type') or ''
                if mag is None or str(mag).strip().lower() in ('', 'n.a.', 'na', 'none'):
                    lines.append("- Magnitud (V) observada/calculada: N/D")
                else:
                    lines.append(f"- Magnitud ({fmt(mag_type,'V')}): {mag}")
                ra = rdict.get('ra'); dec = rdict.get('dec')
                delta = rdict.get('delta_au'); rhel = rdict.get('r_au')
                if ra or dec or delta or rhel:
                    lines.append(f"- Ubicación aproximada (RA, Dec): {fmt(ra)} , {fmt(dec)}")
                    lines.append(f"- Distancia: Δ={fmt(delta)} au, r={fmt(rhel)} au")
                else:
                    lines.append("- Posición/ubicación aproximada (RA-Dec/distancia): N/D")
                notes = rdict.get('notes')
                if notes:
                    lines.append(f"- Nota: {notes}")
                lines.append(f"- Fuente: {fmt(rdict.get('source_url'))}")
            else:
                lines.append("- **Última observación registrada:** N/D")
                lines.append("- **Magnitud observada (último dato):** N/D")
                lines.append("- **Ubicación aproximada (última observación):** N/D — pendiente de ingestión de efemérides/observaciones (p. ej. JPL Horizons/MPC).")

            # recent publications
            pubs = q(cur, """
                SELECT p.title, p.published_at, p.source_url
                FROM publications p
                JOIN object_publications op ON op.publication_id = p.id
                WHERE op.object_id = ?
                ORDER BY p.published_at DESC, p.id DESC LIMIT 5
            """, (oid,))
            lines.append("")
            lines.append("### Análisis/publicaciones recientes (resumen)")
            if pubs:
                for p in pubs:
                    lines.append(f"- {fmt(p['published_at'])}: [{p['title']}]({p['source_url']})")
            else:
                lines.append("- N/D")

            # media
            media = q(cur, """
                SELECT m.url, m.title, m.relevance_score
                FROM media_resources m
                JOIN media_object_links mol ON mol.media_id = m.id
                WHERE mol.object_id = ?
                ORDER BY m.relevance_score DESC, m.id DESC
            """, (oid,))
            lines.append("")
            lines.append("### Recursos audiovisuales (YouTube)")
            if media:
                for m in media:
                    title = m['title'] or m['url']
                    lines.append(f"- [{title}]({m['url']}) (relevancia {m['relevance_score']})")
            else:
                lines.append("- N/D")

            lines.append("")
            lines.append("---")
            lines.append("")

        # general media
        all_media = q(cur, "SELECT url, title, relevance_score FROM media_resources ORDER BY relevance_score DESC, id DESC")
        if all_media:
            lines.append("## Recursos generales")
            for m in all_media:
                title = m['title'] or m['url']
                lines.append(f"- [{title}]({m['url']}) (relevancia {m['relevance_score']})")
            lines.append("")

        lines.append("## Situación actual percibida (resumen final)")
        lines.append("")
        traj_img = os.path.join(BASE_DIR, 'docs', 'images', '1i 2i 3i Trayectoria plana.png')
        if os.path.exists(traj_img):
            lines.append("![Trayectorias y posición aproximada actual de 1I, 2I y 3I](../docs/images/1i%202i%203i%20Trayectoria%20plana.png)")
            lines.append("")
        lines.append("- **1I/'Oumuamua**: objeto interestelar (no se detectó coma/polvo concluyente), en alejamiento; última ubicación **aproximada** por efeméride Horizons (geocéntrica) — ver sección del objeto. Muy débil/lejana para observación directa rutinaria.")
        lines.append("- **2I/Borisov**: cometa interestelar activo (coma/polvo), ya muy distante post-perihelio; ubicación aproximada por efeméride Horizons.")
        lines.append("- **3I/ATLAS**: cometa interestelar activo (alta v∞), en seguimiento; ubicación aproximada por efeméride Horizons (más cercano que 1I/2I en distancia actual, sujeto a actualización).")
        lines.append("- *Las posiciones/magnitudes mostradas son efemérides calculadas (aprox., no astrometría registrada en BD). Actualizar con `ingest_ephemeris_horizons.py` + regenerar dashboard.*")
        lines.append("")
        lines.append("## Cómo evoluciona esta página")
        lines.append("")
        lines.append("- Este dashboard se regenera desde la base de datos (`data/db/iso.db`) y refleja el estado actual.")
        lines.append("- Al ingerir nuevas observaciones, parámetros físicos, composición o publicaciones, la próxima generación mostrará los cambios.")
        lines.append("- Los datos con baja confianza o placeholders se presentan como pendientes/N/D hasta ser reemplazados por mediciones consolidadas.")
        lines.append("")

        with open(out_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        cp['status'] = 'completed'
        cp['finished_at'] = datetime.utcnow().isoformat() + 'Z'
        cp.setdefault('generated', []).append(out_path)
        cp['generated'] = cp['generated'][-20:]
        cp['last_dashboard'] = out_path
        save_checkpoint(cp)

        elapsed = time.time() - start
        log("=" * 60)
        log("FIN DASHBOARD")
        log(f"Tiempo transcurrido: {elapsed:.3f}s")
        log(f"Generado: {out_path}")
        log("=" * 60)
        print(f"Dashboard generated: {out_path}")
        return out_path
    finally:
        conn.close()


def main():
    p = argparse.ArgumentParser(description='Generar dashboard evolutivo de objetos interestelares')
    p.add_argument('--reanudar', action='store_true')
    p.add_argument('--force', action='store_true')
    args = p.parse_args()
    generate_dashboard(resumable=args.reanudar, force=args.force)


if __name__ == '__main__':
    main()
