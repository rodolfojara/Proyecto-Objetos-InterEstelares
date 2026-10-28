# Instrucciones para GitHub

**Cuenta:** `github.com/rodolfojara`
**Repositorio:** [Proyecto-Objetos-InterEstelares](https://github.com/rodolfojara/Proyecto-Objetos-InterEstelares) (público)

## Estado actual (actualizado)

✓ Repositorio creado y proyecto subido (rama `main`)
✓ Directorio del proyecto: `C:\Users\user\Documents\Proyecto Objetos InterEstelares`
✓ GitHub CLI (`gh`) instalado y autenticado

## Flujo de trabajo habitual

Para subir cambios (modificaciones, nuevas fases, correcciones):

```bash
cd "C:\Users\user\Documents\Proyecto Objetos InterEstelares"
git add .
git commit -m "Descripción breve del cambio"
git push
```

## Verificar estado

```bash
git status              # ver cambios pendientes
git log --oneline -5    # últimos commits
gh repo view            # info del repositorio
```

## Archivos clave documentados

- `README.md` - Guía general del sistema
- `HANDOFF.md` - Contexto e historia del proyecto (punto de partida para retomar)
- `docs/EXECUTION.md` - Instrucciones de ejecución de todos los scripts
- `docs/MULTIMEDIA_CURATOR.md` - Curador de vídeos de YouTube
- `docs/PRESENTACION_EJEMPLO.md` - Ejemplo de página de presentación
- `README_FASE5.md` - Orquestador maestro y automatización

## Notas

- El `.gitignore` excluye `logs/`, `__pycache__/`, archivos temporales de SQLite (`*.db-wal`, `*.db-shm`, `*.db-journal`) y archivos de IDE.
- La base de datos `data/db/iso.db` se incluye en el repo con los datos iniciales de los 3 objetos.
- No incluir contenido ajeno al proyecto (CV, vídeos fuera de tema, credenciales).
