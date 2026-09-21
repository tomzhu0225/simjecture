"""Launch real controlled workflow trials; preserve source and observation receipts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from conjecture_solver.campaign_kernel import CampaignKernel
from conjecture_solver.mvp_agent import MVPAgentConfig
from conjecture_solver.mvp_skills import MVPCapabilityRegistry
from conjecture_solver.research_service import ResearchService

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location(
    "oldpilot", HERE.parent / "frontier-workflow/run_pilot.py"
)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)


def prepare(root, task, workflow, budget, source, capabilities):
    directory = root / f"{task}-{workflow}"
    directory.mkdir()
    if task == "plasma":
        hypothesis = (HERE / "assets/plasma-hypothesis.txt").read_text()
        detail = (HERE / "assets/plasma-protocol.md").read_text()
        schema = "Use the precise plasma result schema in the supplied physical protocol."
    else:
        hypothesis, detail = old.TASKS[task]
        schema = (
            "Each row must contain N, E_N, E_2N, ratio; exactly the four original N values."
            if task == "euler"
            else (
                "Each row must contain h, steps, max_energy_error; "
                "exactly the three original h values."
            )
        )
    instructions = f'''Investigate this finite claim: {hypothesis}
{detail}
Write runnable calculation/analysis source and calculation-generated benchmark-result.json
with task="{task}", rows, disposition, conclusion and limitations. {schema}
Include only this task's requested rows. Retain raw outputs and executable source.
If the claim is falsified, propose a scientifically meaningful bounded repair,
write benchmark-plan.json with its statement, acceptance criteria and exact planned
test commands BEFORE executing its validation, and preserve fresh validation output.
Do not define a bound as the observed minimum/maximum and test it on those same data.
For a repaired conclusion, include repair.statement, repair.acceptance and
repair.validation_rows in the final result. Original failures must remain visible.
Follow the selected workflow's recording and independent review rules. Native tools
remain available. Do not inspect other trials, reference results, harness source or
unrelated projects. This is self-contained; no external literature is needed.
You have {budget} seconds. End when the chosen workflow's valid completion conditions
are met; do not repeat calculations merely to consume time.
'''
    instructions_path = directory / "instructions.txt"
    instructions_path.write_text(instructions)
    env = dict(
        os.environ,
        PYTHONPATH=str(source),
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        OMPI_MCA_hwloc_base_binding_policy="none",
    )
    wrapper = REPO / "research/evaluations/frontier-workflow/accounted_codex_glm.py"
    if workflow == "plain":
        work = directory / "research"
        work.mkdir()
        response = directory / "supervisor/turn-00001"
        response.mkdir(parents=True)
        cmd = [
            str(wrapper),
            "exec",
            "--model",
            "glm-5.3",
            "--json",
            "--skip-git-repo-check",
            "--dangerously-bypass-approvals-and-sandbox",
            instructions,
        ]
        env["FLASH_EXECUTABLE"] = (
            "/home/tomzhu0225/src/simjecture/.runtime/flash-driven-sheet-mhd-4.8-r2/bin/flash4"
        )
        out = response / "response.json"
        err = response / "stderr.log"
    elif workflow == "lean":
        campaign = directory / "campaign"
        service = ResearchService.create(
            campaign,
            hypothesis,
            wall_seconds=budget,
            capabilities=capabilities if task == "plasma" else None,
        )
        work = service.work
        cmd = [
            sys.executable,
            "-m",
            "conjecture_solver.research_supervisor",
            "--campaign",
            str(campaign),
            "--instructions-file",
            str(instructions_path),
            "--backend",
            "codex-glm",
            "--model",
            "glm-5.3",
            "--executable",
            str(wrapper),
            "--wall-seconds",
            str(budget),
            "--turn-seconds",
            "600",
        ]
        out = directory / "stdout.log"
        err = directory / "stderr.log"
    else:
        campaign = directory / "campaign"
        config = MVPAgentConfig(
            max_wall_seconds=budget,
            max_command_seconds=1200 if task == "plasma" else 120,
            max_workspace_bytes=8 * 1024**3,
            max_file_bytes=512 * 1024**2,
            require_independent_contract_review=True,
        )
        kwargs = (
            {"capabilities": MVPCapabilityRegistry.discover(capabilities)}
            if task == "plasma"
            else {}
        )
        k = CampaignKernel.open(
            workspace=campaign,
            hypothesis=hypothesis,
            config=config,
            literature_search=old.TaskDefinitionLiterature(),
            **kwargs,
        )
        k.execute(
            dict(
                action="search_literature",
                query="operator finite benchmark definition",
                purpose="Record supplied finite model and benchmark scope.",
                max_results=1,
                research_note="Same task definition across workflows.",
            ),
            iteration=0,
        )
        (campaign / "operator_input").mkdir(exist_ok=True)
        (campaign / "operator_input/scientific_protocol.txt").write_text(instructions)
        work = campaign / "workspace"
        cmd = [
            sys.executable,
            "-m",
            "conjecture_solver.agent_supervisor",
            "--campaign",
            str(campaign),
            "--state-dir",
            str(directory / "supervisor"),
            "--instructions-file",
            str(instructions_path),
            "--backend",
            "codex-glm",
            "--model",
            "glm-5.3",
            "--executable",
            str(wrapper),
            "--workflow",
            workflow,
            "--wall-seconds",
            str(budget),
            "--turn-seconds",
            "600",
        ]
        out = directory / "stdout.log"
        err = directory / "stderr.log"
    if task == "plasma":
        shutil.copy2(HERE / "assets/flash_case.py", work / "flash_case.py")
        (directory / "asset-location.txt").write_text(str(work / "flash_case.py"))
        # Exact resource location is transport context, not a changed scientific task.
        note = (
            f"\nSupplied FLASH launcher: {work}/flash_case.py. "
            "Read it for its CLI and HDF5 fields.\n"
        )
        if workflow == "plain":
            cmd[-1] += note
        else:
            instructions_path.write_text(instructions + note)
    return directory, work, cmd, env, out, err


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--tasks", nargs="+", default=["euler", "midpoint"])
    p.add_argument(
        "--workflows",
        nargs="+",
        choices=["plain", "structured", "frontier", "lean"],
        default=["plain", "structured", "frontier", "lean"],
    )
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--capabilities", type=Path)
    a = p.parse_args()
    root = a.root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = a.source.resolve()
    manifest = {
        "model": "glm-5.3",
        "runs": [],
        "source_hashes": {
            str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source.rglob("*.py")
        },
        "observations": [],
    }
    queue = [(task, w) for task in a.tasks for w in a.workflows]
    running = []
    observed = set()
    while queue or running:
        while queue and len(running) < a.concurrency:
            task, workflow = queue.pop(0)
            budget = 3600 if task == "plasma" else 900
            d, work, cmd, env, out, err = prepare(
                root, task, workflow, budget, source, a.capabilities
            )
            with out.open("w") as o, err.open("w") as e:
                child = subprocess.Popen(
                    cmd,
                    cwd=work,
                    env=env,
                    stdout=o,
                    stderr=e,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
            entry = dict(
                task=task,
                workflow=workflow,
                path=str(d),
                pid=child.pid,
                launched_at=time.time(),
                budget_seconds=budget,
            )
            manifest["runs"].append(entry)
            running.append((child, entry))
            print("Started", task, workflow, flush=True)
        for child, entry in running[:]:
            if (
                child.poll() is None
                and time.time() > entry["launched_at"] + entry["budget_seconds"] + 15
            ):
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                entry["outer_timeout"] = True
            for pattern in ["benchmark-plan.json", "benchmark-result.json"]:
                for path in Path(entry["path"]).rglob(pattern):
                    if path.is_file():
                        raw = path.read_bytes()
                        digest = hashlib.sha256(raw).hexdigest()
                        key = (str(path), digest)
                        if key not in observed:
                            observed.add(key)
                            manifest["observations"].append(
                                dict(
                                    observed_at=time.time(),
                                    run=Path(entry["path"]).name,
                                    path=str(path.relative_to(root)),
                                    sha256=digest,
                                    content=raw.decode(errors="replace")[:262144],
                                )
                            )
            if child.poll() is not None:
                entry.update(returncode=child.returncode, finished_at=time.time())
                running.remove((child, entry))
                print("Finished", entry["task"], entry["workflow"], child.returncode, flush=True)
        temp = root / "launch.tmp"
        temp.write_text(json.dumps(manifest, indent=2) + "\n")
        temp.replace(root / "launch.json")
        if running:
            time.sleep(2)


if __name__ == "__main__":
    main()
