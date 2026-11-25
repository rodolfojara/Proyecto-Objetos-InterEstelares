# Procesos manuales y automatizados (ISO Tracker)

> Última revisión: **2026-11-25**. Fuentes: `config/orchestrator.json`, `scripts/orchestrator/`, `docs/ESTADO_CARGA.md`, `README.md`.
> Este documento responde a: **¿qué se hace solo y dónde hace falta una persona?**

## 1. Aclaración clave: dos tipos de "automatización"

| Nivel | Qué significa aquí | Estado actual |
| --- | --- | --- |
| **Automatización por script** | Una vez lanzado, el script realiza el trabajo sin intervención paso a paso: usa checkpoints, locks, commits parciales, idempotencia y verificación final. | **Sí, implementada** en la mayoría de los scripts. |
| **Automatización por calendario** (cron / Task Scheduler / GitHub Actions) | El proceso se dispara solo en un horario, sin que nadie ejecute el comando. | **No configurada.** `config/orchestrator.json` indica `"mode": "manual"` y `"Los scripts NO corren 24/7"`. |

Por eso la mayoría de los procesos son **semiautomáticos**: *una persona (o el agente, a pedido) decide cuándo lanzarlos; el script hace el trabajo mecánico sin supervisión intermedia*.

## 2. Mapa rápido

| Categoría | Procesos | Qué decide la persona |
| --- | --- | --- |
| **Manual puro** (juicio humano) | Curación de YouTube y referencias web; definición de ventanas/alias de papers; evaluación de confiabilidad y `value_score`; elección del Top N visible; decisión de publicar; generación de imagen con IA externa. | Qué se considera confiable, qué se guarda aunque sea viejo pero bien informado, qué se descarta y con qué nota. |
| **Semiautomáticos** (disparo manual + ejecución automática) | Patches/ingesta inicial, recolector OpenAlex, backfill de abstracts, efemérides Horizons, curadores (una vez editado el config), validador de referencias, reportes, infografía (prompt), dashboard y gráfico de actividad, verificación de estado. | Cuándo ejecutar, con qué flags y contra qué fecha/alias. |
| **Automáticos dentro de un pipeline** | Los pasos que `master_orchestrator.py` invoca según `config/orchestrator.json` (Fases 1-6). | Qué módulos/fases se habilitan y en qué orden. |
| **Sin automatizar** | Programación horaria, descarga automática de nuevos videos/referencias, aceptación automática de fuentes, publicación automática a GitHub, actualización automática de ventanas/efemérides. | Todo eso requiere una decisión o un comando explícito. |

## 3. Detalle por proceso

Leyenda: **M** = decisión manual necesaria; **A** = el script lo ejecuta solo una vez lanzado; **S** = semiautomático (M para lanzar + A para ejecutar).

| Proceso | Script / configuración | Tipo | Intervención humana | Resultado y verificación |
| --- | --- | --- | --- | --- |
| Ingesta inicial / reset controlado | `ingest_init.py` · `data/objects.json` | S | Solo ejecutarlo si se quiere reiniciar la carga base. | Carga objetos, orbitales y actividad; registra en `provenance_log`. |
| Patches de esquema (Fase 2/4/6, identificación) | `apply_patch_fase2.py`, `apply_patch_fase4.py`, `apply_patch_fase6.py`, `apply_patch_identificacion.py` | S | Decidir si hay que aplicarlos; son idempotentes. | Tablas/vistas nuevas y datos de cronología; no alteran tablas científicas ya cargadas. |
| Parámetros físicos (SBDB / curados) | `scripts/orchestrator/ingest_physical_sbdb.py`, `ingest_physical_curated.py` | S | Elegir cuándo refrescar y revisar la procedencia. | `physical_params` con `provenance_log`. |
| Metadatos de papers (OpenAlex / arXiv / Crossref) | `collect_metadata_openalex.py` · `config/metadata_scope.json` · `metadata_discovery.py` | S | **M:** definir/extensionar ventana (`desde = último hasta + 1d`, `hasta = hoy`, alias nuevo) y revisar el `--dry-run`. **A:** filtrado, dedupe, carga por lotes y verificación. | `publications` + `object_publications` + `provenance_log`; sin tocar tablas científicas; checkpoints por ventana. |
| Limpieza/completado de abstracts | `backfill_abstracts.py` (`--refrescar-cortos N`) | S | Decidir si se normaliza o se refrescan truncados. | Abstracts normalizados/completos; idempotente. |
| Efemérides geocéntricas (JPL Horizons) | `ingest_ephemeris_horizons.py --date YYYY-MM-DD --force` | S | Elegir la fecha a cargar. | `observations` (posición aproximada calculada, **no astrometría observada**). |
| Búsqueda retrospectiva | `run_retro_search.py` · `apply_patch_fase4.py` | S | Definir criterios y revisar candidatos. | `retro_candidates` / `retro_candidate_reviews`. |
| YouTube (curación) | `config/media_links.json` → `curate_media.py` · `update_report_with_media.py` | **M + A** | **M:** elegir URLs `watch` reales y evaluar relevancia/canal. **A:** validar oEmbed, poblar `published_at`, cargar en BD. | `media_resources` / `media_object_links`; nunca se descubren videos solos. |
| Referencias web (curación) | `config/web_references.json`, `config/web_reference_rules.json` → `validate_web_references.py` → `curate_web_references.py` | **M + A** | **M:** evaluar ref. por ref. (confiable, consistencia, “goyitas”, desactualizadas pero bien informadas, nota de rechazo), fijar `status`/`value_score` y decisiones finales. **A:** el validador da **sugerencias por reglas** y el curador carga lo aprobado. | `curated_references` / links; rechazadas guardadas con nota y ocultas. |
| Visualización (Top N) | `config/dashboard_display.json` | **M** | Cambiar `top_n_global` / `top_n_por_objeto` y regenerar. | Config editable sin tocar código. |
| Reportes semanales / resumen | `generate_report.py` (`--reanudar` / `--force`) | S | Decidir cuándo regenerar y revisar el resultado. | `reports/weekly/` + checkpoints; patrón por lotes. |
| Prompt de infografía | `generate_infographic_prompt.py` | S | Decidir cuándo generarlo; **la imagen se crea fuera del repo** con una IA con capacidad visual. | `reports/infografia_prompt_*.md`. |
| Dashboard + gráfico de actividad | `generate_dashboard.py --force` | S | Decidir cuándo regenerar (y copiar a `dashboard_latest.md`). | `reports/dashboard_latest.md` + timestamped, `docs/REFERENCE_ACTIVITY.md`, `docs/images/ref_activity*`, bloques README. |
| Orquestación de fases | `master_orchestrator.py` · `config/orchestrator.json` | S | Habilitar fases/orden y lanzar el orquestador; no está en scheduler. | Ejecuta los scripts declarados en las fases 1-6 y deja logs/checkpoints. |
| Verificación rápida | `scripts/utils/check_status.py` | A | Ninguna (solo leer salida). | Conteos de objetos/tablas/publicaciones/provenance. |
| Publicación (commit & push) | Git / GitHub | **M** | Revisar diff y decidir publicar. El agente lo hace **cuando se le pide**. | `origin/main` alineado con local. |

## 4. Ronda de actualización: qué es manual y qué automático

Basado en `docs/ESTADO_CARGA.md` (los tres tipos de fuente son independientes):

1. **[M] + [A] Papers:** contrastar último `hasta`/alias en `config/metadata_scope.json` con `MAX(published_at)` por objeto → crear ventana cola → `collect_metadata_openalex.py --alias <nuevo> --dry-run` → **[A]** ejecución real y verificación de duplicados/huérfanos.
2. **[M] + [A] Efemérides:** fijar fecha → `ingest_ephemeris_horizons.py --date <hoy> --force`.
3. **[M] + [A] YouTube:** elegir URLs y relevancia → `curate_media.py`.
4. **[M] + [A] Referencias web:** evaluar cada fuente, cargar en config → validador opcional → `curate_web_references.py`. El validador **no decide**: solo sugiere.
5. **[A] Consistencia:** `generate_dashboard.py --force` regenera dashboard y actividad. **[M]** actualizar `ESTADO_CARGA.md` y decidir commit/push.

## 5. Qué NO está automatizado hoy (y conviene no automatizar)

- **No hay scheduler**: `execution.mode = "manual"` en `config/orchestrator.json`. Nada se ejecuta en un horario.
- **No hay ingesta automática de URLs** de YouTube ni de referencias web: la selección y el juicio de calidad son humanos (es el corazón del criterio "goyitas").
- **No hay aceptación automática de fuentes**: `validate_web_references.py` aplica reglas y sugiere; las decisiones finales (`status`, `value_score`, nota) son del usuario.
- **No se extienden solas las ventanas de papers** ni se actualizan solas las efemérides: requieren fecha/alias explícitos.
- **No se publica automáticamente**: commit/push es una acción deliberada.
- **No se genera la imagen de infografía dentro del repo**: el script produce el prompt; la imagen depende de una herramienta externa.

## 6. Si se quisiera programar (recomendación)

Solo automatizaría los pasos **deterministas y verificables**, manteniendo al humano en las decisiones de calidad:

```bash
# Ejemplo (manual por ahora; eligible para cron/Task Scheduler)
python scripts/utils/check_status.py
python scripts/orchestrator/collect_metadata_openalex.py --alias <alias_ya_definido> --dry-run
python scripts/orchestrator/collect_metadata_openalex.py --alias <alias_ya_definido>
python scripts/orchestrator/ingest_ephemeris_horizons.py --date <YYYY-MM-DD> --force
python scripts/orchestrator/generate_dashboard.py --force
```

Reglas para cualquier automatización futura: (1) `--dry-run` antes de escribir; (2) checkpoints/locks e idempotencia; (3) verificar conteos y `provenance_log` después; (4) **nunca** auto-aceptar referencias web/videos; (5) publicar solo tras revisión.

## 7. Relación con otros documentos

- `docs/EXECUTION.md` — comandos paso a paso por fase.
- `docs/ESTADO_CARGA.md` — qué está cargado, hasta dónde y cómo continuar.
- `docs/IA_HERRAMIENTAS_Y_FLUJO.md` — rol del agente, loops, skills y buenas prácticas.
- `config/orchestrator.json` — definición de fases y modo de ejecución (`manual`).
