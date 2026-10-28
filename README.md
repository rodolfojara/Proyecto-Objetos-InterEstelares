# Sistema de Seguimiento y Análisis de Objetos Interestelares (ISO Tracker)

Sistema multi-agente/orquestado para recolectar, normalizar, versionar, correlacionar y presentar información sobre objetos interestelares (1I/'Oumuamua, 2I/Borisov, 3I/ATLAS) y futuros descubrimientos.

## Estado del proyecto
- Fase 0: Preparación - **COMPLETADA**
- Fase 1: Ingesta histórica inicial - **COMPLETADA**
- Fase 2: Agentes base - Pendiente
- Fase 3: Validación y correlación - Pendiente
- Fase 4: Búsqueda retrospectiva - Pendiente
- Fase 5: Automatización - Pendiente

> Cuando se mencione una fase por número (Fase 0, Fase 1, ..., Fase 5), se entiende tal como está definida en este proyecto.

## Estructura del proyecto
```
Proyecto Objetos InterEstelares/
├── config/
│   ├── schema.sql        # Esquema SQLite
│   └── sources.json      # Fuentes a monitorear (por crear en fases posteriores)
├── data/
│   ├── db/iso.db         # Base de datos SQLite
│   ├── objects.json      # Datos iniciales de objetos
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
├── logs/                 # Logs de ejecución
└── ingest_init.py        # Script de ingesta inicial (Fase 0/1)
```

## Requisitos
- Python 3.x (sqlite3 viene incluido)
- Acceso a internet para consultas (MPC/JPL/arXiv) - las fases posteriores lo usarán
- No se requiere instalación externa obligatoria para las fases 0-1

## Base de datos
La base de datos se crea en: `data/db/iso.db`

Tablas principales:
- `objects` - Objetos interestelares
- `orbital_elements` - Elementos orbitales (versionados)
- `physical_params` - Parámetros físicos (versionados)
- `composition` - Composición/producción de gases
- `activity` - Actividad/ coma
- `publications` - Papers (arXiv/DOI)
- `object_publications` - Relación objetos-papers
- `observations` - Observaciones
- `provenance_log` - Bitácora inmutable
- `report_metrics` - Métricas para reportes

## Scripts y cómo ejecutarlos

### Ingesta inicial (Fase 0/1 - ya ejecutado)
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
python ingest_init.py
```
**Ubicación:** `ingest_init.py` (raíz del proyecto)
**Qué hace:** Carga 1I/'Oumuamua, 2I/Borisov, 3I/ATLAS desde `data/objects.json` a la DB con sus elementos orbitales y actividad inicial, registrando en `provenance_log`.

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
- **Fase 0:** Preparación - **COMPLETADA**
- **Fase 1:** Ingesta histórica inicial - **COMPLETADA**
- **Fase 2:** Agentes base y skills - **COMPLETADA**
- **Fase 3:** Validación, correlación y reportes - **COMPLETADA**
- **Fase 4:** Búsqueda retrospectiva - **COMPLETADA**
- **Fase 5:** Orquestador completo y automatización - **COMPLETADA**
- **Fase 6:** Curador multimedia (YouTube) - **COMPLETADA**

---
*Sistema ISO Tracker - Todas las fases 0-6 completadas*
