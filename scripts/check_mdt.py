import numpy as np
from osgeo import gdal
ds=gdal.Open('data/processed/terrain/mdt_fused_9377_5m.tif')
a=ds.GetRasterBand(1).ReadAsArray().astype('float32')
print('shape',a.shape)
print('min',a.min(),'max',a.max())
print('neg count', int((a<0).sum()), 'nan count', int(np.isnan(a).sum()))
idx=np.unravel_index(np.nanargmin(a),a.shape)
print('min loc',idx,'val',a[idx])
gt=ds.GetGeoTransform()
x=gt[0]+idx[1]*gt[1]; y=gt[3]+idx[0]*gt[5]
print('min coord',x,y)
# percentiles
print('p1',np.nanpercentile(a,1),'p99',np.nanpercentile(a,99))