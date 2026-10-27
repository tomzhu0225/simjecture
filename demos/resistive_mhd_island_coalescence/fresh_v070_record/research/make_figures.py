from pathlib import Path
import json,tarfile,io
import numpy as np
import h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
rs=[]
for p in Path('../experiments').glob('*/workspace/result.json'):
 r=json.loads(p.read_text());r['_workspace']=p.parent;r['_id']=p.parts[2];rs.append(r)
fig,ax=plt.subplots(1,2,figsize=(10,4))
for n in sorted(set(r['config']['n'] for r in rs)):
 rr=sorted([r for r in rs if r['config']['n']==n and r['config']['cfl']==.4],key=lambda r:r['config']['S_eta'])
 x=[r['config']['S_eta'] for r in rr]; y=[r['metrics']['normalized_flux_slope'] for r in rr]
 ax[0].loglog(x,y,'o-',label=f'{n}² exploratory')
 if len(x)>1: ax[1].plot(np.sqrt(np.array(x[:-1])*x[1:]),np.diff(np.log(y))/np.diff(np.log(x)),'o-',label=f'{n}²')
ax[0].set(xlabel=r'$S_\eta=1/\eta$',ylabel='Flux-window rate R'); ax[0].legend();ax[1].axhspan(-.55,-.45,color='gray',alpha=.3,label='Root band');ax[1].set(xlabel='Geometric midpoint of contrast',ylabel='Contrast log-slope',xscale='log');ax[1].legend();fig.tight_layout();fig.savefig('scaling.png',dpi=170);plt.close(fig)
for S in [1000,2000]:
 candidates=[r for r in rs if r['config']['S_eta']==S and r['config']['cfl']==.4]
 if not candidates:continue
 r=max(candidates,key=lambda r:r['config']['n']); n=r['config']['n'];frows=r['fields'];times=r['timeseries'];x=(np.arange(n)+.5)/n-.5
 fig,ax=plt.subplots(1,3,figsize=(12,4),sharey=True)
 for a,z in zip(ax,[.01,.03,.05]):
  i=min(range(len(times)),key=lambda i:abs(times[i]['reconnected_flux_from_by']-z)); member=frows[i]['path']; p=r['_workspace']/member
  if p.exists(): h=h5py.File(p)
  else:
   with tarfile.open(r['_workspace']/'fields.tar.gz') as tar: b=tar.extractfile(member).read()
   h=h5py.File(io.BytesIO(b))
  with h:
   bx=np.array(h['magx'][0,0],float);by=np.array(h['magy'][0,0],float)
   j=np.gradient(by,1/n,axis=1)-np.gradient(bx,1/n,axis=0)
   az=np.cumsum(by,axis=1)/n-.5*by/n
   # Complete a shared gauge using Bx on the left column.
   az+=(-np.cumsum(bx[:,0])/n+.5*bx[:,0]/n)[:,None]
   im=a.pcolormesh(x,x,j,cmap='RdBu_r',vmin=-100,vmax=100,rasterized=True,shading='auto');a.contour(x,x,az,levels=25,colors='k',linewidths=.45)
   a.set(title=f'ψrec≈{z}, t={times[i]["time"]:.3f}',xlabel='x',aspect='equal');a.set_xlim(-.4,.4);a.set_ylim(-.3,.3)
 ax[0].set_ylabel('y');fig.suptitle(f'Sη={S}, {n}²; current Jz and magnetic-potential contours; exploratory')
 fig.colorbar(im,ax=ax,shrink=.65,label='Jz');fig.savefig(f'fields_S{S}.png',dpi=160);plt.close(fig)
