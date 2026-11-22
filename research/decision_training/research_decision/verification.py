"""Post-study independent numerical replication; never run during preparation."""

import copy
from pathlib import Path

from .case import receipts
from .contracts import fingerprint
from .storage import read_json, write_json


def verification_task(task, claims, budget_fraction=0.2):
    result = copy.deepcopy(task)
    result["question"] = (
        "Independent numerical replication and new-condition prediction checks: " + task["question"]
    )
    result["replication_targets"] = claims
    result["total_wall_seconds"] = max(30, int(task["total_wall_seconds"] * budget_fraction))
    result["scope_statement"] = (
        "Independent code/discretization; preserve units, physical IC/BC and model scope."
    )
    return result


def run_verification(pipeline, case, task, *, slot):
    case = Path(case)
    conclusion = read_json(case / "phase_conclusion.json")
    claims = conclusion["supported"] + conclusion["falsified"]
    if not claims:
        write_json(case / "independent-verification-receipts.json", [], immutable=True)
        return []
    verification_id = case.name + "-independent-verification"
    verification = verification_task(task, claims)
    key = verification["task_id"] + "-verification-" + fingerprint(claims)[:12]
    verification["task_id"] = key
    pipeline.tasks[key] = verification
    result = pipeline.study(
        dict(
            job_id=verification_id,
            task_id=key,
            arm="simjecture",
            verification_only=True,
            original_scientific_case=case.name,
        ),
        slot=slot,
        assess=False,
    )
    destination = Path(result["case"])
    original_hashes = {
        r.get("binding", {}).get("inputs", {}).get(r.get("binding", {}).get("source")) for r in receipts(case)
    }
    verified = []
    for row in receipts(destination):
        binding = row.get("binding", {})
        source_hash = binding.get("inputs", {}).get(binding.get("source"))
        artifacts = row.get("remote_artifacts") or row.get("artifacts") or {}
        if source_hash in original_hashes:
            continue
        verified.append(
            dict(
                row,
                source_sha256=source_hash,
                artifact_sha256=fingerprint(artifacts),
                independent_case_id=verification_id,
            )
        )
    write_json(case / "independent-verification-receipts.json", verified, immutable=True)
    write_json(
        case / "independent-verification-index.json",
        dict(
            case=str(destination),
            measured_study_wall_seconds=verification["total_wall_seconds"],
            task_contract_sha256=fingerprint(verification),
        ),
        immutable=True,
    )
    return verified
