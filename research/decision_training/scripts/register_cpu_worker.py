"""Register and probe the independent CPU worker; no scientific task is launched."""

import json
from pathlib import Path

from conjecture_solver.execution_pool import MachineRegistry

from research_decision.storage import read_json, write_json

root = Path(__file__).resolve().parents[1]
cfg = read_json(root / "config/pipeline.local.json")
registry = MachineRegistry(cfg["machine_registry"])
remote = cfg["remote_root"]
registry.save(
    dict(
        id="independent-cpu",
        label="Independent 16-core CPU host",
        kind="ssh",
        host="cannlab-cpu",
        root=remote + "/cpu-worker",
        python=remote + "/resources/cpu-python",
        config=dict(
            execution_backend="process-cooperative",
            capabilities=[],
            cpus=16,
            memory_mb=24576,
            gpu_ids=[],
            max_jobs=16,
        ),
    )
)
result = registry.check("independent-cpu")
assert result["probe"]["execution"]["available"]
cfg["machine_ids"] = ["remote-cpu", "independent-cpu"]
cfg["public_resources"].update(
    independent_CPU_worker=dict(id="independent-cpu", cpus=16, memory_mb=24576, gpus=0),
    aggregate_simulation_cpus=48,
    aggregate_simulation_memory_mb=155648,
)
write_json(root / "config/pipeline.local.json", cfg)
write_json(root / "reports/independent_cpu_worker.json", result)
print(json.dumps(dict(ready=True, worker="independent-cpu", cpus=16, memory_mb=24576)))
