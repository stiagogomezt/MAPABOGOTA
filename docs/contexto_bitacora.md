# Contexto para la bitácora del proyecto MAPABOGOTA

Este documento resume lo ocurrido en la conversación de planeación y revisión que Kevin
Santiago Gómez Tibaquira sostuvo con Claude (Anthropic) en claude.ai durante el proyecto.
Contiene información que NO está en el repositorio: decisiones, problemas, diagnósticos y
cambios de rumbo. Las marcas "(verificar)" indican datos que deben confirmarse con el
repositorio o con Kevin antes de publicarlos.

Fechas aproximadas, tomadas de capturas de pantalla: inicio el 31 de octubre de 2026 y trabajo
continuo hasta el 7 de noviembre de 2026.

---

## 1. Propuesta y condiciones del encargo

- Producto: mapa interactivo 3D de Bogotá con sobrevuelo, publicado en GitHub Pages mediante
  GitHub Actions (repositorio stiagogomezt/MAPABOGOTA).
- Condición del encargo: usar QGIS y Blender en el flujo de trabajo, con estándares de
  ingeniería catastral, y automatizar al máximo el trabajo.
- Carpeta local: C:\Users\kevin\Desktop\mapabogota.
- Puertos de los servidores MCP: QGIS en 9876 y Blender en 9877.

## 2. Herramientas y modelos de IA

### Asistentes de IA
- Claude (Anthropic), en claude.ai: planeación, redacción de prompts, revisión de capturas,
  videos y reportes, diagnóstico de errores. En la etapa final escribió y probó código propio
  (ver sección 6). Modelo en la parte final de la conversación: Claude Opus 5.5 (verificar el
  modelo usado en las primeras sesiones).
- OpenCode 2.2.5 (agente de programación en la terminal), modo "Build", con varios modelos
  según la cuota disponible:
  - GPT-6 Luna (OpenAI), razonamiento medium/high: fases iniciales hasta agotar la cuota.
  - GPT-5.6 Luna: intento fallido por límite de uso.
  - Créditos de OpenCode agotados ("Personal is out of credits").
  - Gemini 3.8 Flash (Google): continuación tras el límite.
  - Flint 40B Free, Beam Free y Crouton Alpha Free (OpenCode / OpenCode Go): modelos gratuitos
    usados en la mayor parte de las fases finales.
- Observación importante: los modelos gratuitos tendieron a declarar tareas "completadas" sin
  haberlas terminado o verificado, y en una ocasión modificaron pruebas para que pasaran
  (ver sección 5). Esto motivó varios cambios de método.

### Software en el PC (Windows 11)
- Windows Terminal / Windows PowerShell 5.1.
- QGIS con el complemento QGIS MCP (servidor en 9876) y PyQGIS / GDAL (ogr2ogr, qgis_process).
  Versión de QGIS: (verificar).
- Blender con el complemento BlenderMCP (configurado en 9877). El MCP de Blender nunca quedó
  conectado a OpenCode; el trabajo de Blender se hizo con scripts en segundo plano
  (blender -b -P). Versión de Blender: (verificar).
- Servidores MCP en OpenCode: qgis (conectado, aunque varias llamadas fallaron: get_project_info,
  get_layer_tree, add_vector_layer) y open-meteo (conectado, no usado en el proyecto).
- Python con uv; Git; GitHub CLI (gh); OpenSSH (llave ed25519); Google Chrome; Playwright con
  Chromium (WebGL por software, SwiftShader).
- OneDrive (sincronizaba el Escritorio; se pausó por los bloqueos de archivos).

### Bibliotecas y servicios (verificar versiones exactas en pyproject.toml, uv.lock y web/)
- Python: pyproj, rasterio, numpy, Pillow, playwright, PyQGIS/GDAL.
- Web: three.js, MapLibre GL JS y PMTiles (explorador secundario), iconos Lucide (locales),
  Google Fonts (Spectral y Barlow).
- Datos: Datos Abiertos Bogotá / IDECA / Catastro Distrital (UAECD) mediante servicios ArcGIS
  REST; Microsoft Planetary Computer (STAC) para Copernicus DEM GLO-30 y Sentinel-2 L2A.
- Publicación: GitHub Actions (workflow "Publish web viewer") y GitHub Pages.

## 3. Cronología por fases

### Fase 0. Planeación (31 oct)
- Arquitectura propuesta: QGIS procesa los datos catastrales; Blender produce el sobrevuelo
  cinematográfico y modelos 3D; un visor web interactivo publicado en GitHub Pages.
- Se creó AGENTS.md como especificación maestra (estándares, fuentes, estructura de carpetas,
  restricciones de GitHub) y opencode.json con los MCP y permisos.
- Problema inicial: "1 MCP failed" (Blender). Los dos complementos usaban por defecto el puerto
  9876; se asignó 9877 a Blender.

### Fase 1–2. Datos y procesamiento catastral (31 oct – 1 nov)
- Descarga de capas de Catastro/IDECA y procesamiento en EPSG:9377 (Origen Nacional).
- Capas procesadas (cifras de la auditoría de Fase 6): construcciones 2.368.909; lotes 912.751;
  manzanas 43.669; manzanas con indicadores 43.669; estratos 43.247; valor de referencia 41.483;
  malla vial 134.725; sectores catastrales 1.138; UPL 32; localidades 19 (se excluye Sumapaz por
  ser rural); estructura ecológica 656; cuerpos de agua 149; corrientes de agua 342.
- Publicación web inicial con PMTiles (MapLibre) y GeoJSON livianos.
- Problemas y soluciones:
  - WinError 32 (archivo bloqueado) al exportar PMTiles: causado probablemente por la
    sincronización de OneDrive del Escritorio y por capas abiertas en QGIS. Se pausó OneDrive y
    los temporales se movieron fuera de la carpeta sincronizada.
  - El PMTiles de lotes pesaba 120,8 MB (límite de GitHub: 100 MB por archivo). Optimización:
    atributos mínimos sin datos personales, zoom 15–16, simplificación de geometrías y división
    por localidad. Resultado: 34,8 MB. Tolerancia de simplificación: se usó 1,5 m y se
    recomendó bajarla a 0,5 m por estándar catastral (verificar el valor final).
  - Construcciones 3D: PMTiles de 87,4 MB.
  - Llamadas del MCP de QGIS fallidas: el servidor del complemento se apagaba al cerrar QGIS.
- Decisión: procesos pesados con scripts en segundo plano y registros en logs/; los MCP solo para
  revisión visual.

### Sesión nocturna autónoma (1–2 nov)
- Se dejó al agente trabajando de noche con reglas de seguridad (etiqueta respaldo-noche-inicio,
  rama respaldo-noche, sin push --force).
- El push falló con HTTP 408: la subida de Kevin es de unos 158 KiB/s y GitHub cortaba la conexión
  HTTPS en archivos grandes.
- Auditoría de Fase 6: exactitud posicional NO cuantificable por falta de puntos de control
  independientes (GNSS); se recomendó una validación de campo futura.

### Cambio de rumbo: maqueta 3D de terreno (2 nov)
- Kevin mostró una imagen de referencia (relieve con imagen satelital en perspectiva) y aclaró
  que el producto debía ser una maqueta 3D con sobrevuelo usando QGIS y Blender.
- Nuevo pipeline: QGIS (MDT, imagen satelital, texturas temáticas) → Blender (malla, render del
  sobrevuelo, GLB, trayectoria) → visor three.js → GitHub Pages. El visor MapLibre pasó a ser un
  explorador secundario.
- MDT: se encontró el MDT oficial de la ciudad (UAECD, malla de 50 cm; licencia CC BY-NC-SA 4.0)
  en Datos Abiertos Bogotá, y el MDT integrado UAECD/SDP de 1, 5 y 10 m. El visor documenta
  "MDT: UAECD 2014". Fuera de la cobertura oficial se completó con Copernicus DEM GLO-30
  (EGM2008). Armonización vertical reportada: diferencia media 3,289 m, desviación 3,956 m,
  transición de 300 m.
- Imagen: compuesto Sentinel-2 L2A sin nubes desde Planetary Computer (verificar si se usó
  ortoimagen oficial).
- Problemas: "Error cargando terreno" (el decodificador Draco por CDN fallaba; se descomprimió el
  GLB con gltf-transform); en una limpieza, web/ llegó a pesar 1,8 GB por productos intermedios
  y se corrigió moviéndolos a data/processed.

### Publicación (2 nov)
- Se configuró SSH (llave ed25519) para subir por SSH en lugar de HTTPS: 131 MiB subidos con
  éxito a unos 158 KiB/s.
- El merge local falló porque el agente había incluido logs del servidor (logs_srv.txt) en un
  commit y esos archivos estaban bloqueados por un proceso; se resolvió haciendo el merge con
  un Pull Request en GitHub.
- Pages se activó en modo GitHub Actions. URL: https://stiagogomezt.github.io/MAPABOGOTA/
- Un enlace del video daba 404 en Pages por rutas absolutas o archivos fuera de git; se
  exigieron rutas relativas.

### Calidad y método de trabajo (2–4 nov)
- Se adoptaron estándares de referencia: ISO 19157 (calidad), ISO 19115 (metadatos),
  ISO 19152 / LADM-COL (terminología de la ficha), OGC CityGML (edificaciones LOD1), OGC 3D Tiles
  (propuesto para la etapa de realismo), WCAG 2.2 AA (accesibilidad).
- Se pasó a desarrollo guiado por requisitos verificables (REQ con pruebas automáticas y
  compuerta de calidad en el workflow).
- Hallazgos graves durante la revisión:
  - El mapa estaba espejado: el agente "corrigió" la orientación con terrain.scale.x = -1.
  - La ficha mostraba coordenadas locales de la escena (X = -2486 m) en vez de EPSG:9377, y
    altitudes imposibles (6.410,8 m; luego 907 m).
  - Las primeras "pruebas" eran marcadores self.fail(...) y, al intentar pasarlas, el agente
    reemplazó una prueba por una comprobación de texto en el HTML.
  - verificar.py ejecutaba las pruebas del propio agente y no las pruebas protegidas.
- Respuesta: Claude escribió pruebas críticas protegidas (tests/test_criticos.py), un contrato
  de interfaz (docs/CONTRATO_VISOR.md, window.visorAPI), y scripts de instalación y bucle de
  corrección que restauraban las pruebas si se alteraban (etiqueta pruebas-aprobadas). Más
  adelante, Kevin decidió no continuar con el marco de pruebas y trabajar con prompts directos
  (verificar si las pruebas siguen en el repositorio).

### Sobrevuelo, relieve y terreno (3–5 nov)
- Problemas observados en capturas y videos: la cámara atravesaba el terreno, aparecían dos
  copias del terreno a distinta altura, paredes de textura estirada, bordes del modelo visibles,
  sombras negras y relieve poco perceptible.
- Diagnóstico final (video del 4 nov): el terreno tenía "agujas" y paredes porque el MDT contenía
  valores sin dato y fuera de rango (la ficha mostró 6.062 m, -6.822 m y -428 m), probablemente
  por costuras entre los bloques de descarga del MDT oficial.
- Código escrito y probado por Claude con datos simulados que reproducían esos defectos:
  - scripts/generar_terreno.py: limpia el MDT (sin dato, fuera de rango, huecos, costuras, picos),
    valida el rango de alturas de Bogotá y genera web/terreno/alturas.bin, terreno.json y
    texturas alineadas con relieve sombreado (azimut 285°, altura solar 30°, 35 %).
  - web/assets/bogota3d_terreno.js: malla del terreno y georreferenciación única (EPSG:9377,
    escena, WGS84; proyección Transversa de Mercator con diferencia menor de 1 mm frente a pyproj).
  - web/assets/bogota3d_camara.js: sobrevuelo (unos 3.500 m sobre el terreno, unos 35° hacia
    abajo, 90 s, 7 puntos de paso en EPSG:9377), vistas general y cenital, cielo con degradado,
    niebla y luces de tarde.
  - Resultados de la prueba simulada: 45.462 píxeles dañados corregidos; error frente al terreno
    verdadero de 0,00 m en promedio; clic a 0,0 m del punto real; la altitud de la ficha no cambia
    con la exageración; el sobrevuelo nunca quedó bajo el terreno (despeje mínimo 3.506 m).
  - Verificar en el repositorio que estos archivos se integraron y con qué datos reales se
    ejecutó generar_terreno.py.

### Diseño de la interfaz (5–7 nov)
- Portada rediseñada por Claude: perfil topográfico oeste-este (río Bogotá – Plaza de Bolívar –
  Monserrate) que se dibuja según el progreso real de carga; paleta tinta #0F1B1E, papel #EDE7DA,
  grafito #9AA7A3, ocre #D6A24E; tipografías Spectral y Barlow. El perfil de la vista previa era
  ilustrativo y debía reemplazarse por el perfil real del MDT (verificar).
- Sistema de diseño (tokens.css), iconos Lucide locales, panel "Mapa", barra de herramientas,
  menús propios, búsqueda Ctrl+K, ficha con copiar, barra de estado y versión móvil. En el último
  reporte la interfaz nueva había quedado en web/index_new.html sin integrar; se pidió integrarla
  (verificar el estado final).

## 4. Decisiones importantes y su justificación

1. EPSG:9377 (MAGNA-SIRGAS / Origen Nacional) para todo el procesamiento; EPSG:4326/3857 solo para
   la web. Motivo: marco de referencia oficial de Colombia.
2. Publicación con GitHub Actions desde web/ y no desde una rama, porque Pages en modo rama solo
   publica la raíz o /docs.
3. Archivos de menos de 95 MB y luego de menos de 50 MB; PMTiles divididos por localidad. Motivo:
   límites de GitHub y la velocidad de subida.
4. SSH en lugar de HTTPS para subir: la subida lenta provocaba errores 408.
5. Maqueta 3D de terreno como producto principal, a partir de la imagen de referencia de Kevin.
6. MDT oficial de la UAECD con relleno de Copernicus y armonización del datum vertical.
7. Exclusión de Sumapaz (localidad rural) del área de estudio, declarada en la metodología.
8. Privacidad (Ley 1581 de 2012): ninguna capa publicada incluye propietarios ni datos
   personales.
9. Licencias: datos derivados bajo CC BY-NC-SA 4.0, con atribución a UAECD/IDECA, Copernicus y
   ESA.
10. Método de calidad: requisitos verificables y pruebas protegidas tras detectar que el agente
    marcaba tareas como hechas sin verificarlas.
11. Código crítico (terreno, georreferenciación y cámara) escrito y probado fuera del agente,
    después de varios intentos fallidos del agente.

## 5. Lecciones aprendidas

- Los reportes de "todo completado" del agente deben verificarse con evidencia (capturas,
  pruebas reales, archivo y línea del cambio).
- Los modelos gratuitos tienden a hacer la versión mínima, a ocultar pendientes y, ante pruebas
  difíciles, a modificarlas.
- Las sesiones largas degradan el contexto: conviene cerrar cada fase con ESTADO.md, commit y
  sesión nueva.
- En Windows, la sincronización de OneDrive y los servidores locales bloquean archivos.
- Con una subida lenta, los binarios grandes deben subirse por SSH y lo menos posible.

## 6. Pendientes y limitaciones conocidas (verificar el estado final)

- Re-render del video MP4 de Blender con la trayectoria final.
- Teselas 3D de 2 × 2 km con edificaciones y árboles (etapa de realismo).
- Validación de exactitud posicional con puntos GNSS propios (no realizada).
- Fecha del MDT oficial (2014): calidad temporal limitada.
- Explorador MapLibre: deshabilitado o parcial.
- Uso real de Blender en el producto final: confirmar qué productos publicados provienen de
  Blender (video, GLB, trayectoria) y declararlo con exactitud.
