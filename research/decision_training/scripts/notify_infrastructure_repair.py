"""Wake only the four affected pilot roles with factual infrastructure guidance."""
import json
from pathlib import Path

from conjecture_solver.research_continuation import submit

from research_decision.storage import read_json

root=Path(__file__).resolve().parents[1]
cfg=read_json(root/'config/pipeline.local.json')
report=read_json(root/'reports/lab_rpc_checks.json')
assert report['passed']
message=('Host repair completed and independently checked using a nonphysical remote I/O fixture. '
 'DecisionLab now forwards native Lab operations through a case-authenticated controller authority, '
 'which owns registry locking/reservations outside the role filesystem. The existing registry identity '
 'and read-only role filesystem remain unchanged. A real terminal execution and artifact retrieval on '
 'the new independent CPU worker succeeded. In your frozen current study use the existing remote-cpu '
 'worker; do not alter its frozen pool. Retry one normal DecisionLab.run, inspect the actual receipt, '
 'then adapt your own physical plan. This is an infrastructure notice, not scientific evidence or '
 'approval. No deadline, hypothesis, reference installation or numerical answer has changed. '
 'The public teacher decision and all host component reasons must still be recorded before execution.')
for task in read_json(root/'pilot/plan.json')['training_task_ids']:
    case=Path(cfg['case_store'])/'runs'/(task+'-teacher-1')
    record=submit(case,message,key='lab-authority-infrastructure-repair-v1')
    print(json.dumps(dict(case=case.name,notice_id=record['id'])))
