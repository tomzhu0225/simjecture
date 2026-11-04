"""Prepare and replay the frozen commissioning package before the 24-hour clock."""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from conjecture_solver.execution_pool import MachineRegistry
from conjecture_solver.mvp_guidance import MVPGuidedCommissioningPackage
from conjecture_solver.research_service import ResearchService, put


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--attempt", default="01")
    parser.add_argument("--runtime-root", type=Path)
    args = parser.parse_args()
    task = args.task.resolve()
    assert args.attempt.isalnum(), "Use an alphanumeric attempt identifier"
    source = task / "source"
    case = source / "research/evaluations/euler-optimality-24h-20261102"
    package = task / f"commissioning-package-{args.attempt}"
    package.mkdir(exist_ok=False)
    files = subprocess.check_output(
        ["git", "ls-files", "demos/lean_euler", "demos/lean_poisson"], cwd=source, text=True
    ).splitlines()
    names = []
    for name in files:
        destination = Path("commissioning") / Path(name).relative_to("demos")
        (package / destination).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / name, package / destination)
        names.append(destination.as_posix())
    protocol = "commissioning/PROTOCOL.txt"
    shutil.copy2(case / "PROTOCOL.txt", package / protocol)
    names.append(protocol)
    summary = "commissioning/checked/solver-formal.json"
    (package / summary).parent.mkdir(parents=True)
    shutil.copy2(
        source / "demos/lean_euler/nonlinear/record/solver/solver-formal.json", package / summary
    )
    names.append(summary)
    capabilities = task / f"capabilities-{args.attempt}"
    capabilities.mkdir()
    cap = json.loads((source / "capabilities/lean-4.24.0.json").read_text())
    cap["runtime_root"] = str(
        args.runtime_root.resolve() if args.runtime_root else source / ".runtime/lean-4.24.0"
    )
    put(capabilities / "lean-4.24.0.json", cap)
    registry = MachineRegistry(task / f"machines-{args.attempt}")
    registry.save(
        dict(
            id="uu-local",
            kind="local",
            root=str(task / f"execution-worker-{args.attempt}"),
            python=sys.executable,
            config=dict(
                cpus=12,
                memory_mb=32768,
                gpu_ids=[],
                max_jobs=6,
                execution_backend="bubblewrap",
                capabilities=[str(capabilities)],
            ),
        )
    )
    registry.prepare("uu-local")
    pool = registry.freeze(["uu-local"])
    put(task / "operator/execution-pool.json", pool)
    program = "commissioning/lean_euler/nonlinear/check_solver.py"
    spec = dict(
        schema_version="0.1.0",
        name="nonlinear-euler-lean-100-commissioning",
        description="Prior human-directed examples and checked nonlinear foundations",
        capability="lean-4.24.0--at-uu-local",
        program_path=program,
        validated_argv=[program, "--output", "commissioning/checked"],
        validation_summary_path=summary,
        protocol_path=protocol,
        operator_validation=(
            "The source-identical local assembled proof passed all 100 selected theorem "
            "audits. The separate remote readiness receipt must also pass before launch. "
            "All supplied outputs are prior commissioning context, not campaign discoveries."
        ),
        limitations=[
            "No completed continuum solver accuracy or work-optimality theorem.",
            "Smooth existence, trajectory bounds and actual initialization remain open.",
            "Exact-real proofs do not certify the floating-point implementation.",
            "Earlier Poisson/caching/analytic-flow examples have separate scopes.",
        ],
        files=names,
    )
    manifest = package / "guided_commission.json"
    put(manifest, spec)
    frozen = MVPGuidedCommissioningPackage.read(manifest)
    lab = ResearchService.create(
        task / f"readiness-{args.attempt}",
        "Reproduce commissioning only; no new research conclusion.",
        execution_pool=pool,
        wall_seconds=1200,
        artifact_policy="eager",
        execution_backend="bubblewrap",
    )
    lab.install_guidance(manifest)
    proof = lab.reproduce_anchor(timeout=600, resources={"cpus": 1, "memory_mb": 8192, "gpus": 0})
    prefix = "commissioning/lean_euler/nonlinear/"
    numeric = lab.run(
        prefix + "validate_initial_excess.py",
        ["--output", "initial-check"],
        inputs=[prefix + x for x in ["entropy_candidate.py", "finite_volume.py", "contract.json"]],
        outputs=["initial-check/initial-excess-validation.json"],
        stage="exploration",
        timeout=180,
        resources={"cpus": 1, "memory_mb": 2048, "gpus": 0},
    )
    while True:
        lab.status()
        receipts = [lab._read("experiments", r["id"]) for r in [proof, numeric]]
        if all(r["status"] not in {"queued", "running"} for r in receipts):
            break
        if time.time() >= lab.manifest["deadline"]:
            lab.cancel_active()
            raise TimeoutError("Commissioning exceeded its separate readiness budget")
        time.sleep(1)
    models = json.loads((task / "operator/model-preflight/results.json").read_text())
    ready = dict(
        status="passed"
        if all(r["status"] == "succeeded" for r in receipts) and all(r["ready"] for r in models)
        else "failed",
        package_sha256=frozen.package_sha256,
        package=str(manifest),
        registry=str(registry.root),
        jobs=[{"id": r["id"], "status": r["status"]} for r in receipts],
        models=models,
        scientific_evidence_eligible=False,
        source_commit=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=source, text=True
        ).strip(),
    )
    put(task / f"operator/readiness-{args.attempt}.json", ready)
    if ready["status"] == "passed":
        put(task / "operator/readiness.json", ready)
    print(json.dumps(ready, indent=2))
    if ready["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
