"""Complete qualification package for the unchanged finite pressure contract."""
import runpy,sys,json
from pathlib import Path
import numpy as np
argv=sys.argv.copy()
runpy.run_path('qualification.py',run_name='__main__')
r=json.load(open('analysis.json'))
def timeseries(label,sp):
    d=Path('data')/label;raw=np.load(d/'moments.npz');h=json.load(open(d/'history.json'))
    ts=np.array([x['time_omegaci'] for x in h]);P=np.array([raw[f"step{x['step']}_{sp}_pressure"] for x in h]);n=np.array([raw[f"step{x['step']}_{sp}_number_density"].mean() for x in h]);p=np.trace(P,axis1=2,axis2=3).mean(1)/3
    return ts,p,n
def comparison(ref,other):
    out={}
    for sp in ['ions','electrons']:
        t,p,n=timeseries(ref,sp);u,q,m=timeseries(other,sp);tt=np.r_[.3,t[(t>.3)&(t<.8)],.8]
        out[sp]={'A_mean_difference':r['cases'][other]['species'][sp]['area_time_mean']-r['cases'][ref]['species'][sp]['area_time_mean'],'maximum_pressure_mean_relative_difference':float(np.max(abs(np.interp(tt,u,q)/np.interp(tt,t,p)-1))),'maximum_density_mean_relative_difference':float(np.max(abs(np.interp(tt,u,m)/np.interp(tt,t,n)-1)))}
    return out
if 'fine32' in r['cases']:
    c=comparison('particles','fine32');r['matched32_spatial_comparison']=c
    r['control_gates']['matched32_spatial']=all(abs(x['A_mean_difference'])<=.02 and x['maximum_pressure_mean_relative_difference']<=.05 and x['maximum_density_mean_relative_difference']<=.03 for x in c.values())
    c=comparison('fine','fine32');r['fixedfine_particle_comparison']=c
    r['control_gates']['fixedfine_particle']=all(abs(x['A_mean_difference'])<=.03 for x in c.values())
if 'evidence' in r['cases']:
    c=comparison('fine','evidence');r['fresh_seed_comparison']=c
    r['control_gates']['fresh_seed']=all(abs(x['A_mean_difference'])<=.03 for x in c.values())
    r['decision_envelope']={}
    for sp in ['ions','electrons']:
        changes={'spatial':abs(r['matched32_spatial_comparison'][sp]['A_mean_difference']),'ppc':abs(r['fixedfine_particle_comparison'][sp]['A_mean_difference']),'timestep':abs(r['comparisons']['timestep'][sp]['A_mean_difference']),'patch':abs(r['comparisons']['bigfine'][sp]['A_mean_difference']),'seed':abs(c[sp]['A_mean_difference'])}
        # Keep worst measured bin/cadence corrections; no retrospective tolerance fitting.
        changes['bins']=max(v['species'][sp]['bin_mean_change'] or 0 for v in r['cases'].values())
        changes['cadence']=max(v['species'][sp]['cadence_mean_change'] for v in r['cases'].values())
        gamma=max(v['species'][sp]['max_pressure_relativistic_trace_correction'] for v in r['cases'].values())
        allowance=.05+sum(changes.values())+np.sqrt(3)*gamma
        mean=r['cases']['evidence']['species'][sp]['area_time_mean']
        r['decision_envelope'][sp]={'mean':mean,'sampling_allowance':.05,'absolute_control_changes':changes,'relativistic_allowance':float(np.sqrt(3)*gamma),'total_allowance':float(allowance),'lower':float(max(0,mean-allowance)),'upper':float(mean+allowance)}
    required=['fine','fine32','bigfine','timestep','particles','evidence']
    gates=all(all(v is True for v in r['cases'][label]['operational_gates'].values()) and all(r['cases'][label]['species'][sp]['eligible'] for sp in ['ions','electrons']) for label in required) and all(r['control_gates'].values())
    r['qualified_for_decision']=bool(gates)
    r['conditional_support_rule_passed']=bool(gates and all(x['upper']<=.2 for x in r['decision_envelope'].values()))
    r['scientific_status']='Unreviewed; numerical flags do not accept a scientific claim.'
sys.argv=['source_qualification.py','--coarse','macro256.npz','--fine','macro512.npz','--selection','refined_selection.json','--hdf5','source512.h5','--summary','macro512_summary.json']
runpy.run_path('source_qualification.py',run_name='__main__')
r['source_qualification']=json.load(open('source_qualification.json'))
runpy.run_path('macro_figure.py',run_name='__main__')
Path('analysis.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
sys.argv=argv
