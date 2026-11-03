// geo.js - coordinate conversion and terrain height
// Convention: East -> +X, North -> -Z, Height -> +Y (three.js, Y up)
// camera.up = (0,1,0)

import * as THREE from 'three';

const AOI_CENTER = { x: 0, z: 0 }; // terrain centered at origin in GLB space
const EPSG_OFFSET = { x: 4877500, y: 2072500 }; // EPSG:9377 center

export function glbToEpsg(glbX, glbZ) {
  return { x: glbX + EPSG_OFFSET.x, y: EPSG_OFFSET.y - glbZ };
}

export function epsgToGlb(epsgX, epsgY) {
  return { x: epsgX - EPSG_OFFSET.x, z: EPSG_OFFSET.y - epsgY };
}

export function alturaTerreno(terrainMesh, x, z, exag) {
  if (!terrainMesh) return 0;
  // raycast downward from above
  const raycaster = new THREE.Raycaster();
  const origin = new THREE.Vector3(x, 100000, z);
  const dir = new THREE.Vector3(0, -1, 0);
  raycaster.set(origin, dir);
  const hits = raycaster.intersectObject(terrainMesh);
  if (hits.length > 0) {
    return hits[0].point.y / exag;
  }
  return 0;
}

export { THREE };