import json
import time

import pytest

from conjecture_solver.research_oversight import durable_signature
from conjecture_solver.research_service import Lab, ResearchService, put, sha


def service(tmp_path):
    s = ResearchService.create(tmp_path / "study", "A finite physical hypothesis", wall_seconds=300)
    s.freeze_protocol("Keep measurements distinct from interpretations.")
    (s.work / "calc.py").write_text("print(4)\n")
    return s


def receipt(s, identifier="exp_base", *, status="succeeded", payload=None, **kw):
    w = s.root / "experiments" / identifier / "workspace"
    w.mkdir(parents=True)
    (w / "calc.py").write_text("print(4)\n")
    (w / "result.json").write_text(
        json.dumps(payload if payload is not None else {"onset": None, "error": 0.02})
    )
    binding = dict(
        source="calc.py",
        args=[],
        inputs={"calc.py": sha(w / "calc.py")},
        capability=None,
        runtime_sha256=None,
    )
    r = dict(
        id=identifier,
        created_at=time.time(),
        status=status,
        stage="exploration",
        binding=binding,
        commitment=None,
        outputs=["result.json"],
        artifacts={p.name: dict(sha256=sha(p), bytes=p.stat().st_size) for p in w.iterdir()},
        **kw,
    )
    put(s.root / "experiments" / f"{identifier}.json", r)
    return r


def test_notes_link_receipts_and_survive_reopen_without_accepting_claim(tmp_path):
    s = service(tmp_path)
    r = receipt(s)
    n = s.note("No onset was detected.", experiments=[r["id"]])
    assert n["authority"] == "worker_note"
    assert n["evidence_bindings"][r["id"]]
    assert s.note("No onset was detected.", experiments=[r["id"]])["id"] == n["id"]
    again = ResearchService(s.root)
    assert again.notes()["notes"][0]["id"] == n["id"]
    assert not again.status()["completed"]
    with pytest.raises(FileNotFoundError):
        s.note("Invented result", experiments=["exp_missing"])


def test_corrections_preserve_original_observation(tmp_path):
    s = service(tmp_path)
    r = receipt(s)
    first = s.note("The barrier explains it.", kind="interpretation", experiments=[r["id"]])
    second = s.note(
        "Numerical diffusion is also possible.", kind="interpretation", supersedes=first["id"]
    )
    notes = s.notes()["notes"]
    assert next(n for n in notes if n["id"] == first["id"])["superseded"]
    assert not next(n for n in notes if n["id"] == second["id"])["superseded"]
    brief = s.brief()
    assert first["id"] not in [n["id"] for n in brief["notes"]]
    assert second["id"] in [n["id"] for n in brief["notes"]]


def test_next_test_records_competing_predictions_before_experiment(tmp_path):
    s = service(tmp_path)
    n = s.note(
        "Refine the mesh",
        kind="next_test",
        alternatives={"diffusion": "onset shifts", "barrier": "pressure and onset converge"},
        estimated_seconds=90,
    )
    assert n["alternatives"]["diffusion"] == "onset shifts"
    s.validate_experiment_context(None, "diagnostic", n["id"])
    ordinary = s.note("A provisional thought", kind="interpretation")
    with pytest.raises(ValueError, match="next_test"):
        s.validate_experiment_context(None, "diagnostic", ordinary["id"])
    with pytest.raises(ValueError):
        s.note("invalid", kind="next_test", estimated_seconds=float("nan"))
    with pytest.raises(ValueError):
        s.note("invalid", kind="observation", alternatives={"a": "b"})


def test_brief_is_bounded_with_explicit_omissions_and_retrieval(tmp_path):
    s = service(tmp_path)
    for i in range(90):
        receipt(s, f"exp_{i:03}", status="failed" if i % 3 == 0 else "succeeded")
        s.note(f"Interpretation {i}: " + "x" * 1000, kind="interpretation")
    brief = s.brief(max_bytes=4096)
    assert len(json.dumps(brief, ensure_ascii=False).encode()) <= 4096
    assert brief["counts"]["experiments"] == 90
    assert brief["counts"]["execution"]["failed"] == 30
    assert brief["omitted"]["notes"] > 0
    assert "lab.notes" in brief["retrieval"]["notebook"]
    assert len(s.notes(limit=20, offset=20)["notes"]) == 20


def test_generated_brief_does_not_count_as_new_research(tmp_path):
    s = service(tmp_path)
    before = durable_signature(s)
    s.write_brief()
    assert durable_signature(s) == before
    assert (s.work / "RESEARCH_BRIEF.md").is_file()
    assert (s.root / "research_brief.json").is_file()
    s.note("Need to check the boundary conditions", kind="question")
    assert durable_signature(s) != before


def test_comparison_preserves_null_missing_and_failure_without_fake_zero(tmp_path):
    s = service(tmp_path)
    a = receipt(s, "exp_a")
    b = receipt(s, "exp_b", status="failed")
    c = receipt(s, "exp_c", payload={"error": 0.01})
    x = Lab(s.root).compare(
        [a["id"], b["id"], c["id"]],
        {"onset": ["result.json", "onset"], "error": ["result.json", "error"]},
    )
    assert x["rows"][0]["metrics"]["onset"]["status"] == "null"
    assert x["rows"][1]["metrics"]["error"]["status"] == "unavailable"
    assert x["rows"][1]["metrics"]["error"]["value"] is None
    assert x["rows"][2]["metrics"]["onset"]["status"] == "unavailable"
    assert x["rows"][2]["metrics"]["error"]["value"] == 0.01
    assert x["rows"][0]["metrics"]["error"]["sha256"]
    assert "best" not in x


def test_comparison_rejects_mutated_results_and_nonfinite_values(tmp_path):
    s = service(tmp_path)
    r = receipt(s, payload={"metric": float("nan")})
    x = s.compare([r["id"]], {"value": ["result.json", "metric"]})
    assert x["rows"][0]["metrics"]["value"]["status"] == "unavailable"
    (s.root / "experiments" / r["id"] / "workspace/result.json").write_text('{"metric":0}')
    with pytest.raises(ValueError, match="changed"):
        s.compare([r["id"]], {"value": ["result.json", "metric"]})


def test_comparison_uses_existing_json_path_grammar_and_rejects_expressions(tmp_path):
    s = service(tmp_path)
    r = receipt(s, payload={"rows": [{"n": 4}]})
    x = s.compare([r["id"]], {"n": ["result.json", "$.rows[0].n"]})
    assert x["rows"][0]["metrics"]["n"]["value"] == 4
    x = s.compare([r["id"]], {"n": ["result.json", "rows[*].n"]})
    assert x["rows"][0]["metrics"]["n"]["status"] == "unavailable"
    x = s.compare([r["id"]], {"n": ["../../research.json", "hypothesis"]})
    assert x["rows"][0]["metrics"]["n"]["status"] == "unavailable"


def test_experiment_links_record_debug_lineage_without_repairing_hypothesis(tmp_path, monkeypatch):
    s = service(tmp_path)
    parent = receipt(s, status="failed")
    plan = s.note("Fix indexing without changing the physical hypothesis", kind="next_test")

    class Child:
        pid = 99999999

    monkeypatch.setattr(
        "conjecture_solver.research_service.subprocess.Popen", lambda *a, **k: Child()
    )
    child = s.run(
        "calc.py",
        outputs=["result.json"],
        parent_experiment=parent["id"],
        purpose="debug",
        plan=plan["id"],
        stage="exploration",
    )
    assert child["parent_experiment"] == parent["id"]
    assert child["purpose"] == "debug" and child["plan"] == plan["id"]
    assert child["created_at"] >= plan["created_at"]
    assert not s._all("commitments")
    assert (
        s.run(
            "calc.py",
            outputs=["result.json"],
            parent_experiment=parent["id"],
            purpose="debug",
            plan=plan["id"],
            stage="exploration",
        )["id"]
        == child["id"]
    )


def test_memory_remains_optional_and_old_studies_work(tmp_path):
    s = service(tmp_path)
    s.manifest["schema_version"] = 2
    put(s.root / "research.json", s.manifest)
    assert ResearchService(s.root).brief()["notes"] == []
    assert not (s.root / "notebook").exists()
    assert not s.status()["completed"]


def test_old_unanswered_question_survives_recent_note_volume(tmp_path):
    s = service(tmp_path)
    question = s.note("Does numerical diffusion dominate?", kind="question")
    for n in range(105):
        s.note(f"Routine implementation note {n}", kind="implementation")
    brief = s.brief()
    assert question["id"] in [n["id"] for n in brief["notes"]]
    assert brief["counts"]["notes"] == 106


def test_host_tsv_retains_failed_attempts_and_debug_links(tmp_path):
    import csv

    from conjecture_solver.research_audit import write_report

    s = service(tmp_path)
    a = receipt(s, status="failed")
    b = receipt(s, "exp_child", parent_experiment=a["id"], purpose="debug")
    write_report(s, {"status": "running"})
    with (s.root / "experiments.tsv").open() as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    assert rows[0]["execution"] == "failed"
    assert rows[1]["parent"] == a["id"] and rows[1]["id"] == b["id"]
    assert rows[1]["purpose"] == "debug"


def test_brief_handles_pending_review_without_a_verdict(tmp_path):
    s = service(tmp_path)
    r = receipt(s)
    put(
        s.root / "reviews/review_pending.json",
        dict(
            id="review_pending",
            created_at=time.time(),
            status="queued",
            claim="root",
            experiments=[r["id"]],
            disposition="supported",
        ),
    )
    brief = s.write_brief()
    assert brief["accepted_claims"] == []
    assert brief["recent_reviews"][0]["status"] == "queued"
    assert brief["recent_reviews"][0]["next_test"] is None
    assert not brief["completed"]
