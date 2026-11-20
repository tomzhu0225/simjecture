"""Frozen final four-arm comparison and advice attribution. Sealed data stay closed on import."""

import hashlib
import json
from pathlib import Path

from .contracts import TASK_FIELDS, fingerprint
from .pipeline import initial_anchor, rows
from .storage import read_json, write_json


def freeze(pipeline, sft_checkpoint):
    selection = pipeline.remote.read("checkpoints/selection.json")
    if not selection or not selection.get("stop"):
        raise ValueError("Final testing requires the completed development stopping rule")
    record = dict(
        best_checkpoint=selection["best_checkpoint"],
        sft_checkpoint=sft_checkpoint,
        selection=selection,
        protocol_sha256=fingerprint(read_json(pipeline.root / "config/protocol.json")),
        formal_plan_sha256=fingerprint(rows(pipeline.root / "plans/formal_comparison.jsonl")),
        attribution_plan_sha256=fingerprint(rows(pipeline.root / "plans/advice_attribution.jsonl")),
        heldout_ciphertext_sha256=hashlib.sha256(
            (pipeline.root / "sealed/test.aesgcm").read_bytes()
        ).hexdigest(),
        code_sha256={
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (pipeline.root / "research_decision").glob("*.py")
        },
    )
    write_json(pipeline.root / "final-freeze.json", record, immutable=True)
    return record


def release_public_contracts(pipeline, vault):
    frozen = read_json(pipeline.root / "final-freeze.json")
    if not frozen or frozen["protocol_sha256"] != fingerprint(
        read_json(pipeline.root / "config/protocol.json")
    ):
        raise ValueError("Freeze the final checkpoint, protocol and run plans before test access")
    ciphertext = (pipeline.root / "sealed/test.aesgcm").read_bytes()
    if hashlib.sha256(ciphertext).hexdigest() != frozen["heldout_ciphertext_sha256"]:
        raise ValueError("Sealed test commitment changed")
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    manifest = read_json(pipeline.root / "tasks/test_manifest.json")
    plaintext = AESGCM((Path(vault) / "test.key").read_bytes()).decrypt(
        ciphertext[:12], ciphertext[12:], manifest["associated_data"].encode()
    )
    if hashlib.sha256(plaintext).hexdigest() != manifest["payload_sha256"]:
        raise ValueError("Held-out task payload differs from its pretraining commitment")
    private = json.loads(plaintext)
    allowed = set(TASK_FIELDS) | {
        "split",
        "domain",
        "difficulty",
        "mechanism_group",
        "family_group",
        "evaluation_type",
    }
    for task in private:
        public = {k: v for k, v in task.items() if k in allowed}
        public["split"] = "test"
        pipeline.tasks[public["task_id"]] = public
    # Private contracts never enter a role directory or an observation. Only
    # the operator numerical evaluator may consume their hidden validation data.
    return {t["task_id"]: t for t in private}


def formal(pipeline, vault):
    private = release_public_contracts(pipeline, vault)
    frozen = read_json(pipeline.root / "final-freeze.json")
    paths = {
        "simjecture": None,
        "simjecture_raw9b": None,
        "simjecture_sft9b": frozen["sft_checkpoint"],
        "simjecture_sftrl9b": frozen["best_checkpoint"],
    }
    # Randomized within-task arm order is frozen before any test is released.
    # Two study slots have identical worker capacity and admission rules.
    plans = rows(pipeline.root / "plans/formal_comparison.jsonl")
    results = pipeline.jobs(plans, adapter=paths, private_contracts=private)
    summarize(pipeline.root / "reports/formal-results.json", results)
    return results


def attribution(pipeline, vault):
    private = release_public_contracts(pipeline, vault)
    frozen = read_json(pipeline.root / "final-freeze.json")
    plans = rows(pipeline.root / "plans/advice_attribution.jsonl")
    results = []
    for index in range(0, len(plans), 2):
        pair = plans[index : index + 2]
        task = pipeline.tasks[pair[0]["task_id"]]
        anchor = initial_anchor(task, pipeline.cfg)
        pair_results = []
        for slot, job in enumerate(pair):
            assisted = job["arm"] == "host_with_final9b_advice"
            job = dict(
                job,
                arm="simjecture_sftrl9b" if assisted else "simjecture",
                attribution_label=job["arm"],
                anchor_sha256=fingerprint(anchor),
            )
            result = pipeline.study(
                job,
                slot=slot,
                adapter=frozen["best_checkpoint"] if assisted else None,
                private_contract=private[job["task_id"]],
            )
            if result["record"]["initial_state_sha256"] != fingerprint(anchor):
                raise ValueError("Attribution pair did not start from the same precommitted research state")
            pair_results.append(result)
        result = dict(
            pair_id=pair[0]["pair_id"],
            initial_state_sha256=fingerprint(anchor),
            task_id=task["task_id"],
            delta_C=pair_results[1]["review"]["C"] - pair_results[0]["review"]["C"],
            delta_D=pair_results[1]["review"]["D"] - pair_results[0]["review"]["D"],
            executed_experiment_plans=[
                [
                    e["payload"]["executed_plan"]
                    for e in r["record"]["events"]
                    if e["kind"] == "decision_audit"
                ]
                for r in pair_results
            ],
            verified_evidence=[r["record"]["verified_evidence"] for r in pair_results],
            conclusions=[r["record"]["closeout"] for r in pair_results],
            estimand="intention-to-treat effect of access to student advice",
            controllable_randomness="common physical simulation seed streams; provider model RNG unavailable",
        )
        write_json(pipeline.root / "data/attribution" / (task["task_id"] + ".json"), result, immutable=True)
        results.extend(pair_results)
    summarize(pipeline.root / "reports/attribution-results.json", results)
    return results


def summarize(path, results):
    import statistics

    arms = {}
    for row in results:
        job = read_json(Path(row["case"]) / "study-run.json")
        label = job.get("attribution_label", job["arm"])
        arms.setdefault(label, []).append(row)
    report = {
        label: dict(
            n=len(rows),
            C=statistics.fmean(r["review"]["C"] for r in rows),
            D=statistics.fmean(r["review"]["D"] for r in rows),
            unfinished=sum(bool(r["record"]["closeout"]["unresolved"]) for r in rows),
            omitted_incomplete_runs=0,
            verified_findings=sum(len(r["record"]["closeout"]["supported"]) for r in rows),
            falsifications=sum(len(r["record"]["closeout"]["falsified"]) for r in rows),
            cases=[r["case"] for r in rows],
        )
        for label, rows in arms.items()
    }
    write_json(path, report)
    return report
