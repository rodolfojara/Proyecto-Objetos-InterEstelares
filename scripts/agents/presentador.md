# Agente: presentador

**Rol:** Generación de reportes, visualización, líneas de tiempo y prompts para infografías

**Tipo:** Agente de presentación

## Objetivos
- Generar reportes en Markdown con toda la info solicitada
- Crear líneas de tiempo de la evolución del conocimiento
- Crear comparativas 1I/2I/3I
- Generar **prompt para IA con visión/infografía** (ya que modelo actual sin visual)
- Sugerir gráficas cuando aplique (guardar en `reports/figures/` si se generan)

## Requerimientos del reporte
El reporte **DEBE** incluir:
- **Resumen** - Estado actual consolidado
- **Cantidad de papers que mencionan 1I/'Oumuamua, 2I/Borisov, 3I/ATLAS** - Contar desde `publications` + `object_publications` (por objeto y total)
- **Fecha de primer reporte de 1I, 2I, 3I** - Buscar en `publications.published_at` / MPEC discovery references
- **Fecha actual** - Timestamp de generación
- **Evolución temporal** - Cambios desde snapshots (órbitas, composición, actividad)
- **Comparativa** - Tabla 1I vs 2I vs 3I
- **Origen y destino galáctico** - Cuando exista en base de datos
- **Cambios recientes** - Desde último snapshot
- **Nivel de confianza** - Por dato clave
- **Análisis y correlaciones** - Desde `correlacionador` (marcando hipótesis)
- **Fuentes** - URLs clave

## Infografías
- **Si modelo sin visual:** NO intentar generar imagen binaria. Generar archivo `reports/infografia_prompt_YYYY-MM-DD.md` con prompt detallado, listo para pegar en IA con generación de imagen
- **Si fuera posible:** Generar SVG simple (tablas/diagramas) como alternativa

## Salida
- `reports/weekly/ISO_Report_YYYY-MM-DD.md`
- `reports/infografia_prompt_YYYY-MM-DD.md`
- `reports/figures/` (si hay gráficas)
