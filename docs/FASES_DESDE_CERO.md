# Fases ejecutables desde cero (ISO Tracker)

> Última revisión: **2026-11-25**.
> Aquí **"desde cero"** significa: repo recién clonado, `data/db/iso.db` inexistente/vacía, sin checkpoints ni cachés.
> Lo que figura como **verificado** se probó el 2026-11-25 en una copia temporal del repo, **nunca** sobre la BD real. Los pasos que consultan APIs quedan marcados como **no verificados en esa prueba**.
> Relacionado: [`INSTALACION_Y_CONFIGURACION.md`](INSTALACION_Y_CONFIGURACION.md) (instalación) y [`PROCESOS_MANUALES_Y_AUTOMATICOS.md`](PROCESOS_MANUALES_Y_AUTOMATICOS.md) (manual vs automático).

## 1. Resumen ejecutivo

| Bloque / fase | ¿Se ejecuta desde cero? | Condición indispensable |
| --- | --- | --- |
| **Fase 0 — Preparación** | **Sí, pero manualmente** | Aplicar `config/schema.sql` a mano: **ningún script lo hace**. Los patches sí los aplican los `apply_patch_*.py`. |
| **Fase 1 — Ingesta inicial** | **Sí** | Después de `schema.sql`. `ingest_init.py` es idempotente. |
| **Fase 2 — Aliases / físicos** | **Sí (núcleo)** | `apply_patch_fase2.py` + `run_fase2_aliases.py --force` + `run_fase2_rest.py --force`. SBDB/curated dependen de red para datos reales. |
| **Fase 3 — Reportes, infografía, dashboard** | **Sí** | Con las tablas base creadas; toleran `publications=0` y `observations=0` (verificado). |
| **Fase 4 — Búsqueda retrospectiva** | **Sí** | `apply_patch_fase4.py` + `run_retro_search.py`. Sin archivos `data/raw/` no hay candidatos nuevos. |
| **Fase 5 — Orquestador / verificación** | **Sí (verificación)** | `check_status.py` funciona con la BD creada. El orquestador **no** recrea esquemas. |
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
| Ingesta inicial | `ingest_init.py` · `data/objects.json` | Esquema base | Sí (`INSERT OR IGNORE`) | No duplica filas | N | Falla sin esquema |
| Identificación | `apply_patch_identificacion.py` | Esquema base (lee `object_publications`); se ejecuta después de la ingesta en la prueba | Sí (inserciones ignoradas / columnas condicionales) | No | N | Falla sin esquema |
| Patch Fase 2 | `apply_patch_fase2.py` | Esquema base | Sí | No | N | Crea tablas/vistas vacías |
| Patch Fase 4 | `apply_patch_fase4.py` | Esquema base | Sí | No | N | Crea `retro_candidates` vacías |
| Patch Fase 6 | `apply_patch_fase6.py` | Esquema base | Sí | No | N | Crea tablas de multimedia vacías |
| Aliases Fase 2 | `run_fase2_aliases.py --force` | Patch Fase 2 + objetos cargados | Sí, con checkpoint | No; inserta aliases nuevos | N | Sin objetos no produce aliases |
| Resto Fase 2 | `run_fase2_rest.py --force` | Patch Fase 2 + objetos | Sí, con checkpoint | No; inserta `physical_params`/`composition`/`activity` curados | N | Funciona con valores curados locales |
| Físicos SBDB | `ingest_physical_sbdb.py --force` | Esquema base | Sí por `(object_id, param, source_url)` | Actualiza/inserta parámetros | **S** | Sin red, sin datos SBDB |
| Físicos curados | `ingest_physical_curated.py --force` | Esquema base | Sí por `(object_id, param, source_url)` | Actualiza/inserta dimensiones curadas | N | Sin datos locales no aporta (el núcleo ya los carga con `run_fase2_rest.py`) |
| Papers | `collect_metadata_openalex.py` · `config/metadata_scope.json` | Esquema base + ventana/alias definida | Sí, con checkpoint por ventana | No toca tablas científicas | **S** | Sin ventana nueva no hay carga útil; requiere decisión humana |
| Abstracts | `backfill_abstracts.py --refrescar-cortos N` | `publications` con filas | Sí | Solo actualiza `publications.abstract` | **S** | Sin papers no hace nada útil |
| Efemérides | `ingest_ephemeris_horizons.py --date ... --force` | Esquema base | Sí (por fecha/origen) | Inserta observaciones **calculadas**, no astrometría | **S** | Sin red no hay efemérides |
| Reporte | `generate_report.py --force` / `--reanudar` | Tablas base | Sí, con checkpoint | **Sí:** reescribe `reports/weekly/...`; no toca BD científica | N | Funciona con conteos en cero |
| Infografía (prompt) | `generate_infographic_prompt.py --force` | Reporte/Datos base | Sí, con checkpoint | **Sí:** reescribe `reports/infografia_prompt_*.md` | N | La imagen se genera fuera del repo |
| Dashboard | `generate_dashboard.py --force` | Tablas base | Sí, con checkpoint | **Sí:** `dashboard_latest.md` + timestamped y bloques README | N | Verificado con BD mínima |
| Actividad | `generate_reference_activity.py --force` (llamado por el dashboard) | Tablas base; se enriquece con refs | Siempre regenera (el flag `--force` no se consulta) | **Sí:** `docs/REFERENCE_ACTIVITY.md`, `docs/ref_activity/*`, `docs/images/ref_activity*`, bloque README | N | Verificado antes y después del patch web |
| Retro | `run_retro_search.py --reanudar/--force` | Patch Fase 4 + `data/raw/` | Sí, con checkpoint | Inserta candidatos; no borra revisiones | N | Sin archivos raw no encuentra candidatos |
| Patch refs web | `config/schema_web_references_patch.sql` (comando manual §2) | Ninguno | Sí (`IF NOT EXISTS`) | No | N | Sin él, `curate_web_references.py` falla |
| Curación refs web | `curate_web_references.py --force --skip-validate` | Patch refs web + `config/web_references.json` | Sí, con checkpoint | Actualiza por URL e inserta; rechazadas se guardan con nota y se ocultan | N (con `--skip-validate`) | Sin patch, falla; sin config, no carga nada |
| Validador refs | `validate_web_references.py --skip-http` | Config de refs | Sí | **Sí:** escribe sugerencias en el config; **no decide** | N (con `--skip-http`) | Revisar el diff del config después |
| Curación multimedia | `curate_media.py --force --skip-validate` | Patch Fase 6 + `config/media_links.json` | Sí, con checkpoint | Inserta/actualiza recursos por URL | N (con `--skip-validate`) | Sin patch, falla |
| Reporte multimedia | `update_report_with_media.py` | `media_resources` | Reescribe la sección | **Sí:** sección multimedia del reporte | N | Sin media, sección vacía |
| Verificación | `verify_tables.py`, `scripts/utils/check_status.py` | BD creada | Sí (solo lectura) | No | N | Funciona apenas creada la BD |
| Orquestador | `master_orchestrator.py status\|faseN\|all` | `config/orchestrator.json` | `status` sí; `all` depende de cada fase | Ejecuta fases; **no aplica esquema ni pasa flags** | Según fase | Con BD vacía, Fase 1 falla: usar el orden manual §4 |

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
| `metadata_discovery.py` | Es módulo de apoyo (sin `main()`), no un script lanzable desde cero. |
| `scripts/skills/*` | Son utilidades bajo demanda, no fases. |

## 6. Precauciones

1. **Nunca probar sobre la BD real**: trabajar en una copia del repo; `data/db/iso.db` versionada es el estado de producción.
2. Hacer copia de seguridad antes de aplicar patches o `--force`.
3. `--force` descarta el checkpoint y vuelve a generar; `--reanudar` conserva el progreso. Ninguno borra tablas científicas.
4. Los archivos bajo `reports/`, `docs/REFERENCE_ACTIVITY.md`, `docs/ref_activity/*` y los bloques README **sí se regeneran/sobrescriben**; forman parte de la salida derivada.
5. Ejecutar siempre desde la raíz del repo: los scripts ya resuelven sus rutas de forma relativa.

## 7. Documentación relacionada

- [`INSTALACION_Y_CONFIGURACION.md`](INSTALACION_Y_CONFIGURACION.md) — clon, requisitos, configs y `ISO_CA_BUNDLE`.
- [`PROCESOS_MANUALES_Y_AUTOMATICOS.md`](PROCESOS_MANUALES_Y_AUTOMATICOS.md) — qué decide una persona y qué ejecuta el script.
- [`EXECUTION.md`](EXECUTION.md) — comandos por fase.
- [`ESTADO_CARGA.md`](ESTADO_CARGA.md) — qué está cargado y cómo continuar una ronda.
- [`LECCIONES_METADATOS.md`](LECCIONES_METADATOS.md) — rutas alternativas cuando OpenAlex devuelve `429`.
