"""Post-hoc same-packet numerical/runtime comparison, never policy training data."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import time
from pathlib import Path

from simjecture_monitor.events import digest, put

from conjecture_solver.research_helper_runtime import process_stat


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--study", type=Path, action="append", required=True)
    args = parser.parse_args()
    root, repo = args.root.resolve(), Path.cwd()
    root.mkdir(parents=True, exist_ok=False)
    packets, references, selected, missing = [], [], [], []
    for study in args.study:
        study = study.resolve()
        for result in sorted(load(study / "RESULTS.json"), key=lambda r: r["job"]["root"]):
            job = result["job"]
            trial = study / job["root"]
            candidates = [load(p) for p in sorted((trial / "monitor").glob("decision-*.json"))]
            candidates = [d for d in candidates if d.get("decision") and not d.get("error")]
            parked = [
                d
                for d in candidates
                if d["packet"]["state"].get("host_state", {}).get("worker_parked")
            ]
            if job["case"] == "adapter":
                parked = [
                    d
                    for d in parked
                    if any(
                        not r["process_alive"]
                        and r["returncode"] is not None
                        and r["reported_status"] == "running"
                        for r in d["packet"]["state"]["host_state"]["async_completion"]
                    )
                ]
            eligible = parked or (candidates[:1] if job["case"] == "healthy" else [])
            if not eligible:
                missing.append(
                    dict(study=str(study), job=job, reason="No eligible recorded packet")
                )
                continue
            chosen = eligible[0]
            selected.append(
                dict(
                    study=str(study),
                    job=job,
                    index=len(packets),
                    packet_sha256=chosen["packet"]["packet_sha256"],
                    received_at=chosen["received_at"],
                    selected_record_sha256=digest(chosen),
                    selection="first eligible parked record; healthy falls back to first record",
                )
            )
            packets.append(chosen["packet"])
            references.append(chosen["decision"])
    put(
        root / "SELECTION.json",
        dict(
            created_at=time.time(),
            source_revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            selected=selected,
            missing=missing,
            scope=(
                "Post-hoc contradiction/healthy packets; finite/action drift check, "
                "not a held-out policy evaluation"
            ),
        ),
    )
    put(root / "packets.json", packets)
    put(root / "reference.json", references)
    wrapper = root / "benchmark.py"
    wrapper.write_text(
        "import sys,runpy,torch\ntorch.set_num_threads(2)\n"
        "free,total=torch.cuda.mem_get_info()\nassert free>11*1024**3\n"
        "torch.cuda.set_per_process_memory_fraction(.6)\n"
        'script=sys.argv.pop(1)\nrunpy.run_path(script,run_name="__main__")\n'
    )
    for profile, environment in [("reference", "model-env"), ("fla-prefill", "model-fast-env")]:
        command = [
            str(repo / "artifacts" / environment / "bin/python"),
            str(wrapper),
            str(repo / "packages/simjecture-monitor/scripts/benchmark_local.py"),
            "--checkpoint",
            str(repo / "artifacts/models/Decision-verified"),
            "--packets",
            str(root / "packets.json"),
            "--reference",
            str(root / "reference.json"),
            "--output",
            str(root / profile),
        ]
        if profile == "fla-prefill":
            command += ["--kernel-profile", profile]
        env = dict(
            os.environ,
            PYTHONPATH=str(repo / "packages/simjecture-monitor/src"),
            TRITON_CACHE_DIR=str(repo / "artifacts/kernel-live-20261024/triton-cache"),
        )
        with (root / (profile + ".log")).open("w") as log:
            child = subprocess.Popen(
                command, env=env, stdout=log, stderr=log, start_new_session=True
            )
            put(
                root / (profile + "-process.json"),
                dict(identity=process_stat(child.pid), command=command),
            )
            try:
                code = child.wait(timeout=900)
            except subprocess.TimeoutExpired:
                child.terminate()
                try:
                    child.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                code = 124
        put(root / (profile + "-exit.json"), dict(returncode=code, ended_at=time.time()))
        if code:
            raise RuntimeError("Replay benchmark failed; retained outputs: " + profile)
    first = load(root / "reference/predictions.json")
    second = load(root / "fla-prefill/predictions.json")
    assert len(first) == len(second) == len(packets) * 2
    rows = []
    for a, b in zip(first, second, strict=True):
        x, y = a["prediction"], b["prediction"]
        assert x["prompt_sha256"] == y["prompt_sha256"]
        for probabilities in [x["probabilities"], y["probabilities"]]:
            assert all(math.isfinite(p) for p in probabilities.values())
            assert abs(sum(probabilities.values()) - 1) < 1e-5
        rows.append(
            dict(
                packet_index=a["packet_index"],
                repetition=a["repetition"],
                reference_choice=x["choice"],
                fast_choice=y["choice"],
                choices_agree=x["choice"] == y["choice"],
                maximum_probability_difference=max(
                    abs(p - y["probabilities"][k]) for k, p in x["probabilities"].items()
                ),
            )
        )
    put(
        root / "COMPARISON.json",
        dict(
            packets=len(packets),
            comparisons=len(rows),
            rows=rows,
            choices_agree=sum(r["choices_agree"] for r in rows),
            maximum_probability_difference=max(r["maximum_probability_difference"] for r in rows),
        ),
    )


if __name__ == "__main__":
    main()
