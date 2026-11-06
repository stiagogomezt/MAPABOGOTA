/*
 * bogota3d_terreno.js
 * Construye la malla del terreno a partir de terreno/alturas.bin y terreno/terreno.json
 * (generados por scripts/generar_terreno.py) y concentra TODA la georreferenciación del visor:
 *   EPSG:9377 <-> escena <-> WGS84, y la altitud real (sin exageración).
 *
 * Funciona con three.js r128 o superior. Expone Bogota3D.cargarTerreno y Bogota3D.proyeccion
 * (se puede cargar antes o después de bogota3d_camara.js).
 *
 *   const t = await Bogota3D.cargarTerreno({ THREE, base: "terreno/", renderer, exageracion: 1.6 });
 *   escena.add(t.grupo);              // malla del terreno + costados de la maqueta
 *   t.aEscena(este, norte)            // -> {x, z}
 *   t.puntoEscena(este, norte, sobre) // -> THREE.Vector3 sobre el terreno (+ "sobre" metros)
 *   t.consultar(puntoDelRaycast)      // -> ficha {epsg9377:{E,N}, wgs84:{lat,lon}, altitud}
 *   t.alturaReal(este, norte)         // m s.n.m., sin exageración
 *   t.fijarExageracion(1.6)           // luego: ambiente.recalcular(); vuelo.recalcular();
 *   await t.fijarTextura(url)         // texturas temáticas con la MISMA extensión
 *
 * Convención de la escena: Este → +X, Norte → −Z, altura → +Y.
 * y = (altitud − nivelReferencia) × exageración.
 */
(function (global) {
  "use strict";

  // ---------------------------------------------------------------------------
  // EPSG:9377, MAGNA-SIRGAS / Origen-Nacional: Transversa de Mercator sobre GRS80
  // lat0 = 4°, lon0 = −73°, k0 = 0,9992, FE = 5.000.000, FN = 2.000.000
  // ---------------------------------------------------------------------------
  const A = 6378137, F = 1 / 298.257222101, E2 = F * (2 - F), EP2 = E2 / (1 - E2);
  const RAD = Math.PI / 180;
  const LAT0 = 4 * RAD, LON0 = -73 * RAD, K0 = 0.9992, FE = 5000000, FN = 2000000;

  function arcoMeridiano(phi) {
    const e4 = E2 * E2, e6 = e4 * E2;
    return A * ((1 - E2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi
      - (3 * E2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * Math.sin(2 * phi)
      + (15 * e4 / 256 + 45 * e6 / 1024) * Math.sin(4 * phi)
      - (35 * e6 / 3072) * Math.sin(6 * phi));
  }
  const M0 = arcoMeridiano(LAT0);

  function desdeWGS84(lat, lon) {
    const phi = lat * RAD, lam = lon * RAD;
    const s = Math.sin(phi), c = Math.cos(phi), t = Math.tan(phi);
    const N = A / Math.sqrt(1 - E2 * s * s);
    const T = t * t, C = EP2 * c * c, Aa = (lam - LON0) * c;
    const M = arcoMeridiano(phi);
    const este = FE + K0 * N * (Aa + (1 - T + C) * Aa ** 3 / 6
      + (5 - 18 * T + T * T + 72 * C - 58 * EP2) * Aa ** 5 / 120);
    const norte = FN + K0 * (M - M0 + N * t * (Aa * Aa / 2 + (5 - T + 9 * C + 4 * C * C) * Aa ** 4 / 24
      + (61 - 58 * T + T * T + 600 * C - 330 * EP2) * Aa ** 6 / 720));
    return { E: este, N: norte };
  }

  function aWGS84(este, norte) {
    const M = M0 + (norte - FN) / K0;
    const mu = M / (A * (1 - E2 / 4 - 3 * E2 * E2 / 64 - 5 * E2 ** 3 / 256));
    const e1 = (1 - Math.sqrt(1 - E2)) / (1 + Math.sqrt(1 - E2));
    const phi1 = mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * Math.sin(2 * mu)
      + (21 * e1 * e1 / 16 - 55 * e1 ** 4 / 32) * Math.sin(4 * mu)
      + (151 * e1 ** 3 / 96) * Math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * Math.sin(8 * mu);
    const s = Math.sin(phi1), c = Math.cos(phi1), t = Math.tan(phi1);
    const C1 = EP2 * c * c, T1 = t * t;
    const N1 = A / Math.sqrt(1 - E2 * s * s);
    const R1 = A * (1 - E2) / Math.pow(1 - E2 * s * s, 1.5);
    const D = (este - FE) / (N1 * K0);
    const lat = phi1 - (N1 * t / R1) * (D * D / 2
      - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * EP2) * D ** 4 / 24
      + (61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * EP2 - 3 * C1 * C1) * D ** 6 / 720);
    const lon = LON0 + (D - (1 + 2 * T1 + C1) * D ** 3 / 6
      + (5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * EP2 + 24 * T1 * T1) * D ** 5 / 120) / c;
    return { lat: lat / RAD, lon: lon / RAD };
  }

  // ---------------------------------------------------------------------------
  function cargarImagen(THREE, url, renderer) {
    return new Promise(function (resolver, rechazar) {
      new THREE.TextureLoader().load(url, function (tex) {
        if ("colorSpace" in tex && THREE.SRGBColorSpace) tex.colorSpace = THREE.SRGBColorSpace;
        else if (THREE.sRGBEncoding !== undefined) tex.encoding = THREE.sRGBEncoding;
        if (renderer && renderer.capabilities) tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
        resolver(tex);
      }, undefined, function () { rechazar(new Error("No se pudo cargar la textura " + url)); });
    });
  }

  async function cargarTerreno(op) {
    const THREE = op.THREE;
    const base = (op.base || "terreno/").replace(/\/?$/, "/");
    const resp = await fetch(base + "terreno.json");
    if (!resp.ok) throw new Error("No se encontró " + base + "terreno.json");
    const meta = await resp.json();
    const datosResp = await fetch(base + "alturas.bin");
    if (!datosResp.ok) throw new Error("No se encontró " + base + "alturas.bin");
    const datos = new Float32Array(await datosResp.arrayBuffer());
    const W = meta.ancho, H = meta.alto;
    if (datos.length !== W * H) {
      throw new Error(`alturas.bin tiene ${datos.length} valores y terreno.json indica ${W}x${H}`);
    }
    if (op.alProgreso) op.alProgreso(0.4);

    const E0 = (meta.este_min + meta.este_max) / 2;
    const N0 = (meta.norte_min + meta.norte_max) / 2;
    const nivelReferencia = Math.floor(meta.altura_min / 100) * 100;
    let exageracion = op.exageracion || 1.6;

    const movil = typeof matchMedia !== "undefined" && matchMedia("(max-width: 700px)").matches;
    const salto = op.salto || (movil ? 2 : 1);
    const w = Math.floor((W - 1) / salto) + 1;
    const h = Math.floor((H - 1) / salto) + 1;

    // Geometría: un vértice por muestra (registro en centro de celda)
    const posiciones = new Float32Array(w * h * 3);
    const uvs = new Float32Array(w * h * 2);
    const origenDato = new Uint32Array(w * h);
    for (let j = 0; j < h; j++) {
      for (let i = 0; i < w; i++) {
        const ci = i * salto, cj = j * salto, k = j * w + i;
        const este = meta.este_min + (ci + 0.5) * meta.paso_x;
        const norte = meta.norte_max - (cj + 0.5) * meta.paso_y;
        origenDato[k] = cj * W + ci;
        posiciones[k * 3] = este - E0;
        posiciones[k * 3 + 1] = (datos[cj * W + ci] - nivelReferencia) * exageracion;
        posiciones[k * 3 + 2] = -(norte - N0);
        uvs[k * 2] = (ci + 0.5) / W;
        uvs[k * 2 + 1] = 1 - (cj + 0.5) / H;
      }
    }
    const indices = new Uint32Array((w - 1) * (h - 1) * 6);
    let n = 0;
    for (let j = 0; j < h - 1; j++) {
      for (let i = 0; i < w - 1; i++) {
        const a = j * w + i, b = a + 1, c = a + w, d = c + 1;
        indices[n++] = a; indices[n++] = c; indices[n++] = b;
        indices[n++] = b; indices[n++] = c; indices[n++] = d;
      }
    }
    const geometria = new THREE.BufferGeometry();
    geometria.setAttribute("position", new THREE.BufferAttribute(posiciones, 3));
    geometria.setAttribute("uv", new THREE.BufferAttribute(uvs, 2));
    geometria.setIndex(new THREE.BufferAttribute(indices, 1));
    geometria.computeVertexNormals();
    geometria.computeBoundingBox();
    geometria.computeBoundingSphere();

    const grande = op.renderer && op.renderer.capabilities && op.renderer.capabilities.maxTextureSize >= 8192 && !movil;
    const archivoTextura = op.textura || (meta.textura ? meta.textura[grande ? "8192" : "4096"] : null);
    const material = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 1, metalness: 0 });
    if (archivoTextura) material.map = await cargarImagen(THREE, base + archivoTextura, op.renderer);
    if (op.alProgreso) op.alProgreso(0.9);

    const malla = new THREE.Mesh(geometria, material);
    malla.name = "terreno";
    const grupo = new THREE.Group();
    grupo.name = "terreno-maqueta";
    grupo.add(malla);

    // Costados de la maqueta: color sólido en lugar de textura estirada.
    const costados = new THREE.Mesh(new THREE.BufferGeometry(),
      new THREE.MeshStandardMaterial({ color: 0x2b3337, roughness: 1, metalness: 0, side: THREE.DoubleSide }));
    costados.name = "terreno-costados";
    grupo.add(costados);

    function construirCostados() {
      const fondo = -150 * exageracion;
      const bordes = [];
      for (let i = 0; i < w; i++) bordes.push(i);                         // norte
      for (let j = 1; j < h; j++) bordes.push(j * w + (w - 1));           // este
      for (let i = w - 2; i >= 0; i--) bordes.push((h - 1) * w + i);      // sur
      for (let j = h - 2; j > 0; j--) bordes.push(j * w);                 // oeste
      bordes.push(0);
      const pos = new Float32Array(bordes.length * 6);
      bordes.forEach(function (k, m) {
        pos[m * 6] = posiciones[k * 3]; pos[m * 6 + 1] = posiciones[k * 3 + 1]; pos[m * 6 + 2] = posiciones[k * 3 + 2];
        pos[m * 6 + 3] = posiciones[k * 3]; pos[m * 6 + 4] = fondo; pos[m * 6 + 5] = posiciones[k * 3 + 2];
      });
      const idx = [];
      for (let m = 0; m < bordes.length - 1; m++) {
        const a = m * 2, b = a + 1, c = a + 2, d = a + 3;
        idx.push(a, b, c, c, b, d);
      }
      costados.geometry.dispose();
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      g.setIndex(idx);
      g.computeVertexNormals();
      costados.geometry = g;
    }
    construirCostados();

    function alturaReal(este, norte) {
      const fi = (este - meta.este_min) / meta.paso_x - 0.5;
      const fj = (meta.norte_max - norte) / meta.paso_y - 0.5;
      const i0 = Math.max(0, Math.min(W - 1, Math.floor(fi)));
      const j0 = Math.max(0, Math.min(H - 1, Math.floor(fj)));
      const i1 = Math.min(W - 1, i0 + 1), j1 = Math.min(H - 1, j0 + 1);
      const tx = Math.max(0, Math.min(1, fi - i0)), ty = Math.max(0, Math.min(1, fj - j0));
      const a = datos[j0 * W + i0], b = datos[j0 * W + i1], c = datos[j1 * W + i0], d = datos[j1 * W + i1];
      return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty;
    }

    const api = {
      grupo: grupo,
      malla: malla,
      meta: meta,
      nivelReferencia: nivelReferencia,
      exageracion: function () { return exageracion; },
      aEscena: function (este, norte) { return { x: este - E0, z: -(norte - N0) }; },
      aEPSG9377: function (x, z) { return { E: x + E0, N: -z + N0 }; },
      aWGS84: aWGS84,
      desdeWGS84: desdeWGS84,
      alturaReal: alturaReal,
      alturaEscena: function (este, norte) { return (alturaReal(este, norte) - nivelReferencia) * exageracion; },
      puntoEscena: function (este, norte, sobre) {
        return new THREE.Vector3(este - E0, (alturaReal(este, norte) - nivelReferencia) * exageracion + (sobre || 0), -(norte - N0));
      },
      dentro: function (este, norte) {
        return este >= meta.este_min && este <= meta.este_max && norte >= meta.norte_min && norte <= meta.norte_max;
      },
      // Ficha a partir del punto que devuelve un raycast sobre la malla del terreno.
      consultar: function (punto) {
        const E = punto.x + E0, N = -punto.z + N0;
        const g = aWGS84(E, N);
        return { epsg9377: { E: E, N: N }, wgs84: { lat: g.lat, lon: g.lon }, altitud: alturaReal(E, N) };
      },
      fijarExageracion: function (factor) {
        exageracion = factor;
        for (let k = 0; k < w * h; k++) posiciones[k * 3 + 1] = (datos[origenDato[k]] - nivelReferencia) * exageracion;
        geometria.attributes.position.needsUpdate = true;
        geometria.computeVertexNormals();
        geometria.computeBoundingBox();
        geometria.computeBoundingSphere();
        construirCostados();
      },
      fijarTextura: async function (url) {
        const tex = await cargarImagen(THREE, url, op.renderer);
        if (material.map) material.map.dispose();
        material.map = tex;
        material.needsUpdate = true;
      }
    };
    if (op.alProgreso) op.alProgreso(1);
    return api;
  }

  global.Bogota3D = global.Bogota3D || {};
  global.Bogota3D.cargarTerreno = cargarTerreno;
  global.Bogota3D.proyeccion = { desdeWGS84: desdeWGS84, aWGS84: aWGS84 };
})(typeof window !== "undefined" ? window : globalThis);
