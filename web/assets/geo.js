// geo.js - coordinate conversion, delegates to terrain module
window.geo = {
  _t: null,
  setTerreno(t) { this._t = t; },
  glbToEpsg(glbX, glbZ) { return this._t ? this._t.aEPSG9377(glbX, glbZ) : { E: glbX + 4877500, N: 2072500 - glbZ }; },
  epsgToGlb(epsgX, epsgY) { return this._t ? this._t.aEscena(epsgX, epsgY) : { x: epsgX - 4877500, z: 2072500 - epsgY }; },
  alturaTerreno(x, z) { return this._t ? this._t.alturaReal(x, z) : 0; },
  aEscena(este, norte) { return this._t ? this._t.aEscena(este, norte) : { x: este - 4877500, z: 2072500 - norte }; },
  aEPSG9377(x, z) { return this._t ? this._t.aEPSG9377(x, z) : { E: x + 4877500, N: 2072500 - z }; },
  aWGS84(e, n) { return this._t ? this._t.aWGS84(e, n) : null; },
};