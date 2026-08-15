import json, time, numpy as np

F=0.072
k=0.062
L=40.0
N=128
u0=(1-np.sqrt(1-4*(F+k)**2/F))/2.0
v0=(F+k)/u0

dx=L/N
ky=2*np.pi*np.fft.fftfreq(N, d=dx)
kx=2*np.pi*np.fft.rfftfreq(N, d=dx)
KX,KY=np.meshgrid(kx,ky)
ke2=KX*KX+KY*KY

def make_initial(eps=1e-3):
    x=np.arange(N)*dx; y=np.arange(N)*dx
    X,Y=np.meshgrid(x,y)
    # deterministic perturbation with different phases from child experiment
    phi=0.7*np.cos(2*np.pi*X/L+0.3)*np.cos(2*np.pi*Y/L+0.7)
    phi+=0.5*np.sin(4*np.pi*X/L)*np.cos(2*np.pi*Y/L+0.4)
    phi+=0.25*np.cos(6*np.pi*X/L+1.1)*np.sin(4*np.pi*Y/L+0.2)
    phi/=np.max(np.abs(phi))
    u=u0*(1+eps*phi)
    v=v0*(1+eps*phi)
    return np.fft.rfft2(u), np.fft.rfft2(v)

def rk4(u,v,dt):
    Fu=-u*v*v+F*(1-u); Gv=u*v*v-(F+k)*v
    u2=u+0.5*dt*Fu; v2=v+0.5*dt*Gv
    Fu2=-u2*v2*v2+F*(1-u2); Gv2=u2*v2*v2-(F+k)*v2
    u3=u+0.5*dt*Fu2; v3=v+0.5*dt*Gv2
    Fu3=-u3*v3*v3+F*(1-u3); Gv3=u3*v3*v3-(F+k)*v3
    u4=u+dt*Fu3; v4=v+dt*Gv3
    Fu4=-u4*v4*v4+F*(1-u4); Gv4=u4*v4*v4-(F+k)*v4
    return (u+(dt/6)*(Fu+2*Fu2+2*Fu3+Fu4), v+(dt/6)*(Gv+2*Gv2+2*Gv3+Gv4))

def Pmeas(u):
    return float(np.mean((u-np.mean(u))**2)/(np.mean(u)**2))

def run(scale, dt, t_end=1000.0):
    steps=int(round(t_end/dt))
    Du,Dv=scale,scale/3.0
    expu=np.exp(-Du*ke2*(dt/2)); expv=np.exp(-Dv*ke2*(dt/2))
    U,V=make_initial()
    P0=Pmeas(np.fft.irfft2(U,s=(N,N)))
    rec=[(0.0,P0)]
    for n in range(1,steps+1):
        U*=expu; V*=expv
        u=np.fft.irfft2(U,s=(N,N)); v=np.fft.irfft2(V,s=(N,N))
        u,v=rk4(u,v,dt)
        U=np.fft.rfft2(u); V=np.fft.rfft2(v)
        U*=expu; V*=expv
        if n==steps or n%5000==0:
            pf=Pmeas(np.fft.irfft2(U,s=(N,N)))
            rec.append((n*dt,pf))
            if n==steps:
                print(f's={scale} dt={dt}: P_final={pf:.6e}',flush=True)
    uf=np.fft.irfft2(U,s=(N,N)); vf=np.fft.irfft2(V,s=(N,N))
    return Pmeas(uf), rec, uf, vf

out={'contract':'claim_root:v1','F':F,'k':k,'ratio_Du_Dv':3.0,'L':L,'N':N,'t_end':1000.0,'perturbation_eps':1e-3}
for dt in [0.05,0.025]:
    key=f'dt_{dt}'.replace('.','p')
    out[key]={}
    for s in [1.0,10.0]:
        Pf,rec,uf,vf=run(s,dt)
        out[key][str(int(s))]={'P_final':Pf,'records':rec}
        np.savez_compressed(f'root_s{int(s)}_dt{key[3:]}.npz',u=uf,v=vf)
with open('root_pattern_results.json','w') as fh:
    json.dump(out,fh,indent=2)
print('WROTE root_pattern_results.json')