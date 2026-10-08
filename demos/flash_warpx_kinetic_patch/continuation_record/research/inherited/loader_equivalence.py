import ast,json,types
from pathlib import Path
import numpy as np
from scipy.constants import c
q=np.load('fine_patch.npz');data={k:(q[k][:160,:160].copy() if q[k].ndim>=2 and k not in ['x','z'] else q[k][:160].copy()) for k in q.files};meta=json.load(open('fine_patch.json'))
outputs=[]
for path in ['kinetic_before_chunks.py','kinetic.py']:
 capture={}
 class PC:
  def __init__(self,name):self.name=name;capture.setdefault(name,[])
  def add_real_comp(self,*a,**k):pass
  def add_particles(self,**kw):capture[self.name].append({k:np.asarray(v).copy() for k,v in kw.items() if k!='unique_particles'})
 node=next(n for n in ast.parse(Path(path).read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='load_particles')
 env=dict(np=np,picmi=types.SimpleNamespace(constants=types.SimpleNamespace(c=c)),particle_containers=types.SimpleNamespace(ParticleContainerWrapper=PC));exec(compile(ast.Module(body=[node],type_ignores=[]),path,'exec'),env)
 result=env['load_particles'](data,meta,16,20261008)
 outputs.append((result,{sp:{k:np.concatenate([x[k] for x in values]) for k in values[0]} for sp,values in capture.items()}))
report={}
for sp in ['ions','electrons']:
 a,b=outputs[0][1][sp],outputs[1][1][sp];report[sp]={k:dict(exact=bool(np.array_equal(a[k],b[k])),rms_relative=float(np.linalg.norm(a[k]-b[k])/max(np.linalg.norm(a[k]),1e-300)),maximum_absolute=float(np.max(abs(a[k]-b[k])))) for k in a};report[sp]['count']=int(a['w'].size)
Path('equivalence.json').write_text(json.dumps(dict(scope='Agent-owned loader initialization equivalence over 25600 cells and 409600 particles/species, crosses 16384-cell chunk boundary; fake sink checks arithmetic, actual evolution qualified separately by exp_ba37bf1a0947ae8cb2591db0.',comparison=report,statistics=[x[0] for x in outputs]),indent=2)+'\n')
