import numpy as np
import json

F=0.055
k=0.062
Du0=1.0
Dv0=0.5
L=40.0

def gs_hss(F,k):
    disc=1.0-4.0*(F+k)**2/F
    sq=np.sqrt(disc)
    out=[]
    for u in [(1+sq)/2,(1-sq)/2]:
        if u>0:
            v=(F+k)/u
            if v>0: out.append((u,v))
    return out

def lam_disp(F,k,u,v,Du,Dv,q):
    fu=-F-v*v
    fv=-2*u*v
    gu=v*v
    gv=2*u*v-(F+k)
    A=fu-Du*q*q
    B=gv-Dv*q*q
    tr=A+B
    det=A*B-fv*gu
    return tr/2+np.sqrt(max(tr*tr-4*det,0))/2

def band_edges(F,k,u,v,Du,Dv,qmax=10,N=200001):
    q=np.linspace(0,qmax,N)
    lam=np.array([lam_disp(F,k,u,v,Du,Dv,qq) for qq in q])
    pos=q[lam>1e-10]
    if len(pos)==0: return None
    return float(pos.min()),float(pos.max())

u,v=gs_hss(F,k)[1]
print('F,k,u,v',F,k,u,v)

# exact base band
be=band_edges(F,k,u,v,Du0,Dv0,qmax=10)
print('base band q',be)

print('\nAbsolute scale s, Du/Dv fixed =',Du0/Dv0,', L=',L)
results=[]
for s in [0.01,0.05,0.1,0.2,0.257,0.5,1.0,2.0,10.0,100.0]:
    Du=s*Du0; Dv=s*Dv0
    be_s=band_edges(F,k,u,v,Du,Dv,qmax=10*max(np.sqrt(s),0.1)+0.5)
    if be_s is None:
        results.append({'s':s,'band':None,'modes':[]})
        print(f's={s:8g}: no unstable band')
        continue
    qlo,qhi=be_s
    # admissible radial modes for L periodic
    nmax=int(np.ceil(qhi*L/(2*np.pi)))+5
    inside=[]
    for n in range(1,nmax+1):
        qn=2*np.pi*n/L
        if qn>=qlo-1e-8 and qn<=qhi+1e-8:
            cnt=0
            lim=n
            for nx in range(-lim,lim+1):
                ny2=n*n-nx*nx
                ny=int(round(np.sqrt(ny2)))
                if ny*ny==ny2:
                    cnt += 1 if (nx==0 and ny==0) else (2 if nx==0 or ny==0 else 4)
            inside.append((n,float(qn),cnt,float(lam_disp(F,k,u,v,Du,Dv,qn))))
    results.append({'s':s,'band':[qlo,qhi],'modes':inside})
    print(f's={s:8g}: band q=({qlo:.6f},{qhi:.6f}), modes: {[(n,round(q,4),c,round(lam_,4)) for n,q,c,lam_ in inside]}')

with open('mode_analysis_results.json','w') as f:
    json.dump({'F':F,'k':k,'u_branch':1,'u':u,'v':v,'Du0':Du0,'Dv0':Dv0,'L':L,'results':results},f,indent=2)