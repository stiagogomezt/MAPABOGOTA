(() => {
  'use strict';

  const BOGOTA = [-74.0721, 4.711];
  const STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty';
  const PMTILES = {
    blocks: { url: 'descargas/pmtiles/manzanas_indicadores.pmtiles', sourceLayer: 'manzanas_indicadores' },
    ecology: { url: 'descargas/pmtiles/estructura_ecologica.pmtiles', sourceLayer: 'estructura_ecologica' },
    waterbodies: { url: 'descargas/pmtiles/cuerpo_agua.pmtiles', sourceLayer: 'cuerpo_agua' },
    streams: { url: 'descargas/pmtiles/corriente_agua.pmtiles', sourceLayer: 'corriente_agua' },
    roads: { url: 'descargas/pmtiles/malla_vial.pmtiles', sourceLayer: 'malla_vial' },
    lots: { url: 'descargas/pmtiles/lote.pmtiles', sourceLayer: 'lote' },
    buildings: { url: 'descargas/pmtiles/construcciones_3d.pmtiles', sourceLayer: 'construcciones_3d' },
  };
  const PROPERTY = {
    height: 'altura_est_m',
    value: 'valor_ref_m2',
    stratum: 'estrato',
    construction: 'indice_construccion',
  };
  const VIEWPOINTS = [
    ['Usaquén', -74.030, 4.747], ['Chapinero', -74.055, 4.648],
    ['Santa Fe', -74.060, 4.603], ['San Cristóbal', -74.073, 4.548],
    ['Usme', -74.105, 4.480], ['Tunjuelito', -74.133, 4.570],
    ['Bosa', -74.190, 4.612], ['Kennedy', -74.150, 4.635],
    ['Fontibón', -74.145, 4.680], ['Engativá', -74.105, 4.710],
    ['Suba', -74.080, 4.770], ['Barrios Unidos', -74.075, 4.665],
    ['Teusaquillo', -74.085, 4.635], ['Los Mártires', -74.090, 4.605],
    ['Antonio Nariño', -74.105, 4.590], ['Puente Aranda', -74.115, 4.615],
    ['La Candelaria', -74.072, 4.597], ['Rafael Uribe Uribe', -74.112, 4.565],
    ['Ciudad Bolívar', -74.165, 4.535], ['Sumapaz', -74.300, 4.155],
  ];
  const LAYER_GROUPS = {
    buildings: ['buildings-extrusion', 'buildings-outline'],
    blocks: ['blocks-fill', 'blocks-outline'],
    lots: ['lots-fill', 'lots-outline'],
    ecology: ['ecology-fill', 'ecology-outline'],
    roads: ['roads-line'],
    water: ['water-line', 'waterbody-fill'],
    admin: ['locality-line', 'upl-line'],
  };
  const statusText = document.getElementById('map-status');
  const statusDot = document.querySelector('.status-dot');
  const localityData = new Map();
  let siteManifest = { pmtiles: [], geojson: [], media: [] };
  let map;
  let terrainOn = true;
  let activeTheme = 'height';
  let flyIndex = 0;
  let flightRunning = false;
  let flightPaused = false;
  let flightTimer = null;

  function setStatus(text, state = 'ready') {
    statusText.textContent = text;
    statusDot.classList.toggle('ready', state === 'ready');
    statusDot.classList.toggle('error', state === 'error');
  }

  function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[char]);
  }

  function numberFormat(value, digits = 1) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return 'Sin dato';
    return new Intl.NumberFormat('es-CO', { maximumFractionDigits: digits }).format(numeric);
  }

  function numericRamp(property, stops) {
    const value = ['coalesce', ['to-number', ['get', property]], 0];
    return ['interpolate', ['linear'], value, ...stops.flatMap(([stop, color]) => [stop, color])];
  }

  function themeExpression(theme) {
    if (theme === 'height') return numericRamp('altura_est_m', [[0, '#596e7b'], [12, '#72a9a2'], [30, '#e5b16e'], [75, '#df7956'], [160, '#b94448']]);
    if (theme === 'value') return numericRamp('valor_ref_m2', [[0, '#536a7a'], [500000, '#679895'], [1500000, '#b1b574'], [3000000, '#e5a15f'], [6000000, '#ce5e4e']]);
    if (theme === 'construction') return numericRamp('indice_construccion', [[0, '#536a7a'], [0.5, '#659891'], [1.5, '#b4b574'], [3, '#e5a15f'], [6, '#ce5e4e']]);
    return ['match', ['to-string', ['get', 'estrato']],
      '1', '#547d9a', '2', '#5fa9a0', '3', '#9dbb77', '4', '#edbf6e', '5', '#e78e5e', '6', '#d65d58', '#879394'];
  }

  function buildingThemeExpression(theme) {
    if (theme === 'height') return themeExpression(theme);
    const property = PROPERTY[theme];
    return ['case', ['has', property], themeExpression(theme), themeExpression('height')];
  }

  function setLayerVisibility(group, visible) {
    for (const id of LAYER_GROUPS[group] || []) {
      if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
    }
  }

  function legendMarkup(theme) {
    const definitions = {
      height: { title: 'Altura estimada · metros', labels: ['0 m', '12 m', '30 m', '75 m', '160 m+'] },
      value: { title: 'Valor de referencia del suelo · COP/m²', labels: ['$0', '$0,5 M', '$1,5 M', '$3 M', '$6 M+'] },
      construction: { title: 'Índice de construcción · área construida / manzana', labels: ['0', '0,5', '1,5', '3', '6+'] },
    };
    const colors = ['#536a7a', '#679895', '#b1b574', '#e5a15f', '#ce5e4e'];
    const root = document.getElementById('legend');
    if (theme === 'stratum') {
      const classes = [['1', '#547d9a'], ['2', '#5fa9a0'], ['3', '#9dbb77'], ['4', '#edbf6e'], ['5', '#e78e5e'], ['6', '#d65d58']];
      root.innerHTML = '<span class="legend-title">Estrato socioeconómico</span><div class="legend-categories">' + classes.map(([label, color]) => `<span class="legend-category"><i style="background:${color}"></i>Estrato ${label}</span>`).join('') + '</div>';
      return;
    }
    const definition = definitions[theme];
    root.innerHTML = `<span class="legend-title">${definition.title}</span><div class="legend-gradient" style="background:linear-gradient(90deg,${colors.join(',')})"></div><div class="legend-labels">${definition.labels.map(label => `<span>${label}</span>`).join('')}</div>`;
  }

  function updateTheme(theme) {
    activeTheme = theme;
    const expression = themeExpression(theme);
    if (map.getLayer('buildings-extrusion')) map.setPaintProperty('buildings-extrusion', 'fill-extrusion-color', buildingThemeExpression(theme));
    if (map.getLayer('blocks-fill')) map.setPaintProperty('blocks-fill', 'fill-color', expression);
    legendMarkup(theme);
  }

  async function addPMTilesSource(key, definition) {
    if (!siteManifest.pmtiles.includes(definition.url)) return false;
    const sourceId = `${key}-source`;
    map.addSource(sourceId, {
      type: 'vector',
      url: `pmtiles://${new URL(definition.url, window.location.href).href}`,
      attribution: 'Datos: UAECD / IDECA · Bogotá D.C.',
    });
    const sourceLayer = definition.sourceLayer;
    if (key === 'buildings') {
      map.addLayer({
        id: 'buildings-extrusion', type: 'fill-extrusion', source: sourceId, 'source-layer': sourceLayer,
        minzoom: 13,
        paint: {
          'fill-extrusion-color': buildingThemeExpression(activeTheme),
          'fill-extrusion-height': ['max', 3, ['coalesce', ['to-number', ['get', 'altura_est_m']], ['*', ['to-number', ['get', 'CONNPISOS'], 1], 3]]],
          'fill-extrusion-base': 0,
          'fill-extrusion-opacity': 0.92,
          'fill-extrusion-vertical-gradient': true,
        },
      });
      map.addLayer({
        id: 'buildings-outline', type: 'line', source: sourceId, 'source-layer': sourceLayer, minzoom: 15,
        paint: { 'line-color': '#f2c19a', 'line-width': 0.45, 'line-opacity': 0.55 },
      });
    } else if (key === 'blocks') {
      map.addLayer({
        id: 'blocks-fill', type: 'fill', source: sourceId, 'source-layer': sourceLayer,
        paint: { 'fill-color': themeExpression(activeTheme), 'fill-opacity': 0.5 },
      });
      map.addLayer({
        id: 'blocks-outline', type: 'line', source: sourceId, 'source-layer': sourceLayer,
        paint: { 'line-color': '#bfd4cc', 'line-opacity': 0.25, 'line-width': 0.35 },
      });
    } else if (key === 'roads') {
      map.addLayer({ id: 'roads-line', type: 'line', source: sourceId, 'source-layer': sourceLayer, minzoom: 12,
        paint: { 'line-color': '#dfc69b', 'line-opacity': 0.65, 'line-width': ['interpolate', ['linear'], ['zoom'], 11, 0.3, 16, 1.5] } });
    } else if (key === 'streams') {
      map.addLayer({ id: 'water-line', type: 'line', source: sourceId, 'source-layer': sourceLayer,
        paint: { 'line-color': '#64b6c6', 'line-opacity': 0.85, 'line-width': 1.2 } });
    } else if (key === 'waterbodies') {
      map.addLayer({ id: 'waterbody-fill', type: 'fill', source: sourceId, 'source-layer': sourceLayer,
        paint: { 'fill-color': '#4f9db0', 'fill-opacity': 0.56, 'fill-outline-color': '#77c6cf' } });
    } else if (key === 'ecology') {
      map.addLayer({ id: 'ecology-fill', type: 'fill', source: sourceId, 'source-layer': sourceLayer,
        paint: { 'fill-color': '#76a982', 'fill-opacity': 0.24, 'fill-outline-color': '#a6c994' } });
      map.addLayer({ id: 'ecology-outline', type: 'line', source: sourceId, 'source-layer': sourceLayer,
        paint: { 'line-color': '#a6c994', 'line-opacity': 0.55, 'line-width': 0.7 } });
    } else if (key === 'lots') {
      const visible = Boolean(document.querySelector('[data-layer="lots"]')?.checked);
      map.addLayer({ id: 'lots-fill', type: 'fill', source: sourceId, 'source-layer': sourceLayer, minzoom: 15,
        layout: { visibility: visible ? 'visible' : 'none' },
        paint: { 'fill-color': '#efe2b4', 'fill-opacity': 0.015 } });
      map.addLayer({ id: 'lots-outline', type: 'line', source: sourceId, 'source-layer': sourceLayer, minzoom: 15,
        layout: { visibility: visible ? 'visible' : 'none' },
        paint: { 'line-color': '#efe2b4', 'line-opacity': 0.42, 'line-width': 0.35 } });
    }
    return true;
  }

  function popupContent(feature) {
    const properties = feature.properties || {};
    const isBuilding = ['CONCODIGO', 'CONNPISOS', 'altura_est_m', 'LOTECODIGO'].some(key => properties[key] !== undefined);
    const title = properties.LOCNOMBRE || properties.NOMBRE || properties.MANCODIGO || properties.LOTCODIGO || properties.CONCODIGO || 'Elemento cartográfico';
    const rows = [];
    const candidates = isBuilding
      ? [['Código construcción', 'CONCODIGO'], ['Código de lote', 'LOTECODIGO'], ['Pisos reportados', 'CONNPISOS'], ['Altura estimada (m)', 'altura_est_m'], ['Área huella (m²)', 'area_huella_m2'], ['Mejora', 'CONMEJORA']]
      : [['Código manzana', 'MANCODIGO'], ['Código de lote', 'LOTCODIGO'], ['Localidad', 'localidad'], ['Estrato', 'estrato'], ['Valor referencia (COP/m²)', 'valor_ref_m2'], ['Área construida estimada (m²)', 'area_constr_m2'], ['Índice de construcción', 'indice_construccion'], ['UPL', 'upl_nombre']];
    for (const [label, field] of candidates) {
      if (properties[field] === undefined || properties[field] === null || properties[field] === '') continue;
      let value = properties[field];
      if (field === 'valor_ref_m2') value = `$${numberFormat(value, 0)} COP/m²`;
      else if (field.toLowerCase().includes('area') || field.includes('indice') || field === 'altura_est_m') value = numberFormat(value, 2);
      rows.push(`<span>${escapeHTML(label)}</span><strong>${escapeHTML(value)}</strong>`);
    }
    return `<div class="popup-card"><span class="popup-kicker">${isBuilding ? 'Construcción' : 'Dato urbano'}</span><h3>${escapeHTML(title)}</h3><div class="popup-grid">${rows.length ? rows.join('') : '<span>Sin atributos disponibles</span>'}</div></div>`;
  }

  function setupPopups() {
    map.on('click', event => {
      const ids = ['buildings-extrusion', 'lots-fill', 'blocks-fill'];
      const present = ids.filter(id => map.getLayer(id));
      if (!present.length) return;
      const features = map.queryRenderedFeatures(event.point, { layers: present });
      if (!features.length) return;
      const feature = features.find(item => item.layer.id === 'buildings-extrusion')
        || features.find(item => item.layer.id === 'lots-fill') || features[0];
      new maplibregl.Popup({ closeButton: true, closeOnClick: true, maxWidth: '320px' })
        .setLngLat(event.lngLat).setHTML(popupContent(feature)).addTo(map);
    });
    if (map.getLayer('buildings-extrusion')) {
      map.on('mouseenter', 'buildings-extrusion', () => { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', 'buildings-extrusion', () => { map.getCanvas().style.cursor = ''; });
    }
  }

  function coordinateCenter(feature) {
    const coordinates = feature.geometry?.coordinates;
    const values = [];
    const visit = item => {
      if (!Array.isArray(item)) return;
      if (item.length >= 2 && typeof item[0] === 'number' && typeof item[1] === 'number') values.push(item);
      else item.forEach(visit);
    };
    visit(coordinates);
    if (!values.length) return null;
    const bounds = values.reduce((acc, point) => [Math.min(acc[0], point[0]), Math.min(acc[1], point[1]), Math.max(acc[2], point[0]), Math.max(acc[3], point[1])], [Infinity, Infinity, -Infinity, -Infinity]);
    return [(bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2];
  }

  function localityKey(value) {
    const key = String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es').trim().replace(/\s+/g, ' ');
    return key === 'candelaria' ? 'la candelaria' : key;
  }

  function findViewpoint(name) {
    const key = localityKey(name);
    const found = localityData.get(key);
    if (found) return found;
    const fallback = VIEWPOINTS.find(item => localityKey(item[0]) === key);
    return fallback ? { name: fallback[0], center: [fallback[1], fallback[2]] } : null;
  }

  function goToSearch() {
    const input = document.getElementById('locality-search');
    const location = findViewpoint(input.value.trim());
    if (!location) {
      input.setCustomValidity('Selecciona una localidad de la lista.');
      input.reportValidity();
      return;
    }
    input.setCustomValidity('');
    document.getElementById('map-location').textContent = location.name;
    map.flyTo({ center: location.center, zoom: 13.2, pitch: 62, bearing: -18, duration: 1900, essential: true });
  }

  function updateFlightCaption() {
    const current = VIEWPOINTS[flyIndex % VIEWPOINTS.length];
    document.getElementById('flight-caption').textContent = flightPaused ? `Pausado · ${current[0]}` : flightRunning ? `Sobrevolando · ${current[0]}` : 'Listo para explorar';
    document.getElementById('flight-progress-fill').style.width = `${flightRunning ? ((flyIndex + 1) / VIEWPOINTS.length) * 100 : 0}%`;
    document.getElementById('flight-toggle').textContent = flightRunning ? '■ Detener recorrido' : '▶ Iniciar recorrido';
    document.getElementById('flight-pause').disabled = !flightRunning;
    document.getElementById('flight-pause').textContent = flightPaused ? '▶ Continuar' : 'Ⅱ Pausar';
  }

  function flyToNext() {
    if (!flightRunning || flightPaused) return;
    if (flyIndex >= VIEWPOINTS.length) flyIndex = 0;
    const [name, longitude, latitude] = VIEWPOINTS[flyIndex];
    const target = findViewpoint(name) || { center: [longitude, latitude] };
    document.getElementById('map-location').textContent = name;
    updateFlightCaption();
    map.flyTo({ center: target.center, zoom: name === 'Sumapaz' ? 10.4 : 13, pitch: 62, bearing: (flyIndex * 29) % 120 - 58, duration: 3600, essential: true });
    map.once('moveend', () => {
      if (!flightRunning || flightPaused) return;
      flyIndex += 1;
      updateFlightCaption();
      flightTimer = window.setTimeout(flyToNext, 900);
    });
  }

  function setupFlightControls() {
    document.getElementById('flight-toggle').addEventListener('click', () => {
      if (flightRunning) {
        flightRunning = false;
        flightPaused = false;
        window.clearTimeout(flightTimer);
        map.stop();
        updateFlightCaption();
        return;
      }
      flightRunning = true;
      flightPaused = false;
      flyIndex = 0;
      updateFlightCaption();
      flyToNext();
    });
    document.getElementById('flight-pause').addEventListener('click', () => {
      if (!flightRunning) return;
      flightPaused = !flightPaused;
      if (flightPaused) {
        window.clearTimeout(flightTimer);
        map.stop();
      } else {
        flyToNext();
      }
      updateFlightCaption();
    });
  }

  function setupPanelNavigation() {
    const sidebar = document.getElementById('sidebar');
    const setView = view => {
      document.getElementById('map-controls').classList.toggle('hidden', view !== 'map');
      document.getElementById('media-controls').classList.toggle('hidden', view !== 'media');
      document.querySelectorAll('.view-tab[data-view]').forEach(button => {
        const selected = button.dataset.view === view;
        button.classList.toggle('active', selected);
        button.setAttribute('aria-selected', String(selected));
      });
      document.querySelectorAll('.mobile-bottom-nav [data-view]').forEach(button => button.classList.toggle('mobile-nav-active', button.dataset.view === view));
      if (window.innerWidth <= 760) sidebar.classList.add('open');
      if (view === 'media') window.dispatchEvent(new Event('bogota:show-media'));
      window.setTimeout(() => map.resize(), 260);
    };
    document.querySelectorAll('.view-tabs [data-view]').forEach(button => button.addEventListener('click', () => setView(button.dataset.view)));
    document.getElementById('open-sidebar').addEventListener('click', () => sidebar.classList.add('open'));
    document.getElementById('close-sidebar').addEventListener('click', () => sidebar.classList.remove('open'));
    document.querySelectorAll('.mobile-bottom-nav [data-view]').forEach(button => button.addEventListener('click', () => {
      setView(button.dataset.view);
      if (button.dataset.view === 'map') sidebar.classList.remove('open');
      else sidebar.classList.add('open');
    }));
  }

  function setupLayerControls() {
    document.querySelectorAll('.layer-toggle input').forEach(input => {
      input.addEventListener('change', () => setLayerVisibility(input.dataset.layer, input.checked));
    });
    document.getElementById('reset-layers').addEventListener('click', () => {
      document.querySelectorAll('.layer-toggle input').forEach(input => {
        const checked = input.dataset.layer === 'buildings' || input.dataset.layer === 'blocks' || input.dataset.layer === 'ecology';
        input.checked = checked;
        setLayerVisibility(input.dataset.layer, checked);
      });
      document.getElementById('theme-select').value = 'height';
      updateTheme('height');
    });
    document.getElementById('theme-select').addEventListener('change', event => updateTheme(event.target.value));
    document.getElementById('terrain-toggle').addEventListener('click', event => {
      terrainOn = !terrainOn;
      const exaggeration = Number(document.getElementById('terrain-exaggeration').value);
      if (map.getSource('terrain-dem')) map.setTerrain(terrainOn ? { source: 'terrain-dem', exaggeration } : null);
      event.currentTarget.setAttribute('aria-pressed', String(terrainOn));
      event.currentTarget.textContent = terrainOn ? 'Activo' : 'Inactivo';
    });
    document.getElementById('terrain-exaggeration').addEventListener('input', event => {
      const exaggeration = Number(event.target.value);
      document.getElementById('terrain-value').textContent = `${exaggeration.toFixed(1)}×`;
      event.target.setAttribute('aria-valuetext', `${exaggeration.toFixed(1)} veces`);
      if (terrainOn && map.getSource('terrain-dem')) map.setTerrain({ source: 'terrain-dem', exaggeration });
    });
  }

  function setupMap() {
    if (!window.maplibregl || !window.pmtiles) {
      setStatus('No cargó MapLibre o PMTiles', 'error');
      return;
    }
    const protocol = new window.pmtiles.Protocol();
    window.maplibregl.addProtocol('pmtiles', protocol.tile);
    map = new window.maplibregl.Map({
      container: 'map', style: STYLE_URL, center: BOGOTA, zoom: 10.2, pitch: 55, bearing: -12,
      maxPitch: 78, minZoom: 7, maxZoom: 18, hash: true, attributionControl: false,
      cooperativeGestures: true, canvasContextAttributes: { antialias: false },
    });
    map.addControl(new window.maplibregl.NavigationControl({ visualizePitch: true }), 'bottom-right');
    map.addControl(new window.maplibregl.ScaleControl({ maxWidth: 110, unit: 'metric' }), 'bottom-right');
    map.addControl(new window.maplibregl.AttributionControl({ compact: true }), 'bottom-right');

    map.on('load', async () => {
      try {
        map.addSource('terrain-dem', {
          type: 'raster-dem', tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'],
          tileSize: 256, encoding: 'terrarium', maxzoom: 15, attribution: 'Relieve: AWS Terrain Tiles · Terrarium',
        });
        map.setTerrain({ source: 'terrain-dem', exaggeration: 1.3 });
      } catch (_) {
        setStatus('Mapa listo · terreno no disponible', 'error');
      }

      const pmtilesResults = await Promise.all(Object.entries(PMTILES).map(async ([key, definition]) => {
        try { return await addPMTilesSource(key, definition); } catch (error) { console.warn(`PMTiles ${key}:`, error); return false; }
      }));
      if (pmtilesResults.some(Boolean)) setStatus(`${pmtilesResults.filter(Boolean).length} paquetes PMTiles activos`);
      else setStatus('Mapa base listo · capas locales pendientes');

      const [localities, upl] = await Promise.all([
        siteManifest.geojson.includes('descargas/localidad.geojson')
          ? fetch('descargas/localidad.geojson').then(response => response.ok ? response.json() : null).catch(() => null) : null,
        siteManifest.geojson.includes('descargas/upl.geojson')
          ? fetch('descargas/upl.geojson').then(response => response.ok ? response.json() : null).catch(() => null) : null,
      ]);
      if (localities?.features?.length) {
        map.addSource('locality-source', { type: 'geojson', data: localities });
        map.addLayer({ id: 'locality-line', type: 'line', source: 'locality-source', layout: { visibility: 'none' }, paint: { 'line-color': '#c9b9e8', 'line-width': 1.1, 'line-opacity': 0.72 } });
        for (const feature of localities.features) {
          const name = feature.properties?.LOCNOMBRE || feature.properties?.NOMBRE;
          const center = coordinateCenter(feature);
          if (name && center) {
            const key = localityKey(name);
            const displayName = VIEWPOINTS.find(item => localityKey(item[0]) === key)?.[0] || name;
            localityData.set(key, { name: displayName, center });
          }
        }
      }
      if (upl?.features?.length) {
        map.addSource('upl-source', { type: 'geojson', data: upl });
        map.addLayer({ id: 'upl-line', type: 'line', source: 'upl-source', layout: { visibility: 'none' }, paint: { 'line-color': '#7ad4c0', 'line-width': 0.8, 'line-opacity': 0.6, 'line-dasharray': [2, 2] } });
      }
      for (const [name, longitude, latitude] of VIEWPOINTS) {
        if (localityData.has(localityKey(name))) continue;
        const option = document.createElement('option');
        option.value = name;
        document.getElementById('locality-options').appendChild(option);
      }
      setupPopups();
      updateTheme(activeTheme);
      document.getElementById('flight-count').textContent = `${VIEWPOINTS.length} LOCALIDADES`;
      setStatus(`${pmtilesResults.filter(Boolean).length} capas listas · datos experimentales`);
    });
    map.on('mousemove', event => {
      const { lat, lng } = event.lngLat;
      document.getElementById('coordinate-readout').innerHTML = `${Math.abs(lat).toFixed(4)}° ${lat >= 0 ? 'N' : 'S'}&nbsp;&nbsp; ${Math.abs(lng).toFixed(4)}° ${lng >= 0 ? 'E' : 'O'}`;
    });
    map.on('zoom', () => { document.getElementById('zoom-readout').textContent = `Z ${map.getZoom().toFixed(1)}`; });
    map.on('rotate', () => { document.querySelector('.north-marker i').style.transform = `rotate(${-map.getBearing()}deg)`; });
    map.on('error', event => {
      if (event.error && event.sourceId !== 'terrain-dem') console.warn('MapLibre:', event.error.message || event.error);
    });
    map.on('idle', () => {
      if (statusText.textContent === 'Conectando al mapa') setStatus('Mapa listo · capas locales pendientes');
    });
  }

  document.addEventListener('DOMContentLoaded', async () => {
    setupPanelNavigation();
    setupLayerControls();
    setupFlightControls();
    document.getElementById('search-go').addEventListener('click', goToSearch);
    document.getElementById('locality-search').addEventListener('keydown', event => { if (event.key === 'Enter') goToSearch(); });
    legendMarkup('height');
    try {
      const response = await fetch('manifest.json');
      if (response.ok) {
        const manifest = await response.json();
        siteManifest = { pmtiles: manifest.pmtiles || [], geojson: manifest.geojson || [], media: manifest.media || [] };
      }
    } catch (_) { /* The bundled empty manifest is a safe fallback. */ }
    if (siteManifest.media.includes('media/Bogota_Sobrevuelo_Avenida_Septima.mp4')) {
      const video = document.getElementById('city-video');
      const source = document.createElement('source');
      source.src = 'media/Bogota_Sobrevuelo_Avenida_Septima.mp4';
      source.type = 'video/mp4';
      video.appendChild(source);
      video.load();
      document.getElementById('video-message').textContent = 'Sobrevuelo renderizado en Blender · 1080p.';
    }
    setupMap();
  });
})();
