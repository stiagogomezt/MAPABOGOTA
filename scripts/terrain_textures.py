"""Genera texturas tematicas (8192 y 4096 px) para el visor 3D."""
import os, numpy as np, rasterio, geopandas as gpd
from rasterio.warp import reproject, Resampling
from PIL import Image, ImageDraw, ImageFont
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TERR=os.path.join(ROOT,'data','processed','terrain')
AOI=(4850000.0,2040000.0,4905000.0,2105000.0)
xmin,ymin,xmax,ymax=AOI
RES_BASE=10.0  # satellite composite resolution
# satellite source
SAT=os.path.join(TERR,'sentinel2_rgb_9377.tif')

def load_sat(size):
    with rasterio.open(SAT) as src:
        # read full AOI at native 10m -> 5500x6500, then resize
        arr=src.read()  # (3,H,W)
    img=Image.fromarray(np.dstack([arr[0],arr[1],arr[2]]))
    return img.resize((size,int(size*(ymax-ymin)/(xmax-xmin))), Image.LANCZOS)

def world_to_px(x,y,size):
    w=size; h=int(size*(ymax-ymin)/(xmax-xmin))
    c=int((x-xmin)/(xmax-xmin)*w)
    r=int((ymax-y)/(ymax-ymin)*h)
    return c,r

# (a) already exists as texture_satellite_*.jpg
for size in (8192,4096):
    if not os.path.exists(os.path.join(TERR,f'texture_satellite_{size}.jpg')):
        img=load_sat(size)
        img.save(os.path.join(TERR,f'texture_satellite_{size}.jpg'),quality=92)
        print('satellite',size)

# (d) hillshade + hypsometry
for size in (8192,4096):
    # load hillshade and hypsometry, resize
    with rasterio.open(os.path.join(TERR,'hillshade.tif')) as s: hs=s.read(1)
    with rasterio.open(os.path.join(TERR,'hypsometry.tif')) as s: hyp=s.read()  # (3,H,W) or (4?) 
    # hypsometry is RGB
    if hyp.shape[0]>=3:
        hyp_img=Image.fromarray(np.dstack([hyp[0],hyp[1],hyp[2]]))
    else:
        hyp_img=Image.fromarray(hyp[0])
    hs_img=Image.fromarray(hs).convert('L')
    # resize
    w=size; h=int(size*(ymax-ymin)/(xmax-xmin))
    hyp_r=hyp_img.resize((w,h),Image.LANCZOS)
    hs_r=hs_img.resize((w,h),Image.LANCZOS)
    # blend: multiply hypsometry by hillshade
    hyp_arr=np.array(hyp_r).astype('float32')
    hs_arr=np.array(hs_r).astype('float32')/255.0
    # hillshade as lighting factor
    out=np.clip(hyp_arr* (0.4+0.6*hs_arr[:,:,None]),0,255).astype('uint8')
    Image.fromarray(out).save(os.path.join(TERR,f'texture_relief_{size}.jpg'),quality=92)
    print('relief',size)

# (e) slopes colorized
for size in (8192,4096):
    with rasterio.open(os.path.join(TERR,'slope.tif')) as s: sl=s.read(1)
    # color ramp: 0-5 green, 5-15 yellow, 15-30 orange, >30 red
    w=size; h=int(size*(ymax-ymin)/(xmax-xmin))
    sl_r=Image.fromarray(sl).resize((w,h),Image.LANCZOS)
    sla=np.array(sl_r).astype('float32')
    # normalize 0-90
    rgb=np.zeros((h,w,3),dtype='uint8')
    # green for low
    low=sla<5; mid=(sla>=5)&(sla<15); high=(sla>=15)&(sla<30); vhigh=sla>=30
    rgb[low]=[120,180,120]
    rgb[mid]=[220,200,100]
    rgb[high]=[230,140,60]
    rgb[vhigh]=[200,60,60]
    # blend with satellite? keep slope colors
    Image.fromarray(rgb).save(os.path.join(TERR,f'texture_slope_{size}.jpg'),quality=92)
    print('slope',size)

# (b) satellite + localities
loc=gpd.read_file(os.path.join(ROOT,'data','raw','localidad.geojson'))
loc=loc.to_crs('EPSG:9377')
for size in (8192,4096):
    img=load_sat(size).convert('RGBA')
    draw=ImageDraw.Draw(img,'RGBA')
    w,h=img.size
    # draw boundaries
    for _,row in loc.iterrows():
        geom=row.geometry
        if geom is None: continue
        polys=[geom] if geom.geom_type=='Polygon' else (geom.geoms if hasattr(geom,'geoms') else [])
        for poly in polys:
            coords=[world_to_px(x,y,size) for x,y in poly.exterior.coords]
            draw.line(coords,fill=(255,255,255,180),width=2)
            # label centroid
            cx,cy=poly.centroid.x,poly.centroid.y
            px,py=world_to_px(cx,cy,size)
            name=row.get('LOCNOMBRE') or row.get('NOMBRE') or ''
            try:
                draw.text((px,py), str(name), fill=(255,255,255,230))
            except: pass
    img.convert('RGB').save(os.path.join(TERR,f'texture_localidades_{size}.jpg'),quality=92)
    print('localidades',size)

# (c) satellite + valor/estrato semitransparente
manz=gpd.read_file(os.path.join(ROOT,'data','processed','phase2','manzanas_indicadores.gpkg'))
manz=manz.to_crs('EPSG:9377')
for size in (8192,4096):
    img=load_sat(size).convert('RGBA')
    overlay=Image.new('RGBA',img.size,(0,0,0,0))
    draw=ImageDraw.Draw(overlay,'RGBA')
    # color by estrato if available else value
    field='estrato' if 'estrato' in manz.columns else 'valor_ref_m2'
    # normalize
    vals=manz[field].astype(float) if field in manz.columns else None
    vmin=float(vals.min()) if vals is not None else 0
    vmax=float(vals.max()) if vals is not None else 1
    for _,row in manz.iterrows():
        geom=row.geometry
        if geom is None: continue
        polys=[geom] if geom.geom_type=='Polygon' else (list(geom.geoms) if hasattr(geom,'geoms') else [])
        v=float(row[field]) if field in row and row[field] is not None else vmin
        # color ramp blue->red
        t=(v-vmin)/(vmax-vmin) if vmax>vmin else 0.5
        color=(int(50+200*t), int(100+100*(1-t)), int(200-150*t), 90)
        for poly in polys:
            coords=[world_to_px(x,y,size) for x,y in poly.exterior.coords]
            draw.polygon(coords,fill=color)
    out=Image.alpha_composite(img,overlay).convert('RGB')
    out.save(os.path.join(TERR,f'texture_valor_{size}.jpg'),quality=92)
    print('valor',size)

print('done textures')