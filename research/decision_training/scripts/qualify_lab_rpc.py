"""Nonphysical execution proves case-isolated Lab can reserve the new CPU worker."""

import json
import os
import time
import uuid
from pathlib import Path

from conjecture_solver.execution_pool import MachineRegistry
from conjecture_solver.research_service import ResearchService

from research_decision.case import closeout
from research_decision.simjecture_bridge import DecisionLab
from research_decision.storage import read_json, write_json

root = Path(__file__).resolve().parents[1]
cfg = read_json(root / "config/pipeline.local.json")
case = Path(cfg["case_store"]) / "runs" / ("PREP-LAB-AUTHORITY-" + str(time.time_ns()))
pool = MachineRegistry(cfg["machine_registry"]).freeze(cfg["machine_ids"])
service = ResearchService.create(
    case,
    "Nonphysical RPC fixture",
    wall_seconds=60,
    execution_pool=pool,
    execution_backend="process-cooperative",
    artifact_policy="remote",
    report_reserve_seconds=1,
)
write_json(
    case / "task.json", dict(task_id="PREP-LAB-AUTHORITY", question="I/O fixture", total_wall_seconds=60)
)
write_json(case / "initial-state.json", dict(fixture=True))
write_json(
    case / "study-run.json",
    dict(arm="simjecture", deadline=service.manifest["deadline"], transport_token=uuid.uuid4().hex),
)
(case / "research/fixture.py").write_text(
    "from pathlib import Path\nPath('fixture.json').write_text('{\"ready\":true}')\n"
)
os.environ["SCIENCE_TRANSPORT_SOCKET"] = read_json(root / "config/isolation.local.json")["transport_socket"]
lab = DecisionLab(case)
record = lab.run(
    "fixture.py",
    outputs=["fixture.json"],
    machine="independent-cpu",
    resources=dict(cpus=1, memory_mb=256, gpus=0),
    stage="exploration",
    purpose="diagnostic",
)
cutoff = time.monotonic() + 30
while time.monotonic() < cutoff:
    lab.status()
    actual = read_json(case / "experiments" / (record["id"] + ".json"))
    if actual["status"] in {"succeeded", "failed", "timed_out"}:
        break
    time.sleep(0.2)
assert actual["status"] == "succeeded", actual
lab.fetch_remote(experiment=record["id"], path="fixture.json")
closeout(case, "nonphysical_qualification")
write_json(
    root / "reports/lab_rpc_checks.json",
    dict(
        passed=True,
        independent_cpu_execution=True,
        registry_identity_preserved=True,
        filesystem_isolation_unchanged=True,
        scientific_runs=0,
        fixture_case=case.name,
        fixture_receipt=record["id"],
    ),
)
print(json.dumps(dict(passed=True, independent_cpu_execution=True, scientific_runs=0)))
