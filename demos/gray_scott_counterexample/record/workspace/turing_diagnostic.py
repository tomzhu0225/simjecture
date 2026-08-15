import numpy as np

def gs_hss(F,k):
    disc = 1.0 - 4.0*(F+k)**2/F
    if disc < 0:
        return []
    sq = np.sqrt(disc)
    out=[]
    for u in [(1+sq)/2,(1-sq)/2]:
        if u<=0: continue
        v=(F+k)/u
        if v>0: out.append((u,v))
    return out

def jac_entries(F,k,u,v):
    fu = -F - v*v
    fv = -2*u*v
    gu = v*v
    gv = 2*u*v - (F+k)
    return fu,fv,gu,gv

def lam_disp(F,k,u,v,Du,Dv,q):
    fu,fv,gu,gv = jac_entries(F,k,u,v)
    A = fu - Du*q*q
    B = gv - Dv*q*q
    tr = A+B
    det = A*B - fv*gu
    disc = tr*tr - 4*det
    return tr/2 + np.sqrt(np.maximum(disc,0))/2

def find_band(F,k,u,v,Du,Dv,qmax=2000,N=20001):
    q=np.linspace(0,qmax,N)
    lam=np.array([lam_disp(F,k,u,v,Du,Dv,qq) for qq in q])
    pos=q[lam>1e-10]
    return q,lam,pos

# 1. Scan for stable HSS with positive-q Turing band
print('=== Parameter scan: stable HSS + positive-q band ===')
found=[]
for F in np.linspace(0.01,0.10,37):
    for k in np.linspace(0.002,0.07,35):
        hss=gs_hss(F,k)
        for u,v in hss:
            fu,fv,gu,gv=jac_entries(F,k,u,v)
            tr=fu+gv
            det=fu*gv-fv*gu
            if tr > -1e-8 or det < 1e-8:
                continue
            Du,Dv=1.0,0.5
            q=np.linspace(0,100,4001)
            lam=np.array([lam_disp(F,k,u,v,Du,Dv,qq) for qq in q])
            pos=q[(q>1e-6)&(lam>1e-10)]
            if len(pos)>0:
                found.append((F,k,u,v,pos.min(),pos.max()))
                break

print('total found',len(found))
for row in found[:12]:
    F,k,u,v,qmin,qmax=row
    print(f'F={F:.4f} k={k:.4f} u={u:.4f} v={v:.4f} band q=({qmin:.4f},{qmax:.4f})')

# 2. Exact scale invariance for several found parameter sets
print('\n=== Scale invariance of the unstable band under D -> sD ===')
for (F,k,u,v,qmin,qmax) in found[:6]:
    Du,Dv=1.0,0.5
    q,lam,pos=find_band(F,k,u,v,Du,Dv,qmax=300.0,N=30001)
    if len(pos)==0: continue
    print(f'F={F:.5f},k={k:.5f},u={u:.5f},v={v:.5f}: base band q=({pos.min():.6f},{pos.max():.6f})')
    for s in [1e-4,1e-2,1e2,1e4]:
        lam_s=np.array([lam_disp(F,k,u,v,s*Du,s*Dv,qq/np.sqrt(s)) for qq in q])
        err=np.max(np.abs(lam_s-lam))
        qs,ls,poss=find_band(F,k,u,v,s*Du,s*Dv,qmax=300*np.sqrt(s)+50,N=30001)
        mapped=(poss/np.sqrt(s)).min(),(poss/np.sqrt(s)).max()
        print(f'   s={s:.0e}: mapped band=({mapped[0]:.6f},{mapped[1]:.6f}) max|lam diff|={err:.2e}')

# 3. Fixed-domain discrete Fourier modes inside band, L=1 periodic
print('\n=== Discrete Fourier modes inside band on fixed L=1 domain ===')
if found:
    F,k,u,v,qmin,qmax=found[0]
    print(f'Using F={F:.5f},k={k:.5f},u={u:.5f},v={v:.5f}')
    L=1.0
    for s in [1e-8,1e-6,1e-4,1e-2,1e0,1e2,1e4,1e6,1e8]:
        Du,Dv=s*1.0,s*0.5
        qmax_scan=300*np.sqrt(max(s,1e-12))+50
        q,lam,pos=find_band(F,k,u,v,Du,Dv,qmax=qmax_scan,N=40001)
        if len(pos)==0:
            print(f's={s:.0e}: no band')
            continue
        qlo,qhi=pos.min(),pos.max()
        nmax=int(np.ceil(qhi*L/(2*np.pi)))+5
        counts=[]
        nvals=[]
        for n in range(0,nmax+1):
            qn=2*np.pi*n/L
            if qn>=qlo-1e-8 and qn<=qhi+1e-8:
                # count integer vectors nx,ny with nx^2+ny^2=n^2
                cnt=0
                lim=n
                for nx in range(-lim,lim+1):
                    ny2=n*n-nx*nx
                    ny=int(round(np.sqrt(ny2)))
                    if ny*ny==ny2 and abs(ny)<=lim:
                        cnt += 1 if (nx==0 and ny==0) else (2 if nx==0 or ny==0 else 4)
                nvals.append(n)
                counts.append(cnt)
        print(f's={s:.0e}: band q=({qlo:.6f},{qhi:.6f}), radial integer modes inside={len(nvals)}, vector modes={sum(counts)}')
        if len(nvals)>0:
            print(f'   lowest n={nvals[0]} q={2*np.pi*nvals[0]:.6f}, highest n={nvals[-1]} q={2*np.pi*nvals[-1]:.6f}')