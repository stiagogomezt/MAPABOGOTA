"""Muestra: compara altura por pisos*3 m con mediana del nDSM oficial."""
import os, numpy as np, rasterio, geopandas as gpd
from rasterio.warp import reproject, Resampling
from shapely.geometry import box

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NDSM=os.path.join(ROOT,'data','raw','mdt','ndsm_5m_3116.tif')
OUT=os.path.join(ROOT,'data','processed','terrain','ndsm_9377_5m.tif')
RES=5.0
AOI=(4850000.0,2040000.0,4905000.0,2105000.0)
xmin,ymin,xmax,ymax=AOI
width=int((xmax-xmin)/RES); height=int((ymax-ymin)/RES)
dst_transform=rasterio.Affine(RES,0,xmin,0,-RES,ymax)

# reproject ndsm to 9377 if not exists
if not os.path.exists(OUT) or True:
    with rasterio.open(NDSM) as src:
        raw=src.read(1).astype('float32')
        raw[(raw<-9000)|(raw<=0)|(raw>200)]=np.nan
        from rasterio.io import MemoryFile
        prof=src.profile.copy(); prof.update(dtype='float32',nodata=np.nan,count=1)
        with MemoryFile() as mem:
            with mem.open(**prof) as ds:
                ds.write(raw,1); ds.transform=src.transform
                arr=np.zeros((height,width),dtype='float32')
                reproject(source=rasterio.band(ds,1), destination=arr, src_transform=ds.transform, src_crs=src.crs,
                          dst_transform=dst_transform, dst_crs='EPSG:9377', resampling=Resampling.bilinear, dst_nodata=np.nan)
    arr[np.isnan(arr)]=np.nan
    prof={'driver':'GTiff','height':height,'width':width,'count':1,'dtype':'float32','crs':'EPSG:9377','transform':dst_transform,'nodata':-9999.0}
    arr2=np.where(np.isnan(arr),-9999.0,arr).astype('float32')
    with rasterio.open(OUT,'w',**prof) as d: d.write(arr2,1)
    print('ndsm reprojected')

with rasterio.open(OUT) as src:
    ndsm=src.read(1).astype('float32'); transform=src.transform
ndsm[ndsm==-9999.0]=np.nan

gdf=gpd.read_file(os.path.join(ROOT,'data','processed','phase2','construcciones_3d.gpkg'))
# sample 500
sample=gdf.sample(n=min(500,len(gdf)), random_state=42).copy()
def sample_median(geom):
    # bounding box of geometry in pixel coords
    minx,miny,maxx,maxy=geom.bounds
    c0=int((minx-xmin)/RES); r0=int((ymax-maxy)/RES)
    c1=int((maxx-xmin)/RES)+1; r1=int((ymax-miny)/RES)+1
    c0=max(0,c0); r0=max(0,r0); c1=min(width,c1); r1=min(height,r1)
    if c1<=c0 or r1<=r0: return np.nan
    vals=[]
    for r in range(r0,r1):
        for c in range(c0,c1):
            x=xmin+c*RES+RES/2; y=ymax-r*RES-RES/2
            if geom.contains(__import__('shapely.geometry',fromlist=['Point']).Point(x,y)):
                v=ndsm[r,c]
                if not np.isnan(v): vals.append(v)
    return float(np.median(vals)) if vals else np.nan

sample['h_ndsm']=sample.geometry.apply(sample_median)
sample['h_pisos']=sample['CONNPISOS'].astype(float)*3.0
valid=sample.dropna(subset=['h_ndsm'])
print('sample size',len(sample),'valid ndsm',len(valid))
print('median h_ndsm', valid['h_ndsm'].median())
print('median h_pisos', valid['h_pisos'].median())
print('corr', valid['h_ndsm'].corr(valid['h_pisos']))
print('mean diff (ndsm - pisos)', (valid['h_ndsm']-valid['h_pisos']).mean())
# save sample
out_csv=os.path.join(ROOT,'data','processed','terrain','volumetria_sample.csv')
valid[['CONCODIGO','CONNPISOS','h_pisos','h_ndsm']].to_csv(out_csv,index=False)
print('saved',out_csv)