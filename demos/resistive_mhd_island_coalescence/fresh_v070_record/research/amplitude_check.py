"""Failed offline check of a slope-budget extension, without rate fitting."""
import json,numpy as np
from pathlib import Path
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
r=json.loads(Path('conditional_calibration.json').read_text());q=np.array([0,.01,.03,.05]);a=np.array([v['a'] for v in r['common_knots']]);B=np.array([v['B'] for v in r['common_knots']]);pred=[]
for S,target in [(1000,.04968858390778796),(2000,.03824244686429199)]:
 def fun(t,v):
  w,p=v;k=int(np.clip(np.searchsorted(q,p,side='right')-1,0,2));bb=float(np.interp(p,q,B));aa=float(np.interp(p,q,a));bp=(B[k+1]-B[k])/(q[k+1]-q[k]);pd=1/S*np.sqrt(2/np.pi)*bb/np.sqrt(max(w,1e-30));return [-4*aa*w+2/S+2*w*bp/bb*pd,pd]
 def ev(t,v):return v[1]-.05
 ev.terminal=True
 s=solve_ivp(fun,[0,5],[r['w0'],0],events=ev,rtol=1e-9,atol=1e-12,max_step=.001,dense_output=True);hi=float(s.t_events[0][0]);lo=brentq(lambda t:s.sol(t)[1]-.01,0,hi);rate=.04/(hi-lo);de=abs((hi-lo)/(.04/target)-1)
 pred.append({'S_eta':S,'t_low':lo,'t_high':hi,'model_rate':rate,'anchor_rate':target,'duration_relative_error':de,'required_5pct_replay_gate':de<=.05})
Path('amplitude_calibration.json').write_text(json.dumps({'equations':'psi_dot=eta*sqrt(2/pi)*B(psi)/sqrt(w); w_dot=-4*a(psi)*w+2*eta+2*w*B_prime(psi)/B(psi)*psi_dot','motivation':'Local central magnetic-slope budget of an erf template includes time-dependent amplitude, unlike the simple Gaussian-width law. Neglects longitudinal diffusion and higher profile departures.','predictions':pred,'all_calibration_gates':all(v['required_5pct_replay_gate'] for v in pred),'status':'exploratory failed calibration; no validation, no rate fitting, no scientific repair claim'},indent=2)+'\n')
print(json.dumps(pred))
