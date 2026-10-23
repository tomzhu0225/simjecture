"""Behavior logging and missing-coverage guards for actual-return learning."""

import argparse
import importlib.util
import json
from pathlib import Path

import pytest
from simjecture_monitor.events import digest, put
from simjecture_monitor.host import MonitorSupervisor

from conjecture_solver.research_service import ResearchService


def test_sampled_actions_keep_the_behavior_probability_and_greedy_shadow(tmp_path):
    service = ResearchService.create(
        tmp_path / "study", "A bounded monitoring experiment", wall_seconds=600
    )
    instructions = tmp_path / "task.txt"
    instructions.write_text("Inspect scientific progress without changing acceptance criteria.")
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
    sup = MonitorSupervisor(args, policy="sampled", task="Observe", seed=71)
    state = dict(subject="worker", events=[])
    packet = dict(state=state, packet_sha256=digest(state))
    probabilities = dict(
        defer=0.7, request_worker_help=0.2, wake_director=0.05, request_repair_judge=0.05
    )
    decision = dict(
        choice="defer", probabilities=probabilities, packet_sha256=packet["packet_sha256"]
    )
    try:
        for i in range(20):
            sup._record_decision(packet, decision, received_at=i)
        records = [
            json.loads(p.read_text())["decision"] for p in sup.monitor_dir.glob("decision-*.json")
        ]
        assert len({r["choice"] for r in records}) > 1
        assert decision["choice"] == "defer"
        for row in records:
            assert row["selection_kind"] == "sampled"
            assert row["greedy_choice"] == "defer"
            assert row["behavior_probability"] == pytest.approx(probabilities[row["choice"]])
    finally:
        sup.close_monitor()


def exporter():
    path = Path(__file__).parents[1] / "scripts/export_returns.py"
    spec = importlib.util.spec_from_file_location("return_export", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_argmax_only_traces_are_rejected_as_on_policy_training_data(tmp_path):
    root = tmp_path / "episode"
    root.mkdir()
    put(root / "TRIAL.json", dict(stage="completed", started_at=1, ended_at=3, case="harness"))
    put(
        root / "monitor/decision-1.json",
        dict(
            received_at=2,
            packet={},
            decision={"choice": "defer", "probabilities": {"defer": 1}},
            error=None,
        ),
    )
    with pytest.raises(ValueError, match="Non-sampled behavior"):
        exporter().export(tmp_path, tmp_path / "data.json")


def test_incomplete_monitor_coverage_is_retained_and_excluded(tmp_path):
    root = tmp_path / "episode"
    root.mkdir()
    put(root / "TRIAL.json", dict(stage="completed", started_at=1, ended_at=3, case="harness"))
    put(
        root / "monitor/decision-1.json",
        dict(received_at=2, packet={}, decision=None, error="Connection failure"),
    )
    result = exporter().export(tmp_path, tmp_path / "data.json")
    assert result["episodes"] == []
    assert result["excluded"][0]["episode"] == "episode"
    assert (root / "monitor/decision-1.json").exists()
