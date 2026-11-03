import json, numpy as np, rasterio
ROOT=__import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
mdt_path=ROOT+'/data/processed/terrain/mdt_fused_9377_5m.tif'
src=rasterio.open(mdt_path)
a=src.read(1).astype('float32')
a[a==src.nodata]=np.nan
transform=src.transform
# Plaza de Bolivar ~ E=4877500, N=2072500 (EPSG:9377)
# Profile along latitude (N=2072500), from Rio Bogota (west) to 4km east of Monserrate
# Rio Bogota ~ E=4855000, Monserrate ~ E=4881000, 4km east = E=4885000
# Actually, let's go from E=4850000 to E=4890000
xmin_p=4850000; xmax_p=4890000; step=50
n=int((xmax_p-xmin_p)/step)+1
xs=np.linspace(xmin_p,xmax_p,n)
ys=np.full(n,2072500.0)
# sample
pts=[]
for x,y in zip(xs,ys):
    c=int((x-transform.c)/transform.a)
    r=int((transform.f-y)/(-transform.e))
    if 0<=r<a.shape[0] and 0<=c<a.shape[1]:
        h=a[r,c]
        if not np.isnan(h):
            pts.append([round((x-xmin_p)/1000,3), round(float(h),1)])
# marks
marks=[
    {"nombre":"Rio Bogota","km":round((4855000-xmin_p)/1000,3)},
    {"nombre":"Plaza de Bolivar","km":round((4877500-xmin_p)/1000,3)},
    {"nombre":"Monserrate","km":round((4881000-xmin_p)/1000,3)},
]
data={"ilustrativo":False,"puntos":pts,"marcas":marks}
out=ROOT+'/web/data/perfil_portada.json'
import os; os.makedirs(ROOT+'/web/data',exist_ok=True)
open(out,'w').write(json.dumps(data,indent=2))
print('saved',out,'points',len(pts))