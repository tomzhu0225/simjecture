import hashlib,json
from pathlib import Path
import numpy as np
import h5py
from null_diagnostic import nulls
r=json.loads(Path('upper_bracket_identity.json').read_text());actual=hashlib.sha256(Path('upper_bracket.h5').read_bytes()).hexdigest()
assert actual==r['field']['sha256']
with h5py.File('upper_bracket.h5') as h: bx=np.array(h['magx'][0,0],float);by=np.array(h['magy'][0,0],float)
r['nulls']=nulls(bx,by);r['verified_sha256']=actual;r['full_saved_cell_center_domain']=True
x=(np.arange(128)+.5)/128-.5;X,Y=np.meshgrid(x,x)
r['synthetic_controls']=[]
for k,expected in [(1,3),(3,15)]:
 bx=-4*np.pi*np.sin(4*np.pi*Y);by=2*k*np.pi*np.sin(2*k*np.pi*X); ns=nulls(bx,by)
 r['synthetic_controls'].append({'harmonic':k,'expected_null_count':expected,'actual_null_count':len(ns),'nulls':ns})
 assert len(ns)==expected
Path('bracket_result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
