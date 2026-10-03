"""Regressions from the twelve-hour Al reconnection campaign."""

import json
import shutil
import time

import pytest

from conjecture_solver.research_service import ResearchService, put, sha
from conjecture_solver.study_status import study_status


def service(tmp_path):
    s = ResearchService.create(tmp_path / "study", "A scientific bound", wall_seconds=120)
    (s.work / "calc.py").write_text("print(1)\n")
    return s


def method(s, **kw):
    return s.method(
        source="calc.py",
        model="Model",
        geometry="Domain",
        observable="Quantity",
        validation="Recorded validation",
        rationale="Scientific rationale",
        **kw,
    )


def receipt(s, *, value=2, wall=100, stage="exploration"):
    identifier = "exp_" + "a" * 24
    workspace = s.root / "experiments" / identifier / "workspace"
    workspace.mkdir(parents=True)
    shutil.copy2(s.work / "calc.py", workspace / "calc.py")
    (workspace / "result.json").write_text(json.dumps({"actual_end_ns": value}))
    r = dict(
        id=identifier,
        status="succeeded",
        created_at=time.time(),
        binding=s._binding("calc.py", (), (), None),
        outputs=["result.json"],
        stage=stage,
        execution={"wall_seconds": wall},
        artifacts={
            "result.json": {
                "bytes": (workspace / "result.json").stat().st_size,
                "sha256": sha(workspace / "result.json"),
            }
        },
    )
    put(s.root / "experiments" / (identifier + ".json"), r)
    return r


def test_prose_blockers_identify_field_and_recovery(tmp_path):
    s = service(tmp_path)
    with pytest.raises(ValueError, match=r"blockers\[0\].*limitations"):
        method(s, blockers=["No positive detector calibration"])
    m = method(s, limitations=["No positive detector calibration"])
    assert m["status"] == "queued"
    assert m["limitations"] == ["No positive detector calibration"]


@pytest.mark.parametrize("field", ["blockers", "blocker_experiments", "validation_experiments"])
@pytest.mark.parametrize("value", ["", "exp_a", [None], [{"id": "exp_a"}]])
def test_method_receipt_fields_reject_wrong_types(tmp_path, field, value):
    with pytest.raises(ValueError, match=field):
        method(service(tmp_path), **{field: value})


def test_new_and_legacy_blocker_ids_keep_same_identity(tmp_path):
    s = service(tmp_path)
    r = receipt(s)
    a = method(s, blockers=[r["id"]])
    b = method(s, blocker_experiments=[r["id"]])
    assert a["id"] == b["id"]
    with pytest.raises(ValueError, match="not both"):
        method(s, blockers=[r["id"]], blocker_experiments=[r["id"]])


def test_unknown_receipt_error_is_actionable(tmp_path):
    with pytest.raises(ValueError, match="unknown experiment.*lab.status"):
        method(service(tmp_path), blocker_experiments=["exp_missing"])


def test_analysis_records_without_production_approval(tmp_path, monkeypatch):
    s = service(tmp_path)
    s.freeze_requirements({"require_method_review": True})
    monkeypatch.setattr(s, "_spawn_experiment", lambda _: None)
    with pytest.raises(ValueError, match="Submit lab.method"):
        s.run("calc.py", outputs=["result.json"])
    r = s.analyze("calc.py", outputs=["result.json"])
    assert r["stage"] == "exploration" and r["purpose"] == "diagnostic"
    # A successful analysis cannot be retrospectively promoted to claim evidence.
    r = receipt(s)
    with pytest.raises(ValueError, match="Exploration is not claim evidence"):
        s.review([r["id"]], "This is not approved evidence.", disposition="unresolved")
    with pytest.raises(ValueError, match="approved method"):
        s.analyze("calc.py", outputs=["result.json"], stage="evidence")


def progress(s, r, **kwargs):
    return s.progress(
        experiment=r["id"],
        output="result.json",
        path="actual_end_ns",
        quantity="Physical time",
        unit="ns",
        target=20.5,
        baseline=0,
        estimate_rate=True,
        **kwargs,
    )


def test_progress_cost_is_receipt_backed_and_advisory(tmp_path):
    s = service(tmp_path)
    r = receipt(s, value=2, wall=100)
    p = progress(s, r)
    snapshot = s.status()
    row = snapshot["progress"][0]
    assert row["id"] == p["id"] and row["integrity"] == "verified"
    assert row["estimated_additional_seconds"] == pytest.approx(925)
    assert row["exceeds_remaining_budget"] and not row["target_reached"]
    assert "scientific target" in snapshot["audit"]["budget_warning"]
    assert not snapshot["completed"]
    assert s.brief()["progress"][0]["experiment"] == r["id"]
    assert study_status(s.root)["receipt_progress"][0]["value"] == 2
    assert study_status(s.root)["execution_costs"][0]["wall_seconds"] == 100


def test_progress_mutation_is_visible_without_breaking_status(tmp_path):
    s = service(tmp_path)
    r = receipt(s)
    progress(s, r)
    p = s.root / "experiments" / r["id"] / "workspace/result.json"
    p.write_text('{"actual_end_ns":21}')
    row = s.status()["progress"][0]
    assert row["integrity"] == "invalid" and not row["target_reached"]
    assert row["estimated_additional_seconds"] is None
    with pytest.raises(ValueError, match="changed"):
        progress(s, r)


@pytest.mark.parametrize("value", [None, True, "2", [2]])
def test_progress_requires_actual_numeric_output(tmp_path, value):
    s = service(tmp_path)
    r = receipt(s, value=value)
    with pytest.raises(ValueError, match="finite numeric"):
        progress(s, r)


def test_reached_metric_does_not_close_scientific_claim(tmp_path):
    s = service(tmp_path)
    r = receipt(s, value=21)
    progress(s, r)
    snapshot = s.status()
    assert snapshot["progress"][0]["target_reached"]
    assert not snapshot["completed"]


def test_system_compiler_alternatives_work_in_real_launcher(tmp_path):
    if not shutil.which("cc"):
        pytest.skip("System C compiler not installed")
    s = service(tmp_path)
    (s.work / "compile.py").write_text(
        "from pathlib import Path\nimport subprocess,json\n"
        "Path('probe.c').write_text('#include <stdio.h>\\nint main(){puts(\"42\");return 0;}')\n"
        "subprocess.run(['cc','probe.c','-o','probe'],check=True)\n"
        "value=int(subprocess.check_output(['./probe'],text=True))\n"
        "Path('result.json').write_text(json.dumps({'compiled_value':value}))\n"
    )
    r = s.analyze("compile.py", outputs=["result.json"])
    deadline = time.time() + 30
    while time.time() < deadline:
        r = s._read("experiments", r["id"])
        if r["status"] not in {"running", "queued"}:
            break
        time.sleep(.05)
    assert r["status"] == "succeeded", r
    result = s.root / "experiments" / r["id"] / "workspace/result.json"
    assert json.loads(result.read_text())["compiled_value"] == 42
