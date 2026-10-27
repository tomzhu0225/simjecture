"""Fresh FLASH trajectory using operator execution helper, with conservative diagnostics."""
import flash_islands,sys,json,hashlib
from pathlib import Path
import h5py,numpy as np
flash_islands.main()
args=sys.argv
out=Path(args[args.index('--output')+1]);summary=Path(args[args.index('--summary')+1])
r=json.loads(summary.read_text());rows=[]
for path in sorted(out.glob('flash_run_hdf5_plt_cnt_*')):
 with h5py.File(path) as f:
  d={k:f[k][0,0].astype(float) for k in ['dens','pres','magx','magy','velx','vely']}
  t=flash_islands._named_values(f['real scalars'])['time'];rho=d['dens'];p=d['pres'];b2=d['magx']**2+d['magy']**2;u2=d['velx']**2+d['vely']**2
  rows.append(dict(time=t,mass=float(rho.mean()),energy=float((p/ (2/3)+.5*rho*u2+.5*b2).mean()),min_density=float(rho.min()),min_pressure=float(p.min()),file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
r['study_conservation']=dict(rows=rows,mass_relative_change=rows[-1]['mass']/rows[0]['mass']-1,energy_relative_change=rows[-1]['energy']/rows[0]['energy']-1,energy_scope='Volume integral proxy from cell-centered pressure, velocity and magnetic fields; reflecting domain, resistive conversion retained.')
r['scientific_status']='exploration_pending_independent_method_review';r['kind']='autonomous_fresh_macro_trajectory';r['selection_policy']='First stored time >=0.8, origin-centered coalescence sheet; no kinetic evidence used to choose source.'
summary.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
