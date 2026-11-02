# Instrucciones del proyecto

## Producto principal (visión vigente)

Maqueta 3D de terreno de Bogotá: relieve real del DEM Copernicus GLO-30 más imagen satelital Sentinel-2 L2A sin nubes, con sobrevuelo, publicada como visor interactivo three.js en GitHub Pages mediante GitHub Actions.

Pipeline obligatorio: QGIS (procesamiento y texturas) → Blender (malla, materiales, cámara, render) → web (visor three.js). El visor MapLibre existente pasa a ser secundario y se sirve como `web/explorador.html`.

La rama de trabajo de esta visión es `feat/terreno-3d`, creada desde la rama más reciente publicada en el remoto. Cada fase se cierra con commit semántico y capturas en `docs/capturas/`.

## Propósito y estructura

Proyecto académico de gemelo digital 3D de Bogotá D.C. Publicar únicamente `web/`. Mantener originales en `data/raw/` y productos intermedios en `data/processed/`, ambos ignorados por Git.

## Geodesia y datos

- CRS de procesamiento: MAGNA-SIRGAS / Origen-Nacional, EPSG:9377.
- Documentar CRS de origen y transformaciones. GeoJSON de publicación: EPSG:4326; mapa web: EPSG:3857.
- No asumir el CRS. Inspeccionar y validar cada fuente antes de reproyectar.
- Documentar por capa fuente, fecha de corte, licencia, CRS, escala, campos, cantidad, linaje y restricciones en `docs/METADATOS.md`.
- No descargar ni publicar propietarios, documentos ni otra información personal. Mantener datos catastrales sin atributos personales y revisar licencia antes de distribuir.
- Procesamientos pesados mediante scripts reproducibles, no acciones MCP en vivo. Validar geometrías antes de publicar.

## Reproducibilidad y Git

- Usar `uv` para gestionar Python y dependencias.
- Registrar las fases en `docs/BITACORA.md` y documentar descargas manuales en `docs/DESCARGAS_MANUALES.md`.
- Trabajar en ramas de funcionalidades, commits semánticos y nunca hacer push directo a `main`.
- Ejecutar pruebas/validaciones disponibles antes de integrar.
