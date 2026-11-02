# Descargas manuales pendientes

La descarga automatizada se implementa en `scripts/acquire_sources.py`. Ejecutar `uv sync` y luego `uv run python scripts/acquire_sources.py`. El script consulta ArcGIS REST y CKAN; si una fuente falla por disponibilidad o licencia, deja constancia en `docs/METADATOS.md`. No se sustituyen datos catastrales con datos simulados. Los originales se guardan en `data/raw/`, directorio excluido de Git.

## Datos oficiales Bogotá

1. En el portal Datos Abiertos Bogotá (`https://datosabiertos.bogota.gov.co/`) y el catálogo IDECA (`https://www.ideca.gov.co/`), buscar y descargar, priorizando servicios oficiales: localidades, UPL vigentes (y UPZ solo si se requiere histórico), sectores catastrales, manzanas, lotes, construcciones/número de pisos, valor de referencia del terreno, estratificación, malla vial, cuerpos de agua y estructura ecológica.
2. Para cada conjunto, verificar fecha de corte, licencia, CRS declarado, campos personales y restricciones. No publicar nombres, documentos, propietarios ni atributos que permitan identificar personas. Omitirlos del proceso, no solo de la interfaz.
3. Conservar el original sin modificar en `data/raw/`; reproyectar copias de trabajo a EPSG:9377 en `data/processed/`. Documentar explícitamente datum, transformación y unidades. Para entrega GeoJSON transformar a EPSG:4326; servir teselas web en EPSG:3857.

## Fallback y terreno

- Si no existe una capa oficial utilizable, descargar edificios/vías desde OpenStreetMap mediante Overpass u OSMnx, respetando la licencia ODbL, límites de consulta y atribución. Marcar estas capas como OSM, nunca como catastro oficial.
- La fase 2 descarga automáticamente la tesela Copernicus DEM GLO-30 `N04_00_W075_00` desde el bucket público AWS y la guarda como `data/raw/copernicus_dem_glo30_n04_w075.tif`. Si la descarga automática está bloqueada, descarga el objeto desde la URL del inventario y guárdalo con ese nombre exacto. Es un DSM de resolución nominal 30 m, no bare-earth; conserva el GeoTIFF original sin modificar. La fase 2 lo recorta, reproyecta y remuestrea a 30 m en EPSG:9377.
- Para el visor inicial se consumen teselas Terrarium públicas directamente. No se empaquetan ni redistribuyen; disponibilidad y condiciones del servicio pueden cambiar.

## Revisión antes de publicar

Ejecutar `python scripts/run_all.py`. Cuando existan vectores, añadir al flujo reproducible validación de geometrías inválidas, vacías, duplicadas y auto-intersecciones, y escribir resultados por capa en `docs/`. Para volúmenes grandes, generar PMTiles o dividir por localidad y comprobar que cada artefacto versionado sea menor de 95 MB. Mantener datos fuente/procesados fuera de Git.

## Fuentes consultadas en esta fase

- Mapa de Referencia Catastro/IDECA, ArcGIS REST, capas de localidades, UPL, sectores, manzanas, lotes, construcciones, vías y agua. La máscara urbana se deriva de la capa Suelo con `SUECSUELO=1`.
- Catálogo Datos Abiertos Bogotá (CKAN), recurso GeoPackage actual de Estratificación Manzana Bogotá D.C.
- Catálogo Datos Abiertos Bogotá (CKAN), recurso GeoPackage actual de Estructura Ecológica Principal POT Bogotá D.C.
- Catálogo Datos Abiertos Bogotá (CKAN), recurso GeoPackage actual de Mediana del valor comercial por metro cuadrado de terreno por manzana.
- Relieve local Copernicus DEM GLO-30 o ALOS no se descarga en esta fase. La interfaz usa AWS Terrain Tiles en vivo como referencia visual, sujeto a condiciones del servicio. No representa una descarga/mosaico local validado.

URLs de referencia:

- https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/Mapa_Referencia/Mapa_Referencia/MapServer
- https://datosabiertos.bogota.gov.co/dataset/estratificacion-para-bogota
- https://datosabiertos.bogota.gov.co/dataset/estructura-ecologica-principal-bogota-d-c
- https://datosabiertos.bogota.gov.co/dataset/valor-de-referencia-por-metro-cuadrado-de-terreno
- https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N04_00_W075_00_DEM/Copernicus_DSM_COG_10_N04_00_W075_00_DEM.tif
- https://datosabiertos.bogota.gov.co/
