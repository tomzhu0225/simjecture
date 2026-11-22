"""Fresh, blinded GPT-6.1 Sol assessor with validated, separate C/D receipts."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

from .contracts import fingerprint
from .evaluation import C_WEIGHTS, D_WEIGHTS, score
from .storage import read_json, write_json


def review_schema():
    def components(weights):
        return dict(
            type="object",
            properties={k: dict(type="number", minimum=0, maximum=v) for k, v in weights.items()},
            required=list(weights),
            additionalProperties=False,
        )

    properties = dict(
        score_unit=dict(type="string", enum=["component_points"]),
        C_components=components(C_WEIGHTS),
        D_components=components(D_WEIGHTS),
        accepted_for_training=dict(type="boolean"),
        terminal_validity=dict(type="number", minimum=0, maximum=1),
        unsupported_claims=dict(type="number", minimum=0),
        process_gains=dict(
            type="array",
            items=dict(
                type="object",
                properties=dict(
                    evidence_id=dict(type="string"),
                    verified=dict(type="boolean"),
                    value=dict(type="number", minimum=0, maximum=1),
                    causal_decision_ids=dict(type="array", items=dict(type="string")),
                ),
                required=["evidence_id", "verified", "value", "causal_decision_ids"],
                additionalProperties=False,
            ),
        ),
        independent_verifications=dict(
            type="array",
            items=dict(
                type="object",
                properties=dict(
                    verified=dict(type="boolean"),
                    independent_receipt_ids=dict(type="array", items=dict(type="string")),
                    test_types=dict(
                        type="array",
                        items=dict(type="string", enum=["direct_replication", "new_condition_prediction"]),
                    ),
                    conclusion=dict(type="string"),
                    uncertainty=dict(type="string"),
                ),
                required=["verified", "independent_receipt_ids", "test_types", "conclusion", "uncertainty"],
                additionalProperties=False,
            ),
        ),
        auxiliary_novelty=dict(type="number", minimum=0, maximum=100),
        auxiliary_scientific_value=dict(type="number", minimum=0, maximum=100),
        rationale=dict(type="string"),
    )
    return dict(type="object", properties=properties, required=list(properties), additionalProperties=False)


def blinded_record(record):
    record = copy.deepcopy(record)
    original_id = record.get("study_id", "")
    record.pop("study_id", None)
    record.pop("pinned_policy_sha256", None)
    # Execution/audit IDs remain to support evidence attribution; model names,
    # advice provenance, checkpoint names, token likelihoods and arm are hidden.
    record["events"] = [
        dict(kind=e["kind"], payload=e["payload"])
        for e in record["events"]
        if e["kind"] in {"decision_audit", "execution_submission", "execution_submission_failure"}
    ]
    for event in record["events"]:
        if event["kind"] == "decision_audit":
            event["payload"] = {
                k: v
                for k, v in event["payload"].items()
                if k in {"decision_id", "executed_plan", "observation_sha256"}
            }

    def redact(value):
        if isinstance(value, dict):
            return {
                k: redact(v) for k, v in value.items() if k not in {"arm", "teacher_model", "policy_sha256"}
            }
        if isinstance(value, list):
            return [redact(v) for v in value]
        if isinstance(value, str):
            if original_id:
                value = value.replace(original_id, "ANONYMOUS_CASE")
            for label in (
                "simjecture_sftrl9b",
                "simjecture_sft9b",
                "simjecture_raw9b",
                "gpt-6.1-sol",
                "Qwen3.5-9B",
            ):
                value = value.replace(label, "WITHHELD_MODEL_LABEL")
        return value

    return redact(record)


def prepare_packet(root, record, task, *, objective=None, participant_sessions=()):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    packet = dict(
        anonymous_case_id=fingerprint(record)[:20],
        blinding="Model labels and study-directory identifiers are withheld; artifact hashes refer to unmodified archived bytes.",
        task_contract={
            k: v for k, v in task.items() if k not in {"split", "authoring_status", "family_group"}
        },
        scientific_record=blinded_record(record),
        objective_validation=objective,
        independently_executed_verifications=record.get("independent_verification_receipts", []),
        C_weights=C_WEIGHTS,
        D_weights=D_WEIGHTS,
        instructions=(
            "Assess all studies including unfinished and timed-out cases. Only executed evidence can "
            "support claims. Score C and D separately. Unknown or unperformed replication earns no "
            "replication credit. Numerical agreement is insufficient without IC/BC, units, "
            "resolution and uncertainty checks. Never treat a proposal as discovery. Open-task "
            "novelty/value scores are anonymous auxiliary assessments, not a substitute for evidence. "
            "Identify verified process gains and their actual causal decision IDs. "
            "Candidate execution evidence is not automatically scientifically verified; certify it only "
            "after checking the attached numerical outputs and executed source. C/D components are POINTS, "
            "not fractions: C maxima 40,35,25 and D maxima 30,25,25,20. An 80% quality decision "
            "earns 24/30 points for experiment choice, not 0.8. Both totals range 0 to 100. "
            "Only terminal_validity and process gain values use 0 to 1. SFT acceptance concerns "
            "faithful, scientifically sound public decisions with actual receipts; an unfinished goal "
            "can still qualify. Never accept fabricated or unexecuted teaching examples. "
            "No model-generated hidden reference value may replace an operator's objective check."
        ),
    )
    write_json(root / "role-packet.json", packet, immutable=True)
    write_json(root / "review-output.schema.json", review_schema(), immutable=True)
    # Provenance is kept outside the blinded packet.
    return dict(
        reviewed_record_sha256=fingerprint(record), participant_session_ids=list(participant_sessions)
    )


def validate_review(reply, record, provenance, session):
    from jsonschema import Draft202012Validator

    wording = reply.get("rationale", "").replace("\u2013", "-").replace("\u2014", "-")
    if reply.get("score_unit") is None and "0-1 scale" in wording:
        # Preserve the original assessor declaration; this is a unit conversion,
        # never a change to the scientific judgment or to a student observation.
        reply["original_normalized_components"] = {
            "C": dict(reply["C_components"]),
            "D": dict(reply["D_components"]),
        }
        for field, weights in [("C_components", C_WEIGHTS), ("D_components", D_WEIGHTS)]:
            if not all(0 <= v <= 1 for v in reply[field].values()):
                raise ValueError("Conflicting score unit declaration")
            reply[field] = {k: v * weights[k] for k, v in reply[field].items()}
        reply["score_unit"] = "component_points"
    original_units = reply.pop("original_normalized_components", None)

    Draft202012Validator(review_schema()).validate(reply)
    if session in provenance["participant_session_ids"]:
        raise ValueError("Independent reviewer was a research participant")
    evidence_ids = {e["evidence_id"] for e in read_public_evidence(record)}
    decisions = {e["payload"]["decision_id"] for e in record["events"] if e["kind"] == "decision_audit"}
    receipts = {r["id"] for r in record["receipts"]}
    for gain in reply["process_gains"]:
        if gain["verified"] and gain["evidence_id"] not in evidence_ids:
            raise ValueError("Reward review certified evidence absent from the public scientific ledger")
        if not set(gain["causal_decision_ids"]) <= decisions:
            raise ValueError("Reward review names an unrecorded decision")
    verifications = reply["independent_verifications"]
    # A verbal promise of replication never earns the 35 point component.
    executed = {
        v["id"]: v
        for v in record.get("independent_verification_receipts", [])
        if v.get("status") == "succeeded"
        and v.get("execution")
        and v.get("source_sha256")
        and v.get("artifact_sha256")
    }
    valid_verification = any(
        v.get("verified")
        and v.get("independent_receipt_ids")
        and set(v["independent_receipt_ids"]) <= set(executed)
        and not set(v["independent_receipt_ids"]) & receipts
        for v in verifications
    )
    if not valid_verification:
        reply["C_components"]["independent_replication_and_prediction"] = 0
    result = dict(reply, **provenance, reviewer_session_id=session, reviewer_model="gpt-6.1-sol")
    if original_units is not None:
        result["original_normalized_components"] = original_units
    result["C"] = score(reply["C_components"], C_WEIGHTS)
    result["D"] = score(reply["D_components"], D_WEIGHTS)
    return result


def read_public_evidence(record):
    return record.get("verified_evidence", []) + record.get("candidate_evidence", [])


def run_review(config, packet_root, record, task, *, objective=None, participant_sessions=()):
    packet_root = Path(packet_root)
    provenance = prepare_packet(
        packet_root, record, task, objective=objective, participant_sessions=participant_sessions
    )
    output = packet_root / "review-response.json"
    if output.exists():
        try:
            read_json(output)
        except (ValueError, OSError):
            import uuid

            output.rename(output.with_name("invalid-response-" + uuid.uuid4().hex + ".json"))
    if not output.exists():
        old_log = packet_root / "assessor.jsonl"
        if old_log.exists():
            import uuid

            old_log.rename(old_log.with_name("assessor-attempt-" + uuid.uuid4().hex + ".jsonl"))
        argv = [
            config["codex_wrapper"],
            "exec",
            "--ephemeral",
            "--model",
            "gpt-6.1-sol",
            "--skip-git-repo-check",
            "--sandbox",
            "workspace-write",
            "--json",
            "--output-schema",
            str(packet_root / "review-output.schema.json"),
            "--output-last-message",
            str(output),
            "-",
        ]
        prompt = (
            "Read role-packet.json. Act as an independent scientific assessor. "
            "Return only the required JSON. Do not conduct a new research task or infer hidden answers. "
            "Use the supplied independent verification receipts; score missing evidence honestly."
        )
        with (packet_root / "assessor.jsonl").open("wb") as log:
            result = subprocess.run(
                argv,
                input=prompt.encode(),
                cwd=packet_root,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=config["assessment_timeout_seconds"],
            )
        if result.returncode:
            raise RuntimeError("Independent assessor failed; preserve the case and retry review only")
    sessions = []
    for line in (packet_root / "assessor.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "thread.started":
            sessions.append(event["thread_id"])
    if len(set(sessions)) != 1:
        raise ValueError("Independent review lacks an unambiguous native session receipt")
    reply = read_json(output)
    if objective and objective.get("kind") == "known_conclusion":
        fraction = objective["weighted_pass_fraction"]
        if not 0 <= fraction <= 1 or not objective.get("receipt_sha256"):
            raise ValueError("Objective known-answer comparison lacks its operator receipt")
        reply["C_components"]["truth_or_valid_evidence"] = 40 * fraction
    result = validate_review(reply, record, provenance, sessions[0])
    write_json(packet_root / "review-receipt.json", result, immutable=True)
    return result
