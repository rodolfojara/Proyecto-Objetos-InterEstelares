# Cronología de identificación de objetos interestelares

Este documento fija las fechas que marcan cuándo un objeto pasa de ser "un objeto observado" a "un objeto interestelar", y define la regla para separar la literatura previa de la posterior a esa identificación.

Implementación: tabla `object_identification`, vista `v_publication_epoch` y datos en `data/identification_timeline.json`.

---

## 1. Por qué no alcanza una sola fecha

"Primera identificación" mezcla cinco momentos distintos, y cada uno sirve para algo diferente:

| Fecha | Qué marca | Para qué sirve |
| :-- | :-- | :-- |
| `earliest_observation_date` | Imagen o astrometría más antigua conocida, aunque nadie la haya reconocido como objeto nuevo | Detectar precovery y archivo previo |
| `discovery_date` | Se reconoce y reporta como objeto nuevo | Fecha de descubrimiento (coincide con `objects.discovery_date`) |
| `announcement_date` | Primera publicación oficial (MPEC/CBET/IAU) | Saber desde cuándo el objeto es público |
| `iso_confirmation_date` | La órbita hiperbólica u origen interestelar queda establecido | **Corte real para clasificar papers** |
| `iso_designation_date` | Se asigna la designación 1I, 2I, 3I | "Desde cuándo se le llama interestelar" |

La distinción importante: un paper anterior a `iso_confirmation_date` no podía atribuirle origen interestelar, porque el dato no existía. Un paper posterior sí. Por eso el corte de clasificación es la confirmación, no la designación formal.

---

## 2. Fechas registradas

| Objeto | Detección más antigua | Descubrimiento | Anuncio | Confirmación interestelar | Designación I |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **1I/'Oumuamua** | 2017-10-18 | 2017-10-19 | 2017-10-25 | 2017-10-25 | 2017-11-06 |
| **2I/Borisov** | 2019-08-30 | 2019-08-30 | 2019-09-11 | 2019-09-11 | 2019-09-24 |
| **3I/ATLAS** | 2025-06-14 | 2025-07-01 | 2025-07-02 | 2025-07-02 | 2025-07-02 |

### 1I/'Oumuamua
- Detección: 2017 Oct 18.47 UT, Pan-STARRS 1 (F51). Reconocimiento y reporte por Robert Weryk el 2017-10-19.
- MPEC 2017-U181 (2017-10-25 03:53 UT): publica e ≈ 1.2 y advierte que "puede ser el primer caso claro de cometa interestelar".
- MPEC 2017-U183 (2017-10-25 22:22 UT): cambia el prefijo de `C/` a `A/` por aspecto estelar.
- Designación `1I` y nombre `'Oumuamua`: boletín del MPC anunciado el 2017-11-06, reportado por prensa el 2017-11-07. Confianza 4: falta confirmar contra el boletín original.

### 2I/Borisov
- Gennady Borisov (L51, MARGO) reporta el objeto como candidato a cometa el 2019-08-30; primera imagen 2019 Aug 30.04 UT.
- MPEC 2019-R106 (2019-09-11 20:40 UT): elementos hiperbólicos (e = 3.08) e indicio de origen interestelar.
- Designación formal `2I/Borisov`: 2019-09-24, 25 días después del descubrimiento.

### 3I/ATLAS
- ATLAS Chile (W68) lo detecta en cuatro imágenes de 30 s del 2025-07-01; hay precovery de ZTF (I41) desde el 2025-06-14.
- MPEC 2025-N12 (2025-07-02 21:31 UT): ya se publica como `3I/ATLAS = C/2025 N1 (ATLAS)`, e ≈ 6.3.
- Anuncio, confirmación y designación coinciden en fecha: 2025-07-02.

---

## 3. Clasificación de papers

### Épocas (calculadas por fecha)

La vista `v_publication_epoch` asigna cada publicación vinculada a un objeto a una de estas épocas:

| Época | Condición | Significado |
| :-- | :-- | :-- |
| `archivo_previo` | anterior a `earliest_observation_date` | Archivo/precovery: el objeto estaba en los datos pero nadie lo conocía |
| `observado_sin_identificar` | entre detección/descubrimiento y `iso_confirmation_date` | Lo vieron, pero no como objeto interestelar |
| `literatura_interestelar` | posterior a `iso_confirmation_date` | Lo tratan como objeto interestelar |
| `desconocido` | sin `published_at` | Falta fecha |

### Clase editorial (juicio de contenido)

La fecha sola no alcanza: un paper posterior a la confirmación puede mencionar el objeto de pasada sin estudiarlo. Para eso está `object_publications.publication_class`:

| Valor | Uso |
| :-- | :-- |
| `identificacion` | El paper establece o anuncia la naturaleza interestelar |
| `confirmacion` | Confirma independientemente la órbita hiperbólica |
| `caracterizacion` | Estudio de seguimiento que asume el origen interestelar |
| `observacion_previa` | Reporta observaciones de archivo sin identificarlo |
| `mencion` | Mención de pasada |

Regla de uso: la época se calcula, la clase se asigna con lectura del paper. Nunca se sobrescribe una clase ya asignada sin registrar el cambio en `provenance_log`.

---

## 4. Consultas

Papers por objeto y época:

```sql
SELECT designation, epoch, COUNT(*) AS papers
FROM v_publication_epoch
GROUP BY designation, epoch
ORDER BY designation, epoch;
```

Papers que observaron sin identificar:

```sql
SELECT designation, title, published_at
FROM v_publication_epoch
WHERE epoch = 'observado_sin_identificar'
ORDER BY designation, published_at;
```

Conteo por clase editorial:

```sql
SELECT o.designation, op.publication_class, COUNT(*) AS n
FROM object_publications op
JOIN objects o ON o.id = op.object_id
GROUP BY o.designation, op.publication_class;
```

---

## 5. Cómo agregar un objeto nuevo

1. Insertar el objeto en `objects` (o en `data/objects.json` y ejecutar `ingest_init.py`).
2. Agregar su bloque en `data/identification_timeline.json` con las cinco fechas y la referencia primaria (MPEC/CBET/IAU).
3. Ejecutar `python apply_patch_identificacion.py` (idempotente).
4. Registrar la fuente exacta en `source_url` y el grado de certeza en `confidence`.

Si no hay precovery conocido, `earliest_observation_date` queda igual a `discovery_date`. Si la confirmación y la designación coinciden, se repite la fecha: es correcto, no un error.

---

## 6. Advertencias

- **Corrección aplicada:** `data/objects.json` citaba `MPEC 2017-U183` como reporte de descubrimiento de 1I/'Oumuamua. Ese MPEC es el cambio de `C/` a `A/`. El reporte de descubrimiento es `MPEC 2017-U181`.
- **`1I` con confianza 4:** la fecha 2017-11-06 proviene del boletín del MPC citado por prensa, no de una copia directa del boletín. Validar en Fase 3.
- **Precovery no es descubrimiento:** 3I/ATLAS tiene imágenes desde 2025-06-14, pero el descubrimiento es 2025-07-01. Contar papers desde la fecha equivocada infla la literatura previa.
- **Duplicados arXiv/DOI:** al contar papers, deduplicar por publicación, no por identificador. Ver Fase 3.
