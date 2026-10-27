"""Independent checks of retained staggered B and matched interior field histories."""
import json,numpy as np
from pathlib import Path
labels=['refined','time','ppc','boundary','mesh'];out={};hist={}
for label in labels:
 patch={'refined':'refined_patch','time':'refined_patch','ppc':'refined_patch','boundary':'refined_large_patch','mesh':'mesh_patch'}[label]
 m=json.load(open(patch+'.json'));dx,dz=m['cell_size_m'];b0=m['scales']['magnetic_T'];out[label]={}
 for phase in ['initial','final']:
  q=np.load(label+'_record/'+phase+'_fields.npz');div=np.diff(q['bx'],axis=1)/dx+np.diff(q['bz'],axis=0)/dz
  out[label][phase+'_scaled_divB']=float(abs(div).max()*min(dx,dz)/b0)
 h=json.load(open(label+'_record/history.json'));t=np.array([r['time_omegaci'] for r in h]);hist[label]=(t,{k:np.array([r['field_activity'][k+'_roi_rms'] for r in h]) for k in ['Bx','By','Bz','Ex','Ey','Ez']})
ref_t,ref=hist['refined'];mask=(ref_t>=.4)&(ref_t<=.9)
for label in labels[1:]:
 t,f=hist[label];m=json.load(open('refined_patch.json'));b0=m['scales']['magnetic_T'];e0=b0*m['scales']['velocity_m_s']
 out[label]['max_ROI_rms_component_change_normalized']={k:float(np.max(abs(np.interp(ref_t[mask],t,f[k])-ref[k][mask]))/(b0 if k[0]=='B' else e0)) for k in ref}
Path('field_audit.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
