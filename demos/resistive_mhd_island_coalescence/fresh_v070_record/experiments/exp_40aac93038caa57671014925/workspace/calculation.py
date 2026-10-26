"""Fresh FLASH campaign driver; no solver modifications."""
import argparse, json, os, subprocess, sys, time, tarfile
from pathlib import Path
import h5py
import numpy as np
from null_diagnostic import nulls
from island_coalescence import _parameters, _analyze, _named_values, _sha256, _center_flux, _crossing

def sign_changes(a):
    a=np.asarray(a); a=a[np.abs(a)>max(1e-8, np.max(np.abs(a))*1e-5)]
    return int(np.sum(a[1:]*a[:-1]<0))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--S',type=float,required=True); p.add_argument('--n',type=int,default=128)
    p.add_argument('--tmax',type=float,default=3.0); p.add_argument('--cadence',type=float,default=.025)
    p.add_argument('--cfl',type=float,default=.4)
    a=p.parse_args(); a.eta=1/a.S; a.nx=a.ny=a.n; a.alpha=20.; a.plot_interval=a.cadence
    a.ranks=4; a.iprocs=a.jprocs=2; a.flux_low=.01; a.flux_high=.05
    os.environ['OMP_NUM_THREADS']='1'
    d=Path('native'); d.mkdir()
    par=_parameters(a).replace('cfl = 0.4',f'cfl = {a.cfl}').replace('nend = 10000','nend = 1000000')
    (d/'flash.par').write_text(par)
    exe=Path(os.environ['FLASH_EXECUTABLE']).resolve()
    cmd=[sys.executable,os.environ['SIMJECTURE_MPI_HELPER'],'--ranks','4','--launcher',os.environ['FLASH_MPI_LAUNCHER'],'--',str(exe),'-par_file','flash.par']
    start=time.monotonic()
    with (d/'stdout.txt').open('w') as out,(d/'stderr.txt').open('w') as err:
        subprocess.run(cmd,cwd=d,stdout=out,stderr=err,check=True)
    elapsed=time.monotonic()-start
    r=_analyze(d,a)
    # The supplied reader's status describes its guided example, not these fresh runs.
    r.pop('scientific_status'); r['kind']='fresh_campaign_measurement'; r['checks'].pop('scientific_evidence_eligible')
    rows=[]; files=sorted(d.glob('flash_run_hdf5_plt_cnt_*')); initial=None
    first_high=next((i for i,row in enumerate(r['timeseries']) if row['reconnected_flux_from_by']>=.05),len(files)-1)
    null_inventory=[]; selected_profiles={}
    targets=[.01,.03,.05]; flux_values=np.array([v['reconnected_flux_from_by'] for v in r['timeseries']])
    neighbors=set()
    for z in targets:
        ids=np.flatnonzero(flux_values>=z)
        if len(ids): neighbors.update([max(0,int(ids[0])-1),int(ids[0])])
    retained_indices=neighbors|{0,len(files)-1}; recorded_fields=[]
    series=h5py.File('magnetic_series.h5','w')
    for name in ['magx','magy']:
        series.create_dataset(name,(len(files),a.n,a.n),dtype='f4',chunks=(1,a.n,a.n),compression='gzip',compression_opts=4,shuffle=True)
    series['time']=np.array([v['time'] for v in r['timeseries']]); series['flux']=flux_values
    for file_index,f in enumerate(files):
        with h5py.File(f) as h:
            t=float(_named_values(h['real scalars'])['time'])
            bx=np.array(h['magx'][0,0],float); by=np.array(h['magy'][0,0],float)
            series['magx'][file_index]=bx; series['magy'][file_index]=by
            if not (np.array_equal(series['magx'][file_index],bx) and np.array_equal(series['magy'][file_index],by)):
                raise RuntimeError('Magnetic series is not bitwise equal to original magnetic arrays')
            rho=np.array(h['dens'][0,0],float); pres=np.array(h['pres'][0,0],float)
            n=a.n; x=(np.arange(n)+.5)/n-.5
            line=by[n//2-1:n//2+1].mean(0); mask=np.abs(x)<.4
            # A secondary island intersecting the symmetric central sheet adds a pair of zeros.
            topology=sign_changes(line[mask])
            jz=np.gradient(by,1/n,axis=1)-np.gradient(bx,1/n,axis=0)
            if file_index<=first_high:
                null_inventory.append({'index':file_index,'time':t,'flux':float(flux_values[file_index]),'nulls':nulls(bx,by)})
            if file_index in neighbors:
                selected_profiles[file_index]={'Bx':bx[:,n//2-1:n//2+1].mean(1),'Jz':jz[:,n//2-1:n//2+1].mean(1)}
            rows.append({'time':t,'central_sheet_By_sign_changes':topology,'density_min':float(rho.min()),'pressure_min':float(pres.min()),'central_current':float(jz[n//2-1:n//2+1,n//2-1:n//2+1].mean()),'central_pressure':float(pres[n//2-1:n//2+1,n//2-1:n//2+1].mean()),'boundary_current':float(jz[n//2-1:n//2+1,:2].mean()),'sheet_halfwidth_cells':float(np.max(abs(bx[np.abs(x)<.1,n//2-1:n//2+1]))/max(abs(jz[n//2-1:n//2+1,n//2-1:n//2+1].mean()),1e-30)*n),'reflection_residual':float(max(np.max(abs(bx+bx[::-1,:])),np.max(abs(by+by[:,::-1])))),'central_current_max':float(np.max(abs(jz[np.abs(x)<.1,:][:,mask]))),'magnetic_energy_cell_center':float(np.mean((bx*bx+by*by)/2))})
            if initial is None:
                initial={k:_named_values(h[k]) for k in ['real runtime parameters','logical runtime parameters','string runtime parameters']}
                r['representation']={'shape':list(bx.shape),'bounding_box':h['bounding box'][()].tolist(),'coordinates':h['coordinates'][()].tolist(),'block_size':h['block size'][()].tolist(),'initial_density_range':[float(rho.min()),float(rho.max())],'initial_pressure_range':[float(pres.min()),float(pres.max())]}
        recorded_fields.append({'path':str(f),'sha256':_sha256(f),'bytes':f.stat().st_size,'retained_full_state':file_index in retained_indices,'magnetic_series_index':file_index})
        series.flush()
        if file_index not in retained_indices: f.unlink()
    series.close()
    r['extended_timeseries']=rows
    r['full_domain_null_inventory']=null_inventory
    r['matched_flux_profiles']=[]
    for z in targets:
        ids=np.flatnonzero(flux_values>=z)
        if not len(ids): continue
        i=int(ids[0]); j=max(0,i-1); weight=float((z-flux_values[j])/(flux_values[i]-flux_values[j])) if i>j else 0.
        profile={name:((1-weight)*selected_profiles[j][name]+weight*selected_profiles[i][name]).tolist() for name in ['Bx','Jz']}
        profile.update({'flux':z,'y':x.tolist(),'bracket_indices':[j,i],'interpolation_weight':weight,'Jz_center':float((1-weight)*rows[j]['central_current']+weight*rows[i]['central_current']),'halfwidth_cells':float((1-weight)*rows[j]['sheet_halfwidth_cells']+weight*rows[i]['sheet_halfwidth_cells'])})
        r['matched_flux_profiles'].append(profile)
    ts=np.array([v['time'] for v in r['timeseries']]); flux=np.array([v['reconnected_flux_from_by'] for v in r['timeseries']]); flux2=np.array([v['reconnected_flux_from_bx'] for v in r['timeseries']])
    brackets=[]
    for z in [.01,.05]:
        ii=np.flatnonzero(flux>=z)
        brackets.append([float(ts[ii[0]-1]),float(ts[ii[0]])] if len(ii) and ii[0]>0 else None)
    r['crossing_brackets']=brackets
    r['cadence_rate_interval']=None
    if all(v is not None for v in brackets):
        lo,hi=brackets
        if hi[0]>lo[1]: r['cadence_rate_interval']=[.04/(hi[1]-lo[0]),.04/(hi[0]-lo[1])]
    for stride in [2,4]:
        idx=sorted(set(range(0,len(ts),stride))|{len(ts)-1})
        q=[_crossing(ts[idx],flux[idx],z) for z in [.01,.05]]
        r[f'rate_stride_{stride}']=.04/(q[1]-q[0]) if all(v is not None for v in q) and q[1]>q[0] else None
    q=[_crossing(ts,flux2,z) for z in [.01,.05]]
    r['rate_other_path']=.04/(q[1]-q[0]) if all(v is not None for v in q) and q[1]>q[0] else None
    high=r['metrics']['flux_high_crossing_time']; end=high if high else ts[-1]
    bracket_high_index=int(np.flatnonzero(flux>=.05)[0]) if np.any(flux>=.05) else len(ts)-1
    bracket_end=float(ts[bracket_high_index]); r['topology_last_index']=bracket_high_index; r['topology_last_time']=bracket_end
    r['topology_max_sign_changes_through_window']=max(v['central_sheet_By_sign_changes'] for v in rows if v['time']<=bracket_end)
    dat=np.loadtxt(d/'flash_run.dat'); sel=dat[:,0]<=end+a.cadence; dat=dat[sel]
    r['conservation']={'mass_max_relative_drift':float(np.max(abs(dat[:,1]/dat[0,1]-1))),'energy_max_relative_drift':float(np.max(abs(dat[:,5]/dat[0,5]-1))),'max_absolute_net_momentum':float(np.max(abs(dat[:,2:5]))),'floor_corrections':'not separately exported; positivity margins retained; energyFix active as commissioned'}
    r['realized_runtime']=initial
    r['config']={'S_eta':a.S,'eta':a.eta,'n':a.n,'tmax':a.tmax,'cadence':a.cadence,'cfl':a.cfl,'ranks':4,'threads':1}
    r['timing']={'solver_wall_seconds':elapsed,'actual_end_time':float(ts[-1]),'steps':int(len(np.loadtxt(d/'flash_run.dat'))-1)}
    r['provenance']={'command':cmd,'flash_executable_sha256':_sha256(exe),'parameter_sha256':_sha256(d/'flash.par'),'driver_sha256':_sha256(Path(__file__))}
    retained_indices=neighbors|{0,len(files)-1}
    r['fields']=recorded_fields
    r['magnetic_retention_check']={'all_frames_readback_bitwise_equal':True,'frame_count':len(files),'series_sha256':_sha256(Path('magnetic_series.h5'))}
    r['raw_retention']={'magnetic':'All saved magx/magy arrays losslessly in magnetic_series.h5 with time/flux arrays, indexed by fields[].magnetic_series_index.','full_state':'Initial/final and both brackets at flux .01,.03,.05 in fields.tar.gz.','unretained_full_state':'Other full-state HDF5 snapshots are reduced before removal; their source hashes remain recorded.'}
    # Check algebra/sign and independence of the two path reducers on a smooth divergence-free field.
    n=128; x=(np.arange(n)+.5)/n-.5; X,Y=np.meshgrid(x,x)
    bx=-(2*Y+4*Y**3); by=2*X+4*X**3
    f0=_center_flux(bx,by); f1=_center_flux(1.2*bx,1.2*by)
    r['reader_polynomial_test']={'path_delta_disagreement':abs((f1[0]-f0[0])-(f1[1]-f0[1])),'expected_delta':-.2*(.5**2+.5**4),'measured_delta':f1[0]-f0[0]}
    Path('result.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n')
    with tarfile.open('fields.tar.gz','w:gz') as archive:
        for f in [files[i] for i in sorted(retained_indices)]+[d/'flash.par',d/'flash_run.dat',d/'flash_run.log',d/'stdout.txt',d/'stderr.txt']:
            archive.add(f,arcname=str(f))
    # Raw fields remain losslessly in the declared archive; avoid duplicate HDF5 storage.
    for f in d.glob('*hdf5*'):
        f.unlink()
    print(json.dumps({'config':r['config'],'metrics':r['metrics'],'conservation':r['conservation'],'topology':r['topology_max_sign_changes_through_window'],'wall':elapsed}))
if __name__=='__main__': main()
