const modelPath = 'media/Centro_Historico_La_Candelaria.glb';
const viewer = document.getElementById('model-viewer');
const placeholder = document.getElementById('model-message');
const status = document.getElementById('model-status');

async function loadCityModel() {
  try {
    const manifestResponse = await fetch('manifest.json');
    if (!manifestResponse.ok) {
      status.textContent = 'Modelo pendiente de publicación';
      return;
    }
    const manifest = await manifestResponse.json();
    if (!(manifest.media || []).includes(modelPath)) {
      status.textContent = 'Modelo pendiente de publicación';
      return;
    }

    const THREE = await import('three');
    const [{ GLTFLoader }, { OrbitControls }] = await Promise.all([
      import('three/addons/loaders/GLTFLoader.js'),
      import('three/addons/controls/OrbitControls.js'),
    ]);
    const width = Math.max(1, viewer.clientWidth);
    const height = Math.max(1, viewer.clientHeight);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#111b20');
    scene.fog = new THREE.Fog('#111b20', 22, 65);

    const camera = new THREE.PerspectiveCamera(38, width / height, 0.01, 1000);
    camera.position.set(12, 9, 15);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'low-power' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));
    renderer.setSize(width, height);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    viewer.appendChild(renderer.domElement);

    scene.add(new THREE.HemisphereLight('#c8dfdc', '#273329', 2.1));
    const key = new THREE.DirectionalLight('#ffd0a1', 3.4);
    key.position.set(-8, 14, 8);
    scene.add(key);
    const fill = new THREE.DirectionalLight('#8ab6c0', 1.2);
    fill.position.set(10, 5, -10);
    scene.add(fill);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.minDistance = 4;
    controls.maxDistance = 32;
    controls.maxPolarAngle = Math.PI * 0.49;
    const loader = new GLTFLoader();
    loader.load(modelPath, gltf => {
      const model = gltf.scene;
      const bounds = new THREE.Box3().setFromObject(model);
      const center = bounds.getCenter(new THREE.Vector3());
      const size = bounds.getSize(new THREE.Vector3());
      model.position.sub(center);
      const largest = Math.max(size.x, size.y, size.z) || 1;
      model.scale.setScalar(12 / largest);
      scene.add(model);
      camera.position.set(12, 9, 15);
      controls.target.set(0, 0, 0);
      controls.update();
      placeholder.classList.add('hidden');
      status.textContent = 'Modelo listo · Draco / glTF';
    }, undefined, error => {
      console.error('No se pudo cargar el modelo GLB:', error);
      status.textContent = 'No se pudo abrir el GLB';
    });

    const resizeObserver = new ResizeObserver(() => {
      const nextWidth = Math.max(1, viewer.clientWidth);
      const nextHeight = Math.max(1, viewer.clientHeight);
      camera.aspect = nextWidth / nextHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(nextWidth, nextHeight);
    });
    resizeObserver.observe(viewer);
    let animationFrame;
    const render = () => {
      animationFrame = requestAnimationFrame(render);
      controls.update();
      renderer.render(scene, camera);
    };
    render();
    window.addEventListener('pagehide', () => {
      cancelAnimationFrame(animationFrame);
      resizeObserver.disconnect();
      controls.dispose();
      renderer.dispose();
    }, { once: true });
  } catch (error) {
    console.error('El visor GLB requiere WebGL y conexión al CDN de three.js:', error);
    status.textContent = 'Visor 3D no disponible en este navegador';
  }
}

loadCityModel();
