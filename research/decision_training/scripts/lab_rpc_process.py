import json
import sys
from pathlib import Path

from research_decision.processes import manage
from research_decision.storage import read_json

root=Path(__file__).resolve().parents[1]
cfg=read_json(root/'config/pipeline.local.json')
operation=sys.argv[1] if len(sys.argv)>1 else 'status'
argv=[str(root/'bin/controller-python'),'-m','research_decision.lab_rpc','--case-store',cfg['case_store']] if operation=='start' else None
print(json.dumps(manage(root,'lab-authority',operation,argv)))
