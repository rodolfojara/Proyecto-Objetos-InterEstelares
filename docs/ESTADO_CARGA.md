# Estado de carga (ISO Tracker) — qué hay cargado y hasta dónde

> Documento operativo para saber **qué fue lo último cargado** por objeto/fuente y cómo continuar sin perder trazabilidad. Actualizar este archivo (o regenerar sus valores desde BD/config) cada vez que se complete una ingesta.
> Última revisión: **2026-11-08**.

## Resumen por objeto (metadatos/papers — OpenAlex)

| Objeto | Papers vinculados | Último `published_at` hallado (BD) | Última ventana cubierta (`desde`→`hasta`, alias) en `config/metadata_scope.json` | Estado |
|---|---:|---|---|---|
| 1I/'Oumuamua | 189 | 2026-09-21 | 2017-11-07 → **2026-11-07** (`1i-2025`, cola) | Cobertura de ventana al día (hasta 2026-11-07); puede haber papers nuevos al extender a fecha actual. *Cobertura de ventana ≠ último paper hallado.* |
| 2I/Borisov | 99 | 2026-10-01 | 2019-09-24 → **2026-11-07** (`2i-2026`, cola) | Cobertura al día (hasta 2026-11-07). |
| 3I/ATLAS | 161 | 2026-11-05 | 2025-07-09 → **2026-11-07** (`3i-2026b`, cola) | Cobertura al día (hasta 2026-11-07). |

- Fuente de verdad de ventanas/aliases: `config/metadata_scope.json`.
- Verificación rápida: `SELECT o.designation, COUNT(*), MIN(p.published_at), MAX(p.published_at) FROM objects o JOIN object_publications op ON op.object_id=o.id JOIN publications p ON p.id=op.publication_id GROUP BY o.id;`
- Pendiente al 2026-11-08: extender colas **1 día** (o a la fecha actual) si se desea refrescar (nueva ventana por objeto: `desde = (último hasta + 1d)`, `hasta = hoy`, alias nuevo).

## Efemérides / posición aproximada (Horizons, calculada — no astrometría registrada)

| Objeto | Fecha efeméride en BD | Campos | Estado |
|---|---|---|---|
| 1I/'Oumuamua | 2026-11-07 | RA/Dec, Δ (Tierra), r (Sol), mag (efeméride) | Cargado (geocéntrico, aprox.). |
| 2I/Borisov | 2026-11-07 | RA/Dec, Δ, r, mag | Cargado. |
| 3I/ATLAS | 2026-11-07 | RA/Dec, Δ, r, mag | Cargado. |

- Script: `python scripts/orchestrator/ingest_ephemeris_horizons.py --date YYYY-MM-DD --force` + regenerar dashboard.

## Multimedia (YouTube, curación manual)

| Fuente | Config | Registros en BD | Estado |
|---|---|---:|---|
| YouTube (validados oEmbed, relevancia/canal) | `config/media_links.json` | 5 (en `media_resources`/links) | Cargados/curados (verificados). Agregar solo URLs `watch` reales evaluadas. |

- Script: `python scripts/orchestrator/curate_media.py [--reanudar|--force]`.

## Referencias web curadas (complemento, curación manual + validador por reglas)

| Fuente | Config | Registros en BD | Estado |
|---|---|---:|---|
| Referencias web (evaluadas ref. por ref.) | `config/web_references.json` (+ reglas `config/web_reference_rules.json`) | 4 (3 `accepted` visibles, 1 `rejected` guardada con nota/oculta) | **Prueba de flujo OK (2026-11-08):** 3 NASA Science (2I, 1I, 3I) aceptadas (valor 8–9) + 1 Wikipedia rechazada con motivo (almacenada, no mostrada). Visibles en dashboard por objeto y Top destacadas. |

- Flujo: agregar/evaluar en config → (opcional) `python scripts/orchestrator/validate_web_references.py` (sugerencias; aprendizaje = refinar reglas) → revisar/ajustar `status/value/evaluation_note` → `python scripts/orchestrator/curate_web_references.py` → `python scripts/orchestrator/generate_dashboard.py --force`.
- Agente: `scripts/agents/validador_referencias_web.md`.

## Método estándar de actualización (papers + YouTube + referencias web)

Ejecutar **por tipo de fuente**, registrando fecha y resultado (evita olvidar qué se cargó). Orden sugerido cuando se hace una “ronda” de actualización:

1. **Papers (metadatos, por objeto/alias):** detectar último `hasta`/alias en `config/metadata_scope.json` y `MAX(published_at)` en BD → crear ventana(s) cola por objeto (`desde = último_hasta+1d`, `hasta = hoy`, alias nuevo) → `collect_metadata_openalex.py --alias <nuevo> --dry-run` → ejecución real → confirmar conteos.
2. **Efemérides (opcional en la misma ronda):** `ingest_ephemeris_horizons.py --date <hoy> --force`.
3. **YouTube (curación manual):** agregar URLs reales evaluadas en `config/media_links.json` → `curate_media.py`.
4. **Referencias web (curación manual, tu método):** evaluar ref. por ref. (confiable → consistencia/calidad; guardar “goyitas”, incluso desactualizadas si bien informadas, con nota) → cargar en `config/web_references.json` → (opcional) validador → `curate_web_references.py`.
5. **Regenerar y publicar:** `generate_dashboard.py --force` → actualizar este `ESTADO_CARGA.md` con fechas/conteos/últimos alias → commit & push (`config/*`, `data/db/iso.db`, checkpoints generados, `reports/dashboard_latest.md` + timestamped, docs).

> Regla práctica: **no asumir** “ya está al día”; siempre contrastar (a) última ventana/alias y (b) `MAX(published_at)` por objeto, y anotar aquí la fecha de la última ronda. Los tres tipos de carga (papers, YouTube, web) son **independientes**: completar uno no implica completar los otros.