"""Regression scenarios extracted from the ten-hour reconnection investigation."""

import argparse
import json
import time

import pytest

from conjecture_solver.research_audit import output_findings, write_report
from conjecture_solver.research_oversight import durable_signature, trace_summary
from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.research_supervisor import ResearchSupervisor


def make(tmp_path, *, required=False):
    s = ResearchService.create(
        tmp_path / "study", "A bounded physical hypothesis", wall_seconds=120
    )
    if required:
        s.freeze_requirements({"require_method_review": True})
    instructions = tmp_path / "instructions"
    instructions.write_text("Use FLASH first. Do not replace an observed failure with speculation.")
    s.freeze_protocol(instructions.read_text())
    (s.work / "calc.py").write_text("print('numerical calculation')\n")
    args = argparse.Namespace(
        campaign=s.root,
        state_dir=s.root / "supervisor",
        instructions_file=instructions,
        wall_seconds=120,
        turn_seconds=10,
        backend="codex",
        executable="unused",
        model="fixture",
        judge_model="fixture",
    )
    return s, ResearchSupervisor(args)


def proposal(s, **kw):
    return s.method(
        source="calc.py",
        model="resistive MHD",
        geometry="x inflow, y finite ends",
        observable="topology change",
        validation="time-integrated diffusion",
        rationale="Use the specified physical model and runtime",
        **kw,
    )


def transcript(path, *, text="I will launch the refinement now.", command=None):
    events = [{"type": "item.completed", "item": {"type": "agent_message", "text": text}}]
    if command:
        events.append(
            {
                "type": "item.completed",
                "item": {"type": "command_execution", "command": command, "exit_code": 0},
            }
        )
    path.write_text("\n".join(map(json.dumps, events)))


def judge_response(directory, decision="continue"):
    verdict = dict(
        decision=decision,
        rationale="The observed evidence supports this methods decision.",
        findings=[] if decision == "continue" else ["No actual solver benchmark"],
        next_action="Execute the next evidence case.",
        prerequisites=[] if decision == "continue" else ["Run an evolution benchmark"],
    )
    transcript(directory / "response.json", text=json.dumps(verdict))
    with (directory / "response.json").open("a") as f:
        f.write('\n{"type":"turn.completed","usage":{}}\n')


def test_repeated_intentions_recover_session_without_changing_deadline(tmp_path):
    s, sup = make(tmp_path)
    deadline = sup.state["deadline"]
    sup.state["worker_cursor"] = "stuck-thread"
    for n in range(3):
        d = sup.directory / f"turn-{n}"
        d.mkdir()
        transcript(d / "response.json")
        sup.observe_turn(d, durable_signature(s))
    assert "worker_cursor" not in sup.state
    assert sup.state["session_recoveries"] == 1
    assert sup.state["no_progress_streak"] == 3
    assert sup.state["deadline"] == deadline
    assert "Do not repeat" in sup.prompt()
    assert not s.status()["completed"]


def test_actual_edit_and_distinct_action_reset_stall(tmp_path):
    s, sup = make(tmp_path)
    d = sup.directory / "turn-test"
    d.mkdir()
    transcript(d / "response.json", command="python calc.py")
    before = durable_signature(s)
    sup.state["no_progress_streak"] = 3
    sup.observe_turn(d, before)
    assert sup.state["no_progress_streak"] == 0
    sup.observe_turn(d, durable_signature(s))
    assert sup.state["no_progress_streak"] == 1  # repeating the same action isn't new progress
    before = durable_signature(s)
    (s.work / "calc.py").write_text("print('corrected evolution')")
    sup.observe_turn(d, before)
    assert sup.state["no_progress_streak"] == 0


def test_private_reasoning_excluded_from_observer(tmp_path):
    p = tmp_path / "trace"
    transcript(p)
    with p.open("a") as f:
        f.write('\n{"type":"item.completed","item":{"type":"reasoning","text":"PRIVATE"}}')
    assert "PRIVATE" not in json.dumps(trace_summary(p))


def test_methods_gate_requires_approval_and_invalidates_changed_source(tmp_path, monkeypatch):
    s, sup = make(tmp_path, required=True)
    with pytest.raises(ValueError, match="Submit lab.method"):
        s.run("calc.py", outputs=["result.json"])
    m = proposal(s)
    with pytest.raises(ValueError, match="independent review"):
        s.run("calc.py", outputs=["result.json"], method=m["id"])
    monkeypatch.setattr(sup, "launch", lambda d, p, judge=False: judge_response(d) or 0)
    sup.process_methods()
    s.check_method(s._binding("calc.py", (), (), None), m["id"], "evidence")
    assert not s.status()["completed"]  # methods approval is not a scientific conclusion
    (s.work / "calc.py").write_text("print('different solver')")
    with pytest.raises(ValueError, match="changed"):
        s.check_method(s._binding("calc.py", (), (), None), m["id"], "evidence")


def test_method_rejection_does_not_block_exploration(tmp_path, monkeypatch):
    s, sup = make(tmp_path, required=True)
    m = proposal(s)
    monkeypatch.setattr(sup, "launch", lambda d, p, judge=False: judge_response(d, "revise") or 0)
    sup.process_methods()
    b = s._binding("calc.py", (), (), None)
    with pytest.raises(ValueError, match="independent review"):
        s.check_method(b, m["id"], "evidence")
    s.check_method(b, None, "exploration")


def test_explicit_instrument_requirement_cannot_be_waived(tmp_path):
    s, _ = make(tmp_path)
    s.freeze_requirements({"required_capability_prefixes": ["flash-"]})
    with pytest.raises(ValueError, match="required capabilities"):
        proposal(s)
    with pytest.raises(ValueError, match="required capabilities"):
        s.run("calc.py", outputs=["result.json"])
    s.check_method(s._binding("calc.py", (), (), None), None, "exploration")
    with pytest.raises(ValueError, match="immutable"):
        s.freeze_requirements({"required_capability_prefixes": []})


def test_host_progress_review_does_not_depend_on_worker_request(tmp_path, monkeypatch):
    s, sup = make(tmp_path)
    sup.state["last_oversight_at"] = time.time() - 901
    calls = []

    def launch(d, p, judge=False):
        calls.append((p, judge))
        judge_response(d, "revise")
        return 0

    monkeypatch.setattr(sup, "launch", launch)
    sup.run_oversight()
    assert len(calls) == 1 and calls[0][1]
    assert "Use FLASH first" in calls[0][0]
    assert sup.state["oversight_feedback"]["decision"] == "revise"
    assert "No actual solver benchmark" in sup.prompt()
    sup.run_oversight()
    assert len(calls) == 1  # reviews are rate-limited
    assert not s.status()["reviews"]


def test_malformed_methods_review_never_opens_gate(tmp_path, monkeypatch):
    s, sup = make(tmp_path, required=True)
    m = proposal(s)
    monkeypatch.setattr(
        sup, "launch", lambda d, p, judge=False: transcript(d / "response.json", text="okay") or 0
    )
    sup.process_methods()
    assert s._read("methods", m["id"])["status"] == "queued"
    with pytest.raises(ValueError):
        s.check_method(s._binding("calc.py", (), (), None), m["id"], "evidence")


def test_live_report_distinguishes_execution_from_science(tmp_path):
    s, sup = make(tmp_path)
    c = s.commit(
        "A minimal repaired prediction",
        source="calc.py",
        cases=[["a"], ["b"]],
        acceptance="both controls pass",
        rationale="preserve original counterexamples",
    )
    sup.state["status"] = "budget_exhausted"
    write_report(s, sup.state)
    report = json.loads((s.root / "research_report.json").read_text())
    assert report["audit"]["scientific_status"] == "unresolved"
    assert report["audit"]["coverage"][0]["missing"] == 2
    assert c["id"] in (s.root / "STUDY_LEDGER.md").read_text()


def test_output_quality_flags_false_checks_and_nonfinite_json(tmp_path):
    (tmp_path / "a.json").write_text('{"value":NaN}')
    (tmp_path / "b.json").write_text('{"checks":{"current_sheet_resolved":false}}')
    findings = output_findings(tmp_path, ["a.json", "b.json"])
    assert {f["kind"] for f in findings} == {"invalid_json", "failed_checks"}


def test_methods_review_includes_actual_commissioning_code(tmp_path):
    s, _ = make(tmp_path)
    w = s.root / "experiments" / "exp_test" / "workspace"
    w.mkdir(parents=True)
    (w / "benchmark.py").write_text("# Only a Laplacian unit test; never evolves the solver")
    (w / "result.json").write_text('{"passed":true}')
    from conjecture_solver.research_service import sha

    record = dict(
        id="exp_test",
        status="succeeded",
        binding={"source": "benchmark.py", "inputs": {"benchmark.py": sha(w / "benchmark.py")}},
        outputs=["result.json"],
        artifacts={p.name: dict(sha256=sha(p)) for p in w.iterdir()},
    )
    put(s.root / "experiments/exp_test.json", record)
    m = proposal(s, validation_experiments=["exp_test"])
    assert "never evolves" in m["evidence"][0]["sources"]["benchmark.py"]


def test_worker_death_cannot_leave_supervisor_waiting_forever(tmp_path):
    s, _ = make(tmp_path)
    import os

    from conjecture_solver.mvp_launch import read_process_identity

    identity = read_process_identity(os.getpid()).model_dump(mode="json")
    identity["starttime"] = "definitely-not-this-process"
    put(
        s.root / "experiments/exp_dead.json",
        dict(
            id="exp_dead",
            status="running",
            created_at=time.time(),
            worker_identity=identity,
            binding={},
            outputs=[],
            commitment=None,
        ),
    )
    r = s.status()["experiments"][0]
    assert r["status"] == "failed"
    assert "disappeared" in r["error"]
    assert not s.status()["completed"]


def test_new_capabilities_append_without_replacing_original_identity(tmp_path, monkeypatch):
    s, _ = make(tmp_path)
    s.manifest["capabilities"] = str(tmp_path / "registry")
    s.manifest["capability_hashes"] = {"flash-original": "original-hash"}

    class Registry:
        hashes = {"flash-original": "original-hash", "flash-built": "new-hash"}

        def get(self, name):
            return argparse.Namespace(contract_hash=self.hashes[name])

    registry = Registry()
    monkeypatch.setattr(
        "conjecture_solver.research_methods.MVPCapabilityRegistry.discover", lambda p: registry
    )
    added = s.register_capability("flash-built")
    assert added["runtime_sha256"] == "new-hash"
    assert s.capability_hashes() == registry.hashes
    registry.hashes["flash-original"] = "replacement"
    with pytest.raises(ValueError, match="immutable"):
        s.register_capability("flash-original")
    registry.hashes["flash-built"] = "replacement"
    with pytest.raises(ValueError, match="immutable"):
        s.register_capability("flash-built")


def test_method_status_stays_compact_without_repeating_source(tmp_path):
    s, _ = make(tmp_path)
    proposal(s)
    compact = s.status(compact=True)
    assert "sources" not in compact["methods"][0]
    assert "evidence" not in compact["methods"][0]


def test_durable_review_request_interrupts_busy_native_turn(tmp_path):
    s, sup = make(tmp_path)
    script = tmp_path / "busy-native"
    script.write_text(
        "#!/usr/bin/env python3\nimport json,time\nfrom pathlib import Path\n"
        "print(json.dumps({'type':'thread.started','thread_id':'busy-thread'}),flush=True)\n"
        f"Path({str(s.root / 'reviews/review_ready.json')!r}).write_text("
        "json.dumps({'id':'review_ready','status':'queued'}))\n"
        "while True:\n print(json.dumps({'type':'heartbeat'}),flush=True)\n time.sleep(.1)\n"
    )
    script.chmod(0o755)
    sup.args.executable = str(script)
    sup.args.turn_seconds = 30
    d = sup.directory / "turn-busy"
    d.mkdir()
    started = time.monotonic()
    assert sup.launch(d, "Submit review then keep producing output") == 124
    assert time.monotonic() - started < 10
    assert sup.state["worker_cursor"] == "busy-thread"
    assert sup.worker_checkpoint_requested()


def test_conditional_approval_cannot_open_methods_gate(tmp_path, monkeypatch):
    s, sup = make(tmp_path, required=True)
    m = proposal(s)

    def launch(d, prompt, judge=False):
        transcript(
            d / "response.json",
            text=json.dumps(
                dict(
                    decision="continue",
                    rationale="Conditionally approve after fresh commissioning.",
                    findings=[],
                    next_action="Run the missing evolution benchmark.",
                    prerequisites=["End-to-end execution of the bound implementation"],
                )
            ),
        )
        return 0

    monkeypatch.setattr(sup, "launch", launch)
    sup.process_methods()
    assert s._read("methods", m["id"])["status"] == "queued"
    binding = s._binding("calc.py", (), (), None)
    with pytest.raises(ValueError, match="independent review"):
        s.check_method(binding, m["id"], "evidence")
    # Also reject imported/malformed historical approval with unresolved conditions.
    m["verdict"] = {"decision": "continue", "prerequisites": ["unmet condition"]}
    put(s.root / "methods" / (m["id"] + ".json"), m)
    with pytest.raises(ValueError, match="independent review"):
        s.check_method(binding, m["id"], "evidence")


def test_timing_and_parity_context_is_retained_for_review(tmp_path):
    s, sup = make(tmp_path)
    from tests.test_research_service import completed

    (s.work / "calc.py").write_text(
        "from pathlib import Path\nPath('result.json').write_text('{}')"
    )
    for purpose in ["timing", "parity"]:
        record = completed(s, stage="exploration", purpose=purpose)
        assert record["purpose"] == purpose
        assert record["stage"] == "exploration"
    brief = s.brief()
    assert {e["purpose"] for e in brief["recent_experiments"]} == {"timing", "parity"}
    prompt = sup.oversight_prompt({"snapshot": brief})
    assert '"stage": "exploration"' in prompt
    assert "mark it unknown" in prompt
