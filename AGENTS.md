# Instrucciones del proyecto

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
