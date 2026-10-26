"""Audit a proposed decoder on saved logits without fabricating new execution.

This is an offline projection of recorded field probabilities, not model
inference, new training data, or a counterfactual scientific-workflow outcome.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from simjecture_monitor import attention_support as protocol
from simjecture_monitor.action_distribution import (
    CONTRACT,
    choose,
    decoding_receipt,
    factors,
    replay,
    validate_support,
)
from simjecture_monitor.decision_interface import ROUTES, choice_from_answers, scientific_request
from simjecture_monitor.events import put
from simjecture_monitor.measured_wait import read_receipt


def audit(sampling_path, output):
    if output.exists():
        raise ValueError("Refuse to overwrite an existing decoder audit")
    sampling = json.loads(sampling_path.read_text())
    if not sampling.get("closed") or len(sampling["requests"]) != len(sampling["responses"]):
        raise ValueError("Require a complete closed sampling trace")
    rows = []
    for reference in sorted(sampling["responses"], key=lambda r: r["index"]):
        row = read_receipt(sampling_path.parent, reference["row"])
        record = read_receipt(sampling_path.parent, row["decision_receipt"])
        behavior = row["behavior"]
        if behavior != record["result"]["behavior"]:
            raise ValueError("Row and source behavior disagree")
        packet = protocol.Observation.model_validate(row["observation"])
        view = protocol.PackedView.model_validate(record["result"]["view"])
        request = scientific_request(packet, view)
        validate_support(behavior["probabilities"], request)
        original, original_logp = replay(behavior, request)
        if original != behavior["sampled_answers"] or not math.isclose(
            original_logp,
            behavior["sampled_joint_log_probability"],
            rel_tol=1e-10,
            abs_tol=1e-10,
        ):
            raise ValueError("Original behavior draw does not replay exactly")
        projected, logp = choose(
            behavior["probabilities"], distribution=CONTRACT, seed=behavior["seed"]
        )
        # Bind the actual sampled citations; do not fill in missing evidence.
        bound = protocol.bind_choice(
            packet, view, choice_from_answers(projected), policy_id="offline-contract-projection"
        )
        decoder = decoding_receipt(behavior["probabilities"], CONTRACT)
        joint = factors(behavior["probabilities"], CONTRACT)[0]
        expert_indices = [
            i
            for i, (route, _) in enumerate(joint["candidates"])
            if ROUTES[route][0] in {"request_worker_help", "wake_director", "request_repair_judge"}
        ]
        expert_mass = sum(joint["probabilities"][i] for i in expert_indices)
        rows.append(
            dict(
                id=row["id"],
                source_receipt=row["decision_receipt"],
                original_answers=original,
                original_log_probability=original_logp,
                original_status=record["result"]["decision"]["status"],
                original_admission=record["admission"],
                original_invalid_pair_mass=max(0.0, 1.0 - math.exp(decoder["log_valid_pair_mass"])),
                projected_answers=projected,
                projected_log_probability=logp,
                projected_contract_valid=bound.status == "ok",
                projected_executed=False,
                original_valid_expert_proposal_probability=expert_mass
                * math.exp(decoder["log_valid_pair_mass"]),
                projected_expert_proposal_probability=expert_mass,
                decoding=decoder,
            )
        )
    if not rows:
        raise ValueError("No sampled observations to audit")
    result = dict(
        schema="scientific-action-constraint-audit/v1",
        scope="Offline decoder projection only; no inferred intervention value or new returns",
        sampling_sha256=hashlib.sha256(sampling_path.read_bytes()).hexdigest(),
        original_draws_replayed=len(rows),
        original_invalid_outputs=sum(row["original_status"] != "ok" for row in rows),
        mean_original_invalid_pair_mass=sum(r["original_invalid_pair_mass"] for r in rows)
        / len(rows),
        projected_invalid_outputs=sum(not row["projected_contract_valid"] for row in rows),
        mean_original_valid_expert_proposal_probability=sum(
            row["original_valid_expert_proposal_probability"] for row in rows
        )
        / len(rows),
        mean_projected_expert_proposal_probability=sum(
            row["projected_expert_proposal_probability"] for row in rows
        )
        / len(rows),
        rows=rows,
    )
    put(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sampling", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.sampling, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
