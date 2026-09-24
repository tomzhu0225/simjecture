"""Controller journal tests: the researcher never invokes note/plan/parent helpers."""

import argparse
import json
import time

import pytest

from conjecture_solver.provider_retry import ProviderFailure
from conjecture_solver.research_journal import journal_entries, sync_journal
from conjecture_solver.research_oversight import durable_signature
from conjecture_solver.research_service import ResearchService, put, sha
from conjecture_solver.research_supervisor import ResearchSupervisor


def make(tmp_path, wall=3600):
    service = ResearchService.create(tmp_path / "study", "A bounded hypothesis", wall_seconds=wall)
    instructions = tmp_path / "instructions"
    instructions.write_text("Preserve uncertainty; validate every scientific conclusion.")
    args = argparse.Namespace(
        campaign=service.root,
        state_dir=service.root / "supervisor",
        instructions_file=instructions,
        wall_seconds=wall,
        turn_seconds=60,
        backend="codex",
        executable="unused",
        model="fixture",
        judge_model="fixture",
    )
    return service, ResearchSupervisor(args)


def record(s, identifier, *, code="print(1)", status="succeeded", value=0.1):
    w = s.root / "experiments" / identifier / "workspace"
    w.mkdir(parents=True)
    (w / "calc.py").write_text(code)
    (w / "result.json").write_text(json.dumps({"metric": value, "onset": None}))
    body = dict(
        id=identifier,
        created_at=time.time(),
        status=status,
        stage="exploration",
        commitment=None,
        outputs=["result.json"],
        binding=dict(
            source="calc.py",
            inputs={"calc.py": sha(w / "calc.py")},
            args=[],
            capability=None,
            runtime_sha256=None,
        ),
        execution=dict(
            wall_seconds=1.0,
            timed_out=status == "failed",
            returncode=124 if status == "failed" else 0,
        ),
        artifacts={p.name: dict(sha256=sha(p), bytes=p.stat().st_size) for p in w.iterdir()},
    )
    put(s.root / "experiments" / f"{identifier}.json", body)
    return body


def respond(d, ids=("exp_a", "exp_b", "exp_c")):
    answer = {
        "notes": [
            {
                "kind": "interpretation",
                "statement": "The reported metric decreases; physical validity remains untested.",
                "experiments": list(ids),
            }
        ]
    }
    events = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(answer)}},
        {"type": "turn.completed", "usage": {}},
    ]
    (d / "response.json").write_text("\n".join(map(json.dumps, events)))


def test_journal_automatically_records_all_attempts_and_source_changes(tmp_path):
    s, sup = make(tmp_path)
    record(s, "exp_a", status="failed")
    record(s, "exp_b", code="print(2)")
    record(s, "exp_c", code="print(2)")
    prompt = sup.prompt()
    entries = journal_entries(s)
    assert len(entries) == 3 and not s.notes()["notes"]
    assert entries[1]["implementation_changed"]
    assert entries[1]["preceding_attempt_same_entrypoint"] == "exp_a"
    assert entries[1]["explicit_parent"] is None
    assert not entries[0]["implementation_changed"]
    assert entries[2]["execution_details"]["timed_out"]
    assert "exp_a" in prompt and "exp_b" in prompt and "CURRENT RESEARCH STATE" in prompt
    assert "not inferred scientific causality" in entries[0]["relationship_scope"]
    assert not s.status()["completed"]


def test_journal_detects_changed_output_without_inventing_metrics(tmp_path):
    s, _ = make(tmp_path)
    record(s, "exp_a")
    (s.root / "experiments/exp_a/workspace/result.json").write_text('{"metric":99}')
    sync_journal(s)
    result = journal_entries(s)[0]["results"]["result.json"]
    assert "changed" in result["error"]
    assert "reported_values" not in result


def test_refresh_is_idempotent_and_not_research_progress(tmp_path):
    s, _ = make(tmp_path)
    record(s, "exp_a")
    sync_journal(s)
    path = s.root / "journal/attempts/exp_a.json"
    before = path.stat().st_mtime_ns
    signature = durable_signature(s)
    sync_journal(s)
    s.write_brief()
    assert path.stat().st_mtime_ns == before
    assert durable_signature(s) == signature


def test_controller_summarizes_batch_without_worker_request(tmp_path, monkeypatch):
    s, sup = make(tmp_path)
    for i, name in enumerate(["exp_a", "exp_b", "exp_c"]):
        record(s, name, value=1 / (i + 1))
    calls = []

    def launch(d, p, judge=False):
        calls.append((p, judge))
        respond(d)
        return 0

    monkeypatch.setattr(sup, "launch", launch)
    sup.maintain_journal()
    assert len(calls) == 1 and calls[0][1]
    assert "supplied experiment IDs" in calls[0][0]
    assert not s.notes()["notes"]
    brief = s.brief()
    assert brief["controller_summaries"][0]["authority"] == "controller_summary_unreviewed"
    assert "physical validity" in sup.prompt()
    sup.maintain_journal()
    assert len(calls) == 1
    assert not s.status()["completed"]


@pytest.mark.parametrize("failure", ["bad_json", "invented_id", "provider"])
def test_summary_failure_does_not_stop_or_approve_research(tmp_path, monkeypatch, failure):
    s, sup = make(tmp_path)
    for name in ["exp_a", "exp_b", "exp_c"]:
        record(s, name)

    def launch(d, p, judge=False):
        if failure == "provider":
            raise ProviderFailure()
        if failure == "bad_json":
            (d / "response.json").write_text("invalid")
        else:
            respond(d, ("exp_invented",))
        return 0

    monkeypatch.setattr(sup, "launch", launch)
    limit = sup.args.turn_seconds
    sup.maintain_journal()
    assert sup.args.turn_seconds == limit
    assert sup.state["journal_summary_error"]
    assert not list((s.root / "journal/summaries").glob("*.json"))
    assert len(journal_entries(s)) == 3 and not s.status()["completed"]


def test_small_tasks_and_exhausted_summary_budget_use_facts_only(tmp_path, monkeypatch):
    s, sup = make(tmp_path, wall=300)
    for name in ["exp_a", "exp_b", "exp_c"]:
        record(s, name)
    monkeypatch.setattr(
        sup, "launch", lambda *a, **k: pytest.fail("No summary budget for small task")
    )
    sup.maintain_journal()
    assert len(journal_entries(s)) == 3
    sup.service.manifest["deadline"] += 3600
    sup.state["deadline"] += 3600
    sup.state["journal_summary_seconds"] = 301
    sup.maintain_journal()


def test_pending_claim_review_takes_precedence_over_summary(tmp_path, monkeypatch):
    s, sup = make(tmp_path)
    for name in ["exp_a", "exp_b", "exp_c"]:
        record(s, name)
    put(s.root / "reviews/review_pending.json", {"id": "review_pending", "status": "queued"})
    monkeypatch.setattr(sup, "launch", lambda *a, **k: pytest.fail("Claim review must run first"))
    sup.maintain_journal()
    assert len(journal_entries(s)) == 3


def test_nonfinite_numeric_overflow_is_recorded_as_invalid_json(tmp_path):
    s, _ = make(tmp_path)
    record(s, "exp_a")
    w = s.root / "experiments/exp_a/workspace/result.json"
    w.write_text('{"metric":1e999}')
    r = s._read("experiments", "exp_a")
    r["artifacts"]["result.json"] = {"sha256": sha(w), "bytes": w.stat().st_size}
    put(s.root / "experiments/exp_a.json", r)
    sync_journal(s)
    assert "Non-finite" in journal_entries(s)[0]["results"]["result.json"]["error"]
