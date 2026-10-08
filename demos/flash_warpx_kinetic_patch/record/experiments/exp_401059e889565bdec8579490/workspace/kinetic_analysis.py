"""Independent frozen-tensor audit, initialization moments and finite-window controls."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from scipy.constants import e,epsilon_0,c
from estimator import estimate
p=argparse.ArgumentParser();p.add_argument('--case',action='append',nargs=3,metavar=('LABEL','DIRECTORY','PATCH'));a=p.parse_args()
summary={};records={}
for label,directory,patch in a.case:
 d=Path(directory);r=json.loads((d/'result.json').read_text());h=json.loads((d/'history.json').read_text());raw=np.load(d/'moments.npz');q=np.load(patch);m=json.loads(Path(patch).with_suffix('.json').read_text());species={}
 for sp in ['ions','electrons']:
  est=estimate(raw,h,sp);prs=np.array([raw[f"step{x['step']}_{sp}_pressure"] for x in h]);dens=np.array([raw[f"step{x['step']}_{sp}_number_density"] for x in h]);vel=np.array([raw[f"step{x['step']}_{sp}_velocity"] for x in h]);times=np.array([x['time_omegaci'] for x in h]);scalar=np.trace(prs,axis1=2,axis2=3).mean(axis=1)/3
  origin={key:float(max(raw[f"step{x['step']}_{sp}_"+key].max() for x in h)) for key in ['origin_outside_small_patch_fraction','origin_boundary_collar_fraction'] if 'step0_'+sp+'_'+key in raw}
  est.update(initial_scalar_P=scalar[0],final_scalar_P=scalar[-1],scalar_P_ratio_final_initial=float(scalar[-1]/scalar[0]),density_ratio_final_initial=float(dens[-1].mean()/dens[0].mean()),origin=origin)
  species[sp]=est;records[label+'_'+sp]=dict(t=times,p=scalar,n=dens.mean(1),v=vel.mean(1),A=np.array(est['area_means']))
 # Grid-to-initial binned moments: volume/cell average then local mean-subtracted source drift broadening.
 bins=r['moment_bins_per_axis'];l0=m['scales']['length_m'];rx,rz=r['roi_half_code'];xp,zp=np.meshgrid(q['x']/l0,q['z']/l0);ix=((xp+rx)/(2*rx)*bins).astype(int);iz=((zp+rz)/(2*rz)*bins).astype(int);inside=(xp>=-rx)&(xp<rx)&(zp>=-rz)&(zp<rz);ind=(iz*bins+ix)[inside];area=(2*rx*l0/bins)*(2*rz*l0/bins);cellarea=np.prod(m['cell_size_m']);nref=np.bincount(ind,weights=q['n'][inside]*cellarea,minlength=bins*bins)/area
 init={}
 for sp,key in [('ions','i'),('electrons','e')]:
  init[sp]=dict(density_rms_relative=float(np.sqrt(np.mean((raw['step0_'+sp+'_number_density']-nref)**2)/np.mean(nref*nref))),pressure_scalar_mean_ratio=float(np.trace(raw['step0_'+sp+'_pressure'],axis1=1,axis2=2).mean()/3 / (np.bincount(ind,weights=.5*q['p'][inside]*cellarea,minlength=bins*bins)/area).mean()))
 ji=e*(raw['step0_ions_number_density'][:,None]*raw['step0_ions_velocity']-raw['step0_electrons_number_density'][:,None]*raw['step0_electrons_velocity']);jref=np.bincount(ind,weights=q['jy'][inside]*cellarea,minlength=bins*bins)/area
 init['current_y_rms_relative']=float(np.sqrt(np.mean((ji[:,1]-jref)**2)/np.mean(jref*jref)));init['charge_imbalance_fraction']=float(np.max(abs(raw['step0_ions_number_density']-raw['step0_electrons_number_density']))/nref.mean())
 # Reduced energy: exact pinned single-level total columns, initial particle diagnostic known zero replaced by loader total.
 fe=np.atleast_2d(np.loadtxt(d/'reduced/field_energy.txt'));pe=np.atleast_2d(np.loadtxt(d/'reduced/particle_energy.txt'))
 assert 'total_lev0(J)' in (d/'reduced/field_energy.txt').read_text().splitlines()[0] and 'total(J)' in (d/'reduced/particle_energy.txt').read_text().splitlines()[0]
 assert np.array_equal(fe[:,0],pe[:,0]);total=fe[:,2]+pe[:,2];initial=sum(r['initial_maximum_particle_speed_over_c'][sp+'_initial_energy_J_per_m'] for sp in ['ions','electrons']);total[0]=fe[0,2]+initial
 active=np.array([x['field_activity'] for x in h]);Erms2=np.array([sum(v[k+'_roi_rms']**2 for k in ['Ex','Ey','Ez']) for v in active]);therm=np.array([1.5*(records[label+'_ions']['p'][i]+records[label+'_electrons']['p'][i]) for i in range(len(h))]);efraction=epsilon_0*.5*Erms2/therm
 summary[label]=dict(source_patch_sha256=hashlib.sha256(Path(patch).read_bytes()).hexdigest(),species=species,initial_match=init,dt_omega_pe=r['dt_omega_pe'],dt_omega_ce=r['dt_s']*m['scales']['omega_ci_reference_s1']*25,dx_over_de=m['cell_size_m'][0]/(m['scales']['ion_skin_depth_m']/5),dx_over_debye_reference=m['cell_size_m'][0]/(np.sqrt(float(q['te'].mean())/m['scales']['electron_mass_kg'])/m['scales']['omega_pe_reference_s1']),energy_initial_J_per_m=float(total[0]),energy_final_J_per_m=float(total[-1]),unclosed_energy_relative_change=float(total[-1]/total[0]-1),energy_accounting_limitation='Absorbed-particle energy and Poynting flux not available in this version; this is open-domain energy behavior, not a closed residual.',max_interior_electric_to_thermal_energy=float(efraction.max()),electric_to_thermal_energy_at_0p3=float(np.interp(.3,records[label+'_ions']['t'],efraction)),elapsed_seconds=r['elapsed_s'],storage_bytes=r['storage_bytes'])
comparison={}
labels=list(summary)
if len(labels)>1:
 ref=labels[0]
 for label in labels[1:]:
  comparison[label]={}
  for sp in ['ions','electrons']:
   x=records[ref+'_'+sp];y=records[label+'_'+sp];tt=x['t'];mask=(tt>=.3)&(tt<=.8)
   comparison[label][sp]=dict(A_mean_difference=summary[label]['species'][sp]['area_time_mean']-summary[ref]['species'][sp]['area_time_mean'],max_time_area_mean_difference=float(np.max(abs(np.interp(tt[mask],y['t'],y['A'])-x['A'][mask]))),maximum_pressure_mean_relative_difference=float(np.max(abs(np.interp(tt[mask],y['t'],y['p'])/x['p'][mask]-1))),maximum_density_mean_relative_difference=float(np.max(abs(np.interp(tt[mask],y['t'],y['n'])/x['n'][mask]-1))))
Path('analysis.json').write_text(json.dumps(dict(cases=summary,comparisons=comparison),indent=2,allow_nan=False)+'\n')
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
fig,axs=plt.subplots(2,2,figsize=(10,7))
for label in summary:
 for sp in ['ions','electrons']:
  rec=records[label+'_'+sp];axs[0,0].plot(rec['t'],rec['A'],label=label+' '+sp);axs[0,1].plot(rec['t'],rec['p']/rec['p'][0],label=label+' '+sp);axs[1,0].plot(rec['t'],rec['n']/rec['n'][0],label=label+' '+sp)
axs[0,0].axhline(.2,color='k',ls='--');axs[0,0].axvspan(.3,.8,color='grey',alpha=.1)
for ax,title in zip(axs.flat,['Area mean tensor departure','Mean scalar pressure / initial','Mean density / initial','Finite control comparison']):ax.set(xlabel='t Omega_ci reference',title=title);ax.legend(fontsize=7)
axs[1,1].axis('off');axs[1,1].text(0,1,json.dumps(comparison,indent=1)[:1100],va='top',fontsize=7)
fig.tight_layout();fig.savefig('pressure_controls.png',dpi=160)
# Raw initial/final grid fields and local tensors, from actual snapshots.
for label,directory,patch in a.case:
 d=Path(directory);m=json.loads(Path(patch).with_suffix('.json').read_text());b=np.array(m['bounds_xz_m'])/m['scales']['length_m'];fig,axs=plt.subplots(1,2,figsize=(9,4))
 for ax,state in zip(axs,['initial','final']):
  q=np.load(d/(state+'_fields.npz'));bx=q['bx'];bz=q['bz'];nx=m['shape_zx'][1];nz=m['shape_zx'][0]
  if bx.shape[1]==nx+1:bx=(bx[:,:-1]+bx[:,1:])/2
  if bz.shape[0]==nz+1:bz=(bz[:-1,:]+bz[1:,:])/2
  im=ax.imshow(np.hypot(bx,bz)/m['scales']['magnetic_T'],origin='lower',extent=[*b[0],*b[1]],aspect='equal');fig.colorbar(im,ax=ax,label='|B|/B0');ax.set(title=state,xlabel='X code',ylabel='Z code')
 fig.tight_layout();fig.savefig(label+'_kinetic_fields.png',dpi=160)
