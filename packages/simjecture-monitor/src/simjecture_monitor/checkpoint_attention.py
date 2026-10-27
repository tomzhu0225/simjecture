"""Scientific attention inputs for quiescent, verified public checkpoints.

This is a development profile for a single proposal before a real continuation.
It does not reconstruct private provider state or expose future outcomes. The
predeclared public transcript window is eight records, with explicit excerpts.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from . import attention_contract as core
from . import attention_support as protocol
from .checkpoint import inventory
from .decision_interface import scientific_request
from .events import digest


def from_checkpoint(checkpoint, *, packet_id, clock_id, captured_ms, sequence):
    checkpoint = Path(checkpoint)
    manifest = json.loads((checkpoint / "checkpoint.json").read_text())
    original = {k: v for k, v in manifest.items() if not k.endswith("_sha256")}
    if digest(original) != manifest["common_prefix_sha256"]:
        raise ValueError("Checkpoint manifest hash mismatch")
    if inventory(checkpoint / "artifacts") != manifest["artifacts"]:
        raise ValueError("Checkpoint artifact hash mismatch")
    raw = json.loads((checkpoint / "observation.json").read_text())
    if digest(raw["state"]) != raw["packet_sha256"]:
        raise ValueError("Public checkpoint observation hash mismatch")
    # Observation events must actually come from the frozen public transcript.
    if [e["body"] for e in raw["state"]["events"]] != manifest["public_transcript"][-8:]:
        raise ValueError("Observation is not the checkpoint's public transcript window")
    if raw["state"]["task"] != (checkpoint / "artifacts/TASK.txt").read_text():
        raise ValueError("Observation task differs from the frozen task artifact")
    evidence = []

    def add(role, text, *, origin, source_sha256, kind="receipt"):
        excerpted = len(text) > 1600
        if excerpted:
            text = text[:780] + "\n[excerpt]\n" + text[-780:]
        evidence.append(
            core.Evidence(
                id=role,
                source=role,
                source_role=role,
                source_sha256=source_sha256,
                kind=kind,
                # Age of this fresh read of a frozen record, not its historic event.
                age_ms=0,
                origin=origin,
                content=text,
                excerpted=excerpted,
            )
        )

    task = raw["state"]["task"]
    task_hash = hashlib.sha256(task.encode()).hexdigest()
    for index, start in enumerate(range(0, len(task), 1400)):
        add(
            f"declared_task_part_{index}",
            task[start : start + 1400],
            origin="operator",
            source_sha256=task_hash,
            kind="expectation",
        )
    for index, event in enumerate(raw["state"]["events"]):
        body = event["body"]
        add(
            f"public_record_{index}",
            json.dumps(body, sort_keys=True),
            origin="host" if body.get("provenance", "").startswith("host") else "worker",
            source_sha256=digest(body),
            kind="tool_result",
        )
    for name, role, owner in [
        ("harness/bridge.py", "registered_component", "protected"),
        ("analysis_probe.py", "worker_analysis", "worker"),
        ("control.json", "prior_control_report", "worker"),
    ]:
        path = checkpoint / "artifacts" / name
        if not path.exists():
            if name == "control.json":
                continue
            raise ValueError("Required checkpoint source is missing: " + name)
        add(
            role,
            json.dumps(dict(path=name, owner=owner, content=path.read_text())),
            origin="host" if owner == "protected" else "worker",
            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    criteria = manifest["criteria"]
    return protocol.Observation(
        schema_version=protocol.VERSION,
        packet_id=packet_id,
        subject_id="public-checkpoint-worker",
        operation_id="scientific-continuation",
        incident_id="checkpoint-attention",
        clock_id=clock_id,
        captured_ms=captured_ms,
        sequence=sequence,
        state_revision=1,
        task="Assess attention before the worker resumes. The complete declared task is "
        "provided in consecutive declared_task_part evidence records.",
        phase="paused_public_checkpoint",
        scientific_contract=[
            "The worker will resume from these actual saved artifacts and public records.",
            "A correctly reported negative physical check is a valid scientific outcome.",
            f"Preserve field tolerance {criteria['field_tolerance']} and charge tolerance "
            f"{criteria['charge_tolerance']}.",
            "The worker may repair analysis_probe.py. Protected bridge.py changes need "
            "an independent judge and a scoped host grant.",
            "These are fresh reads of frozen records. Historical tool errors are not proof "
            "of a current blocker; compare them with the current source and later results.",
            "This is an attention proposal, not a scientific acceptance decision.",
        ],
        worker_state="parked",
        workflow_state="running",
        assistance="none",
        timing=core.Timing(
            phase_elapsed_ms=None,
            progress_age_ms=None,
            heartbeat_age_ms=None,
            quiet_state="none",
            retries_remaining=None,
            budget_remaining_ms=650000,
        ),
        evidence=evidence,
        questions=[],
        retrieval_history=[],
        retrieval_history_complete=True,
        missing_channels=[],
    )


def request_row(packet):
    view = protocol.pack(packet, len, token_counter_id="assembly:characters", budget_tokens=100000)
    row = scientific_request(packet, view)
    row["observation"] = packet.model_dump()
    row["profile"] = "public-checkpoint-five-field/v0.2-development"
    return row
