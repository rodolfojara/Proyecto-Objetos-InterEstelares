# Guía de Ejecución - ISO Tracker

Este documento contiene **instrucciones paso a paso** para ejecutar todos los scripts del proyecto. Todo lo necesario está en este repositorio.

## Ubicación
Todos los comandos se ejecutan desde la raíz del proyecto:
```bash
cd "C:\Users\user\Documents\Proyecto predeterminado"
```

## Fase 0 y 1 (Completadas)

### 1. Crear estructura y BD (ya hecho)
Ya ejecutado. Ver `config/schema.sql` y `data/db/iso.db`

### 2. Ingesta inicial
**Script:** `ingest_init.py`  
**Ubicación:** Raíz del proyecto  
**Cuándo usarlo:** Solo para inicialización/reset controlado

```bash
cd "C:\Users\user\Documents\Proyecto predeterminado"
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
cd "C:\Users\user\Documents\Proyecto predeterminado"
python apply_patch_fase2.py
```

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
cd "C:\Users\user\Documents\Proyecto predeterminado"
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
 erakimterence_context in messages as much as possible.
The thinking process makes step by step reasoning before responding, and then provides the final answer. The thinking process MUST NOT include tool calling. 
Based on the history, provide the final answer to the user.  
You are an expert in office software. Given a text document, you have to correct and improve it, making sure it is clear, and that the wordings are precise and the sentences are nice. Do not add comment, do not question, do not suggest. Just correct it and improve the wording. 
Provide the output as a final answer with a title markdown format. 
Here is the document: ...
'''
Exempel på alla egenskaper i moderna datorspel...
''' 
