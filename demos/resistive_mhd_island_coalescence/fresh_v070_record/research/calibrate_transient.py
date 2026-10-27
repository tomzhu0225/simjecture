"""Exploratory extraction of conditional strain/diffusion model; no fitted rate coefficients."""
from pathlib import Path
import json,numpy as np,h5py
from scipy.special import erf
from scipy.integrate import solve_ivp
rows=[]
for S in [1000,2000]:
 r=json.loads(Path(f'spatial_S{S}_n384.json').read_text());flux=np.array([v['reconnected_flux_from_by'] for v in r['timeseries']]);n=384;x=(np.arange(n)+.5)/n-.5;diag={}
 idx={0}
 for z in [.01,.03,.05]:
  i=int(np.flatnonzero(flux>=z)[0]);idx.update([i-1,i])
 for i in idx:
  p=Path(f'raw_S{S}_n384_i{i}.h5')
  with h5py.File(p) as h: bx=np.array(h['magx'][0,0],float);vy=np.array(h['vely'][0,0],float);rho=np.array(h['dens'][0,0],float);by=np.array(h['magy'][0,0],float)
  bp=bx[:,191:193].mean(1);vp=vy[:,191:193].mean(1);rp=rho[:,191:193].mean(1);pos=(x>0)&(x<.1); inds=np.flatnonzero(pos);pi=inds[np.argmax(abs(bp[pos]))];B=abs(bp[pi]);hi=next(i for i in inds if abs(bp[i])>=B/2);h=float(np.interp(B/2,[abs(bp[hi-1]),abs(bp[hi])],[x[hi-1],x[hi]]));sigma=h/.6744897501960817;mask=abs(x)<=h;a=-float(np.dot(x[mask],vp[mask])/np.dot(x[mask],x[mask]));fit=-a*x[mask];vr=float(np.linalg.norm(vp[mask]-fit)/np.linalg.norm(vp[mask])) if np.linalg.norm(vp[mask]) else 0.;bf=-B*erf(x[mask]/(np.sqrt(2)*sigma));br=float(np.linalg.norm(bp[mask]-bf)/np.linalg.norm(bp[mask]));dbydx=float(np.gradient(by,1/n,axis=1)[191:193,191:193].mean());diag[i]={'time':r['timeseries'][i]['time'],'B':B,'h':h,'sigma':sigma,'a':a,'rho_up':float(rp[pi]),'velocity_fit_relative_residual':vr,'erf_relative_residual':br,'fit_cells':int(mask.sum()),'central_dBy_dx':dbydx}
 for z in [0,.01,.03,.05]:
  if z==0:d=diag[0]
  else:
   i=int(np.flatnonzero(flux>=z)[0]);j=i-1;w=(z-flux[j])/(flux[i]-flux[j]);d={k:(1-w)*diag[j][k]+w*diag[i][k] for k in diag[j]}
  rows.append({'S_eta':S,'flux':z,**d})
knots=np.array([0,.01,.03,.05]);common=[]
for z in knots:
 rs=[v for v in rows if v['flux']==z];common.append({k:float(np.mean([v[k] for v in rs])) for k in rs[0] if k not in ['S_eta','flux']})
a0=np.array([v['a'] for v in common]);B0=np.array([v['B'] for v in common]);w0=float(np.mean([v['sigma']**2 for v in rows if v['flux']==0]));pred=[]
for S in [1000,2000,750,1500]:
 eta=1/S
 def fun(t,v):
  w,psi=v;a=float(np.interp(psi,knots,a0));B=float(np.interp(psi,knots,B0));return [-2*a*w+2*eta,eta*np.sqrt(2/np.pi)*B/np.sqrt(max(w,1e-30))]
 def event(t,v):return v[1]-.05
 event.terminal=True
 sol=solve_ivp(fun,[0,10],[w0,0],rtol=1e-8,atol=1e-11,events=event,max_step=.001,dense_output=True)
 from scipy.optimize import brentq
 if len(sol.t_events[0]):
  hi=float(sol.t_events[0][0]);lo=brentq(lambda t:sol.sol(t)[1]-.01,0,hi);pred.append({'S_eta':S,'t_low':lo,'t_high':hi,'duration':hi-lo,'rate':.04/(hi-lo)})
Path('conditional_calibration.json').write_text(json.dumps({'rows':rows,'common_knots':common,'w0':w0,'predictions':pred,'status':'native exploratory calibration only; gates not fully assessed; not a committed prediction'},indent=2)+'\n')
print(json.dumps({'rows':rows,'common':common,'predictions':pred}))
