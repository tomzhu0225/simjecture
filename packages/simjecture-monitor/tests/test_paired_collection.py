import hashlib
import importlib.util
import json
import sys
from pathlib import Path

from simjecture_monitor.events import put


def module(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "paired_collection_test", scripts / "paired_continuations.py"
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_reporting_falsification_is_complete_but_tampering_is_rejected(tmp_path, monkeypatch):
    loaded = module(monkeypatch)
    work = tmp_path / "research"
    work.mkdir()
    files = [
        "experiment.py",
        "run_warpx.py",
        "original_analysis.py",
        "environment.json",
        "inputs",
        "harness/bridge.py",
    ]
    manifest = dict(criteria=dict(required_configurations=[[64, 40], [256, 160]]), artifacts={})
    for name in files:
        path = work / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(name)
        manifest["artifacts"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    measurements = []
    for name, cells, steps, passed in [("control", 64, 40, True), ("comparison", 256, 160, False)]:
        measurements.append(
            dict(
                name=name,
                relative_field_error=0.01,
                relative_charge_residual=2e-12 if passed else 2e-11,
                original_checks_passed=passed,
            )
        )
        put(
            work / "runs" / name / "receipt.json",
            dict(status="succeeded", cells=cells, steps=steps),
        )
    (work / "REPORT.txt").write_text(
        "The control passed; the comparison falsifies the original charge check."
    )
    put(
        work / "results.json",
        dict(
            runs=measurements,
            diagnosis="The original charge check failed for the comparison",
            unresolved=[],
        ),
    )

    def verify(work, output):
        put(output, dict(verified_runs=measurements))
        return dict(returncode=0)

    monkeypatch.setattr(loaded.live, "verify", verify)
    assert loaded.quality(tmp_path, manifest)["verified_quality"] == 1
    (work / "experiment.py").write_text("changed protected wrapper")
    assert loaded.quality(tmp_path, manifest)["verified_quality"] == 0


def test_design_keeps_assignments_out_of_runtime_roots_and_freezes_order(tmp_path, monkeypatch):
    module(monkeypatch)
    scripts = Path(__file__).parents[1] / "scripts"
    spec = importlib.util.spec_from_file_location(
        "paired_design_test", scripts / "run_paired_pilot.py"
    )
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    monkeypatch.setattr(loaded.subprocess, "check_output", lambda *a, **k: "revision")
    first = loaded.design(tmp_path)
    assert loaded.design(tmp_path) == first
    roots = [b["root"] for c in first["cases"] for p in c["pairs"] for b in p["branches"]]
    assert len(roots) == len(set(roots)) == 32
    assert all(r.startswith("trial-") and len(r) == 38 for r in roots)
    assert all(
        {b["action"] for b in p["branches"]} == {c["intervention"], "defer"}
        for c in first["cases"]
        for p in c["pairs"]
    )
    assert json.loads((tmp_path / "DESIGN.json").read_text())["parent_continuations"] == 32
    assert sys.modules.get("live_trials")
