"""Bounded, read-only diagnostics from the project's owned NPU processes."""

from pathlib import Path

from research_decision.archive import remote_script
from research_decision.remote_control import Remote
from research_decision.storage import read_json

root = Path(__file__).resolve().parents[1]
remote = Remote(read_json(root / "config/pipeline.local.json"))
body = f"""from pathlib import Path
import json
root=Path({remote.root!r})
result={{}}
for name in ['autonomous-trainer','policy-0','policy-1']:
 p=root/'runtime/processes'/(name+'.log')
 if p.exists():
  with p.open('rb') as stream:
   stream.seek(max(0,p.stat().st_size-5000));result[name]=stream.read().decode(errors='replace')
print(json.dumps(result))
"""
print(remote_script(remote, body).decode())
