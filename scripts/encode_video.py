import os, glob, imageio
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frames=sorted(glob.glob(os.path.join(ROOT,'web','media','frames','frame_*.png')))
print('frames',len(frames))
writer=imageio.get_writer(os.path.join(ROOT,'web','media','bogota_flyover.mp4'),fps=30,codec='libx264',quality=7,bitrate='6M')
for f in frames:
    writer.append_data(imageio.imread(f))
writer.close()
# poster from middle frame
mid=frames[len(frames)//2]
poster=imageio.imread(mid)
if poster.shape[-1]==4: poster=poster[:,:,:3]
imageio.imwrite(os.path.join(ROOT,'web','media','poster.jpg'), poster)
print('done')