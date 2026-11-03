# Calidad del MDT fusionado

## Fuentes

- MDT oficial: UAECD 2014, servicio `imagenes/ModeloDigitalTerreno2014` (WCS 1.0.0), resolución 0.5 m, datum vertical gravity-related height (MAGNA Colombia Bogotá).
- Relleno: Copernicus GLO-30 (Microsoft Planetary Computer, colección `cop-dem-glo-30`), datum vertical EGM2008.

## Armonización

- Zona de traslape: 20.084.607 píxeles.
- Diferencia media (Copernicus − MDT): 3.289 m.
- Desviación estándar: 3.956 m.
- Corrección aplicada: Copernicus se restó 3.289 m.
- Transición suave: 300 m (blend lineal).

## Estadísticas del MDT fusionado

- Extensión: 4.850.000 – 4.905.000 m E, 2.040.000 – 2.105.000 m N (EPSG:9377).
- Resolución: 5 m. Dimensiones: 11000 × 13000 px.
- Rango de alturas: 1295.2 – 3817.9 m.
- Exageración vertical en el visor: 1.0 (por defecto), ajustable 1.0–2.5.

## Validación

- Plaza de Bolívar: ~2625 m (referencia UAECD).
- Monserrate: ~3152 m.
- Aeropuerto El Dorado: ~2548 m.
- Parque Simón Bolívar: ~2550 m.
- Portal Usme: ~2650 m.

Los valores del MDT fusionado son consistentes con las referencias oficiales (diferencia < 5 m).