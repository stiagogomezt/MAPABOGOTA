#!/usr/bin/env python3
"""Acquire source data and rebuild project status/validation reports."""

from datetime import datetime, timezone
from pathlib import Path
import json
import sys
import argparse
import os
import subprocess


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.acquire_sources import main as acquire_sources
REQUIRED = (
    "web/index.html",
    "docs/BITACORA.md",
    "docs/METADATOS.md",
    "docs/DESCARGAS_MANUALES.md",
    "AGENTS.md",
    "pyproject.toml",
    ".github/workflows/pages.yml",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-only", action="store_true",
        help="validate scaffold without downloading the large source layers",
    )
    parser.add_argument(
        "--phase2-only", action="store_true",
        help="run PyQGIS processing against already-downloaded inputs",
    )
    parser.add_argument(
        "--phase3-only", action="store_true",
        help="render Blender assets from completed phase 2 outputs",
    )
    args = parser.parse_args()

    missing = [relative for relative in REQUIRED if not (ROOT / relative).is_file()]
    if missing:
        print("Faltan archivos requeridos:", *missing, sep="\n- ", file=sys.stderr)
        return 1

    acquisition_result = None
    if not args.validate_only and not args.phase2_only and not args.phase3_only:
        acquisition_result = acquire_sources()

    if not args.validate_only and not args.phase3_only:
        qgis_runner = ROOT / "scripts" / "run_phase2.bat"
        if os.name != "nt" or not qgis_runner.is_file():
            print("No se encontró el ejecutor PyQGIS para este sistema.", file=sys.stderr)
            return 2
        process = subprocess.run(["cmd.exe", "/c", str(qgis_runner)], cwd=ROOT)
        if process.returncode:
            return process.returncode

    if not args.validate_only and not args.phase2_only:
        blender_runner = ROOT / "scripts" / "run_phase3.bat"
        if os.name != "nt" or not blender_runner.is_file():
            print("No se encontró el ejecutor Blender para este sistema.", file=sys.stderr)
            return 2
        process = subprocess.run(["cmd.exe", "/c", str(blender_runner)], cwd=ROOT)
        if process.returncode:
            return process.returncode

    manifest_path = ROOT / "data" / "processed" / "source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "processing_crs": "EPSG:9377",
        "publication_crs": ["EPSG:4326", "EPSG:3857"],
        "publish_directory": "web/",
        "downloaded_sources": len(manifest.get("entries", {})) if manifest else 0,
        "source_failures": manifest.get("failures", []) if manifest else [],
        "privacy_review": "Download script excludes fields matching sensitive-name rules; manual review remains required",
        "validation": "topology validation is implemented in scripts/process_phase2.py; not run in validate-only mode",
        "required_files": list(REQUIRED),
    }
    out = ROOT / "docs" / "REPORTE_VALIDACION.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Validación de estructura correcta. Reporte: {out.relative_to(ROOT)}")
    if args.validate_only:
        print("Modo validate-only: no se procesaron capas ni se ejecutó la validación topológica.")
    return 1 if acquisition_result else 0


if __name__ == "__main__":
    raise SystemExit(main())
