"""Measured FLASH state -> SI patch, preserving source and all transfer residuals."""
import argparse,json,hashlib
from pathlib import Path
from types import SimpleNamespace
import numpy as np,h5py
from scipy.interpolate import RectBivariateSpline
from scipy.constants import c,mu_0,epsilon_0,e
from extract_flash import export
from prepare_patch import prepare
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--experiment',required=True);p.add_argument('--nx',type=int,default=384);p.add_argument('--half',type=float,default=.3);p.add_argument('--skin',type=float);p.add_argument('--label',default='patch');p.add_argument('--no-plot',action='store_true');a=p.parse_args()
manifest=export(a.source,Path('state.npz'));d=np.load('state.npz');x,z=d['x'],d['z'];dx=x[1]-x[0];spl=RectBivariateSpline(z,x,d['bx']);profile=spl(z,[0])[:,0];select=(z>=0)&(z<=.1);bup=float(np.max(abs(profile[select])));slope=float(spl([0],[0],dx=1)[0,0]);width=bup/abs(slope)
skin=a.skin or width
m=prepare(SimpleNamespace(state=Path('state.npz'),output=Path(a.label+'.npz'),nx=a.nx,nz=a.nx,center_x=0.,center_z=0.,half_width=a.half,mass_ratio=25.,density=1e24,skin_depth_code=skin,temperature_ratio=1.,va_over_c=.01,electric='ideal'))
m['source_experiment']=a.experiment;m['source_rotation']=manifest['rotation'];m['sheet']=dict(definition='delta = max |Bx(0,z)| for 0<=z<=0.1 divided by |d Bx(0,z)/dz at z=0|, cubic spline of original cell-centered FLASH fields; reference di uses n0.',delta_code=width,upstream_B_code=bup,central_slope=slope,half_width_source_cells=width/dx,delta_over_reference_di=width/skin,source_reference_di_code=skin)
m['measurement_proposal']=dict(roi_half_code=[.04,.015],window_omegaci=[.4,.9],bins=8,minimum_count=256,minimum_effective_count=512)
q=np.load(a.label+'.npz');l0=m['scales']['length_m'];b0=m['scales']['magnetic_T'];xc,zc=q['x']/l0,q['z']/l0;bx=(q['bx'][:,:-1]+q['bx'][:,1:])/2;bz=(q['bz'][:-1]+q['bz'][1:])/2
orig={k:RectBivariateSpline(z,x,d[k])(zc,xc) for k in ['bx','bz','rho','pressure']}
bnorm=np.sqrt(np.mean(orig['bx']**2+orig['bz']**2));m['transfer_checks']=dict(B_relative_RMS=float(np.sqrt(np.mean((bx/b0-orig['bx'])**2+(bz/b0-orig['bz'])**2))/bnorm),density_relative_RMS=float(np.linalg.norm(q['n']/1e24-orig['rho'])/np.linalg.norm(orig['rho'])),pressure_relative_RMS=float(np.linalg.norm(q['p']/(m['scales']['mass_density_kg_m3']*m['scales']['velocity_m_s']**2)-orig['pressure'])/np.linalg.norm(orig['pressure'])))
# Compare spline current with the curl of receiving Yee fields, cell centered from interior nodes.
hx,hz=m['cell_size_m'];jnode=(np.diff(q['bx'],axis=0)/hz)[:,1:-1]-(np.diff(q['bz'],axis=1)/hx)[1:-1,:];jcenter=(jnode[:-1,:-1]+jnode[1:,:-1]+jnode[:-1,1:]+jnode[1:,1:])/4/mu_0
m['transfer_checks']['current_discrete_relative_RMS']=float(np.linalg.norm(jcenter-q['jy'][1:-1,1:-1])/np.linalg.norm(q['jy'][1:-1,1:-1]))
m['resolution']=dict(dx_over_de=hx/(m['scales']['ion_skin_depth_m']/5),dx_over_min_debye=hx/np.min(np.sqrt(epsilon_0*q['te']/(q['n']*e**2))),local_width_over_di_at_center=width/skin*np.sqrt(float(RectBivariateSpline(z,x,d['rho'])([0],[0])[0,0])))
Path(a.label+'.json').write_text(json.dumps(m,indent=2,allow_nan=False)+'\n');Path('result.json').write_text(json.dumps(m,indent=2,allow_nan=False)+'\n')
if not a.no_plot:
 import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 fig,axs=plt.subplots(1,3,figsize=(13,4));j=np.gradient(d['bx'],z,axis=0)-np.gradient(d['bz'],x,axis=1)
 for ax,data,title in zip(axs,[d['bx'],j,d['pressure']],['FLASH Bx','FLASH curl B (WarpX y)','FLASH total scalar pressure']):
  im=ax.imshow(data,origin='lower',extent=[x[0],x[-1],z[0],z[-1]],cmap='RdBu_r');ax.add_patch(Rectangle((-a.half,-a.half),2*a.half,2*a.half,fill=False,color='k'));ax.add_patch(Rectangle((-.04,-.015),.08,.03,fill=False,color='lime'));ax.set(title=title,xlabel='FLASH x = WarpX X',ylabel='FLASH y = WarpX Z');fig.colorbar(im,ax=ax)
 fig.suptitle('Fresh macro source t='+str(manifest['source_time_code'])+'; black patch, green measurement region');fig.tight_layout();fig.savefig('macro_patch.png',dpi=160)
np.savez_compressed('source_profiles.npz',x=x,z=z,bx=d['bx'],bz=d['bz'],current=j,central_Bx=profile)
print(json.dumps(dict(sheet=m['sheet'],resolution=m['resolution'],transfer=m['transfer_checks'])))
