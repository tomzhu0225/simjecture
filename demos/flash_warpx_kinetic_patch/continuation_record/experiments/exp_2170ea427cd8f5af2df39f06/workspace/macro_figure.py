"""Plot the actual retained FLASH fields and prospectively chosen patch."""
import numpy as np,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
f=np.load('macro512.npz');x=f['x'];z=f['z'];dx=x[1]-x[0];dz=z[1]-z[0]
j=np.gradient(f['bx'],dz,axis=0)-np.gradient(f['bz'],dx,axis=1)
fig,axs=plt.subplots(1,3,figsize=(14,4))
axs[0].streamplot(x,z,f['bx'],f['bz'],density=1,color='k',linewidth=.4)
for ax,v,name in [(axs[0],np.hypot(f['bx'],f['bz']),'|B|'),(axs[1],j,'J_Y'),(axs[2],j,'central J_Y')]:
    im=ax.pcolormesh(x,z,v,shading='auto',cmap='RdBu_r' if ax!=axs[0] else 'viridis');fig.colorbar(im,ax=ax,label=name+' code')
    for half,color in [(.3,'red'),(.45,'orange')]:ax.add_patch(Rectangle((-half,-half),2*half,2*half,fill=False,edgecolor=color,lw=1))
    ax.add_patch(Rectangle((-.04,-.015),.08,.03,fill=False,edgecolor='lime',lw=1.5));ax.set(xlabel='X=x_FLASH',ylabel='Z=y_FLASH',aspect='equal')
axs[2].set_xlim(-.08,.08);axs[2].set_ylim(-.04,.04)
fig.suptitle('Recorded FLASH512, t=0.800111392; red/orange patches, green measurement region')
fig.tight_layout();fig.savefig('macro_patch.png',dpi=170)
