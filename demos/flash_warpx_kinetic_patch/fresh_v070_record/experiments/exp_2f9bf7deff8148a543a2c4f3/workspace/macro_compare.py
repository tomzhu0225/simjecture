"""Source convergence at the prospectively selected recorded macro times."""
import h5py,numpy as np,json
from scipy.interpolate import RectBivariateSpline
from pathlib import Path
result={}
def read(path):
 with h5py.File(path) as f:
  d={k:f[k][0,0].astype(float) for k in ['dens','pres','magx','magy','velx','vely']};n=d['dens'].shape[0];x=-.5+(np.arange(n)+.5)/n
  t=next(float(r['value']) for r in f['real scalars'] if r['name'].decode().strip()=='time')
 return x,d,t
x,d,t=read('source256.h5');y,g,u=read('source512.h5');xx=np.linspace(-.04,.04,81);zz=np.linspace(-.015,.015,61)
for region,coords in [('measurement',(xx,zz)),('patch',(np.linspace(-.3,.3,193),np.linspace(-.3,.3,193)))]:
 X,Z=coords;v={k:RectBivariateSpline(x,x,a)(Z,X) for k,a in d.items()};w={k:RectBivariateSpline(y,y,a)(Z,X) for k,a in g.items()};out={}
 for k in d:out[k]=dict(relative_RMS=float(np.linalg.norm(w[k]-v[k])/max(np.linalg.norm(w[k]),1e-300)),max_absolute=float(abs(w[k]-v[k]).max()))
 for name,comp in [('current_y',None)]:
  j=RectBivariateSpline(x,x,d['magx'])(Z,X,dx=1)-RectBivariateSpline(x,x,d['magy'])(Z,X,dy=1);k=RectBivariateSpline(y,y,g['magx'])(Z,X,dx=1)-RectBivariateSpline(y,y,g['magy'])(Z,X,dy=1);out[name]=dict(relative_RMS=float(np.linalg.norm(j-k)/np.linalg.norm(k)),max_absolute=float(abs(j-k).max()))
 result[region]=out
result['source_times']=[t,u];result['time_difference']=u-t
Path('macro_comparison.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result))
