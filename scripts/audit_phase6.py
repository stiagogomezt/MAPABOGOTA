"""Engineering-cadastre audit of available GIS outputs and the static viewer.

Run with QGIS' Python environment, for example:
    scripts/run_audit_phase6.bat

Coordinate round-trip checks validate transformation consistency only. They do
not measure positional accuracy, which requires independent control points.
"""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import traceback
from typing import Any

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsVectorLayer,
)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_web import audit_site, measure_local_http


ROOT = Path(__file__).resolve().parents[1]
PHASE2 = ROOT / "data" / "processed" / "phase2"
WEB = ROOT / "web"
REPORT_JSON = ROOT / "docs" / "REPORTE_AUDITORIA_FASE6.json"
REPORT_MD = ROOT / "docs" / "AUDITORIA_FASE6.md"
EXPECTED_LAYERS = {
    "localidad": ["LOCNOMBRE"],
    "upl": ["NOMBRE", "CODIGO_UPL"],
    "manzana": ["MANCODIGO"],
    "construcciones_3d": ["CONNPISOS", "altura_est_m", "area_huella_m2", "area_constr_m2"],
    "manzanas_indicadores": [
        "MANCODIGO", "area_huella_m2", "area_constr_m2", "indice_ocupacion",
        "indice_construccion", "localidad", "upl_nombre", "estrato", "valor_ref_m2",
    ],
}
BUILDING_THEME_FIELDS = ["altura_est_m", "valor_ref_m2", "estrato", "indice_construccion"]
PRIVACY_FIELD = re.compile(
    r"propiet|document|cedula|identificaci|email|correo|telefono|matricula|"
    r"direccion|domicili|titular|dueno|persona|responsable",
    re.IGNORECASE,
)


def gpkg_table(path: Path) -> str:
    with sqlite3.connect(path) as database:
        row = database.execute("SELECT table_name FROM gpkg_geometry_columns LIMIT 1").fetchone()
    if not row:
        raise RuntimeError(f"No vector table found in {path}")
    return str(row[0])


def field_completeness(path: Path, table: str, fields: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    with sqlite3.connect(path) as database:
        columns = {row[1] for row in database.execute(f'PRAGMA table_info("{table}")')}
        total = database.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        for field in fields:
            if field not in columns:
                result[field] = {"present": False, "null_count": None, "nonnull_pct": None}
                continue
            escaped = field.replace('"', '""')
            null_count = database.execute(
                f'SELECT SUM("{escaped}" IS NULL OR TRIM(CAST("{escaped}" AS TEXT)) = ?) FROM "{table}"',
                ("",),
            ).fetchone()[0] or 0
            result[field] = {
                "present": True,
                "null_count": null_count,
                "nonnull_pct": round(100 * (total - null_count) / total, 2) if total else None,
            }
    return result


def inspect_layer(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    layer = QgsVectorLayer(str(path), path.stem, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"QGIS could not open {path}")
    authid = layer.crs().authid()
    extent = layer.extent()
    to_geo = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())
    geographic = to_geo.transformBoundingBox(extent)
    bounds = [geographic.xMinimum(), geographic.yMinimum(), geographic.xMaximum(), geographic.yMaximum()]
    plausible = (
        -75.0 <= bounds[0] <= -73.0 and -75.0 <= bounds[2] <= -73.0
        and 3.0 <= bounds[1] <= 6.0 and 3.0 <= bounds[3] <= 6.0
    )
    table = gpkg_table(path)
    fields = [field.name() for field in layer.fields()]
    checks = field_completeness(path, table, EXPECTED_LAYERS.get(path.stem, []))
    sensitive = [field for field in fields if PRIVACY_FIELD.search(field)]
    building_theme_fields = {
        field: field in fields for field in BUILDING_THEME_FIELDS
    } if path.stem == "construcciones_3d" else None

    round_trip_error = None
    if authid == "EPSG:9377":
        inverse = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), layer.crs(), QgsProject.instance())
        point = extent.center()
        geographic_point = to_geo.transform(point)
        restored = inverse.transform(geographic_point)
        round_trip_error = ((restored.x() - point.x()) ** 2 + (restored.y() - point.y()) ** 2) ** 0.5

    return {
        "path": path.relative_to(ROOT).as_posix(),
        "feature_count": layer.featureCount(),
        "crs": authid or layer.crs().description(),
        "processing_crs_ok": authid == "EPSG:9377",
        "extent_epsg4326": [round(value, 7) for value in bounds],
        "extent_plausible_for_bogota": plausible,
        "crs_round_trip_error_m": round(round_trip_error, 8) if round_trip_error is not None else None,
        "expected_attribute_completeness": checks,
        "building_theme_fields": building_theme_fields,
        "privacy_sensitive_field_names": sensitive,
    }


def inspect_web() -> dict[str, Any]:
    manifest_path = WEB / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    references = [*manifest.get("pmtiles", []), *manifest.get("geojson", []), *manifest.get("media", [])]
    web_root = WEB.resolve()
    missing = []
    for item in references:
        path = (WEB / item).resolve()
        if web_root not in path.parents or not path.is_file():
            missing.append(item)
    files = [path for path in WEB.rglob("*") if path.is_file()]
    temporary = [
        path.relative_to(WEB).as_posix() for path in files
        if path.name.endswith((".part", ".copying", ".tmp", ".temp.db", ".mbtiles"))
        or "-journal" in path.name or path.name.endswith(("-wal", "-shm"))
    ]
    tiles = [path for path in files if path.suffix.lower() == ".pmtiles"]
    return {
        "files": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "largest_files": [
            {"path": path.relative_to(WEB).as_posix(), "bytes": path.stat().st_size}
            for path in sorted(files, key=lambda entry: entry.stat().st_size, reverse=True)[:10]
        ],
        "pmtiles": [{"path": path.relative_to(WEB).as_posix(), "bytes": path.stat().st_size} for path in tiles],
        "manifest_assets": references,
        "manifest_missing_files": missing,
        "temporary_processing_files": temporary,
    }


def write_markdown(report: dict[str, Any]) -> None:
    findings = report["findings"]
    web = report.get("web", {})
    layer_rows = [
        f"| `{name}` | {item['feature_count']:,} | {item['crs']} | "
        f"{'Sí' if item['processing_crs_ok'] else 'No'} | {'Sí' if item['extent_plausible_for_bogota'] else 'No'} |"
        for name, item in report["layers"].items()
    ]
    lines = [
        "# Auditoría integral de Fase 6",
        "",
        f"Auditoría generada: {report['generated_utc']} (UTC).",
        "",
        "## Resumen ejecutivo",
        "",
        f"Estado: **{report['status']}**. Hallazgos: {len(findings)}.",
        "",
        "## Exactitud posicional y CRS",
        "",
        "La exactitud posicional externa **no es cuantificable** con los insumos disponibles: no se suministraron puntos de control independientes, coordenadas GNSS ni tolerancias de aceptación. Las comprobaciones de transformación inversa solo miden consistencia numérica del CRS, no error de levantamiento o de la fuente.",
        "",
        "Se valida EPSG:9377 en capas de proceso, una envolvente razonable de Bogotá tras transformar a EPSG:4326, y el error de ida y vuelta en el centro de cada envolvente. GeoJSON/PMTiles se publican en EPSG:4326; el mapa proyecta a EPSG:3857.",
        "",
        "| Capa | Entidades | CRS | EPSG:9377 | Envolvente Bogotá |",
        "| --- | ---: | --- |:---:|:---:|",
        *layer_rows,
        "",
        "## Completitud y privacidad de atributos",
        "",
        "La presencia y nulidad de los campos clave se registra por capa en `REPORTE_AUDITORIA_FASE6.json`. Los valores nulos en indicadores son esperables cuando la fuente no aporta pisos, estrato o valor; no se interpretan como cero. Los nombres de campos de privacidad se revisan contra un patrón conservador, esto no sustituye validación jurídica del contenido.",
        "",
        "## Metadatos, geometrías y linaje",
        "",
        "Se inspeccionan conteos, CRS, extensiones, campos clave y nombres de campos sensibles. El pipeline reporta control de geometrías inválidas después de `fixgeometries`; esta revisión no prueba ausencia de solapes, vacíos topológicos entre polígonos ni ajuste a linderos de terreno.",
        "",
        "ArcGIS usa 0 como valor de límite de escala sin restricción; se corrigió la representación documental para no presentarlo como escala 0. Fechas y licencias se conservan en `docs/METADATOS.md`, con los límites declarados por cada fuente.",
        "",
        "## Rendimiento web",
        "",
        f"Peso total de archivos bajo `web/`: {web.get('total_bytes', 0):,} bytes. PMTiles presentes: {len(web.get('pmtiles', []))}. Referencias del manifiesto: {len(web.get('manifest_assets', []))}.",
        "",
        "El informe separa el peso de los archivos estáticos del tiempo secuencial de respuesta local (si se solicitó con `--base-url`). Esa medida no equivale al tiempo de primera pintura del mapa: faltan el proveedor CDN, teselas de relieve, caché, red y dispositivo final. Si todavía no hay PMTiles, no se pueden reportar peso ni tiempos de tesela.",
        "",
        "Los artefactos temporales PMTiles se generan en `data/processed/phase2/` y solo se mueven a `web/` al completarse; el validador rechaza temporales y referencias rotas.",
        "",
        "## Accesibilidad",
        "",
        "`python scripts/audit_web.py` comprueba `lang`, título, landmark principal, enlace para saltar al contenido, etiquetas de formularios y nombre accesible de botones, texto alternativo de imágenes, temporales web y contraste mínimo WCAG AA de los colores de texto de la paleta. Es una revisión estática, no una certificación WCAG ni prueba con tecnologías de asistencia.",
        "",
        "## Hallazgos y acciones",
        "",
        *([f"- {finding}" for finding in findings] or ["- Sin hallazgos bloqueantes en las comprobaciones ejecutadas."]),
        "",
        "## Reproducibilidad y límites",
        "",
        "Ejecutar `cmd /c scripts/run_audit_phase6.bat` después de finalizar Fase 2. Para medir la entrega HTTP del servidor local: `uv run python scripts/audit_web.py --base-url http://localhost:8000`. Las pruebas no reemplazan red de control GNSS/topográfica, inspección de licencias ni ensayo real de primera pintura en móvil.",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="optional HTTP base URL for sequential static-resource timing")
    args = parser.parse_args()
    prefix = QgsApplication.prefixPath() or os.environ.get("QGIS_PREFIX_PATH", "")
    if prefix:
        QgsApplication.setPrefixPath(prefix, True)
    application = QgsApplication([], False)
    application.initQgis()
    project = QgsProject.instance()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:9377"))
    project.setEllipsoid("GRS80")

    report: dict[str, Any] = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "completed",
        "positional_accuracy": {
            "status": "not_assessed",
            "reason": "No independent surveyed/GNSS control points or positional tolerance were supplied.",
            "crs_round_trip_is_not_positional_accuracy": True,
        },
        "processing_crs_expected": "EPSG:9377",
        "publication_crs_expected": "EPSG:4326",
        "display_crs": "EPSG:3857",
        "layers": {},
        "web": {},
        "findings": [],
    }
    try:
        for path in sorted(PHASE2.glob("*.gpkg")):
            if path.name.startswith("_"):
                continue
            for sidecar in (Path(f"{path}-journal"), Path(f"{path}-wal"), Path(f"{path}-shm")):
                if sidecar.exists():
                    raise RuntimeError(f"GPKG is being written; defer audit until sidecar disappears: {sidecar.name}")
            item = inspect_layer(path)
            report["layers"][path.stem] = item
            if not item["processing_crs_ok"]:
                report["findings"].append(f"{path.name} has CRS {item['crs']}, expected EPSG:9377.")
            if not item["extent_plausible_for_bogota"]:
                report["findings"].append(f"{path.name} extent is outside the plausible Bogotá envelope.")
            for field, completeness in item["expected_attribute_completeness"].items():
                if not completeness["present"]:
                    report["findings"].append(f"{path.name} is missing expected attribute {field}.")
            if item["building_theme_fields"]:
                missing_theme_fields = [
                    field for field, present in item["building_theme_fields"].items() if not present
                ]
                if missing_theme_fields:
                    report["findings"].append(
                        "Building extrusions cannot use all selected thematic values because "
                        f"{path.name} lacks attributes {missing_theme_fields}; the block layer carries these indicators."
                    )
            if item["privacy_sensitive_field_names"]:
                report["findings"].append(
                    f"{path.name} has potentially sensitive field names: {item['privacy_sensitive_field_names']}"
                )

        report["web"] = inspect_web()
        report["web"]["static_accessibility_audit"] = audit_site()
        for issue in report["web"]["static_accessibility_audit"]["errors"]:
            report["findings"].append(f"Static web/accessibility audit: {issue}")
        if args.base_url:
            report["web"]["local_http_sample"] = measure_local_http(args.base_url)
        for path in report["web"]["manifest_missing_files"]:
            report["findings"].append(f"Manifest references missing web asset {path}.")
        for path in report["web"]["temporary_processing_files"]:
            report["findings"].append(f"Temporary artifact remains under web/: {path}.")
        if not report["web"]["pmtiles"]:
            report["findings"].append("No completed PMTiles found in web/, tile weight/load-time audit is pending production outputs.")
        required = ["localidad", "upl", "manzana", "construcciones_3d", "manzanas_indicadores"]
        for name in required:
            if name not in report["layers"]:
                report["findings"].append(f"Expected processed layer is not present: {name}.")
        if report["findings"]:
            report["status"] = "completed_with_findings"
    except Exception as exc:
        report["status"] = "failed"
        report["findings"].append(str(exc))
        report["traceback"] = traceback.format_exc()
    finally:
        REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_markdown(report)
        print(f"Audit report: {REPORT_MD.relative_to(ROOT)}")
        application.exitQgis()
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
