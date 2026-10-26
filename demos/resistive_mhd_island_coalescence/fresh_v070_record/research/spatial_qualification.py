"""Recorded qualification on fresh raw brackets and lossless magnetic time series."""
import json,hashlib
from pathlib import Path
import numpy as np
import h5py
from null_diagnostic import nulls
manifest=json.loads(Path('spatial_inputs.json').read_text()); results=[]
for c in manifest:
 r=json.loads(Path(c['summary']).read_text());n=r['config']['n'];x=(np.arange(n)+.5)/n-.5; ts=r['timeseries'];flux=np.array([v['reconnected_flux_from_by'] for v in ts]);times=np.array([v['time'] for v in ts]);end=int(np.flatnonzero(flux>=.05)[0]);selected={};verified=[]
 series=h5py.File(c['series'],'r') if c.get('series') else None
 for raw in c['raw_samples']:
  p=Path(raw['input']);digest=hashlib.sha256(p.read_bytes()).hexdigest();source=r['fields'][raw['index']]
  assert digest==source['sha256']
  with h5py.File(p) as h:
   bx=np.array(h['magx'][0,0],float);by=np.array(h['magy'][0,0],float)
  if series is not None:
   assert np.array_equal(bx,series['magx'][raw['index']]) and np.array_equal(by,series['magy'][raw['index']])
  selected[raw['index']]=(bx,by);verified.append({'index':raw['index'],'sha256':digest,'bitwise_series_match':series is not None})
 inv=[]
 if series is not None:
  assert np.array_equal(times,series['time'][()]);assert np.array_equal(flux,series['flux'][()])
  for i in range(end+1):
   bx=np.array(series['magx'][i],float);by=np.array(series['magy'][i],float)
   inv.append({'index':i,'time':float(times[i]),'flux':float(flux[i]),'nulls':nulls(bx,by),'original_field_sha256':r['fields'][i]['sha256']})
 matched=[]
 for z in [.01,.03,.05]:
  i=int(np.flatnonzero(flux>=z)[0]);j=i-1;w=float((z-flux[j])/(flux[i]-flux[j]));pp=[]
  for k in [j,i]:
   if k in selected:bx,by=selected[k]
   else:bx=np.array(series['magx'][k],float);by=np.array(series['magy'][k],float)
   J=np.gradient(by,1/n,axis=1)-np.gradient(bx,1/n,axis=0);jc=float(J[n//2-1:n//2+1,n//2-1:n//2+1].mean());bp=bx[:,n//2-1:n//2+1].mean(1);jp=J[:,n//2-1:n//2+1].mean(1);width=float(np.max(abs(bx[np.abs(x)<.1,n//2-1:n//2+1]))/abs(jc));pp.append({'Bx':bp,'Jz':jp,'J0':jc,'width':width})
  prof={k:((1-w)*pp[0][k]+w*pp[1][k]).tolist() if hasattr(pp[0][k],'tolist') else (1-w)*pp[0][k]+w*pp[1][k] for k in pp[0]};prof.update({'flux':z,'y':x.tolist(),'bracket_indices':[j,i],'weight':w,'width_cells':prof['width']*n});matched.append(prof)
 if series is not None:series.close()
 results.append({'experiment':c['experiment'],'config':r['config'],'summary':r,'matched':matched,'verified_raw_samples':verified,'topology':{'frames':len(inv),'last_index':end,'last_time':float(times[end]),'last_flux':float(flux[end]),'counts':sorted(set((sum(q[2]=='X' for q in v['nulls']),sum(q[2]=='O' for q in v['nulls'])) for v in inv)),'inventory':inv}})
profiles=[];unc=[]
for S in [1000,2000]:
 rr=sorted([v for v in results if v['config']['S_eta']==S],key=lambda v:v['config']['n']); rr=rr[-3:]; rates=np.array([v['summary']['metrics']['normalized_flux_slope'] for v in rr]);f=rr[-1];r=f['summary'];R=float(rates[-1]);changes=np.abs(np.diff(rates)/rates[1:]); cf=json.loads(Path(f'cfl_{S}.json').read_text());base=json.loads(Path(f'base256_{S}.json').read_text());ct=abs(cf['metrics']['normalized_flux_slope']/base['metrics']['normalized_flux_slope']-1)
 terms={'mesh':2*float(changes.max()),'cadence':float(max(abs(np.array(r['cadence_rate_interval'])/R-1))),'path':abs(r['rate_other_path']/R-1),'CFL':ct};u=max(.01,sum(terms.values()));unc.append({'S_eta':S,'meshes':[v['config']['n'] for v in rr],'rates':rates.tolist(),'relative_changes':changes.tolist(),'terms':terms,'u':u,'rate_interval':[R*(1-u),R*(1+u)],'mesh_gate':bool(changes[-1]<changes[-2] and changes[-1]<=.05),'CFL_control_mesh':256})
 for zi,z in enumerate([.01,.03,.05]):
  row={'S_eta':S,'flux':z,'meshes':[v['config']['n'] for v in rr],'J0':[v['matched'][zi]['J0'] for v in rr],'width_physical':[v['matched'][zi]['width'] for v in rr],'width_cells':[v['matched'][zi]['width_cells'] for v in rr]};row['J0_relative_changes']=(np.abs(np.diff(row['J0']))/np.abs(row['J0'][1:])).tolist();row['width_relative_changes']=(np.abs(np.diff(row['width_physical']))/np.abs(row['width_physical'][1:])).tolist();norms=[]
  for a,b in zip(rr,rr[1:]):
   ya=np.array(a['matched'][zi]['y']);yb=np.array(b['matched'][zi]['y']);jb=np.array(b['matched'][zi]['Jz']);ja=np.interp(yb,ya,a['matched'][zi]['Jz']);mask=abs(yb)<.1;norms.append(float(np.linalg.norm((ja-jb)[mask])/np.linalg.norm(jb[mask])))
  row['J_profile_L2_relative_changes']=norms;profiles.append(row)
a,b=unc;ra=a['rates'][-1];rb=b['rates'][-1];slope={'contrast':[1000,2000],'central':float(np.log(rb/ra)/np.log(2)),'interval':[float(np.log(b['rate_interval'][0]/a['rate_interval'][1])/np.log(2)),float(np.log(b['rate_interval'][1]/a['rate_interval'][0])/np.log(2))],'status':'exploratory qualification only; never claim evidence'}
for v in results:v.pop('summary')
Path('spatial_qualification.json').write_text(json.dumps({'cases':results,'profile_comparisons':profiles,'uncertainty':unc,'slope':slope,'limitations':['Native lossless conversion checked every source file hash; this recorded independent reduction rechecks original raw crossing-bracket hashes and bitwise magnetic-series equality at those samples.','CFL contribution is the measured same-mesh256 control; its transfer to384 requires independent assessment.','Full-domain null inventory covers saved cell-center fields, not subcell/between-output or ghost-layer structures.']},indent=2,allow_nan=False)+'\n')
print(json.dumps({'uncertainty':unc,'slope':slope,'profiles':profiles}))
