import json
from pathlib import Path
x=json.loads(Path('cfl04.json').read_text());y=json.loads(Path('cfl08.json').read_text())
r=x['metrics']['normalized_flux_slope'];s=y['metrics']['normalized_flux_slope']
d={'parents':['exp_450f204fb0aa5b05e30c9f0c','exp_22b4b0e7c2fcdc0417ce7387'],'rates':[r,s],'relative_rate_difference':abs(s/r-1),'crossing_time_changes':{k:y['metrics'][k]-x['metrics'][k] for k in ['flux_low_crossing_time','flux_high_crossing_time']},'conservation':[x['conservation'],y['conservation']],'windows':[x['window'],y['window']],'checks':[x['checks'],y['checks']],'costs':[x['provenance']['elapsed_seconds'],y['provenance']['elapsed_seconds']]}
Path('qualification.json').write_text(json.dumps(d,indent=2,allow_nan=False))
print(json.dumps(d))
