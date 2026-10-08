"""Fixed central-sheet width and audited FLASH-to-Yee-grid handoff."""
import argparse,json,hashlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from scipy.interpolate import RectBivariateSpline
from prepare_patch import prepare

def main():
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--half',type=float,default=.3);p.add_argument('--nx',type=int,default=384);p.add_argument('--di',type=float,default=.03);p.add_argument('--va',type=float,default=.01);p.add_argument('--source-experiment',required=True);a=p.parse_args()
 f=np.load(a.state);x,z=f['x'],f['z'];dx=x[1]-x[0];dz=z[1]-z[0]
 j=np.gradient(f['bx'],dz,axis=0)-np.gradient(f['bz'],dx,axis=1)
 # Average central two x columns; linear interpolated first half-magnitude crossings.
 profile=j[:,np.argsort(abs(x))[:2]].mean(axis=1)
 peak=float(abs(profile[np.argsort(abs(z))[:2]].mean()))
 crossings=[]
 for side in [-1,1]:
  ii=np.flatnonzero(z*side>0);ii=ii[np.argsort(abs(z[ii]))]
  for k in range(len(ii)-1):
   l,r=ii[k:k+2]
   if abs(profile[l])>=peak/2 and abs(profile[r])<peak/2:
    crossings.append(float(z[l]+(peak/2-abs(profile[l]))/(abs(profile[r])-abs(profile[l]))*(z[r]-z[l])));break
 if len(crossings)!=2:raise ValueError('Missing two central-sheet half-maximum crossings')
 width=(crossings[1]-crossings[0])/2
 m=prepare(SimpleNamespace(state=a.state,output=Path('patch.npz'),center_x=0.,center_z=0.,half_width=a.half,nx=a.nx,nz=a.nx,mass_ratio=25.,density=1e24,skin_depth_code=a.di,temperature_ratio=1.,va_over_c=a.va,electric='ideal'))
 with np.load('patch.npz') as q:
  xc,zc=q['x']/m['scales']['length_m'],q['z']/m['scales']['length_m']; bxc=(q['bx'][:,:-1]+q['bx'][:,1:])/2;bzc=(q['bz'][:-1,:]+q['bz'][1:,:])/2
  sx=RectBivariateSpline(z,x,f['bx'])(zc,xc)*m['scales']['magnetic_T'];sz=RectBivariateSpline(z,x,f['bz'])(zc,xc)*m['scales']['magnetic_T']
  b_error=float(np.sqrt(np.mean((bxc-sx)**2+(bzc-sz)**2)/np.mean(sx*sx+sz*sz)))
  jy=np.gradient(bxc,m['cell_size_m'][1],axis=0)-np.gradient(bzc,m['cell_size_m'][0],axis=1)
  from scipy.constants import mu_0
  mask=(abs(zc[:,None])<.08)&(abs(xc[None,:])<.08)
  current_error=float(np.sqrt(np.mean((jy[mask]/mu_0-q['jy'][mask])**2)/np.mean(q['jy'][mask]**2)))
 m.update(source_experiment=a.source_experiment,width_definition='Half separation of first |J_y|=0.5 |J_y(center)| crossings along Z; J_y=dBx/dZ-dBz/dX, averaged over two source columns closest to X=0, central peak; linear crossing interpolation.',sheet_half_width_code=width,sheet_half_width_source_cells=width/dz,half_width_over_reference_di=width/a.di,half_width_over_local_di=width/a.di*np.sqrt(float(f['rho'][np.ix_(np.argsort(abs(z))[:2],np.argsort(abs(x))[:2])].mean())),crossings_z_code=crossings,magnetic_transfer_rms_relative=b_error,interior_ampere_rms_relative=current_error)
 Path('selection.json').write_text(json.dumps(m,indent=2)+'\n')
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 fig,axs=plt.subplots(1,2,figsize=(11,4))
 axs[0].streamplot(x,z,f['bx'],f['bz'],density=1,color='k',linewidth=.4)
 im=axs[0].pcolormesh(x,z,np.hypot(f['bx'],f['bz']),shading='auto');fig.colorbar(im,ax=axs[0],label='|B| code')
 im=axs[1].pcolormesh(x,z,j,shading='auto',cmap='RdBu_r');fig.colorbar(im,ax=axs[1],label='J_y code')
 for ax in axs:
  ax.add_patch(Rectangle((-a.half,-a.half),2*a.half,2*a.half,fill=False,edgecolor='red'))
  ax.add_patch(Rectangle((-.04,-.015),.08,.03,fill=False,edgecolor='lime'))
  ax.set(xlabel='X=x FLASH',ylabel='Z=y FLASH',aspect='equal')
 fig.tight_layout();fig.savefig('macro_patch.png',dpi=160)
 np.savez_compressed('sheet_profile.npz',z=z,current=profile)
if __name__=='__main__':main()
