"""Calcula raster de proximidad (distancia en metros) a pixeles con valor 1.
Uso: python-qgis.bat scripts/mdt_proximity.py <mask.tif> <out.tif> <maxdist>
"""
import sys, os
from osgeo import gdal

mask_path=sys.argv[1]; out_path=sys.argv[2]; maxdist=sys.argv[3]
src=gdal.Open(mask_path)
drv=gdal.GetDriverByName('GTiff')
dst=drv.Create(out_path,src.RasterXSize,src.RasterYSize,1,gdal.GDT_Float32)
dst.SetGeoTransform(src.GetGeoTransform()); dst.SetProjection(src.GetProjection())
gdal.ComputeProximity(src.GetRasterBand(1), dst.GetRasterBand(1), ['DISTUNITS=GEO','MAXDIST='+maxdist])
dst.FlushCache(); dst=None; src=None
print('done', out_path)