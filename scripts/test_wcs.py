import requests, rasterio
url='https://serviciosgis.catastrobogota.gov.co/arcgis/services/imagenes/ModeloDigitalTerreno2014/MapServer/WCSServer'
q='service=WCS&version=2.0.1&request=GetCoverage&coverageId=Coverage1&format=image/tiff&subset=x(-8245757,-8245657)&subset=y(512297,512397)'
r=requests.get(url+'?'+q,timeout=120)
data=r.content
parts=data.split(b'--wcs')
p=[x for x in parts if b'image/tiff' in x.lower()][1]
sep=p.find(b'\n\n')
body=p[sep+2:].rstrip(b'\r\n-')
open('t.tiff','wb').write(body)
src=rasterio.open('t.tiff')
print('size',src.width,src.height,'dtype',src.dtypes)
a=src.read(1)
print('min',a.min(),'max',a.max(),'mean',a.mean())