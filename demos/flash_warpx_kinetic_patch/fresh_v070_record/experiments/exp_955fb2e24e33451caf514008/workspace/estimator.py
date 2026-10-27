"""Version 1: equal-area mean of local pressure departures, then trapezoidal physical-time mean."""
import numpy as np

def estimate(raw,history,species,window=(.3,.8),minimum_count=256,minimum_effective=512):
 ts=np.array([r['time_omegaci'] for r in history],float)
 if len(ts)<2 or not np.all(np.diff(ts)>0):raise ValueError('Invalid time axis')
 lower,upper=window
 samples=(ts>=lower)&(ts<=upper)
 samples[max(0,np.searchsorted(ts,lower)-1)]=True
 samples[min(len(ts)-1,np.searchsorted(ts,upper))]=True
 values=[];count_min=float('inf');neff_min=float('inf');correction_max=0.;eligible=True
 for r,used in zip(history,samples):
  pre=f"step{r['step']}_{species}_";p=raw[pre+'pressure'];trace=np.trace(p,axis1=1,axis2=2);q=trace/3
  count=raw[pre+'count'];eff=raw[pre+'effective_count']
  good=np.isfinite(p).all(axis=(1,2))&(trace>0)&(count>=minimum_count)&(eff>=minimum_effective)
  if used:
   eligible=eligible and bool(np.all(good));count_min=min(count_min,float(count.min()));neff_min=min(neff_min,float(eff.min()));correction_max=max(correction_max,float(raw[pre+'relativistic_pressure_correction'].max()))
  metric=np.linalg.norm(p-q[:,None,None]*np.eye(3),axis=(1,2))/(np.sqrt(3)*np.maximum(q,1e-300))
  values.append(metric.mean())
 eligible=bool(eligible and ts[0]<=lower and ts[-1]>=upper)
 t=np.r_[lower,ts[(ts>lower)&(ts<upper)],upper];v=np.interp(t,ts,values)
 return dict(area_time_mean=float(np.trapezoid(v,t)/(upper-lower)) if eligible else None,eligible=eligible,reason=None if eligible else 'Incomplete window, nonfinite/zero tensor, or at least one bin below frozen count/effective-count policy; bins are never dropped.',minimum_count=count_min,minimum_effective_count=neff_min,max_pressure_relativistic_trace_correction=correction_max,window=list(window),coverage_fraction=1.0 if eligible else None,times=ts.tolist(),area_means=list(map(float,values)))
