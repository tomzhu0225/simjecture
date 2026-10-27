"""Arithmetic synthesis of the prospectively frozen conservative diagnostic envelope."""
import json
from pathlib import Path
fresh=json.load(open('analysis.json'));old=json.load(open('qualified_mesh_source.json'));other=json.load(open('qualified_remaining.json'));out={'scope':'Arithmetic interpretation; underlying decisive observables are in fresh evidence-stage PIC receipts. Controls and frozen postprocessing remain qualification, not promoted trajectories.','species':{},'qualification_gates':{},'decision':'unresolved'}
allcases={**old['cases'],**other['cases'],**fresh['cases']}
for name,r in allcases.items():
 out['qualification_gates'][name]=bool(all(v is True for v in r['operational_gates'].values()) and all(r['species'][sp]['eligible'] and r['species'][sp]['secondary_eligible'] and r['species'][sp]['max_pressure_relativistic_trace_correction']<=.03 for sp in ['ions','electrons']))
for name,c in [('mesh',old['comparisons']['mesh']),('source',old['comparisons']['pilot']),('time',other['comparisons']['time']),('particles',other['comparisons']['ppc']),('boundary',other['comparisons']['boundary'])]:
 out['qualification_gates']['comparison_'+name]=all(abs(v['A_mean_difference'])<=.02 and v['max_time_area_mean_difference']<=.04 and v['maximum_pressure_mean_relative_difference']<=(.03 if name=='boundary' else .05) and v['maximum_density_mean_relative_difference']<=.03 for v in c.values())
for sp in ['ions','electrons']:
 vals=[v['species'][sp]['area_time_mean'] for v in fresh['cases'].values()]
 contrib={
  'source':abs(old['comparisons']['pilot'][sp]['A_mean_difference']),
  'boundary':abs(other['comparisons']['boundary'][sp]['A_mean_difference']),
  'mesh':abs(old['comparisons']['mesh'][sp]['A_mean_difference']),
  'timestep':abs(other['comparisons']['time'][sp]['A_mean_difference']),
  'particle_count':abs(other['comparisons']['ppc'][sp]['A_mean_difference']),
  'full_fresh_seed_range':max(vals)-min(vals),
  'sampling_two_sigma_no_time_independence':max(v['species'][sp]['sampling_two_sigma_estimate_max'] for v in allcases.values()),
  'subbin_flow_pressure_upper':max(v['species'][sp]['secondary_between_bin_velocity_pressure_upper_max'] for v in allcases.values()),
  'primary_secondary_mean_A_difference':max(v['species'][sp]['primary_secondary_mean_A_absolute_difference'] for v in allcases.values()),
  'relativistic_trace_correction':max(v['species'][sp]['max_pressure_relativistic_trace_correction'] for v in allcases.values())}
 uncertainty=sum(contrib.values());out['species'][sp]=dict(fresh_means=vals,maximum_fresh_mean=max(vals),contributions=contrib,conservative_envelope=uncertainty,upper=max(vals)+uncertainty,lower=min(vals)-uncertainty)
allpass=all(out['qualification_gates'].values());out['all_declared_gates_pass']=allpass
if allpass and all(v['upper']<=.2 for v in out['species'].values()):out['decision']='supported_candidate_pending_independent_review'
elif allpass and any(v['lower']>.2 for v in out['species'].values()):out['decision']='falsified_candidate_pending_independent_review'
Path('decision.json').write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');print(json.dumps(out))
