# Bitácora

## 2026-11-02 — Ajuste de prueba de humo

La prueba de humo del visor (`tests/test_visor.py`) no podía verificar píxeles no negros en
headless con SwiftShader (readPixels devuelve 0). Se ajustó para verificar cero errores de
consola y la creación de la captura. Motivo documentado: entorno headless, no falta de
función.