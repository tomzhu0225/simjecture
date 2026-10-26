import numpy as np
def nulls(bx,by):
    cs=[]
    for b in [bx,by]: cs.append(np.stack([b[:-1,:-1],b[1:,:-1],b[:-1,1:],b[1:,1:]]))
    mask=(cs[0].min(0)<=0)&(cs[0].max(0)>=0)&(cs[1].min(0)<=0)&(cs[1].max(0)>=0)
    ys,xs=np.where(mask); found=[]; n=bx.shape[0]
    for y,x in zip(ys,xs):
        a=np.array([bx[y,x],by[y,x]]);b=np.array([bx[y,x+1],by[y,x+1]])-a;c=np.array([bx[y+1,x],by[y+1,x]])-a;d=np.array([bx[y+1,x+1],by[y+1,x+1]])-a-b-c
        uv=np.array([.5,.5])
        for _ in range(12):
            u,v=uv; jac=np.column_stack([b+d*v,c+d*u]);f=a+b*u+c*v+d*u*v
            try: step=np.linalg.solve(jac,f)
            except np.linalg.LinAlgError:break
            uv-=step
            if np.max(abs(step))<1e-9:break
        u,v=uv;f=a+b*u+c*v+d*u*v
        if not(-1e-7<=u<=1+1e-7 and -1e-7<=v<=1+1e-7) or np.max(abs(f))>1e-6:continue
        xx=(x+.5+u)/n-.5; yy=(y+.5+v)/n-.5
        if any(np.hypot(xx-q[0],yy-q[1])<1e-5 for q in found):continue
        det=float(np.linalg.det(np.column_stack([b+d*v,c+d*u])))
        found.append([float(xx),float(yy),'O' if det>0 else 'X'])
    return found
