# Auditoría integral de Fase 6

Auditoría generada: 2026-11-02T13:56:06.156809+00:00 (UTC).

## Resumen ejecutivo

Estado: **completed_with_findings**. Hallazgos: 2.

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

La presencia y nulidad de los campos clave se registra por capa en `REPORTE_AUDITORIA_FASE6.json`. Los valores nulos en indicadores son esperables cuando la fuente no aporta pisos, estrato o valor; no se interpretan como cero. Los nombres de campos de privacidad se revisan contra un patrón conservador, esto no sustituye validación jurídica del contenido.

## Metadatos, geometrías y linaje

Se inspeccionan conteos, CRS, extensiones, campos clave y nombres de campos sensibles. El pipeline reporta control de geometrías inválidas después de `fixgeometries`; esta revisión no prueba ausencia de solapes, vacíos topológicos entre polígonos ni ajuste a linderos de terreno.

ArcGIS usa 0 como valor de límite de escala sin restricción; se corrigió la representación documental para no presentarlo como escala 0. Fechas y licencias se conservan en `docs/METADATOS.md`, con los límites declarados por cada fuente.

## Rendimiento web

Peso total de archivos bajo `web/`: 1,813,774,836 bytes. PMTiles presentes: 0. Referencias del manifiesto: 0.

El informe separa el peso de los archivos estáticos del tiempo secuencial de respuesta local (si se solicitó con `--base-url`). Esa medida no equivale al tiempo de primera pintura del mapa: faltan el proveedor CDN, teselas de relieve, caché, red y dispositivo final. Si todavía no hay PMTiles, no se pueden reportar peso ni tiempos de tesela.

Los artefactos temporales PMTiles se generan en `data/processed/phase2/` y solo se mueven a `web/` al completarse; el validador rechaza temporales y referencias rotas.

## Accesibilidad

`python scripts/audit_web.py` comprueba `lang`, título, landmark principal, enlace para saltar al contenido, etiquetas de formularios y nombre accesible de botones, texto alternativo de imágenes, temporales web y contraste mínimo WCAG AA de los colores de texto de la paleta. Es una revisión estática, no una certificación WCAG ni prueba con tecnologías de asistencia.

## Hallazgos y acciones

- Building extrusions cannot use all selected thematic values because construcciones_3d.gpkg lacks attributes ['valor_ref_m2', 'estrato', 'indice_construccion']; the block layer carries these indicators.
- No completed PMTiles found in web/, tile weight/load-time audit is pending production outputs.

## Reproducibilidad y límites

Ejecutar `cmd /c scripts/run_audit_phase6.bat` después de finalizar Fase 2. Para medir la entrega HTTP del servidor local: `uv run python scripts/audit_web.py --base-url http://localhost:8000`. Las pruebas no reemplazan red de control GNSS/topográfica, inspección de licencias ni ensayo real de primera pintura en móvil.
