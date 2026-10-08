"""Incomplete studies must not break discovery of unrelated campaigns."""

import hashlib

import pytest

from conjecture_solver.mvp_monitor import discover_recent_runs, load_run_snapshot
from conjecture_solver.research_service import ResearchService, put
from conjecture_solver.web.application import SimjectureWebApplication


@pytest.mark.parametrize("damage", ["missing", "modified"])
def test_discovery_isolates_guidance_integrity_failures(tmp_path, damage):
    scans = tmp_path / "studies"
    healthy = ResearchService.create(scans / "healthy", "A complete study")
    damaged = ResearchService.create(scans / "damaged", "An incomplete export")
    original = b"print('commissioned')\n"
    snapshot = damaged.root / "guided_commissioning_input" / "anchor.py"
    snapshot.parent.mkdir()
    if damage == "modified":
        snapshot.write_bytes(b"print('changed')\n")
    damaged.manifest["guided_commissioning"] = {
        "files": [{"path": "anchor.py", "sha256": hashlib.sha256(original).hexdigest()}]
    }
    put(damaged.root / "research.json", damaged.manifest)
    (damaged.root / "director").mkdir(exist_ok=True)
    before = (damaged.root / "research.json").read_bytes()

    found = discover_recent_runs([scans])
    assert [item.run_directory for item in found] == [str(healthy.root)]
    app = SimjectureWebApplication(
        initial_run=healthy.root,
        scan_roots=(scans,),
        runs_root=tmp_path / "web",
        allow_mutations=False,
    )
    cards = app.bootstrap()["campaigns"]
    assert [card["id"] for card in cards] == [app.registry.token_for(healthy.root)]

    # Discovery skips the invalid candidate; it does not repair it or weaken
    # verification when the user explicitly opens or resumes that study.
    with pytest.raises(ValueError, match="snapshot identity changed"):
        load_run_snapshot(damaged.root)
    with pytest.raises(ValueError, match="snapshot identity changed"):
        ResearchService(damaged.root)
    assert (damaged.root / "research.json").read_bytes() == before


def test_discovery_does_not_hide_unexpected_monitor_errors(tmp_path, monkeypatch):
    study = ResearchService.create(tmp_path / "study", "Q")

    def broken_monitor(_path):
        raise RuntimeError("Unexpected monitor failure")

    monkeypatch.setattr("conjecture_solver.mvp_monitor.load_run_snapshot", broken_monitor)
    with pytest.raises(RuntimeError, match="Unexpected monitor failure"):
        discover_recent_runs([study.root])
