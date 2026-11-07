import pathlib, shutil, json
from PIL import Image
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = pathlib.Path(r"C:\Users\kevin\Desktop\mapabogota")
outdir = root/"docs/bitacora/img"
outdir.mkdir(parents=True, exist_ok=True)
webdir = root/"web/bitacora/img"
webdir.mkdir(parents=True, exist_ok=True)

def save_resize(src, dst_name, crop_top=0, crop_bottom=0, maxw=1600):
    im = Image.open(src).convert("RGB")
    w,h = im.size
    if crop_top: im = im.crop((0,crop_top,w,h-crop_bottom))
    if im.width > maxw:
        ratio = maxw/im.width
        im = im.resize((maxw, int(im.height*ratio)), Image.LANCZOS)
    dst = outdir/dst_name
    im.save(dst, "JPEG", quality=82)
    # copy to web
    shutil.copy(dst, webdir/dst_name)
    print(dst_name, dst.stat().st_size)
    return dst_name

# 1 portada final
save_resize(root/"docs/capturas/interfaz_1440.png", "fig01_portada.jpg")
# 2 interfaz desktop
save_resize(root/"docs/capturas/visor_ok.png", "fig02_visor.jpg")
# 3 mobile
save_resize(root/"docs/capturas/interfaz_390.png", "fig03_movil.jpg")
# 4 blender
save_resize(r"C:\Users\kevin\Pictures\Screenshots\Screenshot 2026-10-31 191030.png", "fig04_blender.jpg", crop_top=30, crop_bottom=20)
# 5 satellite texture early
save_resize(r"C:\Users\kevin\Pictures\Screenshots\Screenshot 2026-11-02 070237.png", "fig05_satelital.jpg")
# 6 terrain streaks problem 2026-11-04
save_resize(r"C:\Users\kevin\Pictures\Screenshots\Screenshot 2026-11-04 171633.png", "fig06_agujas.jpg")
# 7 old visor textures 2026-11-02 192338
save_resize(r"C:\Users\kevin\Pictures\Screenshots\Screenshot 2026-11-02 192338.png", "fig07_texturas.jpg")
# 8 ficha wrong altitude cropped browser bar
save_resize(r"C:\Users\kevin\Pictures\Screenshots\Screenshot 2026-11-02 202528.png", "fig08_ficha_error.jpg", crop_top=170, crop_bottom=10)

# matplotlib figures from alturas.bin
arr = np.fromfile(root/"web/terrain/alturas.bin", dtype="<f4")
arr2d = arr.reshape(1211,1025)
# extent EPSG:9377
# este 4850000-4905000, norte 2040000-2105000, rows north to south
extent = [4850000,4905000,2040000,2105000]

plt.figure(figsize=(10,4))
plt.hist(arr, bins=120, color="#0F1B1E", edgecolor="#D6A24E", linewidth=0.5)
plt.axvline(np.median(arr), color="#D9715F", linestyle="--", label=f"mediana {np.median(arr):.1f} m")
plt.axvline(arr.mean(), color="#D6A24E", linestyle=":", label=f"media {arr.mean():.1f} m")
plt.xlabel("Altitud MDT (m s. n. m.)")
plt.ylabel("Frecuencia (celdas)")
plt.title("Histograma de altitudes del MDT fusionado (alturas.bin)")
plt.legend()
plt.tight_layout()
plt.savefig(outdir/"fig09_histograma.jpg", dpi=150)
plt.close()
shutil.copy(outdir/"fig09_histograma.jpg", webdir/"fig09_histograma.jpg")

# hillshade map
# simple hillshade
def hillshade(a, az=315, alt=45):
    az = np.deg2rad(360-az+90)
    alt = np.deg2rad(alt)
    d = np.gradient(a)
    slope = np.arctan(np.hypot(d[0], d[1]))
    aspect = np.arctan2(-d[1], d[0])
    hs = np.sin(alt)*np.cos(slope) + np.cos(alt)*np.sin(slope)*np.cos(az-aspect)
    return hs

hs = hillshade(arr2d)
plt.figure(figsize=(10,9))
ax = plt.subplot(111)
ax.imshow(hs, cmap="gray", extent=extent, origin="upper")
ax.set_xlabel("Este EPSG:9377 (m)")
ax.set_ylabel("Norte EPSG:9377 (m)")
ax.set_title("MDT fusionado, relieve sombreado (azimut 315°, altura 45°)\nÁrea 55 × 65 km, EPSG:9377, 1025 × 1211 celdas")
# north arrow
ax.annotate("N", xy=(0.95,0.95), xycoords="axes fraction", fontsize=16, ha="center",
            arrowprops=dict(facecolor="black", width=5, headwidth=10))
# scale bar 10 km
ax.plot([4850000,4860000],[2045000,2045000], color="red", lw=3)
ax.text(4855000,2047000,"10 km", ha="center", fontsize=9, bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"))
plt.tight_layout()
plt.savefig(outdir/"fig10_hillshade.jpg", dpi=150)
plt.close()
shutil.copy(outdir/"fig10_hillshade.jpg", webdir/"fig10_hillshade.jpg")

# profile west-east middle row
perfil = arr2d[600,:]  # approx middle
x = np.linspace(4850000,4905000,1025)
plt.figure(figsize=(10,4))
plt.plot(x, perfil, color="#0F1B1E", lw=1)
plt.fill_between(x, perfil, 1500, color="#D6A24E", alpha=0.3)
plt.xlabel("Este EPSG:9377 (m)")
plt.ylabel("Altitud (m)")
plt.title("Perfil topográfico oeste-este extraído de alturas.bin (fila central)")
plt.tight_layout()
plt.savefig(outdir/"fig11_perfil.jpg", dpi=150)
plt.close()
shutil.copy(outdir/"fig11_perfil.jpg", webdir/"fig11_perfil.jpg")

# file sizes bar
import json as js
audit = js.loads((root/"docs/collect_info.json").read_text())
sizes = audit["web_sizes"]
# largest 8
sizes_sorted = sorted(sizes, key=lambda x:x[1], reverse=True)[:8]
plt.figure(figsize=(10,5))
labels=[s[0].replace("web\\","").replace("web/","") for s in sizes_sorted]
vals=[s[1]/1024/1024 for s in sizes_sorted]
plt.barh(labels[::-1], vals[::-1], color="#0F1B1E", edgecolor="#D6A24E")
plt.xlabel("Tamaño (MB)")
plt.title("Archivos publicados más grandes en web/ (175 MB totales)")
plt.tight_layout()
plt.savefig(outdir/"fig12_tamanos.jpg", dpi=150)
plt.close()
shutil.copy(outdir/"fig12_tamanos.jpg", webdir/"fig12_tamanos.jpg")

# localidades map from geojson in web/descargas
try:
    gj = json.loads((root/"web/descargas/localidad.geojson").read_text(encoding="utf-8"))
    plt.figure(figsize=(9,9))
    for feat in gj["features"][:19]:
        geom = feat["geometry"]
        name = feat["properties"].get("LOCNOMBRE") or feat["properties"].get("name") or ""
        coords_list = []
        if geom["type"]=="Polygon":
            coords_list=[geom["coordinates"][0]]
        elif geom["type"]=="MultiPolygon":
            coords_list=[p[0] for p in geom["coordinates"]]
        for ring in coords_list:
            xs,ys=zip(*ring)
            plt.plot(xs,ys,color="#0F1B1E",lw=0.6)
            plt.fill(xs,ys,alpha=0.15,color="#D6A24E")
            # label centroid approx
            plt.text(sum(xs)/len(xs), sum(ys)/len(ys), name[:12], fontsize=6, ha="center")
    plt.xlabel("Longitud WGS84 (°)")
    plt.ylabel("Latitud WGS84 (°)")
    plt.title("Localidades de Bogotá D.C. (19, sin Sumapaz)\nFuente: UAECD/IDECA, EPSG:4326")
    plt.gca().set_aspect("equal")
    plt.tight_layout()
    plt.savefig(outdir/"fig13_localidades.jpg", dpi=150)
    plt.close()
    shutil.copy(outdir/"fig13_localidades.jpg", webdir/"fig13_localidades.jpg")
except Exception as e:
    print("localidades fail", e)

print("done")
