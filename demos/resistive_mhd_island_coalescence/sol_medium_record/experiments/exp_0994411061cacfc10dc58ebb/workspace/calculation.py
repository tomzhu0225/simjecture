"""Agent-owned FLASH evolution and auditable field diagnostics."""
import argparse,os,sys,subprocess,json,time
from pathlib import Path
import numpy as np
import h5py
from scipy.signal import find_peaks
import guided_reader as g

def main():
 p=argparse.ArgumentParser();p.add_argument('--eta',type=float,required=True);p.add_argument('--n',type=int,required=True);p.add_argument('--tmax',type=float,default=3.0);p.add_argument('--cadence',type=float,default=.025);p.add_argument('--cfl',type=float,default=.4);p.add_argument('--archive');p.add_argument('--ranks',type=int,choices=[1,2,4],default=4)
 a=p.parse_args();a.nx=a.ny=a.n;a.alpha=20.;a.plot_interval=a.cadence;a.iprocs=2 if a.ranks>1 else 1;a.jprocs=2 if a.ranks==4 else 1;a.flux_low=.01;a.flux_high=.05
 out=Path('case');out.mkdir();par=g._parameters(a).replace('nend = 10000','nend = 1000000').replace('cfl = 0.4',f'cfl = {a.cfl}');(out/'flash.par').write_text(par)
 exe=Path(os.environ['FLASH_EXECUTABLE']).resolve();launcher=os.environ['FLASH_MPI_LAUNCHER']
 cmd=[sys.executable,os.environ['SIMJECTURE_MPI_HELPER'],'--ranks',str(a.ranks),'--launcher',launcher,'--',str(exe),'-par_file','flash.par']
 start=time.monotonic()
 if a.archive:
  import tarfile
  with tarfile.open(a.archive) as tar:tar.extractall(out,filter='data')
 else:
  with (out/'execution.log').open('w') as f:subprocess.run(cmd,cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
 summary=g._analyze(out,a)
 files=sorted(out.glob('flash_run_hdf5_plt_cnt_*'));fields={k:[] for k in ['dens','pres','velx','vely','magx','magy','magp','divb']};ts=[];rows=[];identities=[]
 for file in files:
  with h5py.File(file) as h:
   t=float(g._named_values(h['real scalars'])['time']);ts.append(t)
   fs={k:np.array(h[k][0,0],dtype=float) for k in fields}
   for k in fields:fields[k].append(fs[k].astype('float32'))
   bx,by=fs['magx'],fs['magy'];dx=1/a.n;j=np.gradient(by,dx,axis=1)-np.gradient(bx,dx,axis=0)
   profile=j[:,a.n//2-1:a.n//2+1].mean(1);center=abs(profile[a.n//2-1:a.n//2+1].mean());mask=np.abs(profile)>=center/2
   lo=a.n//2-1;hi=a.n//2
   while lo>0 and mask[lo-1]:lo-=1
   while hi<a.n-1 and mask[hi+1]:hi+=1
   # Flux along the sheet y=0: derivative is By. Extra prominent extrema
   # inside |x|<0.25 are a resolved secondary-island veto.
   psi=np.cumsum(by[a.n//2-1:a.n//2+1].mean(0))*dx
   strip=psi[a.n//4:3*a.n//4];prom=1e-4
   peaks,_=find_peaks(strip,prominence=prom,distance=4);troughs,_=find_peaks(-strip,prominence=prom,distance=4)
   rho,pr=fs['dens'],fs['pres'];energy=np.mean(pr/(5/3-1)+.5*rho*(fs['velx']**2+fs['vely']**2)+.5*(bx**2+by**2))
   rows.append(dict(time=t,current_center=center,sheet_fwhm_cells=hi-lo+1,secondary_extrema=max(0,len(peaks)+len(troughs)-1),sheet_flux_extrema=len(peaks)+len(troughs),mass=float(rho.mean()),energy=float(energy),density_min=float(rho.min()),pressure_min=float(pr.min()),max_j=float(abs(j).max())))
   if len(ts)==1:
    identities=[{k:g._named_values(h[k]) for k in ['real runtime parameters','integer runtime parameters','logical runtime parameters','string runtime parameters','integer scalars']}]
    identities[0]['bounding_box']=h['bounding box'][()].tolist();identities[0]['coordinates']=h['coordinates'][()].tolist()
  summary['diagnostics']=rows
  Path('checkpoint.json').write_text(json.dumps({'actual_end':t,'states':len(ts)}))
 np.savez_compressed('raw_fields.npz',time=np.array(ts),**{k:np.stack(v) for k,v in fields.items()})
 low=summary['metrics']['flux_low_crossing_time'];high=summary['metrics']['flux_high_crossing_time']
 window=[r for r in rows if low is not None and high is not None and low-a.cadence<=r['time']<=high+a.cadence]
 summary['window']={'min_sheet_fwhm_cells':min([r['sheet_fwhm_cells'] for r in window],default=None),'max_secondary_extrema':max([r['secondary_extrema'] for r in window],default=None),'sample_count':len(window)}
 summary['conservation']={'mass_relative_drift':max(abs(r['mass']/rows[0]['mass']-1) for r in rows),'energy_relative_drift':max(abs(r['energy']/rows[0]['energy']-1) for r in rows),'floor_hits_sampled':sum(r['density_min']<=1e-11 or r['pressure_min']<=1e-11 for r in rows),'floor_correction_budget':None,'floor_correction_budget_reason':'Solver does not output integrated floor/source corrections; sampled states and total budgets constrain but cannot exclude between-output corrections.'}
 summary['provenance']={'command':cmd,'executable_sha256':g._sha256(exe),'parameter_sha256':g._sha256(out/'flash.par'),'driver_sha256':g._sha256(Path(__file__)),'hdf5_hashes':{f.name:g._sha256(f) for f in files},'runtime':identities,'elapsed_seconds':time.monotonic()-start}
 summary['normalization']={'L0':1.,'B0':1.,'rho0':1.,'vA0':1.,'R':'(0.05-0.01)/(t_high-t_low)/(B0*vA0)','S_eta':'1/eta nominal; not dimensional Lundquist number'}
 summary['actual_end']=ts[-1];summary['kind']='agent_owned_island_diagnostics';summary.pop('scientific_status',None);summary['checks'].pop('scientific_evidence_eligible',None)
 Path('result.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
 for file in files:file.unlink()
 print(json.dumps({'rate':summary['metrics']['normalized_flux_slope'],'window':summary['window'],'conservation':summary['conservation']}))
if __name__=='__main__':
 if '--report' in sys.argv:
  import study_analysis
  study_analysis.main(sys.argv[sys.argv.index('--report')+1])
 else:main()
