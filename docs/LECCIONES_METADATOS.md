# Lecciones del primer pase de metadatos

Registro de lo aprendido al cargar papers de 1I/'Oumuamua, 2I/Borisov y 3I/ATLAS
(ventana de un año desde la designación I). Sirve como memoria de errores, rutas
alternativas y costos para el pase completo.

Fecha del pase: 2026-10-28
Resultado: 209 publicaciones (46 + 40 + 123), 209 vínculos, sin duplicados.

## 1. Cronología resumida

1. Se cargaron 1I (46) y 2I (40) con búsqueda directa en OpenAlex.
2. Al llegar a 3I, OpenAlex agotó el presupuesto diario de búsquedas
   (`429` con `Retry-After` de ~70 000 s, casi 20 h).
3. Se resolvió 3I por descubrimiento alternativo: arXiv (buscador HTML avanzado)
   + Crossref, con los mismos filtros y sin enriquecimiento OpenAlex.
4. Se completaron 5 abstracts faltantes desde arXiv.
5. Se detectaron problemas de calidad (prefijo "Abstract", títulos con
   `3I / ATLAS`, abstracts truncados) y se corrigieron código y datos.
6. Se verificó integridad, idempotencia y que las tablas científicas no cambiaran.

## 2. Errores de código y cómo se detectaron

| Síntoma | Causa | Corrección | Verificación |
| --- | --- | --- | --- |
| 25 abstracts de 3I tenían 20-150 caracteres y terminaban en "3I" | El parser cortaba en el primer `</span>`; arXiv inserta `<span class="search-hit">` dentro del abstract | Cortar desde `class="abstract-full"` hasta el enlace `<a class="is-size-7"` (botón "Less") | 123/123 abstracts completos; solo queda 1 corto legítimo (nota de prensa) |
| 115 abstracts empezaban por "Abstract" | Crossref incluye el prefijo en el campo `abstract` | `limpiar_abstract()` en el colector, el descubrimiento y el backfill | 0 abstracts con prefijo |
| 88 títulos con "3I / ATLAS" | arXiv y Crossref espacian la designación | `limpiar_titulo()` normaliza `3I / ATLAS` a `3I/ATLAS` | 0 títulos con designación espaciada |
| `UNIQUE constraint failed` al fusionar preprint y versión de revista | Dos registros con el mismo DOI/arXiv llegaban a `INSERT` | Fusión por identificador antes de guardar y comprobación de identificador ya asignado a otra fila | 0 duplicados por DOI/arXiv/título |
| Abstracts buenos se perdían al re-ejecutar | El `UPDATE` usaba `COALESCE(abstract, ?)` y nunca reemplazaba | Gana el abstract más largo (`CASE WHEN length(?) > length(abstract)`) | Re-ejecución de 3I: 0 nuevos, 123 actualizados, sin acortar |
| `provenance_log` crecía en cada re-ejecución | La deduplicación incluía `action`, que cambia entre insert y update | Deduplicar solo por entidad, id y detalle | Segunda pasada no duplica trazas |
| Crossref devolvía resultados irrelevantes | `select` y `cursor` hacen que se ignore `query.bibliographic` | Usar `rows`/`offset` sin `select` | La consulta vuelve a ordenar por relevancia |
| Filtro Crossref por tipo no aplicaba | `type:a,type:b` en un solo parámetro | Repetir `type:` por cada valor | Conteos coherentes con el tipo |
| Enriquecimiento OpenAlex fallaba a mitad | Lotes de 40 DOI y luego 429 | Pre-filtrar por regex antes de enriquecer y bajar el lote; en 3I se desactivó | 3I completo sin depender de OpenAlex |
| `published_at` con longitud 7 (`2025-12`) | Crossref devuelve fecha parcial | Se acepta: `date()` de SQLite la interpreta como `2025-12-01` | 1 registro con formato parcial, 208 con fecha completa |

Error de procedimiento: `publication_class` no vive en `publications` sino en
`object_publications`. Confirmar el esquema antes de escribir evita migraciones
innecesarias.

## 3. Errores de criterio (falsos positivos)

- "Borisov" es un apellido común. La búsqueda inicial traía literatura sobre
  Andrei Borisov, Boyko Borisov, matemáticas (conjetura Borisov-Nuer), etc.
  Se exigió designación `2I/` o `2019 Q4`, con respaldo por título que combine
  "borisov" con "comet/interstellar/hyperbolic" o "interstellar comet/object".
  Se perdieron 4 notas de prensa, pero desaparecieron ~50 homónimos.
- "3I" es ambiguo: microscopía 3I-SIM, cristales `(NbSe4)3I`, subtipo HEV 3i,
  la revista "3i: intellect, idea, innovation". Se exige `3I/ATLAS`,
  `2025 N1` o "3I" cerca (≤ 6000 caracteres) de "interstellar/comet/hyperbolic".
  Pasaron 219 de 228 candidatos plausibles; se quitaron 9 falsos positivos.
- Se descartan repositorios genéricos (Zenodo `10.5281/`, EarthArXiv, blogs).
  En 3I se descartaron 24 registros por fuente y 12 por falta de abstract.
- La ventana empieza en la designación I, no en la confirmación. En 1I eso deja
  fuera el pico de octubre-noviembre de 2017; es una decisión de alcance, no un
  error, y explica que 1I tenga menos papers que 3I.

## 4. Rutas viables cuando un filtro bloquea

OpenAlex:

- El presupuesto diario afecta a `search`, `title.search`,
  `title_and_abstract.search` y `default.search`. Devuelve `429` con
  `Retry-After` de horas.
- Los filtros por `doi:` y por fecha siguen funcionando, incluso con OR
  (`doi:a|b|c`). Eso permite enriquecer registros ya descubiertos sin gastar
  presupuesto de búsqueda.
- Una consulta mínima sin filtros (`per-page=1`) sirve para comprobar si el
  bloqueo ya expiró.

Crossref:

- Ordena por relevancia; los aciertos se agotan después de ~600-800 resultados.
  Paginar más allá no aporta y cuesta tiempo.
- `select` y `cursor` desactivan la búsqueda bibliográfica (devuelven todo el
  corpus). Usar `rows`/`offset` y dejar que la relevancia haga el trabajo.
- Los tipos válidos se repiten: `type:journal-article,type:posted-content,...`.
- Varias formulaciones del nombre rinden más que una sola. Para 3I:
  "3I/ATLAS" aportó casi todo; "C/2025 N1" solo 1 nuevo;
  "interstellar comet ATLAS 3I" aportó 124 nuevos relevantes.

arXiv:

- El buscador avanzado por HTML (`arxiv.org/search/advanced`) permite filtrar
  por rango de fechas de envío y muestra abstracts. Para 3I devolvió 99
  resultados en una página.
- El HTML anida `span.search-hit` dentro del abstract: hay que cortar por el
  enlace "Less", no por el primer `</span>`.
- arXiv no siempre trae DOI de revista; el DOI `10.48550/arxiv.*` se descarta
  como identificador final si existe la versión publicada.

Regla práctica: si OpenAlex bloquea, descubrir por arXiv + Crossref, pre-filtrar
por regex y enriquecer por DOI solo si hace falta. El campo `metodo` de
`config/metadata_scope.json` permite volver a la búsqueda directa sin tocar
código.

## 5. Tiempos y costo

- Pase completo (tres ventanas, 209 registros): aproximadamente 1 h 30 min.
  Es una medición manual; el colector ahora imprime la duración por ventana y
  la duración total para tener números exactos en la próxima corrida.
- El costo no lo dominan los 209 papers aceptados sino los candidatos
  descargados y las esperas entre páginas: 1I y 2I son una página cada una
  (100 y 155 candidatos), mientras 3I implicó ~3 100 candidatos descubiertos
  (99 de arXiv + tres consultas Crossref de 5 páginas) y 347 plausibles.
- Extrapolación: ~65 papers por objeto y año. Cubrir 8 años de 1I, 7 de 2I y 1
  de 3I ronda las 1 000 publicaciones, es decir, entre 7 y 8 veces el trabajo
  actual más el costo de paginación: más de 10 h.
- Recomendación operativa: correr por objeto (`--solo`), con `--cache-dir`, en
  un equipo que no se suspenda, y hacer dry-run antes de cada ventana.

## 6. Interrupciones y reanudación

Qué pasa si se cierra la tapa o se apaga el equipo:

- Cerrar la tapa normalmente suspende el proceso. Al reanudar, las conexiones
  HTTP abiertas suelen fallar; el colector reintenta hasta 8 veces con esperas
  de hasta 50 s, pero si se agotan, la ventana aborta con excepción.
- Apagar o reiniciar mata el proceso. No hay reanudación automática: al volver
  a ejecutar, el script empieza por la primera ventana.

Qué sobrevive:

- La base se confirma al final de cada ventana (`con.commit()`), así que las
  ventanas terminadas quedan cargadas.
- El cache por ventana (`--cache-dir`) se escribe al terminar el descubrimiento;
  permite repetir el filtrado y la carga sin volver a paginar.
- `provenance_log` conserva cada alta y actualización.

Qué se pierde:

- El descubrimiento en curso de la ventana actual (el cache se escribe al final,
  no por página).
- Los registros de la ventana actual si se interrumpe antes del `commit`.

Mitigaciones disponibles hoy: ejecutar una ventana por vez, conservar el cache y
volver a lanzar solo la ventana pendiente. Mejoras posibles para el pase
completo: cache por página, commit por registro y un archivo de checkpoint por
ventana.

## 7. Checklist para la próxima corrida

1. Respaldar `data/db/iso.db`.
2. Comprobar el estado de OpenAlex con una consulta mínima.
3. Por ventana: `--dry-run`, revisar descartes y luego carga real con
   `--cache-dir`.
4. Al cerrar: `--normalizar`, `backfill_abstracts.py --refrescar-cortos 200`,
   verificación de duplicados e integridad, y comparación por hash de las
   tablas científicas contra el respaldo.
5. Anotar duración por ventana y total que imprime el colector.
