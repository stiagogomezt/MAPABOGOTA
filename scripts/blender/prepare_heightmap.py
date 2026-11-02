import os, numpy as np
from PIL import Image
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src=os.path.join(ROOT,'data','processed','terrain','heightmap_16bit.png')
Image.MAX_IMAGE_PIXELS=None
im=Image.open(src)
arr=np.array(im).astype('np'.replace('np','')) if False else np.array(im).astype('uint32')
# PIL can't read I;16 directly? try
try:
    arr=np.array(im).astype('uint16')
except Exception as e:
    print('read err',e)
    arr=None
if arr is None:
    import struct
    # fallback: use rasterio
    import rasterio
    with rasterio.open(src) as s:
        arr=s.read(1).astype('uint16')
w=1024; h=int(arr.shape[0]*1024/arr.shape[1])
small_arr=np.array(Image.fromarray(arr.astype('float32')).resize((w,h),Image.BILINEAR)).astype('uint16')
out=os.path.join(ROOT,'data','processed','terrain','heightmap_blender.png')
Image.fromarray(small_arr,mode='I;16').save(out)
print('saved',out,w,h)