"""Recorded postprocessing: deterministic rate envelope and full-domain magnetic-null inventory."""
import json,tarfile,io,hashlib
from pathlib import Path
import numpy as np
import h5py
from scipy.ndimage import label

def nulls(bx,by):
    cs=[]
    for b in [bx,by]: cs.append(np.stack([b[:-1,:-1],b[1:,:-1],b[:-1,1:],b[1:,1:]]))
    mask=(cs[0].min(0)<=0)&(cs[0].max(0)>=0)&(cs[1].min(0)<=0)&(cs[1].max(0)>=0)
    ys,xs=np.where(mask); found=[]; n=bx.shape[0]
    for y,x in zip(ys,xs):
        a=np.array([bx[y,x],by[y,x]]);b=np.array([bx[y,x+1],by[y,x+1]])-a;c=np.array([bx[y+1,x],by[y+1,x]])-a;d=np.array([bx[y+1,x+1],by[y+1,x+1]])-a-b-c
        uv=np.array([.5,.5])
        for _ in range(12):
            u,v=uv; jac=np.column_stack([b+d*v,c+d*u]);f=a+b*u+c*v+d*u*v
            try: step=np.linalg.solve(jac,f)
            except np.linalg.LinAlgError:break
            uv-=step
            if np.max(abs(step))<1e-9:break
        u,v=uv;f=a+b*u+c*v+d*u*v
        if not(-1e-7<=u<=1+1e-7 and -1e-7<=v<=1+1e-7) or np.max(abs(f))>1e-6:continue
        xx=(x+.5+u)/n-.5; yy=(y+.5+v)/n-.5
        if any(np.hypot(xx-q[0],yy-q[1])<1e-5 for q in found):continue
        det=float(np.linalg.det(np.column_stack([b+d*v,c+d*u])))
        found.append([float(xx),float(yy),'O' if det>0 else 'X'])
    return found

cases=json.loads(Path('analysis_inputs.json').read_text()); results=[]
for c in cases:
    r=json.loads(Path(c['summary']).read_text()); S=r['config']['S_eta'];n=r['config']['n'];kind=c['kind']; entry={'experiment':c['experiment'],'S_eta':S,'n':n,'kind':kind,'rate':r['metrics']['normalized_flux_slope']}
    if c.get('archive'):
        expected={v['path']:v['sha256'] for v in r['fields']}; crossing_index=next(i for i,row in enumerate(r['timeseries']) if row['reconnected_flux_from_by']>=.05)
        wanted={r['fields'][i]['path']:r['timeseries'][i] for i in range(crossing_index+1)}
        inv=[];profiles=[]
        with tarfile.open(c['archive'],'r|gz') as tar:
            for m in tar:
                if m.name not in wanted:continue
                buf=tar.extractfile(m).read(); actual=hashlib.sha256(buf).hexdigest()
                if actual!=expected[m.name]: raise ValueError('Field hash mismatch')
                with h5py.File(io.BytesIO(buf)) as h:
                    bx=np.array(h['magx'][0,0],float); by=np.array(h['magy'][0,0],float)
                row=wanted[m.name]; ns=nulls(bx,by)
                inv.append({'time':row['time'],'flux':row['reconnected_flux_from_by'],'nulls':ns,'field':m.name,'sha256':actual})
                if .008<=row['reconnected_flux_from_by']<=.052:
                    j=np.gradient(by,1/n,axis=1)-np.gradient(bx,1/n,axis=0);x=(np.arange(n)+.5)/n-.5
                    profiles.append({'time':row['time'],'flux':row['reconnected_flux_from_by'],'y':x.tolist(),'Bx_x0':bx[:,n//2-1:n//2+1].mean(1).tolist(),'Jz_x0':j[:,n//2-1:n//2+1].mean(1).tolist(),'Jz_center':float(j[n//2-1:n//2+1,n//2-1:n//2+1].mean())})
        entry['topology']={'frames':len(inv),'null_count_min':min(len(v['nulls']) for v in inv),'null_count_max':max(len(v['nulls']) for v in inv),'counts':sorted(set((sum(q[2]=='X' for q in v['nulls']),sum(q[2]=='O' for q in v['nulls'])) for v in inv)),'inventory':inv,'limitation':'Bilinear null census on saved cell-center fields; subcell or between-output islands and boundary ghost regions are not certified.'}
        entry['profiles']=profiles
    entry['summary']=r;results.append(entry)
comparisons=[]
for S in [1000,2000]:
    rr=sorted([v for v in results if v['S_eta']==S and v['kind']=='base'],key=lambda v:v['n']); cf=[v for v in results if v['S_eta']==S and v['kind']=='cfl']
    if len(rr)<3:continue
    rates=np.array([v['rate'] for v in rr[-3:]]);f=rr[-1];r=f['summary']; R=f['rate'];changes=np.abs(np.diff(rates)/rates[1:]);mesh=2*float(changes.max());cad=max(abs(np.array(r['cadence_rate_interval'])/R-1));path=abs(r['rate_other_path']/R-1);time=abs(cf[-1]['rate']/R-1) if cf else None
    u=max(.01,mesh+cad+path+time) if time is not None else None
    comparisons.append({'S_eta':S,'rates':rates.tolist(),'successive_relative_mesh_changes':changes.tolist(),'mesh_term':mesh,'cadence_term':float(cad),'path_term':path,'CFL_term':time,'relative_uncertainty':u,'rate':R,'rate_interval':[R*(1-u),R*(1+u)] if u is not None else None,'mesh_gate':bool(changes[-1]<=.05 and changes[-1]<changes[-2]),'spatial_limitation':'Empirical R convergence; evolving J profiles are separately retained and still require independent adequacy assessment.'})
slope=None
if len(comparisons)==2:
 a,b=comparisons;p=np.log(b['rate']/a['rate'])/np.log(2); interval=None
 if a['rate_interval'] and b['rate_interval']:interval=[float(np.log(b['rate_interval'][0]/a['rate_interval'][1])/np.log(2)),float(np.log(b['rate_interval'][1]/a['rate_interval'][0])/np.log(2))]
 slope={'contrast':[1000,2000],'central':float(p),'interval':interval,'status':'exploratory, not claim evidence'}
for v in results:v.pop('summary')
Path('qualification.json').write_text(json.dumps({'cases':results,'uncertainty':comparisons,'slope':slope},indent=2,allow_nan=False)+'\n')
print(json.dumps({'uncertainty':comparisons,'slope':slope,'topology':[{k:v[k] for k in ['experiment','S_eta','n','topology'] if k in v} for v in results if 'topology' in v]},default=str)[:5000])
