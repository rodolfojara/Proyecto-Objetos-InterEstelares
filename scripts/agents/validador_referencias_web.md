# Agente: Validador de Referencias Web (curación asistida)

## Propósito
Asistir en la curación de referencias web (complemento a papers/YouTube) aplicando **reglas/filtros configurables** para pre-clasificar y señalar referencias. **No reemplaza el juicio humano**: la calidad final, la detección de la “goyita” (aporte sobre el promedio) y la aceptación la decide el curador.

## Método (alineado al curador humano)
1. Fuentes confiables primero (NASA/JPL/MPC/ESA/observatorios, literatura) como base.
2. Evaluación referencia por referencia: consistencia/calidad; guardar lo que aporta valor, con nota.
3. Una fuente desactualizada puede aceptarse si está bien informada/adecuadamente reportada y aporta (contexto histórico/causal).

## Qué hace (v1, basado en reglas)
- Lee `config/web_references.json` y `config/web_reference_rules.json`.
- Verifica señales básicas: accesibilidad HTTP (opcional), dominio (trusted/caution), relevancia por palabras clave (1I/2I/3I/interestelar), patrones de exclusión en título, presencia de resumen/nota de evaluación.
- Escribe `agent_review`, `agent_suggested_status`, `agent_suggested_value` (1-10) **como sugerencia** en el config.
- Script: `scripts/orchestrator/validate_web_references.py` (`--skip-http`, `--only-pending`).

## “Aprendizaje” (iterativo, controlado por el usuario)
No hay entrenamiento ML automático. El aprendizaje es por **refinamiento de reglas**:
- Tras revisar los resultados del agente, el curador ajusta `status/value_score/evaluation_note` y **agrega/afina filtros** en `config/web_reference_rules.json` (dominios, keywords, `title_exclude_patterns`, umbrales).
- Se vuelve a ejecutar el validador; las sugerencias mejoran según las reglas acumuladas.

## Flujo de trabajo
1. Curador agrega referencias a `config/web_references.json` (status `pending`/`accepted`, con resumen y nota de evaluación cuando corresponda).
2. (Opcional) Ejecutar `python scripts/orchestrator/validate_web_references.py` → genera sugerencias/flags.
3. Curador revisa: fija `status` (`accepted`/`watch`/`rejected`), `value_score` (1-10), `evaluation_note` (y motivo si `rejected`); amplía reglas si hace falta.
4. Ejecutar `python scripts/orchestrator/curate_web_references.py` para ingestar en BD (todas; `rejected` se guarda con nota pero no se muestra en reportes).
5. Regenerar dashboard: `python scripts/orchestrator/generate_dashboard.py --force`.

## Salidas
- Sugerencias en `config/web_references.json` (campos `agent_*`).
- Log: `logs/validate_web_references.log`.
- BD (vía curador): `curated_references`, `curated_reference_object_links`.