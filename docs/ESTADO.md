# Estado del proyecto

Última actualización: 2026-11-01. Rama de trabajo: `feat/bogota-digital-twin`. Las ejecuciones de exportación/auditoría y el servidor HTTP local terminaron; no quedan shells de trabajo activos. QGIS y su MCP permanecen abiertos, pero las llamadas MCP fallan.

## Fases y situación

- Fase 0, estructura del repositorio y visor inicial: completada.
- Fase 1, adquisición/inventario de fuentes: scripts y metadatos implementados. Los insumos originales están en `data/raw/` y se excluyen de Git.
- Fase 2, procesamiento geoespacial: GeoPackages procesados disponibles en `data/processed/phase2/`, CRS EPSG:9377. `--export-only` terminó `completed-with-warnings`: produjo cinco PMTiles en `web/descargas/pmtiles/` y tres GeoJSON administrativos; la exportación de `construcciones_3d` falló por `WinError 32` en un temporal PMTiles y el PMTiles de lotes supera 95 MB, por lo que quedó en `data/processed/pmtiles/lote.pmtiles`. El error inicial de reemplazo de GeoJSON se corrigió liberando capas OGR antes del rename.
- Fase 3, pipeline Blender: `blender/build_scene.py` y `scripts/run_phase3.bat` implementados. No hay conexión MCP de Blender y el render/GLB no se han verificado en esta sesión. La escena depende de las salidas de Fase 2.
- Fase 4, sitio web: visor y página de metodología implementados en `web/`. Los datos derivados están ignorados por Git hasta validar licencia, privacidad y tamaño.
- Fase 5: no hay una entrada o entregable de fase 5 identificado en la bitácora actual.
- Fase 6, auditoría: ejecutada sobre 16 GeoPackages; todos reportan EPSG:9377 y envolventes plausibles para Bogotá. Hallazgo temático: `construcciones_3d.gpkg` no lleva `valor_ref_m2`, `estrato` ni `indice_construccion`. Exactitud posicional externa continúa sin evaluar por falta de controles independientes.

## Archivos y productos generados

- Adquisición y procesamiento: `scripts/acquire_sources.py`, `scripts/process_phase2.py`, `scripts/run_phase2.bat`.
- Datos originales excluidos de Git: `data/raw/`.
- GeoPackages finales/intermedios: `data/processed/phase2/`. Entre los productos finales están `localidad.gpkg`, `upl.gpkg`, `sector.gpkg`, `manzana.gpkg`, `lote.gpkg`, `construccion.gpkg`, `construcciones_3d.gpkg`, `construcciones_centro.gpkg`, `manzanas_indicadores.gpkg`, `estrato.gpkg`, `valor_referencia.gpkg`, `malla_vial.gpkg`, `corriente_agua.gpkg`, `cuerpo_agua.gpkg` y `estructura_ecologica.gpkg`. Los archivos con prefijo `_` son intermedios del pipeline.
- Insumos de terreno/ruta: `data/processed/phase2/terrain_center_9377.tif`, `terrain_center_9377.asc`, `camera_path_9377.json` y `construcciones_centro_9377.geojson`.
- Informe de procesamiento local: `docs/REPORTE_FASE2.json`. Reportes auxiliares locales: `docs/REPORTE_FASE3.json` y `docs/REPORTE_VALIDACION.json`.
- Proyecto cartográfico: `data/processed/Proyecto_Bogota_Urbana.qgz`; PDF previsto en `web/descargas/Mapa_Bogota_Urbana.pdf`.
- Interfaz: `web/index.html`, `web/metodologia.html`, `web/assets/app.js`, `app.css`, `methodology.css` y `model-viewer.js`; inventario de publicación en `web/manifest.json`.
- Productos locales no versionados de exportación: `web/descargas/pmtiles/{corriente_agua,cuerpo_agua,estructura_ecologica,malla_vial,manzanas_indicadores}.pmtiles`, `web/descargas/{localidad,sector,upl}.geojson`, `web/descargas/Mapa_Bogota_Urbana.pdf` y `data/processed/pmtiles/lote.pmtiles`. Permanecen ignorados/no aprobados para redistribución.
- Auditoría: `scripts/audit_web.py`, `scripts/audit_phase6.py`, `scripts/run_audit_phase6.bat`, `docs/AUDITORIA_FASE6.md`.
- Informes: `docs/REPORTE_FASE2.json`, `docs/REPORTE_AUDITORIA_FASE6.json`, `docs/REPORTE_AUDITORIA_WEB_FASE6.json`; informes anteriores/históricos `docs/REPORTE_FASE3.json` y `docs/REPORTE_VALIDACION.json`.
- Blender: `blender/build_scene.py`; los medios `web/media/*.mp4` y `*.glb` solo se publican tras revisión y cumplimiento de tamaños.

## Problemas pendientes

- QGIS MCP está ejecutándose como proceso, pero las llamadas MCP de consulta (`get_qgis_info`, `get_project_info`, `get_layer_tree`) y de carga (`add_vector_layer`) devolvieron error. No se logró cargar las capas ni aplicar simbología en la ventana abierta.
- Blender no está conectado mediante MCP a esta sesión. El pipeline existe, pero no se confirmó un render ni un GLB final.
- La última exportación registró `WinError 32` al finalizar PMTiles de construcciones 3D. El PMTiles de lotes supera 95 MB. No quedaron temporales/journals ni procesos de exportación activos al cierre; sí hay que resolver esos dos productos antes de afirmar que la exportación PMTiles está completa.
- El muestreo web local pasó sin errores estáticos: 71,158,075 bytes en `web/`, cinco PMTiles, 8 referencias locales de manifiesto, solicitudes secuenciales de siete recursos HTML/CSS/JS/manifiesto con 71,871 bytes y 0.6201 s. No equivale a primera pintura, no incluye CDN, tiles ni red/dispositivo remoto.
- No hay puntos GNSS/topográficos independientes ni tolerancia para medir exactitud posicional. La prueba de ida/vuelta CRS no mide exactitud.
- La redistribución/licencia de los datos derivados no está aprobada. GeoJSON, PMTiles y multimedia están excluidos de Git por defecto; el manifiesto rastreado debe permanecer sin referencias locales no aprobadas.
- GitHub Pages no está habilitado/configurado para este repositorio: una ejecución anterior pasó las validaciones web/accesibilidad y falló en “Configure GitHub Pages”. `gh` no estaba autenticado y la URL pública respondía 404.
- El visor temático no asegura que los atributos agregados de manzana estén asociados a cada edificio. Falta validar el join edificio/lote/manzana antes de colorear extrusiones con esos indicadores.
- No existe una comprobación topológica de cobertura, solapes o vacíos entre polígonos colindantes, ni prueba de accesibilidad con lector de pantalla.

## Decisiones técnicas

- CRS de proceso EPSG:9377; GeoJSON/PMTiles de publicación EPSG:4326; representación del mapa web EPSG:3857. Se conserva y transforma desde el CRS declarado de cada fuente.
- No declarar exactitud posicional sin controles independientes. Una transformación inversa solo comprueba consistencia numérica.
- Mantener originales en `data/raw/` y productos intermedios/finales de GIS en `data/processed/`, ambos fuera de Git.
- Generar PMTiles en almacenamiento intermedio y moverlos a `web/` solo cuando estén completos. Usar `cmd /c scripts/run_phase2.bat --export-only` para exportar desde GeoPackages sin repetir el procesamiento.
- Mantener los productos web generados fuera de Git hasta revisar licencia, privacidad, integridad y tamaño. Publicar solo aprobados y referenciarlos en `web/manifest.json`.
- Trabajar en `feat/bogota-digital-twin`, con commits semánticos; no hacer push directo a `main`.

## Siguiente paso exacto

1. Reconectar el MCP de QGIS y comprobar `get_qgis_info` y `get_layer_tree`; cargar los productos finales (no los intermedios con `_`), aplicar simbología y encuadrar Bogotá en la ventana abierta.
2. Corregir/diagnosticar el bloqueo `WinError 32` de PMTiles para `construcciones_3d`; decidir si dividir `lote.pmtiles` (>95 MB) antes de publicar. No repetir el procesamiento geoespacial, usar `--export-only` tras el arreglo.
3. Mantener `web/manifest.json` vacío en Git mientras los productos derivados no tengan licencia/privacidad aprobadas; no agregar datos ignorados por Git al manifiesto versionado.
4. Blender sigue sin conexión MCP y sin render/GLB verificado; conectar o validar su ejecución local como tarea separada.
5. Confirmar configuración de GitHub Pages y validar la URL pública tras un despliegue exitoso.
