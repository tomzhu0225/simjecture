import json,sys,itertools
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.stats import t as student
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import guided_reader as g

def rate(d,path='by',stride=1):
 rows=d['timeseries'][::stride];times=np.array([r['time'] for r in rows]);flux=np.array([r['reconnected_flux_from_'+path] for r in rows]);lo=g._crossing(times,flux,.01);hi=g._crossing(times,flux,.05)
 return None if lo is None or hi is None or hi<=lo else .04/(hi-lo)

def bracket(d):
 times=np.array([r['time'] for r in d['timeseries']]);flux=np.array([r['reconnected_flux_from_by'] for r in d['timeseries']]);bounds=[]
 for target in [.01,.05]:
  ix=np.flatnonzero(flux>=target)
  if not len(ix):return {'rate_bounds':None,'reason':'Window not reached'}
  i=int(ix[0]);bounds.append([float(times[max(0,i-1)]),float(times[i])])
 min_dt=bounds[1][0]-bounds[0][1];max_dt=bounds[1][1]-bounds[0][0]
 return {'crossing_time_bounds':bounds,'rate_bounds':[.04/max_dt,None if min_dt<=0 else .04/min_dt],'reason':None if min_dt>0 else 'Overlapping time brackets; upper rate undefined','decision_role':'Conservative cadence-only bracket diagnostic; not silently substituted for sensitivity envelope or used alone to reject exponent band'}

def adjacent(rows):
 rr=sorted(rows,key=lambda r:r['S']);out=[]
 for a,b in zip(rr,rr[1:]):
  width=np.log(b['S']/a['S']);p=np.log(b['rate']/a['rate'])/width;e=(a['log_margin']+b['log_margin'])/width
  out.append({'S':[a['S'],b['S']],'p':float(p),'numerical_interval':[float(p-e),float(p+e)],'decision_role':'Curvature diagnostic; rejection uses joint band feasibility and common-refinement persistence'})
 return out

def fit(rows):
 if len(rows)<2:return None
 x=np.log([r['S'] for r in rows]);y=np.log([r['rate'] for r in rows]);e=np.array([r['log_margin'] for r in rows]);w=(x-x.mean())/np.sum((x-x.mean())**2);p=float(w@y);inter=float(y.mean()-p*x.mean());res=y-(inter+p*x);half=float(np.sum(abs(w)*e));ci=None
 if len(rows)>2:ci=float(student.ppf(.975,len(rows)-2)*np.sqrt(np.sum(res**2)/(len(rows)-2)/np.sum((x-x.mean())**2)))
 A=np.vstack([np.column_stack([np.ones(len(x)),x]),-np.column_stack([np.ones(len(x)),x])]);b=np.r_[y+e,-y+e];feasible=linprog([0,0],A_ub=A,b_ub=b,bounds=[(None,None),(-.6,-.4)],method='highs').success
 return {'p':p,'intercept':inter,'numerical_slope_interval':[p-half,p+half],'residual_95pct_interval':None if ci is None else [p-ci,p+ci],'residuals_log':res.tolist(),'band_powerlaw_feasible':bool(feasible),'S':[r['S'] for r in rows]}

def main(manifest):
 entries=json.loads(Path(manifest).read_text());data=[]
 for en in entries:
  d=json.loads(Path(en['json']).read_text());r=rate(d);variants=[rate(d,k,st) for k in ['by','bx'] for st in [1,2]];sens=max([abs(np.log(v/r)) for v in variants if v is not None],default=0) if r else None
  data.append({'experiment':en['experiment'],'S':d['metrics']['l_over_eta_nominal'],'n':d['realized']['nx'],'rate':r,'cadence_path_sensitivity':sens,'raw':en.get('raw'),'stage':en['stage'],'data':d})
 # Physical admissibility precedes any convergence estimate.
 for r in data:
  d=r['data'];win=d['window'];cons=d['conservation'];minimum=6 if r['n']>=384 else 4
  missing=[{'path':k,'stride':st,'reason':'Does not reach both crossing thresholds'} for k in ['by','bx'] for st in [1,2] if rate(d,k,st) is None]
  r['unavailable_variants']=missing
  r['crossing_bracket_rate_bounds']=bracket(d)
  r['physical_eligible']=bool(r['rate'] and not missing and all(d['checks'][k] for k in ['representation','physics_controls','boundaries','diagnostics','numerical_regime','flux_window_reached']) and win['min_sheet_fwhm_cells'] is not None and win['min_sheet_fwhm_cells']>=minimum and win['max_secondary_extrema']==0 and cons['mass_relative_drift']<1e-5 and cons['energy_relative_drift']<1e-3 and cons['floor_hits_sampled']==0)
 gaps={}
 for S in sorted(set(r['S'] for r in data)):
  pair=sorted([r for r in data if r['S']==S and r['physical_eligible']],key=lambda r:r['n'])
  if len(set(r['n'] for r in pair))>1:
   gap=abs(np.log(pair[-1]['rate']/pair[0]['rate']))
   if gap<=np.log(1.1):gaps[S]=gap
 worst=max(gaps.values()) if gaps else None
 planned=json.loads(Path('protocol.json').read_text())['refined_S']
 for r in data:
  must_pair=r['S'] in planned or r['n']>=384
  gap=gaps.get(r['S']) if must_pair else worst
  r['convergence_status']='qualified_matched_pair' if r['S'] in gaps else ('borrowed_qualified_pair' if not must_pair and worst is not None else 'unresolved_missing_or_ineligible_refinement')
  r['log_margin']=None if gap is None else max(.01,2*gap+(r['cadence_path_sensitivity'] or 0)+.0018)
  r['eligible']=r['physical_eligible'] and gap is not None
  r['window']=r['data']['window'];r['conservation']=r['data']['conservation']
 grids=sorted(set(r['n'] for r in data));fits={str(n):fit(sorted([r for r in data if r['n']==n and r['eligible']],key=lambda r:r['S'])) for n in grids}
 common=set.intersection(*[set(r['S'] for r in data if r['n']==n and r['eligible']) for n in grids]) if grids else set()
 matched={str(n):fit(sorted([r for r in data if r['n']==n and r['eligible'] and r['S'] in common],key=lambda r:r['S'])) for n in grids}
 fig,ax=plt.subplots(figsize=(7,5))
 for n in grids:
  rr=sorted([r for r in data if r['n']==n and r['rate'] and r['log_margin'] is not None],key=lambda r:r['S']);xs=np.array([r['S'] for r in rr]);ys=np.array([r['rate'] for r in rr]);es=np.array([r['log_margin'] for r in rr]);ax.errorbar(xs,ys,yerr=np.array([ys*(1-np.exp(-es)),ys*(np.exp(es)-1)]),fmt='o-',label=f'{n}²')
 ax.set_xlim(200,5000);ax.set_ylim(.01,.2)
 ax.set(xscale='log',yscale='log',xlabel='Nominal S_eta = 1/eta',ylabel='Normalized flux-window rate R',title='Recorded '+','.join(sorted(set(r['stage'] for r in data)))+' — numerical sensitivity')
 ax.legend();fig.tight_layout();fig.savefig('scaling.png',dpi=160);plt.close(fig)
 rawrow=next((r for r in reversed(data) if r['raw']),None)
 if rawrow:
  z=np.load(rawrow['raw']);time=z['time'];d=rawrow['data'];target=(d['metrics']['flux_low_crossing_time']+d['metrics']['flux_high_crossing_time'])/2 if rawrow['rate'] else time[-1];i=int(np.argmin(abs(time-target)));bx=z['magx'][i].astype(float);by=z['magy'][i].astype(float);n=bx.shape[0];dx=1/n;coord=-.5+(np.arange(n)+.5)*dx;j=np.gradient(by,dx,axis=1)-np.gradient(bx,dx,axis=0);psi=np.cumsum(by[0])*dx-np.cumsum(bx,axis=0)*dx
  fig,axs=plt.subplots(1,2,figsize=(10,4));im=axs[0].pcolormesh(coord,coord,np.hypot(bx,by),shading='auto');axs[0].contour(coord,coord,psi,20,colors='white',linewidths=.4);fig.colorbar(im,ax=axs[0],label='|B|');im=axs[1].pcolormesh(coord,coord,j,shading='auto',cmap='RdBu_r');fig.colorbar(im,ax=axs[1],label='J_z = d_x B_y - d_y B_x')
  for ax in axs:ax.set(xlabel='x',ylabel='y',aspect='equal')
  fig.suptitle(f"{rawrow['stage']}: {rawrow['experiment']}, S={rawrow['S']:g}, N={n}, t={time[i]:.4f}");fig.tight_layout();fig.savefig('field_current.png',dpi=160);plt.close(fig)
  np.savez_compressed('plot_fields.npz',time=time[i],x=coord,y=coord,bx=bx,by=by,jz=j,psi=psi)
 output={'protocol':json.loads(Path('protocol.json').read_text()),'cases':[{k:v for k,v in r.items() if k not in ['data','raw']} for r in data],'matched_log_rate_differences':{str(k):v for k,v in gaps.items()},'fits':fits,'matched_fits':matched,'common_S':sorted(common),'adjacent_slopes':{str(n):adjacent([r for r in data if r['n']==n and r['eligible']]) for n in grids},'declared_refinement_coverage_complete':all(S in gaps for S in planned),'limitations':['Numerical sensitivity margins are empirical, not certified continuum error bars.','Finite samples cannot prove continuous-domain universality.','Topology veto cannot exclude off-axis, subthreshold or between-output islands.'],'figures':{'scaling.png':'Stage labels and case IDs in cases','field_current.png':None if not rawrow else {'experiment':rawrow['experiment'],'stage':rawrow['stage']}}}
 Path('analysis.json').write_text(json.dumps(output,indent=2,allow_nan=False));print(json.dumps({'fits':fits,'matched_fits':matched}))
if __name__=='__main__':main(sys.argv[1])
