#!/usr/bin/env python3
"""
Generate detailed prompt for infographic creation in external AI with vision/image generation
(Resumable - Fase 3 style)
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORT_DIR = os.path.join(BASE_DIR, 'reports')
CHECKPOINT_DIR = os.path.join(BASE_DIR, '.metadata_checkpoints')
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, 'fase3_infographic_checkpoint.json')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'fase3_infographic.log')


def log(msg):
    os.makedirs(LOG_DIR, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            log(f"Error cargando checkpoint: {e}")
    return {
        "started_at": datetime.utcnow().isoformat() + 'Z',
        "prompts_generated": [],
        "status": "in_progress"
    }


def save_checkpoint(cp):
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    cp['updated_at'] = datetime.utcnow().isoformat() + 'Z'
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cp, f, indent=2, ensure_ascii=False)


def generate_prompt(resumable=False, force=False):
    start_time = time.time()
    log("=" * 60)
    log("INICIO FASE 3 - GENERACIÓN DE PROMPT INFOGRÁFICO")
    log(f"Reporte dir: {REPORT_DIR}")
    log("=" * 60)

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

    if force and os.path.exists(CHECKPOINT_FILE):
        try:
            os.remove(CHECKPOINT_FILE)
            log("Checkpoint eliminado por --force")
        except Exception:
            pass

    cp = load_checkpoint()
    # Por defecto regenerar en ejecuciones normales/orquestador; --reanudar solo omite si ya completado.
    if resumable and not force and cp.get('status') == 'completed' and cp.get('prompts_generated'):
        log("Ya completado según checkpoint (reanudar). Usa --force para regenerar.")
        sys.exit(0)

    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d_%H-%M-%S')
    prompt_path = os.path.join(REPORT_DIR, f"infografia_prompt_{date_str}.md")

    prompt = f"""# PROMPT PARA IA CON GENERACIÓN DE IMÁGENES/INFOGRAFÍAS

Copia y pega TODO este prompt en una IA que tenga capacidad de generar imágenes/infografías (ChatGPT con imagen, Gemini, Grok, Midjourney, Ideogram, Flux, etc.)

## Contexto
Crear una infografía clara y científica sobre los tres objetos interestelares detectados hasta la fecha: 1I/'Oumuamua, 2I/Borisov y 3I/ATLAS.

## Objetivo
Generar una infografía educativa/científica que permita ver rápidamente la comparación entre los tres objetos, su evolución y datos clave.

## Datos a mostrar
Incluir obligatoriamente:
- **Título:** "Objetos Interestelares: 1I/'Oumuamua, 2I/Borisov y 3I/ATLAS"
- **Descubrimiento:** Fechas (19 Oct 2017, 30 Ago 2019, 1 Jul 2025)
- **Órbita:** Excentricidad (e), perihelio (q en au), inclinación (i), velocidad hiperbólica v_inf (km/s)
- **Actividad:** 1I sin coma evidente (debatido), 2I cometa activo con coma, 3I activo con seguimiento intenso
- **Origen/Destino:** Mencionar origen galáctico cuando sea relevante (basado en estudios)
- **Comparativa visual:** Iconos/diagramas mostrando diferencias
- **Evolución:** Línea temporal desde descubrimiento hasta actualidad
- **Datos clave:** Resaltar que son los únicos 3 objetos interestelares confirmados

## Requerimientos de diseño
- **Estilo:** Científico, minimalista, profesional. Tipo infografía para divulgación astronómica
- **Colores:** Fondo oscuro (#0a0a0a o azul espacial) con texto claro. Usar colores distintivos por objeto
- **Layout:** Dividir en secciones claras (header, comparativa, órbitas, actividad, línea temporal)
- **Iconografía:** Representaciones esquemáticas de asteroide/cometa. NO fotográficas reales si no hay, usar diagramas
- **Texto:** Conciso, legible. Incluir unidades (au, km/s)
- **Leyenda:** Clara y completa
- **Fuentes:** Mencionar MPC, JPL, arXiv como referencias

## Elementos visuales específicos
1. **Header** con título
2. **Tabla comparativa visual** con los 3 objetos lado a lado
3. **Diagrama orbital esquemático** mostrando trayectorias hiperbólicas
4. **Línea temporal** con fechas clave
5. **Sección "Datos orbitales"** con valores numéricos
6. **Sección "Actividad y composición"** resumida
7. **Notas**: "Únicos 3 objetos interestelares confirmados hasta la fecha"

## Formato
- Formato A4 vertical o poster A3 ratio (A4 portrait preferido para fácil lectura)
- Alta resolución
- Texto en español (o mantener nombres científicos)
- Sin exageraciones especulativas - centrarse en datos medidos

## Instrucciones extra
- Generar versión limpia, apta para guardar/compartir
- Priorizar claridad sobre decoración
- Si hay espacio, añadir mini-gráfica comparando v_inf/e
- Marcar explícitamente qué datos son medidos vs debatidos (ej: 1I actividad)

Fecha de generación del prompt: {now.strftime('%Y-%m-%d %H:%M:%S')}
"""

    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt)

    prompts = cp.get('prompts_generated', [])
    prompts.append(prompt_path)
    cp['prompts_generated'] = prompts[-50:]
    cp['last_prompt'] = prompt_path
    cp['status'] = 'completed'
    cp['finished_at'] = datetime.utcnow().isoformat() + 'Z'
    save_checkpoint(cp)

    elapsed = time.time() - start_time
    log("=" * 60)
    log("FIN FASE 3 - GENERACIÓN DE PROMPT INFOGRÁFICO")
    log(f"Tiempo transcurrido: {elapsed:.3f}s")
    log(f"Prompt generado: {prompt_path}")
    log("=" * 60)
    print(f'Infographic prompt generated: {prompt_path}')
    return prompt_path


def main():
    parser = argparse.ArgumentParser(description='Fase 3 - Generador de prompt infográfico resumable')
    parser.add_argument('--reanudar', action='store_true', help='Reanudar/verificar desde checkpoint')
    parser.add_argument('--force', action='store_true', help='Forzar nueva generación')
    args = parser.parse_args()
    generate_prompt(resumable=args.reanudar, force=args.force)


if __name__ == '__main__':
    main()
