from pathlib import Path
import json,io,tarfile,hashlib
import numpy as np,h5py
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator,FixedFormatter,NullFormatter
root=Path('../experiments');contrast=json.loads(Path('contrast.json').read_text());ids={1000:'exp_40aac93038caa57671014925',2000:'exp_755dffd11e2a3f05a6b86b49'}
mapids=['exp_a2d9039a3b1d3ba9ec78f86c','exp_349433d01686c1d23c0186c8','exp_ff929c68f5acb2eafb2f340b','exp_42cf28ee0c7c41a2f8d923be','exp_b2df128c1c1ecc1d990f7dc5']
rr=[json.loads((root/e/'workspace/result.json').read_text()) for e in mapids];xs=np.array([r['config']['S_eta'] for r in rr]);ys=np.array([r['metrics']['normalized_flux_slope'] for r in rr]);fig,ax=plt.subplots(1,2,figsize=(10.5,4.2));ax[0].loglog(xs,ys,'o--',color='.65',label='128² exploratory map')
cs=contrast['cases'];x=[c['S_eta'] for c in cs];y=[c['rate'] for c in cs];err=[c['rate']*c['relative_uncertainty'] for c in cs];ax[0].errorbar(x,y,yerr=err,fmt='o-',color='navy',capsize=4,label='384² fresh evidence + numerical envelope');ax[0].set(xlabel=r'$S_\eta=1/\eta$',ylabel='Flux-window rate R');ax[0].legend(fontsize=8)
ps=np.diff(np.log(ys))/np.diff(np.log(xs));ax[1].semilogx(np.sqrt(xs[:-1]*xs[1:]),ps,'o--',color='.65',label='Exploratory adjacent contrasts');p=contrast['p_eff'];lo,hi=contrast['numerical_interval'];ax[1].axhspan(-.55,-.45,color='gray',alpha=.25,label='Original band');ax[1].errorbar([np.sqrt(2)*1000],[p],yerr=[[p-lo],[hi-p]],fmt='o',color='navy',capsize=5,label='Accepted fresh counterexample');ax[1].set(xlabel='Geometric midpoint of contrast',ylabel='Contrast log-slope',ylim=(-.6,-.25));ax[1].legend(fontsize=8);ax[0].xaxis.set_major_locator(FixedLocator([250,500,1000,2000,4000]));ax[0].xaxis.set_major_formatter(FixedFormatter(['250','500','1000','2000','4000']));ax[0].xaxis.set_minor_formatter(NullFormatter());ax[1].xaxis.set_major_locator(FixedLocator(np.sqrt(xs[:-1]*xs[1:])));ax[1].xaxis.set_major_formatter(FixedFormatter(['354','707','1414','2828']));ax[1].xaxis.set_minor_formatter(NullFormatter());fig.tight_layout();fig.savefig('scaling.png',dpi=200);plt.close(fig)
provenance=[]
for S,eid in ids.items():
 w=root/eid/'workspace';r=json.loads((w/'result.json').read_text());n=r['config']['n'];xx=(np.arange(n)+.5)/n-.5;ts=r['timeseries'];indices=[min(range(len(ts)),key=lambda i:abs(ts[i]['reconnected_flux_from_by']-z)) for z in [.01,.03,.05]];wanted={r['fields'][i]['path']:i for i in indices};fields={}
 with tarfile.open(w/'fields.tar.gz','r|gz') as tar:
  for m in tar:
   if m.name not in wanted:continue
   i=wanted[m.name];b=tar.extractfile(m).read();assert hashlib.sha256(b).hexdigest()==r['fields'][i]['sha256']
   with h5py.File(io.BytesIO(b)) as h:fields[i]=(np.array(h['magx'][0,0],float),np.array(h['magy'][0,0],float))
 fig,ax=plt.subplots(1,3,figsize=(12,4),sharey=True)
 for a,i,z in zip(ax,indices,[.01,.03,.05]):
  bx,by=fields[i];J=np.gradient(by,1/n,axis=1)-np.gradient(bx,1/n,axis=0);A=np.cumsum(by,axis=1)/n-.5*by/n;A+=(-np.cumsum(bx[:,0])/n+.5*bx[:,0]/n)[:,None];im=a.pcolormesh(xx,xx,J,cmap='RdBu_r',vmin=-100,vmax=100,shading='auto',rasterized=True);a.contour(xx,xx,A,levels=30,colors='k',linewidths=.4);a.set(xlabel='x',title=f'ψrec≈{z}, t={ts[i]["time"]:.3f}',aspect='equal',xlim=(-.5,.5),ylim=(-.5,.5));provenance.append({'figure':f'fields_S{S}.png','experiment':eid,'index':i,'field':r['fields'][i],'time':ts[i]['time']})
 ax[0].set_ylabel('y');fig.suptitle(f'Sη={S}, 384² fresh evidence: full-domain current Jz and magnetic contours');fig.colorbar(im,ax=ax,shrink=.7,label='Jz');fig.savefig(f'fields_S{S}.png',dpi=180);plt.close(fig)
Path('figure_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
