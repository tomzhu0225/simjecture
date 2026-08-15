import json, numpy as np

data=json.load(open('simulation_results.json'))
print('=== Trajectory samples from simulation_results.json ===')
for s in ['1','10']:
    print('\ncase s=',s)
    print('P_final',data[s]['P_final'],'t_final',data[s]['t_final'])
    # print selected records
    recs = data[s]['records']
    for r in recs[::max(1,len(recs)//15)]:
        print(' t',r['t'],'P',f"{r['P']:.3e}")

print('\n=== Final fields ===')
for s in [1,10]:
    z=np.load(f'result_s{s}.npz',allow_pickle=True)
    u=z['u']; v=z['v']
    P=float(np.mean((u-np.mean(u))**2)/(np.mean(u)**2))
    print(f's={s}: P={P:.6e}, mean_u={np.mean(u):.6f}, min_u={u.min():.6f}, max_u={u.max():.6f}, mean_v={np.mean(v):.6f}, min_v={v.min():.6f}, max_v={v.max():.6f}')

print('\n=== Radial Fourier power spectrum of final u (share per integer n) ===')
for s in [1,10]:
    z=np.load(f'result_s{s}.npz')
    u=z['u']; N=u.shape[0]; L=40.0; dx=L/N
    ky=2*np.pi*np.fft.fftfreq(N,d=dx)
    kx=2*np.pi*np.fft.rfftfreq(N,d=dx)
    KX,KY=np.meshgrid(kx,ky)
    Uhat=np.fft.rfft2(u-np.mean(u))
    power=np.abs(Uhat)**2
    QK=np.sqrt(KX**2+KY**2)
    print(f's={s}: total non-zero-mode power={power.sum():.3e}')
    for n in range(0,9):
        q0=2*np.pi*n/L
        if n==0:
            mask=(QK<=2*np.pi*0.5/L)
            # exclude homogeneous mean component already removed
        else:
            qm=2*np.pi*(n-0.5)/L
            qp=2*np.pi*(n+0.5)/L
            mask=(QK>qm)&(QK<=qp)
        tot=np.sum(power[mask])
        share=tot/power.sum() if power.sum()>0 else 0
        print(f'  n={n} q~{q0:.4f}: power={tot:.3e}, share={share:.4f}')