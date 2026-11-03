"""
Pruebas CRÍTICAS del visor 3D de Bogotá.

ARCHIVO PROTEGIDO: lo escribió una persona, no el agente.
El agente NO puede modificarlo. Si una prueba falla, se corrige el visor,
nunca la prueba. El contrato que debe cumplir el visor está en
docs/CONTRATO_VISOR.md.

Dependencias:
    uv add playwright pyproj pillow
    uv run playwright install chromium
"""

import io
import socket
import statistics
import subprocess
import sys
import time
import unittest
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright
from pyproj import Transformer

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"

A_9377 = Transformer.from_crs("EPSG:4326", "EPSG:9377", always_xy=True)

# Puntos de referencia: (latitud, longitud, altitud aproximada m s.n.m., tolerancia de altitud m).
# Las tolerancias de altitud son amplias a propósito: detectan errores gruesos
# (escala, unidades, exageración). La exactitud fina del MDT se evalúa aparte.
PUNTOS = {
    "plaza_bolivar": (4.5981, -74.0758, 2620, 80),
    "monserrate": (4.6058, -74.0561, 3150, 150),
    "el_dorado": (4.7016, -74.1469, 2548, 60),
}

NOMBRES_ETIQUETAS = {
    "plaza_bolivar": "Plaza de Bolívar",
    "monserrate": "Monserrate",
    "el_dorado": "Aeropuerto El Dorado",
}

TOLERANCIA_POSICION_M = 30.0
TOLERANCIA_ETIQUETA_PX = 25.0
TOLERANCIA_GRADOS = 0.0003  # unos 33 m


def a_9377(clave):
    lat, lon, _, _ = PUNTOS[clave]
    este, norte = A_9377.transform(lon, lat)
    return este, norte


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class VisorCritico(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.puerto = puerto_libre()
        cls.servidor = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(cls.puerto),
             "--bind", "127.0.0.1", "--directory", str(WEB)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        time.sleep(1.5)
        cls.pw = sync_playwright().start()
        cls.navegador = cls.pw.chromium.launch(args=[
            "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
        ])
        cls.pagina = cls.navegador.new_page(viewport={"width": 1280, "height": 720})
        cls.errores = []
        cls.pagina.on("console", lambda m: cls.errores.append(m.text) if m.type == "error" else None)
        cls.pagina.on("pageerror", lambda e: cls.errores.append(str(e)))
        cls.pagina.goto(f"http://127.0.0.1:{cls.puerto}/index.html")
        cls.pagina.wait_for_function(
            "() => window.visorAPI && window.visorAPI.listo === true", timeout=180_000)
        cls.pagina.evaluate("() => window.visorAPI.cerrarPortada()")

    @classmethod
    def tearDownClass(cls):
        cls.navegador.close()
        cls.pw.stop()
        cls.servidor.terminate()

    def api(self, metodo, *args):
        return self.pagina.evaluate(f"(a) => window.visorAPI.{metodo}(...a)", list(args))

    def esperar(self, ms=1000):
        self.pagina.wait_for_timeout(ms)

    # ---------- REQ-CARGA (CRÍTICO) ----------
    def test_req_carga_canvas_con_contenido(self):
        self.api("vistaGeneral")
        self.esperar(1500)
        png = self.pagina.locator("canvas").first.screenshot()
        gris = Image.open(io.BytesIO(png)).convert("L").resize((160, 90))
        valores = list(gris.getdata())
        self.assertGreater(statistics.mean(valores), 20, "El canvas está casi negro.")
        self.assertGreater(statistics.pstdev(valores), 8, "El canvas es uniforme: no se dibuja el terreno.")

    # ---------- REQ-ORIENTACION (CRÍTICO) ----------
    def test_req_orientacion(self):
        self.assertGreater(
            self.api("determinanteTerreno"), 0,
            "La malla del terreno está espejada (determinante negativo). Prohibidas las escalas negativas.")
        self.api("vistaNorte")
        self.esperar()
        rumbo = self.api("rumboCamara")
        self.assertTrue(rumbo < 10 or rumbo > 350, f"vistaNorte() debe mirar al norte; rumbo actual {rumbo:.1f}°.")
        p = {k: self.api("pantallaDesdeEPSG9377", *a_9377(k)) for k in PUNTOS}
        for k, v in p.items():
            self.assertTrue(v["visible"], f"{k} no es visible en la vista hacia el norte.")
        self.assertGreater(
            p["monserrate"]["x"], p["el_dorado"]["x"],
            "Mirando al norte, Monserrate (oriente) debe quedar a la derecha de El Dorado (occidente).")
        self.assertLess(
            p["el_dorado"]["y"], p["plaza_bolivar"]["y"],
            "Mirando al norte, El Dorado (más al norte) debe quedar más arriba que la Plaza de Bolívar.")

    # ---------- REQ-COORD (CRÍTICO) ----------
    def test_req_coordenadas_clic(self):
        for k in PUNTOS:
            lat, lon, _, _ = PUNTOS[k]
            este, norte = a_9377(k)
            self.api("enfocar", este, norte, 3000)
            self.esperar()
            p = self.api("pantallaDesdeEPSG9377", este, norte)
            self.assertTrue(p["visible"], f"{k} no es visible después de enfocar().")
            ficha = self.api("consultarPantalla", p["x"], p["y"])
            self.assertIsNotNone(ficha, f"{k}: el clic no devolvió ficha.")
            error = ((ficha["epsg9377"]["E"] - este) ** 2 + (ficha["epsg9377"]["N"] - norte) ** 2) ** 0.5
            self.assertLess(error, TOLERANCIA_POSICION_M,
                            f"{k}: el clic devuelve un punto a {error:.1f} m de la referencia.")
            self.assertAlmostEqual(ficha["wgs84"]["lat"], lat, delta=TOLERANCIA_GRADOS, msg=f"{k}: latitud")
            self.assertAlmostEqual(ficha["wgs84"]["lon"], lon, delta=TOLERANCIA_GRADOS, msg=f"{k}: longitud")

    def test_req_coordenadas_ficha_visible(self):
        este, norte = a_9377("plaza_bolivar")
        self.api("enfocar", este, norte, 3000)
        self.esperar()
        p = self.api("pantallaDesdeEPSG9377", este, norte)
        self.pagina.mouse.click(p["x"], p["y"])  # clic real, como el de una persona
        self.esperar(800)
        ficha = self.pagina.locator('[data-testid="ficha"]')
        texto = ficha.inner_text()
        self.assertIn("EPSG:9377", texto, "La ficha visible no indica el sistema EPSG:9377.")
        e_mostrado = float(self.pagina.locator('[data-testid="ficha-este"]').get_attribute("data-valor"))
        n_mostrado = float(self.pagina.locator('[data-testid="ficha-norte"]').get_attribute("data-valor"))
        h_mostrada = float(self.pagina.locator('[data-testid="ficha-altitud"]').get_attribute("data-valor"))
        lat_mostrada = float(self.pagina.locator('[data-testid="ficha-lat"]').get_attribute("data-valor"))
        lon_mostrada = float(self.pagina.locator('[data-testid="ficha-lon"]').get_attribute("data-valor"))
        lat_ref, lon_ref, _, _ = PUNTOS["plaza_bolivar"]
        self.assertAlmostEqual(lat_mostrada, lat_ref, delta=TOLERANCIA_GRADOS, msg="Latitud WGS84 mostrada")
        self.assertAlmostEqual(lon_mostrada, lon_ref, delta=TOLERANCIA_GRADOS, msg="Longitud WGS84 mostrada")
        self.assertLess(abs(e_mostrado - este), TOLERANCIA_POSICION_M, f"Este mostrado: {e_mostrado}")
        self.assertLess(abs(n_mostrado - norte), TOLERANCIA_POSICION_M, f"Norte mostrado: {n_mostrado}")
        self.assertAlmostEqual(h_mostrada, 2620, delta=80, msg=f"Altitud mostrada: {h_mostrada}")
        solo_digitos = "".join(c for c in texto if c.isdigit())
        self.assertIn(str(int(e_mostrado))[:5], solo_digitos, "El Este no aparece en el texto visible.")
        self.assertIn(str(int(n_mostrado))[:5], solo_digitos, "El Norte no aparece en el texto visible.")

    # ---------- REQ-ALTITUD (CRÍTICO) ----------
    def test_req_altitud(self):
        self.api("fijarExageracion", 1.0)
        for k, (_, _, h_ref, tol) in PUNTOS.items():
            ficha = self.api("consultarEPSG9377", *a_9377(k))
            self.assertAlmostEqual(ficha["altitud"], h_ref, delta=tol,
                                   msg=f"{k}: altitud {ficha['altitud']:.1f} m (referencia ~{h_ref} m)")
        rango = self.api("rangoAlturas")
        self.assertTrue(1500 < rango["min"] < 2700, f"Altitud mínima improbable: {rango['min']}")
        self.assertTrue(3000 < rango["max"] < 4300, f"Altitud máxima improbable: {rango['max']}")

    def test_req_altitud_independiente_de_exageracion(self):
        punto = a_9377("monserrate")
        self.api("fijarExageracion", 1.0)
        h1 = self.api("consultarEPSG9377", *punto)["altitud"]
        self.api("fijarExageracion", 2.5)
        h2 = self.api("consultarEPSG9377", *punto)["altitud"]
        self.api("fijarExageracion", 1.5)
        self.assertAlmostEqual(h1, h2, delta=0.5, msg="La altitud mostrada cambia con la exageración vertical.")

    # ---------- REQ-ETIQUETAS (CRÍTICO) ----------
    def test_req_etiquetas_en_su_lugar(self):
        for k, nombre in NOMBRES_ETIQUETAS.items():
            este, norte = a_9377(k)
            self.api("enfocar", este, norte, 5000)
            self.esperar(1200)
            etiqueta = self.pagina.locator(f'[data-testid="etiqueta"][data-nombre="{nombre}"]')
            self.assertEqual(etiqueta.count(), 1, f"Debe existir exactamente una etiqueta '{nombre}'.")
            self.assertTrue(etiqueta.is_visible(), f"La etiqueta '{nombre}' no es visible al enfocar su punto.")
            punto = etiqueta.locator('[data-testid="etiqueta-punto"]')
            caja = punto.bounding_box()
            self.assertIsNotNone(caja, f"La etiqueta '{nombre}' no tiene su marcador de punto visible.")
            cx, cy = caja["x"] + caja["width"] / 2, caja["y"] + caja["height"] / 2
            ref = self.api("pantallaDesdeEPSG9377", este, norte)
            distancia = ((cx - ref["x"]) ** 2 + (cy - ref["y"]) ** 2) ** 0.5
            self.assertLess(distancia, TOLERANCIA_ETIQUETA_PX,
                            f"La etiqueta '{nombre}' está a {distancia:.0f} px de su posición real.")

    def test_req_etiquetas_sin_superposicion(self):
        for vista in ("vistaGeneral", "vistaNorte"):
            self.api(vista)
            self.esperar(1500)
            cajas = []
            for e in self.pagina.locator('[data-testid="etiqueta"]').all():
                if e.is_visible():
                    c = e.bounding_box()
                    if c:
                        cajas.append((e.get_attribute("data-nombre"), c))
            for i in range(len(cajas)):
                for j in range(i + 1, len(cajas)):
                    (na, a), (nb, b) = cajas[i], cajas[j]
                    cruzan = (a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"]
                              and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"])
                    self.assertFalse(cruzan, f"{vista}: las etiquetas '{na}' y '{nb}' se superponen.")

    # ---------- REQ-SOBREVUELO (CRÍTICO) ----------
    def test_req_sobrevuelo_sobre_el_terreno(self):
        duracion = self.api("duracionSobrevuelo")
        self.assertGreater(duracion, 30, "El sobrevuelo dura menos de 30 s.")
        plaza = a_9377("plaza_bolivar")
        try:
            for exageracion in (1.0, 2.5):
                self.api("fijarExageracion", exageracion)
                despejes, ve_centro = [], 0
                t = 0.0
                while t <= duracion:
                    self.api("posicionarSobrevuelo", t)
                    despejes.append(self.api("despejeCamara"))
                    if self.api("pantallaDesdeEPSG9377", *plaza)["visible"]:
                        ve_centro += 1
                    t += 2.0
                minimo, mediana = min(despejes), statistics.median(despejes)
                self.assertGreater(minimo, 400,
                                   f"Exageración {exageracion}: la cámara baja a {minimo:.0f} m del terreno "
                                   "(negativo = por debajo del terreno).")
                self.assertTrue(800 < mediana < 3500,
                                f"Exageración {exageracion}: altura típica {mediana:.0f} m; debe ser un vuelo panorámico.")
                self.assertGreaterEqual(ve_centro / len(despejes), 0.5,
                                        f"Exageración {exageracion}: el centro de Bogotá se ve en menos de la mitad del vuelo.")
        finally:
            self.api("detenerSobrevuelo")
            self.api("fijarExageracion", 1.5)

    # ---------- REQ-PUBLICACION (CRÍTICO) ----------
    # El nombre empieza por "test_req_z" para que se ejecute al final
    # y reúna los errores de consola de todas las pruebas anteriores.
    def test_req_z_publicacion_sin_errores_consola(self):
        self.api("vistaGeneral")
        self.esperar()
        self.assertEqual(self.errores, [], f"Errores de consola: {self.errores[:5]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)