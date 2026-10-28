# Ejemplo de página de presentación - Objetos InterEstelares

> **Propósito:** Mostrar cómo quedaría la página de presentación final con datos ejemplo basados en lo que el sistema ya tiene. Esto es un ejemplo ilustrativo, no datos definitivos. Todos los valores mostrados son datos esperados/consolidados y se generan automáticamente desde la base de datos.

---

## Título
**Objetos Interestelares en el Sistema Solar: 1I/'Oumuamua, 2I/Borisov, 3I/ATLAS**

## Resumen
Los objetos interestelares son cuerpos que provienen de otros sistemas estelares y atraviesan nuestro Sistema Solar en trayectorias hiperbólicas. Hasta la fecha, solo se han confirmado tres: 1I/'Oumuamua (2017), 2I/Borisov (2019) y 3I/ATLAS (2025).

---

## Comparativa rápida (Datos ejemplo desde BD)
*Estos datos provienen de la tabla `objects` y `orbital_elements` del sistema ISO Tracker.*

| Parámetro | 1I/'Oumuamua *(ejemplo)* | 2I/Borisov *(ejemplo)* | 3I/ATLAS *(ejemplo)* |
| :-- | :-- | :-- | :-- |
| Designación | 1I/2017 U1 ('Oumuamua) | 2I/2019 Q4 (Borisov) | 3I/2025 N1 (ATLAS) |
| Descubrimiento | 19 de octubre de 2017 | 30 de agosto de 2019 | 1 de julio de 2025 |
| Excentricidad (e) | ~1.1995 | ~3.3565 | ~6.140 |
| Perihelio (q) | ~0.2559 au | ~2.0066 au | ~1.356 au |
| Inclinación (i) | ~122.68° | ~44.05° | ~175.11° |
| Velocidad hiperbólica v_inf | ~26.33 km/s | ~32.30 km/s | ~58.00 km/s |
| Actividad | Sin coma evidente (debatido) | Cometa activo con coma visible | Activo, seguimiento intenso |
| Origen galáctico | Disco delgado/joven (estimado) | Disco intermedio (estimado) | Disco grueso/antiguo (estimado) |

*Valores basados en datos consolidados en la base de datos del sistema. Pueden actualizarse conforme se añaden nuevos análisis.*

---

## Evolución del conocimiento (Ejemplo de seguimiento)
El sistema rastrea cómo han ido cambiando estos valores con el tiempo (elementos orbitales, actividad, composición) gracias al versionado, trazabilidad por fuente y nivel de confianza.

**Línea temporal (datos ejemplo):**
- **Oct 2017:** Descubrimiento de 1I/'Oumuamua (MPEC)
- **Nov 2017:** Primeras estimaciones orbitales, debate sobre actividad
- **Ago 2019:** Descubrimiento de 2I/Borisov
- **Sep 2019:** Confirmación de coma cometaria
- **Jul 2025:** Descubrimiento de 3I/ATLAS
- **Jul-Oct 2025:** Seguimiento intensivo, estudios espectroscópicos y composicionales
- **Oct 2026:** Monitoreo continuo con actualizaciones desde preprints y observatorios

---

## Recursos audiovisuales complementarios (Página de búsquedas)
El curador multimedia (`scripts/orchestrator/curate_media.py`) busca, filtra y enlaza vídeos explicativos/visualizadores curados de YouTube relacionados con objetos interestelares. **Solo se enlazan URLs, nunca se descargan vídeos**.

### Ejemplo de presentación en página web
| Vídeo (EJEMPLO - Ilustrativo) | Relación con objeto | Tipo | Relevancia | Notas |
| :-- | :-- | :-- | :--: | :-- |
| [Interstellar Comets: 1I/'Oumuamua, 2I/Borisov & 3I/ATLAS Explained](https://www.youtube.com/results?search_query=Interstellar%20Comets%20Oumuamua%20Borisov%20ATLAS%20explained) | Comparativo (1I, 2I, 3I) | Visualizador/Explicativo | 5/5 *(ejemplo)* | *Ejemplo ilustrativo.* En producción, el sistema mostrará vídeos reales curados que hayan pasado el filtro del `curador_multimedia`. |

> **Nota:** En el sistema real, esta tabla se genera automáticamente desde `media_resources` y `media_object_links`. Los vídeos solo aparecen tras ser revisados con los criterios del curador (priorizar contenido con datos orbitales/compositivos, descartar clickbait). Este enlace es un ejemplo de búsqueda, no un vídeo específico curado. 

---

## Métricas del sistema (Datos ejemplo)
*Estos valores se generan con `scripts/orchestrator/generate_report.py`*

| Métrica | Estado | Descripción |
| :-- | :-- | :-- |
| Papers vinculados (1I/2I/3I) | *0 / Por actualizar* | Contados desde `publications` + `object_publications` |
| Fecha primer reporte | *Por obtener* | Primera mención oficial/MPEC o publicación |
| Última actualización | *2026-10-26* | Timestamp de generación del reporte |
| Candidatos retrospectivos | *0* | Desde búsqueda en archivos históricos (e > 1) |
| Recursos multimedia curados | *0* | Tras aplicar filtros del curador |

---

## Reportes y datos
- **Reporte semanal/consolidado:** `reports/weekly/ISO_Report_*.md` (incluye conteo de papers, fecha primer reporte, fecha actual, evolución temporal, comparativa, nivel de confianza)
- **Reporte con multimedia:** `reports/weekly/ISO_Report_with_Media_*.md` (añade sección "Recursos audiovisuales complementarios" con enlaces curados)
- **Prompt para infografía:** `reports/infografia_prompt_*.md` (generado con `scripts/orchestrator/generate_infographic_prompt.py` para usar en IA externa con generación de imágenes)
- **Búsqueda retrospectiva:** `reports/retro_search_*.md` (candidatos hiperbólicos encontrados)
- **Base de datos:** `data/db/iso.db` con trazabilidad completa via `provenance_log`

---

## Cómo replicar esta presentación
1. **Ver estado:** `python scripts/utils/check_status.py`
2. **Generar reporte:** `python scripts/orchestrator/generate_report.py`
3. **Generar prompt infográfico:** `python scripts/orchestrator/generate_infographic_prompt.py`
4. **Curar multimedia:** Editar `config/media_links.json` con URLs válidas → `python scripts/orchestrator/curate_media.py` → `python scripts/orchestrator/update_report_with_media.py`
5. **Buscar retrospectivamente:** `python scripts/orchestrator/run_retro_search.py`
6. **Publicar:** Subir a GitHub con `README.md`, `HANDOFF.md`, `docs/` e instrucciones

---

**Nota:** Este documento es un **ejemplo ilustrativo** para mostrar la estructura esperada de la página de presentación. Los valores numéricos son ejemplos basados en datos conocidos de los objetos. El sistema genera reportes reales desde la base de datos con trazabilidad completa. Todos los vídeos mostrados son enlaces a resultados de búsqueda o ejemplos, no contenido alojado localmente.


---

## Reportes y datos
- **Reporte generado:** `reports/weekly/ISO_Report_*.md` (incluye conteo de papers, fecha primer reporte, fecha actual, comparativa)
- **Prompt infográfico:** `reports/infografia_prompt_*.md` (generado con `scripts/orchestrator/generate_infographic_prompt.py` para usar en IA externa con generación de imágenes)
- **Base de datos:** `data/db/iso.db` con trazabilidad completa

---

## Cómo replicar esta presentación
1. Ejecutar `python scripts/orchestrator/generate_report.py` para obtener el reporte actualizado
2. Ejecutar `python scripts/orchestrator/generate_infographic_prompt.py` para generar prompt de infografía
3. Curar vídeos con `python scripts/orchestrator/curate_media.py` y `update_report_with_media.py`
4. Publicar en GitHub con documentación clara usando `README.md`, `HANDOFF.md` y este ejemplo

---

**Nota:** Este ejemplo es puramente ilustrativo para mostrar la estructura de presentación. Los valores mostrados provienen de las fuentes consolidadas en el sistema.
