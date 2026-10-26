"""Admit a logged proposal and measure its real, bounded worker continuation.

This is a one-proposal public-checkpoint development profile. Two fresh verified
reads confirm that the paused artifacts still match; they do not establish a
new observation of a running worker or constitute a second independent model vote.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from simjecture_monitor import attention_support as protocol
from simjecture_monitor.checkpoint_attention import from_checkpoint, request_row
from simjecture_monitor.decision_interface import choice_from_answers
from simjecture_monitor.events import digest, put
from simjecture_monitor.reward import ContinuationOutcome, RewardWeights, utility


def admission(checkpoint, row):
    gate = protocol.AdmissionGate()
    records = []
    started = time.monotonic()
    for sequence in [1, 2]:
        if sequence == 2:
            time.sleep(max(0, 5.01 - (time.monotonic() - started)))
        now = int(time.monotonic() * 1000)
        packet = from_checkpoint(
            checkpoint,
            packet_id=f"{row['id']}-{sequence}",
            clock_id="checkpoint-process-" + str(os.getpid()),
            captured_ms=now,
            sequence=sequence,
        )
        fresh = request_row(packet)
        if (fresh["state"], fresh["questions"]) != (row["state"], row["questions"]):
            raise ValueError("Frozen public input changed after the model sampled its proposal")
        view = protocol.pack(
            packet, len, token_counter_id="assembly:characters", budget_tokens=100000
        )
        try:
            decision = protocol.bind_choice(
                packet,
                view,
                choice_from_answers(row["behavior"]["sampled_answers"]),
                policy_id="sampled-checkpoint-development",
            )
        except ValueError as error:
            return dict(
                action="defer",
                invalid_penalty=0.05,
                error=str(error),
                reads=records,
                overhead_seconds=time.monotonic() - started,
            )
        result = gate.evaluate(packet, view, decision, packet, now_ms=now)
        records.append(
            dict(submitted=packet.model_dump(), decision=decision.model_dump(), admission=result)
        )
        if result["disposition"] != "pending":
            break
    final = records[-1]["admission"]
    admitted = final["disposition"] == "admitted"
    legitimate_abstention = (
        decision.action in {"observe", "recheck"} and decision.support_kind == "none"
    )
    return dict(
        action=decision.action if admitted else "defer",
        invalid_penalty=0.0 if admitted or legitimate_abstention else 0.05,
        reads=records,
        overhead_seconds=time.monotonic() - started,
    )


def require_confirmed_solver_outcomes(root):
    """An unavailable transfer is not evidence that the sampled policy failed."""
    paths = list((Path(root) / "research/runs").glob("*/receipt.json"))
    if not paths:
        raise ValueError("No physical execution receipts; continuation is ineligible for training")
    for path in paths:
        receipt = json.loads(path.read_text())
        if receipt.get("status") not in {"succeeded", "failed", "timeout"} or receipt.get(
            "transport_status"
        ) in {"failed", "timeout"}:
            raise ValueError(
                "Unconfirmed solver transport; continuation is ineligible for training"
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--wrapper", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--plasma-assets", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    args = parser.parse_args()
    row = json.loads(args.sample.read_text())
    args.receipts.mkdir(parents=True, exist_ok=True)
    admitted = admission(args.checkpoint, row)
    put(args.receipts / (row["id"] + "-admission.json"), admitted)
    command = [
        sys.executable,
        str(Path(__file__).with_name("scientific_counterfactual_trials.py")),
        "continue",
        "--root",
        str(args.root),
        "--checkpoint",
        str(args.checkpoint),
        "--wrapper",
        str(args.wrapper),
        "--python",
        str(args.python),
        "--plasma-assets",
        str(args.plasma_assets),
        "--action",
        admitted["action"],
        "--replicate",
        row["return_group"],
    ]
    process = subprocess.run(command, check=False, timeout=720)
    if process.returncode:
        raise RuntimeError("Continuation collector failed; no reward will be fabricated")
    raw = (args.root / "OUTCOME.json").read_bytes()
    outcome = ContinuationOutcome.model_validate_json(raw)
    status = json.loads((args.root / "CONTINUATION.json").read_text())
    if status["stage"] != "completed":
        raise ValueError("Collector failed; this is not a measured task outcome")
    require_confirmed_solver_outcomes(args.root)
    measured = utility(outcome, RewardWeights())
    overhead_penalty = 0.1 * admitted["overhead_seconds"] / 650
    receipt = dict(
        source_kind="executed_worker_continuation",
        status="completed",
        prompt_sha256=row["behavior"]["prompt_sha256"],
        sampled_answers=row["behavior"]["sampled_answers"],
        verification_sha256=digest(status["quality"]),
        outcome_sha256=hashlib.sha256(raw).hexdigest(),
        outcome=outcome.model_dump(),
        solver_outcomes_confirmed=True,
        utility=measured["total"] - admitted["invalid_penalty"] - overhead_penalty,
        utility_components=measured["components"]
        | dict(invalid_proposal=-admitted["invalid_penalty"], admission_overhead=-overhead_penalty),
        admission=admitted,
    )
    destination = args.receipts / (row["id"] + "-reward.json")
    put(destination, receipt)
    row["outcome_receipt"] = dict(
        path=destination.name, sha256=hashlib.sha256(destination.read_bytes()).hexdigest()
    )
    put(args.receipts / (row["id"] + "-training.json"), row)


if __name__ == "__main__":
    main()
