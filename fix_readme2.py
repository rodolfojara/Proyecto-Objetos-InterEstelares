with open(r'C:/Users/user/Documents/Proyecto predeterminado/README.md',encoding='utf-8') as f:
    s=f.read()

old = "## Próximos pasos\n- Fase 2: Crear agentes base (`vigilante`, `recolector`, `normalizador`) y skills (`parse_mpec`, `extract_orbital_elements`, `normalize_units`)\n- Fase 3: Implementar `validador`, `correlacionador` (con análisis tipo humano pero marcado como hipótesis) y visualización\n- Fase 4: Búsqueda retrospectiva\n- Fase 5: Orquestador y automatización\n\n---\n*Generado para proyecto ISO Tracker - Fases 0 y 1 completadas*"

new = """## Recursos audiovisuales (complemento multimedia)
El sistema cuenta con un **curador multimedia** para añadir vídeos de YouTube complementarios a los objetos interestelares, enlazarlos con la base de datos y mostrarlos en los reportes junto a los datos del sistema.

- **Documentación completa:** `docs/MULTIMEDIA_CURATOR.md`
- **Agente:** `scripts/agents/curador_multimedia.md`
- **Curador:** `scripts/orchestrator/curate_media.py`
- **Reporte con multimedia:** `scripts/orchestrator/update_report_with_media.py`
- **Configuración:** `config/media_links.json`

**Uso rápido:**
```bash
cd "C:\\Users\\user\\Documents\\Proyecto predeterminado"
# Editar config/media_links.json con URLs de vídeos relacionados con 1I/'Oumuamua, 2I/Borisov o 3I/ATLAS
python scripts/orchestrator/curate_media.py
python scripts/orchestrator/update_report_with_media.py
```

**Notas:** Solo se enlazan vídeos (no se descargan). Se priorizan visualizadores explicativos con datos y se descarta contenido sensacionalista. Todo queda registrado en `media_resources` y `media_object_links` con trazabilidad.

## Estado de las fases
- **Fase 0:** Preparación - **COMPLETADA**
- **Fase 1:** Ingesta histórica inicial - **COMPLETADA**
- **Fase 2:** Agentes base y skills - **COMPLETADA**
- **Fase 3:** Validación, correlación y reportes - **COMPLETADA**
- **Fase 4:** Búsqueda retrospectiva - **COMPLETADA**
- **Fase 5:** Orquestador completo y automatización - **COMPLETADA**
- **Fase 6:** Curador multimedia (YouTube) - **COMPLETADA**

---
*Sistema ISO Tracker - Todas las fases 0-6 completadas*"""

if old in s:
    s2 = s.replace(old, new)
    with open(r'C:/Users/user/Documents/Proyecto predeterminado/README.md','w',encoding='utf-8') as f:
        f.write(s2)
    print('done')
else:
    print('not found')
