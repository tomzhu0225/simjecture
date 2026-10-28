from pathlib import Path
import json,hashlib,time
r=Path('/home/simjecture/investigations/scientific-attention-20261025');read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert read(r/'c12-guard-status.json')['stage']=='released'
assert read(r/'c12-controller-status.json')['native_starts']==0
assert read(r/'native-budget-c12.json')['starts']==[]
assert not (r/'parked-commission-c12/CAMPAIGN.json').exists()
assert not list((r/'parked-commission-c12').glob('episode-*-controller.json'))
assert read(r/'c12-preflight-status.json')['stage']=='passed'
parent=read(r/'c12-resource-plan.json');resource=read(r/'c13-resource-plan.json');assert all(parent[k]==resource[k] for k in ['stop_by','starting_balance','compute_cap','maximum_native_starts'])
(r/'c13-probes.json').write_bytes((r/'c12-probes.json').read_bytes())
(r/'c13-native-codex').write_bytes((r/'c12-native-codex').read_bytes());(r/'c13-native-codex').chmod(0o700)
old=read(r/'c12-phase-plan.json');names=[n.replace('c12','c13') for n in old['orchestration_sha256']]
assert sha(r/'parked-commission-c12/PLAN.json')==old['assignment_plan_sha256']
asset=read(r/'c13-assets.json');assert sha(r/'validation-model-assets-c13.tar.gz')==asset['sha256']
value=old|dict(created_at=time.time(),replacement_of='c12-phase-plan.json',parent_plan_sha256=sha(r/'c12-phase-plan.json'),orchestration_sha256={n:sha(r/n) for n in names},resource_plan_sha256=sha(r/'c13-resource-plan.json'),asset_archive=asset,unchanged_scientific_assignments=True,prior_scientific_attempts=0,scope='Replace timed-out 240 MB deployment with 120 MB identical-SFT subset; unchanged scientific source/IDs/model/decoder/resource ceilings')
(r/'c13-phase-plan.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value),flush=True)
