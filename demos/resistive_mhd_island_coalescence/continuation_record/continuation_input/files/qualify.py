import json
from pathlib import Path
x=json.loads(Path('cfl04.json').read_text());y=json.loads(Path('cfl08.json').read_text())
r=x['metrics']['normalized_flux_slope'];s=y['metrics']['normalized_flux_slope']
d={'parents':['exp_450f204fb0aa5b05e30c9f0c','exp_22b4b0e7c2fcdc0417ce7387'],'rates':[r,s],'relative_rate_difference':abs(s/r-1),'crossing_time_changes':{k:y['metrics'][k]-x['metrics'][k] for k in ['flux_low_crossing_time','flux_high_crossing_time']},'conservation':[x['conservation'],y['conservation']],'windows':[x['window'],y['window']],'checks':[x['checks'],y['checks']],'costs':[x['provenance']['elapsed_seconds'],y['provenance']['elapsed_seconds']]}
z=json.loads(Path('refine384.json').read_text())
d['refinement']={'experiment':'exp_45fced4d67b6d6b304622ac3','rate':z['metrics']['normalized_flux_slope'],'relative_change_from256':z['metrics']['normalized_flux_slope']/s-1,'window':z['window'],'metrics':z['metrics'],'conservation':z['conservation'],'realized':z['realized'],'executable_sha256':z['provenance']['executable_sha256'],'cost_seconds':z['provenance']['elapsed_seconds']}
Path('qualification.json').write_text(json.dumps(d,indent=2,allow_nan=False))
print(json.dumps(d))
