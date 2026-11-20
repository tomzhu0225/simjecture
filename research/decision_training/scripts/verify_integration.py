"""Nonphysical end-to-end native worker/review/reward fixtures, never training data."""

import json
import os
import tempfile
import threading
import time
from pathlib import Path


def main():
    from conjecture_solver.execution_pool import MachineRegistry
    from conjecture_solver.research_service import ResearchService

    from research_decision.case import closeout
    from research_decision.collect import live_record, rl_trajectory, sft_samples
    from research_decision.contracts import DECISION_COMPONENTS
    from research_decision.gateway import ScienceGateway
    from research_decision.remote_control import Remote
    from research_decision.review import prepare_packet, validate_review
    from research_decision.rloo import action_advantages, validate_group
    from research_decision.simjecture_bridge import DecisionLab
    from research_decision.storage import read_json, write_json

    root = Path(__file__).resolve().parents[1]
    cfg = read_json(root / "config/pipeline.local.json")
    remote = Remote(cfg)
    os.environ["PATH"] = str(root / "bin") + ":" + os.environ["PATH"]
    task = dict(
        task_id="PREP-TRANSPORT-FIXTURE",
        split="train",
        question="Nonphysical I/O fixture",
        equations="none",
        hypotheses=[],
        total_wall_seconds=90,
        scope_statement="engineering only",
    )
    advice = dict(
        action="propose_experiments",
        experiments=[],
        organization="fixture",
        parameter_justification="fixture",
        model_hierarchy="none",
        budget_allocation={},
        public_justification="No physical task",
        change_of_mind_conditions=[],
        requested_evidence_ids=[],
    )
    packet_template = dict(
        C_components=dict(
            truth_or_valid_evidence=0,
            independent_replication_and_prediction=35,
            numerical_validity_scope_uncertainty=0,
        ),
        D_components=dict(
            experiment_choice_discrimination=0,
            parameters_resolution_scale=0,
            evidence_adaptation=0,
            series_and_budget=0,
        ),
        accepted_for_training=True,
        terminal_validity=0,
        unsupported_claims=0,
        process_gains=[],
        independent_verifications=[],
        auxiliary_novelty=0,
        auxiliary_scientific_value=0,
        rationale="Engineering fixture, no scientific finding",
    )
    checks = []
    with tempfile.TemporaryDirectory(prefix="science-chain-") as scratch:
        socket = Path(scratch) / "gateway.sock"
        with ScienceGateway(socket, remote.route, remote.root) as gateway:
            server = threading.Thread(target=gateway.serve_forever, daemon=True)
            server.start()
            os.environ["SCIENCE_TRANSPORT_SOCKET"] = str(socket)
            try:
                pool = MachineRegistry(cfg["machine_registry"]).freeze(["remote-cpu"])
                trajectories = []
                teacher_samples = []
                for index in range(5):
                    case = (
                        Path(cfg["case_store"])
                        / "diagnostics/integration-fixtures"
                        / ("PREP-" + str(time.time_ns()) + "-" + str(index))
                    )
                    native = ResearchService.create(
                        case,
                        "Nonphysical remote I/O fixture",
                        wall_seconds=90,
                        execution_pool=pool,
                        execution_backend="process-cooperative",
                        artifact_policy="remote",
                        report_reserve_seconds=2,
                        allow_solver_development=True,
                    )
                    write_json(case / "task.json", task)
                    write_json(case / "initial-state.json", dict(task=task, seed=1))
                    arm = "teacher" if index == 0 else "simjecture_sftrl9b"
                    write_json(
                        case / "study-run.json",
                        dict(
                            arm=arm,
                            policy_sha256="fixture-policy",
                            deadline=native.manifest["deadline"],
                            public_resources=cfg["public_resources"],
                        ),
                    )
                    text = "from pathlib import Path\nPath('fixture.bin').write_bytes(b'P'*2097153)\n"
                    if index == 3:
                        text = "raise SystemExit(3)\n"
                    if index == 4:
                        text = "import time\ntime.sleep(5)\n"
                    (case / "research/fixture.py").write_text(text)
                    lab = DecisionLab(case)
                    state = lab.state()
                    if index == 0:
                        identifier = lab.record_teacher_decision(state, advice)
                    else:
                        identifier = "fixture-advice"
                        lab.journal.append(
                            study_id=case.name,
                            event_id=identifier,
                            kind="raw_advice",
                            payload=dict(
                                observation=state,
                                received_at=time.time(),
                                raw_reply=dict(
                                    advice=advice,
                                    input_ids=[100, 101],
                                    response_ids=[102],
                                    behavior_logprob=-1.0,
                                    policy_sha256="fixture-policy",
                                    temperature=0.8,
                                ),
                            ),
                        )
                    receipt = lab.run(
                        "fixture.py",
                        advice_id=identifier,
                        executed_plan=dict(purpose="fixture"),
                        component_sources={k: "student" for k in DECISION_COMPONENTS},
                        outputs=["fixture.bin"],
                        resources=dict(cpus=1, memory_mb=256),
                        stage="exploration",
                        purpose="diagnostic",
                        timeout=0.2 if index == 4 else None,
                    )
                    # Native run submissions remain asynchronous: polling obtains
                    # the actual worker receipt, never a mock completion result.
                    cutoff = time.monotonic() + 40
                    while time.monotonic() < cutoff:
                        native.status()
                        actual = read_json(case / "experiments" / (receipt["id"] + ".json"))
                        if actual["status"] in {
                            "succeeded",
                            "failed",
                            "timed_out",
                            "cancelled",
                            "partial",
                            "interrupted",
                        }:
                            break
                        time.sleep(0.2)
                    if index < 3:
                        assert actual["status"] == "succeeded", actual
                        native.fetch_remote(experiment=receipt["id"], path="fixture.bin")
                        downloaded = case / "experiments" / receipt["id"] / "workspace/fixture.bin"
                        assert downloaded.read_bytes() == b"P" * 2097153
                    elif index == 3:
                        assert actual["status"] == "failed", actual
                    else:
                        assert actual["status"] in {"timed_out", "failed"}, actual
                    closeout(case, "engineering_fixture_complete")
                    lab.journal.close()
                    record = live_record(case)
                    assert record["closeout"]["include_in_C"] and record["closeout"]["include_in_D"]
                    provenance = prepare_packet(case / "blinded-review", record, task)
                    reviewed = validate_review(
                        json.loads(json.dumps(packet_template)),
                        record,
                        provenance,
                        "fixture-independent-session",
                    )
                    assert reviewed["C_components"]["independent_replication_and_prediction"] == 0
                    if index == 0:
                        teacher_samples = sft_samples(record, task, reviewed, "fixture-review-not-production")
                    else:
                        trajectories.append(rl_trajectory(record, task, reviewed))
                validate_group(trajectories)
                assert len(teacher_samples) == 1
                assert all(all(x == 0 for x in action_advantages(t, 0)) for t in trajectories)
                checks.extend(
                    [
                        "native remote asynchronous execution and actual terminal receipt import",
                        "streamed artifact hash and 2097153-byte content verification",
                        "execution failure and timeout remain in C/D closeouts",
                        "blinded independent-review packet and missing-replication zero credit",
                        "teacher public-decision export and same-initial-state four-trajectory RLOO group",
                        "all fixture IDs rejected by the production frozen train-task whitelist",
                    ]
                )
            finally:
                gateway.shutdown()
    report = dict(
        passed=True,
        checks=checks,
        nonphysical_remote_fixtures=5,
        physics_solver_executions=0,
        scientific_studies=0,
        teacher_calls=0,
        training_updates=0,
        production_training_samples_written=0,
    )
    write_json(root / "reports/integration_checks.json", report)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
