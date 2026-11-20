"""Export reviewed live records into SFT samples and closed RLOO groups."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .contracts import fingerprint, reject_private_fields
from .journal import Journal
from .rloo import scientific_return, validate_group


def live_record(study):
    study = Path(study)
    journal = Journal(study / "decision-audit/events.sqlite")
    events = journal.export(study.name)
    journal.close()
    receipts = [json.loads(path.read_bytes()) for path in sorted((study / "experiments").glob("*.json"))]
    if any(receipt["status"] in {"queued", "running", "staging"} for receipt in receipts):
        raise ValueError("Close or cancel every experiment before exporting a complete trajectory")
    closeout = json.loads((study / "phase_conclusion.json").read_bytes())
    if not closeout["include_in_C"] or not closeout["include_in_D"]:
        raise ValueError("Incomplete studies must participate in both evaluations")
    initial = json.loads((study / "initial-state.json").read_bytes())
    from .case import public_evidence
    from .storage import read_json

    return dict(
        study_id=study.name,
        events=events,
        receipts=receipts,
        candidate_evidence=[
            dict(
                evidence_id="execution:" + r["id"],
                receipt_ids=[r["id"]],
                verification_level="execution_integrity_only; independent scientific review pending",
            )
            for r in receipts
            if r["status"] == "succeeded"
        ],
        submitted_scientific_report=(study / "research/RESULTS.md").read_text(
            encoding="utf-8", errors="replace"
        )
        if (study / "research/RESULTS.md").exists()
        else "",
        closeout=closeout,
        initial_state_sha256=fingerprint(initial),
        verified_evidence=public_evidence(study, receipts),
        independent_verification_receipts=read_json(study / "independent-verification-receipts.json", []),
        pinned_policy_sha256=read_json(study / "study-run.json", {}).get("policy_sha256"),
        scientific_output_summaries=[
            dict(
                item,
                text=(study / "assessment-artifacts" / item["file"]).read_text(
                    encoding="utf-8", errors="replace"
                ),
            )
            for item in read_json(study / "assessment-artifacts/index.json", [])
        ],
    )


def checked_review(record, review):
    if review["reviewer_model"] != "gpt-6.1-sol":
        raise ValueError("The independent review must use GPT-6.1 Sol")
    if review["reviewer_session_id"] in review["participant_session_ids"]:
        raise ValueError("The independent reviewer participated in the study")
    if review["reviewed_record_sha256"] != fingerprint(record):
        raise ValueError("The reviewed record differs from the exported trajectory")


def bound_actions(record):
    audits = {
        event["payload"]["decision_id"]: event["payload"]
        for event in record["events"]
        if event["kind"] == "decision_audit"
    }
    links = [event["payload"] for event in record["events"] if event["kind"] == "advice_execution_link"]
    by_advice = {}
    for link in links:
        if link["advice_id"]:
            by_advice.setdefault(link["advice_id"], []).append(audits[link["decision_id"]])
    receipt_ids = {receipt["id"] for receipt in record["receipts"]}
    for event in record["events"]:
        if event["kind"] != "raw_advice":
            continue
        bound = by_advice.get(event["event_id"], [])
        reject_private_fields(event["payload"]["observation"])
        submissions = [
            entry["payload"]
            for entry in record["events"]
            if entry["kind"] == "execution_submission"
            and entry["payload"]["decision_id"] in {audit["decision_id"] for audit in bound}
        ]
        if any(entry["receipt"]["id"] not in receipt_ids for entry in submissions):
            raise ValueError("An advice submission lacks a real terminal receipt")
        yield event, bound, [entry["receipt"]["id"] for entry in submissions]


def sft_samples(record, task, review, review_receipt):
    checked_review(record, review)
    if not review["accepted_for_training"] or not record["receipts"]:
        raise ValueError("SFT requires an accepted teacher demonstration with actual execution receipts")
    if task["split"] != "train":
        raise ValueError("Development and test studies cannot enter SFT")
    samples = []
    for index, (event, audits, receipts) in enumerate(bound_actions(record)):
        payload = event["payload"]
        reply = payload["raw_reply"]
        if not receipts:
            continue
        if reply.get("teacher_model") != "gpt-6.1-sol":
            raise ValueError("SFT target is not a public GPT-6.1 Sol decision")
        samples.append(
            dict(
                collection_id=record["study_id"],
                task_id=task["task_id"],
                split="train",
                teacher="gpt-6.1-sol",
                observation=payload["observation"],
                teacher_public_decision=reply["advice"],
                receipt_ids=receipts,
                trajectory_id=record["study_id"],
                decision_index=index,
                quality_review_receipt=review_receipt,
            )
        )
    if not samples:
        raise ValueError("No executed public teacher decision was found")
    return samples


def rl_trajectory(record, task, review):
    checked_review(record, review)
    if task["split"] != "train":
        raise ValueError("Development and test studies cannot enter RLOO")
    actions = []
    audits = [e["payload"] for e in record["events"] if e["kind"] == "decision_audit"]
    for event, bound, receipts in bound_actions(record):
        payload = event["payload"]
        if payload["observation"]["task_contract"]["task_id"] != task["task_id"]:
            raise ValueError("The trajectory task differs from the frozen training task")
        action = dict(payload["raw_reply"])
        action["student_executed_components"] = sorted(
            {component for audit in bound for component in audit["retained_student_components"]}
        )
        action["receipt_ids"] = receipts
        action["decision_ids"] = [audit["decision_id"] for audit in bound]
        actions.append(action)
    policy_sha = actions[0]["policy_sha256"] if actions else record.get("pinned_policy_sha256")
    if not policy_sha:
        raise ValueError("The failed/empty trajectory lacks its frozen policy identity")
    returns = scientific_return(
        process_gains=review["process_gains"],
        terminal_validity=review["terminal_validity"],
        unsupported_claims=review["unsupported_claims"],
        audits=audits,
    )
    return dict(
        task_id=task["task_id"],
        split="train",
        trajectory_id=record["study_id"],
        initial_state_sha256=record["initial_state_sha256"],
        old_policy_sha256=policy_sha,
        budget_seconds=task["total_wall_seconds"],
        actions=actions,
        closeout=record["closeout"],
        receipts=record["receipts"],
        audits=audits,
        return_metadata=returns,
        **{"return": returns["value"]},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["sft", "rloo_group"])
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--study", type=Path, action="append", required=True)
    parser.add_argument("--review", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(args.study) != len(args.review):
        parser.error("Each study requires its independent review receipt")
    task = json.loads(args.task.read_bytes())
    records = [live_record(path) for path in args.study]
    reviews = [json.loads(path.read_bytes()) for path in args.review]
    if args.stage == "sft":
        samples = [
            sample
            for record, review, path in zip(records, reviews, args.review)
            for sample in sft_samples(record, task, review, str(path))
        ]
        payload = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in samples)
    else:
        trajectories = [rl_trajectory(record, task, review) for record, review in zip(records, reviews)]
        validate_group(trajectories)
        payload = json.dumps(dict(trajectories=trajectories), ensure_ascii=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError("An exported trajectory cannot be overwritten")
    from .storage import write_json

    if args.stage == "rloo_group":
        write_json(args.output, json.loads(payload), immutable=True)
    else:
        # Single-writer CLI publishes JSONL through a unique fsynced temporary.
        import os
        import uuid

        partial = args.output.with_name("." + args.output.name + "." + uuid.uuid4().hex)
        try:
            with partial.open("x", encoding="utf-8") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(partial, args.output)
        finally:
            partial.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
