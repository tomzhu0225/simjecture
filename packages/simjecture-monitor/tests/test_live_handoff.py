"""A real supervisor must resume after a repair supersedes a provisional report."""

import argparse
import importlib.util
import json
import os
import time
from pathlib import Path

from simjecture_monitor.host import MonitorSupervisor

from conjecture_solver.research_service import ResearchService


def test_driver_delivers_repair_outcome_before_accepting_existing_report(tmp_path, monkeypatch):
    source = Path(__file__).parents[1] / "scripts/live_trials.py"
    spec = importlib.util.spec_from_file_location("monitor_live_trials", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    service = ResearchService.create(
        tmp_path / "study", "Repair a status adapter after a failed run", wall_seconds=600
    )
    instructions = tmp_path / "instructions.txt"
    instructions.write_text("Bounded engineering validation; preserve scientific requirements.")
    args = argparse.Namespace(
        campaign=service.root,
        state_dir=service.root / "supervisor",
        wall_seconds=600,
        turn_seconds=120,
        instructions_file=instructions,
        backend="codex",
        model="worker",
        judge_model="judge",
        director_enabled=True,
    )
    sup = MonitorSupervisor(args, policy="rules", task="Repair the status adapter")
    monkeypatch.setattr(module, "prepare", lambda *a: (sup, "Repair the status adapter"))
    monkeypatch.setattr(module, "verify", lambda *a: dict(returncode=0))
    monkeypatch.setattr(sup, "monitor_tick", lambda *a: None)
    monkeypatch.setattr(sup, "run_director", lambda *a, **kw: None)
    launches = []
    report = sup.service.work / "REPORT.txt"
    result = sup.service.work / "results.json"

    def launch(directory, prompt):
        launches.append(prompt)
        result.write_text(json.dumps({"runs": []}))
        if len(launches) == 1:
            report.write_text("The adapter is currently blocking diagnostics.")
            os.utime(report, (time.time() - 10, time.time() - 10))
            sup.state["monitor_authority_results"] = [
                dict(
                    stage="completed",
                    ended_at=time.time() - 5,
                    verdict={"decision": "grant"},
                    deployment={"status": "applied", "id": "grant_fixture"},
                )
            ]
        else:
            assert "grant_fixture" in prompt
            assert "rerun the affected operation" in prompt
            report.write_text("Rechecked diagnostics through the repaired adapter.")
        return 0

    monkeypatch.setattr(sup, "launch", launch)
    module.run(sup.root, "harness", "rules", None)
    final = json.loads((sup.root / "TRIAL.json").read_text())
    assert len(launches) == 2
    assert not final["pending_feedback_after_final_report"]
