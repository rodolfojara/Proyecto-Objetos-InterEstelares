# Guía de Ejecución - ISO Tracker

Este documento contiene **instrucciones paso a paso** para ejecutar todos los scripts del proyecto. Todo lo necesario está en este repositorio.

## Ubicación
Todos los comandos se ejecutan desde la raíz del proyecto:
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
```

## Fase 0 y 1 (Completadas)

### 1. Crear estructura y BD (ya hecho)
Ya ejecutado. Ver `config/schema.sql` y `data/db/iso.db`

### 2. Ingesta inicial
**Script:** `ingest_init.py`  
**Ubicación:** Raíz del proyecto  
**Cuándo usarlo:** Solo para inicialización/reset controlado

```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
python ingest_init.py
```

**Qué hace:**
- Carga objetos desde `data/objects.json`
- Inserta en `objects`, `orbital_elements`, `activity`
- Registra en `provenance_log`

## Fase 2 (Completada - estructura)

**Archivos creados:**
- `config/schema_fase2_patch.sql` - Añade `object_aliases`
- `apply_patch_fase2.py` - Aplica patch (ejecutado)
- `config/sources.json` - Fuentes a monitorear
- `scripts/skills/parse_mpec.py` - Skill para parsear MPEC
- `scripts/skills/extract_orbital_elements.py` - Skill para extraer elementos orbitales
- `scripts/skills/normalize_units.py` - Skill para normalizar unidades
- `scripts/agents/vigilante.md`, `recolector.md`, `normalizador.md` - Definiciones de agentes
- `scripts/orchestrator/orchestrator_fase2.md` - Orquestación

**Aplicar patch (si necesario):**
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
python apply_patch_fase2.py
```

## Cronología de identificación (soporte a Fase 2/3)

Registra las fechas de detección, descubrimiento, anuncio, confirmación interestelar y designación I de cada objeto, y permite clasificar papers previos y posteriores a la identificación.

**Archivos:**
- `config/schema_identificacion_patch.sql` - Tabla `object_identification`
- `config/schema_identificacion_view.sql` - Vista `v_publication_epoch`
- `data/identification_timeline.json` - Fechas y referencias primarias
- `apply_patch_identificacion.py` - Aplica el patch y carga los datos (idempotente)
- `docs/IDENTIFICACION.md` - Criterios y consultas

**Ejecutar:**
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
python apply_patch_identificacion.py
```

## Pase inicial de metadatos bibliográficos (soporte a Fase 2/3)

Carga metadatos de papers en `publications` y las vincula a cada objeto en `object_publications`, dentro de la ventana de un año posterior a la designación I. No toca tablas científicas ni alias, y deja los registros listos para que Fase 2/3 los procese sin rehacer trabajo.

**Archivos:**
- `config/metadata_scope.json` - ventanas, queries y reglas de relevancia por objeto
- `scripts/orchestrator/collect_metadata_openalex.py` - colector
- `scripts/orchestrator/metadata_discovery.py` - descubrimiento alternativo arXiv + Crossref
- `scripts/orchestrator/backfill_abstracts.py` - completa abstracts faltantes desde arXiv o Crossref

**Ejecutar:**
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
python scripts/orchestrator/collect_metadata_openalex.py --dry-run
python scripts/orchestrator/collect_metadata_openalex.py
```

Opciones útiles:
- `--solo 3I` procesa solo la ventana indicada.
- `--cache-dir <ruta>` guarda las respuestas de la API y permite reintentar sin volver a paginar (OpenAlex devuelve `429` si se piden muchas páginas seguidas).
- `--normalizar` limpia títulos y abstracts ya cargados (prefijo `Abstract`, espaciado `3I / ATLAS` → `3I/ATLAS`) sin volver a consultar fuentes.
- `python scripts/orchestrator/backfill_abstracts.py` rellena abstracts vacíos sin tocar el resto de campos.
- `python scripts/orchestrator/backfill_abstracts.py --refrescar-cortos 200` reemplaza abstracts truncados (< 200 caracteres) por la versión completa de arXiv o Crossref.

**Ventanas (un año desde la designación I):**

| Objeto | Desde | Hasta |
| --- | --- | --- |
| 1I/'Oumuamua | 2017-11-06 | 2018-11-06 |
| 2I/Borisov | 2019-09-24 | 2020-09-24 |
| 3I/ATLAS | 2025-07-02 | 2026-07-02 |

**Qué escribe:**

| Tabla | Acción |
| --- | --- |
| `publications` | inserta o actualiza por `doi` o `arxiv_id` (nunca duplica); `processed = 0` |
| `object_publications` | crea el vínculo objeto-paper con `relevance_score`; `publication_class` queda NULL |
| `provenance_log` | deja constancia con `agent = 'recolector'` y el `openalex_id` de origen |

**Qué NO toca:** `orbital_elements`, `physical_params`, `composition`, `activity`, `object_aliases`, `objects`, ni `object_identification`.

**Criterios aplicados a cada candidato:**

| Criterio | Regla |
| --- | --- |
| Tipo | `article`, `preprint` o `review` |
| Pertenencia al objeto | regex por objeto sobre título + abstract (2I y 3I exigen designación, para evitar homónimos) |
| Identificador | DOI o arXiv obligatorio |
| Abstract | obligatorio, salvo que exista arXiv |
| Fuente | arXiv, o revista con ISSN (descarta Zenodo, EarthArXiv, blogs y similares) |
| Idioma | inglés o desconocido |
| Dominio | `Physical Sciences` o desconocido |
| Duplicados | fusión por título normalizado, por identificador compartido y por similitud de título ≥ 0.95 |

**Diferencia con la ventana de papers de Fase 3:** este pase usa `iso_designation_date` como inicio; la clasificación de papers previos/posteriores a la identificación usa `iso_confirmation_date` (ver `docs/IDENTIFICACION.md`).

**Descubrimiento alternativo (OpenAlex → arXiv + Crossref):** OpenAlex aplica un presupuesto diario a las consultas de búsqueda. Cuando se agota (`429` con `Retry-After` de horas), la ventana puede resolverse descubriendo DOIs en arXiv (buscador avanzado) y en Crossref (artículos de revista, proceedings y preprints registrados), aplicando el mismo regex y cargando los registros con los mismos campos. La ventana de 3I/ATLAS se cargó por esta vía. Para reactivar la búsqueda directa, cambiar `"metodo": "arxiv+crossref"` por `"metodo": "openalex"` en `config/metadata_scope.json`.

**Resultado del pase (2026-10-28):**

| Objeto | Papers | Ventana | Vía |
| --- | --- | --- | --- |
| 1I/'Oumuamua | 46 | 2017-11-06 a 2018-11-06 | OpenAlex |
| 2I/Borisov | 40 | 2019-09-24 a 2020-09-24 | OpenAlex |
| 3I/ATLAS | 123 | 2025-07-02 a 2026-07-02 | arXiv + Crossref |
| **Total** | **209** | | |

Verificado al cierre: 209 filas en `publications` y 209 en `object_publications`, sin duplicados por DOI, arXiv ni título; todas con `processed = 0` y `publication_class` NULL; todas dentro de su ventana; `objects`, `object_aliases`, `orbital_elements`, `physical_params`, `composition`, `activity` y `object_identification` sin cambios. Una segunda ejecución no creó registros nuevos.

**Limpieza posterior (mismo día):** se corrigió el extractor de abstracts de arXiv (cortaba en el primer `</span>` y perdía el texto tras un `search-hit` anidado), se limpiaron 151 registros con `--normalizar` (115 abstracts con prefijo `Abstract` de Crossref y 88 títulos con `3I / ATLAS` espaciado) y se refrescaron 22 abstracts truncados desde arXiv. Al cierre: 0 abstracts con prefijo, 0 títulos con designación espaciada y solo 3 abstracts cortos, todos legítimos (una nota breve de arXiv y dos notas de prensa de Eos). `--normalizar` es idempotente: una segunda pasada reporta 0 cambios.

**Cobertura:** OpenAlex, arXiv y Crossref no indexan todo. La ventana desde la designación deja fuera el pico de papers de octubre-noviembre de 2017 sobre 1I, y los trabajos sin DOI/arXiv o sin fuente con ISSN quedan descartados (en 3I/ATLAS se descartaron 24 por fuente y 12 por falta de abstract). Los conteos son un piso, no un techo.

**Tiempos y lecciones:** el colector imprime la duración de cada ventana y el total. El pase de 209 papers tomó aproximadamente 1 h 30 min. Errores encontrados, rutas alternativas cuando OpenAlex bloquea y qué sobrevive a una interrupción están documentados en `docs/LECCIONES_METADATOS.md`.


## Fase 3 (Pendiente)

Se crearán:
- `scripts/agents/validador.md`
- `scripts/agents/correlacionador.md` 
- `scripts/agents/presentador.md`
- `scripts/orchestrator/generate_report.py` - **Generará reporte con lo solicitado**

**Reporte debe incluir:**
- Resumen
- Cantidad de papers que mencionan 1I/'Oumuamua, 2I/Borisov, 3I/ATLAS
- Fecha de primer reporte de 1I, 2I, 3I
- Fecha actual
- Evolución temporal
- Comparativa
- Origen/destino galáctico (cuando disponible)
- Cambios recientes
- Nivel de confianza

## Fase 4 (Pendiente)
Búsqueda retrospectiva de candidatos hiperbólicos en archivos históricos.

## Fase 5 (Pendiente)
Orquestador completo y automatización (manual con Task Scheduler/cron)

## Verificación rápida de BD
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
python -c "
import sqlite3
conn = sqlite3.connect('data/db/iso.db')
cur = conn.cursor()
cur.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
print([r[0] for r in cur.fetchall()])
conn.close()
"
```

## Logs
Los logs se guardarán en `logs/` con formato `YYYY-MM-DD_<agente>.log/json`
