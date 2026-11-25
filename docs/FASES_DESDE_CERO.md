# Fases ejecutables desde cero (ISO Tracker)

> Última revisión: **2026-11-25**.
> Aquí **"desde cero"** significa: repo recién clonado, `data/db/iso.db` inexistente/vacía, sin checkpoints ni cachés.
> Lo que figura como **verificado** se probó el 2026-11-25 en una copia temporal del repo, **nunca** sobre la BD real. Los pasos que consultan APIs quedan marcados como **no verificados en esa prueba**.
> Relacionado: [`INSTALACION_Y_CONFIGURACION.md`](INSTALACION_Y_CONFIGURACION.md) (instalación) y [`PROCESOS_MANUALES_Y_AUTOMATICOS.md`](PROCESOS_MANUALES_Y_AUTOMATICOS.md) (manual vs automático).

## 1. Resumen ejecutivo

| Bloque / fase | ¿Se ejecuta desde cero? | Condición indispensable |
| --- | --- | --- |
| **Fase 0 — Preparación** | **Sí, pero manualmente** | Aplicar `config/schema.sql` a mano: **ningún script lo hace**. Los patches sí los aplican los `apply_patch_*.py`. |
| **Fase 1 — Ingesta inicial** | **Sí, una sola vez** | Después de `schema.sql`. `ingest_init.py` protege `objects`, pero **duplica** orbitales/actividad/provenance si se repite. |
| **Fase 2 — Aliases / físicos** | **Sí (núcleo)** | `apply_patch_fase2.py` + `run_fase2_aliases.py --force` + `run_fase2_rest.py --force`. SBDB/curated dependen de red para datos reales. |
| **Fase 3 — Reportes, infografía, dashboard** | **Sí** | Con las tablas base creadas; toleran `publications=0` y `observations=0` (verificado). |
| **Fase 4 — Búsqueda retrospectiva** | **Sí** | `apply_patch_fase4.py` + `run_retro_search.py`. Sin archivos `data/raw/` no hay candidatos nuevos. |
| **Fase 5 — Orquestador / verificación** | **Sí (verificación)** | `check_status.py` necesita el patch Fase 4 aplicado (consulta `retro_candidates`). El orquestador **no** recrea esquemas. |
| **Fase 6 — Multimedia** | **Sí** | `apply_patch_fase6.py` + `curate_media.py` (config de videos ya incluida en el repo). |
| **Referencias web (extra)** | **Sí, pero manualmente** | Aplicar `config/schema_web_references_patch.sql` a mano: **ningún script lo aplica**. |
| **Gráfico de actividad (extra)** | **Sí** | Lo invoca `generate_dashboard.py`; se enriquece cuando hay refs curadas. |
| **Papers (OpenAlex / arXiv+Crossref)** | **Sí, con decisión + red** | Definir ventana/alias nuevo en `config/metadata_scope.json`. No verificado en la prueba. |
| **Efemérides (JPL Horizons)** | **Sí, con fecha + red** | `--date YYYY-MM-DD --force`. No verificado en la prueba. |

**Conclusión corta:** casi todo el núcleo se reconstruye desde cero, pero **la Fase 0 no es automática**: hoy hay que ejecutar **dos sentencias de esquema a mano** (`schema.sql` y, si se quieren referencias web, `schema_web_references_patch.sql`). El orquestador no las aplica.

## 2. Hallazgo crítico: la Fase 0 no se ejecuta sola

- `config/orchestrator.json` tiene la Fase 0 con `"scripts": []` (corregido el 2026-11-25): los `.sql` **no son código Python** y `master_orchestrator.py` los lanzaría con `sys.executable`, así que se excluyeron del pipeline.
- Ningún `apply_patch_*.py` aplica `config/schema.sql`. Comprobado en una BD vacía:
  - `ingest_init.py` → `sqlite3.OperationalError: no such table: objects`.
  - `apply_patch_identificacion.py` → `sqlite3.OperationalError: no such table: object_publications`.
  - `generate_report.py` y `generate_dashboard.py` también fallan sin las tablas base.
- Ningún script aplica `config/schema_web_references_patch.sql`: sin él, `curate_web_references.py` no encuentra `curated_references`.

Por eso el orden seguro empieza con dos comandos de esquema ejecutados desde la raíz del repo (funcionan en Windows/Linux/macOS porque usan solo `sqlite3` + `pathlib` de la stdlib):

```bash
# Esquema base (Fase 0) — imprescindible
python -c "import sqlite3,pathlib; c=sqlite3.connect('data/db/iso.db'); c.executescript(pathlib.Path('config/schema.sql').read_text(encoding='utf-8')); c.commit(); c.close()"
```

```bash
# Patch de referencias web — solo si se van a cargar refs curadas
python -c "import sqlite3,pathlib; c=sqlite3.connect('data/db/iso.db'); c.executescript(pathlib.Path('config/schema_web_references_patch.sql').read_text(encoding='utf-8')); c.commit(); c.close()"
```

Ambos usan `CREATE TABLE IF NOT EXISTS`: **no borran ni sobrescriben** datos existentes.

## 3. Matriz detallada

Leyenda de red: **S** = consulta APIs/internet; **N** = funciona sin red (con los archivos incluidos).

| Paso | Script / config | Prerrequisito | Idempotente | ¿Sobrescribe algo? | Red | Riesgo si se corre solo |
| --- | --- | --- | --- | --- | --- | --- |
| Esquema base | `config/schema.sql` (comando manual §2) | Ninguno | Sí (`IF NOT EXISTS`) | No; solo crea tablas | N | Ninguno; es el punto de partida |
| Ingesta inicial | `ingest_init.py` · `data/objects.json` | Esquema base | **Parcial:** `objects` usa `INSERT OR IGNORE`, pero `orbital_elements`, `activity` y `provenance_log` usan `INSERT` directo → **repetir duplica** | Solo inserta | N | Falla sin esquema; ejecutar **una sola vez** |
| Identificación | `apply_patch_identificacion.py` | Esquema base (lee `object_publications`); después de la ingesta en la prueba | **Parcial:** upsert por `object_id`, pero inserta provenance en cada corrida y recrea la vista con `DROP VIEW IF EXISTS` | `UPDATE` de identificación + provenance duplicada | N | Falla sin esquema; no repetir en una BD ya cargada |
| Patch Fase 2 | `apply_patch_fase2.py` | Esquema base | Sí | No | N | Crea tablas/vistas vacías |
| Patch Fase 4 | `apply_patch_fase4.py` | Esquema base | Sí | No | N | Crea `retro_candidates` vacías; sin él falla `check_status.py` |
| Patch Fase 6 | `apply_patch_fase6.py` | Esquema base | Sí | No | N | Crea tablas de multimedia vacías |
| Aliases Fase 2 | `run_fase2_aliases.py --force` | Patch Fase 2 + objetos cargados | Sí: hay UNIQUE real `(object_id, alias)` + checkpoint | No; inserta aliases nuevos | N | Con `objects` vacío marca `completed` con 0 aliases (**falso éxito**) |
| Resto Fase 2 | `run_fase2_rest.py --force` | Patch Fase 2 + objetos | **Solo por checkpoint:** no hay UNIQUE en esas tablas; `--force` reinicia el checkpoint y puede duplicar | Inserta placeholders de baja confianza | N | Funciona con valores locales; sin checkpoint, repetir duplica |
| Físicos SBDB | `ingest_physical_sbdb.py --force` | Esquema base | **No garantizada:** sin UNIQUE en `physical_params`; el docstring lo afirma pero la BD no lo respalda | `--force` **borra** los params con `source_url` de SBDB y los reinserta | **S** | Sin red no hay datos; `--force` sobre BD real borra un subconjunto |
| Físicos curados | `ingest_physical_curated.py --force` | Esquema base | **No garantizada** por la misma razón | `--force` borra params NASA de ciertos `param` | N | Repetir sin checkpoint duplica; el núcleo ya los carga con `run_fase2_rest.py` |
| Papers | `collect_metadata_openalex.py` · `config/metadata_scope.json` | Esquema base + ventana/alias definida | Sí: upsert por DOI/arXiv + PK real en `object_publications` + checkpoints | Actualiza DOI/arXiv/journal/abstract; no toca tablas científicas | **S** | Sin ventana nueva no hay carga útil; requiere decisión humana |
| Abstracts | `backfill_abstracts.py --refrescar-cortos N` | `publications` con filas | Sí | Solo actualiza `publications.abstract` cuando el nuevo es más largo | **S** | Sin papers no hace nada útil |
| Efemérides | `ingest_ephemeris_horizons.py --date ... --force` | Esquema base; la script agrega columnas si faltan | **No garantizada:** sin UNIQUE en `observations`; `--force` borra solo la fecha indicada | Inserta observaciones **calculadas**, no astrometría | **S** | Sin `--force`, repetir la misma fecha duplica; sin red no hay efemérides |
| Reporte | `generate_report.py --force` / `--reanudar` | Tablas base | Sí, con checkpoint | **Sí:** crea `reports/weekly/...` timestampado; no toca BD científica | N | Funciona con conteos en cero |
| Infografía (prompt) | `generate_infographic_prompt.py --force` | **Ninguno:** no importa `sqlite3`, funciona sin BD | Sí, con checkpoint | **Sí:** crea `reports/infografia_prompt_*.md` | N | El más seguro en "cero absoluto"; la imagen se genera fuera del repo |
| Dashboard | `generate_dashboard.py --force` | Tablas base (`objects` obligatorio); `dashboard_display.json` con defaults | Sí, con checkpoint | **Sí:** timestamped + bloques README. **No crea `dashboard_latest.md`** (hay que copiarlo, §4.1) | N | Verificado con BD mínima; sin `objects` falla |
| Actividad | `generate_reference_activity.py --force` (llamado por el dashboard) | `publications` y `media_resources`; refs web dentro de `try` | Siempre regenera (el flag `--force` no se consulta) | **Sí:** `docs/REFERENCE_ACTIVITY.md`, `docs/ref_activity/*`, `docs/images/ref_activity*`, bloque README | N | Verificado antes y después del patch web |
| Retro | `run_retro_search.py --reanudar/--force` | Patch Fase 4 + `data/raw/` | Sí, con checkpoint y dedupe por archivo/e | Inserta candidatos; no borra revisiones | N | Sin archivos raw marca `completed` con 0 candidatos |
| Patch refs web | `config/schema_web_references_patch.sql` (comando manual §2) | Ninguno | Sí (`IF NOT EXISTS`) | No | N | Sin él, `curate_web_references.py` falla |
| Curación refs web | `curate_web_references.py --force --skip-validate` | Patch refs web + `config/web_references.json` | Sí, con checkpoint + UNIQUE en `url` | Actualiza por URL e inserta; rechazadas se guardan con nota y se ocultan | N (con `--skip-validate`) | Sin patch falla; sin config crea plantilla vacía y marca `completed` (**falso éxito**) |
| Validador refs | `validate_web_references.py --skip-http` | Solo config; **no usa BD** | Sí | **Sí:** reescribe tres campos de sugerencia en el config; **no decide** | N (con `--skip-http`) | Revisar el diff del config; sin config termina sin hacer nada |
| Curación multimedia | `curate_media.py --force --skip-validate` | Patch Fase 6 + `config/media_links.json` | Sí: UNIQUE en `url` + checkpoint | Inserta/actualiza recursos por URL | N (con `--skip-validate`) | Sin patch falla; sin config crea plantilla y marca `completed` sin videos |
| Reporte multimedia | `update_report_with_media.py` | `media_resources`, `media_object_links`, `objects` | Reescribe la sección | **Sí:** crea `reports/weekly/ISO_Report_with_Media_<ts>.md` | N | Sin media escribe nota "No hay vídeos añadidos aún" |
| Verificación | `verify_tables.py`, `scripts/utils/check_status.py` | BD creada **con el patch Fase 4 aplicado** (consulta `retro_candidates`) | Sí (solo lectura) | No | N | Antes del patch Fase 4 falla con `no such table: retro_candidates` |
| Orquestador | `master_orchestrator.py status\|faseN\|all` | `config/orchestrator.json` | `status` sí; `all` depende de cada fase | Ejecuta fases; **no aplica esquema ni pasa flags**; errores se loguean y continúa | Según fase | Con BD vacía no reconstruye: Fase 0 vacía, Fase 1 falla, `SKIP` silencioso |

## 4. Orden seguro y verificado

### 4.1 Núcleo mínimo (BD funcional, sin papers ni efemérides)

```bash
cd "<ruta-del-repo>"

# 0) Esquema base — manual, imprescindible
python -c "import sqlite3,pathlib; c=sqlite3.connect('data/db/iso.db'); c.executescript(pathlib.Path('config/schema.sql').read_text(encoding='utf-8')); c.commit(); c.close()"

# 1) Objetos + cronología + patches
python ingest_init.py
python apply_patch_identificacion.py
python apply_patch_fase2.py
python apply_patch_fase4.py
python apply_patch_fase6.py

# 2) Poblado curado local (Fase 2 corta)
python scripts/orchestrator/run_fase2_aliases.py --force
python scripts/orchestrator/run_fase2_rest.py --force

# 3) Salidas regenerables
python scripts/orchestrator/generate_report.py --force
python scripts/orchestrator/generate_infographic_prompt.py --force
python scripts/orchestrator/generate_dashboard.py --force

# 4) Verificación
python verify_tables.py
python scripts/utils/check_status.py
```

**Resultado medido tras este bloque:** 17 tablas, 3 objetos, 15 aliases, `physical_params=3`, `composition=3`, `activity=6`, `publications=0`, `observations=0`, `media_resources=0`, `curated_references` aún no existe. Todos los comandos terminaron con código 0.

Dos precauciones sobre este bloque:

- `ingest_init.py` y `apply_patch_identificacion.py` se ejecutan **una sola vez**. Repetirlos duplica `orbital_elements`/`activity`/`provenance_log` y la provenance de identificación, respectivamente (ver §6).
- `generate_dashboard.py` **no crea `reports/dashboard_latest.md`**: escribe el archivo timestampado. Para publicar la "última" versión, copiarlo desde el checkpoint:

```bash
python -c "import json,shutil,pathlib; d=json.loads(pathlib.Path('.metadata_checkpoints/dashboard_checkpoint.json').read_text(encoding='utf-8')); shutil.copyfile(d['last_dashboard'],'reports/dashboard_latest.md')"
```

### 4.2 Complemento: referencias web y multimedia

```bash
# Patch web — manual
python -c "import sqlite3,pathlib; c=sqlite3.connect('data/db/iso.db'); c.executescript(pathlib.Path('config/schema_web_references_patch.sql').read_text(encoding='utf-8')); c.commit(); c.close()"

python scripts/orchestrator/curate_web_references.py --force --skip-validate
python scripts/orchestrator/curate_media.py --force --skip-validate
python scripts/orchestrator/update_report_with_media.py
python scripts/orchestrator/generate_reference_activity.py --force
python scripts/orchestrator/generate_dashboard.py --force
```

**Resultado medido:** 19 tablas, `curated_references=4`, `curated_reference_object_links=4`, `media_resources=5`, `media_object_links=4`. `--skip-validate` se usó para que la prueba no dependa de HTTP; en operación normal el validador es opcional y **solo sugiere**.

### 4.3 Complementos dependientes de red (no ejecutados en la prueba)

Estos **no** se verificaron en la BD temporal porque requieren APIs y, en algunos casos, una decisión previa:

```bash
# Papers: crear primero la ventana/alias en config/metadata_scope.json
python scripts/orchestrator/collect_metadata_openalex.py --alias <alias_nuevo> --dry-run
python scripts/orchestrator/collect_metadata_openalex.py --alias <alias_nuevo>

# Abstracts truncados
python scripts/orchestrator/backfill_abstracts.py --refrescar-cortos 200

# Efemérides geocéntricas (calculadas, no astrometría observada)
python scripts/orchestrator/ingest_ephemeris_horizons.py --date <YYYY-MM-DD> --force

# Parámetros físicos desde SBDB (JPL; requiere red)
python scripts/orchestrator/ingest_physical_sbdb.py --force

# Parámetros curados locales (no requiere red)
python scripts/orchestrator/ingest_physical_curated.py --force

# Validación HTTP de refs (opcional; el validador no auto-acepta)
python scripts/orchestrator/validate_web_references.py --only-pending
```

## 5. Qué NO se reconstruye solo con "desde cero"

| Limitación | Por qué |
| --- | --- |
| El estado actual de la BD real | La BD real tiene 407 publicaciones, 449 vínculos, 638 entradas de provenance y 6 observaciones. Eso viene de rondas de ingesta con red y decisiones acumuladas, **no** del núcleo local. |
| Ventanas de papers | Hay que crear `desde = último_hasta + 1d`, `hasta = hoy` y un alias nuevo en `config/metadata_scope.json`; el recolector no lo decide. |
| Efemérides | Requieren fecha explícita y JPL Horizons. |
| Aceptación de fuentes | Videos y referencias web se eligen y puntúan a mano; el validador solo sugiere. |
| Esquemas | `schema.sql` y `schema_web_references_patch.sql` siguen siendo manuales (§2). |
| `master_orchestrator.py all` | No aplica esquemas, no pasa `--force/--reanudar/--date` y con BD vacía fallaría en Fase 1. Para reconstruir, usar el orden manual §4. |
| `dashboard_latest.md` | `generate_dashboard.py` solo escribe el timestampado; la copia a `dashboard_latest.md` hay que hacerla aparte (§4.1). |
| `metadata_discovery.py` | Es módulo de apoyo (sin `main()`), no un script lanzable desde cero. |
| `scripts/skills/*` | Son utilidades bajo demanda, no fases. |

## 6. Precauciones

1. **Nunca probar sobre la BD real**: trabajar en una copia del repo; `data/db/iso.db` versionada es el estado de producción.
2. Hacer copia de seguridad antes de aplicar patches o `--force`.
3. `--force` descarta el checkpoint y vuelve a generar, **pero en SBDB/curados/efemérides también borra un subconjunto** (por `source_url`, por `param` o por fecha) antes de reinsertar. `--reanudar` conserva el progreso.
4. **Idempotencia real:** la BD tiene UNIQUE en `objects.designation`, `publications.doi/arxiv_id`, `object_aliases(object_id, alias)`, `object_publications`, `media_resources.url`, `curated_references.url` y `object_identification.object_id`. **No** lo tiene en `physical_params`, `activity`, `observations`, `orbital_elements` ni `provenance_log`: los `INSERT OR IGNORE` de esos ingestores no evitan duplicados por sí solos; dependen de checkpoints o de `--force`. En la BD real ya hay provenance duplicada por ejecutar `apply_patch_identificacion.py` más de una vez.
5. **Falsos éxitos:** `run_fase2_aliases.py` con `objects` vacío, `run_retro_search.py` sin `data/raw`, y `curate_media.py`/`curate_web_references.py` sin su JSON de config marcan el checkpoint como `completed` sin cargar datos. Revisar siempre los conteos con `check_status.py`.
6. Los archivos bajo `reports/`, `docs/REFERENCE_ACTIVITY.md`, `docs/ref_activity/*` y los bloques README **sí se regeneran/sobrescriben**; forman parte de la salida derivada. El validador de refs también reescribe tres campos de sugerencia en `config/web_references.json`.
7. Ejecutar siempre desde la raíz del repo: los scripts ya resuelven sus rutas de forma relativa.

## 7. Documentación relacionada

- [`INSTALACION_Y_CONFIGURACION.md`](INSTALACION_Y_CONFIGURACION.md) — clon, requisitos, configs y `ISO_CA_BUNDLE`.
- [`PROCESOS_MANUALES_Y_AUTOMATICOS.md`](PROCESOS_MANUALES_Y_AUTOMATICOS.md) — qué decide una persona y qué ejecuta el script.
- [`EXECUTION.md`](EXECUTION.md) — comandos por fase.
- [`EJEMPLO_FLUJO_COMPLETO.md`](EJEMPLO_FLUJO_COMPLETO.md) — traza real de fuente → recolección → normalización → BD → reporte.
- [`ESTADO_CARGA.md`](ESTADO_CARGA.md) — qué está cargado y cómo continuar una ronda.
- [`LECCIONES_METADATOS.md`](LECCIONES_METADATOS.md) — rutas alternativas cuando OpenAlex devuelve `429`.
