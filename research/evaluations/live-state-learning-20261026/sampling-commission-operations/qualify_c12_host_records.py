"""Read-only check of new exporter bindings against six retained native workflows."""
from pathlib import Path
import json,time,hashlib
from export_workflow_returns import require_host_configuration
from simjecture_monitor.workflow_collection import check_schedule
r=Path('/home/simjecture/investigations/scientific-attention-20261025')
root=r/'control-commission-02'
plan=json.loads((root/'PLAN.json').read_text())
config=dict(worker_prompt='task_protocol',parent_turn_limit=12,maximum_parallel_workflows=1,minimum_gap_seconds=90)
checking=dict(collection_settings=config,source_files_sha256={'src/simjecture_monitor/workflow_prompt.py':plan['source_files_sha256']['packages/simjecture-monitor/src/simjecture_monitor/workflow_prompt.py']})
commission=json.loads((root/'COMMISSION.json').read_text());assert commission['commissioned'] and not commission['violations']
assert all(x.get('ended_at') is not None for x in json.loads((root/'native-budget.json').read_text())['starts'])
rows=[]
for block in plan['blocks']:
 for trial in block['trials']:
  folder=root/trial['id'];out=json.loads((folder/'OUTCOME.json').read_text())
  rows.append(dict(id=trial['id'],execution=require_host_configuration(folder,out,checking)))
campaign=json.loads((root/'CAMPAIGN.json').read_text())
check_schedule([trial for block in campaign['blocks'] for trial in block['trials']],config)
value=dict(stage='passed',at=time.time(),configuration=config,rows=rows,source=str(Path(require_host_configuration.__code__.co_filename)),scope='Read-only validation against retained native records; no new sampling, model calls or training')
(r/'c12-host-record-qualification.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value))
