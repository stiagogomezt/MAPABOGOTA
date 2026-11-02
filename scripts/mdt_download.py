"""Descarga MDT 2014 (UAECD) y nDSM via WCS 1.0.0 a 5 m, por bloques, con cache.

Salidas:
  data/raw/mdt/mdt_2014_5m_3857.tif
  data/raw/mdt/ndsm_5m_3116.tif
  data/processed/terrain/mdt_urban_9377_5m.tif
"""
import os, math, time, requests, numpy as np, rasterio
from rasterio.transform import from_origin
from rasterio.crs import CRS
from rasterio.warp import reproject, Resampling, calculate_default_transform
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'data'/'raw'/'mdt'
CACHE.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'data'/'processed'/'terrain'
OUT.mkdir(parents=True,exist_ok=True)
RES=5.0

def wcs_getcoverage(url, coverage, crs, bbox, res, fmt='GeoTIFF', retries=3):
    # bbox: (xmin,ymin,xmax,ymax) in crs units
    params = {
        'service':'WCS','version':'1.0.0','request':'GetCoverage',
        'coverage':coverage,'crs':crs,'bbox':f'{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}',
        'format':fmt,'resx':res,'resy':res,
    }
    q='&'.join(f'{k}={v}' for k,v in params.items())
    for attempt in range(retries):
        try:
            r=requests.get(url+'?'+q,timeout=300)
            if r.status_code==200 and r.headers.get('content-type','').startswith('image'):
                return r.content
            print(f'  intento {attempt+1}: status {r.status_code} ctype {r.headers.get("content-type")}')
        except Exception as e:
            print(f'  intento {attempt+1}: {e}')
        time.sleep(2*(attempt+1))
    raise RuntimeError(f'Fallo descarga {bbox}')

def download_mdt_urban():
    url='https://serviciosgis.catastrobogota.gov.co/arcgis/services/imagenes/ModeloDigitalTerreno2014/MapServer/WCSServer'
    # extent en EPSG:3857
    xmin,ymin,xmax,ymax=-8262734.5129,495702.2404,-8238496.2165,539270.7670
    block=2000*RES  # 10 km
    xs=np.arange(xmin,xmax,block)
    ys=np.arange(ymin,ymax,block)
    tiles=[]
    for xi,x0 in enumerate(xs):
        for yi,y0 in enumerate(ys):
            x1=min(x0+block,xmax); y1=min(y0+block,ymax)
            cache=CACHE/f'mdt_2014_5m_{xi}_{yi}.tiff'
            if cache.exists():
                print(f'MDT bloque {xi},{yi} (cache)')
            else:
                print(f'MDT bloque {xi},{yi} descargando...')
                content=wcs_getcoverage(url,'1','EPSG:3857',(x0,y0,x1,y1),RES)
                cache.write_bytes(content)
            tiles.append((xi,yi,x0,y0,x1,y1,cache))
    # mosaic
    # read first to get dtype
    with rasterio.open(tiles[0][6]) as s:
        profile=s.profile.copy()
    # build mosaic manually using rasterio merge
    from rasterio.merge import merge
    srcs=[rasterio.open(t[6]) for t in tiles]
    mosaic,transform=merge(srcs)
    profile.update(height=mosaic.shape[1],width=mosaic.shape[2],transform=transform,crs=CRS.from_epsg(3857))
    out=CACHE/'mdt_2014_5m_3857.tif'
    with rasterio.open(out,'w',**profile) as dst:
        dst.write(mosaic)
    for s in srcs: s.close()
    print(f'MDT mosaico 3857: {mosaic.shape}')
    # reproject to EPSG:9377
    dst_crs=CRS.from_epsg(9377)
    transform9377,width,height=calculate_default_transform(CRS.from_epsg(3857),dst_crs,mosaic.shape[2],mosaic.shape[1],*rasterio.transform.array_bounds(mosaic.shape[1],mosaic.shape[2],transform),resolution=RES)
    profile9377=profile.copy()
    profile9377.update(crs=dst_crs,transform=transform9377,width=width,height=height,dtype='float32')
    data=np.zeros((height,width),dtype='float32')
    reproject(source=rasterio.band(rasterio.open(out),1),destination=data,src_transform=transform,src_crs=CRS.from_epsg(3857),dst_transform=transform9377,dst_crs=dst_crs,resampling=Resampling.bilinear,dst_nodata=-9999.0)
    out9377=OUT/'mdt_urban_9377_5m.tif'
    profile9377.update(nodata=-9999.0)
    with rasterio.open(out9377,'w',**profile9377) as dst:
        dst.write(data,1)
    print(f'MDT urbano 9377: {width}x{height}')

def download_ndsm():
    url='https://serviciosgis.catastrobogota.gov.co/arcgis/services/topografia/nDSM/MapServer/WCSServer'
    xmin,ymin,xmax,ymax=958000.041,904000.0,999000.041,985000.0  # EPSG:3116
    block=2000*RES
    xs=np.arange(xmin,xmax,block); ys=np.arange(ymin,ymax,block)
    tiles=[]
    for xi,x0 in enumerate(xs):
        for yi,y0 in enumerate(ys):
            x1=min(x0+block,xmax); y1=min(y0+block,ymax)
            cache=CACHE/f'ndsm_5m_{xi}_{yi}.tiff'
            if cache.exists():
                print(f'nDSM bloque {xi},{yi} (cache)')
            else:
                print(f'nDSM bloque {xi},{yi} descargando...')
                content=wcs_getcoverage(url,'1','EPSG:3116',(x0,y0,x1,y1),RES)
                cache.write_bytes(content)
            tiles.append(cache)
    from rasterio.merge import merge
    srcs=[rasterio.open(t) for t in tiles]
    mosaic,transform=merge(srcs)
    profile=srcs[0].profile.copy()
    profile.update(height=mosaic.shape[1],width=mosaic.shape[2],transform=transform,crs=CRS.from_epsg(3116))
    out=CACHE/'ndsm_5m_3116.tif'
    with rasterio.open(out,'w',**profile) as dst:
        dst.write(mosaic)
    for s in srcs: s.close()
    print(f'nDSM mosaico 3116: {mosaic.shape}')

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--mdt',action='store_true')
    ap.add_argument('--ndsm',action='store_true')
    ap.add_argument('--all',action='store_true')
    a=ap.parse_args()
    if a.all or (not a.mdt and not a.ndsm):
        a.mdt=True; a.ndsm=True
    if a.mdt: download_mdt_urban()
    if a.ndsm: download_ndsm()