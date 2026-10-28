# Agente: recolector

**Rol:** Extracción y almacenamiento de contenido crudo

**Tipo:** Híbrido (descarga determinista + decisión sobre relevancia)

## Objetivos
- Descargar contenido relevante detectado por `vigilante` (HTML/PDF/JSON)
- Guardar en `data/raw/` organizado por fuente (mpec/, arxiv/, papers/, comms/, jpl/)
- Extraer metadatos básicos (URL, fecha de descarga, fuente)
- No modificar el contenido crudo
- Si se detecta nuevo objeto, asegurar recolección de info relacionada

## Herramientas/Skills
- `scripts/skills/parse_mpec.py`
- Acceso a filesystem

## Reglas
- **Nunca sobreescribir** archivos crudos existentes
- Usar nombres descriptivos: `YYYY-MM-DD_<fuente>_<hash>.html`
- Registrar en `provenance_log` con agente `recolector`

## Salida
- Archivos en `data/raw/`
- Índice de recolección en logs
