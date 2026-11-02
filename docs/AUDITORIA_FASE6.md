# Auditoría integral de Fase 6

Fecha: 2026-11-01. Estado: revisión parcial; la Fase 2 seguía escribiendo productos cuando se realizó esta auditoría. Ejecutar `cmd /c scripts/run_audit_phase6.bat --base-url http://localhost:8000` para actualizar el informe geoespacial cuando no haya archivos SQLite journal activos.

## Exactitud posicional y CRS

La exactitud posicional externa no es cuantificable con los insumos disponibles: no se entregaron puntos de control GNSS/topográficos independientes ni tolerancias de aceptación. La transformación inversa comprueba coherencia numérica del CRS, no exactitud de fuente ni error de levantamiento.

La capa procesada de localidades se abrió con QGIS: 19 entidades, EPSG:9377. Su envolvente transformada fue `[-74.223941, 4.4684551, -74.0116925, 4.8307068]` en EPSG:4326. El error numérico de ida y vuelta en el centro de la envolvente fue 0.0 m a la precisión reportada. Esta prueba no reemplaza una red de control.

El reporte de procesamiento disponible registra EPSG:4326 en los GeoJSON de origen; EPSG:9377 en productos procesados; WGS 84 personalizado `SRS_ID=300001` para dos GeoPackages CarMAGBOG; y EPSG:4326 para el valor de referencia. Se mantiene la transformación desde la definición CRS original, no una reasignación.

## Geometrías y atributos

El último reporte de Fase 2 indica 0 geometrías inválidas después de reparación en las capas procesadas. En valor de referencia registra 6 inválidas en origen reparadas y 8 duplicadas retiradas. Una geometría GEOS válida no prueba que polígonos vecinos no tengan solapes o vacíos topológicos.

Se agregó una validación que detiene la exportación GeoJSON si falta un campo pedido, en vez de omitirlo silenciosamente. El conteo de nulos y la presencia de atributos clave se automatizaron en `scripts/audit_phase6.py`, pero no se ejecutaron contra todos los GeoPackages porque algunos tenían una transacción activa. Los nulos de indicador pueden ser ausencia de dato y no deben interpretarse como cero.

No se incorporan propietarios ni identificaciones. La lista de nombres de campo sensibles es un filtro preventivo, no una revisión legal de los valores.

## Metadatos y linaje

Se corrigió la escala ArcGIS en `docs/METADATOS.md`: el cero es el centinela de límite abierto, no una escala 0. Se documentó el DSM Copernicus GLO-30 descargado, recorte con buffer de 5 km y reproyección a EPSG:9377. El raster incluye edificios y vegetación y no tiene ajuste vertical comprobado.

## Rendimiento y publicación web

La muestra secuencial local de los primeros cuatro recursos estáticos fue de 50.702 bytes y 0,1504 s en localhost. No es una medida de primera pintura: no incluye MapLibre/PMTiles por CDN, relieve, teselas, caché, red móvil ni dispositivo.

Al muestrear la carpeta mientras la exportación estaba activa, se observó un temporal del driver PMTiles mayor a 95 MB y un GeoJSON redundante de indicadores de aproximadamente 24 MB. Los tamaños cambiaban durante la escritura, por lo que no se consideran medidas finales. Se corrigió el pipeline para preparar tiles y GeoJSON en `data/processed/phase2/`, retirar el GeoJSON redundante y mover únicamente productos completos a `web/`. Se añadió `--export-only` para rehacer la publicación después de completar el proceso, sin recalcular las capas.

Todavía no hay una medición reproducible de tamaño/tiempo de tiles finales. La Fase 2 debe terminar y los productos deben aprobar licencia antes de agregarlos a Git. El manifiesto rastreado permanece vacío para evitar publicar datos sin aprobación.

## Accesibilidad

Se añadieron enlaces para saltar al contenido, foco visible, instrucciones accesibles del mapa, estado dinámico anunciable y etiqueta de valor para exageración del terreno. Se elevaron colores de texto con contraste bajo. La auditoría estática de ambos HTML pasó; los colores de texto de paleta muestreados superan 6:1 sobre el panel oscuro. No equivale a certificación WCAG ni a prueba con lector de pantalla.

## Hallazgos y estado de publicación

- La exactitud posicional requiere puntos de control independientes.
- Los paquetes PMTiles finales y sus tiempos de carga requieren que termine Fase 2.
- Valor, estrato e índice están asociados a manzanas; el producto de edificios puede no contener esos atributos y el visor lo advierte. Asociarlos por lote/manzana requiere un join derivado y una nueva validación.
- Los productos derivados permanecen fuera de Git por defecto hasta aprobar licencia, privacidad e integridad.
- La publicación pública sigue bloqueada: GitHub Pages no estaba habilitado y `gh` no estaba autenticado; la URL devolvía 404. El push de esta fase necesita autenticación y nueva ejecución de Actions.
