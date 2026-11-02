# Estado del proyecto

Rama: `feat/terreno-3d`. Visión: gemelo digital 3D de Bogotá con MDT oficial, publicado en GitHub Pages.

## Fase A - MDT

- Área de trabajo EPSG:9377: xmin 4850000, ymin 2040000, xmax 4905000, ymax 2105000 (55 x 65 km).
- MDT oficial: servicio UAECD `imagenes/ModeloDigitalTerreno2014` vía WCS 1.0.0 a 5 m (EPSG:3857), remuestreado y reproyectado a EPSG:9377. Cache en `data/raw/mdt/`.
- nDSM oficial: servicio `topografia/nDSM` vía WCS 1.0.0 a 5 m (EPSG:3116), reproyectado a EPSG:9377.
- Relleno Copernicus GLO-30 (Microsoft Planetary Computer) para cerros/sabana. Diferencia media Copernicus - MDT: 3.289 m, desviación 3.956 m (20.084.607 px de traslape). Corrección aplicada. Transición suave de 300 m.
- MDT fusionado: `data/processed/terrain/mdt_fused_9377_5m.tif`, 11000 x 13000 px a 5 m, rango 1295.2 - 3817.9 m.
- Heightmap 16 bits: `heightmap_16bit.png` (11000 x 13000). Georreferenciación en `georef.json`.
- Volumetría: altura de edificaciones = mediana del nDSM dentro del polígono; fallback pisos x 3 m. Muestra en `data/processed/terrain/volumetria_sample.csv`.

## Fase B - Imagen y texturas

- Compuesto Sentinel-2 L2A (mediana dic-mar, máscara SCL) en `sentinel2_rgb_9377.tif` y `texture_satellite_*.jpg`.
- Texturas temáticas en `data/processed/terrain/`: satelital, localidades, valor/estrato, relieve, pendientes (8192 y 4096 px).

## Fase C - Blender

- Malla de terreno desde heightmap, exageración vertical 1.5x. GLB con Draco: `data/processed/terrain/terrain.glb` (9.7 MB).
- Trayectoria de cámara: `data/processed/terrain/camera_path.json`.
- Render Eevee 1080p: `web/media/bogota_flyover.mp4` (1.5 MB), póster `web/media/poster.jpg`.

## Fase D - Visor web three.js

- `web/index.html`: visor three.js con selector de textura, sobrevuelo, créditos.
- `web/explorador.html`: visor MapLibre secundario.
- Assets en `web/terrain/`.

## Pruebas

- `python -m unittest discover -s tests -v`: 5 pruebas, OK.
- `python scripts/audit_web.py`: sin errores.
- `cmd /c scripts/run_audit_phase6.bat`: completado, reporte en `docs/AUDITORIA_FASE6.md`.

## Tabla de archivos de web/

| Archivo | Bytes |
|---|---:|
| web/terrain/terrain.glb | 9701872 |
| web/terrain/texture_satellite_8192.jpg | 23985610 |
| web/terrain/texture_localidades_8192.jpg | 24296763 |
| web/terrain/texture_valor_8192.jpg | 23708365 |
| web/terrain/texture_slope_8192.jpg | 21177383 |
| web/terrain/texture_relief_8192.jpg | 6499409 |
| web/terrain/texture_satellite_4096.jpg | 8679273 |
| web/terrain/texture_localidades_4096.jpg | 8794644 |
| web/terrain/texture_valor_4096.jpg | 8500825 |
| web/terrain/texture_slope_4096.jpg | 6966584 |
| web/terrain/texture_relief_4096.jpg | 2267893 |
| web/media/bogota_flyover.mp4 | 1522687 |
| web/media/poster.jpg | 33267 |
| web/assets/app.js | 29431 |
| web/index.html | (three.js viewer) |
| web/explorador.html | (MapLibre viewer) |

## Pendientes

- Publicación: merge a main, push, activar Pages en modo workflow, verificar URL.
- Validación visual con Playwright (capturas en docs/capturas/).
EOF