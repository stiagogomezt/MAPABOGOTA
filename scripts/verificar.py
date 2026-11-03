import subprocess, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

tests = [
    ("REQ-COORD", "tests.test_coordenadas"),
    ("REQ-ALTITUD", "tests.test_altitud"),
    ("REQ-ETIQUETAS", "tests.test_etiquetas"),
    ("REQ-DISEÑO", "tests.test_diseno"),
    ("REQ-NAVEGACIÓN", "tests.test_navegacion"),
    ("REQ-VISOR", "tests.test_visor"),
    ("REQ-PUBLICACIÓN", "tests.test_publicacion"),
]

results = []
for req, mod in tests:
    r = subprocess.run([sys.executable, "-m", "unittest", mod, "-v"], capture_output=True, text=True)
    status = "PASA" if r.returncode == 0 else "FALLA"
    evidence = (r.stdout + r.stderr).strip()[:200].replace("\n", " ")
    results.append((req, status, evidence))

# write VERIFICACION.md
lines = ["# Verificación del visor 3D de Bogotá", "", "| REQ | Estado | Evidencia |", "|---|---|---|"]
for req, status, ev in results:
    lines.append(f"| {req} | {status} | {ev} |")
out = "\n".join(lines) + "\n"
(ROOT / "docs" / "VERIFICACION.md").write_text(out, encoding="utf-8")
print(out)

if any(s == "FALLA" for _, s, _ in results):
    sys.exit(1)