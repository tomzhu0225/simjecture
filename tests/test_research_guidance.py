"""Guided handoff and scoped readiness regressions from the reconnection campaigns."""

import json
from pathlib import Path

import pytest

from conjecture_solver.research_service import ResearchService, put
from tests.test_research_oversight import judge_response, make, proposal

ANCHOR = Path("demos/resistive_mhd_island_coalescence/guided_commission.json")


def guided_service(tmp_path, monkeypatch):
    s = ResearchService.create(tmp_path / "study", "A fresh scaling hypothesis")
    monkeypatch.setattr(
        ResearchService,
        "capability_hashes",
        lambda self: {"flash-island-coalescence-resistive-mhd-4.8": "fixture-runtime"},
    )
    return s


def test_real_demo_package_resume_preserves_agent_edits_and_checks_snapshot(tmp_path, monkeypatch):
    s = guided_service(tmp_path, monkeypatch)
    s.install_guidance(ANCHOR)
    descriptor = s.manifest["guided_commissioning"]
    assert descriptor["scientific_evidence_eligible"] is False
    original = (s.work / "guided/island_coalescence.py").read_bytes()
    assert b"h5py.File" in original
    (s.work / "guided/island_coalescence.py").write_text("# agent adaptation\n")
    reopened = ResearchService(s.root)
    reopened.install_guidance(ANCHOR)
    assert (s.work / "guided/island_coalescence.py").read_text() == "# agent adaptation\n"
    snapshot = s.root / "guided_commissioning_input/guided/island_coalescence.py"
    assert snapshot.read_bytes() == original
    snapshot.write_text("tampered")
    with pytest.raises(ValueError, match="identity changed"):
        ResearchService(s.root)


def test_guidance_requires_installed_capability_and_prelaunch_install(tmp_path, monkeypatch):
    s = ResearchService.create(tmp_path / "study", "A fresh hypothesis")
    with pytest.raises(ValueError, match="not installed"):
        s.install_guidance(ANCHOR)
    monkeypatch.setattr(
        s, "capability_hashes", lambda: {"flash-island-coalescence-resistive-mhd-4.8": "fixture"}
    )
    put(s.root / "study-launch.json", {})
    with pytest.raises(ValueError, match="after launch"):
        s.install_guidance(ANCHOR)


def test_instrument_approval_cannot_authorize_hypothesis_evidence(tmp_path):
    s, sup = make(tmp_path, required=True)
    instrument = proposal(s, scope="instrument", validation_experiments=[commission(s)])
    instrument.update(status="resolved", verdict={"decision": "continue"})
    put(s.root / "methods" / (instrument["id"] + ".json"), instrument)
    binding = s._binding("calc.py", (), (), None)
    s.check_method(binding, instrument["id"], "exploration")
    with pytest.raises(ValueError, match="does not authorize"):
        s.check_method(binding, instrument["id"], "evidence")
    production = proposal(s)
    assert production["scope"] == "production"
    assert production["id"] != instrument["id"]
    production.update(status="resolved", verdict={"decision": "continue"})
    put(s.root / "methods" / (production["id"] + ".json"), production)
    s.check_method(binding, production["id"], "evidence")


def test_scoped_review_receives_actual_scope_and_preserves_host_gate(tmp_path, monkeypatch):
    s, sup = make(tmp_path, required=True)
    p = proposal(s, scope="instrument", validation_experiments=[commission(s)])

    def launch(directory, prompt, **kw):
        assert "judge ONLY" in prompt
        packet = json.loads((directory / "packet.json").read_text())
        assert packet["method"]["scope"] == "instrument"
        judge_response(directory)
        return 0

    monkeypatch.setattr(sup, "launch", launch)
    sup.process_methods()
    assert s._read("methods", p["id"])["verdict"]["decision"] == "continue"
    with pytest.raises(ValueError, match="does not authorize"):
        s.check_method(s._binding("calc.py", (), (), None), p["id"], "evidence")


def test_supplied_validation_cannot_masquerade_as_fresh_output(tmp_path):
    s, _ = make(tmp_path)
    (s.work / "result.json").write_text('{"checks":{"passed":true}}')
    with pytest.raises(ValueError, match="cannot also be supplied inputs"):
        s.run("calc.py", inputs=["result.json"], outputs=["result.json"], stage="exploration")


def test_non_evidence_annotation_reaches_review_without_metadata_rerun(tmp_path):
    from conjecture_solver.research_audit import output_findings
    from tests.test_research_service import completed, service

    s = service(tmp_path)
    exp = completed(s)
    record = s._read("experiments", exp["id"])
    workspace = s.root / "experiments" / exp["id"] / "workspace"
    name = record["outputs"][0]
    (workspace / name).write_text('{"checks":{"scientific_evidence_eligible":false}}')
    assert output_findings(workspace, [name])[0]["kind"] == "eligibility_annotation"
    from conjecture_solver.research_service import sha

    record["artifacts"][name]["sha256"] = sha(workspace / name)
    put(s.root / "experiments" / (exp["id"] + ".json"), record)
    packet = s.packet(
        dict(
            claim="root",
            disposition="falsified",
            conclusion="A counterexample",
            experiments=[exp["id"]],
        )
    )
    assert packet["experiments"][0]["output_findings"][0]["kind"] == "eligibility_annotation"
    assert not s.status()["completed"]  # review is still required
    record["stage"] = "exploration"
    put(s.root / "experiments" / (exp["id"] + ".json"), record)
    with pytest.raises(ValueError, match="Exploration is not claim evidence"):
        s.packet(packet["request"])


@pytest.mark.parametrize("mode", ["minimal", "structured", "frontier"])
def test_guided_study_launch_and_resume_in_each_mode(tmp_path, monkeypatch, mode):
    import argparse
    import sys

    from conjecture_solver.agent_supervisor import AgentSupervisor
    from conjecture_solver.research_supervisor import ResearchSupervisor
    from conjecture_solver.study import configure_parser, run

    caps = tmp_path / "caps"
    caps.mkdir()
    cap = json.loads(
        Path("capabilities/flash-island-coalescence-resistive-mhd-4.8.json").read_text()
    )
    cap.update(runtime_root="/usr", executable="bin/python3", identity_files=[], environment={})
    (caps / "flash.json").write_text(json.dumps(cap))
    h, i = tmp_path / "h", tmp_path / "i"
    h.write_text("A bounded scaling hypothesis")
    i.write_text("Reproduce the supplied anchor before adapting it.")
    parser = argparse.ArgumentParser()
    configure_parser(parser)
    argv = [
        "--campaign",
        str(tmp_path / "study"),
        "--hypothesis-file",
        str(h),
        "--instructions-file",
        str(i),
        "--mode",
        mode,
        "--executable",
        sys.executable,
        "--capabilities",
        str(caps),
        "--guided-commission",
        str(ANCHOR),
    ]
    monkeypatch.setattr(AgentSupervisor, "run", lambda self: 0)
    monkeypatch.setattr(ResearchSupervisor, "run", lambda self: 0)
    assert run(parser.parse_args(argv)) == 0
    # Resume without the original package path; use the immutable snapshot.
    assert run(parser.parse_args(argv[:-2])) == 0


def test_guided_resume_rejects_changed_package(tmp_path, monkeypatch):
    import shutil

    s = guided_service(tmp_path, monkeypatch)
    s.install_guidance(ANCHOR)
    spec = json.loads(ANCHOR.read_text())
    alternative = tmp_path / "changed-package"
    alternative.mkdir()
    for name in spec["files"]:
        target = alternative / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ANCHOR.parent / name, target)
    spec["operator_validation"] += " Changed after launch."
    manifest = alternative / "guided.json"
    manifest.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match="immutable"):
        s.install_guidance(manifest)


def commission(s):
    from tests.test_research_service import completed

    (s.work / "calc.py").write_text(
        "from pathlib import Path\n"
        'Path("result.json").write_text(\'{"checks":{"completed":true}}\')\n'
    )
    return completed(s, stage="exploration")["id"]


def test_instrument_readiness_rejects_missing_or_stale_validation(tmp_path):
    s, _ = make(tmp_path)
    with pytest.raises(ValueError, match="successful recorded validation"):
        proposal(s, scope="instrument")
    exp = commission(s)
    with (s.work / "calc.py").open("a") as f:
        f.write("# changed implementation\n")
    with pytest.raises(ValueError, match="current source/runtime"):
        proposal(s, scope="instrument", validation_experiments=[exp])


def test_reproduce_anchor_uses_packaged_arguments_and_rejects_edits(tmp_path, monkeypatch):
    s = guided_service(tmp_path, monkeypatch)
    s.install_guidance(ANCHOR)
    calls = []
    monkeypatch.setattr(s, "run", lambda source, **kw: calls.append((source, kw)) or kw)
    result = s.reproduce_anchor(timeout=12)
    assert calls[0][0] == "guided/island_coalescence.py"
    assert result["args"][0] == "--eta"
    assert result["stage"] == "exploration"
    assert not set(result["inputs"]) & set(result["outputs"])
    (s.work / calls[0][0]).write_text("# changed")
    with pytest.raises(ValueError, match="workspace changed"):
        s.reproduce_anchor()
