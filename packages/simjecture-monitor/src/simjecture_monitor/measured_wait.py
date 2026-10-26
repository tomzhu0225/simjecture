"""Independent measured wait controls for sampled-decision policy gradients.

Forced controls are never represented as samples from the behavior policy.
Receipt hashes bind host-produced records; they are not a substitute for the
collector's scientific verifier or a proof of causal benefit.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from .reward import ContinuationOutcome, RewardWeights, paired_reward, utility


def read_receipt(root, reference):
    root = Path(root).resolve()
    path = (root / reference["path"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Receipt must be inside the portable dataset directory")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference["sha256"]:
        raise ValueError("Outcome receipt changed")
    return json.loads(raw)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_measured_receipt(receipt, *, control):
    expected = "executed_wait_continuation" if control else "executed_worker_continuation"
    if receipt.get("source_kind") != expected or receipt.get("status") != "completed":
        raise ValueError("Require a completed executed continuation of the assigned kind")
    if receipt.get("solver_outcomes_confirmed") is not True:
        raise ValueError("Unconfirmed solver outcomes cannot supply a wait-controlled reward")
    outcome = ContinuationOutcome.model_validate(receipt["outcome"])
    if receipt.get("verification_sha256") != outcome.quality_receipt_sha256:
        raise ValueError("Scientific verification identity differs from the outcome")
    value = utility(outcome, RewardWeights())["total"]
    if control:
        if outcome.action != "defer":
            raise ValueError("Wait control must continue without an automatic intervention")
    else:
        admission = receipt["admission"]
        penalty, overhead = admission["invalid_penalty"], admission["overhead_seconds"]
        if (
            penalty not in (0.0, 0.05)
            or isinstance(penalty, bool)
            or not finite(overhead)
            or overhead < 0
            or admission["action"] != outcome.action
        ):
            raise ValueError("Invalid admission cost or executed-action binding")
        value -= penalty + RewardWeights().wall_time * overhead / 650
    if not finite(receipt.get("utility")) or not math.isclose(
        value, receipt["utility"], rel_tol=1e-10, abs_tol=1e-10
    ):
        raise ValueError("Utility does not reproduce the declared measured components")
    return outcome, value


def wait_controlled_advantages(rows, root):
    """Subtract the same independent wait mean from every sample of each state.

    Require at least two distinct real controls per state. All sampled actions
    share those controls, independently of the sampled answer or its outcome.
    The controls do not enter the optimizer as if they had policy logprobs.
    """
    if not rows or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Sample identities must be distinct and nonempty")
    sample_ids = {row["id"] for row in rows}
    groups = defaultdict(list)
    for row in rows:
        if row.get("split") != "train":
            raise ValueError("Wait-controlled optimization requires explicit training rows")
        groups[row["return_group"]].append(row)
    result, audit, used_controls = {}, {}, {}
    for group_id, group in groups.items():
        if len(group) < 2:
            raise ValueError("Require at least two sampled decisions per state")
        references = group[0].get("wait_outcome_receipts", [])
        if len(references) < 2:
            raise ValueError("Require at least two independently executed wait controls")
        canonical = sorted((ref["path"], ref["sha256"]) for ref in references)
        controls = [
            validate_measured_receipt(read_receipt(root, ref), control=True) for ref in references
        ]
        control_ids = [outcome.record_id for outcome, _ in controls]
        if len(set(control_ids)) != len(controls) or sample_ids.intersection(control_ids):
            raise ValueError("Wait controls must be distinct from each other and policy samples")
        for identity in control_ids:
            if identity in used_controls and used_controls[identity] != group_id:
                raise ValueError("A wait execution cannot belong to different state groups")
            used_controls[identity] = group_id
        wait_mean = sum(value for _, value in controls) / len(controls)
        measured = []
        for row in group:
            if canonical != sorted(
                (ref["path"], ref["sha256"]) for ref in row.get("wait_outcome_receipts", [])
            ):
                raise ValueError("Every sampled decision for a state must share its wait controls")
            receipt = read_receipt(root, row["outcome_receipt"])
            if (
                receipt.get("prompt_sha256") != row["behavior"]["prompt_sha256"]
                or receipt.get("sampled_answers")
                != {key: value["label"] for key, value in row["targets"].items()}
                or receipt.get("sampled_answers") != row["behavior"]["sampled_answers"]
            ):
                raise ValueError("Continuation is not bound to the logged sampled decision")
            chosen, value = validate_measured_receipt(receipt, control=False)
            if chosen.record_id != row["id"] or chosen.replicate_id != group_id:
                raise ValueError("Continuation record or comparison-group identity mismatch")
            for waiting, _ in controls:
                matched = paired_reward(chosen, waiting)
                if not matched["eligible"]:
                    raise ValueError("Incomparable wait control: " + ", ".join(matched["reasons"]))
            result[row["id"]] = value - wait_mean
            measured.append(dict(id=row["id"], utility=value, advantage=result[row["id"]]))
        audit[group_id] = dict(
            wait_records=control_ids,
            wait_utilities=[value for _, value in controls],
            wait_mean=wait_mean,
            samples=measured,
        )
    if max(map(abs, result.values())) < 1e-8:
        raise ValueError("No measured advantage relative to waiting; skip the RL update")
    return result, audit
