"""Regression for the parent/repair review deadlock found in the fresh Kepler demo."""

import argparse
import json
import time

import pytest

from conjecture_solver.research_service import ResearchService
from conjecture_solver.research_supervisor import ResearchSupervisor


def setup_reviews(tmp_path, monkeypatch):
    service = ResearchService.create(
        tmp_path / "study", "A finite scheduling fixture", wall_seconds=90
    )
    service.freeze_protocol("Scheduling fixture; provider verdicts are simulated.")
    (service.work / "calc.py").write_text(
        "from pathlib import Path\nPath('result.json').write_text('{\"value\":4}')\n"
    )

    def run(**kwargs):
        receipt = service.run("calc.py", outputs=["result.json"], **kwargs)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            record = service._read("experiments", receipt["id"])
            if record["status"] not in {"queued", "running"}:
                assert record["status"] == "succeeded", record
                return record["id"]
            time.sleep(0.03)
        pytest.fail("Recorded fixture execution did not finish")

    parent_run = run()
    child = service.commit(
        "A repaired scheduling fixture",
        source="calc.py",
        cases=[[]],
        acceptance="The finite fixture returns four",
        rationale="Repair the tested bound only.",
    )
    child_run = run(commitment=child["id"])
    # Submit the child first as well as sorting it first on disk. Neither order
    # should cause the reviewer to be called before its accepted prerequisites.
    repair = service.review(
        [child_run],
        "The fresh finite repair fixture passed.",
        claim=child["id"],
        challenge={
            "strategy": "Test the finite case",
            "experiments": [child_run],
            "outcome": "All cases returned four",
        },
    )
    root = service.review([parent_run], "Fixture parent is falsified.", disposition="falsified")
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Scheduling fixture; provider verdicts are simulated.")
    supervisor = ResearchSupervisor(
        argparse.Namespace(
            campaign=service.root,
            state_dir=service.root / "supervisor",
            wall_seconds=90,
            instructions_file=instructions,
            backend="codex",
            model="fixture",
            judge_model="fixture",
        )
    )
    service = supervisor.service
    original_all = service._all
    monkeypatch.setattr(
        service,
        "_all",
        lambda name: (
            sorted(original_all(name), key=lambda r: r["claim"] == "root")
            if name == "reviews"
            else original_all(name)
        ),
    )
    calls = []

    def launch(directory, prompt, *, judge=False):
        assert judge
        packet = json.loads((directory / "packet.json").read_text())
        calls.append(packet["target_claim"]["id"])
        return 0

    monkeypatch.setattr(supervisor, "launch", launch)
    return supervisor, root, repair, child, calls


def reviewer(monkeypatch, *, root_decision="approved"):
    def parse(path, backend, **kwargs):
        claim = json.loads((path.parent / "packet.json").read_text())["target_claim"]["id"]
        blocked = claim == "root" and root_decision == "needs_revision"
        return dict(
            claim_id=claim,
            decision="needs_revision" if blocked else "approved",
            disposition="unresolved"
            if blocked
            else "falsified"
            if claim == "root"
            else "supported",
            rationale="Synthetic reviewer verdict for dependency-order regression testing.",
            evidence_gaps=["Missing parent control"] if blocked else [],
            next_test="Run the parent control" if blocked else None,
        )

    monkeypatch.setattr("conjecture_solver.research_supervisor.parse_judge_stream", parse)


def test_parent_is_reviewed_before_earlier_child_request(tmp_path, monkeypatch):
    sup, root, repair, child, calls = setup_reviews(tmp_path, monkeypatch)
    reviewer(monkeypatch)
    sup.process_reviews()
    assert calls == ["root", child["id"]]
    assert sup.service.review_status(root["id"])["status"] == "resolved"
    assert sup.service.review_status(repair["id"])["status"] == "resolved"
    assert sup.service.status()["completed"]


def test_parent_gap_defers_repair_without_retries_or_checkpoint_loop(
    tmp_path, monkeypatch
):
    sup, root, repair, child, calls = setup_reviews(tmp_path, monkeypatch)
    reviewer(monkeypatch, root_decision="needs_revision")
    sup.process_reviews()
    sup.process_reviews()
    assert calls == ["root"]
    assert not sup.worker_checkpoint_requested()
    pending = sup.service.review_status(repair["id"])
    assert pending["status"] == "queued"
    assert pending["blocked_by_claims"] == ["root"]
    assert not sup.service.status()["completed"]
    # A new parent submission can be reviewed, then release the original repair.
    sup.service.review(root["experiments"], "Revised parent argument.", disposition="falsified")
    reviewer(monkeypatch)
    assert sup.worker_checkpoint_requested()
    sup.process_reviews()
    assert calls == ["root", "root", child["id"]]
    assert sup.service.status()["completed"]
