"""Periodic 1D full ideal MHD, smooth unlimited linear reconstruction + LLF flux, SSPRK2.
Units: mu0=rho0=|B0|=L=1; gamma=5/3. Bx constant exactly.
"""
import numpy as np
import json, math, hashlib, argparse, time
from pathlib import Path
G=5/3
BASE=825307220

def rhs(u,bx,dx):
    slope=(np.roll(u,-1,axis=1)-np.roll(u,1,axis=1))/2
    l=u+slope/2; r=np.roll(u-slope/2,-1,axis=1)
    def flux(q):
        rho=q[0]; v=q[1:4]/rho; by,bz=q[5:7]
        b2=bx*bx+by*by+bz*bz
        p=(G-1)*(q[4]-.5*rho*np.sum(v*v,axis=0)-.5*b2)
        if np.min(p)<=0 or np.min(rho)<=0: raise ValueError('Nonpositive primitive')
        pt=p+.5*b2; vb=v[0]*bx+v[1]*by+v[2]*bz
        f=np.empty_like(q); f[0]=q[1]
        f[1]=q[1]*v[0]+pt-bx*bx
        f[2]=q[2]*v[0]-bx*by; f[3]=q[3]*v[0]-bx*bz
        f[4]=(q[4]+pt)*v[0]-bx*vb
        f[5]=by*v[0]-bx*v[1]; f[6]=bz*v[0]-bx*v[2]
        a2=G*p/rho; va2=b2/rho
        cf=np.sqrt(.5*(a2+va2+np.sqrt(np.maximum((a2+va2)**2-4*a2*bx*bx/rho,0))))
        return f,np.abs(v[0])+cf
    fl,al=flux(l); fr,ar=flux(r)
    f=.5*(fl+fr)-.5*np.maximum(al,ar)*(r-l)
    return -(f-np.roll(f,1,axis=1))/dx

def simulate(n,cfl,angle,beta,amp,periods,label,arrays):
    signature=json.dumps([BASE,angle,beta,amp],sort_keys=True)
    seed=int(hashlib.sha256(signature.encode()).hexdigest()[:8],16)
    phase=np.random.default_rng(seed).uniform(-np.pi,np.pi)
    bx=np.cos(np.deg2rad(angle)); by=np.sin(np.deg2rad(angle)); p=beta/2
    c=bx; T=1/abs(c); end=periods*T; dx=1/n; x=(np.arange(n)+.5)*dx
    b=amp*np.sin(2*np.pi*x+phase)*np.sinc(1/n)
    u=np.zeros((7,n)); u[0]=1; u[3]=-b; u[5]=by; u[6]=b
    u[4]=p/(G-1)+.5*(1+b*b)+.5*b*b
    if label=='circular':
        transverse=amp*np.cos(2*np.pi*x+phase)*np.sinc(1/n)
        u[2]=-transverse; u[5]=transverse
        u[4]=p/(G-1)+.5*(bx*bx+transverse*transverse+b*b)+.5*(transverse*transverse+b*b)
    initial=u.copy(); totals=u.sum(axis=1)*dx
    cf=np.sqrt(.5*(G*p+1+np.sqrt((G*p+1)**2-4*G*p*bx*bx)))
    steps=math.ceil(end/(cfl*dx/cf)); dt=end/steps
    mode=np.exp(-2j*np.pi*x)
    times=[]; coeff=[]; sample=max(1,steps//120)
    def record(t): times.append(t); coeff.append(np.sum(u[6]*mode)*2/n)
    record(0)
    for it in range(steps):
        v=u+dt*rhs(u,bx,dx); u=.5*u+.5*(v+dt*rhs(v,bx,dx))
        if (it+1)%sample==0 or it==steps-1:record((it+1)*dt)
    coeff=np.array(coeff); times=np.array(times)
    ph=np.unwrap(np.angle(coeff)); fit=np.polyfit(times,ph,1)
    speed=-fit[0]/(2*np.pi); residual=ph-np.polyval(fit,times)
    exact=amp*np.sin(2*np.pi*(x-c*end)+phase)*np.sinc(1/n)
    err=float(np.sqrt(np.mean((u[6]-exact)**2))/(amp/np.sqrt(2)))
    pressure=(G-1)*(u[4]-.5*np.sum(u[1:4]**2,axis=0)/u[0]-.5*(bx*bx+u[5]**2+u[6]**2))
    conservation=u.sum(axis=1)*dx-totals
    arrays[label+'_initial']=initial;arrays[label+'_final']=u;arrays[label+'_times']=times
    arrays[label+'_mode']=np.stack([coeff.real,coeff.imag])
    result=dict(polarization='circular exact nonlinear' if label=='circular' else 'linear transverse z',label=label,n=n,cfl=cfl,angle_deg=angle,beta=beta,amplitude=amp,seed=seed,initial_phase=phase,dt=dt,steps=steps,end_time=end,periods=periods,theory_speed=c,measured_speed=float(speed),relative_speed_error=float(abs(speed/c-1)),normalized_L2_error=err,amplitude_ratio=float(abs(coeff[-1]/coeff[0])),phase_fit_max_residual=float(max(abs(residual))),conserved_residuals=conservation.tolist(),max_conservation_residual=float(max(abs(conservation))),min_density=float(u[0].min()),min_pressure=float(pressure.min()),density_max_deviation=float(max(abs(u[0]-1))),divB_max=0.0,floor_corrections=0,source_corrections=0)
    print(json.dumps(result),flush=True)
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--suite',default='pilot');args=ap.parse_args()
    arr={}; cases=[]; start=time.time()
    if args.suite=='pilot':
        configs=[(n,.25,43.9063292,1.25212856,1e-4,.7,'space_'+str(n)) for n in [32,64,128,256]]
    else:
        configs=[]
        for angle,beta in [(0,.05),(60,10),(43.9063292,1.25212856)]:
            for n in [32,64,128,256]: configs.append((n,.12,angle,beta,1e-4,.7,f'space_{angle}_{n}'))
        for cfl in [.6,.3,.15,.075,.009375]: configs.append((64,cfl,43.9063292,1.25212856,1e-4,.7,f'time_{cfl}'))
        for amp in [0.05291726,.005291726,.0005291726]:configs.append((256,.2,43.9063292,1.25212856,amp,.7,f'amp_{amp}'))
        configs.append((256,.12,23.0,.7,1e-4,1.3,'holdout'))
        configs.append((256,.12,0.0,.05,.05291726,.7,'circular'))
    for conf in configs:
        cases.append(simulate(*conf,arr))
        Path('result.json').write_text(json.dumps({'suite':args.suite,'cases':cases,'complete':False},indent=2,allow_nan=False))
    groups={}
    for c in cases:
        if c['label'].startswith('space_'):groups.setdefault(str(c['angle_deg']),[]).append(c)
    orders={}
    for key,cs in groups.items():
        orders[key]=[math.log(a['normalized_L2_error']/b['normalized_L2_error'],2) for a,b in zip(cs[:-1],cs[1:])]
    temporal=[]
    tc=[c for c in cases if c['label'].startswith('time_')]
    if tc:
        ref=arr[tc[-1]['label']+'_final'][6]
        for c in tc[:-1]:
            e=float(np.sqrt(np.mean((arr[c['label']+'_final'][6]-ref)**2))/(c['amplitude']/np.sqrt(2)))
            temporal.append({'cfl':c['cfl'],'dt':c['dt'],'error_vs_reference':e})
    tout=[math.log(a['error_vs_reference']/b['error_vs_reference'])/math.log(a['dt']/b['dt']) for a,b in zip(temporal[:-1],temporal[1:])]
    np.savez_compressed('raw.npz',**arr)
    result={'suite':args.suite,'complete':True,'model':'full conservative 1D ideal MHD, mu0=1, gamma=5/3','boundary':'periodic, constant Bx; wavevector along x and background B inclined in xy plane','scheme':'unlimited centered MUSCL reconstruction of conserved state, local Lax Friedrichs flux, SSPRK2; no floors or sources','units':'rho0=B0=L=mu0=1; velocity in B0/sqrt(mu0*rho0); time in L sqrt(mu0*rho0)/B0','cases':cases,'spatial_orders':orders,'temporal_comparison':temporal,'temporal_orders':tout,'wall_seconds':time.time()-start,'limitations':['1D spatial dependence with three vector components; not multidimensional oblique mesh convergence','linear theory prediction only asymptotic in amplitude; finite-amplitude case is a challenge control','divB vanishes structurally because Bx constant; does not test multidimensional divergence control']}
    Path('result.json').write_text(json.dumps(result,indent=2,allow_nan=False))
if __name__=='__main__':main()
