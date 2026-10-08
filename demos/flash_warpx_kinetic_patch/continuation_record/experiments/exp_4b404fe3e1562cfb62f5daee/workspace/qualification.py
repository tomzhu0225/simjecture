"""Frozen continuation audit; inherited observations keep their original status."""
import sys,json,hashlib,runpy
from pathlib import Path
import numpy as np

provenance=json.load(open('parent_provenance.json'))
historical={'fine':'exp_55205438f03261250c2f8238','bigfine':'exp_ba37bf1a0947ae8cb2591db0','timestep':'exp_ec59942cf4fe18f457b92418','particles':'exp_3a4cd829f718a2211536f64c','base':'exp_1c6e664e972b5f583f31d498'}
cases=[]
for i,v in enumerate(sys.argv):
    if v=='--case':cases.append(sys.argv[i+1:i+4])
hash_checks=[]
for label,directory,patch in cases:
    if label in historical:
        receipt=next(r for r in provenance['records'] if r['id']==historical[label])
        for relative in ['result.json','history.json','moments.npz','initial_fields.npz','final_fields.npz','reduced/field_energy.txt','reduced/particle_energy.txt']:
            path=Path(directory)/relative
            actual=hashlib.sha256(path.read_bytes()).hexdigest()
            expected=receipt['artifacts']['kinetic/'+relative]['sha256']
            if actual!=expected:raise ValueError('Inherited artifact hash mismatch: '+str(path))
            hash_checks.append(dict(path=str(path),sha256=actual,original_experiment=receipt['id'],status='historical exploration'))
    meta=json.load(open(Path(patch).with_suffix('.json')))
    if hashlib.sha256(Path(patch).read_bytes()).hexdigest()!=meta['patch_sha256']:raise ValueError('Patch hash mismatch')
runpy.run_path('kinetic_analysis.py',run_name='__main__')
result=json.load(open('analysis.json'))
def average(t,y):
    tt=np.r_[.3,t[(t>.3)&(t<.8)],.8]
    return float(np.trapezoid(np.interp(tt,t,y),tt)/.5)
for label,directory,patch in cases:
    raw=np.load(Path(directory)/'moments.npz');h=json.load(open(Path(directory)/'history.json'))
    ts=np.array([r['time_omegaci'] for r in h])
    for sp in ['ions','electrons']:
        row=result['cases'][label]['species'][sp]
        ii=np.unique(np.r_[np.arange(0,len(ts),2),len(ts)-1])
        row['cadence_mean_change']=abs(average(ts[ii],np.array(row['area_means'])[ii])-row['area_time_mean'])
        sub=[]
        for r in h:
            key=f"substep{r['step']}_{sp}_pressure"
            if key not in raw:break
            P=raw[key];p=np.trace(P,axis1=1,axis2=2)/3
            sub.append(float(np.mean(np.linalg.norm(P-p[:,None,None]*np.eye(3),axis=(1,2))/(np.sqrt(3)*p))))
        row['secondary_area_time_mean']=average(ts,np.array(sub)) if len(sub)==len(ts) else None
        row['bin_mean_change']=abs(row['secondary_area_time_mean']-row['area_time_mean']) if row['secondary_area_time_mean'] is not None else None
    result['cases'][label]['status']='historical exploration' if label in historical else 'fresh exploration or evidence as recorded by host'
    result['cases'][label]['originating_experiment']=historical.get(label)
result['hash_verification']=hash_checks
result['control_gates']={}
for label,comparison in result['comparisons'].items():
    if label=='bigfine':
        result['control_gates']['matched_fine_patch']=all(abs(v['A_mean_difference'])<=.02 and v['maximum_pressure_mean_relative_difference']<=.05 and v['maximum_density_mean_relative_difference']<=.05 for v in comparison.values()) and all(result['cases'][label]['species'][sp]['origin'].get('origin_boundary_collar_fraction',1)<=.01 for sp in ['ions','electrons'])
    if label=='timestep':result['control_gates']['timestep']=all(abs(v['A_mean_difference'])<=.01 and v['maximum_pressure_mean_relative_difference']<=.03 for v in comparison.values())
result['limitations']=['Historical data remain exploration; postprocessing never promotes stage. Conditional control envelope is not a distribution-free confidence interval. Secondary bins bound inter-bin broadening only. Debye underresolution and nearest-cell boundary flux remain explicit.']
Path('analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
