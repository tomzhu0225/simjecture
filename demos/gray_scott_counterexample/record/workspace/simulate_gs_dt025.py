import json, time, numpy as np

F=0.072
k=0.062
L=40.0
N=128
dt=0.025
t_end=1000.0
steps=int(round(t_end/dt))

dx=L/N
ky=2*np.pi*np.fft.fftfreq(N, d=dx)
kx=2*np.pi*np.fft.rfftfreq(N, d=dx)
KX,KY=np.meshgrid(kx,ky)
ke2=KX*KX+KY*KY

u0=(1-np.sqrt(1-4*(F+k)**2/F))/2.0
v0=(F+k)/u0

def make_initial():
    x=np.arange(N)*dx; y=np.arange(N)*dx
    X,Y=np.meshgrid(x,y)
    eps=1.0e-3
    phi=(np.cos(2*np.pi*X/L)+np.cos(2*np.pi*Y/L)
         +0.5*np.cos(4*np.pi*X/L)*np.cos(2*np.pi*Y/L)
         +0.25*np.cos(6*np.pi*X/L)*np.cos(4*np.pi*Y/L))/3.0
    return np.fft.rfft2(u0*(1+eps*phi)), np.fft.rfft2(v0*(1+eps*phi))

def rk4(u,v,dt):
    Fu=-u*v*v+F*(1-u); Gv=u*v*v-(F+k)*v
    u2=u+0.5*dt*Fu; v2=v+0.5*dt*Gv
    Fu2=-u2*v2*v2+F*(1-u2); Gv2=u2*v2*v2-(F+k)*v2
    u3=u+0.5*dt*Fu2; v3=v+0.5*dt*Gv2
    Fu3=-u3*v3*v3+F*(1-u3); Gv3=u3*v3*v3-(F+k)*v3
    u4=u+dt*Fu3; v4=v+dt*Gv3
    Fu4=-u4*v4*v4+F*(1-u4); Gv4=u4*v4*v4-(F+k)*v4
    return (u+(dt/6)*(Fu+2*Fu2+2*Fu3+Fu4), v+(dt/6)*(Gv+2*Gv2+2*Gv3+Gv4))

def Pmeas(u): return float(np.mean((u-np.mean(u))**2)/(np.mean(u)**2))

def run(scale):
    Du,Dv=scale,scale/3.0
    expu=np.exp(-Du*ke2*(dt/2)); expv=np.exp(-Dv*ke2*(dt/2))
    U,V=make_initial()
    P0=Pmeas(np.fft.irfft2(U,s=(N,N)))
    rec=[(0.0,P0)]
    t0=time.time()
    for n in range(1,steps+1):
        U*=expu; V*=expv
        u=np.fft.irfft2(U,s=(N,N)); v=np.fft.irfft2(V,s=(N,N))
        u,v=rk4(u,v,dt)
        U=np.fft.rfft2(u); V=np.fft.rfft2(v)
        U*=expu; V*=expv
        if n%40000==0 or n==steps:
            ud=np.fft.irfft2(U,s=(N,N)); P=Pmeas(ud)
            rec.append((n*dt,P))
            print(f'[s={scale}] step {n}/{steps} t={n*dt} P={P:.4e} el={time.time()-t0:.1f}',flush=True)
    uf=np.fft.irfft2(U,s=(N,N)); vf=np.fft.irfft2(V,s=(N,N))
    return Pmeas(uf),rec,uf,vf

out={}
for s in [1.0,10.0]:
    Pf,rec,uf,vf=run(s)
    out[str(int(s))]={'P_final':Pf,'t_final':t_end,'records':rec}
    np.savez_compressed(f'result_s{int(s)}_dt025.npz',u=uf,v=vf,t=np.array([t_end]))
    print('DONE s',s,'Pf',Pf,flush=True)
with open('simulation_results_dt025.json','w') as fh:
    json.dump(out,fh,indent=2)