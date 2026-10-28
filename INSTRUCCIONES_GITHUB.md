# Instrucciones para subir a GitHub

**Cuenta objetivo:** `github.com/rodolfojara`  
**Nombre de repositorio sugerido:** `Proyecto-Objetos-InterEstelares`

## 1) Renombrar directorio (cuando esté libre)
El directorio actual está en uso. Cuando puedas, renómbralo:
```text
De: C:\Users\user\Documents\Proyecto predeterminado
A: C:\Users\user\Documents\Proyecto Objetos InterEstelares
```

## 2) Inicializar git
Desde la raíz del proyecto:
```bash
cd "C:\Users\user\Documents\Proyecto predeterminado"  # o "Proyecto Objetos InterEstelares" tras renombrar
git init
git branch -M main
```

## 3) Crear .gitignore
Crear archivo `.gitignore` con:
```
logs/
__pycache__/
*.pyc
*.pyo
*.db-wal
*.db-shm
*.log
.DS_Store
Thumbs.db
```

## 4) Añadir remote
Si necesitas permisos para crear el repo en `github.com/rodolfojara`, solicítalos. Luego:
```bash
git remote add origin https://github.com/rodolfojara/Proyecto-Objetos-InterEstelares.git
```

## 5) Commit inicial
```bash
git add .
git commit -m "Initial commit: Sistema de seguimiento de Objetos Interestelares (1I, 2I, 3I) - Fases 0-6 + HANDOFF"
git push -u origin main
```

## 6) Archivos clave a revisar
- `README.md` - Guía general
- `HANDOFF.md` - Contexto completo para continuar
- `docs/EXECUTION.md` - Instrucciones de ejecución
- `docs/MULTIMEDIA_CURATOR.md` - Curador multimedia
- `docs/PRESENTACION_EJEMPLO.md` - Ejemplo de página de presentación
- `README_FASE5.md` - Orquestador

**Nota:** No se incluye CV ni contenido ajeno al proyecto. Todo está enfocado a objetos interestelares.
