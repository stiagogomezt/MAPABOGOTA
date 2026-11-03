# Requisitos del visor 3D de Bogotá

## Bloque 1 — Información exacta
- REQ-COORD: ficha muestra coordenadas EPSG:9377 reales y WGS84 (decimal y GMS), con botón copiar. Error < 30 m vs pyproj.
- REQ-ALTITUD: altitud ortométrica real del MDT, sin exageración. Plaza de Bolívar y Monserrate ±5 m. Ningún punto fuera del rango del MDT.
- REQ-FICHA-CATASTRAL: ficha con secciones Ubicación, Manzana, Terreno/Construcción (LADM-COL). Consulta tesela vectorial del punto (PMTiles lotes/manzanas). Sin datos personales. 5 puntos conocidos.
- REQ-ETIQUETAS: etiquetas en coordenada real (<30 px), sin superposiciones, prioridad por importancia, incluye localidades. Captura + cálculo de recuadros.
- REQ-ESCALA: barra de escala calculada según distancia cámara-centro. Cambia al acercar.

## Bloque 2 — Calidad de imagen
- REQ-HD: pixelRatio min(devicePixelRatio,2), anisotropía máxima, texturas 8192 en escritorio, sRGB, antialiasing. Decodificadores en web/vendor/ con versión fija. GLB con Draco.
- REQ-COSTURAS: eliminar franja oscura del occidente (ajuste de color + transición).
- REQ-SOMBRAS: sin vetas en laderas (bias, resolución, estiramiento de textura).

## Bloque 3 — Exploración rápida
- REQ-NAVEGACIÓN: MapControls zoomToCursor, velocidad proporcional a altura, amortiguación, doble clic, render on demand. <2 s de vista general a 500 m; ≥50 fps en calidad Media.

## Bloque 4 — Interfaz premium
- REQ-DISEÑO: sistema de diseño en un archivo de variables, iconos SVG locales, paneles con desenfoque, interruptores/deslizadores propios, estados hover/activo/foco. WCAG 2.2 AA.
- REQ-ORGANIZACIÓN: panel izquierdo "Mapa" (Mapa base + Capas agrupadas) y barra vertical de herramientas. Cada función aparece una sola vez. Textura "Localidades" desaparece (es una capa).
- REQ-AYUDA: tooltip por herramienta, ícono "?" con explicación, recorrido guiado de 5-6 pasos, accesible por teclado.

## Orientación
- REQ-ORIENTACIÓN: Este→+X, Norte→−Z, altura→+Y. camera.up=(0,1,0). OrbitControls sin pasar del nadir. Conversión Blender→three.js documentada. Prueba: Monserrate a la derecha de El Dorado, Suba arriba de Usme, brújula coincide. Clic en Plaza de Bolívar <50 m del valor de referencia.
EOF