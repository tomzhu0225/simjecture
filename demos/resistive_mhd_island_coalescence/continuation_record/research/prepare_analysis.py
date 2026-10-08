import json,shutil
from pathlib import Path
from lab import lab
root=Path('..')
s=lab.status();states={e['id']:e['status'] for e in s['experiments']};entries=[];inputs=['guided_reader.py','study_analysis.py','protocol.json','cfl_control.json']
for c in json.loads(Path('fresh_cases.json').read_text()):
 if states[c['experiment']]!='succeeded':continue
 name=f"fresh_S{c['S']}_N{c['n']}.json";w=root/'experiments'/c['experiment']/'workspace';shutil.copyfile(w/'result.json',name);inputs.append(name)
 entries.append({'experiment':c['experiment'],'json':name,'stage':'fresh_evidence'})
# Include one complete refined raw trajectory for field audit and display.
raw=next((c for c in json.loads(Path('fresh_cases.json').read_text()) if c['n']==384 and states[c['experiment']]=='succeeded'),None)
if raw:
 shutil.copyfile(root/'experiments'/raw['experiment']/'workspace/raw_fields.npz','figure_raw.npz');inputs.append('figure_raw.npz');next(e for e in entries if e['experiment']==raw['experiment'])['raw']='figure_raw.npz'
Path('fresh_manifest.json').write_text(json.dumps(entries,indent=2));inputs.append('fresh_manifest.json');Path('analysis_inputs.json').write_text(json.dumps(inputs));print(json.dumps(entries))
