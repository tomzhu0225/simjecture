"""Input validation tests that do not need a numerical execution backend."""

from __future__ import annotations

import pytest

from conjecture_solver.research_service import ResearchService

INVALID_SECONDS = [float("nan"), float("inf"), float("-inf"), 0, -1, True, "60", 10**400]


@pytest.mark.parametrize("seconds", INVALID_SECONDS)
def test_invalid_deadline_does_not_poison_new_study_directory(tmp_path, seconds):
    root = tmp_path / "study"
    with pytest.raises(ValueError, match="positive finite deadline"):
        ResearchService.create(root, "A bounded arithmetic claim.", wall_seconds=seconds)
    assert not list(root.iterdir())
    service = ResearchService.create(root, "A bounded arithmetic claim.", wall_seconds=60)
    assert service.manifest["deadline"] > service.manifest["created_at"]


@pytest.mark.parametrize("seconds", INVALID_SECONDS)
def test_invalid_timeout_is_rejected_before_creating_experiment(tmp_path, seconds, monkeypatch):
    service = ResearchService.create(tmp_path / "study", "A bounded arithmetic claim.")
    (service.work / "calc.py").write_text("print(4)\n")
    spawned = []
    monkeypatch.setattr(service, "_spawn_experiment", lambda record: spawned.append(record))
    with pytest.raises(ValueError, match="positive finite timeout"):
        service.run("calc.py", outputs=["result.json"], timeout=seconds, stage="exploration")
    assert not list((service.root / "experiments").iterdir())
    assert not spawned
    receipt = service.run("calc.py", outputs=["result.json"], timeout=0.5, stage="exploration")
    assert receipt["timeout"] == 0.5
    assert len(spawned) == 1
