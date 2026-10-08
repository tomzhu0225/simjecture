import json,sys,itertools
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
from scipy.stats import t as student

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

def draw_scaling(data):
 lines=['<svg xmlns="http://www.w3.org/2000/svg" width="700" height="500"><rect width="700" height="500" fill="white"/><text x="70" y="30">Recorded rates and numerical sensitivity (log axes)</text>']
 for r in data:
  if r['rate'] is None:continue
  x=70+560*np.log(r['S']/250)/np.log(16);y=440-370*np.log(r['rate']/.02)/np.log(6);color='blue' if r['n']==256 else 'red';e=r['log_margin'];dy=0 if e is None else 370*e/np.log(6)
  lines.append(f'<line x1="{x}" x2="{x}" y1="{y-dy}" y2="{y+dy}" stroke="{color}"/><circle cx="{x}" cy="{y}" r="4" fill="{color}"/><text x="{x+5}" y="{y-5}" font-size="11">S={r["S"]:g}, N={r["n"]}</text>')
 lines.append('<text x="100" y="480">S_eta=1/eta nominal; blue N256, red N384; empirical error bars</text><text x="15" y="70">R</text></svg>');Path('scaling.svg').write_text(''.join(lines))

def draw_fields(bx,by,j,row,time):
 lines=['<svg xmlns="http://www.w3.org/2000/svg" width="850" height="460"><rect width="850" height="460" fill="white"/>',f'<text x="20" y="25">{row["stage"]}: S={row["S"]:g}, N={row["n"]}, t={time:.4f}; |B| left, Jz right</text>']
 for index,array in enumerate([np.hypot(bx,by),j]):
  step=max(1,array.shape[0]//48);z=array[::step,::step];maximum=max(float(abs(z).max()),1e-12);size=380/z.shape[0]
  for iy in range(z.shape[0]):
   for ix in range(z.shape[1]):
    v=float(z[iy,ix])/maximum;c=int(255*(1-abs(v)));color=f'rgb(255,{c},{c})' if v>=0 else f'rgb({c},{c},255)';lines.append(f'<rect x="{20+index*420+ix*size:.2f}" y="{50+(z.shape[0]-1-iy)*size:.2f}" width="{size+.1:.2f}" height="{size+.1:.2f}" fill="{color}"/>')
 lines.append('<text x="20" y="450">Square x,y in [-0.5,0.5]; sampled display only, full fields retained in NPZ</text></svg>');Path('field_current.svg').write_text(''.join(lines))

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
 draw_scaling(data)
 rawrow=next((r for r in reversed(data) if r['raw']),None)
 if rawrow:
  z=np.load(rawrow['raw']);time=z['time'];d=rawrow['data'];target=(d['metrics']['flux_low_crossing_time']+d['metrics']['flux_high_crossing_time'])/2 if rawrow['rate'] else time[-1];i=int(np.argmin(abs(time-target)));bx=z['magx'][i].astype(float);by=z['magy'][i].astype(float);n=bx.shape[0];dx=1/n;coord=-.5+(np.arange(n)+.5)*dx;j=np.gradient(by,dx,axis=1)-np.gradient(bx,dx,axis=0);psi=np.cumsum(by[0])*dx-np.cumsum(bx,axis=0)*dx
  draw_fields(bx,by,j,rawrow,time[i])
  np.savez_compressed('plot_fields.npz',time=time[i],x=coord,y=coord,bx=bx,by=by,jz=j,psi=psi)
 output={'protocol':json.loads(Path('protocol.json').read_text()),'cases':[{k:v for k,v in r.items() if k not in ['data','raw']} for r in data],'matched_log_rate_differences':{str(k):v for k,v in gaps.items()},'fits':fits,'matched_fits':matched,'common_S':sorted(common),'adjacent_slopes':{str(n):adjacent([r for r in data if r['n']==n and r['eligible']]) for n in grids},'declared_refinement_coverage_complete':all(S in gaps for S in planned),'limitations':['Numerical sensitivity margins are empirical, not certified continuum error bars.','Finite samples cannot prove continuous-domain universality.','Topology veto cannot exclude off-axis, subthreshold or between-output islands.'],'figures':{'scaling.svg':'Stage labels and case IDs in cases','field_current.svg':None if not rawrow else {'experiment':rawrow['experiment'],'stage':rawrow['stage']}}}
 Path('analysis.json').write_text(json.dumps(output,indent=2,allow_nan=False));print(json.dumps({'fits':fits,'matched_fits':matched}))
if __name__=='__main__':main(sys.argv[1])
