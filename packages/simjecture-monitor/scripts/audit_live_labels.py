"""Validate native observation judgments without promoting consensus to ground truth."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from simjecture_monitor import attention_support as protocol
from simjecture_monitor.decision_interface import ROUTES, choice_from_answers, scientific_request


def read(path):
    return json.loads(path.read_text())


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root):
    plan = read(root / "PLAN.json")
    if (
        fingerprint(root / "rows.json") != plan["rows_sha256"]
        or fingerprint(root / "provenance.json") != plan["provenance_sha256"]
    ):
        raise ValueError("Frozen auditor inputs changed")
    rows = {r["id"]: r for r in read(root / "rows.json")}
    provenance = {r["id"]: r for r in read(root / "provenance.json")}
    if set(rows) != set(provenance) or len(rows) != 24:
        raise ValueError("Incomplete prospective observation set")
    planned = {batch["id"]: batch for batch in plan["batches"]}
    by_batch, attempts = {}, []
    folders = [root, *sorted(root.glob("recovery-*"))]
    for folder in folders:
        if not folder.is_dir():
            continue
        if folder != root:
            recovery = read(folder / "PLAN.json")
            if recovery["original_plan_sha256"] != fingerprint(root / "PLAN.json") or recovery[
                "original_status_sha256"
            ] != fingerprint(root / "STATUS.json"):
                raise ValueError("Recovery no longer binds the original plan and failed attempt")
            if any(planned.get(batch["id"]) != batch for batch in recovery["assignments"]):
                raise ValueError("Recovery changed an original assignment")
            previous = recovery.get("previous_recovery_status_sha256")
            if previous and not any(
                other.is_dir()
                and other.name < folder.name
                and (other / "STATUS.json").is_file()
                and fingerprint(other / "STATUS.json") == previous
                for other in folders
                if other != root
            ):
                raise ValueError("Recovery no longer binds its previous terminal attempt")
        for path in sorted(folder.glob("*/execution.json")):
            result = read(path)
            identity = result["id"]
            if identity not in planned:
                raise ValueError("Unassigned native judgment")
            batch = planned[identity]
            if (
                fingerprint(path.parent / "prompt.txt") != batch["prompt_sha256"]
                or fingerprint(path.parent / "schema.json") != batch["schema_sha256"]
            ):
                raise ValueError("Auditor saw a different prompt or schema")
            attempts.append(
                dict(
                    batch=identity,
                    path=str(path.relative_to(root)),
                    **{k: result.get(k) for k in ["stage", "returncode", "started_at", "ended_at"]},
                )
            )
            if result["stage"] != "completed" or result["returncode"] != 0:
                continue
            if identity in by_batch:
                raise ValueError("Multiple successful responses to one assignment; do not select")
            event_types = Counter()
            for line in path.with_name("events.jsonl").read_text().splitlines():
                event = json.loads(line)
                if event.get("type") in {"error", "turn.failed"}:
                    raise ValueError("Completed judgment contains a provider failure")
                item = event.get("item", {})
                if item:
                    event_types[item.get("type", "unknown")] += 1
            if set(event_types) - {"agent_message", "reasoning"}:
                raise ValueError("Auditor used a tool despite the text-only protocol")
            value = read(path.with_name("answers.json"))
            assessments = value["assessments"]
            if len(assessments) != len(batch["observation_ids"]) or {
                a["id"] for a in assessments
            } != set(batch["observation_ids"]):
                raise ValueError("Missing, duplicate or unassigned observation judgment")
            by_batch[identity] = dict(
                path=str(path.parent.relative_to(root)),
                answer_sha256=fingerprint(path.with_name("answers.json")),
                event_types=dict(event_types),
                assessments=assessments,
            )
    judgments = {identity: {} for identity in rows}
    for identity, result in by_batch.items():
        reviewer = planned[identity]["reviewer"]
        for assessment in result["assessments"]:
            identity = assessment["id"]
            row, source = rows[identity], provenance[identity]
            packet = protocol.Observation.model_validate(source["observation"])
            view = protocol.PackedView.model_validate(source["view"])
            reconstructed = scientific_request(packet, view)
            if (row["state"], row["questions"]) != (
                reconstructed["state"],
                reconstructed["questions"],
            ):
                raise ValueError("Judgment input differs from the actual public observation")
            answers = assessment["answers"]
            if set(answers) != set(row["questions"]) or any(
                value not in row["questions"][field]["criteria"] for field, value in answers.items()
            ):
                raise ValueError("Auditor selected a label absent from this observation")
            choice = choice_from_answers(answers)
            bound = protocol.bind_choice(packet, view, choice, policy_id="native-label-audit")
            alternatives = assessment["acceptable_routes"]
            if (
                not alternatives
                or not set(alternatives) <= set(ROUTES)
                or answers["route"] not in alternatives
            ):
                raise ValueError("Inconsistent acceptable-route judgment")
            if any(ROUTES[r][1] != "none" for r in alternatives) and not view.question_aliases:
                raise ValueError("Support alternative has no visible question")
            if reviewer in judgments[identity]:
                raise ValueError("Duplicate reviewer judgment")
            grounding = bound.action in {"observe", "recheck"} or (
                bound.basis != "unspecified" and bound.evidence_basis == "selected"
            )
            judgments[identity][reviewer] = dict(
                **assessment,
                structurally_valid=True,
                admissible_grounding=grounding,
                batch_path=result["path"],
            )
    summaries = []
    for identity, ratings in judgments.items():
        a, b = ratings.get("a"), ratings.get("b")
        overlap = (
            sorted(set(a["acceptable_routes"]) & set(b["acceptable_routes"])) if a and b else None
        )
        summaries.append(
            dict(
                id=identity,
                case=provenance[identity]["case"],
                judgments=ratings,
                both_reviewed=bool(a and b),
                exact_route_agreement=a["answers"]["route"] == b["answers"]["route"]
                if a and b
                else None,
                acceptable_route_intersection=overlap,
                requires_review=bool(a and b)
                and (
                    not overlap
                    or any(
                        j["certainty"] == "low"
                        or j["intervention_before_fallback"] == "uncertain"
                        or not j["admissible_grounding"]
                        for j in ratings.values()
                    )
                ),
            )
        )
    return dict(
        schema="live-observation-label-audit/v1",
        eligible_for_optimizer=False,
        reason=(
            "Model judgments require evidence review; consensus is not measured intervention value"
        ),
        complete=len(by_batch) == len(planned),
        planned_calls=len(planned),
        completed_calls=len(by_batch),
        native_attempts=attempts,
        completed_batches=by_batch,
        judgments=sum(len(row["judgments"]) for row in summaries),
        dual_reviewed=sum(row["both_reviewed"] for row in summaries),
        exact_route_agreements=sum(row["exact_route_agreement"] is True for row in summaries),
        overlapping_route_sets=sum(bool(row["acceptable_route_intersection"]) for row in summaries),
        requires_review=sum(row["requires_review"] for row in summaries),
        observations=summaries,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(args.root)
    if args.output:
        with args.output.open("x") as stream:
            json.dump(result, stream, indent=2)
    print(
        json.dumps(
            {
                k: v
                for k, v in result.items()
                if k not in {"native_attempts", "completed_batches", "observations"}
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
