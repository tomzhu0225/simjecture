"""Lab submission utility; only calculation.py is executed in the sandbox."""
import argparse,json
from lab import lab
p=argparse.ArgumentParser();p.add_argument('--patch',required=True);p.add_argument('--key',required=True);p.add_argument('--parent');p.add_argument('--ppc',default='32');p.add_argument('--cfl',default='.7');p.add_argument('--seed',default='4101');p.add_argument('--max-grid',default='0');p.add_argument('--timeout',type=int,default=1200);p.add_argument('--method');a=p.parse_args()
m=json.load(open(a.patch+'.json'));nx=m['shape_zx'][1]
args=['kinetic','--patch',a.patch+'.npz','--output','pic','--ppc',a.ppc,'--seed',a.seed,'--duration-omegaci','.9','--boundary-accounting','--secondary-bins','8','--field-diagnostics','2','--diagnostics','36','--cfl',a.cfl,'--max-grid-size',str(nx) if a.max_grid=='0' else a.max_grid,'--moment-bins','4','--roi-x','.04','--roi-z','.015']
kw=dict(stage='evidence',method=a.method) if a.method else dict(stage='exploration')
extras=['macro_study.py','flash_islands.py','transfer_study.py','extract_flash.py','prepare_patch.py','macro_comparison.json','analysis_study.py'] if a.method else []
r=lab.run('calculation.py',args=args,inputs=['kinetic_study.py','estimator.py',a.patch+'.npz',a.patch+'.json','PROTOCOL.json']+extras,outputs=['pic/result.json','pic/moments.npz','pic/history.json','pic/initial_fields.npz','pic/final_fields.npz','pic/reduced/field_energy.txt','pic/reduced/particle_energy.txt','pic/warpx_used_inputs'],capability='warpx-cuda-openpmd-26.07',timeout=a.timeout,key=a.key,purpose='validation' if not a.method else 'comparison',parent_experiment=a.parent,**kw)
print(json.dumps(r))
