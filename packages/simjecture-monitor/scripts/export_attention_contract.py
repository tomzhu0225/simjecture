"""Export the draft contract and synthetic examples; optionally count actual tokens.

No model inference, training, native worker, simulation or GPU allocation occurs.
The examples exercise the interface; they are not a learned-policy evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from simjecture_monitor.attention_contract import (
    VERSION,
    Decision,
    Evidence,
    Measurement,
    Observation,
    Timing,
    pack,
    render,
    schemas,
    semantic_view,
)
from simjecture_monitor.events import put


def examples():
    entries = [
        (
            "solver_progress",
            "progress",
            "instrument",
            "Step 420 completed; physical time advanced.",
            [],
        ),
        ("storage_metadata", "expectation", "instrument", "Stored electric fields use V/m.", []),
        (
            "diagnostic_summary",
            "measurement",
            "instrument",
            "Measured values from the current run.",
            [
                Measurement(name="physical_time", value=6.67e-14, unit="s", validity="measured"),
                Measurement(
                    name="stored_peak_field", value=1.52e9, unit="V/m", validity="measured"
                ),
                Measurement(
                    name="reported_peak_field", value=1.52e9, unit="V/m", validity="measured"
                ),
                Measurement(
                    name="charge_residual",
                    value=8.35e-12,
                    unit="1",
                    validity="measured",
                    reference="Operator-declared original tolerance: 1e-11.",
                ),
            ],
        ),
    ]
    evidence = [
        Evidence(
            id=f"record-{i}",
            source=f"opaque-source-{i}",
            source_role=role,
            source_sha256=hashlib.sha256(content.encode()).hexdigest(),
            kind=kind,
            age_ms=1500,
            origin=origin,
            content=content,
            measurements=measurements,
        )
        for i, (role, kind, origin, content, measurements) in enumerate(entries)
    ]
    normal = Observation(
        schema_version=VERSION,
        packet_id="packet-0001",
        subject_id="subject-0001",
        operation_id="operation-0001",
        incident_id="incident-0001",
        clock_id="observer-boot-0001",
        captured_ms=100_000,
        sequence=1,
        state_revision=1,
        task="Complete two plasma controls and report independently checked diagnostics.",
        phase="diagnostic_aggregation",
        scientific_contract=[
            "Report the saved absolute peak electric field in V/m.",
            "Keep original tolerances unchanged. An accurately reported negative result is valid.",
        ],
        worker_state="parked",
        workflow_state="running",
        assistance="none",
        timing=Timing(
            phase_elapsed_ms=15000,
            progress_age_ms=1500,
            heartbeat_age_ms=500,
            quiet_state="none",
            retries_remaining=2,
            budget_remaining_ms=600000,
        ),
        evidence=evidence,
    )
    quiet = Observation.model_validate(
        normal.model_dump()
        | dict(
            packet_id="packet-0002",
            timing=dict(
                phase_elapsed_ms=40000,
                progress_age_ms=35160,
                heartbeat_age_ms=500,
                quiet_state="expired",
                quiet_remaining_ms=0,
                since_quiet_end_ms=142,
                retries_remaining=2,
                budget_remaining_ms=600000,
            ),
        )
    )
    quiet.evidence[0].content = "The current diagnostic phase declared 36 seconds of quiet work."
    quiet.evidence[0].source_sha256 = hashlib.sha256(quiet.evidence[0].content.encode()).hexdigest()
    history = Observation.model_validate(normal.model_dump() | dict(packet_id="packet-0003"))
    for i in range(12):
        content = (
            f"Earlier public tool read {i} completed. It did not change the current operation. " * 6
        )
        history.evidence.append(
            Evidence(
                id=f"old-{i}",
                source=f"old-source-{i}",
                source_role="tool_history",
                source_sha256=hashlib.sha256(content.encode()).hexdigest(),
                kind="tool_result",
                age_ms=(i + 1) * 6000,
                origin="worker",
                content=content,
                required=False,
            )
        )
    return {"progress": normal, "quiet-expiry": quiet, "long-history": history}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path)
    parser.add_argument("--tokenizer-python", type=Path, default=Path(sys.executable))
    parser.add_argument(
        "--check", action="store_true", help="Check committed schemas/examples without rewriting"
    )
    args = parser.parse_args()
    outputs = {f"schemas/{name}.schema.json": value for name, value in schemas().items()}
    outputs.update(
        {f"examples/{name}.json": packet.model_dump() for name, packet in examples().items()}
    )
    progress = examples()["progress"]
    outputs["examples/model-input.txt"] = render(
        semantic_view(progress, progress.evidence, 0), compact=False
    )
    outputs["examples/decision.json"] = Decision(
        schema_version=VERSION,
        packet_id="packet-0001",
        model_view_sha256=hashlib.sha256(
            render(
                semantic_view(examples()["progress"], examples()["progress"].evidence, 0),
                compact=False,
            ).encode()
        ).hexdigest(),
        policy_id="example-only-not-a-real-prediction",
        status="ok",
        action="recheck",
        basis="missing",
        evidence_basis="selected",
        evidence_ids=["record-2"],
    ).model_dump()
    for name, value in outputs.items():
        path = args.output / name
        if args.check:
            stored = path.read_text() if isinstance(value, str) else json.loads(path.read_text())
            if stored != value:
                raise ValueError("Contract export differs: " + name)
        elif isinstance(value, str):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value)
        else:
            put(path, value)
    if args.tokenizer:
        process = subprocess.Popen(
            [
                str(args.tokenizer_python.absolute()),
                str(Path(__file__).with_name("count_attention_tokens.py")),
                "--tokenizer",
                str(args.tokenizer.resolve()),
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            env=dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src")),
        )
        profile = "intern-decision-4b:route-only-chat:0.1-draft"
        rows = []
        try:
            first = process.stdout.readline()
            if not first:
                raise RuntimeError("Tokenizer failed before returning identity; inspect its stderr")
            identity = json.loads(first)

            def count(text):
                process.stdin.write(json.dumps(text) + "\n")
                process.stdin.flush()
                return json.loads(process.stdout.readline())

            for name, packet in examples().items():
                for compact in [False, True]:
                    for budget in [512, 1024, 2048, 4096, 16384]:
                        view = pack(
                            packet,
                            count,
                            token_counter_id=profile,
                            budget_tokens=budget,
                            compact=compact,
                        )
                        rows.append(
                            dict(example=name, **view.model_dump(exclude={"text", "aliases"}))
                        )
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        if process.returncode:
            raise RuntimeError("Tokenizer subprocess failed")
        put(
            args.output / "token-counts.json",
            dict(
                scope=(
                    "Synthetic development examples; actual tokenizer counts only. "
                    "No policy accuracy, latency or false-alert improvement measured."
                ),
                framing=(
                    "Existing pinned checkpoint chat template and route-only decision slot. "
                    "Grounded output prompting needs separate validation."
                ),
                identity=identity,
                rows=rows,
            ),
        )
        print(json.dumps([r for r in rows if r["budget_tokens"] in [512, 2048, 16384]], indent=2))
    else:
        print(
            f"{len(outputs)} contract exports verified"
            if args.check
            else f"{len(outputs)} contract exports written"
        )


if __name__ == "__main__":
    main()
