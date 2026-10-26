"""Export complete parked-worker episodes without replacing missing outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from audit_generalization import completion_measurement
from audit_scientific_workflows import verifier_report_value
from execute_checkpoint_decision import require_confirmed_solver_outcomes
from simjecture_monitor.events import digest, put
from simjecture_monitor.feedback_audit import feedback_measurement
from simjecture_monitor.measured_wait import read_receipt
from simjecture_monitor.sampling_trace import file_reference
from simjecture_monitor.workflow_returns import CHECKS, workflow_advantages, workflow_utility


def read(path):
    return json.loads(path.read_text())


def require_native_evidence(root, starts):
    own = [s for s in starts if s["continuation"] == root.name]
    if not own or any(not s.get("native") or s.get("ended_at") is None for s in own):
        raise ValueError("Native invocations are absent, unconfirmed or still active")
    files = [p for p in root.rglob("response.json") if not p.is_relative_to(root / "research")]
    if not files:
        raise ValueError("Native response evidence is missing")
    for path in files:
        with path.open() as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if isinstance(event, dict) and event.get("type") in {"error", "turn.failed"}:
                    raise ValueError(
                        "Recorded provider failure cannot be assigned to the attention policy"
                    )
    return len(own)


def require_parked_requests(root, outcome, requests, starts):
    """Check the execution timeline, not only the model-visible parked label."""
    parent = [
        s
        for s in starts
        if s["continuation"] == root.name and s.get("cwd") == str(root / "research")
    ]
    for request in requests:
        at = request["requested_at"]
        if (
            not isinstance(at, (int, float))
            or not math.isfinite(at)
            or not any(
                window["started_at"] <= at <= window["ended_at"] for window in outcome["parking"]
            )
        ):
            raise ValueError("Model request falls outside a recorded parked-worker interval")
        if any(s["started_at"] <= at <= s["ended_at"] for s in parent):
            raise ValueError("Model request overlaps an active main-worker invocation")


def export_episode(root, block, trial, *, plan_reference, starts, output, split):
    receipt = read(root.parent / (root.name + "-controller.json"))
    if receipt.get("stage") != "completed" or receipt.get("returncode") != 0:
        raise ValueError("Episode controller failed; do not fabricate a workflow return")
    if receipt["plan_sha256"] != plan_reference["sha256"]:
        raise ValueError("Episode controller used a different frozen plan")
    outcome = read(root / "OUTCOME.json")
    if outcome.get("stage") != "completed":
        raise ValueError("Workflow collector failed")
    case = read(root / "HOST_CASE.json")
    expected_arm = "adapted" if trial["role"] == "sampled" else "observe"
    if case != dict(family=block["family"], seed=block["seed"], arm=expected_arm):
        raise ValueError("Executed task or policy differs from its prospective assignment")
    initial, quality = read(root / "INITIAL.json"), read(root / "QUALITY.json")
    if (
        digest(initial["criteria"]) != block["context"]["criteria_sha256"]
        or quality != outcome["quality"]
    ):
        raise ValueError("Scientific criteria or verification receipt changed")
    if digest(verifier_report_value(root / "research/results.json")) != quality["results_sha256"]:
        raise ValueError("Reported values changed after scientific verification")
    report = root / "research/REPORT.txt"
    if quality.get("report_sha256") and (
        not report.is_file() or digest(report.read_text()) != quality["report_sha256"]
    ):
        raise ValueError("Report changed after scientific verification")
    require_confirmed_solver_outcomes(root)
    native_starts = require_native_evidence(root, starts)
    if native_starts != outcome["native_starts"] or outcome.get("observation_violations"):
        raise ValueError("Workflow accounting or observation audit failed")
    errors = root / "monitor/attention-errors.jsonl"
    if errors.is_file() and errors.read_text().strip():
        raise ValueError("Monitor inference/transport errors make this episode ineligible")
    ledger = read(root / "incident-ledger.json")
    feedback = feedback_measurement(ledger)
    if feedback["required_feedback_misses"] is None:
        raise ValueError("Required feedback reconciliation is unmeasured")
    waiting = read(root / "worker_wait.json") if (root / "worker_wait.json").is_file() else {}
    completion = completion_measurement(outcome, waiting, feedback)
    alerts = read(root / "monitor/alerts.json") if (root / "monitor/alerts.json").is_file() else []
    rows, invalid, requested = [], 0, 0
    model_identity = temperature = None
    # DecisionModel reports end-to-end scoring time, not a separate forward
    # measurement. Do not require the legacy MonitorModel timing schema or
    # invent zero seconds for an unmeasured component.
    usage = dict(inferences=0, input_tokens=0, total_scoring_seconds=0.0)
    sampling_path = root / "monitor/SAMPLING.json"
    if trial["role"] == "sampled":
        sampling = read(sampling_path)
        if (
            not sampling["closed"]
            or sampling["episode_id"] != root.name
            or sampling["seed"] != trial["sampling_seed"]
            or sampling["split"] != split
        ):
            raise ValueError("Sampling trace is not the closed assigned episode")
        requests = sampling["requests"]
        responses = sampling["responses"]
        requested = len(requests)
        if sorted(r["index"] for r in responses) != list(range(requested)):
            raise ValueError("A requested model decision has no recorded response")
        require_parked_requests(root, outcome, requests, starts)
        for response in sorted(responses, key=lambda r: r["index"]):
            row = read_receipt(root / "monitor", response["row"])
            record = read_receipt(root / "monitor", row["decision_receipt"])
            request = requests[row["step_index"]]
            submitted = read_receipt(root / "monitor", request["submitted"])
            if (
                submitted != row["observation"]
                or digest(submitted) != request["packet_sha256"]
                or row["behavior"]["seed"] != request["seed"]
            ):
                raise ValueError("Sampling row does not match the requested parked observation")
            if (
                record["result"]["policy"] != request["policy"]
                or row["episode_id"] != root.name
                or row["split"] != split
            ):
                raise ValueError("Sampled row policy or episode identity mismatch")
            destination = output / (row["id"] + "-decision.json")
            put(destination, record)
            row["decision_receipt"] = file_reference(destination)
            rows.append(row)
            invalid += record["result"]["decision"]["status"] == "inference_error"
            prediction = record["result"]["prediction"]
            usage["inferences"] += 1
            usage["input_tokens"] += prediction["input_tokens"]
            usage["total_scoring_seconds"] += prediction["total_seconds"]
        model_identity, temperature = sampling["model_identity"], sampling["temperature"]
    elif sampling_path.exists() or alerts:
        raise ValueError("The wait control executed automatic policy work")
    measured = dict(
        verified_quality=float(completion["whole_workflow_verified"]),
        native_starts=native_starts,
        elapsed_seconds=outcome["elapsed_seconds"],
        required_feedback_misses=feedback["required_feedback_misses"],
        duplicate_wakeups=outcome["ledger"]["duplicate_wakeups"],
        invalid_proposals=invalid,
    )
    scored = workflow_utility(measured)
    artifact_names = ["OUTCOME.json", "INITIAL.json", "QUALITY.json", "incident-ledger.json"]
    artifact_names += [
        name
        for name in ["VERIFIED.json", "QUANTITY_VERIFIED.json", "monitor/SAMPLING.json"]
        if (root / name).is_file()
    ]
    episode = dict(
        source_kind="executed_parked_workflow",
        status="completed",
        id=root.name,
        role=trial["role"],
        context=block["context"],
        plan_sha256=plan_reference["sha256"],
        lifecycle="parked_until_terminal_fallback_or_returned_attention/v1",
        checks=dict.fromkeys(CHECKS, True),
        measurements=measured,
        utility=scored["total"],
        utility_components=scored["components"],
        automatic_alerts=len(alerts),
        requested_decisions=requested,
        decision_ids=[row["id"] for row in rows],
        model_identity=model_identity,
        temperature=temperature,
        monitor_usage=usage,
        source_artifacts={
            name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in artifact_names
        },
        monitor_cost_scope=(
            "Measured inference work reported separately; utility uses whole-episode "
            "elapsed time and native starts, not billing prices"
        ),
    )
    path = output / (root.name + "-episode.json")
    put(path, episode)
    return file_reference(path), rows


def export(root, output, budget):
    campaign, plan = read(root / "CAMPAIGN.json"), read(root / "PLAN.json")
    if campaign["stage"] != "completed" or campaign.get("infrastructure_failures"):
        raise ValueError(
            "Only a terminal cohort without recorded infrastructure defects is exportable"
        )
    assigned = {t["id"] for b in plan["blocks"] for t in b["trials"]}
    completed = {
        r["id"] for b in campaign["blocks"] for r in b["results"] if r["stage"] == "completed"
    }
    if assigned != completed:
        raise ValueError(
            "Assigned cohort is incomplete; keep all raw outcomes without selected training export"
        )
    output.mkdir(parents=True, exist_ok=False)
    (output / "PLAN.json").write_bytes((root / "PLAN.json").read_bytes())
    plan_ref = file_reference(output / "PLAN.json")
    manifest = dict(
        schema="parked-workflow-return-dataset/v1",
        plan=plan_ref,
        episodes=[],
        model_identity=campaign["model_identity"],
    )
    rows = []
    for block in plan["blocks"]:
        for trial in block["trials"]:
            reference, part = export_episode(
                root / trial["id"],
                block,
                trial,
                plan_reference=plan_ref,
                starts=read(budget)["starts"],
                output=output,
                split=plan["split"],
            )
            manifest["episodes"].append(reference)
            rows.extend(part)
    put(output / "episodes.json", manifest)
    reference = file_reference(output / "episodes.json")
    for row in rows:
        row["episode_manifest"] = reference
    # Commissioning data is retained under a different filename and split. It
    # never becomes training data merely because the workflow happened to pass.
    filename = "train.jsonl" if plan["split"] == "train" else "commissioning.jsonl"
    if plan["split"] == "train":
        _, audit = workflow_advantages(rows, output)
        put(output / "ADVANTAGES.json", audit)
    (output / filename).write_text("".join(json.dumps(row) + "\n" for row in rows))
    ready = dict(
        eligible=plan["split"] == "train",
        collection_verified=True,
        sampling_exercised=bool(rows),
        split=plan["split"],
        episodes=len(manifest["episodes"]),
        sampled_decisions=len(rows),
        data=file_reference(output / filename),
    )
    if plan["split"] != "train":
        ready["reason"] = "Commissioning is deliberately excluded from the optimizer"
    put(output / "READY.json", ready)
    return ready


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.root, args.output, args.budget), indent=2))


if __name__ == "__main__":
    main()
