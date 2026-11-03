# Contrato del visor: `window.visorAPI`

**Documento protegido.** Lo escribió una persona, no el agente, y no se modifica.
Las pruebas de `tests/test_criticos.py` usan esta interfaz para comprobar el
comportamiento real del visor, no la presencia de textos en el HTML. La interfaz
de usuario debe usar internamente estas mismas funciones: por ejemplo, el clic
del usuario y `consultarPantalla()` ejecutan el mismo código.

## Convenciones obligatorias

- Conversión de ejes: Este → +X, Norte → −Z, altura → +Y (three.js, Y arriba),
  con el origen local definido en `georef.json`.
- Prohibido usar escalas negativas o espejados para orientar el mapa.
  El determinante de la matriz del terreno debe ser positivo.
- Las altitudes que se muestran o se devuelven son reales (m s.n.m.), sin exageración vertical.
- Las coordenadas EPSG:9377 que se muestran o se devuelven son absolutas
  (Origen Nacional), nunca locales de la escena.
- Un clic simple sobre el terreno, sin otra herramienta activa, abre la ficha.
- Todas las conversiones entre EPSG:9377 y la escena pasan por un único módulo
  (`web/assets/geo.js`). El terreno, las etiquetas, la ficha, el perfil y el
  sobrevuelo usan ese módulo; ninguna otra parte del código convierte coordenadas
  ni aplica la exageración por su cuenta.

## Miembros de `window.visorAPI`

| Miembro | Devuelve | Descripción |
|---|---|---|
| `listo` | booleano | `true` solo cuando el terreno y la textura activa están cargados y se dibujó al menos un fotograma. |
| `cerrarPortada()` | — | Cierra la portada y pantallas superpuestas, como si el usuario presionara "Explorar". |
| `vistaGeneral()` | — | Vista inicial oblicua de toda el área. |
| `vistaNorte()` | — | Vista oblicua (unos 45°) de toda el área, mirando al norte. |
| `enfocar(este, norte, distancia)` | — | Centra la cámara sobre el punto EPSG:9377, a esa distancia en metros, mirando al norte con unos 45° de inclinación. |
| `rumboCamara()` | número | Rumbo de la cámara en grados, de 0 a 360 (0 = norte, sentido horario). Es el mismo valor que usa la brújula. |
| `pantallaDesdeEPSG9377(este, norte)` | `{x, y, visible}` | Posición en píxeles CSS del viewport del punto sobre el terreno (altura del MDT × exageración actual). `visible` es falso si queda fuera de pantalla o detrás de la cámara. |
| `consultarPantalla(x, y)` | ficha o `null` | Hace exactamente lo mismo que un clic del usuario en (x, y): raycast, abre o actualiza la ficha visible, y devuelve el objeto ficha. |
| `consultarEPSG9377(este, norte)` | ficha | Objeto ficha del punto, sin mover la cámara. |
| `fijarExageracion(factor)` | — | Cambia la exageración vertical, y actualiza el deslizador. |
| `rangoAlturas()` | `{min, max}` | Altitudes reales mínima y máxima del MDT, en metros. |
| `determinanteTerreno()` | número | Determinante de la parte 3×3 de `matrixWorld` de la malla del terreno. |
| `duracionSobrevuelo()` | número | Duración del sobrevuelo en segundos. |
| `posicionarSobrevuelo(t)` | — | Coloca la cámara en la pose del sobrevuelo en el instante `t` (segundos), con la exageración actual y sin animar. Usa el mismo código que la reproducción. |
| `iniciarSobrevuelo()` / `detenerSobrevuelo()` | — | Inician o detienen la reproducción, como el botón de la interfaz. |
| `despejeCamara()` | número | Distancia vertical en metros, tal como se dibuja la escena (con la exageración actual), entre la cámara y la superficie del terreno justo debajo. Negativa si la cámara está bajo el terreno. |

## Objeto ficha

```js
{
  epsg9377: { E: number, N: number },  // absolutas, Origen Nacional
  wgs84:    { lat: number, lon: number }, // grados decimales
  altitud:  number,                     // m s.n.m., real, sin exageración
  localidad: string | null
}
```

## Requisitos del DOM de la ficha

- Contenedor visible con `data-testid="ficha"`, cuyo texto incluye "EPSG:9377".
- Elementos con `data-testid="ficha-este"`, `data-testid="ficha-norte"`,
  `data-testid="ficha-lat"`, `data-testid="ficha-lon"` y
  `data-testid="ficha-altitud"`, cada uno con el atributo `data-valor` igual al
  número sin formato (por ejemplo `data-valor="4880712.35"`). El texto visible
  puede ir formateado (por ejemplo "4.880.712,35 m").

## Sobrevuelo

La cámara se mantiene siempre a más de 400 m sobre el terreno, con cualquier
exageración entre 1.0 y 2.5, y la altura típica del vuelo está entre 800 y
3.500 m (vuelo panorámico). Si la exageración cambia, la trayectoria se adapta
para conservar ese despeje. El centro de Bogotá se ve durante al menos la mitad
del vuelo.

## Requisitos del DOM de las etiquetas

- Cada etiqueta es un elemento con `data-testid="etiqueta"` y
  `data-nombre="<nombre exacto>"`. Nombres obligatorios: "Plaza de Bolívar",
  "Monserrate" y "Aeropuerto El Dorado" (más las localidades).
- Dentro de cada etiqueta, un marcador con `data-testid="etiqueta-punto"` cuyo
  centro visual está exactamente sobre el punto real del terreno.
- Si dos etiquetas chocan, se oculta la de menor prioridad: nunca se superponen.

## Entorno de pruebas

Chromium de Playwright con WebGL por software
(`--use-angle=swiftshader --enable-unsafe-swiftshader`). El visor debe cargar y
dibujar correctamente en ese entorno.