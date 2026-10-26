"""Run a configured QE instrument through real Simjecture skill/capability discovery.

Model-free integration qualification; does not start an autonomous hypothesis study.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import shutil
from pathlib import Path

from conjecture_solver.mvp_agent import BubblewrapSandbox, MVPAgentConfig, MVPArtifactInput
from conjecture_solver.mvp_skills import MVPCapabilityRegistry, MVPSkillCatalog


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--pseudo-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile")
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--confirmation", type=Path, required=True)
    parser.add_argument("--mode", choices=("full", "scf-only"))
    parser.add_argument("--smoke", action="store_true", default=None)
    parser.add_argument("--convergence", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--wall-seconds", type=int)
    parser.add_argument("--memory-mib", type=int)
    parser.add_argument("--workspace-mib", type=int)
    args = parser.parse_args()
    functions = runpy.run_path(
        str(args.project / "skills/quantum-espresso/examples/dft_workflow.py")
    )
    if args.smoke and args.mode not in (None, "scf-only"):
        parser.error("Conflicting workflow modes")
    stored = functions["read_plan"](args.plan)
    mode = "scf-only" if args.smoke else (args.mode or stored["mode"])
    cfg = functions["load_case"](args.case, args.profile, mode)
    approved, consent = functions["require_confirmation"](
        cfg,
        args.protocol,
        args.plan,
        args.confirmation,
        mode,
        args.convergence,
        execution_context="simjecture",
    )
    effective = approved["effective_case"]
    for field, value in effective["launcher_limits"].items():
        if getattr(args, field) is not None and getattr(args, field) != value:
            parser.error(f"{field} differs from confirmed plan; preview and reconfirm")
        setattr(args, field, value)
    args.smoke = approved["mode"] == "scf-only"
    args.convergence = approved["convergence"]
    output = args.output.resolve()
    if output.exists():
        parser.error("Use a fresh output directory")
    skills = MVPSkillCatalog.discover(args.project / "skills")
    capability = "quantum-espresso-7.4"
    registry = MVPCapabilityRegistry.discover(args.project / "capabilities", names=(capability,))
    skill = skills.read("quantum-espresso", None, max_chars=30000)
    descriptor, source = skills.read_bytes(
        "quantum-espresso", "examples/dft_workflow.py", max_bytes=256 * 1024
    )
    if (
        capability not in registry
        or capability
        not in next(x for x in skills.descriptors() if x["name"] == "quantum-espresso")[
            "capability_names"
        ]
    ):
        raise RuntimeError("Skill/capability binding missing")
    if args.memory_mib < 256 or args.workspace_mib < 64:
        parser.error("Choose at least 256 MiB memory and 64 MiB workspace")
    functions["verify_pseudos"](effective, args.pseudo_dir)
    output.mkdir(parents=True)
    # Durable replay must discover only the selected, installed instrument.
    # Other repository manifests may describe optional runtimes not installed here.
    replay = output / "capabilities"
    replay.mkdir()
    config = json.loads((args.project / "capabilities" / f"{capability}.json").read_text())
    config["runtime_root"] = str(registry.get(capability).runtime_root)
    (replay / f"{capability}.json").write_text(json.dumps(config, indent=2) + "\n")
    workspace = output / "workspace"
    workspace.mkdir()
    (workspace / "workflow.py").write_bytes(source)
    shutil.copy2(args.case, workspace / "case.json")
    shutil.copy2(args.protocol, workspace / "PROTOCOL.md")
    shutil.copy2(args.plan, workspace / "plan.json")
    shutil.copy2(args.confirmation, workspace / "confirmation.json")
    (workspace / "effective_case.json").write_text(json.dumps(effective, indent=2) + "\n")
    (workspace / "pseudo").mkdir()
    for s in effective["species"]:
        shutil.copy2(args.pseudo_dir / s["pseudo"], workspace / "pseudo" / s["pseudo"])
    argv = (
        "workflow.py",
        "run",
        "--case",
        "case.json",
        "--pseudo-dir",
        "pseudo",
        "--output",
        "result",
        "--protocol",
        "PROTOCOL.md",
        "--plan",
        "plan.json",
        "--confirmation",
        "confirmation.json",
    )
    if args.profile:
        argv += ("--profile", args.profile)
    if args.smoke:
        argv += ("--smoke",)
    if args.convergence:
        argv += ("--convergence",)
    record = {
        "scope": "model-free exploratory integration qualification",
        "approved_plan_sha256": approved["plan_sha256"],
        "confirmation": consent,
        "scientific_evidence_eligible": False,
        "argv": argv,
        "skill": skill,
        "workflow_resource": descriptor,
        "capabilities": registry.descriptors(),
        "case_sha256": sha(args.case),
        "protocol_sha256": sha(args.protocol),
        "resource_limits": {
            "memory_mib": args.memory_mib,
            "workspace_mib": args.workspace_mib,
            "omp_threads": 1,
        },
    }
    (output / "discovery.json").write_text(json.dumps(record, indent=2) + "\n")
    sandbox = BubblewrapSandbox(
        workspace,
        MVPAgentConfig(
            execution_backend="bubblewrap",
            max_wall_seconds=args.wall_seconds,
            max_command_seconds=args.wall_seconds,
            max_workspace_bytes=args.workspace_mib * 1024**2,
            max_file_bytes=min(128, args.workspace_mib) * 1024**2,
            max_memory_bytes=args.memory_mib * 1024**2,
        ),
        registry,
    )
    inputs = tuple(
        MVPArtifactInput(path=p.relative_to(workspace).as_posix(), sha256=sha(p))
        for p in sorted(workspace.rglob("*"))
        if p.is_file() and p.name != "workflow.py"
    )
    result = sandbox.run_capability(
        capability,
        argv,
        input_artifacts=inputs,
        program_path="workflow.py",
        program_sha256=sha(workspace / "workflow.py"),
        timeout_seconds=args.wall_seconds,
    )
    (output / "execution_receipt.json").write_text(result.model_dump_json(indent=2) + "\n")
    print(result.model_dump_json(indent=2))
    if result.returncode != 0:
        return 1
    summary = json.loads((workspace / "result/summary.json").read_text())
    if (
        summary["status"] != "passed"
        or summary.get("approved_plan_sha256") != approved["plan_sha256"]
    ):
        raise RuntimeError("Workflow did not pass declared checks")
    # Produce a guided package only after the exact command really completed.
    package = output / "guided"
    package.mkdir()
    for name in (
        "workflow.py",
        "case.json",
        "PROTOCOL.md",
        "plan.json",
        "confirmation.json",
        "effective_case.json",
    ):
        shutil.copy2(workspace / name, package / name)
    shutil.copytree(workspace / "pseudo", package / "pseudo")
    (package / "result").mkdir()
    shutil.copy2(workspace / "result/summary.json", package / "result/summary.json")
    spec = {
        "schema_version": "0.1.0",
        "name": "qe-configured-dft-anchor-v1",
        "description": (
            "SCF-only QE smoke reproduced through Simjecture"
            if args.smoke
            else "QE relaxation and independent DOS/band branches reproduced through Simjecture"
        ),
        "capability": capability,
        "program_path": "workflow.py",
        "validated_argv": argv,
        "validation_summary_path": "result/summary.json",
        "protocol_path": "PROTOCOL.md",
        "operator_validation": (
            "The exact command completed through the registered QE capability "
            "in the Bubblewrap experiment sandbox. See the source-bound discovery "
            "and execution receipts; this is exploratory instrument commissioning."
        ),
        "limitations": [
            "No autonomous research claim or held-out evidence.",
            "Material, functional, pseudopotential and sampling are specific to the supplied case.",
            (
                "Runtime availability, parser tests, calculation execution "
                "and convergence are separate checks."
            ),
        ],
        "files": [
            "workflow.py",
            "case.json",
            "PROTOCOL.md",
            "plan.json",
            "confirmation.json",
            "effective_case.json",
            "result/summary.json",
        ]
        + [f"pseudo/{s['pseudo']}" for s in effective["species"]],
    }
    (package / "guided_commission.json").write_text(json.dumps(spec, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
