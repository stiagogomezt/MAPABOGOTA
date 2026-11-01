# Metadatos e inventario de fuentes

Inventario generado: 2026-11-01T08:17:32.922308+00:00 (UTC).
Datos fuente en `data/raw/` se excluyen de Git. Los GeoJSON ArcGIS se exportaron a EPSG:4326 para preservación interoperable. El CRS oficial de origen se registra por servicio; la reproyección a EPSG:9377 se realizará en procesamiento, no sobre estos originales. El visor proyecta en EPSG:3857.

## Capas descargadas

### suelo_urbano_mascara

- Archivo: `data/raw/suelo_urbano_mascara.geojson`
- Fuente: https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/Mapa_Referencia/Mapa_Referencia/MapServer/45
- Fecha de edición de origen: no informada por servicio
- Fecha de descarga: 2026-11-01T06:56:24.254237+00:00
- Entidades descargadas: 5; conteo intersectando suelo urbano: 5.
- CRS origen informado: EPSG:4326; CRS del archivo descargado: EPSG:4326.
- Escala de visualización del servicio (denominador): maxScale 1:25,000; minScale sin límite (ArcGIS codifica el límite abierto como 0).
- Campos descargados: SUECODIGO, SUECSUELO, SUEAADMIN, SUEAREA, OBJECTID.
- Licencia: consultar términos del Mapa de Referencia y metadatos IDECA antes de redistribuir.

### localidad

- Archivo: `data/raw/localidad.geojson`
- Fuente: https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/Mapa_Referencia/Mapa_Referencia/MapServer/48
- Fecha de edición de origen: no informada por servicio
- Fecha de descarga: 2026-11-01T06:56:26.445300+00:00
- Entidades descargadas: 19; conteo intersectando suelo urbano: 19.
- CRS origen informado: EPSG:4326; CRS del archivo descargado: EPSG:4326.
- Escala de visualización del servicio (denominador): no declarada / sin límite (ArcGIS informa 0 en ambos límites).
- Campos descargados: LOCCODIGO, LOCNOMBRE, LOCAADMINI, LOCAREA, OBJECTID.
- Licencia: consultar términos del Mapa de Referencia y metadatos IDECA antes de redistribuir.

### upl

- Archivo: `data/raw/upl.geojson`
- Fuente: https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/Mapa_Referencia/Mapa_Referencia/MapServer/44
- Fecha de edición de origen: no informada por servicio
- Fecha de descarga: 2026-11-01T06:56:28.201711+00:00
- Entidades descargadas: 32; conteo intersectando suelo urbano: 32.
- CRS origen informado: EPSG:4326; CRS del archivo descargado: EPSG:4326.
- Escala de visualización del servicio (denominador): no declarada / sin límite (ArcGIS informa 0 en ambos límites).
- Campos descargados: NOMBRE, ACTO_ADMINISTRATIVO, OBJECTID, CODIGO_UPL, NUMERO_ACTO_ADMINISTRATIVO, FECHA_ACTO_ADMINISTRATIVO, NORMATIVA, VOCACION, OBSERVACION, AREA_HA.
- Licencia: consultar términos del Mapa de Referencia y metadatos IDECA antes de redistribuir.

### sector_catastral

- Archivo: `data/raw/sector_catastral.geojson`
- Fuente: https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/Mapa_Referencia/Mapa_Referencia/MapServer/37
- Fecha de edición de origen: no informada por servicio
- Fecha de descarga: 2026-11-01T06:56:43.720375+00:00
- Entidades descargadas: 1,138; conteo intersectando suelo urbano: 1,138.
- CRS origen informado: EPSG:4326; CRS del archivo descargado: EPSG:4326.
- Escala de visualización del servicio (denominador): minScale 1:199,999; maxScale sin límite (ArcGIS codifica el límite abierto como 0).
- Campos descargados: SCACODIGO, SCATIPO, SCANOMBRE, OBJECTID.
- Licencia: consultar términos del Mapa de Referencia y metadatos IDECA antes de redistribuir.

### manzana

- Archivo: `data/raw/manzana.geojson`
- Fuente: https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/Mapa_Referencia/Mapa_Referencia/MapServer/40
- Fecha de edición de origen: no informada por servicio
- Fecha de descarga: 2026-11-01T07:01:50.812179+00:00
- Entidades descargadas: 43,682; conteo intersectando suelo urbano: 43,682.
- CRS origen informado: EPSG:4326; CRS del archivo descargado: EPSG:4326.
- Escala de visualización del servicio (denominador): minScale 1:20,000; maxScale sin límite (ArcGIS codifica el límite abierto como 0).
- Campos descargados: MANCODIGO, SECCODIGO, OBJECTID.
- Licencia: consultar términos del Mapa de Referencia y metadatos IDECA antes de redistribuir.

### lote

- Archivo: `data/raw/lote.geojson`
- Fuente: https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/Mapa_Referencia/Mapa_Referencia/MapServer/38
- Fecha de edición de origen: no informada por servicio
- Fecha de descarga: 2026-11-01T07:20:53.444957+00:00
- Entidades descargadas: 912,777; conteo intersectando suelo urbano: 912,777.
- CRS origen informado: EPSG:4326; CRS del archivo descargado: EPSG:4326.
- Escala de visualización del servicio (denominador): minScale 1:10,000; maxScale sin límite (ArcGIS codifica el límite abierto como 0).
- Campos descargados: LOTCODIGO, LOTDISPERS, LOTILDISPE, LOTUPREDIA, LOTDISTRIT, MANZCODIGO, OBJECTID.
- Licencia: consultar términos del Mapa de Referencia y metadatos IDECA antes de redistribuir.

### malla_vial

- Archivo: `data/raw/malla_vial.geojson`
- Fuente: https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/Mapa_Referencia/Mapa_Referencia/MapServer/13
- Fecha de edición de origen: no informada por servicio
- Fecha de descarga: 2026-11-01T08:07:10.393929+00:00
- Entidades descargadas: 134,726; conteo intersectando suelo urbano: 134,726.
- CRS origen informado: EPSG:4326; CRS del archivo descargado: EPSG:4326.
- Escala de visualización del servicio (denominador): minScale 1:10,000; maxScale sin límite (ArcGIS codifica el límite abierto como 0).
- Campos descargados: MVICODIGO, MVICCALZAD, MVICIV, MVICCAT, MVITCLA, MVITIPO, MVINOMBRE, MVINALTERN, MVINPRINCI, MVINGENERA, MVINANTIGU, MVIETIQUET, MVISVIA, MVINUMC, MVIVELREG, OBJECTID.
- Licencia: consultar términos del Mapa de Referencia y metadatos IDECA antes de redistribuir.

### corriente_agua

- Archivo: `data/raw/corriente_agua.geojson`
- Fuente: https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/Mapa_Referencia/Mapa_Referencia/MapServer/27
- Fecha de edición de origen: no informada por servicio
- Fecha de descarga: 2026-11-01T08:07:29.729968+00:00
- Entidades descargadas: 342; conteo intersectando suelo urbano: 342.
- CRS origen informado: EPSG:4326; CRS del archivo descargado: EPSG:4326.
- Escala de visualización del servicio (denominador): no declarada / sin límite (ArcGIS informa 0 en ambos límites).
- Campos descargados: TIPO, NOMBRE, SECTOR, CODCUE, CUENCA, CODSCUE, SUBCUENCA, CODMCUE, MICROCUENCA, OBSERVACION, LONGITUD, IDTABINV, CODHIDRO, OBJECTID.
- Licencia: consultar términos del Mapa de Referencia y metadatos IDECA antes de redistribuir.

### cuerpo_agua

- Archivo: `data/raw/cuerpo_agua.geojson`
- Fuente: https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/Mapa_Referencia/Mapa_Referencia/MapServer/29
- Fecha de edición de origen: no informada por servicio
- Fecha de descarga: 2026-11-01T08:07:43.058060+00:00
- Entidades descargadas: 149; conteo intersectando suelo urbano: 149.
- CRS origen informado: EPSG:4326; CRS del archivo descargado: EPSG:4326.
- Escala de visualización del servicio (denominador): no declarada / sin límite (ArcGIS informa 0 en ambos límites).
- Campos descargados: TIPO, NOMBRE, SECTOR, CODCUE, CUENCA, CODSCUE, SUBCUENCA, CODMCUE, MICROCUENCA, VOLUMEN, OBSERVACION, IDTABINV, CODHIDRO, OBJECTID, AMBIENTE.Hidrografia_CAgu.AREA.
- Licencia: consultar términos del Mapa de Referencia y metadatos IDECA antes de redistribuir.

### estratificacion_manzana

- Conjunto: Estratificación Manzana Bogotá D.C.
- Recurso: `data/raw/estratificacion_manzana.gpkg`
- Fecha de corte / actualización del metadato: 2025-11-20T14:56:11.902289
- Licencia declarada: Creative Commons Attribution 4.0
- Fuente: https://datosabiertos.bogota.gov.co/dataset/55467552-0af4-4524-a390-a2956035744e/resource/cde22374-35e8-4c7d-abf9-903cd82faa42/download/manzanaestratificacion.gpkg
- Tabla `ManzanaEstratificacion`: 44,260 registros; CRS CUSTOM:SRS_ID=300001 (Custom) (SRS ID 300001); campos: OBJECTID, Shape, CODIGO_MANZANA, ESTRATO, CODIGO_ZONA_ESTRATO, CODIGO_CRITERIO, NORMATIVA, ACTO_ADMINISTRATIVO, NUMERO_ACTO_ADMINISTRATIVO, FECHA_ACTO_ADMINISTRATIVO, ESCALA_CAPTURA, FECHA_CAPTURA, RESPONSABLE.
- Definición CRS de origen (WKT): `PROJCS["PCS_CarMAGBOG",GEOGCS["GCS_CarMAGBOG",DATUM["CGS_CarMAGBOG",SPHEROID["GRS80 Mod",6380687.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",92334.879],PARAMETER["False_Northing",109320.965],PARAMETER["Central_Meridian",-74.14659167],PARAMETER["Scale_Factor",1.0],PARAMETER["Latitude_Of_Origin",4.680486111],UNIT["Meter",1.0]]`

### estructura_ecologica_principal

- Conjunto: Estructura Ecológica Principal. POT Bogotá D.C.
- Recurso: `data/raw/estructura_ecologica_principal.gpkg`
- Fecha de corte / actualización del metadato: 2026-10-14T20:13:46.513869
- Licencia declarada: Creative Commons Attribution 4.0
- Fuente: https://datosabiertos.bogota.gov.co/dataset/ad85f11b-e9bc-41b6-aafc-716123801dae/resource/d42772aa-3a63-4fde-bf66-4217bd2aee12/download/estructuraecologicaprincipal.gpkg
- Tabla `EstructuraEcologicaPrincipal`: 4,553 registros; CRS CUSTOM:SRS_ID=300001 (Custom) (SRS ID 300001); campos: OBJECTID, Shape, CODIGO_ID, COMPONENTE, CATEGORIA, ELEMENTO, AREA_AMBIENTAL, NOMBRE_TOTAL, ACTO_ADMINISTRATIVO, NORMATIVA, OBSERVACION, ESCALA_CAPTURA, FECHA_CAPTURA, RESPONSABLE, REGLAID, OVERRIDE.
- Definición CRS de origen (WKT): `PROJCS["PCS_CarMAGBOG",GEOGCS["GCS_CarMAGBOG",DATUM["CGS_CarMAGBOG",SPHEROID["GRS80 Mod",6380687.0,298.257222101]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",92334.879],PARAMETER["False_Northing",109320.965],PARAMETER["Central_Meridian",-74.14659167],PARAMETER["Scale_Factor",1.0],PARAMETER["Latitude_Of_Origin",4.680486111],UNIT["Meter",1.0]]`

### valor_referencia_terreno

- Conjunto: Mediana del valor comercial por metro cuadrado de terreno por manzana – Valor de referencia. Bogotá D.C.
- Recurso: `data/raw/valor_referencia_terreno.gpkg`
- Fecha de corte / actualización del metadato: 2026-06-03T15:56:41.174958
- Licencia declarada: Creative Commons Attribution 4.0
- Fuente: https://datosabiertos.bogota.gov.co/dataset/a0ad3bf4-1e97-4cf9-b853-76558158036f/resource/90ad1c5e-ad74-4963-abf6-50aecb2314c1/download/valor_ref_2026.gpkg
- Tabla `valor_ref_m_2026`: 41,858 registros; CRS EPSG:4326 (SRS ID 4326); campos: fid, geom, MANCODIGO, V_REF, ANO, Shape_Leng, Shape_Area.
- Definición CRS de origen (WKT): `GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]`

## Capas no descargadas

- ArcGIS construccion (capa 39): [WinError 5] Access is denied: 'C:\\Users\\kevin\\Desktop\\mapabogota\\data\\raw\\construccion.geojson.part' -> 'C:\\Users\\kevin\\Desktop\\mapabogota\\data\\raw\\construccion.geojson'

## Protección de datos y alcance

Se excluyen campos cuyo nombre coincide con propietario, documento, cédula, identificación, titular, matrícula, dirección, teléfono, correo o persona. Esta lista no sustituye una revisión legal del contenido. No se descargó la tabla Predio del servicio ArcGIS. Los datos no deben publicarse hasta verificar licencia, atributos y controles de privacidad. La máscara de área urbana corresponde al polígono oficial de Suelo con clasificación urbana; no incluye suelo rural ni de expansión.

## Terreno y fallback

- Terreno mostrado en el visor: AWS Terrain Tiles, codificación Terrarium, consultado en vivo por tiles. No se hizo mosaico local ni se redistribuyen tiles. Fecha de descarga: no aplica; CRS de tesela: Web Mercator (EPSG:3857); elevación codificada en RGB. Verificar términos y atribución del proveedor.
- Copernicus DEM GLO-30: se descargó el 2026-11-01 en `data/raw/copernicus_dem_glo30_n04_w075.tif` (tesela N04 W075). El pipeline recortó un buffer de 5 km para las localidades centrales, reproyectó a EPSG:9377 con resolución de 30 m y produjo `data/processed/phase2/terrain_center_9377.tif`/`.asc`. Es un DSM con edificios y vegetación; no se aplicó transformación vertical ni se evaluó contra puntos de control. Verificar términos de redistribución antes de publicar el raster.
- OpenStreetMap/OSMnx: no utilizado como fallback, dado que el servicio oficial de referencia expone vías, edificios, hidrografía y áreas catastrales. Si se emplea después, identificarlo como OSM y cumplir ODbL.
