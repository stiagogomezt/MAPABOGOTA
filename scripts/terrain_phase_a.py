"""Fase A - QGIS/GDAL: DEM Copernicus GLO-30 a EPSG:9377 y compuesto Sentinel-2 L2A sin nubes.

Uso:
    python scripts/terrain_phase_a.py --dem-only
    python scripts/terrain_phase_a.py --sentinel-only
    python scripts/terrain_phase_a.py --all
"""
import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import from_bounds
from rasterio.warp import calculate_default_transform, reproject
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "terrain"
OUT.mkdir(parents=True, exist_ok=True)

# Area de trabajo en EPSG:9377 (Bogota urbana + cerros orientales + borde de sabana)
AOI = {
    "xmin": 4850000.0,
    "ymin": 2040000.0,
    "xmax": 4905000.0,
    "ymax": 2105000.0,
    "crs": "EPSG:9377",
}
PIXEL = 10.0  # metros, alineado con Sentinel-2 10 m


def dem_to_9377():
    src_path = RAW / "copernicus_dem_glo30_n04_w075.tif"
    if not src_path.exists():
        raise FileNotFoundError(src_path)
    with rasterio.open(src_path) as src:
        dst_crs = CRS.from_epsg(9377)
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds, resolution=PIXEL
        )
        # recorte a AOI
        from rasterio.windows import from_bounds as win_from_bounds
        window = win_from_bounds(AOI["xmin"], AOI["ymin"], AOI["xmax"], AOI["ymax"], transform=transform)
        col_off = int(math.floor(window.col_off))
        row_off = int(math.floor(window.row_off))
        width = int(math.ceil(window.width))
        height = int(math.ceil(window.height))
        new_transform = rasterio.Affine(PIXEL, 0, AOI["xmin"], 0, -PIXEL, AOI["ymax"])
        profile = src.profile.copy()
        profile.update(
            crs=dst_crs, transform=new_transform, width=width, height=height,
            dtype="float32", count=1, nodata=-9999.0,
        )
        out_tif = OUT / "dem_9377_10m.tif"
        data = np.zeros((height, width), dtype="float32")
        reproject(
            source=rasterio.band(src, 1),
            destination=data,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=new_transform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
            dst_nodata=-9999.0,
        )
        with rasterio.open(out_tif, "w", **profile) as dst:
            dst.write(data, 1)
        # heightmap 16 bits
        valid = data[data != -9999.0]
        vmin = float(np.nanmin(valid))
        vmax = float(np.nanmax(valid))
        rng = vmax - vmin
        scaled = np.clip((data - vmin) / rng * 65535.0, 0, 65535.0).astype("uint16")
        scaled[data == -9999.0] = 0
        Image.fromarray(scaled, mode="I;16").save(OUT / "heightmap_16bit.png")
        georef = {
            "crs": "EPSG:9377",
            "extent_m": AOI,
            "pixel_size_m": PIXEL,
            "width_px": width,
            "height_px": height,
            "origin_local_m": [AOI["xmin"], AOI["ymax"]],
            "height_range_m": {"min": vmin, "max": vmax},
            "vertical_exaggeration": 1.5,
            "nodata": -9999.0,
        }
        (OUT / "georef.json").write_text(json.dumps(georef, indent=2), encoding="utf-8")
        (OUT / "height_range.json").write_text(json.dumps({"min_m": vmin, "max_m": vmax, "range_m": rng}, indent=2), encoding="utf-8")
        print(f"DEM: {width}x{height} px, altura {vmin:.1f}-{vmax:.1f} m")
        return out_tif


def sentinel_composite():
    """Compuesto Sentinel-2 L2A sin nubes (mediana temporada seca dic-mar)."""
    import pystac_client
    import planetary_computer as pc

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=pc.sign_inplace,
    )
    # Temporada seca: dic-mar de 2024-2025
    bbox_wgs = (-74.30, 4.40, -73.90, 4.90)
    search = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox_wgs,
        datetime="2024-12-01/2025-03-31",
        query={"eo:cloud_cover": {"lt": 30}},
        max_items=40,
    )
    items = list(search.items())
    print(f"Escenas Sentinel-2 encontradas: {len(items)}")
    if not items:
        raise RuntimeError("No se encontraron escenas Sentinel-2")

    # Ordenar por cobertura de nubes y tomar las mejores
    items.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100))
    selected = items[:6]
    print("Escenas seleccionadas:", [it.id for it in selected], flush=True)

    # Reproyectar AOI a WGS84 para leer ventanas? Usamos rasterio warp por escena.
    # Leemos bandas B02,B03,B04,SCL a 10m reprojectadas a EPSG:9377.
    import rasterio
    from rasterio.warp import reproject, Resampling as R

    bands = {"B02": None, "B03": None, "B04": None, "SCL": None}
    stacks = {b: [] for b in bands}
    scls = []

    dst_crs = "EPSG:9377"
    new_transform = rasterio.Affine(PIXEL, 0, AOI["xmin"], 0, -PIXEL, AOI["ymax"])
    width = int((AOI["xmax"] - AOI["xmin"]) / PIXEL)
    height = int((AOI["ymax"] - AOI["ymin"]) / PIXEL)

    for idx, it in enumerate(selected):
        print(f"Procesando escena {idx+1}/{len(selected)}: {it.id}", flush=True)
        asset_keys = {"B02": "B02", "B03": "B03", "B04": "B04", "SCL": "SCL"}
        # leer cada banda
        band_arrays = {}
        for bname, akey in asset_keys.items():
            href = it.assets[akey].href
            with rasterio.open(href) as src:
                arr = np.zeros((height, width), dtype="float32" if bname != "SCL" else "uint8")
                reproject(
                    source=rasterio.band(src, 1),
                    destination=arr,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=new_transform,
                    dst_crs=dst_crs,
                    resampling=R.bilinear if bname != "SCL" else R.nearest,
                )
                band_arrays[bname] = arr
        scl = band_arrays["SCL"]
        # mascara valida: SCL en {4,5,6,7}
        valid_mask = np.isin(scl, [4, 5, 6, 7])
        for bname in ["B02", "B03", "B04"]:
            arr = band_arrays[bname].copy()
            arr[~valid_mask] = np.nan
            stacks[bname].append(arr)
        scls.append(valid_mask)

    # mediana por pixel (ignorando nan)
    composite = {}
    for bname in ["B02", "B03", "B04"]:
        stack = np.stack(stacks[bname], axis=0)
        comp = np.nanmedian(stack, axis=0)
        composite[bname] = comp

    # ajuste de contraste/gamma/saturacion
    def to_rgb(b04, b03, b02):
        # Sentinel-2: B04=red, B03=green, B02=blue. Reflectancia 0-1 (escala 10000)
        r = b04 / 10000.0
        g = b03 / 10000.0
        b = b02 / 10000.0
        # percentiles para contraste
        for arr in (r, g, b):
            pass
        # clip a percentiles globales
        allv = np.concatenate([r.flatten(), g.flatten(), b.flatten()])
        lo, hi = np.nanpercentile(allv, [2, 98])
        r = np.clip((r - lo) / (hi - lo), 0, 1)
        g = np.clip((g - lo) / (hi - lo), 0, 1)
        b = np.clip((b - lo) / (hi - lo), 0, 1)
        # gamma
        gamma = 1.1
        r = r ** (1.0 / gamma)
        g = g ** (1.1 / gamma)
        b = b ** (1.0 / gamma)
        # saturacion
        # convertir a hsv, aumentar S
        import colorsys
        # vectorizado aproximado: boost saturation 1.15
        # usar formula
        maxc = np.maximum(np.maximum(r, g), b)
        minc = np.minimum(np.minimum(r, g), b)
        sat = np.where(maxc > 0, (maxc - minc) / np.where(maxc == 0, 1, maxc), 0)
        sat = np.clip(sat * 1.15, 0, 1)
        # reconstruir rgb manteniendo hue/value
        # simple: blend toward original
        # Aproximacion: escalar diferencia respecto a gris
        gray = (r + g + b) / 3.0
        r = gray + (r - gray) * 1.15
        g = gray + (g - gray) * 1.15
        b = gray + (b - gray) * 1.15
        r = np.clip(r, 0, 1)
        g = np.clip(g, 0, 1)
        b = np.clip(b, 0, 1)
        rgb = np.dstack([ (r*255).astype("uint8"), (g*255).astype("uint8"), (b*255).astype("uint8") ])
        return rgb

    rgb = to_rgb(composite["B04"], composite["B03"], composite["B02"])
    # guardar GeoTIFF 8bit RGB
    out_tif = OUT / "sentinel2_rgb_9377.tif"
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 3,
        "dtype": "uint8",
        "crs": dst_crs,
        "transform": new_transform,
    }
    with rasterio.open(out_tif, "w", **profile) as dst:
        for i in range(3):
            dst.write(rgb[:, :, i], i + 1)
    # guardar JPG a 8192 y 4096
    img = Image.fromarray(rgb)
    for size in (8192, 4096):
        resized = img.resize((size, int(size * height / width)), Image.LANCZOS)
        resized.save(OUT / f"texture_satellite_{size}.jpg", quality=92)
    print(f"Sentinel composite guardado: {out_tif}")
    # contar pixeles validos
    valid_pixels = int(np.sum(~np.isnan(composite["B04"])))
    print(f"Pixels validos: {valid_pixels} / {width*height}")
    return out_tif


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dem-only", action="store_true")
    ap.add_argument("--sentinel-only", action="store_true")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    if args.all or (not args.dem_only and not args.sentinel_only):
        args.dem_only = True
        args.sentinel_only = True
    if args.dem_only:
        dem_to_9377()
    if args.sentinel_only:
        sentinel_composite()


if __name__ == "__main__":
    main()
