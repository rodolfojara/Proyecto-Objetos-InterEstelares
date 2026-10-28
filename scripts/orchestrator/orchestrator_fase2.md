# Orquestador - Fase 2

**Propósito:** Coordinar agentes/skills para Fase 2

## Flujo Fase 2
1. **Inicialización** - Verificar estructura, DB, schema patch aplicado
2. **Detección de nuevos ISOs** - `vigilante` revisa fuentes con enfoque en e>1/hiperbólicos
3. **Gestión de objetos** - Si nuevo objeto detectado con múltiples alias → crear en `objects` + `object_aliases` + log en `provenance_log`
4. **Recolección** - `recolector` guarda crudo
5. **Normalización** - `normalizador` extrae y normaliza
6. **Preparación para Fase 3** - Dejar todo listo para validación/correlación

## Lógica: "¿Apareció nuevo objeto interestelar?"
```python
# Pseudocódigo
candidates = vigilante.detect_hyperbolic()
for c in candidates:
    if not exists_in_db(c.designations):
        # Crear objeto nuevo
        create_object(designation=c.primary, ...)
        # Añadir TODOS los alias
        for alias in c.all_aliases:
            add_alias(object_id, alias, source_url)
        log_provenance('objects', new_id, 'insert_new_iso', 'vigilante', ...)
```

## Scripts a ejecutar (manual por ahora)
```bash
cd "C:\Users\user\Documents\Proyecto predeterminado"
python scripts/orchestrator/run_fase2_check.py  # (se creará si necesario)
```

## Notas
- Manual execution - no daemon 24/7
- Todo versionado y con provenance
- Aliases son críticos para no duplicar objetos
