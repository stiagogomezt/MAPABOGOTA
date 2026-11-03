import argparse, json, subprocess, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

CRITICOS = {"REQ-COORD", "REQ-ALTITUD", "REQ-ORIENTACION", "REQ-PUBLICACION", "REQ-VISOR"}

# Map REQ -> test module
REQ_TESTS = {
    "REQ-COORD": "tests.test_reqs.TestReqCoord",
    "REQ-ALTITUD": "tests.test_reqs.TestReqAltitud",
    "REQ-FICHA-CATASTRAL": "tests.test_reqs.TestReqFichaCatastral",
    "REQ-ETIQUETAS": "tests.test_reqs.TestReqEtiquetas",
    "REQ-ESCALA": "tests.test_reqs.TestReqEscala",
    "REQ-HD": "tests.test_reqs.TestReqHd",
    "REQ-COSTURAS": "tests.test_reqs.TestReqCosturas",
    "REQ-SOMBRAS": "tests.test_reqs.TestReqSombras",
    "REQ-NAVEGACION": "tests.test_reqs.TestReqNavegacion",
    "REQ-DISENO": "tests.test_reqs.TestReqDiseno",
    "REQ-ORGANIZACION": "tests.test_reqs.TestReqOrganizacion",
    "REQ-AYUDA": "tests.test_reqs.TestReqAyuda",
    "REQ-ORIENTACION": "tests.test_reqs.TestReqOrientacion",
    "REQ-PUBLICACION": "tests.test_reqs.TestReqPublicacion",
    "REQ-VISOR": "tests.test_visor.VisorSmokeTests",
}

def run_test(req, mod):
    r = subprocess.run([sys.executable, "-m", "unittest", mod, "-v"],
                       capture_output=True, text=True)
    output = (r.stdout + r.stderr).strip()
    if r.returncode == 0:
        status = "PASA"
    else:
        status = "FALLA"
    # first line of error
    err_lines = [l for l in output.splitlines() if "FAIL:" in l or "Error" in l or "FAIL" in l]
    evidence = err_lines[0][:150] if err_lines else output[:150].replace("\n", " ")
    return status, evidence

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--criticos", action="store_true")
    args = ap.parse_args()

    results = []
    for req in sorted(REQ_TESTS):
        mod = REQ_TESTS[req]
        status, evidence = run_test(req, mod)
        results.append((req, status, evidence))

    # write VERIFICACION.md
    lines = ["# Verificación del visor 3D de Bogotá", "", "| REQ | Severidad | Estado | Evidencia |", "|---|---|---|---|"]
    for req, status, ev in results:
        sev = "CRÍTICO" if req in CRITICOS else "MEJORA"
        lines.append(f"| {req} | {sev} | {status} | {ev} |")
    out = "\n".join(lines) + "\n"
    (ROOT / "docs" / "VERIFICACION.md").write_text(out, encoding="utf-8")
    print(out)

    if args.criticos:
        failed = [r for r, s, _ in results if s == "FALLA" and r in CRITICOS]
    else:
        failed = [r for r, s, _ in results if s == "FALLA"]
    if failed:
        sys.exit(1)

if __name__ == "__main__":
    main()