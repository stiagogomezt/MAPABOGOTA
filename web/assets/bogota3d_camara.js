/*
 * bogota3d_camara.js
 * Ambiente (cielo, niebla, luz, base) y sobrevuelo robusto para el visor 3D de Bogotá.
 *
 * Funciona con three.js r128 o superior, como script normal o junto a módulos ES.
 * Expone window.Bogota3D. No depende de cómo esté construido el resto del visor:
 * lee las alturas directamente de los vértices reales de la malla de terreno
 * (ya transformados al mundo, con la exageración vertical aplicada), así que la
 * cámara nunca puede quedar por debajo del terreno.
 *
 * Uso:
 *   const ambiente = Bogota3D.crearAmbiente({ THREE, escena, terreno, renderer, camara });
 *   const vuelo = Bogota3D.crearSobrevuelo({ THREE, camara, controles, terreno, aEscena,
 *                                            lienzo: renderer.domElement });
 *   vuelo.iniciar();
 *   Bogota3D.vistaGeneral({ THREE, camara, controles, terreno });
 *   Bogota3D.vistaCenital({ THREE, camara, controles, terreno });
 *
 *   aEscena(este, norte) recibe coordenadas EPSG:9377 y devuelve {x, z} de la escena
 *   (usar la conversión de web/assets/geo.js).
 *
 *   Cuando cambie la exageración vertical: ambiente.recalcular(); vuelo.recalcular();
 *
 *   Para pegar etiquetas y edificaciones al terreno:
 *     const alturas = Bogota3D.alturas(THREE, terreno);
 *     etiqueta.position.y = alturas.altura(x, z) + 40;
 */
(function (global) {
  "use strict";

  // Puntos de paso del sobrevuelo en EPSG:9377 (Origen Nacional), calculados con pyproj.
  const RUTA_BOGOTA = [
    [4873588, 2061976], // Tunjuelito - Ciudad Bolívar
    [4871604, 2069494], // Kennedy
    [4873610, 2075569], // Fontibón - El Dorado
    [4879386, 2082080], // Suba
    [4885589, 2078755], // Usaquén
    [4882696, 2071687], // Chapinero
    [4879806, 2067050]  // Centro
  ];

  const rad = (g) => (g * Math.PI) / 180;
  const limitar = (v, a, b) => Math.min(b, Math.max(a, v));
  const srgb = (hex) => [((hex >> 16) & 255) / 255, ((hex >> 8) & 255) / 255, (hex & 255) / 255];

  // ---------------------------------------------------------------------------
  // Rejilla de alturas construida con los vértices reales del terreno
  // ---------------------------------------------------------------------------
  function crearRejilla(THREE, terreno, n) {
    n = n || 256;
    terreno.updateMatrixWorld(true);
    const caja = new THREE.Box3().setFromObject(terreno);
    const ancho = caja.max.x - caja.min.x;
    const fondo = caja.max.z - caja.min.z;
    let alt = new Float32Array(n * n).fill(-Infinity);
    const v = new THREE.Vector3();

    terreno.traverse(function (o) {
      if (!o.isMesh || !o.geometry || !o.geometry.attributes.position) return;
      const pos = o.geometry.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        v.fromBufferAttribute(pos, i).applyMatrix4(o.matrixWorld);
        const ix = limitar(Math.floor(((v.x - caja.min.x) / ancho) * n), 0, n - 1);
        const iz = limitar(Math.floor(((v.z - caja.min.z) / fondo) * n), 0, n - 1);
        const k = iz * n + ix;
        if (v.y > alt[k]) alt[k] = v.y;
      }
    });

    // Celdas sin vértices: se rellenan con el vecino más alto.
    for (let vuelta = 0; vuelta < 64; vuelta++) {
      let vacias = 0;
      const sig = alt.slice();
      for (let z = 0; z < n; z++) {
        for (let x = 0; x < n; x++) {
          const k = z * n + x;
          if (alt[k] !== -Infinity) continue;
          let m = -Infinity;
          for (let dz = -1; dz <= 1; dz++) {
            for (let dx = -1; dx <= 1; dx++) {
              const xx = x + dx, zz = z + dz;
              if (xx >= 0 && xx < n && zz >= 0 && zz < n) m = Math.max(m, alt[zz * n + xx]);
            }
          }
          if (m === -Infinity) vacias++;
          sig[k] = m;
        }
      }
      alt = sig;
      if (!vacias) break;
    }

    const celdaX = ancho / n;
    const celdaZ = fondo / n;
    const valor = (x, z) => alt[limitar(z, 0, n - 1) * n + limitar(x, 0, n - 1)];

    return {
      caja: caja,
      altura: function (x, z) {
        const fx = (x - caja.min.x) / celdaX - 0.5;
        const fz = (z - caja.min.z) / celdaZ - 0.5;
        const x0 = Math.floor(fx), z0 = Math.floor(fz);
        const tx = limitar(fx - x0, 0, 1), tz = limitar(fz - z0, 0, 1);
        const a = valor(x0, z0), b = valor(x0 + 1, z0), c = valor(x0, z0 + 1), d = valor(x0 + 1, z0 + 1);
        return (a * (1 - tx) + b * tx) * (1 - tz) + (c * (1 - tx) + d * tx) * tz;
      },
      maximoEnRadio: function (x, z, r) {
        const cx = Math.floor((x - caja.min.x) / celdaX);
        const cz = Math.floor((z - caja.min.z) / celdaZ);
        const rx = Math.ceil(r / celdaX), rz = Math.ceil(r / celdaZ);
        let m = -Infinity;
        for (let dz = -rz; dz <= rz; dz++) {
          for (let dx = -rx; dx <= rx; dx++) {
            if ((dx * celdaX) ** 2 + (dz * celdaZ) ** 2 > r * r) continue;
            m = Math.max(m, valor(cx + dx, cz + dz));
          }
        }
        return m;
      }
    };
  }

  function dilatar(a, w) {
    return a.map((_, i) => {
      let m = -Infinity;
      for (let j = i - w; j <= i + w; j++) m = Math.max(m, a[limitar(j, 0, a.length - 1)]);
      return m;
    });
  }

  function suavizar(a, sigma) {
    const r = Math.ceil(sigma * 3);
    const k = [];
    let s = 0;
    for (let i = -r; i <= r; i++) { const w = Math.exp(-(i * i) / (2 * sigma * sigma)); k.push(w); s += w; }
    return a.map((_, i) => {
      let v = 0;
      for (let j = -r; j <= r; j++) v += a[limitar(i + j, 0, a.length - 1)] * k[j + r];
      return v / s;
    });
  }

  // ---------------------------------------------------------------------------
  // Ruta del sobrevuelo
  // ---------------------------------------------------------------------------
  function construirRuta(THREE, rejilla, aEscena, cfg) {
    const c = rejilla.caja;
    const margen = Math.min(cfg.margen, 0.25 * Math.min(c.max.x - c.min.x, c.max.z - c.min.z));
    const dentro = (p) => new THREE.Vector3(
      limitar(p.x, c.min.x + margen, c.max.x - margen), 0,
      limitar(p.z, c.min.z + margen, c.max.z - margen));

    const base = cfg.puntos.map(function (p) {
      const s = aEscena(p[0], p[1]);
      return dentro(new THREE.Vector3(s.x, 0, s.z));
    });

    // Punto extra al final, solo para que el objetivo siempre quede adelante de la cámara.
    const ultimo = base[base.length - 1];
    const direccion = ultimo.clone().sub(base[base.length - 2]).setY(0).normalize();
    const extra = ultimo.clone().addScaledVector(direccion, cfg.adelanto * 2);

    const curva = new THREE.CatmullRomCurve3(base.concat([extra]), false, "centripetal");
    curva.arcLengthDivisions = 4000;
    const curvaReal = new THREE.CatmullRomCurve3(base, false, "centripetal");
    curvaReal.arcLengthDivisions = 4000;
    const largo = curva.getLength();
    const uFin = Math.min(1, curvaReal.getLength() / largo);

    const N = cfg.muestras;
    const puntos = [], delante = [];
    for (let i = 0; i <= N; i++) {
      const u = (i / N) * uFin;
      puntos.push(curva.getPointAt(u));
      delante.push(curva.getPointAt(Math.min(1, u + cfg.adelanto / largo)));
    }

    // Altura de vuelo: envolvente del terreno alrededor de la cámara, suavizada y nunca por debajo.
    const envolvente = puntos.map((p) => rejilla.maximoEnRadio(p.x, p.z, cfg.radioSeguridad));
    let suelo = suavizar(dilatar(envolvente, 15), 10);
    suelo = suelo.map((y, i) => Math.max(y, envolvente[i]));
    suelo = suavizar(suelo, 4).map((y, i) => Math.max(y, envolvente[i]));

    const posiciones = puntos.map((p, i) => new THREE.Vector3(p.x, suelo[i] + cfg.alturaSobreTerreno, p.z));
    const yObjetivo = suavizar(delante.map((p) => rejilla.altura(p.x, p.z)), 6);
    const objetivos = delante.map((p, i) => new THREE.Vector3(p.x, yObjetivo[i], p.z));
    return { posiciones: posiciones, objetivos: objetivos };
  }

  // Aceleración y frenado suaves al inicio y al final (rampa = fracción de la duración).
  function rampa(x, r) {
    if (r <= 0) return x;
    const total = 1 - r;
    if (x < r) return (x * x) / (2 * r) / total;
    if (x > 1 - r) return 1 - ((1 - x) * (1 - x)) / (2 * r) / total;
    return (x - r / 2) / total;
  }

  function crearSobrevuelo(op) {
    const THREE = op.THREE, camara = op.camara, controles = op.controles || null;
    const cfg = Object.assign({
      puntos: RUTA_BOGOTA,
      alturaSobreTerreno: 3500, // m sobre el terreno (en la escena, con la exageración aplicada)
      adelanto: 5000,           // m: el objetivo va adelante; con 3500 m da unos 35° hacia abajo
      radioSeguridad: 2500,     // m: se considera el terreno más alto en este radio
      margen: 6000,             // m: distancia mínima a los bordes del terreno
      duracion: 90,             // s
      muestras: 900,
      segundosRampa: 4
    }, op.opciones || {});

    let curvaPos = null, curvaObj = null;
    let activo = false, t = 0, ultimo = 0, idCuadro = 0, amortiguacion = null;
    const objetivo = new THREE.Vector3();

    function recalcular() {
      const rejilla = crearRejilla(THREE, op.terreno, 256);
      const ruta = construirRuta(THREE, rejilla, op.aEscena, cfg);
      curvaPos = new THREE.CatmullRomCurve3(ruta.posiciones, false, "centripetal");
      curvaObj = new THREE.CatmullRomCurve3(ruta.objetivos, false, "centripetal");
    }

    function posicionar(segundos) {
      if (!curvaPos) recalcular();
      const x = limitar(segundos / cfg.duracion, 0, 1);
      const u = limitar(rampa(x, cfg.segundosRampa / cfg.duracion), 0, 1);
      camara.up.set(0, 1, 0);
      camara.position.copy(curvaPos.getPoint(u));
      objetivo.copy(curvaObj.getPoint(u));
      camara.lookAt(objetivo);
      camara.updateMatrixWorld();
      // Si el visor llama a controles.update() en cada cuadro, debe mirar al mismo objetivo.
      if (controles && controles.target) controles.target.copy(objetivo);
    }

    function cuadro(ahora) {
      if (!activo) return;
      const dt = ultimo ? (ahora - ultimo) / 1000 : 0;
      ultimo = ahora;
      t += Math.min(dt, 0.1);
      posicionar(t);
      if (op.alCuadro) op.alCuadro();
      if (t >= cfg.duracion) {
        detener();
        if (op.alTerminar) op.alTerminar();
        return;
      }
      idCuadro = requestAnimationFrame(cuadro);
    }

    function iniciar(desde) {
      if (!curvaPos) recalcular();
      if (camara.near > 10) camara.near = 10;
      if (camara.far < 600000) camara.far = 600000;
      camara.updateProjectionMatrix();
      t = desde || 0;
      ultimo = 0;
      activo = true;
      if (controles) {
        controles.enabled = false;
        if ("enableDamping" in controles) { amortiguacion = controles.enableDamping; controles.enableDamping = false; }
      }
      cancelAnimationFrame(idCuadro);
      idCuadro = requestAnimationFrame(cuadro);
    }

    function detener() {
      const estabaActivo = activo;
      activo = false;
      cancelAnimationFrame(idCuadro);
      if (estabaActivo && controles) {
        if (controles.target) controles.target.copy(objetivo);
        if (amortiguacion !== null) controles.enableDamping = amortiguacion;
        controles.enabled = true;
        if (controles.update) controles.update();
      }
    }

    if (op.lienzo) {
      ["pointerdown", "wheel", "touchstart"].forEach(function (ev) {
        op.lienzo.addEventListener(ev, function () {
          if (activo) { detener(); if (op.alPausar) op.alPausar(); }
        }, { passive: true });
      });
    }

    return {
      iniciar: iniciar,
      detener: detener,
      reanudar: function () { iniciar(t); },
      posicionar: posicionar,
      recalcular: recalcular,
      activo: function () { return activo; },
      duracion: function () { return cfg.duracion; },
      tiempo: function () { return t; }
    };
  }

  // ---------------------------------------------------------------------------
  // Vistas
  // ---------------------------------------------------------------------------
  function encuadre(THREE, camara, terreno, factor) {
    const caja = new THREE.Box3().setFromObject(terreno);
    const centro = caja.getCenter(new THREE.Vector3());
    const tam = caja.getSize(new THREE.Vector3());
    const radio = 0.5 * Math.hypot(tam.x, tam.z) * (factor || 1);
    const distancia = radio / Math.tan(rad(camara.fov) / 2);
    return { centro: centro, distancia: distancia };
  }

  function aplicarVista(camara, controles, posicion, objetivo) {
    camara.up.set(0, 1, 0);
    camara.position.copy(posicion);
    camara.lookAt(objetivo);
    if (controles && controles.target) {
      controles.target.copy(objetivo);
      if (controles.update) controles.update();
    }
  }

  // Vista oblicua desde el suroccidente, con toda la ciudad encuadrada.
  function vistaGeneral(op) {
    const THREE = op.THREE;
    const e = encuadre(THREE, op.camara, op.terreno, op.factor || 0.62);
    const objetivo = op.objetivo || e.centro;
    const elev = rad(op.elevacion || 48), azim = rad(op.azimut || 225);
    // Norte = −Z, Este = +X. El azimut indica desde dónde mira la cámara.
    const p = new THREE.Vector3(
      objetivo.x + e.distancia * Math.cos(elev) * Math.sin(azim),
      objetivo.y + e.distancia * Math.sin(elev),
      objetivo.z - e.distancia * Math.cos(elev) * Math.cos(azim));
    aplicarVista(op.camara, op.controles, p, objetivo);
  }

  // Vista desde arriba, con el norte hacia arriba en la pantalla.
  function vistaCenital(op) {
    const THREE = op.THREE;
    const e = encuadre(THREE, op.camara, op.terreno, op.factor || 0.55);
    const objetivo = op.objetivo || e.centro;
    const p = new THREE.Vector3(objetivo.x, objetivo.y + e.distancia, objetivo.z + e.distancia * 0.01);
    aplicarVista(op.camara, op.controles, p, objetivo);
  }

  // ---------------------------------------------------------------------------
  // Ambiente: cielo con degradado, niebla atmosférica, luz de tarde y base
  // ---------------------------------------------------------------------------
  function crearAmbiente(op) {
    const THREE = op.THREE, escena = op.escena, terreno = op.terreno;
    const fisico = Number(THREE.REVISION) >= 155 && !(op.renderer && op.renderer.useLegacyLights === true);
    const cfg = Object.assign({
      cenit: 0x5a86b0,
      horizonte: 0xd5dee0,
      bajoHorizonte: 0xaab5ad,
      base: 0x8d9a8b,
      azimutSol: 285,   // grados desde el norte: sol de tarde desde el occidente
      elevacionSol: 30,
      intensidadSol: fisico ? 2.0 : 0.8,
      intensidadRelleno: fisico ? 0.9 : 0.5,
      niebla: true
    }, op.opciones || {});

    const grupo = new THREE.Group();
    grupo.name = "ambiente";
    escena.add(grupo);

    function asegurarMaterial() {
      const anisotropia = op.renderer && op.renderer.capabilities ? op.renderer.capabilities.getMaxAnisotropy() : 1;
      terreno.traverse(function (o) {
        if (!o.isMesh) return;
        if (!o.geometry.attributes.normal) o.geometry.computeVertexNormals();
        const lista = Array.isArray(o.material) ? o.material : [o.material];
        const nuevos = lista.map(function (m) {
          if (!m) return m;
          if (m.map) m.map.anisotropy = anisotropia;
          if (m.isMeshBasicMaterial) {
            const s = new THREE.MeshStandardMaterial({ map: m.map, color: 0xffffff, roughness: 1, metalness: 0 });
            m.dispose();
            return s;
          }
          if (m.isMeshStandardMaterial) { m.roughness = 1; m.metalness = 0; }
          return m;
        });
        o.material = Array.isArray(o.material) ? nuevos : nuevos[0];
      });
    }

    // Color promedio de la textura del terreno, para que la base continúe el paisaje sin cortes.
    function colorPromedio() {
      let resultado = null;
      terreno.traverse(function (o) {
        if (resultado || !o.isMesh) return;
        const m = Array.isArray(o.material) ? o.material[0] : o.material;
        const img = m && m.map && m.map.image;
        if (!img || !(img.width || img.videoWidth)) return;
        try {
          const c = document.createElement("canvas");
          c.width = c.height = 16;
          const g = c.getContext("2d");
          g.drawImage(img, 0, 0, 16, 16);
          const d = g.getImageData(0, 0, 16, 16).data;
          let r = 0, gg = 0, b = 0;
          for (let i = 0; i < d.length; i += 4) { r += d[i]; gg += d[i + 1]; b += d[i + 2]; }
          const n = d.length / 4;
          resultado = (Math.round(r / n * 0.9) << 16) | (Math.round(gg / n * 0.9) << 8) | Math.round(b / n * 0.9);
        } catch (e) { /* textura de otro origen: se usa el color por defecto */ }
      });
      return resultado;
    }

    function vaciar() {
      for (let i = grupo.children.length - 1; i >= 0; i--) {
        const h = grupo.children[i];
        grupo.remove(h);
        if (h.geometry) h.geometry.dispose();
        if (h.material) h.material.dispose();
      }
    }

    function construir() {
      vaciar();
      asegurarMaterial();
      terreno.updateMatrixWorld(true);
      const caja = new THREE.Box3().setFromObject(terreno);
      const centro = caja.getCenter(new THREE.Vector3());
      const tam = caja.getSize(new THREE.Vector3());
      const diag = Math.hypot(tam.x, tam.z);

      if (op.camara) {
        op.camara.far = Math.max(op.camara.far, diag * 7);
        op.camara.updateProjectionMatrix();
      }

      // Cielo: degradado de cénit a horizonte, con una franja de bruma bajo el horizonte.
      const cielo = new THREE.Mesh(
        new THREE.SphereGeometry(diag * 5, 48, 24),
        new THREE.ShaderMaterial({
          side: THREE.BackSide,
          depthWrite: false,
          fog: false,
          toneMapped: false,
          uniforms: {
            cenit: { value: new THREE.Vector3().fromArray(srgb(cfg.cenit)) },
            horizonte: { value: new THREE.Vector3().fromArray(srgb(cfg.horizonte)) },
            bajo: { value: new THREE.Vector3().fromArray(srgb(cfg.bajoHorizonte)) }
          },
          vertexShader:
            "varying vec3 vDir;\n" +
            "void main() {\n" +
            "  vDir = normalize(position);\n" +
            "  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);\n" +
            "}",
          fragmentShader:
            "uniform vec3 cenit;\nuniform vec3 horizonte;\nuniform vec3 bajo;\nvarying vec3 vDir;\n" +
            "void main() {\n" +
            "  float h = vDir.y;\n" +
            "  vec3 c = h >= 0.0 ? mix(horizonte, cenit, pow(clamp(h * 1.6, 0.0, 1.0), 0.7))\n" +
            "                    : mix(horizonte, bajo, clamp(-h * 6.0, 0.0, 1.0));\n" +
            "  gl_FragColor = vec4(c, 1.0);\n" +
            "}"
        }));
      cielo.position.copy(centro);
      cielo.frustumCulled = false;
      cielo.renderOrder = -1;
      cielo.userData.ignorarEnPruebas = true;

      // Base: llanura amplia bajo el terreno que se funde con la niebla del horizonte.
      const base = new THREE.Mesh(
        new THREE.PlaneGeometry(diag * 9, diag * 9),
        new THREE.MeshStandardMaterial({ color: colorPromedio() ?? cfg.base, roughness: 1, metalness: 0 }));
      base.rotation.x = -Math.PI / 2;
      base.position.set(centro.x, caja.min.y - 5, centro.z);
      base.userData.ignorarEnPruebas = true;

      // Luz de tarde desde el occidente: ilumina la cara de los cerros orientales que mira a la ciudad.
      const sol = new THREE.DirectionalLight(0xfff0d8, cfg.intensidadSol);
      const az = rad(cfg.azimutSol), el = rad(cfg.elevacionSol), d = diag * 2;
      sol.position.set(
        centro.x + d * Math.cos(el) * Math.sin(az),
        centro.y + d * Math.sin(el),
        centro.z - d * Math.cos(el) * Math.cos(az));
      sol.target.position.copy(centro);
      const relleno = new THREE.HemisphereLight(0xcfe3f2, 0x4a5a48, cfg.intensidadRelleno);

      grupo.add(cielo, base, sol, sol.target, relleno);

      escena.background = new THREE.Color(cfg.horizonte);
      escena.fog = cfg.niebla ? new THREE.Fog(cfg.horizonte, diag * 0.32, diag * 1.45) : null;
    }

    construir();
    return { recalcular: construir, grupo: grupo };
  }

  global.Bogota3D = Object.assign(global.Bogota3D || {}, {
    RUTA_BOGOTA: RUTA_BOGOTA,
    // Alturas del terreno tal como se dibuja (con exageración): úsalo para ubicar etiquetas y
    // edificaciones. Vuelve a crearlo cada vez que cambie la exageración.
    alturas: function (THREE, terreno) { return crearRejilla(THREE, terreno, 512); },
    crearAmbiente: crearAmbiente,
    crearSobrevuelo: crearSobrevuelo,
    vistaGeneral: vistaGeneral,
    vistaCenital: vistaCenital
  });
})(typeof window !== "undefined" ? window : globalThis);
