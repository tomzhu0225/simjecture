import numpy as np

F=0.072
k=0.062
L=40.0
# lower stable HSS
u=(1-np.sqrt(1-4*(F+k)**2/F))/2
v=(F+k)/u
fu=-F-v*v
fv=-2*u*v
Gu=v*v
Gv=2*u*v-(F+k)
print('u,v',u,v,'trace',fu+Gv,'det',fu*Gv-fv*Gu)

def lam(q,Du,Dv):
    A=fu-Du*q*q
    B=Gv-Dv*q*q
    tr=A+B
    det=A*B-fv*Gu
    return tr/2+np.sqrt(max(tr*tr-4*det,0))/2

base=[0.1126,0.4877]
print('base band approx',base)
for s in [0.5,1.0,5.0,8.0,10.0,12.0,20.0,50.0,100.0]:
    Du=s; Dv=s/3.0
    print('\ns=',s)
    for n in [0,1,2,3,4]:
        q=2*np.pi*n/L
        if n==0:
            print(' homogeneous lam',lam(q,Du,Dv))
        else:
            print(' n',n,'q',round(q,5),'lam',round(lam(q,Du,Dv),8))
    # exact band
    qg=np.linspace(0,3,200001)
    lams=np.array([lam(qq,Du,Dv) for qq in qg])
    pos=qg[lams>1e-9]
    if len(pos):
        print(' band',pos.min(),pos.max())
    else:
        print(' no positive band')