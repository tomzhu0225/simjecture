import sys,json
from pathlib import Path
from lab import lab
S=int(sys.argv[1]);n=int(sys.argv[2]);t=sys.argv[3];cap=int(sys.argv[4])
a=['--eta',str(1/S),'--n',str(n),'--tmax',t,'--cadence','.025','--cfl','.8','--ranks','4']
r=lab.run('calculation.py',args=a,inputs=['guided_reader.py','study_analysis.py','protocol.json','cfl_control.json'],outputs=['result.json','raw_fields.npz','case/flash.par','case/execution.log'],capability='flash-island-coalescence-resistive-mhd-4.8',stage='evidence',method='method_462b34a5c15f82e6165b0cc4',timeout=cap,key=f'fresh-S{S}-N{n}',purpose='comparison' if n==384 else 'baseline',monitor={'path':'case/execution.log','format':'flash','unit':'s','target':float(t),'baseline':0.})
p=Path('fresh_cases.json');lst=json.loads(p.read_text()) if p.exists() else [];lst.append({'experiment':r['id'],'S':S,'n':n,'tmax':float(t),'args':a});p.write_text(json.dumps(lst,indent=2));print(r['id'],r['status'])
