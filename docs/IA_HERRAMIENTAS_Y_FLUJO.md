# Uso de IA, herramientas y flujo de trabajo

Este documento describe cómo se utiliza la IA para este proyecto, qué herramientas se emplean, cómo se organizan (agentes/skills/loops) y las buenas prácticas para mantener trazabilidad e integridad de los datos.

## 1. Modelo y entorno

- **Agente**: OpenCode (Big Pickle, proveedor `opencode`, modelo `big-pickle`)
- **Entorno**: Windows, repositorio en `C:\Users\user\Documents\Proyecto Objetos InterEstelares\`
- **Objetivo**: Asistir en el análisis, desarrollo, depuración y automatización manteniendo la integridad de la base de datos científica.

## 2. Herramientas disponibles

El agente dispone de herramientas para interactuar con el sistema y el código:

| Herramienta | Uso |
| --- | --- |
| `read` | Leer archivos y directorios |
| `write` | Crear/sobreescribir archivos completos |
| `edit` | Ediciones quirúrgicas con reemplazo exacto |
| `glob` | Buscar archivos por patrón |
| `grep` | Buscar contenido por regex/literal |
| `shell` | Ejecutar comandos del sistema (usar con criterio) |
| `subagent` | Delegar tareas a subagentes especializados (`explore`, `general`) |
| `skill` | Cargar habilidades predefinidas cuando aplique |
| `question` | Preguntar al usuario para aclarar ambigüedad |
| `webfetch`/`websearch` | Obtener información externa cuando sea necesario |
| `execute`/`tools.*` (Code Mode) | Invocar herramientas del catálogo cuando corresponda |

## 3. Diferencia entre loop, agentes y skills

Para este proyecto, el enfoque es práctico y orientado a la seguridad de datos.

| Concepto | ¿Qué es? | ¿Cuándo usarlo aquí? |
| --- | --- | --- |
| **Loop / flujo secuencial** | Ejecución paso a paso con checkpoints, commits parciales y reanudación. | Tareas largas/propensas a interrupción (recolección de metadatos, Fase 2). Es el patrón usado ahora con `--reanudar`, locks y verificaciones. |
| **Agente** | Entidad con razonamiento que planifica, usa herramientas y puede delegar. Aquí es el agente principal (OpenCode) con acceso a las herramientas. | Tareas complejas: diseño de soluciones, depuración, refactorización, coordinación multi-archivo. |
| **Subagente** | Agente especializado invocado por el principal para una tarea acotada. | Exploración rápida (`explore`) o investigación/ejecución paralela (`general`). Se usa para ganar contexto sin contaminar el hilo principal. |
| **Skill** | Conjunto de instrucciones/recursos cargado bajo demanda para un tipo de tarea. | Cuando la tarea coincide con la descripción del skill (ej. `opencode`, `report`). Aplica reglas/contexto predefinidos sin reescribir todo. |

### Diagrama conceptual

```text
Usuario
  ↓
Agente principal (OpenCode) ──┬── usa herramientas (read/edit/write/shell/grep/glob)
                              ├── delega a subagente (explore/general) para búsqueda/acotado
                              ├── carga skill si aplica (reglas específicas)
                              └── ejecuta flujos por lotes/loops (con checkpoint + reanudación)
                                   ↓
                                Scripts (orchestrator) con modo por lotes
                                   ↓
                                SQLite (iso.db) con commits parciales + verificación
```

**Regla práctica**: Para trabajo mecánico repetitivo y largo (pases bibliográficos, Fase 2), se prefiere **flujo por lotes con checkpoint** (loop controlado). Para análisis/comprensión o cambios complejos, se usa el **agente principal** con herramientas; para búsquedas exhaustivas se delega a **subagentes**. Los **skills** solo se cargan cuando encajan estrictamente con la tarea.

## 4. Buenas prácticas para este proyecto

- **Integridad ante todo**: No tocar tablas científicas (`orbital_elements`, `physical_params`, `composition`, `activity`) a menos que sea explícitamente necesario. Las tablas `publications`, `object_publications`, `provenance_log` son las que se usan para metadatos.
- **Idempotencia**: Siempre asumir que una ejecución puede repetirse. Usar `INSERT OR IGNORE`, comprobaciones por identificador (DOI/arXiv), y no sobrescribir datos mejores.
- **Resiliencia**: Usar modo por lotes con checkpoint, commits parciales, locks y caché. Tras interrupción, reanudar con `--reanudar` en lugar de empezar desde cero.
- **Trazabilidad**: Registrar acciones relevantes en `provenance_log` cuando se modifiquen `publications`.
- **Verificación**: Tras cargas por ventana/lote, comprobar duplicados y enlaces huérfanos.
- **Transparencia**: Mostrar plan de lotes, avance y qué queda por ejecutar.

## 5. Comandos útiles

```bash
# Recolector con modo por lotes
python scripts/orchestrator/collect_metadata_openalex.py --cache-dir .cache_meta --commit-cada 10

# Reanudar tras interrupción
python scripts/orchestrator/collect_metadata_openalex.py --cache-dir .cache_meta --reanudar

# Solo una ventana para pruebas
python scripts/orchestrator/collect_metadata_openalex.py --solo 3I --dry-run
```

## 6. Notas

- El modo por lotes con checkpoint/reanudación está implementado en `collect_metadata_openalex.py` y con caché parcial en `metadata_discovery.py`.
- Para futuras fases (Fase 2), se aplicará el mismo patrón: plan de lotes visible, checkpoint por fase, reanudación idempotente y verificación al finalizar.
