"""Export task-format files, delegating scheduling and agents to Harbor."""

import json
import shutil
from pathlib import Path

from . import PACK_VERSION
from .pack import HERE, TASKS, instruction, prepare, validate_task

DOCKERFILE = """FROM python:3.12.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends bash git curl \\
    && rm -rf /var/lib/apt/lists/* \\
    && pip install --no-cache-dir numpy==2.2.6 h5py==3.14.0 matplotlib==3.10.6 \\
    && useradd -m -u 1000 agent
WORKDIR /app
COPY task/ /app/
RUN chown -R agent:agent /app
"""

DRIVER = r'''"""Trusted separate-container driver. Submitted code runs as an unprivileged UID."""
import json
import os
import resource
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, "/tests/lib")
from conjecture_solver.llm_bench.pack import grade, render_verified_plots

def execute(work, backend, timeout):
    if os.geteuid() != 0 or not Path("/.dockerenv").exists():
        raise RuntimeError("This driver requires the dedicated root verifier container")
    # Expected answers and test code are not accessible to the candidate UID.
    Path("/tests").chmod(0o700)
    work.parent.chmod(0o711)
    work.chmod(0o777)
    def limits():
        os.setgroups([])
        os.setgid(1000)
        os.setuid(1000)
        resource.setrlimit(resource.RLIMIT_CPU, (int(timeout), int(timeout)))
        resource.setrlimit(resource.RLIMIT_AS, (3 * 1024**3, 3 * 1024**3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (4_000_000, 4_000_000))
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
    with (work / "stdout.log").open("w") as out, (work / "stderr.log").open("w") as err:
        result = subprocess.run(
            [sys.executable, "runner.py", "reduce.py", "cases.json", "actual.json"],
            cwd=work, timeout=timeout, preexec_fn=limits, stdout=out, stderr=err,
            env={"PATH":"/usr/local/bin:/usr/bin:/bin", "HOME":str(work),
                 "OPENBLAS_NUM_THREADS":"1", "OMP_NUM_THREADS":"1"},
        )
    return SimpleNamespace(returncode=result.returncode, timed_out=False,
                           workspace_exceeded=False,
                           stderr=(work / "stderr.log").read_text()[-1000:])

task = sys.argv[1]
logs = Path("/logs/verifier")
logs.mkdir(parents=True, exist_ok=True)
try:
    report = grade(task, "/app", backend="harbor-separate-verifier",
                   _candidate_executor=execute)
    render_verified_plots(task, "/app", report, logs / "verified-plots")
except Exception as error:
    report = {"passed":False, "error":str(error)[:1500]}
(logs / "result.json").write_text(json.dumps(report, indent=2))
(logs / "reward.txt").write_text("1" if report["passed"] else "0")
'''


def export(task, output):
    validate_task(task)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    env = output / "environment"
    tests = output / "tests"
    env.mkdir()
    tests.mkdir()
    prepare(task, env / "task")
    (env / "Dockerfile").write_text(DOCKERFILE)
    (output / "instruction.md").write_text(
        instruction(task) + "\nWork in /app. Inputs are /app/raw.\n"
    )
    artifacts = [
        "/app/reduce.py",
        "/app/result.json",
        "/app/FINDINGS.md",
        "/app/PROGRESS.md",
        "/app/raw",
    ]
    if task == "rz-diagnostics":
        artifacts.append("/app/plot-data.json")
    (output / "task.toml").write_text(f'''schema_version = "1.3"
artifacts = {json.dumps(artifacts)}

[task]
name = "simjecture/{task}"
description = "Experimental Simjecture Bench {PACK_VERSION}: recorded diagnostic coding"
authors = [{{name = "Bowen Zhu"}}]

[metadata]
pack_version = "{PACK_VERSION}"
category = "scientific-computing"
scientific_claim_approval = false

[agent]
timeout_sec = {TASKS[task]["seconds"]}
user = "agent"

[verifier]
timeout_sec = 240
environment_mode = "separate"
user = "root"
network_mode = "no-network"

[environment]
cpus = 2
memory_mb = 4096
storage_mb = 4096
network_mode = "public"
''')
    library = tests / "lib/conjecture_solver/llm_bench"
    library.mkdir(parents=True)
    library.parent.joinpath("__init__.py").write_text("")
    for name in ("__init__.py", "pack.py", "reference.py", "fixtures.py", "candidate_runner.py"):
        shutil.copyfile(HERE / name, library / name)
    shutil.copytree(HERE / "data", library / "data")
    (tests / "driver.py").write_text(DRIVER)
    (tests / "test.sh").write_text(
        f"#!/bin/bash\nset -euo pipefail\npython /tests/driver.py {task}\n"
    )
    (tests / "test.sh").chmod(0o755)
    solution = output / "solution"
    solution.mkdir()
    shutil.copyfile(HERE / "reference.py", solution / "reference.py")
    (solution / "solve.py").write_text(f"""import json
import shutil
from pathlib import Path
from reference import csv_result, rz_result
task = {task!r}
fn = csv_result if task == "csv-energy" else rz_result
values = {{name: fn(Path("/app/raw") / name) for name in ("n64","n128")}}
result = {{"cases":{{name:v[0] for name,v in values.items()}}}}
if task == "rz-diagnostics":
    result["relative_grid_differences"] = {{
        k:abs(values["n128"][0][k]-values["n64"][0][k])/max(abs(values["n128"][0][k]),1e-12)
        for k in ("K_in_peak_J","E_rad_total_J","E_rad_compression_J")}}
    data = {{"cases":{{name:v[1] for name,v in values.items()}}}}
    Path("/app/plot-data.json").write_text(json.dumps(data))
Path("/app/result.json").write_text(json.dumps(result))
Path("/app/FINDINGS.md").write_text(
    "Oracle control only. Recorded RZ outputs, CGS to joules. Operator agreement "
    "does not establish whole-domain closure or causation. Two grids measure sensitivity. "
    "Provenance: packaged input hashes. Compression sampling is not physical qualification.")
source = Path("/solution/reference.py").read_text()
fn_name = "csv_result" if task == "csv-energy" else "rz_result"
Path("/app/reduce.py").write_text(
    source + "\\ndef reduce_case(directory):\\n    return " + fn_name + "(directory)[0]\\n")
""")
    (solution / "solve.sh").write_text(
        "#!/bin/bash\nset -euo pipefail\npython /solution/solve.py\n"
    )
    (solution / "solve.sh").chmod(0o755)
    (output / "README.md").write_text(
        f"# Simjecture Bench {PACK_VERSION}\n\nExperimental Harbor task-format export. "
        "Run with a Harbor version supporting schema 1.3 and separate verifier containers. "
        "Docker and provider configuration are operator prerequisites. "
        "Use oracle and no-op controls before paid trials. The verifier receives only "
        "declared artifacts in a fresh container; candidate code is run as UID 1000. "
        "Do not merge model-only and native-agent framework comparisons.\n"
    )
    return {
        "task": task,
        "version": PACK_VERSION,
        "format": "harbor-1.3",
        "path": str(output.resolve()),
        "experimental": True,
        "requires": "Harbor separate-verifier support and Docker",
    }
