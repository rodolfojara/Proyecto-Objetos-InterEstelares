# Ejemplo completo: fuente → recolección → normalización → base de datos → reporte

> Ejemplo **real** del repositorio, contrastado con `data/db/iso.db` el 2026-11-25. No es un caso hipotético: los identificadores, fechas y conteos son los de la BD incluida.
> Sirve para entender qué hace cada eslabón y dónde se pone la intervención humana. Reglas generales en [`PROCESOS_MANUALES_Y_AUTOMATICOS.md`](PROCESOS_MANUALES_Y_AUTOMATICOS.md) y orden de reconstrucción en [`FASES_DESDE_CERO.md`](FASES_DESDE_CERO.md).

## 0. Mapa de una mirada

```text
FUENTE                    RECOLECCIÓN                    NORMALIZACIÓN
OpenAlex works API  →  collect_metadata_openalex.py  →  filtros + fusiones +
(config/metadata_       (--dry-run → real, cache,         limpiar_titulo/abstract
 scope.json)            lock, checkpoint, commit/10)      + --normalizar en BD)
                                                                ↓
REPORTE                   BASE DE DATOS                         ↓
generate_report.py  ←  publications / object_publications  ←  upsert por DOI/arXiv
(agrega conteos)       provenance_log                          + vínculo al objeto
        ↓
generate_dashboard.py → dashboard_latest.md + gráfico de actividad (published_at)
```

**La persona decide la fuente y la ventana; el script decide el resto.** El validador de referencias y el curador multimedia nunca auto-aceptan contenido.

---

## 1. FUENTE — dónde está declarada

Para este ejemplo se usa un paper de **1I/'Oumuamua** cargado desde **OpenAlex**. La fuente no se improvisa: está en `config/metadata_scope.json`, ventana `1i-2025`:

```json
{
  "alias": "1i-2025",
  "designation": "1I/'Oumuamua",
  "desde": "2025-11-07",
  "hasta": "2026-11-07",
  "metodo": "openalex",
  "query": "Oumuamua",
  "regex": "oumuamua",
  "regex_excluir_titulo": "\\b2i\\s*/?\\s*borisov\\b|...|\\b3i\\s*/?\\s*atlas\\b|..."
}
```

- Endpoint real: `https://api.openalex.org/works` (`API` en `collect_metadata_openalex.py:54`).
- `query` acota la búsqueda; `regex` exige que título+abstract mencionen al objeto; `regex_excluir_titulo` evita que un paper centrado en 2I/3I se cuele en la ventana de 1I.
- `campos_permitidos` del config: `arxiv_id`, `doi`, `title`, `authors`, `journal`, `published_at`, `abstract`, `source_url`.
- `campos_prohibidos`: orbitales, físicos, composición, actividad, aliases e identificación → **el recolector no los toca**.

> **[M]** Extender la ventana es decisión humana: `desde = último_hasta + 1d`, `hasta = hoy`, alias nuevo (por ejemplo `1i-2026`). Ver [`ESTADO_CARGA.md`](ESTADO_CARGA.md).

---

## 2. RECOLECCIÓN — del API al candidato

```bash
cd "<ruta-del-repo>"

# 2.1 Ensayo (no escribe en la BD)
python scripts/orchestrator/collect_metadata_openalex.py --alias 1i-2025 --dry-run

# 2.2 Ejecución real, por ventana
python scripts/orchestrator/collect_metadata_openalex.py --alias 1i-2025 --reanudar
```

Qué ocurre dentro del script:

1. `buscar()` descarga todos los `works` de la ventana (reintentos ante `429`). Con `--cache-dir` guarda `1I__Oumuamua_2025-11-07.json`; sin él, consulta directamente.
2. Toma un lock por ventana (`.metadata_checkpoints/1I__Oumuamua_2025-11-07_lock`) para no duplicar ejecuciones concurrentes.
3. Escribe checkpoint y hace commit cada 10 registros (`COMMIT_CADA = 10`), de modo que una interrupción se reanuda con `--reanudar`.
4. Solo acepta `article`, `preprint` o `review`; descarta sin DOI/arXiv, sin abstract o con idioma/dominio no válido.
5. Registra cada inserción/actualización en `provenance_log` con `agent='recolector'` y el `openalex:W...` de origen.

Si `metodo = "arxiv+crossref"` (caso de las ventanas `3i-*`), el descubrimiento lo hace `metadata_discovery.py` —módulo de apoyo, no CLI— y el mismo recolector aplica después los mismos filtros. Ver [`LECCIONES_METADATOS.md`](LECCIONES_METADATOS.md).

---

## 3. NORMALIZACIÓN — antes, durante y después

Hay **tres capas** de normalización, y conviene no confundirlas:

| Momento | Función | Ejemplo concreto |
| --- | --- | --- |
| Al leer cada `work` | `abstract_de()` reconstruye el texto desde `abstract_inverted_index` ordenando por posición. | `{"We": [0], "observed": [1], ...}` → `"We observed ..."` |
| Antes de filtrar | `limpiar_titulo()` unifica espacios y designación; `limpiar_abstract()` quita prefijos. | `"3I / ATLAS"` → `"3I/ATLAS"`; `"Abstract: ... △ Less"` → `"..."` |
| Dedupe | `normalizar()` (NFKD → sin acentos → minúsculas → `[^a-z0-9]` a espacio) + `fusionar_por_identificador()` (mismo DOI/arXiv) + `fusionar_similares()` (títulos con similitud ≥ 0.95). | preprint sin DOI y versión de revista sin arXiv se unen en **un** registro |
| Después de cargar | `collect_metadata_openalex.py --normalizar` (o `backfill_abstracts.py --refrescar-cortos N`) reescribe **solo** lo que cambia y deja provenance `normalizacion de metadatos (titulo/abstract)`. | título con espaciado raro se corrige sin volver a consultar la API |

La normalización **no clasifica** el paper: `publications.processed` queda en `0` y `object_publications.publication_class` en `NULL` a propósito, para decisiones posteriores.

---

## 4. BASE DE DATOS — lo que queda escrito

El paper de ejemplo es el registro **`publications.id = 406`**:

| Campo | Valor real en BD |
| --- | --- |
| `title` | `Capture of interstellar objects during stellar encounters` |
| `doi` | `10.1051/0004-6361/202660697` |
| `arxiv_id` | `2607.18551` |
| `published_at` | `2026-07-31` |
| `journal` | `Astronomy & Astrophysics` |
| `source_url` | `https://doi.org/10.1051/0004-6361/202660697` |
| `processed` | `0` (pendiente de clasificación) |

Vínculo y trazabilidad:

```sql
-- object_publications
object_id = 1  |  publication_id = 406  |  relevance_score = 4  |  publication_class = NULL

-- provenance_log (id 636)
entity='publications' | entity_id=406 | action='insert' | agent='recolector'
details='openalex metadata pass | ventana 2025-11-07..2026-11-07 | openalex:W7171974151'
timestamp='2026-11-07 03:00:51'
```

Para verlo exactamente:

```bash
python -c "import sqlite3; c=sqlite3.connect('data/db/iso.db'); c.row_factory=sqlite3.Row; print(dict(c.execute('SELECT id,title,doi,arxiv_id,published_at,processed FROM publications WHERE id=406').fetchone())); print([dict(r) for r in c.execute('SELECT * FROM provenance_log WHERE entity_id=406')])"
```

Conteos agregados tras todas las ventanas: **1I = 189**, **2I = 99**, **3I = 161** papers vinculados (449 vínculos en total). El recolector **no escribió** en `orbital_elements`, `physical_params`, `composition`, `activity`, `object_aliases` ni `object_identification`.

---

## 5. REPORTE — de la fila al markdown

```bash
python scripts/orchestrator/generate_report.py --force
```

`generate_report.py` solo lee la BD y escribe `reports/weekly/ISO_Report_<timestamp>.md`. La sección `## Cantidad de papers que mencionan cada objeto` se construye con `count_papers_by_object()` (`generate_report.py:61-70`) y queda así:

| Objeto | Cantidad de papers vinculados |
| :-- | :--: |
| 1I/'Oumuamua | 189 |
| 2I/Borisov | 99 |
| 3I/ATLAS | 161 |

El reporte **agrega**; el paper individual se consulta en la BD (SQL de arriba) o en las secciones de análisis del dashboard. Para publicar la vista evolutiva:

```bash
python scripts/orchestrator/generate_dashboard.py --force
python -c "import json,shutil,pathlib; d=json.loads(pathlib.Path('.metadata_checkpoints/dashboard_checkpoint.json').read_text(encoding='utf-8')); shutil.copyfile(d['last_dashboard'],'reports/dashboard_latest.md')"
```

El dashboard también refresca el gráfico de actividad: la serie de papers usa **`published_at`**, la de videos `published_at|added_at` y la de referencias web `source_date|retrieved_at` (fecha de publicación/origen, no de ingesta). Ver [`docs/REFERENCE_ACTIVITY.md`](REFERENCE_ACTIVITY.md).

---

## 6. Reproducción completa en una línea de tiempo

```bash
cd "<ruta-del-repo>"

# 1) Fuente: revisar/crear la ventana en config/metadata_scope.json  [M]
# 2) Recolección: ensayo y ejecución  [A]
python scripts/orchestrator/collect_metadata_openalex.py --alias 1i-2025 --dry-run
python scripts/orchestrator/collect_metadata_openalex.py --alias 1i-2025 --reanudar

# 3) Normalización de lo ya cargado  [A]
python scripts/orchestrator/collect_metadata_openalex.py --normalizar --dry-run
python scripts/orchestrator/collect_metadata_openalex.py --normalizar

# 4) Verificar BD y provenance  [A]
python scripts/utils/check_status.py

# 5) Reporte y vista publicable  [A] + [M] (copiar dashboard_latest)
python scripts/orchestrator/generate_report.py --force
python scripts/orchestrator/generate_dashboard.py --force
python -c "import json,shutil,pathlib; d=json.loads(pathlib.Path('.metadata_checkpoints/dashboard_checkpoint.json').read_text(encoding='utf-8')); shutil.copyfile(d['last_dashboard'],'reports/dashboard_latest.md')"
```

> No ejecutar el colector real sobre la BD de producción solo "para probar": usar `--dry-run` y una copia del repo. `--force` en otros scripts sí puede borrar subconjuntos (ver [`FASES_DESDE_CERO.md`](FASES_DESDE_CERO.md#6-precauciones)).

---

## 7. Dos variantes cortas (mismo patrón, otra fuente)

### 7.1 YouTube → multimedia → reporte

| Etapa | Dato real |
| --- | --- |
| **Fuente [M]** | `config/media_links.json`: `https://www.youtube.com/watch?v=ZtQHgCEVZ4o` (elegido y evaluado a mano). |
| **Recolección [A]** | `curate_media.py` consulta YouTube oEmbed (salvo `--skip-validate`) y obtiene título/canal/`published_at`. |
| **Normalización [A]** | Título y canal se toman del oEmbed: `NASA Spacecraft Observe Interstellar Comet 3I/ATLAS as It Approaches Mars`, `NASA Jet Propulsion Laboratory`, `published_at=2025-09-30`. |
| **BD [A]** | `media_resources.id = 10` + `media_object_links(media_id=10, object_id=3, relation='mentions', confidence=3)`. |
| **Reporte [A]** | `update_report_with_media.py` → `reports/weekly/ISO_Report_with_Media_<timestamp>.md`; el dashboard muestra el bloque multimedia y el gráfico usa `published_at`. |

### 7.2 Página web NASA → referencia curada → dashboard

| Etapa | Dato real |
| --- | --- |
| **Fuente [M]** | `config/web_references.json`: `https://science.nasa.gov/solar-system/comets/3i-atlas/`, `source_date=2026-05-28`, dominio confiable en `web_reference_rules.json`. |
| **Recolección [A]** | `validate_web_references.py` (opcional) hace HEAD/GET y escribe **sugerencias** (`agent_suggested_status/value`); `curate_web_references.py` carga lo aprobado. |
| **Normalización [M+A]** | La persona fija `status='accepted'`, `value_score=9`, `confidence=5` y `evaluation_note`; el script deriva `domain` y guarda la nota. Las rechazadas se guardan ocultas con nota. |
| **BD [A]** | `curated_references.id = 3` + `curated_reference_object_links(ref_id=3, object_id=3, relation='mentions', confidence=5)`. Requiere el patch manual `schema_web_references_patch.sql`. |
| **Reporte [A]** | `generate_dashboard.py --force` muestra el Top 5 global / Top 3 por objeto (`config/dashboard_display.json`) y alimenta la serie web del gráfico con `source_date`. |

Wikipedia quedó como `status='rejected'`, `value_score=3`, guardada con nota y **no mostrada**: es el ejemplo de que "fuentes primarias primero" no significa borrar lo descartado.

---

## 8. Reglas que se repiten en los tres flujos

1. **[M]** Config = entradas decididas por una persona; **[A]** script = trabajo mecánico.
2. `--dry-run` antes de escribir; checkpoint/lock para reanudar.
3. Toda fila nueva lleva `provenance_log` (qué, cuándo, desde qué URL, con qué agente).
4. Nunca se auto-acepta una fuente: `status`/`value_score`/notas son decisión humana.
5. `--force` reinicia checkpoints y, en algunos scripts, borra un subconjunto: revisar siempre el diff y los conteos.
6. Salidas derivadas (`reports/`, gráficos, bloques README) se regeneran; las tablas científicas no se reemplazan en bloque.

Documentación relacionada: [`EXECUTION.md`](EXECUTION.md) (comandos por fase), [`INSTALACION_Y_CONFIGURACION.md`](INSTALACION_Y_CONFIGURACION.md) (configs), [`FASES_DESDE_CERO.md`](FASES_DESDE_CERO.md) (desde BD vacía).
