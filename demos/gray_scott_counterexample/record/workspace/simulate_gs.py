import sys, time, json
import numpy as np

F=0.072
k=0.062
L=40.0
N=128
dt=0.05
t_end=1000.0
steps=int(round(t_end/dt))

dx=L/N
ky=2*np.pi*np.fft.fftfreq(N, d=dx)
kx=2*np.pi*np.fft.rfftfreq(N, d=dx)
KX,KY=np.meshgrid(kx,ky)
ke2=KX*KX+KY*KY

# stable lower homogeneous steady state
u0=(1-np.sqrt(1-4*(F+k)**2/F))/2.0
v0=(F+k)/u0
print('u0,v0',u0,v0, flush=True)

def make_initial(scale):
    x=np.arange(N)*dx
    y=np.arange(N)*dx
    X,Y=np.meshgrid(x,y)
    eps=1.0e-3
    phi=(np.cos(2*np.pi*X/L)+np.cos(2*np.pi*Y/L)
         +0.5*np.cos(4*np.pi*X/L)*np.cos(2*np.pi*Y/L)
         +0.25*np.cos(6*np.pi*X/L)*np.cos(4*np.pi*Y/L))/3.0
    u=u0*(1+eps*phi)
    v=v0*(1+eps*phi)
    U=np.fft.rfft2(u)
    V=np.fft.rfft2(v)
    return u,v,U,V

def reaction_rk4(u,v,dt):
    # du/dt = -u v^2 + F(1-u)
    # dv/dt =  u v^2 - (F+k)v
    Fu = -u*v*v + F*(1.0-u)
    Gv = u*v*v - (F+k)*v
    u2 = u + 0.5*dt*Fu
    v2 = v + 0.5*dt*Gv
    Fu2 = -u2*v2*v2 + F*(1.0-u2)
    Gv2 = u2*v2*v2 - (F+k)*v2
    u3 = u + 0.5*dt*Fu2
    v3 = v + 0.5*dt*Gv2
    Fu3 = -u3*v3*v3 + F*(1.0-u3)
    Gv3 = u3*v3*v3 - (F+k)*v3
    u4 = u + dt*Fu3
    v4 = v + dt*Gv3
    Fu4 = -u4*v4*v4 + F*(1.0-u4)
    Gv4 = u4*v4*v4 - (F+k)*v4
    u_new = u + (dt/6.0)*(Fu + 2*Fu2 + 2*Fu3 + Fu4)
    v_new = v + (dt/6.0)*(Gv + 2*Gv2 + 2*Gv3 + Gv4)
    return u_new, v_new

def pattern_measure(u):
    return float(np.mean((u-np.mean(u))**2)/(np.mean(u)**2))

def run(scale, max_steps, out_prefix):
    Du=scale
    Dv=scale/3.0
    expu=np.exp(-Du*ke2*(dt/2.0))
    expv=np.exp(-Dv*ke2*(dt/2.0))
    u0_init,v0_init,U,V=make_initial(scale)
    P0=pattern_measure(u0_init)
    records=[{'t':0.0,'P':P0}]
    t0=time.time()
    for n in range(1,max_steps+1):
        U *= expu
        V *= expv
        u = np.fft.irfft2(U, s=(N,N))
        v = np.fft.irfft2(V, s=(N,N))
        u,v = reaction_rk4(u,v,dt)
        U = np.fft.rfft2(u)
        V = np.fft.rfft2(v)
        U *= expu
        V *= expv
        if n % 500 == 0 or n==max_steps:
            # diagnostic physical state
            ud = np.fft.irfft2(U, s=(N,N))
            P=pattern_measure(ud)
            el=time.time()-t0
            if n % 5000 == 0 or n==max_steps:
                print(f'[s={scale}] step {n}/{max_steps} t={n*dt:.1f} P={P:.3e} el={el:.1f}s', flush=True)
            if (n*dt) % 100.0 < 1e-9 or n % 2000 == 0:
                records.append({'t':float(n*dt),'P':P})
        if not np.isfinite(P) if False else False:
            pass
    # final physical fields
    uf=np.fft.irfft2(U, s=(N,N))
    vf=np.fft.irfft2(V, s=(N,N))
    Pf=pattern_measure(uf)
    if records[-1]['t'] < t_end-1e-9:
        records.append({'t':float(max_steps*dt),'P':Pf})
    np.savez_compressed(out_prefix+'.npz', u=uf, v=vf, t=np.array([max_steps*dt]), records=np.array(records,dtype=object))
    return Pf, records, uf, vf

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'full'
    max_steps = 200 if mode=='bench' else steps
    print('mode',mode,'max_steps',max_steps,'dt',dt,'tend',max_steps*dt, flush=True)
    results={}
    for s in [1.0,10.0]:
        Pf,records,uf,vf=run(s,max_steps,f'result_s{int(s)}')
        results[str(int(s))]={'P_final':Pf,'t_final':float(max_steps*dt),'records':records}
        print('DONE s',s,'P_final',Pf, flush=True)
    with open('simulation_results.json','w') as fh:
        json.dump(results,fh,indent=2)