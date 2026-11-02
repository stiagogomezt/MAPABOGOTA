"""Fusion MDT urbano (UAECD 2014) con Copernicus GLO-30 (relleno), harmonizacion y transicion.
Ejecutar con .venv python: python scripts/mdt_fuse.py
"""
import os, json, subprocess, numpy as np, rasterio
from rasterio.crs import CRS
from rasterio.warp import reproject, Resampling, calculate_default_transform
from rasterio.transform import from_bounds
from PIL import Image

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MDT_URBAN=os.path.join(ROOT,'data','processed','terrain','mdt_urban_9377_5m.tif')
COPERNICUS=os.path.join(ROOT,'data','processed','terrain','dem_9377_10m.tif')
OUT_TIF=os.path.join(ROOT,'data','processed','terrain','mdt_fused_9377_5m.tif')
OUT_PNG=os.path.join(ROOT,'data','processed','terrain','heightmap_16bit.png')
GEOREF=os.path.join(ROOT,'data','processed','terrain','georef.json')
HRANGE=os.path.join(ROOT,'data','processed','terrain','height_range.json')
QGIS_PY='C:/Program Files/QGIS 4.2.3/bin/python-qgis.bat'
RES=5.0
AOI=(4850000.0,2040000.0,4905000.0,2105000.0)
xmin,ymin,xmax,ymax=AOI
width=int((xmax-xmin)/RES); height=int((ymax-ymin)/RES)
dst_transform=rasterio.Affine(RES,0,xmin,0,-RES,ymax)

# load MDT urban, pad to AOI grid
with rasterio.open(MDT_URBAN) as src:
    mdt_src=src.read(1).astype('float32')
    mdt_nd=src.nodata if src.nodata is not None else -9999.0
    mdt_src[mdt_src==mdt_nd]=np.nan
    gt=src.transform
mdt_full=np.full((height,width),np.nan,dtype='float32')
col0=int(round((gt.c if hasattr(gt,'c') else gt[2]-xmin)/RES)) if False else int(round((gt[2]-xmin)/RES))
row0=int(round((ymax-gt[5])/RES))  # gt[5] is top? transform (a,b,c,d,e,f): top=gt[5]? Actually transform.f is top y for north-up? rasterio transform: (a,b,c,d,e,f) with c=top-left x, f=top-left y.
# recompute properly
col0=int(round((gt.c - xmin)/RES))
row0=int(round((ymax - gt.f)/RES))
h_m,w_m=mdt_src.shape
r0=max(0,row0); c0=max(0,col0)
r1=min(height,row0+h_m); c1=min(width,col0+w_m)
sr0=r0-row0; sc0=c0-col0
er0=sr0+(r1-r0); ec0=sc0+(c1-c0)
mdt_full[r0:r1,c0:c1]=mdt_src[sr0:er0,sc0:ec0]
mdt=mdt_full

# resample Copernicus to 5m grid with nodata handling
with rasterio.open(COPERNICUS) as src:
    cop=np.zeros((height,width),dtype='float32')
    reproject(source=rasterio.band(src,1), destination=cop,
              src_transform=src.transform, src_crs=src.crs,
              dst_transform=dst_transform, dst_crs=CRS.from_epsg(9377),
              resampling=Resampling.bilinear, dst_nodata=-9999.0)
cop[cop==-9999.0]=np.nan

mask_mdt=~np.isnan(mdt)
mask_fill=~mask_mdt  # areas where MDT invalid (use Copernicus)

# harmonization in overlap
overlap=mask_mdt & ~np.isnan(cop)
diff=cop[overlap]-mdt[overlap]
mean_diff=float(np.nanmean(diff)); std_diff=float(np.nanstd(diff))
cop_corr=cop - mean_diff
print(f'Overlap pixels: {overlap.sum()}')
print(f'Mean diff (Copernicus - MDT): {mean_diff:.3f} m, std: {std_diff:.3f} m')

# write masks for proximity
import rasterio as _r
def write_mask(arr,path):
    prof={'driver':'GTiff','height':arr.shape[0],'width':arr.shape[1],'count':1,'dtype':'uint8','crs':CRS.from_epsg(9377),'transform':dst_transform,'nodata':0}
    with _r.open(path,'w',**prof) as d: d.write(arr.astype('uint8'),1)
mask_mdt_path=os.path.join(ROOT,'data','processed','terrain','_mask_mdt.tif')
mask_fill_path=os.path.join(ROOT,'data','processed','terrain','_mask_fill.tif')
write_mask(mask_mdt.astype('uint8'),mask_mdt_path)
write_mask(mask_fill.astype('uint8'),mask_fill_path)

# proximity via QGIS python
dist_mdt_path=os.path.join(ROOT,'data','processed','terrain','_dist_mdt.tif')
dist_fill_path=os.path.join(ROOT,'data','processed','terrain','_dist_fill.tif')
for mask,out in [(mask_mdt_path,dist_mdt_path),(mask_fill_path,dist_fill_path)]:
    subprocess.run(['C:/Program Files/QGIS 4.2.3/bin/python-qgis.bat','scripts/mdt_proximity.py',mask,out,'300'],check=True,cwd=ROOT)
    print('proximity done', out)

def read_raster(path):
    with rasterio.open(path) as s: return s.read(1).astype('float32')

dist_mdt=read_raster(dist_mdt_path)   # distance to nearest MDT pixel
dist_fill=read_raster(dist_fill_path)  # distance to nearest fill pixel
signed=dist_fill - dist_mdt
w=np.clip((signed+300.0)/600.0,0.0,1.0).astype('float32')

# fuse
mdt_safe=np.where(np.isnan(mdt),cop_corr,mdt)
cop_safe=np.where(np.isnan(cop),mdt,cop_corr)
blend_val=w*mdt_safe + (1-w)*cop_safe
trans=np.abs(signed)<300
fused=np.where(mask_mdt & ~mask_fill, mdt,
       np.where(~mask_mdt & mask_fill, cop_corr,
       np.where(mask_mdt & mask_fill, mdt, np.nan)))
fused=np.where(trans, blend_val, fused)
fused=np.where(np.isnan(fused), cop_corr, fused)
fused=np.where(np.isnan(fused), mdt, fused)

# save tif
prof={'driver':'GTiff','height':height,'width':width,'count':1,'dtype':'float32','crs':CRS.from_epsg(9377),'transform':dst_transform,'nodata':-9999.0}
fused_out=np.where(np.isnan(fused),-9999.0,fused).astype('float32')
with rasterio.open(OUT_TIF,'w',**prof) as d: d.write(fused_out,1)

# heightmap
valid=fused[~np.isnan(fused)]
vmin=float(np.nanmin(valid)); vmax=float(np.nanmax(valid)); rng=vmax-vmin
scaled=np.clip((fused-vmin)/rng*65535.0,0,65535.0).astype('uint16')
scaled[np.isnan(fused)]=0
Image.fromarray(scaled,mode='I;16').save(OUT_PNG)

georef={'crs':'EPSG:9377','extent_m':{'xmin':xmin,'ymin':ymin,'xmax':xmax,'ymax':ymax},'pixel_size_m':RES,'width_px':width,'height_px':height,'origin_local_m':[xmin,ymax],'height_range_m':{'min':vmin,'max':vmax},'vertical_exaggeration':1.5,'nodata':-9999.0,'datum_vertical':'MDT UAECD 2014 (gravity-related height, m) + Copernicus GLO-30 harmonizado','harmonization':{'mean_diff_copernicus_minus_mdt_m':mean_diff,'std_diff_m':std_diff,'transition_m':300}}
open(GEOREF,'w').write(json.dumps(georef,indent=2))
open(HRANGE,'w').write(json.dumps({'min_m':vmin,'max_m':vmax,'range_m':rng},indent=2))

# cleanup
for f in [mask_mdt_path,mask_fill_path,dist_mdt_path,dist_fill_path]:
    try: os.remove(f)
    except: pass
print(f'Fused MDT: {width}x{height}, altura {vmin:.1f}-{vmax:.1f} m')
print(f'Mean diff: {mean_diff:.3f} m, std: {std_diff:.3f} m')