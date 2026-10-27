"""Exploratory diagnostic of a shared effective-width budget; no validation data."""
import json,numpy as np,h5py
from pathlib import Path
from scipy.signal import savgol_filter
from scipy.special import erf
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
ks=np.array([0,.01,.03,.05]); anchors=[]
for S in [1000,2000]:
 p=Path(f'S{S}_n384_magnetic.h5')
 with h5py.File(p) as h:
  t=h['time'][()];psi=h['flux'][()];B=[];w=[]
  n=h['magx'].shape[1];x=(np.arange(n)+.5)/n-.5;pos=np.flatnonzero((x>0)&(x<.1))
  for i in range(len(t)):
   bp=h['magx'][i,:,n//2-1:n//2+1].mean(1);bu=float(max(abs(bp[pos])));k=next(k for k in pos if abs(bp[k])>=bu/2);hh=float(np.interp(bu/2,[abs(bp[k-1]),abs(bp[k])],[x[k-1],x[k]]));B.append(bu);w.append((hh/.6744897501960817)**2)
 w=np.array(w);B=np.array(B);ws=savgol_filter(w,11,3,mode='interp');der=np.gradient(ws,t);aa=(1/S-.5*der)/w
 arr={'S_eta':S,'time':t.tolist(),'flux':psi.tolist(),'B':B.tolist(),'w':w.tolist(),'a_eff':aa.tolist(),'knots':{'B':np.interp(ks,psi,B).tolist(),'a_eff':np.interp(ks,psi,aa).tolist()},'w0':float(w[0])};anchors.append(arr)
Bmean=np.mean([v['knots']['B'] for v in anchors],axis=0);amean=np.mean([v['knots']['a_eff'] for v in anchors],axis=0);w0=float(np.mean([v['w0'] for v in anchors]));pred=[]
for S in [1000,2000,1500]:
 def fun(t,v):
  w,p=v;return [-2*np.interp(p,ks,amean)*w+2/S,1/S*np.sqrt(2/np.pi)*np.interp(p,ks,Bmean)/np.sqrt(max(w,1e-30))]
 def ev(t,v):return v[1]-.05
 ev.terminal=True
 sol=solve_ivp(fun,[0,5],[w0,0],events=ev,rtol=1e-9,atol=1e-12,max_step=.001,dense_output=True)
 hi=float(sol.t_events[0][0]);lo=brentq(lambda t:sol.sol(t)[1]-.01,0,hi);widths=[]
 for q in ks:
  tt=0 if q==0 else (hi if q==.05 else brentq(lambda t:sol.sol(t)[1]-q,0,hi));widths.append(float(np.sqrt(sol.sol(tt)[0])*.6744897501960817))
 pred.append({'S_eta':S,'t_low':lo,'t_high':hi,'duration':hi-lo,'rate':.04/(hi-lo),'h_at_knots':widths})
Path('effective_width_calibration.json').write_text(json.dumps({'knots':ks.tolist(),'common_B':Bmean.tolist(),'common_a_eff':amean.tolist(),'w0':w0,'anchors':anchors,'predictions':pred,'status':'exploratory calibration of separate phenomenological effective-width closure; no physical-causation claim; not validation'},indent=2)+'\n')
print(json.dumps({'knots':ks.tolist(),'B':Bmean.tolist(),'a_eff':amean.tolist(),'anchor_aeff':[v['knots']['a_eff'] for v in anchors],'predictions':pred}))
