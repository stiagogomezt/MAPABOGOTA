"""PyQGIS processing pipeline for the Bogotá urban digital-twin phase 2.

Run with the Python bundled with QGIS, not the project's uv interpreter:
    scripts/run_phase2.bat
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import traceback
import unicodedata
import urllib.request
from typing import Any

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureRequest,
    QgsField,
    QgsFillSymbol,
    QgsGraduatedSymbolRenderer,
    QgsLayoutExporter,
    QgsLayoutItemLabel,
    QgsLayoutItemLegend,
    QgsLayoutItemMap,
    QgsLayoutItemScaleBar,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsPrintLayout,
    QgsProject,
    QgsReferencedRectangle,
    QgsRectangle,
    QgsRendererCategory,
    QgsSingleSymbolRenderer,
    QgsSpatialIndex,
    QgsSymbol,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
    QgsGeometry,
    QgsPointXY,
)
from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QColor, QFont


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
WORK = ROOT / "data" / "processed" / "phase2"
FINAL = ROOT / "data" / "processed"
WEB_DOWNLOADS = ROOT / "web" / "descargas"
PROJECT_CRS = QgsCoordinateReferenceSystem("EPSG:9377")
WEB_CRS = QgsCoordinateReferenceSystem("EPSG:4326")
PROCESSING: Any = None
QGIS_APP: Any = None
DEM_URL = (
    "https://copernicus-dem-30m.s3.amazonaws.com/"
    "Copernicus_DSM_COG_10_N04_00_W075_00_DEM/"
    "Copernicus_DSM_COG_10_N04_00_W075_00_DEM.tif"
)

SOURCE_FILES = {
    "mask": RAW / "suelo_urbano_mascara.geojson",
    "localidad": RAW / "localidad.geojson",
    "upl": RAW / "upl.geojson",
    "sector": RAW / "sector_catastral.geojson",
    "manzana": RAW / "manzana.geojson",
    "lote": RAW / "lote.geojson",
    "construccion": RAW / "construccion.geojson",
    "malla_vial": RAW / "malla_vial.geojson",
    "corriente_agua": RAW / "corriente_agua.geojson",
    "cuerpo_agua": RAW / "cuerpo_agua.geojson",
    "estrato": RAW / "estratificacion_manzana.gpkg",
    "estructura_ecologica": RAW / "estructura_ecologica_principal.gpkg",
    "valor_referencia": RAW / "valor_referencia_terreno.gpkg",
}

SENSITIVE_FIELD = re.compile(
    r"propiet|document|cedula|identificaci|email|correo|telefono|matricula|"
    r"direccion|domicili|titular|dueno|persona|responsable",
    re.IGNORECASE,
)


def log(message: str) -> None:
    print(f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {message}", flush=True)


def initialize_processing() -> None:
    global PROCESSING, QGIS_APP
    prefix = QgsApplication.prefixPath()
    if not prefix:
        prefix = os.environ.get("QGIS_PREFIX_PATH", "")
        QgsApplication.setPrefixPath(prefix, True)
    QGIS_APP = QgsApplication([], False)
    QGIS_APP.initQgis()
    QgsProject.instance().setCrs(PROJECT_CRS)
    QgsProject.instance().setEllipsoid("GRS80")
    sys.path.append(str(Path(prefix) / "python" / "plugins"))
    import processing
    from processing.core.Processing import Processing

    Processing.initialize()
    PROCESSING = processing


def gpkg_layer_name(path: Path) -> str:
    with sqlite3.connect(path) as db:
        row = db.execute(
            "SELECT table_name FROM gpkg_geometry_columns ORDER BY table_name LIMIT 1"
        ).fetchone()
    if not row:
        raise RuntimeError(f"No se encontró capa vectorial en {path}")
    return str(row[0])


def declared_crs_label(layer: QgsVectorLayer, path: Path) -> str:
    authid = layer.crs().authid()
    if authid:
        return authid
    if path.suffix.lower() == ".gpkg":
        with sqlite3.connect(path) as database:
            row = database.execute(
                "SELECT srs_id FROM gpkg_geometry_columns LIMIT 1"
            ).fetchone()
        if row:
            return f"CUSTOM:SRS_ID={row[0]}"
    return layer.crs().description()


def open_source(name: str, path: Path) -> QgsVectorLayer:
    if not path.is_file() or path.name.endswith(".part"):
        raise FileNotFoundError(
            f"Falta la fuente completa {path}. Ejecuta primero scripts/acquire_sources.py."
        )
    uri = f"{path}|layername={gpkg_layer_name(path)}" if path.suffix.lower() == ".gpkg" else str(path)
    layer = QgsVectorLayer(uri, name, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"QGIS no puede abrir la capa fuente: {uri}")
    if not layer.crs().isValid():
        raise RuntimeError(f"La fuente {name} no declara un CRS válido, no se asumirá uno.")
    return layer


def run_algorithm(algorithm: str, params: dict[str, Any]) -> QgsVectorLayer:
    result = PROCESSING.run(algorithm, params)
    output = result.get("OUTPUT")
    layer = output if isinstance(output, QgsVectorLayer) else QgsVectorLayer(str(output), algorithm, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"La salida del algoritmo {algorithm} no es válida: {output}")
    return layer


def save_gpkg(layer: QgsVectorLayer, path: Path, layer_name: str) -> QgsVectorLayer:
    path.parent.mkdir(parents=True, exist_ok=True)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name
    options.fileEncoding = "UTF-8"
    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer, str(path), QgsProject.instance().transformContext(), options
    )
    if result[0] != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"No se pudo escribir {path}: {result}")
    return open_source(layer_name, path)


def clear_generated(path: Path) -> None:
    """Remove only a pipeline-owned output and its SQLite sidecars before rebuild."""
    for candidate in (path, Path(f"{path}-wal"), Path(f"{path}-shm")):
        if candidate.exists():
            candidate.unlink()


def run_to_gpkg(algorithm: str, params: dict[str, Any], path: Path, name: str) -> QgsVectorLayer:
    clear_generated(path)
    params["OUTPUT"] = str(path)
    PROCESSING.run(algorithm, params)
    return open_source(name, path)


def count_invalid(layer: QgsVectorLayer) -> int:
    invalid = 0
    for feature in layer.getFeatures():
        geometry = feature.geometry()
        if geometry.isNull() or geometry.isEmpty() or not geometry.isGeosValid():
            invalid += 1
    return invalid


def empty_feature_ids(layer: QgsVectorLayer) -> list[int]:
    """Return FIDs for geometries with no coordinates after overlay operations."""
    return [
        feature.id() for feature in layer.getFeatures()
        if feature.geometry().isNull() or feature.geometry().isEmpty()
    ]


def load_processed(
    name: str,
    source_path: Path,
    mask: QgsVectorLayer,
    previous_details: dict[str, Any] | None = None,
    resume: bool = False,
) -> tuple[QgsVectorLayer, dict[str, Any]]:
    fixed_path = WORK / f"{name}.gpkg"
    if resume and previous_details and fixed_path.is_file() and source_path.is_file():
        if fixed_path.stat().st_mtime >= source_path.stat().st_mtime:
            cached = open_source(name, fixed_path)
            expected_count = previous_details.get("features_after_urban_clip")
            if (
                cached.crs().authid() == "EPSG:9377"
                and (expected_count is None or cached.featureCount() == expected_count)
                and previous_details.get("invalid_after_fix") == 0
            ):
                log(f"{name}: reutilizando salida EPSG:9377 validada ({cached.featureCount():,} entidades).")
                details = dict(previous_details)
                if not details.get("source_crs"):
                    source_layer = open_source(name, source_path)
                    details["source_crs"] = declared_crs_label(source_layer, source_path)
                return cached, details

    source = open_source(name, source_path)
    fields_to_drop = [field.name() for field in source.fields() if SENSITIVE_FIELD.search(field.name())]
    if fields_to_drop:
        source = run_algorithm(
            "native:deletecolumn",
            {"INPUT": source, "COLUMN": fields_to_drop, "OUTPUT": "memory:"},
        )
    source_count = source.featureCount()
    source_crs = declared_crs_label(source, source_path)
    invalid_source = count_invalid(source)
    source_repaired = run_to_gpkg(
        "native:fixgeometries", {"INPUT": source},
        WORK / f"_{name}_source_fixed.gpkg", f"{name}_source_fixed",
    )
    source_multipart = run_to_gpkg(
        "native:promotetomulti", {"INPUT": source_repaired},
        WORK / f"_{name}_source_multi.gpkg", f"{name}_source_multi",
    )
    projected = run_to_gpkg(
        "native:reprojectlayer",
        {"INPUT": source_multipart, "TARGET_CRS": PROJECT_CRS},
        WORK / f"_{name}_reprojected.gpkg", name,
    )
    clipped = run_to_gpkg(
        "native:clip", {"INPUT": projected, "OVERLAY": mask}, WORK / f"_{name}_clipped.gpkg", name,
    )
    invalid_before = count_invalid(clipped)
    repaired = run_to_gpkg(
        "native:fixgeometries", {"INPUT": clipped}, WORK / f"_{name}_fixed.gpkg", name,
    )
    empty_ids = empty_feature_ids(repaired)
    nonempty = run_to_gpkg(
        "native:removenullgeometries",
        {"INPUT": repaired, "REMOVE_EMPTY": True},
        WORK / f"_{name}_nonempty.gpkg", name,
    )
    final_layer = run_to_gpkg(
        "native:deleteduplicategeometries", {"INPUT": nonempty}, fixed_path, name,
    )
    invalid_after = count_invalid(final_layer)
    if invalid_after:
        raise RuntimeError(f"{name}: {invalid_after} geometrías inválidas después de reparar.")
    details = {
        "source": source_path.relative_to(ROOT).as_posix(),
        "source_crs": source_crs,
        "processing_crs": "EPSG:9377",
        "source_features": source_count,
        "invalid_in_source": invalid_source,
        "source_geometries_repaired_before_projection": invalid_source,
        "features_after_urban_clip": final_layer.featureCount(),
        "invalid_before_fix": invalid_before,
        "empty_geometries_removed": len(empty_ids),
        "empty_geometry_output_fids": empty_ids,
        "duplicate_geometries_removed": max(0, nonempty.featureCount() - final_layer.featureCount()),
        "invalid_after_fix": invalid_after,
        "output": fixed_path.relative_to(ROOT).as_posix(),
    }
    log(f"{name}: {details['features_after_urban_clip']:,} entidades, inválidas antes={invalid_before}.")
    return final_layer, details


def find_field(layer: QgsVectorLayer, candidates: list[str], required: bool = True) -> str | None:
    lookup = {re.sub(r"[^A-Z0-9]", "", field.name().upper()): field.name() for field in layer.fields()}
    for candidate in candidates:
        normalized = re.sub(r"[^A-Z0-9]", "", candidate.upper())
        if normalized in lookup:
            return lookup[normalized]
    if required:
        raise RuntimeError(
            f"No encontré campo entre {candidates} en {layer.name()}. "
            f"Campos disponibles: {[field.name() for field in layer.fields()]}"
        )
    return None


def normalize_locality_name(value: Any) -> str:
    """Normalize locality labels for matching despite accents and whitespace."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    without_marks = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(without_marks.upper().split())


def canonical_locality_name(value: Any) -> str:
    """Return the pipeline's locality label, including official short-name aliases."""
    normalized = normalize_locality_name(value)
    return {"CANDELARIA": "LA CANDELARIA"}.get(normalized, normalized)


def add_calculated_fields(buildings: QgsVectorLayer) -> QgsVectorLayer:
    floors = find_field(buildings, ["CONNPISOS", "NUM_PISOS", "NUMPISOS", "PISOS"])
    height = run_to_gpkg(
        "native:fieldcalculator",
        {
            "INPUT": buildings, "FIELD_NAME": "altura_est_m", "FIELD_TYPE": 0,
            "FIELD_LENGTH": 12, "FIELD_PRECISION": 2,
            "FORMULA": f'CASE WHEN to_real("{floors}") > 0 THEN to_real("{floors}") * 3.0 END',
        }, WORK / "_buildings_height.gpkg", "buildings_height",
    )
    footprint = run_to_gpkg(
        "native:fieldcalculator",
        {
            "INPUT": height, "FIELD_NAME": "area_huella_m2", "FIELD_TYPE": 0,
            "FIELD_LENGTH": 18, "FIELD_PRECISION": 2,
            "FORMULA": "area($geometry)",
        }, WORK / "_buildings_footprint.gpkg", "buildings_footprint",
    )
    built_area = run_to_gpkg(
        "native:fieldcalculator",
        {
            "INPUT": footprint, "FIELD_NAME": "area_constr_m2", "FIELD_TYPE": 0,
            "FIELD_LENGTH": 18, "FIELD_PRECISION": 2,
            "FORMULA": f'CASE WHEN to_real("{floors}") > 0 THEN area($geometry) * to_real("{floors}") END',
        }, WORK / "_buildings_built_area.gpkg", "buildings_built_area",
    )
    return save_gpkg(built_area, WORK / "construcciones_3d.gpkg", "construcciones_3d")


def prepare_center_assets(localities: QgsVectorLayer, buildings: QgsVectorLayer) -> dict[str, Any]:
    """Prepare local-coordinate buildings, Copernicus DEM and Blender flight path."""
    locality_field = find_field(localities, ["LOCNOMBRE", "NOMBRE"])
    wanted = {"LA CANDELARIA", "SANTA FE", "CHAPINERO"}
    selected = [
        feature for feature in localities.getFeatures()
        if canonical_locality_name(feature[locality_field]) in wanted
    ]
    matched = {canonical_locality_name(feature[locality_field]) for feature in selected}
    if matched != wanted:
        raise RuntimeError(f"Localidades esperadas no halladas: {sorted(wanted - matched)}")

    localities_index = QgsSpatialIndex()
    for locality in selected:
        localities_index.addFeature(locality)
    locality_by_id = {feature.id(): feature for feature in selected}
    center_layer = QgsVectorLayer(
        f"{QgsWkbTypes.displayString(buildings.wkbType())}?crs=EPSG:9377",
        "construcciones_centro", "memory"
    )
    provider = center_layer.dataProvider()
    provider.addAttributes(list(buildings.fields()) + [QgsField("localidad", QVariant.String)])
    center_layer.updateFields()
    bounds = QgsRectangle()
    for locality in selected:
        bounds.combineExtentWith(locality.geometry().boundingBox())

    batch: list[QgsFeature] = []
    for building in buildings.getFeatures(QgsFeatureRequest().setFilterRect(bounds)):
        geometry = building.geometry()
        if geometry.isNull() or geometry.isEmpty():
            continue
        point = geometry.pointOnSurface()
        locality_name = None
        for fid in localities_index.intersects(point.boundingBox()):
            candidate = locality_by_id[fid]
            if candidate.geometry().intersects(point):
                locality_name = str(candidate[locality_field]).strip()
                break
        if locality_name is None:
            continue
        feature = QgsFeature(center_layer.fields())
        feature.setGeometry(geometry)
        feature.setAttributes(building.attributes() + [locality_name])
        batch.append(feature)
        if len(batch) == 1000:
            provider.addFeatures(batch)
            batch = []
    if batch:
        provider.addFeatures(batch)
    center_layer.updateExtents()
    center_path = WORK / "construcciones_centro.gpkg"
    center_layer = save_gpkg(center_layer, center_path, "construcciones_centro")

    blender_geojson = WORK / "construcciones_centro_9377.geojson"
    geojson_options = QgsVectorFileWriter.SaveVectorOptions()
    geojson_options.driverName = "GeoJSON"
    geojson_options.fileEncoding = "UTF-8"
    geojson_options.ct = QgsCoordinateTransform(PROJECT_CRS, PROJECT_CRS, QgsProject.instance())
    geojson_options.layerOptions = ["COORDINATE_PRECISION=3"]
    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        center_layer, str(blender_geojson), QgsProject.instance().transformContext(), geojson_options
    )
    if result[0] != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"No se pudo crear GeoJSON local para Blender: {result}")

    # Av. Séptima northbound, then east to Monserrate. QGIS performs the CRS
    # conversion from geographic WGS 84 to EPSG:9377.
    route_lonlat = [
        (-74.0740, 4.5981, 150), (-74.0721, 4.6100, 130),
        (-74.0680, 4.6250, 120), (-74.0630, 4.6400, 140),
        (-74.0600, 4.6500, 180), (-74.0550, 4.6420, 240),
        (-74.0500, 4.6300, 350), (-74.0508, 4.6150, 500),
        (-74.0550, 4.6050, 650),
    ]
    transform = QgsCoordinateTransform(WEB_CRS, PROJECT_CRS, QgsProject.instance())
    route = []
    for lon, lat, camera_height in route_lonlat:
        point = transform.transform(QgsPointXY(lon, lat))
        route.append({"x": point.x(), "y": point.y(), "height_above_ground_m": camera_height})
    route_path = WORK / "camera_path_9377.json"
    route_path.write_text(
        json.dumps({"crs": "EPSG:9377", "route": route}, indent=2) + "\n", encoding="utf-8"
    )

    dem_path = RAW / "copernicus_dem_glo30_n04_w075.tif"
    if not dem_path.exists():
        log("Descargando tesela pública Copernicus DEM GLO-30 para Bogotá…")
        temp = dem_path.with_suffix(".tif.part")
        with urllib.request.urlopen(DEM_URL, timeout=180) as response, temp.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        temp.replace(dem_path)

    from osgeo import gdal

    locality_zone = QgsVectorLayer("MultiPolygon?crs=EPSG:9377", "zone_for_dem", "memory")
    zone_provider = locality_zone.dataProvider()
    zone_provider.addAttributes(list(localities.fields()))
    locality_zone.updateFields()
    zone_provider.addFeatures(selected)
    locality_zone.updateExtents()
    buffer_path = WORK / "center_dem_buffer.gpkg"
    clear_generated(buffer_path)
    buffer_layer = PROCESSING.run(
        "native:buffer",
        {
            "INPUT": locality_zone, "DISTANCE": 5000, "SEGMENTS": 8,
            "END_CAP_STYLE": 0, "JOIN_STYLE": 0, "MITER_LIMIT": 2,
            "DISSOLVE": True, "OUTPUT": str(buffer_path),
        },
    )["OUTPUT"]
    dem_output = WORK / "terrain_center_9377.tif"
    clear_generated(dem_output)
    warped = gdal.Warp(
        str(dem_output), str(dem_path), dstSRS="EPSG:9377",
        cutlineDSName=str(buffer_layer), cropToCutline=True,
        xRes=30, yRes=30, resampleAlg="bilinear", dstNodata=-9999,
        creationOptions=["TILED=YES", "COMPRESS=DEFLATE", "PREDICTOR=3"],
    )
    if warped is None:
        raise RuntimeError("gdal.Warp no pudo recortar/reproyectar el DEM Copernicus.")
    warped = None
    ascii_path = WORK / "terrain_center_9377.asc"
    if gdal.Translate(str(ascii_path), str(dem_output), format="AAIGrid") is None:
        raise RuntimeError("No se pudo exportar el DEM a ASCII Grid para Blender.")

    return {
        "buildings": center_path.relative_to(ROOT).as_posix(),
        "building_geojson": blender_geojson.relative_to(ROOT).as_posix(),
        "building_count": center_layer.featureCount(),
        "localities": sorted(matched),
        "dem_source": DEM_URL,
        "dem_raw": dem_path.relative_to(ROOT).as_posix(),
        "dem_type": "Copernicus GLO-30 DSM (surface model, includes vegetation/buildings)",
        "dem_crs": "EPSG:9377",
        "dem_resolution_m": 30,
        "dem_raster": dem_output.relative_to(ROOT).as_posix(),
        "dem_ascii": ascii_path.relative_to(ROOT).as_posix(),
        "camera_path": route_path.relative_to(ROOT).as_posix(),
        "terrain_buffer_m": 5000,
    }


def build_value_index(layer: QgsVectorLayer, key_candidates: list[str], value_candidates: list[str]) -> dict[str, Any]:
    key = find_field(layer, key_candidates, required=False)
    value = find_field(layer, value_candidates, required=False)
    result: dict[str, Any] = {"key": key, "value": value, "by_code": {}}
    if key and value:
        for feature in layer.getFeatures(QgsFeatureRequest().setSubsetOfAttributes([key, value], layer.fields())):
            code = feature[key]
            if code is not None:
                result["by_code"][str(code).strip()] = feature[value]
    return result


def make_spatial_lookup(layer: QgsVectorLayer, value_candidates: list[str]) -> tuple[QgsSpatialIndex, dict[int, QgsFeature], str]:
    field = find_field(layer, value_candidates)
    features = {feature.id(): QgsFeature(feature) for feature in layer.getFeatures()}
    return QgsSpatialIndex(layer.getFeatures()), features, field


def spatial_value(point_layer_feature: QgsFeature, index: QgsSpatialIndex, features: dict[int, QgsFeature], value_field: str) -> Any:
    point = point_layer_feature.geometry().pointOnSurface()
    for fid in index.intersects(point.boundingBox()):
        reference = features[fid]
        if reference.geometry().intersects(point):
            return reference[value_field]
    return None


def build_block_indicators(
    blocks: QgsVectorLayer,
    lots: QgsVectorLayer,
    buildings: QgsVectorLayer,
    locality: QgsVectorLayer,
    upl: QgsVectorLayer,
    sectors: QgsVectorLayer,
    estrato: QgsVectorLayer,
    values: QgsVectorLayer,
) -> QgsVectorLayer:
    block_key = find_field(blocks, ["MANCODIGO", "CODIGO_MANZANA"])
    lot_block_key = find_field(lots, ["MANZCODIGO", "MANCODIGO"])
    lot_key = find_field(lots, ["LOTCODIGO", "CODIGO_LOTE"])
    building_lot_key = find_field(buildings, ["LOTECODIGO", "LOTCODIGO", "CODIGO_LOTE"])
    sector_code = find_field(blocks, ["SECCODIGO"], required=False)
    sector_key = find_field(sectors, ["SCACODIGO"], required=False)
    stratum_key = find_field(estrato, ["CODIGO_MANZANA", "MANCODIGO"], required=False)
    stratum_value = find_field(estrato, ["ESTRATO", "ESTRATO_SOCIOECONOMICO"], required=False)
    reference_key = find_field(values, ["MANCODIGO", "CODIGO_MANZANA"], required=False)
    reference_value = find_field(
        values, ["V_REF", "MEDIANA", "VALOR_M2", "VALORM2", "VALOR_REFERENCIA"], required=False
    )

    lot_to_block: dict[str, str] = {}
    for lot in lots.getFeatures(QgsFeatureRequest().setSubsetOfAttributes([lot_key, lot_block_key], lots.fields())):
        if lot[lot_key] is not None and lot[lot_block_key] is not None:
            lot_to_block[str(lot[lot_key]).strip()] = str(lot[lot_block_key]).strip()

    block_area: dict[str, float] = {}
    sector_by_block: dict[str, str] = {}
    for block in blocks.getFeatures():
        code = str(block[block_key]).strip()
        block_area[code] = block.geometry().area()
        if sector_code and block[sector_code] is not None:
            sector_by_block[code] = str(block[sector_code]).strip()

    stratum_by_block: dict[str, Any] = {}
    if stratum_key and stratum_value:
        for item in estrato.getFeatures():
            if item[stratum_key] is not None:
                stratum_by_block[str(item[stratum_key]).strip()] = item[stratum_value]
    value_by_block: dict[str, Any] = {}
    if reference_key and reference_value:
        for item in values.getFeatures():
            if item[reference_key] is not None:
                value_by_block[str(item[reference_key]).strip()] = item[reference_value]

    sums: dict[str, list[float]] = {}
    fields_to_read = [building_lot_key]
    for candidate in ["CONNPISOS", "NUM_PISOS", "PISOS", "area_huella_m2", "area_constr_m2"]:
        actual = find_field(buildings, [candidate], required=False)
        if actual and actual not in fields_to_read:
            fields_to_read.append(actual)
    floors_field = find_field(buildings, ["CONNPISOS", "NUM_PISOS", "NUMPISOS", "PISOS"])
    footprint_field = find_field(buildings, ["area_huella_m2"])
    built_field = find_field(buildings, ["area_constr_m2"])
    for building in buildings.getFeatures(
        QgsFeatureRequest().setSubsetOfAttributes(fields_to_read, buildings.fields())
    ):
        lot_code = building[building_lot_key]
        block_code = lot_to_block.get(str(lot_code).strip()) if lot_code is not None else None
        if not block_code:
            continue
        values_for_block = sums.setdefault(block_code, [0.0, 0.0, 0.0])
        footprint = building[footprint_field]
        built = building[built_field]
        if footprint is not None:
            values_for_block[0] += float(footprint)
        if built is not None:
            values_for_block[1] += float(built)
        floor_value = building[floors_field]
        if floor_value is not None:
            values_for_block[2] += 1

    locality_index, locality_features, locality_field = make_spatial_lookup(locality, ["LOCNOMBRE", "NOMBRE"])
    upl_index, upl_features, upl_field = make_spatial_lookup(upl, ["NOMBRE", "CODIGO_UPL"])
    estrato_index, estrato_features, estrato_field = make_spatial_lookup(
        estrato, ["ESTRATO", "ESTRATO_SOCIOECONOMICO", "ESTRATOSOCIOECONOMICO"]
    )
    value_index, value_features, value_field = make_spatial_lookup(
        values, ["V_REF", "MEDIANA", "VALOR_M2", "VALORM2", "VALOR_REFERENCIA", "VALOR_REF_M2"]
    )

    out = QgsVectorLayer(
        f"{QgsWkbTypes.displayString(blocks.wkbType())}?crs=EPSG:9377",
        "manzanas_indicadores", "memory"
    )
    provider = out.dataProvider()
    extra_fields = [
        QgsField("area_huella_m2", QVariant.Double),
        QgsField("area_constr_m2", QVariant.Double),
        QgsField("indice_ocupacion", QVariant.Double),
        QgsField("indice_construccion", QVariant.Double),
        QgsField("localidad", QVariant.String),
        QgsField("upl_nombre", QVariant.String),
        QgsField("sector_codigo", QVariant.String),
        QgsField("estrato", QVariant.String),
        QgsField("valor_ref_m2", QVariant.Double),
    ]
    provider.addAttributes(list(blocks.fields()) + extra_fields)
    out.updateFields()
    output_features: list[QgsFeature] = []
    for block in blocks.getFeatures():
        code = str(block[block_key]).strip()
        footprint, built, _ = sums.get(code, [0.0, 0.0, 0.0])
        area = block_area.get(code, 0.0)
        point_feature = QgsFeature(block)
        locality_value = spatial_value(point_feature, locality_index, locality_features, locality_field)
        upl_value = spatial_value(point_feature, upl_index, upl_features, upl_field)
        estrato_value = stratum_by_block.get(code)
        if estrato_value is None:
            estrato_value = spatial_value(point_feature, estrato_index, estrato_features, estrato_field)
        value_value = value_by_block.get(code)
        if value_value is None:
            value_value = spatial_value(point_feature, value_index, value_features, value_field)
        attributes = block.attributes() + [
            footprint,
            built,
            footprint / area if area else None,
            built / area if area else None,
            str(locality_value) if locality_value is not None else None,
            str(upl_value) if upl_value is not None else None,
            sector_by_block.get(code),
            str(estrato_value) if estrato_value is not None else None,
            float(value_value) if value_value is not None else None,
        ]
        feature = QgsFeature(out.fields())
        feature.setGeometry(block.geometry())
        feature.setAttributes(attributes)
        output_features.append(feature)
        if len(output_features) >= 1000:
            provider.addFeatures(output_features)
            output_features = []
    if output_features:
        provider.addFeatures(output_features)
    out.updateExtents()
    return save_gpkg(out, WORK / "manzanas_indicadores.gpkg", "manzanas_indicadores")


def save_geojson(layer: QgsVectorLayer, path: Path, fields: list[str]) -> None:
    missing_fields = [field for field in fields if layer.fields().indexFromName(field) < 0]
    if missing_fields:
        raise RuntimeError(
            f"No se exporta {path.name}: faltan atributos esperados {missing_fields} "
            f"en la capa {layer.name()}."
        )
    simplified = run_algorithm(
        "native:simplifygeometries",
        {"INPUT": layer, "METHOD": 0, "TOLERANCE": 1.5, "OUTPUT": "memory:"},
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = WORK / f"_{path.name}"
    clear_generated(staging)
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GeoJSON"
    options.fileEncoding = "UTF-8"
    options.ct = QgsCoordinateTransform(PROJECT_CRS, WEB_CRS, QgsProject.instance())
    options.attributes = [simplified.fields().indexFromName(field) for field in fields]
    options.layerOptions = ["RFC7946=YES"]
    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        simplified, str(staging), QgsProject.instance().transformContext(), options
    )
    if result[0] != QgsVectorFileWriter.NoError:
        clear_generated(staging)
        raise RuntimeError(f"No se pudo exportar GeoJSON {path}: {result}")
    verified = open_source(path.stem, staging)
    if verified.crs().authid() != "EPSG:4326":
        clear_generated(staging)
        raise RuntimeError(f"GeoJSON {path.name} no quedó en EPSG:4326: {verified.crs().authid()}")
    if verified.featureCount() != simplified.featureCount():
        clear_generated(staging)
        raise RuntimeError(
            f"GeoJSON {path.name}: conteo exportado {verified.featureCount()} "
            f"no coincide con origen simplificado {simplified.featureCount()}."
        )
    clear_generated(path)
    staging.replace(path)


def export_pmtiles(layer: QgsVectorLayer, name: str) -> list[str]:
    ogr2ogr = shutil.which("ogr2ogr")
    if not ogr2ogr:
        candidate = Path(os.environ.get("OSGEO4W_ROOT", "")) / "bin" / "ogr2ogr.exe"
        if candidate.exists():
            ogr2ogr = str(candidate)
    if not ogr2ogr:
        raise RuntimeError("No se encontró ogr2ogr con controlador PMTiles en la instalación QGIS.")
    results: list[str] = []
    source = WORK / f"{layer.name()}.gpkg"
    if not source.exists():
        # The indicator layer is the only output whose layer name differs from
        # the input file name. save_gpkg still stores it at this exact location.
        raise FileNotFoundError(source)
    target = WEB_DOWNLOADS / "pmtiles" / f"{name}.pmtiles"
    target.parent.mkdir(parents=True, exist_ok=True)
    archive_target = FINAL / "pmtiles" / f"{name}.pmtiles"
    clear_generated(target)
    clear_generated(archive_target)
    for candidate in target.parent.glob(f"{target.name}.tmp*"):
        if candidate.is_file():
            candidate.unlink()
    staging = WORK / f"_{name}.pmtiles"
    clear_generated(staging)
    for candidate in WORK.glob(f"{staging.name}.tmp*"):
        if candidate.is_file():
            candidate.unlink()
    command = [
        ogr2ogr, "-f", "PMTiles", str(staging), str(source),
        "-t_srs", "EPSG:4326", "-dsco", "MINZOOM=11", "-dsco", "MAXZOOM=16",
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        clear_generated(staging)
        for candidate in WORK.glob(f"{staging.name}.tmp*"):
            if candidate.is_file():
                candidate.unlink()
        raise RuntimeError(f"ogr2ogr PMTiles falló para {name}: {completed.stderr[-2000:]}")
    if not staging.is_file():
        for candidate in WORK.glob(f"{staging.name}.tmp*"):
            if candidate.is_file():
                candidate.unlink()
        raise RuntimeError(f"ogr2ogr PMTiles finalizó sin crear el archivo {staging}.")
    if staging.stat().st_size >= 95 * 1024 * 1024:
        archive_target.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(archive_target)
        final_target = archive_target
    else:
        clear_generated(target)
        staging.replace(target)
        final_target = target
    for candidate in WORK.glob(f"{staging.name}.tmp*"):
        if candidate.is_file():
            candidate.unlink()
    results.append(final_target.relative_to(ROOT).as_posix())
    return results


def write_web_manifest() -> Path:
    """List only locally generated, publishable assets for the no-build viewer."""
    manifest_path = ROOT / "web" / "manifest.json"
    try:
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        previous = {}
    pmtiles = sorted(
        path.relative_to(ROOT / "web").as_posix()
        for path in (ROOT / "web" / "descargas").rglob("*.pmtiles")
        if path.is_file() and path.stat().st_size < 95 * 1024 * 1024
    )
    geojson = sorted(
        path.relative_to(ROOT / "web").as_posix()
        for path in (ROOT / "web" / "descargas").glob("*.geojson")
        if path.is_file() and path.stat().st_size < 95 * 1024 * 1024
    )
    media = []
    web_root = (ROOT / "web").resolve()
    for item in previous.get("media", []):
        asset = (web_root / item).resolve()
        if web_root not in asset.parents or not asset.is_file():
            continue
        suffix = asset.suffix.lower()
        limit = 50 if suffix == ".mp4" else 20 if suffix == ".glb" else 95
        if asset.stat().st_size < limit * 1024 * 1024:
            media.append(asset.relative_to(web_root).as_posix())
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "pmtiles": pmtiles,
        "geojson": geojson,
        "media": sorted(set(media)),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def publish_web_products(processed: dict[str, QgsVectorLayer], report: dict[str, Any]) -> None:
    administrative = {
        "localidad": ["LOCCODIGO", "LOCNOMBRE"],
        "upl": ["CODIGO_UPL", "NOMBRE"],
        "sector": ["SCACODIGO", "SCANOMBRE"],
    }
    for layer_name, fields in administrative.items():
        geojson_path = WEB_DOWNLOADS / f"{layer_name}.geojson"
        save_geojson(processed[layer_name], geojson_path, fields)
        report["outputs"][f"geojson_{layer_name}"] = {
            "path": geojson_path.relative_to(ROOT).as_posix(),
            "crs": "EPSG:4326",
            "features": processed[layer_name].featureCount(),
            "bytes": geojson_path.stat().st_size,
        }

    # Indicators are already carried by PMTiles. Avoid a second, bulky GeoJSON
    # copy in the static site and remove this pipeline-owned legacy artifact.
    legacy_indicators = WEB_DOWNLOADS / "manzanas_indicadores.geojson"
    if legacy_indicators.is_file():
        legacy_indicators.unlink()

    for layer_name in [
        "construcciones_3d", "manzanas_indicadores", "lote", "malla_vial",
        "corriente_agua", "cuerpo_agua", "estructura_ecologica",
    ]:
        try:
            paths = export_pmtiles(processed[layer_name], layer_name)
            report["outputs"][f"pmtiles_{layer_name}"] = paths
            for relative in paths:
                size = (ROOT / relative).stat().st_size
                if size >= 95 * 1024 * 1024:
                    report["warnings"].append(
                        f"{relative} exceeds 95 MB and must be partitioned before web publication."
                    )
        except Exception as exc:
            report["warnings"].append(f"PMTiles {layer_name}: {exc}")
    write_web_manifest()


def style_layer(layer: QgsVectorLayer, theme: str) -> None:
    if theme == "buildings":
        symbol = QgsFillSymbol.createSimple({"color": "#e59b56", "outline_color": "#8d542d", "outline_width": "0.12"})
    elif theme == "blocks":
        symbol = QgsFillSymbol.createSimple({"color": "#c9ded8", "outline_color": "#568a7b", "outline_width": "0.18"})
    elif theme == "roads":
        symbol = QgsLineSymbol.createSimple({"line_color": "#d4a971", "line_width": "0.32"})
    elif theme == "water":
        symbol = QgsFillSymbol.createSimple({"color": "#8bd3e6", "outline_color": "#378aa8", "outline_width": "0.18"})
    elif theme == "ecology":
        symbol = QgsFillSymbol.createSimple({"color": "#96c783,150", "outline_color": "#4d8245", "outline_width": "0.2"})
    else:
        symbol = QgsFillSymbol.createSimple({"style": "no", "outline_color": "#43566b", "outline_width": "0.35"})
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    layer.triggerRepaint()


def create_project_and_pdf(layers: dict[str, QgsVectorLayer]) -> Path:
    project = QgsProject.instance()
    project.clear()
    project.setCrs(PROJECT_CRS)
    project.setTitle("Gemelo Digital 3D de Bogotá D.C. | Área urbana")
    project.setFileName(str(FINAL / "Proyecto_Bogota_Urbana.qgz"))
    project.setEllipsoid("GRS80")
    draw_order = [
        ("manzanas_indicadores", "blocks"),
        ("estructura_ecologica", "ecology"),
        ("cuerpo_agua", "water"),
        ("corriente_agua", "roads"),
        ("malla_vial", "roads"),
        ("construcciones_3d", "buildings"),
        ("localidad", "boundary"),
        ("upl", "boundary"),
        ("sector", "boundary"),
    ]
    for name, theme in draw_order:
        layer = layers.get(name)
        if layer and layer.isValid():
            style_layer(layer, theme)
            project.addMapLayer(layer)

    project.viewSettings().setDefaultViewExtent(
        QgsReferencedRectangle(layers["manzanas_indicadores"].extent(), PROJECT_CRS)
    )
    project.setFilePathStorage(Qgis.FilePathType.Relative)
    if not project.write():
        raise RuntimeError(f"No se pudo guardar el proyecto QGIS: {project.fileName()}")

    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("Bogotá urbana | mapa de síntesis")
    page = layout.pageCollection().pages()[0]
    page.setPageSize(QgsLayoutSize(297, 210))
    title = QgsLayoutItemLabel(layout)
    title.setText("BOGOTÁ D.C. | GEMELO DIGITAL URBANO")
    title.setFont(QFont("Noto Sans", 17, QFont.Weight.Bold))
    title.setFontColor(QColor("#17324d"))
    title.setHAlign(Qt.AlignmentFlag.AlignLeft)
    title.attemptMove(QgsLayoutPoint(12, 7))
    title.attemptResize(QgsLayoutSize(185, 12))
    layout.addLayoutItem(title)

    subtitle = QgsLayoutItemLabel(layout)
    subtitle.setText("Huella construida, dinámica catastral y estructura ecológica")
    subtitle.setFontColor(QColor("#526577"))
    subtitle.attemptMove(QgsLayoutPoint(12, 19))
    subtitle.attemptResize(QgsLayoutSize(185, 8))
    layout.addLayoutItem(subtitle)

    map_item = QgsLayoutItemMap(layout)
    map_item.setLayers([layers[name] for name, _ in draw_order if name in layers])
    map_item.setKeepLayerSet(True)
    map_item.zoomToExtent(layers["manzanas_indicadores"].extent())
    map_item.attemptMove(QgsLayoutPoint(10, 31))
    map_item.attemptResize(QgsLayoutSize(205, 164))
    layout.addLayoutItem(map_item)

    legend = QgsLayoutItemLegend(layout)
    legend.setTitle("Capas")
    legend.setLinkedMap(map_item)
    legend.setAutoUpdateModel(False)
    legend.attemptMove(QgsLayoutPoint(222, 38))
    layout.addLayoutItem(legend)

    north = QgsLayoutItemLabel(layout)
    north.setText("N\n▲")
    north.setHAlign(Qt.AlignmentFlag.AlignHCenter)
    north.setFontColor(QColor("#17324d"))
    north.attemptMove(QgsLayoutPoint(270, 12))
    north.attemptResize(QgsLayoutSize(15, 15))
    layout.addLayoutItem(north)

    scale = QgsLayoutItemScaleBar(layout)
    scale.setStyle("Single Box")
    scale.setLinkedMap(map_item)
    scale.setUnits(Qgis.DistanceUnit.Kilometers)
    scale.setUnitsPerSegment(2)
    scale.setNumberOfSegments(3)
    scale.setNumberOfSegmentsLeft(0)
    scale.setUnitLabel("km")
    scale.setHeight(2)
    scale.attemptMove(QgsLayoutPoint(14, 181))
    layout.addLayoutItem(scale)

    attribution = QgsLayoutItemLabel(layout)
    attribution.setText(
        "Fuentes: UAECD/IDECA, SDP, Datos Abiertos Bogotá. "
        "CRS: EPSG:9377. Altura estimada = pisos × 3 m. "
        f"Corte/consulta: {datetime.now().date().isoformat()}. "
        "Uso académico, no sustituye información oficial de Catastro."
    )
    attribution.setFontColor(QColor("#35495d"))
    attribution.attemptMove(QgsLayoutPoint(12, 198))
    attribution.attemptResize(QgsLayoutSize(273, 8))
    layout.addLayoutItem(attribution)

    project.layoutManager().addLayout(layout)
    WEB_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    pdf_path = WEB_DOWNLOADS / "Mapa_Bogota_Urbana.pdf"
    exporter = QgsLayoutExporter(layout)
    settings = QgsLayoutExporter.PdfExportSettings()
    settings.dpi = 200
    settings.rasterizeWholeImage = False
    result = exporter.exportToPdf(str(pdf_path), settings)
    if result != QgsLayoutExporter.Success:
        raise RuntimeError(f"Falló exportación PDF: código {result}")
    return pdf_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Procesa capas urbanas de Bogotá con PyQGIS.")
    parser.add_argument(
        "--resume", action="store_true",
        help="reuse pipeline outputs already validated against the current source files",
    )
    parser.add_argument(
        "--export-only", action="store_true",
        help="rebuild publication GeoJSON/PMTiles from completed phase2 GeoPackages without repeating processing",
    )
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    FINAL.mkdir(parents=True, exist_ok=True)
    WEB_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    previous_report: dict[str, Any] = {}
    previous_report_path = ROOT / "docs" / "REPORTE_FASE2.json"
    if (args.resume or args.export_only) and previous_report_path.is_file():
        try:
            previous_report = json.loads(previous_report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous_report = {}
    report: dict[str, Any] = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "processing_crs": "EPSG:9377",
        "publication_crs": "EPSG:4326",
        "height_assumption": "estimated height in metres = CONNPISOS × 3 m; null when floor count is missing/non-positive",
        "indicators": {
            "area_huella_m2": "sum of horizontal building footprints per block",
            "area_constr_m2": "sum of footprint area × reported floor count per block",
            "indice_ocupacion": "building footprint area / block polygon area",
            "indice_construccion": "estimated built floor area / block polygon area",
        },
        "layers": {},
        "outputs": {},
        "warnings": [],
    }
    if args.export_only:
        report["layers"] = previous_report.get("layers", {})
        if "topology" in previous_report:
            report["topology"] = previous_report["topology"]
    try:
        initialize_processing()
        if args.export_only:
            publication_inputs = [
                "localidad", "upl", "sector", "construcciones_3d", "manzanas_indicadores",
                "lote", "malla_vial", "corriente_agua", "cuerpo_agua", "estructura_ecologica",
            ]
            processed: dict[str, QgsVectorLayer] = {}
            missing_products = [WORK / f"{name}.gpkg" for name in publication_inputs if not (WORK / f"{name}.gpkg").is_file()]
            if missing_products:
                raise FileNotFoundError(
                    "Export-only needs completed phase2 layers: "
                    + ", ".join(path.relative_to(ROOT).as_posix() for path in missing_products)
                )
            for name in publication_inputs:
                layer = open_source(name, WORK / f"{name}.gpkg")
                if layer.crs().authid() != "EPSG:9377":
                    raise RuntimeError(
                        f"Export-only rechazó {name}: CRS {layer.crs().authid()}, se esperaba EPSG:9377."
                    )
                processed[name] = layer
            publish_web_products(processed, report)
            report["status"] = "completed-with-warnings" if report["warnings"] else "completed"
            return 0

        expected = list(SOURCE_FILES.items())
        missing = [path for _, path in expected if not path.exists() or path.name.endswith(".part")]
        if missing:
            raise FileNotFoundError(
                "Fuentes pendientes o incompletas, no se inicia el proceso: "
                + ", ".join(path.relative_to(ROOT).as_posix() for path in missing)
            )

        raw_mask = open_source("suelo_urbano_mascara", SOURCE_FILES["mask"])
        mask = run_algorithm(
            "native:reprojectlayer",
            {"INPUT": raw_mask, "TARGET_CRS": PROJECT_CRS, "OUTPUT": "memory:"},
        )
        # The urban mask is itself official and may contain multiple disjoint
        # polygons. Repair before using it as a clipping overlay.
        mask = run_algorithm("native:fixgeometries", {"INPUT": mask, "OUTPUT": "memory:"})
        processed: dict[str, QgsVectorLayer] = {}
        for name, path in expected:
            if name == "mask":
                continue
            processed[name], report["layers"][name] = load_processed(
                name, path, mask,
                previous_details=previous_report.get("layers", {}).get(name),
                resume=args.resume,
            )

        buildings = add_calculated_fields(processed["construccion"])
        processed["construcciones_3d"] = buildings
        report["layers"]["construcciones_3d"] = {
            "features": buildings.featureCount(),
            "floor_field": find_field(buildings, ["CONNPISOS", "NUM_PISOS", "NUMPISOS", "PISOS"]),
            "height_field": "altura_est_m",
            "height_assumption": "number of floors × 3.0 m",
        }

        indicators = build_block_indicators(
            processed["manzana"], processed["lote"], buildings,
            processed["localidad"], processed["upl"], processed["sector"],
            processed["estrato"], processed["valor_referencia"],
        )
        processed["manzanas_indicadores"] = indicators
        report["layers"]["manzanas_indicadores"] = {
            "features": indicators.featureCount(),
            "fields": [field.name() for field in indicators.fields()],
            "joins": "building.LOTECODIGO → lot.LOTCODIGO → lot.MANZCODIGO → block.MANCODIGO; administrative and socio-economic layers by point-on-surface intersection",
        }
        report["outputs"]["blender_inputs"] = prepare_center_assets(processed["localidad"], buildings)

        report["topology"] = {
            "method": "native:fixgeometries, native:deleteduplicategeometries, GEOS validity scan",
            "layers": {name: values for name, values in report["layers"].items() if "invalid_after_fix" in values},
            "limitations": "Boundary coverage/overlap rules between adjacent cadastral polygons are not asserted by simple geometry validity.",
        }

        publish_web_products(processed, report)
        report["outputs"]["pdf"] = create_project_and_pdf(processed).relative_to(ROOT).as_posix()
        report["outputs"]["qgz"] = (FINAL / "Proyecto_Bogota_Urbana.qgz").relative_to(ROOT).as_posix()
        report["height_note"] = (
            "3 m por piso es un supuesto de visualización, no una altura medida ni una especificación normativa. "
            "CONNPISOS conserva el número oficial de pisos; altura nula cuando el dato no es válido."
        )
        report["status"] = "completed-with-warnings" if report["warnings"] else "completed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        report["traceback"] = traceback.format_exc()
        log(f"ERROR: {exc}")
    finally:
        report_path = ROOT / "docs" / "REPORTE_FASE2.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(f"Reporte Fase 2: {report_path.relative_to(ROOT)}")
    return 1 if report.get("status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
