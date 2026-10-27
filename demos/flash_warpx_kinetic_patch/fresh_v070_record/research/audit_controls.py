"""Submit frozen postprocessing of completed controls; copies preserve hashes."""
from pathlib import Path
import shutil
from lab import lab
cases=[('refined','exp_0cc759f4429f9587ef9f4c55','refined_patch'),('time','exp_a3feea9cfd7050363e077857','refined_patch'),('ppc','exp_598cf8a2dc75dceade0c52c4','refined_patch'),('boundary','exp_4b72bb874b27665a7cc11322','refined_large_patch')]
files=['result.json','moments.npz','history.json','initial_fields.npz','final_fields.npz','reduced/field_energy.txt','reduced/particle_energy.txt'];inputs=['analysis_study.py','estimator.py'];args=['analysis'];outputs=['analysis.json','pressure_controls.png']
for label,e,patch in cases:
 d=Path(label+'_record');d.mkdir(exist_ok=True)
 for f in files:
  t=d/f;t.parent.mkdir(exist_ok=True);shutil.copy2(Path('../experiments')/e/'workspace/pic'/f,t);inputs.append(str(t))
 inputs +=[patch+'.npz',patch+'.json'];args+=['--case',label,str(d),patch+'.npz'];outputs +=[label+'_kinetic_fields.png',label+'_pressure_tensor.png']
r=lab.analyze('calculation.py',args=args,inputs=list(dict.fromkeys(inputs)),outputs=outputs,parent_experiment='exp_4b72bb874b27665a7cc11322',key='remaining-controls-audit');print({'audit':r['id']});s=lab.status();print({'remaining':s['remaining_seconds'],'active':[(e['id'],e['status']) for e in s['experiments'] if e['status'] in ['running','queued']]})
