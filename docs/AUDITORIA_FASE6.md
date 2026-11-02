# Auditoría integral de Fase 6

Auditoría generada: 2026-11-02T01:40:40.509844+00:00 (UTC).

## Resumen ejecutivo

Estado: **completed_with_findings**. Hallazgos: 1.

## Exactitud posicional y CRS

La exactitud posicional externa **no es cuantificable** con los insumos disponibles: no se suministraron puntos de control independientes, coordenadas GNSS ni tolerancias de aceptación. Las comprobaciones de transformación inversa solo miden consistencia numérica del CRS, no error de levantamiento o de la fuente.

Se valida EPSG:9377 en capas de proceso, una envolvente razonable de Bogotá tras transformar a EPSG:4326, y el error de ida y vuelta en el centro de cada envolvente. GeoJSON/PMTiles se publican en EPSG:4326; el mapa proyecta a EPSG:3857.

| Capa | Entidades | CRS | EPSG:9377 | Envolvente Bogotá |
| --- | ---: | --- |:---:|:---:|
| `center_dem_buffer` | 1 | EPSG:9377 | Sí | Sí |
| `construccion` | 2,368,909 | EPSG:9377 | Sí | Sí |
| `construcciones_3d` | 2,368,909 | EPSG:9377 | Sí | Sí |
| `construcciones_centro` | 78,089 | EPSG:9377 | Sí | Sí |
| `corriente_agua` | 342 | EPSG:9377 | Sí | Sí |
| `cuerpo_agua` | 149 | EPSG:9377 | Sí | Sí |
| `estrato` | 43,247 | EPSG:9377 | Sí | Sí |
| `estructura_ecologica` | 656 | EPSG:9377 | Sí | Sí |
| `localidad` | 19 | EPSG:9377 | Sí | Sí |
| `lote` | 912,751 | EPSG:9377 | Sí | Sí |
| `malla_vial` | 134,725 | EPSG:9377 | Sí | Sí |
| `manzana` | 43,669 | EPSG:9377 | Sí | Sí |
| `manzanas_indicadores` | 43,669 | EPSG:9377 | Sí | Sí |
| `sector` | 1,138 | EPSG:9377 | Sí | Sí |
| `upl` | 32 | EPSG:9377 | Sí | Sí |
| `valor_referencia` | 41,483 | EPSG:9377 | Sí | Sí |

## Completitud y privacidad de atributos

La presencia y nulidad de los campos clave se registra por capa en `REPORTE_AUDITORIA_FASE6.json`. En `manzanas_indicadores` se contaron 43,669 entidades: `estrato` tiene 772 nulos (98.23% no nulo), `valor_ref_m2` 2,164 nulos (95.04% no nulo), y `MANCODIGO` 4 nulos (99.99% no nulo). En `construcciones_3d`, `altura_est_m` y `area_constr_m2` tienen 16,230 nulos cada uno (99.31% no nulo), mientras que `area_huella_m2` está completo. Los nulos no se interpretan como cero. No se detectaron nombres de campos sensibles en estas capas; esto no sustituye validación jurídica de valores.

## Metadatos, geometrías y linaje

Se inspeccionan conteos, CRS, extensiones, campos clave y nombres de campos sensibles. El pipeline reporta control de geometrías inválidas después de `fixgeometries`; esta revisión no prueba ausencia de solapes, vacíos topológicos entre polígonos ni ajuste a linderos de terreno.

ArcGIS usa 0 como valor de límite de escala sin restricción; se corrigió la representación documental para no presentarlo como escala 0. Fechas y licencias se conservan en `docs/METADATOS.md`, con los límites declarados por cada fuente.

## Rendimiento web

Peso total de archivos locales bajo `web/`: 71,158,075 bytes. Hay cinco PMTiles terminados, con un peso combinado de 69,226,308 bytes: vías 35,392,293; manzanas 29,707,007; estructura ecológica 2,428,096; cuerpos de agua 872,022; corrientes de agua 826,890 bytes. Durante la auditoría, el manifiesto local listó esos cinco paquetes y tres GeoJSON administrativos; luego se devolvió al estado vacío versionado para no dejar referencias a assets ignorados por Git. Estos archivos locales no están aprobados aún para redistribución.

La prueba secuencial HTTP local de siete recursos de la interfaz (HTML/CSS/JS/manifiesto) respondió 200 en todos: 71,871 bytes y 0.6201 s. No equivale al tiempo de primera pintura del mapa: no incluye peticiones CDN, lectura/consulta de PMTiles, teselas de relieve, caché, red externa ni dispositivo final. Los tamaños de PMTiles sí se midieron, pero no el tiempo real de carga de tiles.

La exportación `--export-only` finalizó con advertencias: no pudo mover el PMTiles de construcciones 3D por `WinError 32` en el temporal, y el PMTiles de lotes excede 95 MB, por lo que se guardó en `data/processed/pmtiles/lote.pmtiles` y no se incluyó en el manifiesto web. El validador rechaza temporales y referencias rotas.

## Accesibilidad

`python scripts/audit_web.py` comprueba `lang`, título, landmark principal, enlace para saltar al contenido, etiquetas de formularios y nombre accesible de botones, texto alternativo de imágenes, temporales web y contraste mínimo WCAG AA de los colores de texto de la paleta. Es una revisión estática, no una certificación WCAG ni prueba con tecnologías de asistencia.

## Hallazgos y acciones

- Building extrusions cannot use all selected thematic values because construcciones_3d.gpkg lacks attributes ['valor_ref_m2', 'estrato', 'indice_construccion']; the block layer carries these indicators.

## Reproducibilidad y límites

Reejecutar `cmd /c scripts/run_audit_phase6.bat` después de cambios GIS. Para repetir la muestra HTTP local, iniciar `python -m http.server 8000 --directory web` y correr `uv run python scripts/audit_web.py --base-url http://localhost:8000`. Las pruebas no reemplazan red de control GNSS/topográfica, inspección de licencias ni ensayo real de primera pintura en móvil. En esta sesión, el MCP de QGIS falló al consultar el proyecto y al añadir capas, por lo que no se comprobó la simbología en la ventana.
