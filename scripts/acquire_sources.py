"""Download public Bogotá urban layers and build a machine-readable inventory.

Raw source files are intentionally excluded from Git. ArcGIS features are
retrieved in small ID batches and spatially filtered against the official
urban-soil polygon. No cadastral owner or personal-identification attributes
are written to the downloaded GeoJSON.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from shapely.geometry import shape
from shapely.ops import unary_union
from shapely.prepared import prep


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
METADATA = ROOT / "docs" / "METADATOS.md"
MAP_SERVER = (
    "https://serviciosgis.catastrobogota.gov.co/arcgis/rest/services/"
    "Mapa_Referencia/Mapa_Referencia/MapServer"
)
CKAN = "https://datosabiertos.bogota.gov.co/api/3/action/"
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "MAPABOGOTA-reproducible-study/0.1 (public-data research)"
SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=5, connect=5, read=3, backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(("GET", "POST")),
            respect_retry_after_header=True,
        )
    ),
)

# Leaf layers from the official Bogotá reference map. The soil layer provides
# the exact official urban area mask. Rural polygons are deliberately excluded.
ARCGIS_LAYERS: dict[int, str] = {
    45: "suelo_urbano_mascara",
    48: "localidad",
    44: "upl",
    37: "sector_catastral",
    40: "manzana",
    38: "lote",
    39: "construccion",
    13: "malla_vial",
    27: "corriente_agua",
    29: "cuerpo_agua",
}

# Keep useful public cartographic identifiers while excluding personal or
# ownership-related columns. Match field names, not values, conservatively.
PRIVATE_FIELD = re.compile(
    r"propiet|document|cedula|identificaci|\bemail\b|correo|telefono|"
    r"matricula|direccion|domicili|titular|dueno|\bdue[nñ]o\b|persona",
    re.IGNORECASE,
)


def get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = SESSION.get(url, params=params, timeout=(20, 300))
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(f"ArcGIS/API error at {response.url}: {payload['error']}")
            return payload
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Consulta API falló tras reintentos en {url}: {last_error}")


def query_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """POST spatial queries to avoid URL-length limits from urban polygons."""
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            response = SESSION.post(url, data=params, timeout=(20, 300))
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(f"ArcGIS query error at {url}: {payload['error']}")
            return payload
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Consulta ArcGIS falló tras reintentos en {url}: {last_error}")


def arcgis_layer_metadata(layer_id: int) -> dict[str, Any]:
    return get_json(f"{MAP_SERVER}/{layer_id}", {"f": "pjson"})


def urban_geometries() -> list[dict[str, Any]]:
    """Get all official polygons for urban soil classification (code 1)."""
    result = query_json(
        f"{MAP_SERVER}/45/query",
        {
            "where": "SUECSUELO=1",
            "outFields": "SUECODIGO,SUECSUELO,SUEAADMIN,SUEAREA",
            "returnGeometry": "true",
            "outSR": 4326,
            "f": "geojson",
        },
    )
    features = result.get("features", [])
    if not features:
        raise RuntimeError("No se recibió la geometría oficial de suelo urbano.")
    return [feature["geometry"] for feature in features]


def esri_geometry(geometry: dict[str, Any]) -> dict[str, Any]:
    # ArcGIS geometry query parameters require Esri JSON, not RFC 7946 GeoJSON.
    geometry_type = geometry.get("type")
    if geometry_type == "Polygon":
        esri_geometry = {"rings": geometry["coordinates"], "spatialReference": {"wkid": 4326}}
    elif geometry_type == "MultiPolygon":
        esri_geometry = {
            "rings": [ring for polygon in geometry["coordinates"] for ring in polygon],
            "spatialReference": {"wkid": 4326},
        }
    else:
        raise ValueError(f"Tipo de geometría no soportado para máscara urbana: {geometry_type}")
    return esri_geometry


def query_params(geometry: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "geometry": json.dumps(esri_geometry(geometry), separators=(",", ":")),
        "geometryType": "esriGeometryPolygon",
        "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects",
        **extra,
    }


def layer_ids(layer_id: int, bounds: tuple[float, float, float, float]) -> list[int]:
    endpoint = f"{MAP_SERVER}/{layer_id}/query"
    result = query_json(
        endpoint,
        query_params(
            {"type": "Polygon", "coordinates": [[
                [bounds[0], bounds[1]], [bounds[0], bounds[3]],
                [bounds[2], bounds[3]], [bounds[2], bounds[1]],
                [bounds[0], bounds[1]],
            ]]},
            where="1=1", returnIdsOnly="true", returnGeometry="false", f="json"
        ),
    )
    return sorted(result.get("objectIds") or [])


def safe_fields(layer: dict[str, Any]) -> list[str]:
    return [
        field["name"]
        for field in layer.get("fields", [])
        if field.get("type") != "esriFieldTypeGeometry"
        and not PRIVATE_FIELD.search(field["name"])
    ]


def download_arcgis_layer(
    layer_id: int, name: str, ids: list[int], urban_mask: Any, layer: dict[str, Any]
) -> dict[str, Any]:
    endpoint = f"{MAP_SERVER}/{layer_id}/query"
    fields = safe_fields(layer)
    candidate_count = len(ids)
    outpath = RAW / f"{name}.geojson"

    # Stream batches into a FeatureCollection so large building layers do not
    # need to reside entirely in RAM. A .part file protects previous downloads.
    temp = outpath.with_suffix(".geojson.part")
    written = 0
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write('{"type":"FeatureCollection","features":[\n')
        first = True
        for start in range(0, len(ids), 500):
            batch = ids[start : start + 500]
            payload = query_json(
                endpoint,
                {
                    "objectIds": ",".join(map(str, batch)),
                    "outFields": ",".join(fields),
                    "returnGeometry": "true",
                    "outSR": 4326,
                    "f": "geojson",
                },
            )
            for feature in payload.get("features", []):
                geom = feature.get("geometry")
                if not geom or not urban_mask.intersects(shape(geom)):
                    continue
                properties = feature.get("properties", {})
                feature["properties"] = {
                    key: value
                    for key, value in properties.items()
                    if not PRIVATE_FIELD.search(key)
                }
                if not first:
                    stream.write(",\n")
                json.dump(feature, stream, ensure_ascii=False, separators=(",", ":"))
                first = False
                written += 1
            print(f"  {name}: {written:,}/{len(ids):,}", end="\r", flush=True)
            time.sleep(0.03)
        stream.write('\n]}\n')
    try:
        temp.replace(outpath)
    except PermissionError:
        # Windows scanners/indexers can briefly hold a closed large .part file.
        # Stage a verified copy, then atomically publish the complete GeoJSON.
        staged = outpath.with_suffix(".geojson.copying")
        shutil.copyfile(temp, staged)
        if staged.stat().st_size != temp.stat().st_size:
            staged.unlink(missing_ok=True)
            raise RuntimeError(f"Copia incompleta al publicar {outpath.name}")
        os.replace(staged, outpath)
        try:
            temp.unlink()
        except PermissionError:
            pass
    print(f"\nDescargada {name}: {written:,} entidades -> {outpath.relative_to(ROOT)}")
    layer_spatial_reference = (
        layer.get("sourceSpatialReference")
        or (layer.get("extent") or {}).get("spatialReference")
        or {}
    )
    return {
        "file": outpath.relative_to(ROOT).as_posix(),
        "count": written,
        "source_count_intersecting_bbox": candidate_count,
        "source_count_intersecting_urban_mask": written,
        "fields": fields,
        "source_crs": layer_spatial_reference.get(
            "latestWkid", layer_spatial_reference.get("wkid", 4326)
        ),
        "nominal_scale_min": layer.get("minScale"),
        "nominal_scale_max": layer.get("maxScale"),
        "output_crs": "EPSG:4326",
        "source_url": f"{MAP_SERVER}/{layer_id}",
        "source_updated": (layer.get("editingInfo") or {}).get("lastEditDate"),
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
    }


def ckan_package(slug: str) -> dict[str, Any]:
    data = get_json(f"{CKAN}package_show", {"id": slug})
    if not data.get("success"):
        raise RuntimeError(f"CKAN no encontró el conjunto {slug}")
    return data["result"]


def download_ckan_gpkg(slug: str, name: str) -> dict[str, Any]:
    """Download the current official GeoPackage resource and inspect its schema."""
    package = ckan_package(slug)
    resources = package.get("resources", [])
    resource = next(
        (r for r in resources if r.get("format", "").upper() == "GPKG"), None
    )
    if not resource:
        raise RuntimeError(f"No hay GeoPackage en CKAN para {slug}")
    outpath = RAW / f"{name}.gpkg"
    temp = outpath.with_suffix(".gpkg.part")
    for attempt in range(4):
        try:
            with SESSION.get(resource["url"], stream=True, timeout=(30, 300)) as response:
                response.raise_for_status()
                with temp.open("wb") as stream:
                    for chunk in response.iter_content(1024 * 1024):
                        if chunk:
                            stream.write(chunk)
            break
        except requests.RequestException:
            temp.unlink(missing_ok=True)
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    temp.replace(outpath)
    tables: list[dict[str, Any]] = []
    with sqlite3.connect(outpath) as connection:
        layer_tables = connection.execute(
            "SELECT table_name, column_name, srs_id FROM gpkg_geometry_columns"
        ).fetchall()
        for table, geom_col, srs_id in layer_tables:
            columns = [row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')]
            count = connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
            crs = connection.execute(
                "SELECT srs_name, organization, organization_coordsys_id, definition "
                "FROM gpkg_spatial_ref_sys WHERE srs_id=?",
                (srs_id,),
            ).fetchone()
            tables.append(
                {"table": table, "geometry_column": geom_col, "count": count,
                 "fields": columns, "srs_id": srs_id,
                 "crs": (f"EPSG:{crs[2]}" if crs and crs[1] == "EPSG"
                         else f"{crs[1]}:SRS_ID={srs_id} ({crs[0]})" if crs else None),
                 "crs_definition": crs[3] if crs else None}
            )
    print(f"Descargado {name}: {outpath.stat().st_size / 1_000_000:.1f} MB")
    return {
        "file": outpath.relative_to(ROOT).as_posix(),
        "dataset": package.get("title"),
        "description": package.get("notes"),
        "license": package.get("license_title"),
        "cutoff": package.get("metadata_modified"),
        "fields_and_counts": tables,
        "source_url": resource["url"],
        "downloaded_utc": datetime.now(timezone.utc).isoformat(),
    }


def write_inventory(entries: dict[str, Any], failures: list[str]) -> None:
    lines = [
        "# Metadatos e inventario de fuentes",
        "",
        f"Inventario generado: {datetime.now(timezone.utc).isoformat()} (UTC).",
        "Datos fuente en `data/raw/` se excluyen de Git. Los GeoJSON ArcGIS se exportaron a EPSG:4326 para preservación interoperable. El CRS oficial de origen se registra por servicio; la reproyección a EPSG:9377 se realizará en procesamiento, no sobre estos originales. El visor proyecta en EPSG:3857.",
        "",
        "## Capas descargadas",
        "",
    ]
    for name, item in entries.items():
        lines += [f"### {name}", ""]
        if "fields_and_counts" in item:
            lines += [
                f"- Conjunto: {item.get('dataset')}",
                f"- Recurso: `{item['file']}`",
                f"- Fecha de corte / actualización del metadato: {item.get('cutoff')}",
                f"- Licencia declarada: {item.get('license')}",
                f"- Fuente: {item.get('source_url')}",
            ]
            for table in item["fields_and_counts"]:
                lines += [
                    f"- Tabla `{table['table']}`: {table['count']:,} registros; CRS {table['crs']} (SRS ID {table['srs_id']}); campos: {', '.join(table['fields'])}.",
                    f"- Definición CRS de origen (WKT): `{table['crs_definition']}`" if table.get("crs_definition") else "- Definición WKT CRS: no incluida en el GeoPackage.",
                ]
        else:
            lines += [
                f"- Archivo: `{item['file']}`",
                f"- Fuente: {item['source_url']}",
                f"- Fecha de edición de origen: {item.get('source_updated') or 'no informada por servicio'}",
                f"- Fecha de descarga: {item['downloaded_utc']}",
                f"- Entidades descargadas: {item['count']:,}; conteo intersectando suelo urbano: {item['source_count_intersecting_urban_mask']:,}.",
                f"- CRS origen informado: EPSG:{item.get('source_crs')}; CRS del archivo descargado: {item['output_crs']}.",
                f"- Escala de visualización del servicio (denominador): {item.get('nominal_scale_min')} a {item.get('nominal_scale_max')}.",
                f"- Campos descargados: {', '.join(item['fields'])}.",
                "- Licencia: consultar términos del Mapa de Referencia y metadatos IDECA antes de redistribuir.",
            ]
        lines.append("")
    lines += ["## Capas no descargadas", ""]
    if failures:
        lines += [f"- {failure}" for failure in failures]
    else:
        lines.append("- Sin fallos registrados en esta ejecución.")
    lines += [
        "",
        "## Protección de datos y alcance",
        "",
        "Se excluyen campos cuyo nombre coincide con propietario, documento, cédula, identificación, titular, matrícula, dirección, teléfono, correo o persona. Esta lista no sustituye una revisión legal del contenido. No se descargó la tabla Predio del servicio ArcGIS. Los datos no deben publicarse hasta verificar licencia, atributos y controles de privacidad. La máscara de área urbana corresponde al polígono oficial de Suelo con clasificación urbana; no incluye suelo rural ni de expansión.",
        "",
        "## Terreno y fallback",
        "",
        "- Terreno mostrado en el visor: AWS Terrain Tiles, codificación Terrarium, consultado en vivo por tiles. No se hizo mosaico local ni se redistribuyen tiles. Fecha de descarga: no aplica; CRS de tesela: Web Mercator (EPSG:3857); elevación codificada en RGB. Verificar términos y atribución del proveedor.",
        "- Copernicus DEM GLO-30 / ALOS: no descargados en esta fase. Requieren seleccionar teselas, verificar datum vertical/licencia y preparar mosaicos; ver `docs/DESCARGAS_MANUALES.md`.",
        "- OpenStreetMap/OSMnx: no utilizado como fallback, dado que el servicio oficial de referencia expone vías, edificios, hidrografía y áreas catastrales. Si se emplea después, identificarlo como OSM y cumplir ODbL.",
        "",
    ]
    METADATA.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    entries: dict[str, Any] = {}
    failures: list[str] = []
    try:
        masks = urban_geometries()
        urban_mask = unary_union([shape(mask) for mask in masks])
        prepared_mask = prep(urban_mask)
        bounds = urban_mask.bounds
        print(f"Geometrías oficiales de suelo urbano obtenidas: {len(masks)}; envolvente: {bounds}.")
    except Exception as exc:
        print(f"Fallo al obtener máscara urbana: {exc}", file=sys.stderr)
        return 2

    for layer_id, name in ARCGIS_LAYERS.items():
        try:
            layer = arcgis_layer_metadata(layer_id)
            if layer_id == 45:
                result = query_json(
                    f"{MAP_SERVER}/{layer_id}/query",
                    {"where": "SUECSUELO=1", "outFields": "*", "returnGeometry": "true", "outSR": 4326, "f": "geojson"},
                )
                path = RAW / f"{name}.geojson"
                path.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
                entries[name] = {
                    "file": path.relative_to(ROOT).as_posix(), "count": len(result.get("features", [])),
                    "fields": safe_fields(layer), "output_crs": "EPSG:4326",
                    "source_crs": (layer.get("sourceSpatialReference") or {}).get("latestWkid", 4326),
                    "nominal_scale_min": layer.get("minScale"),
                    "nominal_scale_max": layer.get("maxScale"),
                    "source_url": f"{MAP_SERVER}/{layer_id}",
                    "source_updated": (layer.get("editingInfo") or {}).get("lastEditDate"),
                    "downloaded_utc": datetime.now(timezone.utc).isoformat(),
                    "source_count_intersecting_urban_mask": len(result.get("features", [])),
                }
            else:
                ids = layer_ids(layer_id, bounds)
                entries[name] = download_arcgis_layer(layer_id, name, ids, prepared_mask, layer)
        except Exception as exc:
            message = f"ArcGIS {name} (capa {layer_id}): {exc}"
            failures.append(message)
            print(f"FALLO: {message}", file=sys.stderr)

    # CKAN slugs provide current open resources; the raw GeoPackages are kept
    # intact and inspected with SQLite for feature counts, CRS and fields.
    for slug, name in (
        ("estratificacion-para-bogota", "estratificacion_manzana"),
        ("estructura-ecologica-principal-bogota-d-c", "estructura_ecologica_principal"),
        ("valor-de-referencia-por-metro-cuadrado-de-terreno", "valor_referencia_terreno"),
    ):
        try:
            entries[name] = download_ckan_gpkg(slug, name)
        except Exception as exc:
            message = f"CKAN {name} ({slug}): {exc}"
            failures.append(message)
            print(f"FALLO: {message}", file=sys.stderr)

    write_inventory(entries, failures)
    (ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "area": "Bogotá urbana, máscara oficial Suelo=SUECSUELO 1",
        "entries": entries,
        "failures": failures,
    }
    (ROOT / "data" / "processed" / "source_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Inventario actualizado: docs/METADATOS.md ({len(entries)} fuentes).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
