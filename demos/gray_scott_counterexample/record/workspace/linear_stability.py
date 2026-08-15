import numpy as np

def gs_hss(F,k):
    # Nontrivial HSS: u*v = F+k, and F(1-u) = u*v^2
    disc = 1.0 - 4.0*(F+k)**2/F
    if disc < 0:
        return []
    suc = []
    for sign in (1.0,-1.0):
        u = (1.0 + sign*np.sqrt(disc))/2.0
        if u <= 0:
            continue
        v = (F+k)/u
        if v > 0:
            suc.append((u,v))
    return suc

def lam_max(F,k,u0,v0,Du,Dv,q):
    # Jacobian entries
    fu = -v0*v0 - F
    fv = -2.0*u0*v0
    gu = v0*v0
    gv = 2.0*u0*v0 - (F+k)
    A = fu - Du*q*q
    B = gv - Dv*q*q
    tr = A + B
    det = A*B - fv*gu
    disc = tr*tr - 4.0*det
    if disc < 0:
        return tr/2.0
    return tr/2.0 + np.sqrt(disc)/2.0

def find_band(F,k,u0,v0,Du,Dv,qmax=2000,N=20001):
    q = np.linspace(0,qmax,N)
    lam = np.array([lam_max(F,k,u0,v0,Du,Dv,qq) for qq in q])
    pos = q[lam > 1e-10]
    return q, lam, pos

print('=== Infinite-continuum scale invariance of unstable band ===')
for F,k in [(0.09,0.05),(0.06,0.01),(0.11,0.05),(0.04,0.07)]:
    hss = gs_hss(F,k)
    if not hss:
        print(f'F={F}, k={k}: no nontrivial HSS')
        continue
    print(f'F={F}, k={k}, HSS={hss}')
    for u0,v0 in hss:
        Du0,Dv0 = 2e-4, 1e-4
        q, lam, pos = find_band(F,k,u0,v0,Du0,Dv0)
        if len(pos)==0:
            print(f'  HSS {u0:.6f},{v0:.6f}: no unstable band')
            continue
        # Check exact invariance: for scaled diffusions, lam(q/sqrt(s)) should equal lam(q)
        s = 100.0
        qs = q/np.sqrt(s)
        lams = np.array([lam_max(F,k,u0,v0,s*Du0,s*Dv0,qq) for qq in qs])
        err = np.max(np.abs(lams - lam))
        # band for base and scaled in natural units
        q2, lam2, pos2 = find_band(F,k,u0,v0,s*Du0,s*Dv0)
        band0=(pos.min(),pos.max())
        band1=(pos2.min()/np.sqrt(s), pos2.max()/np.sqrt(s))
        print(f'  HSS {u0:.6f},{v0:.6f}: band0 q={band0}, scaled band/sqrt(s)={band1}, max|lam diff|={err:.2e}')

print()
print('=== Fixed finite domain: discrete Fourier modes inside unstable band ===')
L = 1.0
for s in [1e-4, 1e-2, 1.0, 1e2, 1e4]:
    Du,Dv = s*2e-4, s*1e-4
    F,k=0.09,0.05
    u0,v0 = gs_hss(F,k)[1]
    q, lam, pos = find_band(F,k,u0,v0,Du,Dv)
    if len(pos)==0:
        print(f's={s:.0e}: no band')
        continue
    qmin,qmax=pos.min(),pos.max()
    # allowed wavevectors for periodic LxL: q=(2pi/L)*sqrt(nx^2+ny^2)
    n = np.arange(0,2001)
    qa = (2*np.pi/L)*n
    inside = qa[(qa>=qmin-1e-9)&(qa<=qmax+1e-9)]
    # include vector multiplicity approximately
    vec_count = 0
    for qq in inside:
        nn = qq*L/(2*np.pi)
        # exact integer n
        ni = int(round(nn))
        cnt = 0
        for nx in range(-ni,ni+1):
            ny2 = ni*ni - nx*nx
            if ny2<0: continue
            ny = int(round(np.sqrt(ny2)))
            if nx*nx+ny*ny==ni*ni:
                cnt += 1 if nx==0 and ny==0 else (2 if nx==0 or ny==0 else 4)
        vec_count += cnt
    print(f's={s:.0e}: band q=({qmin:.4f},{qmax:.4f}), radial modes inside={len(inside)}, vector modes~{vec_count}')
    # lowest positive mode
    if len(inside)>0:
        print(f'   lowest unstable Fourier q={inside.min():.4f} (wavelength {2*np.pi/inside.min():.4f})')