"""Start the explicitly authorized remote 24-hour investigation exactly once."""

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from conjecture_solver.execution_pool import MachineRegistry
from conjecture_solver.mvp_guidance import MVPGuidedCommissioningPackage
from conjecture_solver.research_limits import configure_limits
from conjecture_solver.research_service import ResearchService, put


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    args = parser.parse_args()
    task = args.task.resolve()
    source = task / "source"
    case = source / "research/evaluations/euler-optimality-24h-20261102"
    ready = json.loads((task / "operator/readiness.json").read_text())
    assert ready["status"] == "passed", "Commissioning/model readiness must pass first"
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    assert current == ready["source_commit"], "Source changed after readiness"
    package = MVPGuidedCommissioningPackage.read(ready["package"])
    assert package.package_sha256 == ready["package_sha256"], "Commissioning changed"
    campaign = task / "study"
    assert not campaign.exists(), "Do not restart or replace a study's original clock"
    pool = MachineRegistry(task / "machines").freeze(["uu-local"])
    hypothesis = (
        "Find a useful numerical algorithm for the frozen nonlinear compressible 3D Euler "
        "Taylor-Green family, with a Lean-checked continuum accuracy theorem and matching "
        "complete computational-work upper/lower bounds in a scientifically justified "
        "competitor class. Discharge smooth existence, admissibility, regularity, actual "
        "initialization, discrete evolution and continuous reconstruction. All competitors "
        "receive the explicit initial formulas. Preserve unknown coupled dynamics and the "
        "specified physical error. No analytic-flow, output-size, cache/CFL/stage-count, "
        "assumed-accuracy or finite-benchmark substitute completes this objective. "
        "Read commissioning/lean_euler/nonlinear/contract.json and commissioning/PROTOCOL.txt."
    )
    protocol = (case / "PROTOCOL.txt").read_text()
    lab = ResearchService.create(
        campaign,
        hypothesis,
        wall_seconds=86400,
        report_reserve_seconds=1800,
        execution_pool=pool,
        execution_backend="bubblewrap",
        artifact_policy="eager",
        completion_policy="repair",
        allow_solver_development=True,
        max_experiment_bytes=8 * 1024**3,
        max_total_bytes=64 * 1024**3,
        method_review_scope="used_instruments",
    )
    lab.freeze_protocol(protocol)
    lab.install_guidance(ready["package"])
    configure_limits(
        campaign,
        {
            "helper_workers": 4,
            "review_seconds": 1200.0,
            "worker_action_limit": None,
            "worker_checkpoint_seconds": None,
        },
        reason="Operator authorizes director-selected parallel mathematical research.",
    )
    operator = campaign / "operator_input"
    operator.mkdir(exist_ok=True)
    (operator / "hypothesis.txt").write_text(hypothesis)
    (operator / "instructions.txt").write_text(protocol)
    command = [
        sys.executable,
        "-m",
        "conjecture_solver.study",
        "--campaign",
        str(campaign),
        "--state-dir",
        str(campaign / "supervisor"),
        "--hypothesis-file",
        str(operator / "hypothesis.txt"),
        "--instructions-file",
        str(operator / "instructions.txt"),
        "--mode",
        "minimal",
        "--execution-backend",
        "bubblewrap",
        "--capabilities",
        "none",
        "--backend",
        "codex",
        "--model",
        "gpt-6.1-sol",
        "--reasoning-effort",
        "high",
        "--executable",
        str(task / "operator/codex-study"),
        "--judge-model",
        "gpt-6-astra",
        "--judge-reasoning-effort",
        "xhigh",
        "--director-model",
        "gpt-6-astra",
        "--director-reasoning-effort",
        "xhigh",
        "--director",
        "--allow-solver-development",
        "--completion-policy",
        "repair",
        "--machine-registry",
        str(task / "machines"),
        "--machine",
        "uu-local",
        "--wall-seconds",
        "86400",
        "--turn-seconds",
        "1800",
        "--quiet",
    ]
    token = hashlib.sha256(str(campaign).encode()).hexdigest()[:20]
    record = dict(
        campaign=str(campaign),
        command=command,
        source_commit=current,
        models={
            "director": ["gpt-6-astra", "xhigh"],
            "reviewer": ["gpt-6-astra", "xhigh"],
            "worker_and_helpers": ["gpt-6.1-sol", "high"],
        },
        wall_seconds=86400,
        created_at=lab.manifest["created_at"],
        deadline=lab.manifest["deadline"],
        deadline_Asia_Shanghai=datetime.fromtimestamp(
            lab.manifest["deadline"], timezone(timedelta(hours=8))
        ).isoformat(),
        package_sha256=package.package_sha256,
        helper_capacity_initial=4,
        director_helper_capacity_range=[1, 16],
        local_host_dependency=False,
        downstream_compute_hosts=[],
        monitor_token=token,
    )
    put(task / "operator/launch.json", record)
    unit = "simjecture-euler-optimality-20261102.service"
    units = Path.home() / ".config/systemd/user"
    units.mkdir(parents=True, exist_ok=True)
    unit_path = units / unit
    assert not unit_path.exists(), "Refuse to replace an existing service"
    unit_path.write_text(
        "[Unit]\nDescription=Simjecture 24-hour nonlinear Euler research\n"
        "[Service]\nType=simple\n"
        f"WorkingDirectory={task}\nExecStart={sys.executable} {case / 'watchdog.py'} {task}\n"
        "Environment=PATH=/home/simjecture/.local/bin:/usr/local/bin:/usr/bin:/bin\n"
        "Environment=OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1\n"
        "Environment=HTTP_PROXY=http://127.0.0.1:9674 HTTPS_PROXY=http://127.0.0.1:9674\n"
        "Restart=on-failure\nRestartSec=30\nKillMode=control-group\nTimeoutStopSec=30\n"
        f"StandardOutput=append:{task / 'operator/watchdog.log'}\n"
        f"StandardError=append:{task / 'operator/watchdog.log'}\n"
        "[Install]\nWantedBy=default.target\n"
    )
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", unit], check=True)
    record.update(service=unit, status="launched")
    put(task / "operator/deployment.json", record)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
