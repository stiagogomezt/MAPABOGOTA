# Verificación del visor 3D de Bogotá

| REQ | Estado | Evidencia |
|---|---|---|
| REQ-COORD | FALLA | test_click_returns_real_coords (tests.test_coordenadas.CoordenadasTests.test_click_returns_real_coords) ... FAIL test_pyproj_conversion (tests.test_coordenadas.CoordenadasTests.test_pyproj_conversion) |
| REQ-ALTITUD | FALLA | test_click_altitude_no_exaggeration (tests.test_altitud.AltitudTests.test_click_altitude_no_exaggeration) ... FAIL test_height_range_exists (tests.test_altitud.AltitudTests.test_height_range_exists) . |
| REQ-ETIQUETAS | FALLA | test_labels_in_dom (tests.test_etiquetas.EtiquetasTests.test_labels_in_dom) ... FAIL test_no_overlap (tests.test_etiquetas.EtiquetasTests.test_no_overlap) ... FAIL  =================================== |
| REQ-DISEÑO | PASA | test_localidades_texture_removed (tests.test_diseno.DisenoTests.test_localidades_texture_removed) ... ok test_no_native_controls_unstyled (tests.test_diseno.DisenoTests.test_no_native_controls_unstyle |
| REQ-NAVEGACIÓN | FALLA | test_fps (tests.test_navegacion.NavegacionTests.test_fps) ... FAIL test_zoom_time (tests.test_navegacion.NavegacionTests.test_zoom_time) ... FAIL  ===================================================== |
| REQ-VISOR | FALLA | test_page_loads (tests.test_visor.VisorTests.test_page_loads) ... FAIL  ====================================================================== FAIL: test_page_loads (tests.test_visor.VisorTests.test_p |
| REQ-PUBLICACIÓN | PASA | test_no_file_over_50mb (tests.test_publicacion.PublicationSizeTests.test_no_file_over_50mb) ... ok test_web_total_below_300mb (tests.test_publicacion.PublicationSizeTests.test_web_total_below_300mb) . |
