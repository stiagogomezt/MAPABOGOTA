"""
Genera el terreno web del visor 3D de Bogotá a partir del MDT (GeoTIFF en EPSG:9377).

Corrige los defectos que producen "agujas" y paredes en el visor:
  - valores sin dato (nodata) y costuras entre bloques de descarga,
  - valores fuera de rango (por ejemplo -32768, -6822 o 6062 m),
  - picos aislados.
Después valida que todas las alturas sean plausibles para Bogotá y escribe:

  <salida>/alturas.bin     Float32 little-endian, fila por fila de NORTE a SUR, oeste a este.
  <salida>/terreno.json    Georreferenciación y estadísticas (lo lee bogota3d_terreno.js).
  <salida>/textura_8192.jpg y textura_4096.jpg   (si se indica --imagen) con la MISMA
                           extensión exacta del terreno, opcionalmente con relieve sombreado.

Uso:
  uv run python scripts/generar_terreno.py --mdt RUTA_MDT.tif --salida web/terreno
         [--imagen RUTA_IMAGEN_RGB.tif] [--extension E_MIN N_MIN E_MAX N_MAX]
         [--ancho 1025] [--sombreado 0.35]

Dependencias: uv add rasterio numpy pillow
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.fill import fillnodata
from rasterio.windows import from_bounds

Image.MAX_IMAGE_PIXELS = None


def parametros():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mdt", required=True, help="GeoTIFF del MDT fusionado, en EPSG:9377")
    p.add_argument("--salida", required=True, help="Carpeta de salida, por ejemplo web/terreno")
    p.add_argument("--imagen", help="GeoTIFF RGB (EPSG:9377) para generar texturas alineadas")
    p.add_argument("--extension", nargs=4, type=float, metavar=("E_MIN", "N_MIN", "E_MAX", "N_MAX"),
                   help="Extensión en EPSG:9377. Por defecto, la extensión completa del MDT")
    p.add_argument("--ancho", type=int, default=1025, help="Número de vértices en dirección este-oeste")
    p.add_argument("--min-valido", type=float, default=1500.0, help="Altura mínima plausible (m)")
    p.add_argument("--max-valido", type=float, default=4500.0, help="Altura máxima plausible (m)")
    p.add_argument("--umbral-pico", type=float, default=60.0,
                   help="Diferencia (m) con la mediana local para considerar un punto como pico aislado")
    p.add_argument("--sombreado", type=float, default=0.35,
                   help="Intensidad del relieve sombreado mezclado en la textura (0 = sin sombreado)")
    p.add_argument("--azimut", type=float, default=285.0, help="Azimut del sol para el sombreado (grados)")
    p.add_argument("--textura-max", type=int, default=8192, help="Lado mayor de la textura grande (px)")
    p.add_argument("--altura-sol", type=float, default=30.0, help="Altura del sol para el sombreado (grados)")
    return p.parse_args()


def comprobar_crs(ds, nombre):
    epsg = ds.crs.to_epsg() if ds.crs else None
    if epsg != 9377:
        sys.exit(f"ERROR: {nombre} está en {ds.crs} y debe estar en EPSG:9377. Reproyéctalo primero.")


def mediana_3x3(a):
    p = np.pad(a, 1, mode="edge")
    capas = [p[1 + dy:1 + dy + a.shape[0], 1 + dx:1 + dx + a.shape[1]]
             for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    return np.median(np.stack(capas), axis=0)


def media_movil(a, r):
    """Media en una ventana de (2r+1)x(2r+1) usando una imagen integral (rápido y con poca memoria)."""
    p = np.pad(a.astype("float64"), r + 1, mode="edge")
    s = p.cumsum(0).cumsum(1)
    k = 2 * r + 1
    tot = s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]
    return (tot / (k * k))[: a.shape[0], : a.shape[1]].astype(a.dtype)


def limpiar_mdt(datos, mascara_valida, args):
    malos = (~mascara_valida) | ~np.isfinite(datos) | (datos < args.min_valido) | (datos > args.max_valido)
    print(f"  Píxeles sin dato o fuera de rango: {int(malos.sum()):,} de {datos.size:,}")
    if malos.all():
        sys.exit("ERROR: el MDT no tiene ningún valor válido en la extensión pedida.")
    trabajo = np.where(malos, 0, datos).astype("float32")
    valido = (~malos).astype("uint8")
    for _ in range(3):  # varias pasadas para huecos grandes
        trabajo = fillnodata(trabajo, mask=valido, max_search_distance=500, smoothing_iterations=0)
        valido = ((trabajo >= args.min_valido) & (trabajo <= args.max_valido)).astype("uint8")
        if valido.all():
            break
    if not valido.all():
        relleno = float(np.median(trabajo[valido.astype(bool)]))
        trabajo = np.where(valido.astype(bool), trabajo, relleno)
    # Suaviza las zonas rellenadas y su borde para que no queden costuras visibles en el relieve.
    zona = media_movil(malos.astype("float32"), 3) > 0
    for _ in range(2):
        trabajo = np.where(zona, media_movil(trabajo, 2), trabajo)
    print(f"  Píxeles rellenados y suavizados: {int(zona.sum()):,}")
    return trabajo


def quitar_picos(alturas, umbral):
    total = 0
    for _ in range(3):
        med = mediana_3x3(alturas)
        picos = np.abs(alturas - med) > umbral
        n = int(picos.sum())
        total += n
        if not n:
            break
        alturas = np.where(picos, med, alturas)
    print(f"  Picos aislados corregidos: {total:,}")
    return alturas


def sombreado(alturas, paso_x, paso_y, azimut, altura_sol):
    gy, gx = np.gradient(alturas, paso_y, paso_x)  # gy: hacia el sur (filas), gx: hacia el este
    pendiente = np.arctan(np.hypot(gx, gy))
    orientacion = np.arctan2(-gx, gy)  # 0 = la ladera mira al norte, sentido horario
    az, alt = np.radians(azimut), np.radians(altura_sol)
    hs = np.sin(alt) * np.cos(pendiente) + np.cos(alt) * np.sin(pendiente) * np.cos(az - orientacion)
    return np.clip(hs / np.sin(alt), 0.0, 1.5)  # 1.0 = terreno plano


def generar_texturas(args, bounds, alturas_finas, salida):
    """Procesa la imagen banda por banda y en franjas para no agotar la memoria."""
    lado = args.textura_max
    relacion = (bounds[3] - bounds[1]) / (bounds[2] - bounds[0])
    if relacion <= 1:
        w, h = lado, max(1, round(lado * relacion))
    else:
        w, h = max(1, round(lado / relacion)), lado

    # Factor de relieve sombreado, calculado a menor resolución (el relieve es suave) y ampliado.
    factor = None
    if args.sombreado > 0:
        wr, hr = max(2, w // 4), max(2, h // 4)
        alt_red = np.asarray(Image.fromarray(alturas_finas.astype("float32"), mode="F").resize((wr, hr), Image.BILINEAR))
        hs = sombreado(alt_red, (bounds[2] - bounds[0]) / wr, (bounds[3] - bounds[1]) / hr, args.azimut, args.altura_sol)
        f = 1 - args.sombreado + args.sombreado * hs                      # 1.0 = terreno plano
        factor = Image.fromarray(np.clip(f * 160, 0, 255).astype("uint8"), "L").resize((w, h), Image.BILINEAR)
        factor = np.asarray(factor)

    bandas = []
    with rasterio.open(args.imagen) as img:
        comprobar_crs(img, "La imagen")
        ventana = from_bounds(*bounds, transform=img.transform)
        for b in (1, 2, 3):
            crudo = img.read(b, window=ventana, out_shape=(h, w), resampling=Resampling.average,
                             boundless=True, fill_value=0)
            estirar = crudo.dtype != np.uint8
            if estirar:
                muestra = crudo[crudo > 0][::37]
                lo, hi = np.percentile(muestra, [2, 98]) if muestra.size else (0.0, 1.0)
            salida_b = np.empty((h, w), dtype=np.uint8)
            for f0 in range(0, h, 1024):
                seg = crudo[f0:f0 + 1024].astype("float32")
                if estirar:
                    seg = np.clip((seg - lo) / max(hi - lo, 1e-6), 0, 1) ** 0.9 * 255
                if factor is not None:
                    seg = seg * (factor[f0:f0 + 1024].astype("float32") / 160.0)
                salida_b[f0:f0 + 1024] = np.clip(seg, 0, 255).astype(np.uint8)
            del crudo
            bandas.append(Image.fromarray(salida_b, "L"))
    imagen = Image.merge("RGB", bandas)
    del bandas
    imagen.save(salida / "textura_8192.jpg", quality=86, optimize=True, progressive=True)
    imagen.resize((max(1, w // 2), max(1, h // 2)), Image.LANCZOS).save(
        salida / "textura_4096.jpg", quality=86, optimize=True, progressive=True)
    print(f"  Texturas: {w}x{h} y {w // 2}x{h // 2} px, sombreado {args.sombreado:.0%}")


def main():
    args = parametros()
    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    with rasterio.open(args.mdt) as ds:
        comprobar_crs(ds, "El MDT")
        bounds = tuple(args.extension) if args.extension else tuple(ds.bounds)
        print(f"Extensión EPSG:9377: E {bounds[0]:.1f}–{bounds[2]:.1f}, N {bounds[1]:.1f}–{bounds[3]:.1f}")
        ventana = from_bounds(*bounds, transform=ds.transform)
        datos = ds.read(1, window=ventana, boundless=True, fill_value=ds.nodata if ds.nodata is not None else -32768,
                        masked=False).astype("float64")
        mascara = ds.read_masks(1, window=ventana, boundless=True) > 0
        if ds.nodata is not None:
            mascara &= datos != ds.nodata

    print("Limpiando el MDT...")
    fino = limpiar_mdt(datos, mascara, args)

    ancho = args.ancho
    alto = max(2, round(ancho * (bounds[3] - bounds[1]) / (bounds[2] - bounds[0])))
    reducido = Image.fromarray(fino.astype("float32"), mode="F").resize((ancho, alto), Image.BOX)
    alturas = np.asarray(reducido, dtype="float64")
    alturas = quitar_picos(alturas, args.umbral_pico)

    hmin, hmax = float(alturas.min()), float(alturas.max())
    print(f"  Rejilla: {ancho}x{alto} vértices, alturas {hmin:.1f}–{hmax:.1f} m")
    if not (np.isfinite(alturas).all() and hmin >= args.min_valido and hmax <= args.max_valido):
        sys.exit("ERROR: después de limpiar, siguen quedando alturas no plausibles. Revisa el MDT de entrada.")
    salto = max(np.abs(np.diff(alturas, axis=0)).max(), np.abs(np.diff(alturas, axis=1)).max())
    paso_x = (bounds[2] - bounds[0]) / ancho
    paso_y = (bounds[3] - bounds[1]) / alto
    print(f"  Paso de la rejilla: {paso_x:.1f} x {paso_y:.1f} m; mayor salto entre vecinos: {salto:.1f} m")

    alturas.astype("<f4").tofile(salida / "alturas.bin")
    meta = {
        "crs": "EPSG:9377",
        "registro": "centro de celda",
        "orden": "filas de norte a sur, columnas de oeste a este, Float32 little-endian",
        "ancho": ancho,
        "alto": alto,
        "este_min": bounds[0], "norte_min": bounds[1], "este_max": bounds[2], "norte_max": bounds[3],
        "paso_x": paso_x, "paso_y": paso_y,
        "altura_min": hmin, "altura_max": hmax,
        "fuente": Path(args.mdt).name,
        "generado": date.today().isoformat(),
    }
    if args.imagen:
        print("Generando texturas alineadas...")
        generar_texturas(args, bounds, fino, salida)
        meta["textura"] = {"8192": "textura_8192.jpg", "4096": "textura_4096.jpg",
                           "sombreado": args.sombreado, "azimut_sol": args.azimut, "altura_sol": args.altura_sol}
    (salida / "terreno.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Listo: {salida / 'alturas.bin'} ({(salida / 'alturas.bin').stat().st_size / 1e6:.1f} MB) y terreno.json")


if __name__ == "__main__":
    main()
