import os, numpy as np, rasterio
from rasterio.merge import merge
from rasterio.transform import from_bounds
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE=os.path.join(ROOT,'data','raw','mdt')
tiles=sorted([os.path.join(CACHE,f) for f in os.listdir(CACHE) if f.startswith('ndsm_5m_') and f.endswith('.tiff')])
# normalize nodata to -9999
norm_tiles=[]
for t in tiles:
    with rasterio.open(t) as src:
        a=src.read(1).astype('float32')
        a[a<-1e30]=-9999.0
        prof=src.profile.copy()
        prof.update(nodata=-9999.0,dtype='float32')
        out=t.replace('.tiff','_norm.tiff')
        with rasterio.open(out,'w',**prof) as d:
            d.write(a,1)
        norm_tiles.append(out)
srcs=[rasterio.open(t) for t in norm_tiles]
mosaic,transform=merge(srcs,nodata=-9999.0)
if mosaic.ndim==3: mosaic=mosaic[0]
prof=srcs[0].profile.copy()
prof.update(height=mosaic.shape[0],width=mosaic.shape[1],transform=transform,crs=srcs[0].crs,nodata=-9999.0,count=1)
out=os.path.join(CACHE,'ndsm_5m_3116.tif')
with rasterio.open(out,'w',**prof) as d:
    d.write(mosaic,1)
for s in srcs: s.close()
# cleanup norm
for t in norm_tiles:
    try: os.remove(t)
    except: pass
print('mosaic shape',mosaic.shape,'min',np.nanmin(mosaic[mosaic!=-9999]),'max',np.nanmax(mosaic))