"""Build and render the Bogotá urban scene in Blender background mode.

Requires phase 2 outputs in EPSG:9377:
  data/processed/phase2/construcciones_centro_9377.geojson
  data/processed/phase2/terrain_center_9377.asc
  data/processed/phase2/camera_path_9377.json

Run: blender -b -P blender/build_scene.py
"""

import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "processed" / "phase2"
MEDIA = ROOT / "web" / "media"
BLEND = ROOT / "data" / "processed" / "Bogota_Urbana_Atardecer.blend"
VIDEO = MEDIA / "Bogota_Sobrevuelo_Avenida_Septima.mp4"
GLB = MEDIA / "Centro_Historico_La_Candelaria.glb"
REPORT = ROOT / "docs" / "REPORTE_FASE3.json"
BUILDINGS_PATH = WORK / "construcciones_centro_9377.geojson"
TERRAIN_PATH = WORK / "terrain_center_9377.asc"
ROUTE_PATH = WORK / "camera_path_9377.json"
FPS = 24
DURATION_SECONDS = 40
FRAME_END = FPS * DURATION_SECONDS


def read_ascii_grid(path):
    with path.open("r", encoding="ascii") as stream:
        header = {}
        for _ in range(6):
            key, value = stream.readline().split()
            header[key.lower()] = float(value)
        values = []
        for row in stream:
            if row.strip():
                values.append([float(value) for value in row.split()])
    grid = {
        "ncols": int(header["ncols"]),
        "nrows": int(header["nrows"]),
        "xllcorner": header["xllcorner"],
        "yllcorner": header["yllcorner"],
        "cellsize": header["cellsize"],
        "nodata": header["nodata_value"],
        "values": values,
    }
    if len(values) != grid["nrows"] or any(len(row) != grid["ncols"] for row in values):
        raise ValueError("El ASCII Grid tiene dimensiones inconsistentes.")
    valid = [value for row in values for value in row if value != grid["nodata"]]
    if not valid:
        raise ValueError("El DEM no contiene celdas válidas.")
    grid["z_origin"] = min(valid)
    grid["min_z"] = min(valid)
    grid["max_z"] = max(valid)
    grid["x_center"] = grid["xllcorner"] + grid["ncols"] * grid["cellsize"] / 2
    grid["y_center"] = grid["yllcorner"] + grid["nrows"] * grid["cellsize"] / 2
    return grid


def iter_geojson_features(path, chunk_size=1024 * 1024):
    """Yield GeoJSON features incrementally instead of loading a large file in RAM."""
    decoder = json.JSONDecoder()
    with path.open("r", encoding="utf-8") as stream:
        buffer = ""
        while '"features"' not in buffer:
            chunk = stream.read(chunk_size)
            if not chunk:
                raise ValueError(f"No se encontró el arreglo features en {path}.")
            buffer += chunk
        position = buffer.index('"features"') + len('"features"')
        while True:
            if position >= len(buffer):
                chunk = stream.read(chunk_size)
                if not chunk:
                    raise ValueError(f"GeoJSON truncado antes de features: {path}")
                buffer = buffer[position:] + chunk
                position = 0
            if buffer[position].isspace() or buffer[position] == ":":
                position += 1
                continue
            if buffer[position] == "[":
                position += 1
                break
            raise ValueError(f"Formato GeoJSON inesperado en {path}.")

        while True:
            while position < len(buffer) and (buffer[position].isspace() or buffer[position] == ","):
                position += 1
            if position < len(buffer) and buffer[position] == "]":
                return
            try:
                feature, end = decoder.raw_decode(buffer, position)
            except json.JSONDecodeError:
                chunk = stream.read(chunk_size)
                if not chunk:
                    raise ValueError(f"GeoJSON truncado dentro del arreglo features: {path}")
                buffer = buffer[position:] + chunk
                position = 0
                continue
            yield feature
            position = end
            # Retain only the unread suffix to keep memory bounded by one feature.
            if position > chunk_size:
                buffer = buffer[position:]
                position = 0


def terrain_value(grid, x, y):
    col = int(round((x - grid["xllcorner"]) / grid["cellsize"]))
    row = int(round((grid["yllcorner"] + grid["nrows"] * grid["cellsize"] - y) / grid["cellsize"]))
    col = max(0, min(grid["ncols"] - 1, col))
    row = max(0, min(grid["nrows"] - 1, row))
    value = grid["values"][row][col]
    return grid["z_origin"] if value == grid["nodata"] else value


def terrain_base(grid, x, y):
    """Approximate bare ground from the lower quartile of a 5x5 DSM window."""
    cell = grid["cellsize"]
    col = int(round((x - grid["xllcorner"]) / cell))
    row = int(round((grid["yllcorner"] + grid["nrows"] * cell - y) / cell))
    samples = []
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            rr, cc = row + dy, col + dx
            if 0 <= rr < grid["nrows"] and 0 <= cc < grid["ncols"]:
                value = grid["values"][rr][cc]
                if value != grid["nodata"]:
                    samples.append(value)
    if not samples:
        return terrain_value(grid, x, y)
    samples.sort()
    return samples[int((len(samples) - 1) * 0.25)]


def get_material(name, color, roughness=0.88, metallic=0.0):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    principled = material.node_tree.nodes.get("Principled BSDF")
    principled.inputs["Base Color"].default_value = (*color, 1.0)
    principled.inputs["Roughness"].default_value = roughness
    principled.inputs["Metallic"].default_value = metallic
    return material


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.collections:
        if block.name != "Collection":
            bpy.data.collections.remove(block)
    root = bpy.context.scene.collection
    collection = bpy.data.collections.get("Collection")
    if collection:
        collection.name = "Bogota | escena urbana"
    return root


def create_terrain(grid, origin, historic_bounds=None):
    ncols, nrows, cell = grid["ncols"], grid["nrows"], grid["cellsize"]
    x0, y0 = grid["xllcorner"], grid["yllcorner"]
    stride = max(1, int(math.ceil(max(ncols, nrows) / 480)))
    if historic_bounds:
        minx, miny, maxx, maxy = historic_bounds
        c0 = max(0, int((minx - x0) / cell))
        c1 = min(ncols - 1, int((maxx - x0) / cell))
        r0 = max(0, int((y0 + nrows * cell - maxy) / cell))
        r1 = min(nrows - 1, int((y0 + nrows * cell - miny) / cell))
    else:
        c0, c1, r0, r1 = 0, ncols - 1, 0, nrows - 1
    columns = list(range(c0, c1 + 1, stride))
    rows = list(range(r0, r1 + 1, stride))
    if columns[-1] != c1:
        columns.append(c1)
    if rows[-1] != r1:
        rows.append(r1)

    vertices = []
    for row in rows:
        for col in columns:
            value = grid["values"][row][col]
            if value == grid["nodata"]:
                value = terrain_value(grid, x0 + col * cell, y0 + (nrows - row) * cell)
            x = x0 + col * cell - origin[0]
            y = y0 + (nrows - row) * cell - origin[1]
            z = value - grid["z_origin"]
            vertices.append((x, y, z))
    faces = []
    width = len(columns)
    for row in range(len(rows) - 1):
        for col in range(width - 1):
            a = row * width + col
            faces.append((a, a + width, a + width + 1, a + 1))

    mesh = bpy.data.meshes.new("Terrain | malla DEM 30 m")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("Terreno y cerros orientales | Copernicus GLO-30", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(get_material("Terreno | bosque andino", (0.20, 0.31, 0.22)))
    return obj


def building_bands(features, grid, origin):
    bands = {
        "bajo": {"color": (0.73, 0.49, 0.31), "vertices": [], "faces": [], "historic_v": [], "historic_f": [], "count": 0},
        "medio": {"color": (0.82, 0.36, 0.20), "vertices": [], "faces": [], "historic_v": [], "historic_f": [], "count": 0},
        "alto": {"color": (0.51, 0.20, 0.17), "vertices": [], "faces": [], "historic_v": [], "historic_f": [], "count": 0},
    }
    hist_extent = [float("inf"), float("inf"), float("-inf"), float("-inf")]
    accepted = 0
    for feature in features:
        props = feature.get("properties", {})
        floors = props.get("CONNPISOS") or props.get("NUM_PISOS") or props.get("PISOS")
        try:
            floors = max(1.0, float(floors))
        except (TypeError, ValueError):
            continue
        height = props.get("altura_est_m")
        try:
            height = float(height) if height is not None else floors * 3.0
        except (TypeError, ValueError):
            height = floors * 3.0
        band_name = "bajo" if floors <= 3 else "medio" if floors <= 8 else "alto"
        geometry = feature.get("geometry") or {}
        if geometry.get("type") == "Polygon":
            polygons = [geometry.get("coordinates", [])]
        elif geometry.get("type") == "MultiPolygon":
            polygons = geometry.get("coordinates", [])
        else:
            continue
        is_historic = str(props.get("localidad", "")).strip().casefold() == "la candelaria"
        base_heights = []
        polygon_rings = []
        for polygon in polygons:
            if not polygon:
                continue
            ring = polygon[0]
            points = [(float(p[0]), float(p[1])) for p in ring[:-1]]
            if len(points) < 3:
                continue
            polygon_rings.append(points)
            center_x = sum(p[0] for p in points) / len(points)
            center_y = sum(p[1] for p in points) / len(points)
            base_heights.append(terrain_base(grid, center_x, center_y) - grid["z_origin"])
        if not polygon_rings:
            continue
        # Multi-polygons are treated as separate building components; an average
        # terrain sample avoids floating volumes over small disconnected parts.
        ground = sum(base_heights) / len(base_heights)
        band = bands[band_name]
        for points in polygon_rings:
            n = len(points)
            local = []
            for x, y in points:
                local.append((x - origin[0], y - origin[1], ground))
            top = [(x, y, z + height) for x, y, z in local]
            offset = len(band["vertices"])
            band["vertices"].extend(local + top)
            band["faces"].extend(
                [(offset + i, offset + (i + 1) % n, offset + (i + 1) % n + n, offset + i + n) for i in range(n)]
            )
            band["faces"].append(tuple(offset + n + i for i in range(n)))
            if is_historic:
                historic_offset = len(band["historic_v"])
                band["historic_v"].extend(local + top)
                band["historic_f"].extend(
                    [(historic_offset + i, historic_offset + (i + 1) % n,
                      historic_offset + (i + 1) % n + n, historic_offset + i + n) for i in range(n)]
                )
                band["historic_f"].append(tuple(historic_offset + n + i for i in range(n)))
                for x, y in points:
                    hist_extent[0] = min(hist_extent[0], x)
                    hist_extent[1] = min(hist_extent[1], y)
                    hist_extent[2] = max(hist_extent[2], x)
                    hist_extent[3] = max(hist_extent[3], y)
        band["count"] += 1
        accepted += 1
    return bands, accepted, hist_extent


def object_from_mesh(name, vertices, faces, material):
    if not vertices or not faces:
        return None
    mesh = bpy.data.meshes.new(name + " | mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def create_lighting_and_camera(grid, route, origin):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = FRAME_END
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.render.image_settings.color_mode = "RGB"

    world = bpy.data.worlds.new("Atardecer bogotano") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    background = nodes.get("Background")
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(7)
    sky.sun_rotation = math.radians(245)
    sky.air_density = 1.1
    sky.dust_density = 1.2
    world.node_tree.links.new(sky.outputs["Color"], background.inputs["Color"])
    background.inputs["Strength"].default_value = 0.45

    sun_data = bpy.data.lights.new("Sol cálido de poniente", "SUN")
    sun_data.energy = 2.3
    sun_data.color = (1.0, 0.57, 0.31)
    sun = bpy.data.objects.new("Sol cálido de poniente", sun_data)
    scene.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(25), math.radians(-18), math.radians(-120))

    cam_data = bpy.data.cameras.new("Cámara | sobrevuelo Séptima-Monserrate")
    camera = bpy.data.objects.new("Cámara | sobrevuelo Séptima-Monserrate", cam_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    cam_data.lens = 36
    target = bpy.data.objects.new("Objetivo animado de cámara", None)
    scene.collection.objects.link(target)
    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = target
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

    points = route["route"]
    keyframes = [1 + round(i * (FRAME_END - 1) / (len(points) - 1)) for i in range(len(points))]
    for i, (point, frame) in enumerate(zip(points, keyframes)):
        ground = terrain_value(grid, point["x"], point["y"]) - grid["z_origin"]
        camera.location = (
            point["x"] - origin[0], point["y"] - origin[1],
            ground + float(point["height_above_ground_m"]),
        )
        next_point = points[min(i + 1, len(points) - 1)]
        target_ground = terrain_value(grid, next_point["x"], next_point["y"]) - grid["z_origin"]
        target.location = (
            next_point["x"] - origin[0], next_point["y"] - origin[1], target_ground + 45,
        )
        camera.keyframe_insert(data_path="location", frame=frame)
        target.keyframe_insert(data_path="location", frame=frame)
    scene.frame_set(1)


def configure_video():
    scene = bpy.context.scene
    scene.render.filepath = str(VIDEO)
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.ffmpeg.video_bitrate = 4500
    scene.render.ffmpeg.maxrate = 5500
    scene.render.ffmpeg.minrate = 2500
    scene.render.ffmpeg.buffersize = 9000
    scene.render.ffmpeg.gopsize = FPS
    scene.render.ffmpeg.audio_codec = "NONE"
    scene.render.ffmpeg.use_autosplit = False


def render_video():
    configure_video()
    scene = bpy.context.scene
    bpy.ops.render.render(animation=True)


def export_glb(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0] if objects else None
    operator = bpy.ops.export_scene.gltf
    properties = {prop.identifier for prop in operator.get_rna_type().properties}
    options = {
        "filepath": str(GLB),
        "export_format": "GLB",
        "use_selection": True,
        "export_apply": True,
        "export_texcoords": False,
        "export_normals": True,
        "export_materials": "EXPORT",
    }
    draco_enabled = "export_draco_mesh_compression_enable" in properties
    if draco_enabled:
        options["export_draco_mesh_compression_enable"] = True
        options["export_draco_mesh_compression_level"] = 6
        options["export_draco_position_quantization"] = 14
    operator(**options)
    return draco_enabled


def main():
    MEDIA.mkdir(parents=True, exist_ok=True)
    required = [BUILDINGS_PATH, TERRAIN_PATH, ROUTE_PATH]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("Faltan salidas de Fase 2: " + ", ".join(missing))

    grid = read_ascii_grid(TERRAIN_PATH)
    with ROUTE_PATH.open(encoding="utf-8") as stream:
        route = json.load(stream)
    if route.get("crs") != "EPSG:9377":
        raise ValueError("La ruta de cámara debe estar transformada a EPSG:9377.")
    reset_scene()
    origin = (grid["x_center"], grid["y_center"])
    terrain = create_terrain(grid, origin)
    bands, building_count, historic_extent = building_bands(
        iter_geojson_features(BUILDINGS_PATH), grid, origin
    )
    if not building_count:
        raise ValueError("No se encontraron construcciones con altura válida en la escena.")
    objects = [terrain]
    for name, band in bands.items():
        material = get_material(f"Edificaciones | {name}", band["color"], roughness=0.76)
        city_obj = object_from_mesh("Edificios | " + name, band["vertices"], band["faces"], material)
        if city_obj:
            objects.append(city_obj)
    if not any(band["historic_f"] for band in bands.values()):
        raise RuntimeError("No se encontraron construcciones de La Candelaria para exportar GLB.")
    if all(math.isfinite(value) for value in historic_extent):
        margin = 1000
        historic_bounds = (
            historic_extent[0] - margin, historic_extent[1] - margin,
            historic_extent[2] + margin, historic_extent[3] + margin,
        )
    else:
        historic_bounds = None
    create_lighting_and_camera(grid, route, origin)
    configure_video()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
    render_video()

    # Build the compact historical GLB after rendering, so duplicate LOD meshes
    # do not appear in the cinematic scene or cause z-fighting.
    historical_objects = []
    for name, band in bands.items():
        material = bpy.data.materials.get(f"Edificaciones | {name}")
        historic_obj = object_from_mesh(
            "Centro histórico | " + name, band["historic_v"], band["historic_f"], material
        )
        if historic_obj:
            historical_objects.append(historic_obj)
    historic_terrain = create_terrain(grid, origin, historic_bounds)
    historic_terrain.name = "Terreno histórico | DEM 30 m"
    historical_objects.append(historic_terrain)
    draco_enabled = export_glb(historical_objects)
    attempts = 0
    while GLB.stat().st_size > 20 * 1024 * 1024 and attempts < 4:
        attempts += 1
        for obj in historical_objects:
            if obj == historic_terrain:
                continue
            modifier = obj.modifiers.new(name=f"GLB LOD {attempts}", type="DECIMATE")
            modifier.ratio = 0.72
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            obj.select_set(False)
        draco_enabled = export_glb(historical_objects)
    video_bytes = VIDEO.stat().st_size if VIDEO.exists() else 0
    glb_bytes = GLB.stat().st_size if GLB.exists() else 0
    report = {
        "status": "completed",
        "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "blender_version": bpy.app.version_string,
        "crs": "Inputs were pre-transformed with QGIS from their source CRS to EPSG:9377; Blender scene axes are local offsets in metres.",
        "local_origin_epsg9377": {"x": origin[0], "y": origin[1], "z_origin_m": grid["z_origin"]},
        "dem": {
            "source": "Copernicus DEM GLO-30 Public, DSM, 30 m nominal resolution",
            "vertical_datum": "EGM2008 as delivered by Copernicus; verify source metadata before survey-grade use",
            "building_base_method": "lower quartile of a 5x5 DSM window to reduce rooftop contribution; approximate only",
            "elevation_min_m": grid["min_z"], "elevation_max_m": grid["max_z"],
        },
        "height_assumption": "Building height = reported floor count × 3 m. This is a visualization assumption, not surveyed height.",
        "animation": {"duration_seconds": DURATION_SECONDS, "fps": FPS, "resolution": "1920x1080", "route": "Av. Séptima to Monserrate"},
        "building_features": building_count,
        "outputs": {
            "blend": {"path": str(BLEND.relative_to(ROOT)), "bytes": BLEND.stat().st_size},
            "mp4": {"path": str(VIDEO.relative_to(ROOT)), "bytes": video_bytes, "limit_bytes": 50 * 1024 * 1024},
            "glb": {"path": str(GLB.relative_to(ROOT)), "bytes": glb_bytes, "limit_bytes": 20 * 1024 * 1024, "draco_enabled": draco_enabled},
        },
        "warnings": [],
    }
    if video_bytes > 50 * 1024 * 1024:
        report["warnings"].append("El MP4 supera 50 MB, reducir bitrate/resolución o acortar duración antes de publicar.")
    if glb_bytes > 20 * 1024 * 1024:
        report["warnings"].append("El GLB supera 20 MB, simplificar/particionar mallas antes de publicar.")
    if not draco_enabled:
        report["warnings"].append("La instalación de Blender no expuso opciones Draco al exportador glTF.")
    manifest_path = ROOT / "web" / "manifest.json"
    try:
        web_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        web_manifest = {"pmtiles": [], "geojson": [], "media": []}
    published_media = []
    for asset in (VIDEO, GLB):
        if asset.exists() and asset.stat().st_size < (50 if asset.suffix == ".mp4" else 20) * 1024 * 1024:
            published_media.append(asset.relative_to(MEDIA.parent).as_posix())
    web_manifest["generated_utc"] = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    web_manifest["media"] = sorted(set(web_manifest.get("media", []) + published_media))
    manifest_path.write_text(json.dumps(web_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


try:
    main()
except Exception as error:
    failure = {
        "status": "failed",
        "error": str(error),
        "traceback": traceback.format_exc(),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(failure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
    raise
