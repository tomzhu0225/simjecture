"""Versioned source-readiness audit; energyFix is explicitly unaccounted separately."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np,h5py
from scipy.interpolate import RectBivariateSpline
p=argparse.ArgumentParser();p.add_argument('--coarse',required=True);p.add_argument('--fine',required=True);p.add_argument('--selection',required=True);p.add_argument('--hdf5',required=True);p.add_argument('--summary',required=True);a=p.parse_args()
f=np.load(a.fine);g=np.load(a.coarse);sel=json.load(open(a.selection));summ=json.load(open(a.summary));x=f['x'];z=f['z'];mask=np.ix_(abs(z)<.08,abs(x)<.08)
comparisons={}
for key in ['rho','pressure','bx','bz','ux','uz']:
 v=f[key][mask];u=RectBivariateSpline(g['z'],g['x'],g[key])(z[abs(z)<.08],x[abs(x)<.08]);comparisons[key]=dict(rms_absolute_code=float(np.sqrt(np.mean((v-u)**2))),rms_relative=float(np.sqrt(np.mean((v-u)**2)/max(np.mean(v*v),1e-300))))
with h5py.File(a.hdf5) as h:
 div=h['divb'][0,0];dx=float(x[1]-x[0]);bscale=float(np.hypot(f['bx'],f['bz']).max());scaled=float(abs(div).max()*dx/bscale)
res=dict(version=1,source_sha256=hashlib.sha256(Path(a.hdf5).read_bytes()).hexdigest(),fine_state_sha256=hashlib.sha256(Path(a.fine).read_bytes()).hexdigest(),source_time=sel['source_time_code'],central_comparison_region_code=[[-.08,.08],[-.08,.08]],comparisons=comparisons,scaled_divb_definition='max(abs(divB))*source_cell_size/max(abs(B))',scaled_divb=scaled,width=sel['sheet_half_width_code'],width_cells=sel['sheet_half_width_source_cells'],floor_occupation_density=int(np.count_nonzero(f['rho']<=1e-11)),floor_occupation_pressure=int(np.count_nonzero(f['pressure']<=1e-11)),energy_drift=summ['energy_relative_drift'],mass_drift=summ['mass_relative_drift'],energy_fix_accounting='energyFix is enabled; separate correction totals are not supplied in these diagnostics. Reconstructed energy drift is a consistency residual, not an independently closed physical conservation budget.',limitations=['Output density/pressure far above floor; unseen corrections between outputs are not bounded independently. This is source readiness only.'])
Path('source_qualification.json').write_text(json.dumps(res,indent=2)+'\n')
