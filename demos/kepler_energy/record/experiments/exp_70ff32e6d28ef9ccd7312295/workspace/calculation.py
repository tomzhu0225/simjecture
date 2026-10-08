import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import newton
from scipy.integrate import solve_ivp

MU=1.0; A=1.0; PERIOD=2*np.pi; TEND=20*PERIOD
eccs=[0.0,0.3,0.6]; ns=[64,128,256,512]

def exact_orbit(t,e):
    M=np.asarray(t)*1.0
    E=M.copy()
    for _ in range(30):
        d=(E-e*np.sin(E)-M)/(1-e*np.cos(E)); E-=d
        if np.max(np.abs(d))<2e-15: break
    resid=np.max(np.abs(E-e*np.sin(E)-M))
    x=np.cos(E)-e; y=np.sqrt(1-e*e)*np.sin(E)
    return np.stack((x,y),axis=-1),resid

def accel(q): return -q/np.linalg.norm(q,axis=-1)[...,None]**3

rows=[]; plot_cases=[]; raw={}
for e in eccs:
 for n in ns:
    dt=PERIOD/n; steps=int(round(TEND/dt)); t=np.arange(steps+1)*dt
    q=np.empty((steps+1,2)); v=np.empty_like(q)
    q[0]=[1-e,0]; v[0]=[0,np.sqrt((1+e)/(1-e))]
    # Explicit kick-drift-kick (velocity Verlet) map.
    for i in range(steps):
        vh=v[i]+0.5*dt*accel(q[i]); q[i+1]=q[i]+dt*vh
        v[i+1]=vh+0.5*dt*accel(q[i+1])
    ref,res=exact_orbit(t,e)
    E=0.5*np.sum(v*v,axis=1)-1/np.linalg.norm(q,axis=1)
    E0=0.5*np.sum(v[0]**2)-1/np.linalg.norm(q[0])
    pos=np.linalg.norm(q-ref,axis=1)
    ph=np.unwrap(np.arctan2(q[:,1],q[:,0])-np.arctan2(ref[:,1],ref[:,0]))
    # Independent adaptive integration check for the most discriminating case.
    ivp_err=None
    if e==0.6 and n==128:
        def rhs(_,z):
            qq=z[:2]; vv=z[2:]; return np.r_[vv,accel(qq)]
        sol=solve_ivp(rhs,(0,TEND),np.r_[q[0],v[0]],method='DOP853',rtol=2e-13,atol=2e-14,t_eval=t)
        ivp_err=float(np.max(np.linalg.norm(sol.y[:2].T-ref,axis=1)))
        kdk_vs_ivp=float(np.max(np.linalg.norm(q-sol.y[:2].T,axis=1)))
    else: kdk_vs_ivp=None
    row={'e':e,'steps_per_period':n,'dt':dt,'sample_count':len(t),'max_rel_energy_error':float(np.max(np.abs((E-E0)/abs(E0)))),
         'max_position_error_a':float(np.max(pos)),'max_abs_phase_error_rad':float(np.max(np.abs(ph))),
         'kepler_max_residual':float(res),'initial_position_error':float(pos[0]),'initial_velocity_error':0.0,
         'period_consistency_error':float(np.linalg.norm(exact_orbit(np.array([PERIOD]),e)[0][0]-exact_orbit(np.array([0.]),e)[0][0])),
         'independent_ivp_max_position_error':ivp_err,'kdk_vs_ivp_max_position_difference':kdk_vs_ivp}
    rows.append(row)
    key=f'e{e:g}_n{n}'
    raw[key+'_t']=t; raw[key+'_q_kdk']=q; raw[key+'_q_exact']=ref; raw[key+'_rel_energy']=(E-E0)/abs(E0); raw[key+'_phase_error']=ph
    if (e,n) in [(0.3,128),(0.6,128),(0.6,256)]: plot_cases.append((e,n,t,q,ref,(E-E0)/abs(E0),pos,ph))

with open('result.json','w') as f: json.dump({'units':{'GM':1,'a':1,'period':PERIOD},'window_periods':20,'method':'fixed-step kick-drift-kick leapfrog; half kick, full drift, half kick','energy_normalization':'|E(t)-E(0)|/|E(0)|, E(0)=-1/2','position_normalization':'Euclidean position error divided by a=1','cases':rows},f,indent=2)
np.savez_compressed('trajectories.npz',**raw)
fig,axs=plt.subplots(2,2,figsize=(12,8))
for e,n,t,q,ref,en,pos,ph in plot_cases:
    label=f'e={e}, N={n}'
    axs[0,0].plot(q[:,0],q[:,1],label=label); axs[0,0].plot(ref[:,0],ref[:,1],':',alpha=.8)
    axs[0,1].plot(t/PERIOD,pos,label=label)
    axs[1,0].plot(t/PERIOD,en,label=label)
    axs[1,1].plot(t/PERIOD,ph,label=label)
axs[0,0].set(title='Orbit: KDK solid, exact Kepler dotted',xlabel='x/a',ylabel='y/a',aspect='equal')
axs[0,1].set(title='Position error',xlabel='time / period',ylabel='|qKDK-qexact|/a'); axs[0,1].axhline(.01,color='k',ls='--')
axs[1,0].set(title='Relative energy error',xlabel='time / period',ylabel='(E-E0)/|E0|'); axs[1,0].axhline(.001,color='k',ls='--')
axs[1,1].set(title='Unwrapped phase error',xlabel='time / period',ylabel='phase difference (rad)')
for ax in axs.flat: ax.grid(alpha=.25); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig('errors.png',dpi=150)
