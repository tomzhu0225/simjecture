import numpy as np
import json

def gs_hss(F,k):
    disc=1.0-4.0*(F+k)**2/F
    if disc<0: return []
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

def find_band(F,k,u,v,Du,Dv,qmax=5,N=100001):
    q=np.linspace(0,qmax,N)
    lam=np.array([lam_disp(F,k,u,v,Du,Dv,qq) for qq in q])
    pos=q[lam>1e-10]
    if len(pos)==0: return None,None,0,None
    return pos.min(),pos.max(),lam.max(),q[lam.argmax()]

L=40.0
q1=2*np.pi/L
print('L',L,'q1',q1)
cands=[]
for ratio in [2.0,3.0,5.0,10.0]:
    for F in np.linspace(0.02,0.10,41):
        for k in np.linspace(0.02,0.08,31):
            hss=gs_hss(F,k)
            for u,v in hss:
                Du=1.0; Dv=Du/ratio
                # homogeneous stability
                fu=-F-v*v; fv=-2*u*v; gu=v*v; gv=2*u*v-(F+k)
                tr=fu+gv; det=fu*gv-fv*gu
                if tr>-1e-6 or det<1e-8: continue
                qmin,qmax,lmax,qpeak=find_band(F,k,u,v,Du,Dv)
                if lmax is None or lmax<0.01: continue
                # base band should contain q1; scaled s=10 band should be below q1
                qmin10=qmin/np.sqrt(10.0); qmax10=qmax/np.sqrt(10.0)
                if qmin<q1-1e-6 and qmax>q1+1e-6 and qmax10<q1-1e-6:
                    cands.append({'ratio':ratio,'F':F,'k':k,'u':u,'v':v,'qmin':qmin,'qmax':qmax,'lmax':lmax,'qpeak':qpeak,'tr':tr,'det':det})
                    break
            if cands and abs(cands[-1]['F']-F)<1e-9 and abs(cands[-1]['k']-k)<1e-9 and cands[-1]['ratio']==ratio:
                pass

cands.sort(key=lambda c:-c['lmax'])
print('candidates',len(cands))
for c in cands[:20]:
    print(f"ratio={c['ratio']} F={c['F']:.4f} k={c['k']:.4f} u={c['u']:.4f} v={c['v']:.4f} band=({c['qmin']:.4f},{c['qmax']:.4f}) lmax={c['lmax']:.4f} qpeak={c['qpeak']:.4f} tr={c['tr']:.2e} det={c['det']:.2e}")

if cands:
    with open('regime_candidates.json','w') as f:
        json.dump(cands[:20],f,indent=2)