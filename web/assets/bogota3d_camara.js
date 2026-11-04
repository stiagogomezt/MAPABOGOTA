// bogota3d_camara.js - ambiente y sobrevuelo para el visor 3D de Bogota
const Bogota3D = (function () {
  function crearAmbiente({ THREE, escena, terreno, renderer, camara }) {
    // sky color
    escena.background = new THREE.Color(0x87a8c4);
    escena.fog = new THREE.Fog(0x87a8c4, 30000, 100000);
    // hemisphere light
    const hemi = new THREE.HemisphereLight(0xcfe3f2, 0x3a4a3f, 0.6);
    escena.add(hemi);
    // directional sun
    const sun = new THREE.DirectionalLight(0xffffff, 1.2);
    sun.position.set(10000, -10000, 5000);
    sun.castShadow = true;
    sun.shadow.mapSize.width = 2048;
    sun.shadow.mapSize.height = 2048;
    sun.shadow.bias = -0.001;
    sun.shadow.normalBias = 0.02;
    escena.add(sun);
    escena.add(new THREE.AmbientLight(0xffffff, 0.3));
    // base plane
    const baseGeo = new THREE.PlaneGeometry(200000, 200000);
    const baseMat = new THREE.MeshStandardMaterial({ color: 0x1f2a2e });
    const basePlane = new THREE.Mesh(baseGeo, baseMat);
    basePlane.rotation.x = -Math.PI / 2;
    basePlane.position.y = -50;
    basePlane.receiveShadow = true;
    escena.add(basePlane);

    return {
      recalcular() {
        // re-apply exaggeration is handled by caller on mesh
      },
    };
  }

  function alturas(THREE, terreno) {
    const raycaster = new THREE.Raycaster();
    return {
      altura(x, z) {
        const origin = new THREE.Vector3(x, 100000, z);
        raycaster.set(origin, new THREE.Vector3(0, -1, 0));
        const hits = raycaster.intersectObject(terreno);
        if (hits.length > 0) return hits[0].point.y;
        return 0;
      },
    };
  }

  function vistaGeneral({ THREE, camara, controles, terreno }) {
    camara.position.set(-30000, 20000, 30000);
    camara.lookAt(0, 0, 0);
    if (controles) { controles.target.set(0, 0, 0); controles.update(); }
  }

  function vistaCenital({ THREE, camara, controles, terreno }) {
    camara.position.set(0, 50000, 0);
    camara.lookAt(0, 0, 0);
    if (controles) { controles.target.set(0, 0, 0); controles.update(); }
  }

  function crearSobrevuelo({ THREE, camara, controles, terreno, aEscena, lienzo, alCuadro, alTerminar, alPausar }) {
    let playing = false;
    let t = 0;
    let last = 0;
    let curvePos = null;
    let curveTgt = null;
    let duration = 70;

    // load trajectory
    fetch('terrain/camera_path.json').then(r => r.json()).then(data => {
      const pts = data.map(p => new THREE.Vector3(p.position[0], p.position[1], p.position[2]));
      const tgs = data.map(p => new THREE.Vector3(p.target[0], p.target[1], p.target[2]));
      curvePos = new THREE.CatmullRomCurve3(pts);
      curveTgt = new THREE.CatmullRomCurve3(tgs);
      duration = data[data.length - 1].t;
    });

    function iniciar() {
      playing = true;
      t = 0;
      last = performance.now();
      if (controles) controles.enabled = false;
    }
    function reanudar() {
      playing = true;
      last = performance.now();
      if (controles) controles.enabled = false;
    }
    function recalcular() {
      // recompute height offset if needed
    }

    function step(now) {
      if (playing && curvePos && curveTgt) {
        const dt = (now - last) / 1000;
        last = now;
        t = Math.min(t + dt, duration);
        const u = t / duration;
        const pos = curvePos.getPointAt(u);
        const tgt = curveTgt.getPointAt(u);
        camara.position.copy(pos);
        camara.lookAt(tgt);
        if (alCuadro) alCuadro();
        if (t >= duration) {
          playing = false;
          if (alTerminar) alTerminar();
          if (controles) controles.enabled = true;
        }
      }
      // detect user drag -> pause
      // (handled by lienzo pointerdown)
      requestAnimationFrame(step);
    }
    requestAnimationFrame(step);

    // pause on user interaction
    lienzo.addEventListener('pointerdown', () => {
      if (playing) {
        playing = false;
        if (alPausar) alPausar();
      }
    });

    return { iniciar, reanudar, recalcular };
  }

  return { crearAmbiente, crearSobrevuelo, vistaGeneral, vistaCenital, alturas };
})();

window.Bogota3D = Bogota3D;