// portada.js
const portada = {
  _el: null,
  _ready: false,
  init() {
    this._el = document.getElementById('portada');
  },
  progreso(frac) {
    const fill = document.getElementById('portadaFill');
    if (fill) fill.style.width = (frac * 100) + '%';
  },
  listo() {
    this._ready = true;
    const btns = document.getElementById('portadaBtns');
    if (btns) btns.style.opacity = '1';
  },
  cargarPerfil(datos) {
    const el = document.getElementById('portadaPerfil');
    if (!el) return;
    if (datos && datos.ilustrativo === false && datos.puntos) {
      el.textContent = 'Perfil real del MDT — ' + datos.puntos.length + ' puntos';
      const ill = document.getElementById('portadaIlustrativo');
      if (ill) ill.style.display = 'none';
    }
  },
  cerrar() {
    const el = this._el || document.getElementById('portada');
    if (el) { el.style.opacity = '0'; setTimeout(() => { el.style.display = 'none'; }, 800); }
  },
  alExplorar(cb) { if (cb) cb(); this.cerrar(); },
  alSobrevolar(cb) { if (cb) cb(); this.cerrar(); },
};
window.portada = portada;
document.addEventListener('DOMContentLoaded', () => portada.init());