"""Lossless magnetic-series and compact matched-flux diagnostics from registered raw archive."""
import argparse,hashlib,io,json,tarfile
from pathlib import Path
import h5py
import numpy as np
from null_diagnostic import nulls
p=argparse.ArgumentParser();p.add_argument('--summary',required=True);p.add_argument('--archive',required=True);p.add_argument('--prefix',required=True);a=p.parse_args()
r=json.loads(Path(a.summary).read_text());times=r['timeseries']; flux=np.array([v['reconnected_flux_from_by'] for v in times]); n=r['config']['n'];x=(np.arange(n)+.5)/n-.5
end=int(np.flatnonzero(flux>=.05)[0]);wanted={v['path']:(i,v) for i,v in enumerate(r['fields'])}; profiles=[];inventory=[];scalar=[]
with h5py.File(a.prefix+'_magnetic.h5','w') as series,tarfile.open(a.archive,'r|gz') as tar:
 for name in ['magx','magy']: series.create_dataset(name,(len(times),n,n),dtype='f4',chunks=(1,n,n),compression='gzip',compression_opts=4,shuffle=True)
 series['time']=np.array([v['time'] for v in times]);series['flux']=flux
 series['source_sha256']=np.array([v['sha256'].encode() for v in r['fields']],dtype='S64')
 for m in tar:
  if m.name not in wanted:continue
  i,v=wanted[m.name];b=tar.extractfile(m).read()
  if hashlib.sha256(b).hexdigest()!=v['sha256']:raise ValueError('Field hash mismatch')
  with h5py.File(io.BytesIO(b)) as h: bx=np.array(h['magx'][0,0],float);by=np.array(h['magy'][0,0],float)
  series['magx'][i]=bx;series['magy'][i]=by
  j=np.gradient(by,1/n,axis=1)-np.gradient(bx,1/n,axis=0);jc=float(j[n//2-1:n//2+1,n//2-1:n//2+1].mean()); width=float(np.max(abs(bx[np.abs(x)<.1,n//2-1:n//2+1]))/abs(jc))
  scalar.append({'index':i,'flux':float(flux[i]),'Jz_center':jc,'halfwidth':width,'halfwidth_cells':width*n})
  profiles.append({'Bx':bx[:,n//2-1:n//2+1].mean(1),'Jz':j[:,n//2-1:n//2+1].mean(1)})
  if i<=end:inventory.append({'index':i,'time':times[i]['time'],'flux':float(flux[i]),'nulls':nulls(bx,by),'source_sha256':v['sha256']})
matched=[]
for z in [.01,.03,.05]:
 i=int(np.flatnonzero(flux>=z)[0]); j=i-1;w=float((z-flux[j])/(flux[i]-flux[j]));d={'flux':z,'y':x.tolist(),'bracket_indices':[j,i],'weight':w}
 for name in ['Bx','Jz']:d[name]=((1-w)*profiles[j][name]+w*profiles[i][name]).tolist()
 for name in ['Jz_center','halfwidth','halfwidth_cells']:d[name]=(1-w)*scalar[j][name]+w*scalar[i][name]
 matched.append(d)
result={'config':r['config'],'upper_bracket_index':end,'upper_bracket_time':times[end]['time'],'upper_bracket_flux':float(flux[end]),'inventory':inventory,'matched_profiles':matched,'scalar_profiles':scalar,'topology_counts':sorted(set((sum(q[2]=='X' for q in v['nulls']),sum(q[2]=='O' for q in v['nulls'])) for v in inventory))}
Path(a.prefix+'_reduction.json').write_text(json.dumps(result,indent=2)+'\n')
print({'prefix':a.prefix,'frames':len(inventory),'counts':result['topology_counts'],'upper_bracket_time':result['upper_bracket_time']})
