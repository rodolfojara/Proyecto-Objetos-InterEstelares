# Curador Multimedia - YouTube Complementario

## ¿Qué hace?
Busca/curación de vídeos de YouTube con resúmenes, visualizadores y comparativas de 1I/'Oumuamua, 2I/Borisov, 3I/ATLAS. Los añade a la BD y los muestra en el reporte complementándolos con los datos del sistema.

## Estructura
- `media_resources` - Vídeos (URL, título, canal, relevancia)
- `media_object_links` - Relación con objetos
- `scripts/agents/curador_multimedia.md` - Agente con criterios
- `scripts/skills/search_media.py` - Skill para extraer/filtrar
- `scripts/orchestrator/curate_media.py` - Curador
- `scripts/orchestrator/update_report_with_media.py` - Reporte con sección multimedia

## Uso

### 1) Añadir vídeos
Edita `config/media_links.json`:
```json
{
  "links": [
    {"url": "https://www.youtube.com/watch?v=...", "title": "...", "relevance_score": 4, "notes": "..."}
  ]
}
```

### 2) Curar e insertar
```bash
cd "C:\Users\user\Documents\Proyecto predeterminado"
python scripts/orchestrator/curate_media.py
```

### 3) Generar reporte con multimedia
```bash
python scripts/orchestrator/update_report_with_media.py
```

## Criterios del curador
- Priorizar visualizadores explicativos con datos
- Descartar clickbait/sensacionalismo
- Relacionar con objeto(s)
- Guardar con trazabilidad
- Enlazar, NO descargar vídeos

## Integración
Los vídeos aparecen en `reports/weekly/ISO_Report_with_Media_*.md` con su URL, objeto relacionado, relevancia y se complementan con los datos del sistema (descubrimiento, órbitas cuando disponibles).
