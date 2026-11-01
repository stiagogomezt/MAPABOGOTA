# Bitácora del proyecto

## 2026-10-31 | Fase 0: estructura y visor inicial

- Se verificó el repositorio remoto `stiagogomezt/MAPABOGOTA`, inicialmente vacío salvo el README.
- Se creó la rama de trabajo `feat/bogota-digital-twin`.
- Se estableció estructura reproducible, exclusión de datos locales y despliegue de `web/` mediante GitHub Actions.
- Se creó visor base con estilo cartográfico externo y terreno global Terrarium. Las capas oficiales aún no están integradas.
- CRS objetivo de procesamiento: EPSG:9377. Para publicación GeoJSON: EPSG:4326. El mapa web representa en EPSG:3857.
- Se agregó `scripts/run_all.py`; su reporte confirma el estado del andamiaje, no una validación de capas catastrales.
- No disponibles en este entorno: `qgis_process` y Blender. Se aplaza procesamiento pesado hasta contar con esos programas y las fuentes oficiales.
- Pendiente: conseguir datos oficiales con licencias verificables, generar capas/tiles, aplicar validación topológica y completar el modelo 3D urbano.

## 2026-11-01 | Fase 1: inicialización y adquisición de fuentes

- Se confirmó que la carpeta ya contenía un repositorio clonado del remoto, por lo que se conservó la rama `feat/bogota-digital-twin` y el historial existente, sin reinicializar ni reemplazar `.git`.
- Se creó `AGENTS.md` con reglas de CRS, privacidad, trazabilidad, Git y publicación.
- Se inicializó el proyecto Python con `uv`, Python >=3.10 y dependencia de solicitudes HTTP.
- Se implementó `scripts/acquire_sources.py`: consulta el ArcGIS REST oficial del Mapa de Referencia, limita las entidades a la geometría oficial de suelo urbano y descarga por lotes. Excluye campos personales/propietarios y evita la tabla Predio.
- El inventario se genera con campos, CRS, conteos, fecha de descarga y fechas de edición si el servicio las entrega. GeoJSON descargado en EPSG:4326; reproyección posterior a EPSG:9377 queda fuera de esta fase de adquisición.
- Se automatizó la obtención de GeoPackages para estratificación, estructura ecológica y valor de referencia desde CKAN. Cada fuente queda documentada, incluso ante fallos.
- Pendiente de ejecución completa: medir disponibilidad y tamaño final de cada fuente; el servicio informa millones de geometrías para todo el Distrito, el script filtra suelo urbano antes de recuperar entidades.

## 2026-11-01 | Fase 2: pipeline PyQGIS

- Se creó `scripts/process_phase2.py` para reproyectar desde el CRS declarado de cada fuente a EPSG:9377, recortar con suelo urbano oficial, reparar geometrías y retirar duplicados.
- Se implementaron campos derivados: altura = pisos × 3 m; área de huella, área construida estimada, índice de ocupación e índice de construcción por manzana.
- Los atributos jerárquicos se relacionan por código lote → manzana → sector; localidad/UPL y capas socioeconómicas se relacionan por código de manzana o punto interior según disponibilidad de claves.
- La estratificación y la estructura ecológica entregan CRS CarMAGBOG (GeoPackage SRS 300001, definición WKT conservada); el valor de referencia está en EPSG:4326. Se reproyectan a EPSG:9377 por QGIS, no se reasignan etiquetas.
- Se comprobó que QGIS 4.2.3 y GDAL 3.13.3 están instalados, `qgis_process` funciona y el driver PMTiles está disponible.
- La ejecución de diagnóstico se detuvo intencionalmente: faltan GeoJSON completos de lotes, construcciones, vías y agua, porque la adquisición anterior falló. No se generaron indicadores, PMTiles, QGZ ni PDF válidos aún.

## 2026-11-01 | Fase 3: pipeline Blender

- Se creó `blender/build_scene.py` y `scripts/run_phase3.bat`: escena local EPSG:9377, DEM Copernicus GLO-30, extrusión de edificios, materiales por altura, iluminación de atardecer, vuelo de 40 s y exportación GLB con Draco.
- La fase 2 prepara sus entradas Blender, recorta el DEM a 5 km alrededor de La Candelaria, Santa Fe y Chapinero, y transforma los puntos de ruta desde EPSG:4326 con QGIS.
- Blender 5.2.3 está instalado y el exportador glTF declara soporte Draco. No se renderizó aún: depende de las salidas completas de fase 2.
- El catálogo de herramientas MCP disponible no expone herramientas Blender; la revisión final se hará con inspección de la escena por `blender -b` y controles de archivo. El MCP de QGIS se reservará para validar el proyecto QGIS generado.

## 2026-11-01 | Fase 4: visor web estático

- Se rediseñó `web/` como sitio sin build step con MapLibre GL JS 5.6.1, PMTiles 4.3.0 y three.js 0.180.0, todos con versión CDN fija.
- Se implementaron panel responsive de capas, leyenda por tema, exageración de terreno, controles cartográficos, coordenadas, búsqueda, popups con atributos seleccionados y recorrido pausables por 20 localidades.
- Se añadió pestaña de video/modelo GLB, lector WebGL con OrbitControls y página `web/metodologia.html` con procedencia, CRS, limitaciones y autoría.
- `web/manifest.json` evita solicitar paquetes que todavía no han sido generados. PyQGIS y Blender actualizarán el manifiesto al completar sus salidas.
- Verificación local con `python -m http.server 8000 --directory web`: todos los HTML/CSS/JS/SVG respondieron 200; Chrome headless registró cero errores de consola y cero respuestas HTTP fallidas. La prueba responsive a 390×844 px no mostró desbordamiento horizontal.
- La prueba de datos locales se realizó con el manifiesto vacío, por lo que todavía no valida la carga de PMTiles, video o GLB generados por las fases anteriores.

## 2026-11-01 | Fase 6: auditoría técnica y accesibilidad

- Alcance evaluado: posición/CRS, campos y privacidad, inventario de metadatos, tamaño/entrega web, accesibilidad y publicación.
- Exactitud posicional externa queda **no evaluada**: no hay puntos de control GNSS/topográficos independientes ni una tolerancia de aceptación. La consistencia de reproyección/retorno no se interpretará como exactitud de los datos.
- Se corrigió la documentación de escalas ArcGIS: el valor 0 es el centinela de límite abierto, no una escala 0. La Fase 2 registra `CUSTOM:SRS_ID=300001` para las capas CarMAGBOG y transforma desde el WKT declarado.
- Se endureció la exportación GeoJSON para fallar si faltan atributos solicitados, evitando que el escritor omita campos silenciosamente.
- El primer muestreo local detectó archivos temporales voluminosos del driver PMTiles dentro de `web/` (incluido un temporal >95 MB) y un GeoJSON de indicadores redundante de ~24 MB. Se cambió la exportación para crear PMTiles en `data/processed/phase2/` y moverlos a `web/` solo al finalizar; se retiró el GeoJSON redundante del conjunto web. El validador web/CI rechaza temporales, referencias rotas y archivos sobre el umbral.
- Los GeoJSON/PMTiles derivados y medios se excluyeron de Git por defecto: las fuentes ArcGIS aún requieren confirmación de términos de redistribución y revisión final de privacidad/tamaños. La publicación requiere agregar explícitamente solo productos aprobados y referenciarlos en el manifiesto.
- Se añadió `cmd /c scripts/run_phase2.bat --export-only` para regenerar GeoJSON/PMTiles desde GeoPackages ya completos, sin repetir cálculo de indicadores, recortes o Blender.
- Accesibilidad: se añadieron enlaces para saltar al contenido, foco visible, región de estado anunciable, instrucciones del mapa y texto accesible para el control de exageración. Se ajustaron tonos de texto de bajo contraste. La revisión estática de paleta reportó contraste mínimo 6.17:1 en los colores de texto muestreados sobre panel oscuro.
- Se añadieron `scripts/audit_web.py`, pruebas estáticas y `scripts/audit_phase6.py`/`run_audit_phase6.bat` para capturar tamaño web, enlaces del manifiesto, controles accesibles, contraste, CRS/cobertura y nulidad de atributos clave. El informe geoespacial debe ejecutarse cuando termine Fase 2, sin archivos SQLite journal activos.
- Se detectó una limitación de completitud temática: las capas de manzana llevan valor/estrato/índice, pero la tabla de construcciones no necesariamente incluye esos campos. Se explicitó en el visor; el informe auditará cuáles están presentes. Asociar indicadores por lote/manzana a cada edificio requiere una derivación adicional y validación de join antes de afirmar que los cuatro temas colorean las extrusiones.
- Medición HTTP preliminar en localhost: 50,702 bytes para HTML/CSS/JS/manifiesto y 0.1504 s de solicitudes secuenciales. No incluye CDN, teselas de relieve, primera pintura, caché ni un dispositivo/red móvil; los PMTiles terminados aún no estaban disponibles para medir.
- Estado de este registro: auditoría parcialmente automatizada; exactitud externa, métricas de teselas, carga del mapa con datos reales y accesibilidad con lector de pantalla permanecen como limitaciones explícitas.
