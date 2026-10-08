import json, hashlib
from pathlib import Path
import numpy as np
import study_analysis as a
x=json.loads(Path('cfl08.json').read_text());y=json.loads(Path('cfl04.json').read_text())
r8=a.rate(x);r4=a.rate(y)
control={'experiments':['exp_27bae5c10115cc47b7ee511a','exp_f4615601bac4bd9ea59211c3'],'rates':{'cfl08':r8,'cfl04':r4},'absolute_log_rate_difference':abs(float(np.log(r8/r4))),'relative_difference':abs(r8/r4-1),'inputs_sha256':{f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in ['cfl08.json','cfl04.json']},'variants':{k:[a.rate(d,path,st) for path in ['by','bx'] for st in [1,2]] for k,d in [('cfl08',x),('cfl04',y)]},'scope':'Fresh S500 full-window parity; borrowing to other S is empirical, not demonstrated whole-domain timestep accuracy.'}
Path('cfl_control.json').write_text(json.dumps(control,indent=2))
Path('qualification.json').write_text(json.dumps({'control':control,'window':[x['window'],y['window']],'conservation':[x['conservation'],y['conservation']],'all_variants_defined':all(v is not None for row in control['variants'].values() for v in row)},indent=2))
print(json.dumps(control))
