"""Offline integrity checks. Fixtures never call a teacher, model or physical solver."""

import argparse
import hashlib
import json
import py_compile
import sys
import tempfile
import types
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def rejects(function, exception=ValueError):
    try:
        function()
    except exception:
        return
    raise AssertionError("Invalid data was accepted")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-only", action="store_true", help="Verify published contracts without mounting sealed test bytes")
    args = parser.parse_args()
    from research_decision.contracts import (
        DECISION_COMPONENTS,
        decision_audit,
        fingerprint,
        observation,
        phase_conclusion,
    )
    from research_decision.evaluation import C_WEIGHTS, D_WEIGHTS, checkpoint_result, score, stopping_update
    from research_decision.journal import Journal
    from research_decision.rloo import leave_one_out, rollout_importance, scientific_return, validate_group

    checks = []
    train = [
        json.loads(line) for line in (ROOT / "tasks/train.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    dev = [json.loads(line) for line in (ROOT / "tasks/dev.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(train) == 80 and len(dev) == 16
    assert Counter(t["difficulty"] for t in train) == {1: 20, 2: 20, 3: 20, 4: 20}
    assert Counter(t["difficulty"] for t in dev) == {1: 4, 2: 4, 3: 4, 4: 4}
    assert Counter(t["domain"] for t in train) == {"plasma": 64, "cross": 16}
    assert Counter(t["domain"] for t in dev) == {"plasma": 13, "cross": 3}
    assert len({t["task_id"] for t in train + dev}) == 96
    assert not {t["mechanism_group"] for t in train} & {t["mechanism_group"] for t in dev}
    manifest = json.loads((ROOT / "tasks/test_manifest.json").read_bytes())
    assert manifest["task_count"] == 20 and manifest["known_count"] == manifest["open_count"] == 10
    assert manifest["levels"] == {"1": 5, "2": 5, "3": 5, "4": 5}
    if not args.public_only:
        assert (
            hashlib.sha256((ROOT / "sealed/test.aesgcm").read_bytes()).hexdigest()
            == manifest["ciphertext_sha256"]
        )
    assert not list((ROOT / "sealed").glob("*.key"))
    assert len((ROOT / "data/sft_collection_manifest.jsonl").read_text(encoding="utf-8").splitlines()) == 240
    checks.append("116 task counts, difficulty balance, domains, split keys and sealed ciphertext commitment")
    for path in (ROOT / "schemas").glob("*.json"):
        Draft202012Validator.check_schema(json.loads(path.read_bytes()))
    state = observation(
        task=train[0],
        hypotheses=["fixture"],
        physical_models=[],
        available_resources={},
        completed_receipts=[],
        verified_evidence=[],
        necessary_history=[],
        remaining_wall_seconds=10,
        observed_at=1,
    )
    Draft202012Validator(json.loads((ROOT / "schemas/research_state.schema.json").read_bytes())).validate(
        state
    )
    rejects(
        lambda: observation(
            task=train[0],
            hypotheses=[],
            physical_models=[],
            available_resources={"hidden_answer": "fixture"},
            completed_receipts=[],
            verified_evidence=[],
            necessary_history=[],
            remaining_wall_seconds=10,
            observed_at=1,
        )
    )
    rejects(
        lambda: observation(
            task=train[0],
            hypotheses=[],
            physical_models=[],
            available_resources={},
            completed_receipts=[dict(finished_at=2, status="succeeded")],
            verified_evidence=[],
            necessary_history=[],
            remaining_wall_seconds=10,
            observed_at=1,
        )
    )
    checks.append(
        "schema validity, observation whitelist, hidden-field rejection and future-result rejection"
    )
    sources = {key: "host" for key in DECISION_COMPONENTS}
    audit = decision_audit(
        study_id="fixture",
        decision_id="d",
        state=state,
        original_advice={},
        executed_plan={},
        component_sources=sources,
        override_reasons={key: "fixture takeover" for key in sources},
    )
    rejects(
        lambda: decision_audit(
            study_id="fixture",
            decision_id="d",
            state=state,
            original_advice={},
            executed_plan={},
            component_sources=sources,
            override_reasons={},
        )
    )
    result = scientific_return(
        process_gains=[dict(evidence_id="fixture-e", verified=True, value=1, causal_decision_ids=["d"])],
        terminal_validity=1,
        unsupported_claims=0,
        audits=[audit],
    )
    assert result["process_credit"] == result["terminal_credit"] == 0
    values = leave_one_out([1, 2, 3, 4])
    assert abs(sum(values)) < 1e-12 and values[0] == -2 and values[-1] == 2
    assert rollout_importance(0) == 1 and rollout_importance(10) == 2
    assert 0 < rollout_importance(-10) < 1
    trajectories = [
        dict(
            task_id="fixture",
            initial_state_sha256="s",
            old_policy_sha256="p",
            budget_seconds=10,
            closeout={"unresolved": ["fixture"]},
            return_value=i,
        )
        for i in range(4)
    ]
    for item in trajectories:
        item["return"] = item.pop("return_value")
    assert all(abs(a - b) < 1e-12 for a, b in zip(validate_group(trajectories), values))
    trajectories[-1]["task_id"] = "other-fixture"
    rejects(lambda: validate_group(trajectories))
    checks.append(
        "takeover receives no positive scientific credit, override reasons and trajectory LOO group consistency"
    )
    with tempfile.TemporaryDirectory() as directory:
        journal = Journal(Path(directory) / "events.sqlite")
        first = journal.append(study_id="fixture", event_id="a", kind="fixture", payload={"value": 1})
        assert journal.append(study_id="fixture", event_id="a", kind="fixture", payload={"value": 1}) == first
        rejects(
            lambda: journal.append(study_id="fixture", event_id="a", kind="fixture", payload={"value": 2})
        )
        journal.append(study_id="fixture", event_id="b", kind="fixture", payload={"value": 3})
        records = journal.export("fixture")
        assert len(records) == 2 and records[1]["previous_hash"] == first
        for event in records:
            claimed = event.pop("event_hash")
            assert fingerprint(event) == claimed
        journal.close()
    checks.append("transactional event retries, conflicting retries and event hash chain")
    from research_decision.simjecture_bridge import DecisionLab
    from research_decision.train_adapter import retain_recent_checkpoints

    class FixtureLab:
        def __init__(self, root):
            self.calls = []

        def status(self):
            return {"remaining_seconds": 1234}

        def run(self, source, args=(), **kwargs):
            self.calls.append((source, args, kwargs))
            return {"id": "fixture-experiment", "status": "queued"}

    fixture_module = types.ModuleType("conjecture_solver.research_service")
    fixture_module.Lab = FixtureLab
    sys.modules["conjecture_solver.research_service"] = fixture_module
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "research").mkdir()
        (root / "research/fixture.py").write_text("# no scientific computation\n", encoding="utf-8")
        lab = DecisionLab(root, arm="simjecture")
        lab.run("fixture.py", outputs=["fixture.json"])
        assert lab.native.calls[0][2]["timeout"] == 1234
        audit = next(
            event["payload"] for event in lab.journal.export(root.name) if event["kind"] == "decision_audit"
        )
        Draft202012Validator(json.loads((ROOT / "schemas/decision_audit.schema.json").read_bytes())).validate(
            audit
        )
        assert not audit["student_positive_credit_eligible"]
        lab.journal.close()
        checkpoints = root / "checkpoints"
        for index in range(4):
            path = checkpoints / f"rloo-update-{index:06d}"
            path.mkdir(parents=True)
            (path / "manifest.json").write_text("{}")
        (checkpoints / "retain.json").write_text('["rloo-update-000000"]')
        retain_recent_checkpoints(checkpoints)
        assert (checkpoints / "rloo-update-000000").exists()
        assert not (checkpoints / "rloo-update-000001").exists()
        assert (checkpoints / "pruned-manifests/rloo-update-000001.json").exists()
    checks.append(
        "native Lab entry-point timeout inheritance, baseline audit schema and pinned-checkpoint retention"
    )
    assert sum(C_WEIGHTS.values()) == sum(D_WEIGHTS.values()) == 100
    assert score(C_WEIGHTS, C_WEIGHTS) == score(D_WEIGHTS, D_WEIGHTS) == 100
    closeout = phase_conclusion(
        supported=[],
        falsified=[],
        unresolved=["fixture"],
        scope="fixture scope",
        evidence_ids=[],
        termination_reason="timeout",
    )
    assert closeout["include_in_C"] and closeout["include_in_D"]
    result = dict(reliable_improvement=False, reliable_regression=False)
    selection = {"best_checkpoint": "sft"}
    for index in range(4):
        selection = stopping_update(selection, result, f"fixture-{index}")
    assert selection["stop"] and selection["best_checkpoint"] == "sft"
    rejects(lambda: checkpoint_result([dict(comparison="original_baseline")], 1))
    checks.append(
        "independent 100-point scores, timeout inclusion, four-evaluation stopping and incumbent comparison"
    )
    for directory in [ROOT / "scripts", ROOT / "research_decision"]:
        for path in directory.glob("*.py"):
            py_compile.compile(str(path), doraise=True)
    checks.append("Python syntax compilation without importing training or inference runtimes")
    report = dict(
        scope="offline fixtures, never live experiment counters",
        sealed_payload_checked=not args.public_only,
        status="offline_checks_passed",
        checks=checks,
        model_or_teacher_calls=0,
        physics_solver_executions=0,
        training_updates=0,
        runtime_qualifications="not_executed",
    )
    (ROOT / "reports/offline_checks.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
