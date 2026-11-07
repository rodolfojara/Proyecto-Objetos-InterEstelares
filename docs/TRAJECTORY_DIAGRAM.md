# Diagrama de trayectorias (1I, 2I, 3I) y ubicación aproximada

## Diagrama actual (trayectorias y posición aproximada)
![Trayectorias planas y posición aproximada actual de 1I, 2I y 3I](images/1i%202i%203i%20Trayectoria%20plana.png)

*Fuente de la imagen: `docs/images/1i 2i 3i Trayectoria plana.png` (agregada al repositorio). Es una representación referencial/esquemática de trayectorias y situación aproximada. Para posiciones precisas a una fecha usar efemérides JPL Horizons (y ver “Última observación / ubicación aproximada” en `reports/dashboard_latest.md`).*

## Estado actual de datos en la BD (limitaciones)
- **`orbital_elements`** (confianza alta, fuentes MPC MPEC): tenemos `e, q, i, epoch, e_hyperbolic_v_inf` para 1I/'Oumuamua, 2I/Borisov y 3I/ATLAS.
- **Faltan para una órbita 3D completa:** `Ω` (longitud del nodo ascendente), `ω` (argumento del perihelio) / `arg_peri`, `node`, anomalía/estado en una fecha, y efemérides. Sin esto, no se puede trazar con precisión la trayectoria orientada en el plano del sistema solar.
- **`observations`**: vacía → **no hay magnitud observada reciente ni posición/ubicación aproximada registrada** en BD. “Última observación/ubicación aproximada” queda pendiente de integrar efemérides.
- **`physical_params`**: placeholders → **tamaño estimado y magnitud absoluta (H) no consolidados** en BD.

> Conclusión: un diagrama *preciso* (posición a una fecha + trayectoria real) requiere obtener efemérides/orbitales completos desde JPL Horizons/MPC y luego graficar. Con los datos actuales solo es viable un **esquema comparativo** (q, e, i, dirección hiperbólica aproximada).

## Datos disponibles (BD)
| Objeto | Época | e | q (au) | i (°) | v∞ (km/s) | Fuente |
|---|---:|---:|---:|---:|---:|---|
| 1I/'Oumuamua | 2017-10-25 | 1.19951 | 0.255916 | 122.676 | 26.33 | MPC MPEC K17UI3 |
| 2I/Borisov | 2019-09-30 | 3.35648 | 2.00662 | 44.0525 | 32.3 | MPC MPEC K19RA6 |
| 3I/ATLAS | 2025-07-01 | 6.14 | 1.356 | 175.11 | 58.0 | MPC MPEC K25N12 |

## Opción A (recomendada): diagrama preciso con JPL Horizons + Python
**Herramientas:** Python 3, `matplotlib`, `numpy` (y opcional `astroquery` o `requests`).

1. Instalar dependencias (en tu entorno):
   ```bash
   pip install matplotlib numpy astroquery
   ```
2. Obtener efemérides/vectores desde **JPL Horizons** (https://ssd.jpl.nasa.gov/horizons/):
   - Objetos: `1I/'Oumuamua` (o id Horizons correspondiente), `C/2019 Q4 (Borisov)`, `3I/ATLAS`.
   - Ephemeris Type: `VECTORS` (heliocéntricos) o `OBSERVER` según necesidad.
   - Rango de fechas: p. ej. ±1-2 años alrededor del perihelio de cada objeto; incluir una fecha de “última observación” si la defines.
   - Center: `@sun` para sistema solar.
3. Graficar en 2D (plano eclíptico, X-Y) u 3D:
   - Órbitas planetarias (opcional, simplificadas) como referencia.
   - Trayectorias hiperbólicas de 1I/2I/3I desde vectores/estado.
   - Marcar perihelio (q) y la **posición en la fecha de última observación** (si obtuviste efeméride para esa fecha).
4. Guardar como `reports/figures/trajectories_1I_2I_3I.png` y enlazar desde el dashboard.

**Plantilla (esqueleto) con `astroquery`** — ajustar IDs/nombres según Horizons:
```python
# pip install astroquery matplotlib numpy
from astroquery.jplhorizons import Horizons
import matplotlib.pyplot as plt
import numpy as np

# Ejemplo de IDs/nombres: verificar en Horizons ('1I', '2I', 'C/2019 Q4', '3I')
targets = [("1I/'Oumuamua", '1I'), ('2I/Borisov', 'C/2019 Q4'), ('3I/ATLAS', '3I')]
fig = plt.figure(); ax = fig.add_subplot(111, projection='3d')
for label, tid in targets:
    obj = Horizons(id=tid, location='@sun', epochs={'start':'2017-01-01','stop':'2027-01-01','step':'5d'})
    vec = obj.vectors()
    x,y,z = np.array(vec['x'],float), np.array(vec['y'],float), np.array(vec['z'],float)
    ax.plot(x,y,z,label=label)
ax.scatter([0],[0],[0], s=80, label='Sol')
ax.set_xlabel('X (au)'); ax.set_ylabel('Y (au)'); ax.set_zlabel('Z (au)')
ax.legend(); plt.tight_layout(); plt.savefig('reports/figures/trajectories_1I_2I_3I.png', dpi=150)
```
> Nota: los identificadores/rangos deben validarse en Horizons; algunos objetos interestelares requieren el nombre exacto aceptado por el servicio.

## Opción B (rápida, visual): herramientas oficiales/interactivas
- **NASA/JPL Eyes on the Solar System** (https://eyes.nasa.gov/apps/solar-system/): visualización 3D; buscar cometas/objetos si están disponibles y capturar imagen.
- **JPL Orbit Viewer / Small-Body Database Lookup** (https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html): diagramas de órbita por objeto; útil para comparar y exportar/capturar.
- **TheSkyLive** (https://theskylive.com/): posiciones/trayectorias y efemérides.
Estas opciones son buenas para una imagen informativa rápida, pero la reproducibilidad depende de captura manual.

## Opción C (esquemática): prompt para IA generadora de imágenes
Si no se genera con código/datos de Horizons, usar una IA de imagen con un prompt **esquemático** (no como dato observacional preciso). Prompt sugerido:

> Create a clear, labeled educational infographic diagram of the inner/outer Solar System (top-down ecliptic view). Show the Sun at center and approximate orbits of Earth, Mars, Jupiter. Overlay three hyperbolic interstellar object trajectories for comparison:
> 1) 1I/'Oumuamua — perihelion q≈0.256 au (inside Mercury's orbit region), high inclination (~123° retrograde-like), v∞≈26 km/s; passed perihelion 2017, now leaving the Solar System.
> 2) 2I/Borisov — q≈2.007 au (near Mars/Jupiter gap), inclination ~44°, eccentricity e≈3.36 (strongly hyperbolic), v∞≈32 km/s; perihelion 2019.
> 3) 3I/ATLAS — q≈1.356 au, very high inclination (~175°, nearly retrograde), very high eccentricity e≈6.14, v∞≈58 km/s; perihelion 2025.
> Mark perihelion points and direction arrows. Add a legend and note: “Schematic comparison (not to scale for all elements; orientation simplified). For precise positions use JPL Horizons ephemerides.” Style: clean scientific infographic, dark background, readable labels.

Guarda el resultado en `reports/figures/trajectories_1I_2I_3I.png` y referencia la imagen desde el dashboard/README.

## Qué falta integrar para “ubicación aproximada en últimas observaciones”
1. Ingerir efemérides (JPL Horizons `OBSERVER`/`VECTORS`) en `observations` o tabla de efemérides con fecha, RA/Dec, distancia, magnitud (si aplica), fuente.
2. Completar `orbital_elements` con `arg_peri/node/omega` y epoch consistentes.
3. Regenerar dashboard (`generate_dashboard.py`) y, si aplica, el diagrama con la fecha de última observación marcada.

## Enlace desde el dashboard
Cuando exista la imagen, añadir en `reports/dashboard_latest.md` (o regenerar con soporte de imagen):  
`![Trayectorias comparadas 1I/2I/3I](figures/trajectories_1I_2I_3I.png)`
