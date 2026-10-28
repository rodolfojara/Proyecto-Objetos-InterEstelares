# HANDOFF - Proyecto Objetos InterEstelares

**Fecha:** 2026-10-26  
**Propósito:** Transferir contexto limpio para continuar el desarrollo del sistema de seguimiento de objetos interestelares.

---

## 1. Objetivo
Desarrollar un sistema modular para recolectar, normalizar, versionar, correlacionar y presentar información sobre objetos interestelares confirmados (**1I/'Oumuamua**, **2I/Borisov**, **3I/ATLAS**) con capacidad para incorporar futuros descubrimientos.

---

## 2. Historia del desarrollo
- **Fase 0:** Estructura de carpetas, esquema SQLite base, configuración inicial - **IMPLEMENTADA Y EJECUTADA**
- **Fase 1:** Ingesta histórica inicial de los 3 objetos con elementos orbitales y actividad - **IMPLEMENTADA Y EJECUTADA**
- **Fase 2:** Agentes base (vigilante, recolector, normalizador), skills reutilizables, tabla `object_aliases` para manejar múltiples designaciones/alias de un objeto - **IMPLEMENTADA ESTRUCTURALMENTE, PENDIENTE DE EJECUCIÓN**
- **Fase 3:** Validación cruzada con fuentes primarias, correlacionador con análisis asistido (hipótesis marcadas), presentador, generador de reportes con métricas requeridas y generador de prompt para infografías (modelo sin capacidad visual) - **IMPLEMENTADA ESTRUCTURALMENTE, PENDIENTE DE EJECUCIÓN**
- **Fase 4:** Búsqueda retrospectiva de candidatos hiperbólicos (e > 1) con tablas `retro_candidates` y `retro_candidate_reviews` - **IMPLEMENTADA ESTRUCTURALMENTE, PENDIENTE DE EJECUCIÓN**
- **Fase 5:** Orquestador maestro (`master_orchestrator.py`), utilidades y automatización manual/Task Scheduler/cron - **IMPLEMENTADA ESTRUCTURALMENTE, PENDIENTE DE EJECUCIÓN**
- **Fase 6:** Curador multimedia (YouTube) con tablas `media_resources` y `media_object_links`, criterios de curación, integración a reportes - **IMPLEMENTADA ESTRUCTURALMENTE, PENDIENTE DE EJECUCIÓN**

---

## 3. Arquitectura
- **Base de datos:** SQLite (`data/db/iso.db`) con trazabilidad via `provenance_log`
- **Agentes:** Roles especializados con instrucciones en `scripts/agents/*.md`
- **Skills:** Funciones reutilizables en `scripts/skills/*.py`
- **Orquestador:** `scripts/orchestrator/master_orchestrator.py` para ejecución coordinada
- **Reportes:** Generados en `reports/weekly/`
- **Prompts infográficos:** Generados en `reports/` para uso con IA externa

---

## 4. Estado actual
- **Objetos:** 1I/'Oumuamua, 2I/Borisov, 3I/ATLAS registrados (mediante ingesta Fase 0-1 ejecutada)
- **Tablas:** 16 tablas (incluyendo aliases, candidatos retrospectivos, multimedia) - esquema completo implementado
- **Infraestructura:** Fases 0-6 implementadas estructuralmente. Solo Fases 0-1 ejecutadas. Fases 2-6 pendientes de ejecución.
- **Multimedia:** Sistema implementado pero sin vídeos añadidos (se eliminaron enlaces erróneamente añadidos)
- **Infografías:** Requieren generación externa via prompt

---

## 5. Puntos clave para continuar
- **Nuevos objetos:** Al detectar un nuevo ISO, agregar con TODOS sus alias en `object_aliases`
- **Versionado:** Nunca sobrescribir datos; guardar con fuente, fecha, agente, confianza
- **Fuentes primarias:** Priorizar MPC, JPL Horizons/SBDB
- **Búsqueda retrospectiva:** Enfocar en trayectorias hiperbólicas, filtrar artefactos
- **Multimedia:** Solo enlazar vídeos relacionados, curar con criterio
- **Reportes:** Deben incluir conteo de papers por objeto, fecha primer reporte, fecha actual, evolución, comparativa

---

## 6. Comandos rápidos
```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
python scripts/utils/check_status.py
python scripts/orchestrator/generate_report.py
python scripts/orchestrator/generate_infographic_prompt.py
```

**Directorio:** `C:\Users\user\Documents\Proyecto Objetos InterEstelares`  
**Cuenta GitHub:** `github.com/rodolfojara`
