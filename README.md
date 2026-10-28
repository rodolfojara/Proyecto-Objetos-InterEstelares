# Sistema de Seguimiento y Análisis de Objetos Interestelares (ISO Tracker)

Sistema multi-agente/orquestado para recolectar, normalizar, versionar, correlacionar y presentar información sobre objetos interestelares (1I/'Oumuamua, 2I/Borisov, 3I/ATLAS) y futuros descubrimientos.

## Estado del proyecto
- **Estructura e implementación (fabricación):** Fases 0-6 implementadas estructuralmente (esquema, agentes, skills, orquestador, reportes, multimedia)
- **Ejecución:** Fase 0: Preparación - **EJECUTADA** | Fase 1: Ingesta histórica inicial - **EJECUTADA**
- **Pendientes de ejecución:** Fase 2: Agentes base - Pendiente | Fase 3: Validación y correlación - Pendiente | Fase 4: Búsqueda retrospectiva - Pendiente | Fase 5: Automatización/Orquestador - Pendiente | Fase 6: Curador multimedia - Pendiente

> Cuando se mencione una fase por número (Fase 0, Fase 1, ..., Fase 5), se entiende tal como está definida en este proyecto.

## Cronología de identificación

Fechas que marcan cuándo cada objeto pasa de ser "un objeto observado" a "un objeto interestelar". No existe una sola fecha: hay cinco hitos y cada uno sirve para algo distinto.

| Objeto | Detección más antigua | Descubrimiento | Anuncio | Confirmación interestelar | Designación I |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **1I/'Oumuamua** | 2017-10-18 | 2017-10-19 | 2017-10-25 | 2017-10-25 | 2017-11-06 * |
| **2I/Borisov** | 2019-08-30 | 2019-08-30 | 2019-09-11 | 2019-09-11 | 2019-09-24 |
| **3I/ATLAS** | 2025-06-14 | 2025-07-01 | 2025-07-02 | 2025-07-02 | 2025-07-02 |

- **Detección más antigua:** imagen o astrometría más antigua conocida, aunque nadie la haya reconocido como objeto nuevo (precovery).
- **Descubrimiento:** se reconoce y reporta como objeto nuevo.
- **Anuncio:** primera publicación oficial del MPC (MPEC).
- **Confirmación interestelar:** la órbita hiperbólica u origen interestelar queda establecido.
- **Designación I:** se asigna 1I, 2I o 3I. Es la fecha desde la cual se lo llama formalmente interestelar.

**Por qué varias fechas:** un paper anterior a la confirmación no podía atribuirle origen interestelar, porque el dato no existía todavía. Por eso el corte para clasificar literatura es la confirmación, no la designación formal. Usar la designación como corte clasificaría mal la producción científica de la ventana entre ambos hitos (13 días en Borisov, 12 en 'Oumuamua).

Estas fechas se registran en la tabla `object_identification` y la vista `v_publication_epoch` las usa para separar papers en tres épocas: `archivo_previo`, `observado_sin_identificar` y `literatura_interestelar`.

\* La fecha de designación 1I (2017-11-06) tiene confianza 4: proviene del boletín del MPC citado por prensa, pendiente de validar contra el boletín original.

Detalle, criterios y consultas SQL: [`docs/IDENTIFICACION.md`](docs/IDENTIFICACION.md)

## Estructura del proyecto
```
Proyecto Objetos InterEstelares/
├── config/
│   ├── schema.sql        # Esquema SQLite
│   ├── schema_identificacion_patch.sql  # Tabla object_identification
│   ├── schema_identificacion_view.sql   # Vista v_publication_epoch
│   └── sources.json      # Fuentes a monitorear
├── data/
│   ├── db/iso.db         # Base de datos SQLite
│   ├── objects.json      # Datos iniciales de objetos
│   ├── identification_timeline.json  # Fechas de identificación
│   ├── raw/              # Archivos crudos (HTML/PDF/JSON/XML)
│   ├── normalized/       # JSON normalizados por objeto
│   ├── snapshots/        # Snapshots por fecha
│   ├── efemerides/       # Cache JPL Horizons
│   └── embeddings/       # Embeddings para búsqueda semántica (futuro)
├── scripts/
│   ├── agents/           # Definiciones/instrucciones de agentes
│   ├── skills/           # Skills reutilizables (parse_mpec, etc)
│   ├── orchestrator/     # Orquestador
│   └── utils/            # Utilidades
├── reports/
│   ├── figures/          # Gráficas/infografías generadas
│   └── weekly/           # Reportes semanales
├── docs/                 # Documentación (incluye IDENTIFICACION.md)
├── logs/                 # Logs de ejecución
├── ingest_init.py        # Script de ingesta inicial (Fase 0/1)
└── apply_patch_identificacion.py  # Aplica y carga la cronología
```

## Requisitos
- Python 3.x (sqlite3 viene incluido)
- Acceso a internet para consultas (MPC/JPL/arXiv) - las fases posteriores lo usarán
- No se requiere instalación externa obligatoria para las fases 0-1

## Base de datos
La base de datos se crea en: `data/db/iso.db`

Tablas principales:
- `objects` - Objetos interestelares
- `object_identification` - Cronología de identificación (detección, confirmación, designación I)
- `object_aliases` - Designaciones y alias de cada objeto
- `orbital_elements` - Elementos orbitales (versionados)
- `physical_params` - Parámetros físicos (versionados)
- `composition` - Composición/producción de gases
- `activity` - Actividad/ coma
- `publications` - Papers (arXiv/DOI)
- `object_publications` - Relación objetos-papers y clase editorial
- `observations` - Observaciones
- `retro_candidates` / `retro_candidate_reviews` - Búsqueda retrospectiva
- `media_resources` / `media_object_links` - Multimedia
- `provenance_log` - Bitácora inmutable
- `report_metrics` - Métricas para reportes

Vista:
- `v_publication_epoch` - Clasifica cada paper según la cronología de identificación

## Scripts y cómo ejecutarlos

### Ingesta inicial (Fase 0/1 - ya ejecutado)
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
python ingest_init.py
```
**Ubicación:** `ingest_init.py` (raíz del proyecto)
**Qué hace:** Carga 1I/'Oumuamua, 2I/Borisov, 3I/ATLAS desde `data/objects.json` a la DB con sus elementos orbitales y actividad inicial, registrando en `provenance_log`.

### Metadatos bibliográficos (Fase 2 - recolección)
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
python scripts/orchestrator/collect_metadata_openalex.py --dry-run
python scripts/orchestrator/collect_metadata_openalex.py
```
**Ubicación:** `scripts/orchestrator/collect_metadata_openalex.py` (con `metadata_discovery.py` como apoyo)
**Qué hace:** Carga papers (título, autores, DOI/arXiv, revista, fecha, abstract) en `publications` y los vincula a cada objeto en `object_publications`, dentro de la ventana de un año desde la designación I. No toca tablas científicas ni alias. Criterios, ventanas y resultados en `docs/EXECUTION.md`.

Mantenimiento de esos metadatos:
```bash
python scripts/orchestrator/collect_metadata_openalex.py --normalizar
python scripts/orchestrator/backfill_abstracts.py --refrescar-cortos 200
```
`--normalizar` limpia títulos y abstracts ya cargados; `--refrescar-cortos` reemplaza abstracts truncados por la versión completa de arXiv o Crossref. Ambos son idempotentes. El detalle de errores, rutas alternativas y tiempos está en `docs/LECCIONES_METADATOS.md`.

### Generador de reportes (se creará en fases posteriores)
Los scripts de reporte seguirán el patrón:
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
python scripts/orchestrator/generate_report.py [--weekly|--summary]
```
Las instrucciones específicas de cada script se añadirán en `docs/EXECUTION.md` cuando se creen.

## Reporte - Información requerida
El reporte debe incluir SIEMPRE:
- **Resumen general** - Estado actual de los 3 objetos
- **Cantidad de papers** - Número de papers que mencionan 1I/'Oumuamua, 2I/Borisov, 3I/ATLAS (desde `publications` + `object_publications`)
- **Fecha de primer reporte** - Primera mención/oficial report para cada objeto (1I, 2I, 3I)
- **Fecha actual** - Fecha/hora de generación del reporte
- **Evolución temporal** - Cómo han cambiado los datos (órbitas, composición, actividad) entre snapshots
- **Comparativa** - 1I vs 2I vs 3I
- **Origen/destino galáctico** - Cuando esté disponible en papers
- **Hallazgos y cambios recientes** - Diferencias desde último snapshot
- **Nivel de confianza** - Por dato/afirmación

## Fuentes monitoreadas (prioridad)
1. MPC (MPEC) - Crítica
2. arXiv astro-ph.EP - Crítica  
3. JPL Horizons/SBDB - Crítica
4. NASA Science/ESA - Alta
5. Revistas (Nature Astronomy, ApJ, A&A, MNRAS, Icarus, PSJ) - Alta
6. Acta Astronautica y similares - Condicional (solo si relevante a misiones/ISO)

## Notas importantes
- **Sin agentes corriendo 24/7:** Los scripts se ejecutan manualmente o con Task Scheduler/cron propio. Yo genero los scripts, tú los ejecutas.
- **Versionado estricto:** Nunca se sobreescriben datos. Cada valor se guarda con fuente, fecha, agente y confianza.
- **Fuentes primarias primero:** MPC/JPL tienen prioridad sobre noticias.
- **Escepticismo:** Separa hechos medidos vs especulación. El correlacionador marca hipótesis como `propuesta/especulativa`.
- **Búsqueda retrospectiva:** Se buscarán trayectorias hiperbólicas (e>1) en archivos antiguos, no solo por nombre "interstellar".
- **SQLite:** Creado y configurado con `sqlite3` nativo (sin instalaciones externas).
- **Agentes vs Skills:** Skills para tareas repetitivas/deterministas, Agentes para juicio/decisión.

## Recursos audiovisuales (complemento multimedia)
El sistema cuenta con un **curador multimedia** para añadir vídeos de YouTube complementarios a los objetos interestelares, enlazarlos con la base de datos y mostrarlos en los reportes junto a los datos del sistema.

- **Documentación completa:** `docs/MULTIMEDIA_CURATOR.md`
- **Agente:** `scripts/agents/curador_multimedia.md`
- **Curador:** `scripts/orchestrator/curate_media.py`
- **Reporte con multimedia:** `scripts/orchestrator/update_report_with_media.py`
- **Configuración:** `config/media_links.json`

**Uso rápido:**
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
# Editar config/media_links.json con URLs de vídeos relacionados con 1I/'Oumuamua, 2I/Borisov o 3I/ATLAS
python scripts/orchestrator/curate_media.py
python scripts/orchestrator/update_report_with_media.py
```

**Notas:** Solo se enlazan vídeos (no se descargan). Se priorizan visualizadores explicativos con datos y se descarta contenido sensacionalista. Todo queda registrado en `media_resources` y `media_object_links` con trazabilidad.

## Prompts para infografías (generación externa)

Dado que el modelo actual **no tiene capacidad de visión/generación de imágenes**, el sistema genera un **prompt listo para copiar y pegar** en otra IA con generación de infografías/imágenes.

- **Script:** `scripts/orchestrator/generate_infographic_prompt.py`
- **Cuándo ejecutarlo:** **Manualmente**. No forma parte de `master_orchestrator.py all`, se ejecuta solo cuando lo necesites.
- **Dónde se genera:** `reports/infografia_prompt_YYYY-MM-DD_HH-MM-SS.md`
- **Dónde verlo:** Carpeta `reports/` del proyecto (`C:\Users\user\Documents\Proyecto Objetos InterEstelares\reports\`). Abre ese archivo con cualquier editor de texto.
- **Cómo usarlo:** Copia todo el contenido del archivo `.md` y pégalo en una IA con capacidad de generar imágenes (ChatGPT con imagen, Google Gemini, Grok, Ideogram, Flux, etc.).

**Uso rápido:**
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
python scripts/orchestrator/generate_infographic_prompt.py
```

Tras ejecutarlo, la consola te mostrará la ruta exacta del archivo generado. Ahí tendrás el prompt con los datos actuales del sistema (fechas de descubrimiento, elementos orbitales, actividad y comparativa entre 1I, 2I y 3I).

## Estado de las fases
- **Infraestructura (implementación estructural):** Fases 0-6 - **IMPLEMENTADAS**
- **Fase 0:** Preparación - **EJECUTADA**
- **Fase 1:** Ingesta histórica inicial - **EJECUTADA**
- **Fase 2:** Agentes base y skills - **IMPLEMENTADA, PENDIENTE DE EJECUCIÓN**
- **Fase 3:** Validación, correlación y reportes - **IMPLEMENTADA, PENDIENTE DE EJECUCIÓN**
- **Fase 4:** Búsqueda retrospectiva - **IMPLEMENTADA, PENDIENTE DE EJECUCIÓN**
- **Fase 5:** Orquestador completo y automatización - **IMPLEMENTADA, PENDIENTE DE EJECUCIÓN**
- **Fase 6:** Curador multimedia (YouTube) - **IMPLEMENTADA, PENDIENTE DE EJECUCIÓN**

---
*Sistema ISO Tracker - Infraestructura 0-6 implementada; solo fases 0-1 ejecutadas, fases 2-6 pendientes de ejecución.*
