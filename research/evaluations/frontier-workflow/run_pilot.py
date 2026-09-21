"""Real GLM workflow pilot. Creates isolated campaigns, no mocks or invented results."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from conjecture_solver.campaign_kernel import CampaignKernel
from conjecture_solver.literature import LiteratureSearchRecord, LiteratureSearchStatus
from conjecture_solver.models import utc_now
from conjecture_solver.mvp_agent import MVPAgentConfig

TASKS = {
    "euler": (
        "For explicit Euler y[n+1]=(1-1/N)*y[n] applied to y'=-y, y(0)=1 at t=1, "
        "E_N=abs(y[N]-exp(-1)). For every N in {16,32,64,128}, the refinement ratio "
        "R_N=E_N/E_(2N) lies in [3.5,4.5].",
        "Compute E_N and E_(2N) and R_N at all four specified N. If the claim is "
        "false, propose the smallest useful repair that describes the convergence "
        "order on this same finite set, then test it. Do not simply drop offending "
        "cases or assert a universal convergence theorem from finite samples.",
    ),
    "midpoint": (
        "For the implicit-midpoint harmonic-oscillator update q_new=((1-h*h/4)*q+h*p)/(1+h*h/4), "
        "p_new=(-h*q+(1-h*h/4)*p)/(1+h*h/4), q(0)=1,p(0)=0, for h in {0.2,0.1,0.05} "
        "and every computed step to T=20, abs((q*q+p*p)/2-0.5) is at most 1e-11 "
        "in IEEE binary64 arithmetic.",
        "Test all three step sizes and every step through T=20. Use the old q,p "
        "simultaneously for both updates. Quantify maximum energy error and "
        "explain the finite-precision and finite-domain scope. Do not generalize "
        "to arbitrary nonlinear oscillators or all floating-point implementations.",
    ),
}


class TaskDefinitionLiterature:
    identity = {
        "name": "self-contained-benchmark-definition",
        "version": "1",
        "providers": ["operator"],
    }

    def search(self, *, hypothesis, query, purpose, max_results):
        return LiteratureSearchRecord(
            id="literature_search_" + hashlib.sha256(hypothesis.encode()).hexdigest()[:16],
            hypothesis_sha256=hashlib.sha256(hypothesis.encode()).hexdigest(),
            query=query,
            purpose=purpose,
            requested_results=max_results,
            status=LiteratureSearchStatus.UNAVAILABLE,
            provider_status={
                "operator": "Self-contained mathematical task; no external retrieval."
            },
            searched_at=utc_now(),
        )


def prepare(root, task, workflow):
    directory = root / f"{task}-{workflow}"
    directory.mkdir(parents=True, exist_ok=False)
    campaign = directory / "campaign"
    hypothesis, detail = TASKS[task]
    config = MVPAgentConfig(
        max_wall_seconds=900,
        max_command_seconds=120,
        max_workspace_bytes=1024**3,
        max_file_bytes=64 * 1024**2,
        require_independent_contract_review=True,
    )
    k = CampaignKernel.open(
        workspace=campaign,
        hypothesis=hypothesis,
        config=config,
        literature_search=TaskDefinitionLiterature(),
    )
    k.execute(
        dict(
            action="search_literature",
            query="operator mathematical task definition",
            purpose="Record self-contained benchmark scope, no novelty or absence claim.",
            max_results=1,
            research_note="Same supplied definition and startup policy in both conditions.",
        ),
        iteration=0,
    )
    task_text = f'''Conduct this numerical investigation using Simjecture. The hypothesis in
snapshot is the immutable task. {detail}
This is a finite self-contained mathematical benchmark; no external literature is
needed and the host recorded that fact. Do not inspect harness implementation files
or unrelated projects. Use only the tool schemas and error receipts to operate it.
Develop calculations before proposing evidence contracts when useful, but do not
promote exploratory results into evidence. Use run_python through the official
adapter for recorded computations. No installed external solver is needed; Python's
standard library is sufficient. Evidence contracts and any claimed qualification
need independent host review before they authorize evidence. Request reviews as
instructed by the supervisor, and end that turn so it can process the request.
After qualification/contract approval generate fresh numerical evidence and request
independent scientific adjudication. If falsified, preserve the original claim and
test an explicit repair. Do not finish on your own or bypass the review gates.
Write a calculation-generated benchmark-result.json with task="{task}", a rows array,
and scope/limitations. Euler rows: N (integer), E_N, E_2N, ratio (numbers). Midpoint
rows: h, steps (integer), max_energy_error (number). This schema is for external
measurement of correctness, not an instruction about which conclusion to reach.
Preserve scripts, raw numerical output and provenance. Do not modify supplied inputs
or campaign internals through native tools. Do not repeat tiny calculations merely
to consume time; progress toward an accepted, appropriately scoped conclusion.
'''
    instructions = directory / "instructions.txt"
    instructions.write_text(task_text)
    (campaign / "operator_input").mkdir(exist_ok=True)
    (campaign / "operator_input/scientific_protocol.txt").write_text(hypothesis + "\n" + task_text)
    return directory, campaign, instructions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--implementation-source", type=Path)
    parser.add_argument("--executable", default="codex-glm")
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    implementation = (
        args.implementation_source.resolve()
        if args.implementation_source
        else Path(__file__).resolve().parents[3] / "src"
    ) / "conjecture_solver"
    record = {
        "requested_model": "glm-5.3",
        "wall_seconds_per_run": 900,
        "session_seconds": 180,
        "implementation_hashes": {
            f.name: hashlib.sha256(f.read_bytes()).hexdigest()
            for f in [
                implementation / "agent_supervisor.py",
                implementation / "role_assignments.py",
                implementation / "scientific_review.py",
                implementation / "campaign_kernel.py",
            ]
        },
        "task_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "runs": [],
    }
    queue = [
        ("euler", "frontier"),
        ("euler", "structured"),
        ("midpoint", "structured"),
        ("midpoint", "frontier"),
    ]
    running = []
    while queue or running:
        while queue and len(running) < 2:
            task, workflow = queue.pop(0)
            directory, campaign, instructions = prepare(root, task, workflow)
            cmd = [
                sys.executable,
                "-m",
                "conjecture_solver.agent_supervisor",
                "--campaign",
                str(campaign),
                "--state-dir",
                str(directory / "supervisor"),
                "--instructions-file",
                str(instructions),
                "--backend",
                "codex-glm",
                "--executable",
                args.executable,
                "--workflow",
                workflow,
                "--model",
                "glm-5.3",
                "--judge-model",
                "glm-5.3",
                "--wall-seconds",
                "900",
                "--turn-seconds",
                "180",
            ]
            env = dict(os.environ, PYTHONPATH=str(implementation.parent))
            with (
                (directory / "stdout.log").open("w") as out,
                (directory / "stderr.log").open("w") as err,
            ):
                child = subprocess.Popen(
                    cmd, cwd=directory, env=env, stdout=out, stderr=err, start_new_session=True
                )
            entry = dict(
                task=task,
                workflow=workflow,
                path=str(directory),
                pid=child.pid,
                launched_at=time.time(),
                command=cmd,
            )
            record["runs"].append(entry)
            running.append((child, entry))
            print("Started", task, workflow, child.pid, flush=True)
        for child, entry in running[:]:
            rc = child.poll()
            if rc is not None:
                entry.update(returncode=rc, finished_at=time.time())
                running.remove((child, entry))
                print("Finished", entry["task"], entry["workflow"], rc, flush=True)
        (root / "launch.json").write_text(json.dumps(record, indent=2) + "\n")
        if running:
            time.sleep(1)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
