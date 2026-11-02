import numpy as np, rasterio
from PIL import Image
src=rasterio.open('data/processed/terrain/mdt_fused_9377_5m.tif')
a=src.read(1).astype('float32')
a[a==-9999]=np.nan
# fill nan with nearest (simple)
# gradient
gy,gx=np.gradient(a)
# normal = (-gx, -gy, 1) normalized
nx=-gx; ny=-gy; nz=np.ones_like(a)
norm=np.sqrt(nx*nx+ny*ny+nz*nz)
nx/=norm; ny/=norm; nz/=norm
# encode to 0-255 (normal map convention: (n+1)/2)
rgb=np.zeros((a.shape[0],a.shape[1],3),dtype='uint8')
rgb[:,:,0]=((nx+1)/2*255).astype('uint8')
rgb[:,:,1]=((ny+1)/2*255).astype('uint8')
rgb[:,:,2]=((nz+1)/2*255).astype('uint8')
from PIL import Image
small=Image.fromarray(rgb).resize((4096, int(4096*rgb.shape[0]/rgb.shape[1])), Image.LANCZOS)
small.save('web/terrain/normalmap.jpg',quality=90)
print('saved normalmap.jpg', small.size)