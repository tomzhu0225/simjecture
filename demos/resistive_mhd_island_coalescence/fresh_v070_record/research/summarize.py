"""Regenerate human-facing table from immutable experiment receipts; no claim promotion."""
from pathlib import Path
import json,math
root=Path('../experiments'); rows=[]
for p in sorted(root.glob('exp_*.json')):
 rec=json.loads(p.read_text()); w=root/rec['id']/'workspace'; f=w/'result.json'
 row={'experiment':rec['id'],'status':rec['status'],'stage':rec['stage'],'source':rec['binding']['source'],'args':rec['binding']['args'],'wall_seconds':rec.get('execution',{}).get('wall_seconds'),'runtime_sha256':rec['binding'].get('runtime_sha256'),'outputs':rec.get('artifacts',{}),'missing_outputs':rec.get('missing_outputs',[])}
 if f.exists():
  r=json.loads(f.read_text()); row.update({k:r.get(k) for k in ['config','metrics','checks','conservation','cadence_rate_interval','topology_max_sign_changes_through_window','fields','timing','provenance']}); row['result_path']=str(f)
 rows.append(row)
Path('run_table.json').write_text(json.dumps({'runs':rows,'interpretation':'Fresh records; exploration remains non-evidentiary; slope intervals added after qualified comparisons.'},indent=2)+'\n')
for r in rows:
 if 'config' in r: print(r['experiment'],r['stage'],r['config']['S_eta'],r['config']['n'],r['metrics']['normalized_flux_slope'],r['metrics']['flux_high_crossing_time'],r['metrics']['flux_path_max_abs_mismatch'])
