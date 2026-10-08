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
  sampling=[];shear=[];reconstruction=[]
  for row in h:
   pre=f"step{row['step']}_{sp}_";P=raw[pre+'pressure'];tr=np.trace(P,axis1=1,axis2=2);eff=raw[pre+'effective_count']
   if pre+'normalized_velocity_fourth_moment' in raw:
    q4=raw[pre+'normalized_velocity_fourth_moment'];frob=np.sum(P*P,axis=(1,2))/tr**2
    variance=np.maximum(0,3*(q4-frob)/eff)
    sampling.append(float(2*np.sqrt(variance.sum())/len(eff)))
   sub=f"substep{row['step']}_{sp}_"
   if sub+'pressure' in raw:
    nb=r.get('secondary_bins',0);bp=r['moment_bins_per_axis'];assert nb==2*bp
    Ps=raw[sub+'pressure'].reshape(nb,nb,3,3);ns=raw[sub+'number_density'].reshape(nb,nb);vs=raw[sub+'velocity'].reshape(nb,nb,3);mass=m['scales']['ion_mass_kg' if sp=='ions' else 'electron_mass_kg'];rec=[];frac=[]
    for iz in range(bp):
     for ix in range(bp):
      sl=(slice(iz*2,iz*2+2),slice(ix*2,ix*2+2));n=ns[sl].reshape(4);v=vs[sl].reshape(4,3);mean=(n[:,None]*v).sum(0)/n.sum();dv=v-mean;S=mass*np.einsum('n,ni,nj->ij',n,dv,dv)/4;R=Ps[sl].reshape(4,3,3).mean(0)+S;rec.append(R);frac.append(np.linalg.norm(S)/(np.trace(R)/np.sqrt(3)))
    reconstruction.append(float(np.linalg.norm(np.array(rec)-P)/np.linalg.norm(P)));shear.append(float(max(frac)))
  est['sampling_two_sigma_estimate_max']=max(sampling) if sampling else None
  est['secondary_coarse_tensor_reconstruction_rms_max']=max(reconstruction) if reconstruction else None
  est['secondary_between_bin_velocity_pressure_upper_max']=max(shear) if shear else None
  origin={key:float(max(raw[f"step{x['step']}_{sp}_"+key].max() for x in h)) for key in ['origin_outside_small_patch_fraction','origin_boundary_collar_fraction'] if 'step0_'+sp+'_'+key in raw}
  est.update(initial_scalar_P=scalar[0],final_scalar_P=scalar[-1],scalar_P_ratio_final_initial=float(scalar[-1]/scalar[0]),density_ratio_final_initial=float(dens[-1].mean()/dens[0].mean()),origin=origin)
  species[sp]=est;records[label+'_'+sp]=dict(t=times,p=scalar,n=dens.mean(1),v=vel.mean(1),A=np.array(est['area_means']))
 # Grid-to-initial binned moments: volume/cell average then local mean-subtracted source drift broadening.
 bins=r['moment_bins_per_axis'];l0=m['scales']['length_m'];rx,rz=r['roi_half_code'];area=(2*rx*l0/bins)*(2*rz*l0/bins);dx,dz=m['cell_size_m']
 def overlap(centers,spacing,half):
  edges=np.linspace(-half*l0,half*l0,bins+1)
  return np.maximum(0,np.minimum(edges[1:,None],centers[None,:]+spacing/2)-np.maximum(edges[:-1,None],centers[None,:]-spacing/2))
 wx=overlap(q['x'],dx,rx);wz=overlap(q['z'],dz,rz)
 def binref(value):return (wz@value@wx.T).ravel()/area
 nref=binref(q['n'])
 init={}
 for sp,key in [('ions','i'),('electrons','e')]:
  init[sp]=dict(density_rms_relative=float(np.sqrt(np.mean((raw['step0_'+sp+'_number_density']-nref)**2)/np.mean(nref*nref))),pressure_scalar_mean_ratio=float(np.trace(raw['step0_'+sp+'_pressure'],axis1=1,axis2=2).mean()/3 / binref(.5*q['p']).mean()))
 ji=e*(raw['step0_ions_number_density'][:,None]*raw['step0_ions_velocity']-raw['step0_electrons_number_density'][:,None]*raw['step0_electrons_velocity']);jref=binref(q['jy'])
 init['current_y_rms_relative']=float(np.sqrt(np.mean((ji[:,1]-jref)**2)/np.mean(jref*jref)));init['charge_imbalance_fraction']=float(np.max(abs(raw['step0_ions_number_density']-raw['step0_electrons_number_density']))/nref.mean())
 # Reduced energy: exact pinned single-level total columns, initial particle diagnostic known zero replaced by loader total.
 fe=np.atleast_2d(np.loadtxt(d/'reduced/field_energy.txt'));pe=np.atleast_2d(np.loadtxt(d/'reduced/particle_energy.txt'))
 assert 'total_lev0(J)' in (d/'reduced/field_energy.txt').read_text().splitlines()[0] and 'total(J)' in (d/'reduced/particle_energy.txt').read_text().splitlines()[0]
 assert np.array_equal(fe[:,0],pe[:,0]);total=fe[:,2]+pe[:,2];initial=sum(r['initial_maximum_particle_speed_over_c'][sp+'_initial_energy_J_per_m'] for sp in ['ions','electrons']);total[0]=fe[0,2]+initial
 active=np.array([x['field_activity'] for x in h]);Erms2=np.array([sum(v[k+'_roi_rms']**2 for k in ['Ex','Ey','Ez']) for v in active]);therm=np.array([1.5*(records[label+'_ions']['p'][i]+records[label+'_electrons']['p'][i]) for i in range(len(h))]);efraction=epsilon_0*.5*Erms2/therm
 summary[label]=dict(source_patch_sha256=hashlib.sha256(Path(patch).read_bytes()).hexdigest(),species=species,initial_match=init,dt_omega_pe=r['dt_omega_pe'],dt_omega_ce=r['dt_s']*m['scales']['omega_ci_reference_s1']*25,dx_over_de=m['cell_size_m'][0]/(m['scales']['ion_skin_depth_m']/5),dx_over_debye_reference=m['cell_size_m'][0]/(np.sqrt(float(q['te'].mean())/m['scales']['electron_mass_kg'])/m['scales']['omega_pe_reference_s1']),energy_initial_J_per_m=float(total[0]),energy_final_J_per_m=float(total[-1]),unclosed_energy_relative_change=float(total[-1]/total[0]-1),energy_accounting_limitation='Absorbed-particle energy and Poynting flux not available in this version; this is open-domain energy behavior, not a closed residual.',max_interior_electric_to_thermal_energy=float(efraction.max()),electric_to_thermal_energy_at_0p3=float(np.interp(.3,records[label+'_ions']['t'],efraction)),elapsed_seconds=r['elapsed_s'],storage_bytes=r['storage_bytes'])
 if r.get('boundary_accounting_enabled'):
  last=h[-1]['energy_boundary_accounting'];live=last['live_particle_energy_J_per_m'];qf=np.load(d/'final_fields.npz');dx,dz=m['cell_size_m']
  # Native reduced field diagnostic final may be one period before actual last step.
  est_field=fe[-1,2]
  residual=(live+est_field+last['absorbed_particle_energy_J_per_m']+last['estimated_poynting_outflow_J_per_m']-total[0])/total[0]
  summary[label]['boundary_budget']=dict(**last,estimated_relative_residual=float(residual),field_energy_sample_step=float(fe[-1,0]),final_step=r['steps'],limitation='Nearest-cell Poynting quadrature and field diagnostic may precede final step; cadence/spatial check required for precise closure.')
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

for label,directory,patch in a.case:
 d=Path(directory);raw=np.load(d/'moments.npz');h=json.load(open(d/'history.json'));m=json.load(open(Path(patch).with_suffix('.json')));r=json.load(open(d/'result.json'));bins=r['moment_bins_per_axis'];rx,rz=r['roi_half_code'];fig,axs=plt.subplots(2,2,figsize=(10,7))
 for i,sp in enumerate(['ions','electrons']):
  P=np.array([raw[f"step{row['step']}_{sp}_pressure"] for row in h]);scalar=np.trace(P,axis1=2,axis2=3).mean(1)/3;t=[row['time_omegaci'] for row in h]
  for j,cname in enumerate(['XX','YY','ZZ']):axs[i,0].plot(t,P[:,:,j,j].mean(1)/scalar,label='P'+cname+'/p')
  for j,k,cname in [(0,1,'XY'),(0,2,'XZ'),(1,2,'YZ')]:axs[i,0].plot(t,P[:,:,j,k].mean(1)/scalar,ls='--',label='P'+cname+'/p')
  axs[i,0].set(title=sp+' pressure tensor',xlabel='t Omega_ci');axs[i,0].legend(fontsize=7,ncol=2);im=axs[i,1].imshow(raw[f"step{h[-1]['step']}_{sp}_isotropy_departure"].reshape(bins,bins),origin='lower',extent=[-rx,rx,-rz,rz],aspect='auto',vmin=0,vmax=.2);fig.colorbar(im,ax=axs[i,1],label='Final local A');axs[i,1].set(xlabel='X code',ylabel='Z code')
 fig.tight_layout();fig.savefig(label+'_pressure_tensor.png',dpi=160)
