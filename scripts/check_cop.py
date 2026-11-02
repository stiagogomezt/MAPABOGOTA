from osgeo import gdal
import numpy as np
ds=gdal.Open('data/processed/terrain/dem_9377_10m.tif')
a=ds.GetRasterBand(1).ReadAsArray().astype('float32')
print('orig shape',a.shape,'min',np.nanmin(a),'max',np.nanmax(a))
# replicate warp
from osgeo import osr
RES=5.0; xmin,ymin,xmax,ymax=4850000.0,2040000.0,4905000.0,2105000.0
w=int((xmax-xmin)/RES); h=int((ymax-ymin)/RES)
drv=gdal.GetDriverByName('MEM')
dst=drv.Create('',w,h,1,gdal.GDT_Float32)
gt=(xmin,RES,0,ymax,0,-RES)
srs=osr.SpatialReference(); srs.ImportFromEPSG(9377)
dst.SetGeoTransform(gt); dst.SetProjection(srs.ExportToWkt())
gdal.Warp(dst,'data/processed/terrain/dem_9377_10m.tif', dstSRS='EPSG:9377', resampleAlg=gdal.GRA_Bilinear, outputBounds=(xmin,ymin,xmax,ymax), xRes=RES, yRes=RES, dstNodata=-9999.0)
arr=dst.GetRasterBand(1).ReadAsArray().astype('float32')
arr[arr==-9999.0]=np.nan
print('warped shape',arr.shape,'min',np.nanmin(arr),'max',np.nanmax(arr),'nan',np.isnan(arr).sum())