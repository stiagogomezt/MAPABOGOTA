import json, numpy as np, os
ctrl = np.array([
    [-5000, -30000, 6000],
    [15000, -5000, 5000],
    [10000, 5000, 4500],
    [5000, 15000, 5000],
    [-5000, 28000, 6000],
], dtype=float)
def catmull_rom(p0,p1,p2,p3,t):
    return 0.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
pts=[]
for i in range(len(ctrl)-1):
    p0=ctrl[max(0,i-1)]; p1=ctrl[i]; p2=ctrl[i+1]; p3=ctrl[min(len(ctrl)-1,i+2)]
    for j in range(100):
        t=j/100.0
        pts.append(catmull_rom(p0,p1,p2,p3,t))
pts.append(ctrl[-1])
pts=np.array(pts)
seg=np.linalg.norm(np.diff(pts,axis=0),axis=1)
cum=np.concatenate([[0],np.cumsum(seg)])
total=cum[-1]
duration=70.0
fps=30
nframes=int(duration*fps)
times=np.linspace(0,duration,nframes)
def smoothstep(x): x=np.clip(x,0,1); return x*x*(3-2*x)
s_eased=total*smoothstep(times/duration)
pos_interp=np.zeros((nframes,3))
target_interp=np.zeros((nframes,3))
target_offset=2000.0
for k in range(3):
    pos_interp[:,k]=np.interp(s_eased,cum,pts[:,k])
    target_interp[:,k]=np.interp(np.clip(s_eased+target_offset,0,total),cum,pts[:,k])
out=[]
for i in range(nframes):
    out.append({'t':round(float(times[i]),3),'position':[round(float(pos_interp[i,0]),2),round(float(pos_interp[i,1]),2),round(float(pos_interp[i,2]),2)],'target':[round(float(target_interp[i,0]),2),round(float(target_interp[i,1]),2),round(float(target_interp[i,2]),2)]})
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path=os.path.join(ROOT,'web','terrain','camera_path.json')
with open(path,'w') as f: json.dump(out,f)
print('saved',path,'frames',len(out),'duration',duration)