# Instalación y configuración (ISO Tracker)

> Última revisión: **2026-11-25**. Válido para Windows, Linux y macOS. Todas las rutas internas son relativas a la raíz del repositorio.
> Si querés saber **qué se ejecuta automáticamente y qué requiere decisión humana**, mirá [`PROCESOS_MANUALES_Y_AUTOMATICOS.md`](PROCESOS_MANUALES_Y_AUTOMATICOS.md).

## 1. Requisitos

| Requisito | Detalle |
| --- | --- |
| **Python** | 3.8 o superior (probado con 3.13). Sin paquetes externos: todo el código usa biblioteca estándar (`sqlite3`, `pathlib`, `urllib`, `ssl`, `json`, `subprocess`, etc.). |
| **Git** | Solo para clonar y publicar. No es necesario para ejecutar los scripts. |
| **Conexión a internet** | Necesaria para consultar OpenAlex, arXiv, Crossref, JPL Horizons/SBDB, YouTube oEmbed y páginas web curadas. **No** hace falta para leer/generar el dashboard con la BD ya incluida. |
| **SQLite** | Viene con Python; la BD está versionada en `data/db/iso.db`. No se instala nada adicional. |
| **Scheduler** | **No requerido ni configurado**: `config/orchestrator.json` declara `execution.mode = "manual"`. Ver §6 si se quiere agregar uno. |
| **Certificados TLS** | Los scripts usan los certificados del sistema y permiten override con `ISO_CA_BUNDLE` (ver §5). |

No hay `requirements.txt` porque **no hay dependencias pip**.

## 2. Instalación

```bash
# 1) Clonar
git clone https://github.com/rodolfojara/Proyecto-Objetos-InterEstelares.git
cd Proyecto-Objetos-InterEstelares

# 2) Verificar Python
python --version

# 3) Verificar que la BD y los scripts estén completos
python scripts/utils/check_status.py
python verify_tables.py
```

Salida esperada de `check_status.py`: 3 objetos, 19 tablas, 407 publicaciones y ~638 entradas en `provenance_log` (los conteos crecen cuando se cargan datos nuevos).

En Windows, si `python` no existe pero sí `py`, usá `py -3 ...` en los comandos.

### 2.1 No hace falta “inicializar” la BD

`data/db/iso.db` ya está incluida con las fases 0-6 ejecutadas. Ejecutar `ingest_init.py` o los `apply_patch_*.py` **solo** tiene sentido para un reset controlado o para repetir un patch (son idempotentes). Si querés hacerlo, seguí el orden de `docs/EXECUTION.md` y hacé una copia de seguridad antes:

```bash
cp data/db/iso.db data/db/iso.db.bak        # Linux/macOS
copy data\db\iso.db data\db\iso.db.bak      # Windows (CMD)
```

## 3. Estructura que usa la configuración

```text
config/
├── orchestrator.json          # fases y modo de ejecución
├── metadata_scope.json        # ventanas/alias de papers (OpenAlex / arXiv + Crossref)
├── sources.json               # inventario de fuentes y prioridades (informativo)
├── media_links.json           # URLs de YouTube curadas
├── web_references.json        # referencias web evaluadas una por una
├── web_reference_rules.json   # reglas del validador (sugerencias)
├── dashboard_display.json     # Top N global / por objeto
└── schema*.sql                # esquema (aplicado por apply_patch_*.py)
data/
├── db/iso.db                  # BD versionada
├── objects.json               # datos base de 1I/2I/3I
├── identification_timeline.json
└── raw/ | normalized/ | snapshots/ | efemerides/   # cachés/datos de trabajo
.metadata_checkpoints/         # checkpoints (cache/ y *_lock se ignoran en Git)
logs/                          # logs (ignorados en Git)
reports/                       # dashboard, reportes, prompts, figuras
docs/images/ref_activity*/     # gráfico generado
```

## 4. Configuración por archivo

| Archivo | Para qué sirve | Cuándo editarlo | Después de editar |
| --- | --- | --- | --- |
| `config/orchestrator.json` | Define las fases que `master_orchestrator.py` puede ejecutar y `execution.mode = "manual"`. El orquestador **no pasa flags**. | Si cambiás el orden/fases o querés documentar otro modo de disparo. | No requiere regeneración; `master_orchestrator.py status` lo relee. |
| `config/metadata_scope.json` | Fuente de verdad de ventanas/alias (`desde`, `hasta`, `query`, `regex`, `metodo`). | Para extender una cola: `desde = último_hasta + 1d`, `hasta = hoy`, alias nuevo. | `collect_metadata_openalex.py --alias <nuevo> --dry-run` → ejecución real → verificar. |
| `config/sources.json` | Lista de fuentes, prioridad e `check_interval_hours`. **Es inventario, no un scheduler.** | Si se agrega una fuente nueva. | Solo documentación; no dispara consultas por sí solo. |
| `config/media_links.json` | URLs `watch?v=` de YouTube, `title`, `channel`, `relevance_score`, `notes`. | Cuando decidís sumar un video evaluado. | `curate_media.py` → `generate_dashboard.py --force`. |
| `config/web_references.json` | Referencias web con `status` (`pending`/`accepted`/`watch`/`rejected`), `value_score` 1-10, `confidence` 1-5, `objects`, `summary`, `evaluation_note`. Las rechazadas se guardan con nota y no se muestran. | Cuando evaluás una referencia nueva o cambiás una decisión. | (Opcional) `validate_web_references.py` → `curate_web_references.py` → dashboard. |
| `config/web_reference_rules.json` | Dominios confiables/cautela, palabras clave y umbrales del validador. | Al refinar sugerencias (“aprendizaje” iterativo). El validador **no decide**. | Volver a correr el validador. |
| `config/dashboard_display.json` | `top_n_global` (hoy 5) y `top_n_por_objeto` (hoy 3). | Para cambiar la jerarquía visible. | `generate_dashboard.py --force`. |

Regla general: **config = entradas decididas por una persona; BD = resultado; reports/ = salida regenerable**.

## 5. Opciones de entorno y resolución de problemas

| Situación | Solución |
| --- | --- |
| Error SSL / certificados al consultar APIs | Definir `ISO_CA_BUNDLE` con la ruta a un bundle válido. Los scripts ya prueban rutas estándar de Linux/macOS y el bundle de Git para Windows. |
| Renovar efemérides | `python scripts/orchestrator/ingest_ephemeris_horizons.py --date YYYY-MM-DD --force` y luego regenerar el dashboard. Son posiciones **calculadas**, no astrometría observada. |
| OpenAlex devuelve `429` | El proyecto puede usar `metodo: "arxiv+crossref"` en `config/metadata_scope.json` para esa ventana; ver `docs/LECCIONES_METADATOS.md`. |
| Consola Windows con caracteres raros | Los mensajes del orquestador usan ASCII (`[OK]`). Si otro script muestra mal los acentos, es solo la terminal (cp1252), no la BD. |
| Rutas con `C:\Users\...` en docs | Reemplazar por el directorio donde clonaste (`<ruta-del-repo>`) o simplemente ejecutar desde la raíz; los scripts ya calculan sus rutas solos. |
| Lock / checkpoint atascado | Confirmar que no haya un recolector en ejecución; borrar solo `.metadata_checkpoints/<ventana>_lock` si corresponde. Los `cache/` y `*_lock` están ignorados por Git. |
| Querés reanudar una carga larga | Usar `--reanudar` (o el estado guardado del checkpoint). `--force` descarta el checkpoint y vuelve a generar. |

Ejemplos de `ISO_CA_BUNDLE`:

```bash
# Linux (bash)
export ISO_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
```

```powershell
# Windows (PowerShell)
$env:ISO_CA_BUNDLE = "C:\ruta\a\ca-bundle.crt"
```

## 6. Ejecución y (opcional) programación

El flujo normal es manual; los scripts se lanzan desde la raíz:

```bash
python scripts/utils/check_status.py
python scripts/orchestrator/generate_dashboard.py --force
```

Si más adelante se quiere programar **solo** lo determinista (nunca la curación de fuentes), ver el ejemplo y las reglas en [`PROCESOS_MANUALES_Y_AUTOMATICOS.md`](PROCESOS_MANUALES_Y_AUTOMATICOS.md#6-si-se-quisiera-programar-recomendación). Resumen: `--dry-run` antes de escribir, verificar conteos/provenance, checkpoints/locks, y decisión humana para aceptar videos o referencias web.

## 7. Verificación post-instalación (checklist)

- [ ] `python --version` → 3.8+.
- [ ] `python scripts/utils/check_status.py` muestra 3 objetos y 19 tablas.
- [ ] `python verify_tables.py` imprime la lista de tablas.
- [ ] `python scripts/orchestrator/generate_dashboard.py --force` termina sin error y actualiza `reports/dashboard_latest.md`.
- [ ] `python scripts/orchestrator/master_orchestrator.py status` lista las 7 fases (no reinicia nada).
- [ ] Si se va a publicar: `git remote -v`, `git config user.name`, `git config user.email` y `git status` sin cambios inesperados en `data/db/iso.db`.

## 8. Documentación relacionada

- [`PROCESOS_MANUALES_Y_AUTOMATICOS.md`](PROCESOS_MANUALES_Y_AUTOMATICOS.md) — manual vs automático, flags y precauciones del orquestador.
- [`EXECUTION.md`](EXECUTION.md) — comandos por fase.
- [`ESTADO_CARGA.md`](ESTADO_CARGA.md) — qué hay cargado y cómo continuar una ronda.
- [`IA_HERRAMIENTAS_Y_FLUJO.md`](IA_HERRAMIENTAS_Y_FLUJO.md) — rol del agente, loops y buenas prácticas de integridad.
- [`LECCIONES_METADATOS.md`](LECCIONES_METADATOS.md) — errores/rutas alternativas de la ingesta bibliográfica.
