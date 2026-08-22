from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from conjecture_solver.llm import CompletionResult, ModelRoute
from conjecture_solver.mvp_agent import BubblewrapSandbox, MVPAgentConfig, MVPAgentRunner
from conjecture_solver.mvp_control import (
    CampaignPaused,
    begin_or_resume_clock,
    pause_at_boundary,
    read_clock,
    read_pause_state,
)


def _action(**values: Any) -> str:
    return json.dumps(values)


class PauseAfterFirstClient:
    def __init__(self, output: Path, contents: list[str]) -> None:
        self.output = output
        self.contents = contents
        self.calls: list[dict[str, Any]] = []

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> CompletionResult:
        from conjecture_solver.mvp_control import ControlCommand, write_control

        self.calls.append({"messages": messages, "kwargs": kwargs})
        write_control(self.output, ControlCommand.PAUSE, source="test")
        return CompletionResult(
            request_id=f"request_{len(self.calls)}",
            model="test-model",
            content=self.contents[len(self.calls) - 1],
            finish_reason="stop",
            usage={"prompt_tokens": 11, "completion_tokens": 3, "total_tokens": 14},
            route=ModelRoute.DEFAULT,
            route_reason="test",
        )


class ScriptedClient:
    def __init__(self, contents: list[str]) -> None:
        self.contents = contents
        self.calls: list[dict[str, Any]] = []

    def complete(self, messages: list[dict[str, str]], **kwargs: Any) -> CompletionResult:
        self.calls.append({"messages": messages, "kwargs": kwargs})
        return CompletionResult(
            request_id=f"resume_{len(self.calls)}",
            model="test-model",
            content=self.contents[len(self.calls) - 1],
            finish_reason="stop",
            usage={"prompt_tokens": 8, "completion_tokens": 2, "total_tokens": 10},
            route=ModelRoute.DEFAULT,
            route_reason="test",
        )


@pytest.mark.skipif(shutil.which("bwrap") is None, reason="bubblewrap is unavailable")
def test_runner_pauses_at_action_boundary_without_a_report(tmp_path: Path) -> None:
    output = tmp_path / "pause-run"
    config = MVPAgentConfig(
        max_iterations=4,
        max_wall_seconds=30,
        max_command_seconds=10,
        max_workspace_bytes=16 * 1024 * 1024,
        max_file_bytes=2 * 1024 * 1024,
        max_memory_bytes=1024 * 1024 * 1024,
        enforce_repair_loop=False,
    )
    first = PauseAfterFirstClient(
        output,
        [
            _action(
                action="list_files",
                research_note="Inspect the workspace before pausing.",
                path=".",
            )
        ],
    )
    runner = MVPAgentRunner(
        hypothesis="An operator may pause after the current action finishes.",
        output_directory=output,
        completion_client=first,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    )
    with pytest.raises(CampaignPaused):
        runner.run()

    assert not (output / "mvp_report.json").exists()
    paused = read_pause_state(output)
    assert paused is not None
    assert paused.iterations == 1
    clock = read_clock(output)
    assert clock is not None
    assert clock.state == "paused"
    events = [json.loads(line) for line in (output / "transcript.jsonl").read_text().splitlines()]
    assert any(record.get("event") == "campaign_paused" for record in events)
    assert first.calls  # the first model turn ran
    # The next model turn must not have been requested.
    assert len(first.calls) == 1

    resumed = MVPAgentRunner(
        hypothesis=runner.hypothesis,
        output_directory=output,
        completion_client=ScriptedClient(
            [
                _action(
                    action="finish",
                    research_note="Resume after the requested pause.",
                    final_answer="The campaign resumed from the action boundary.",
                )
            ]
        ),
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    )
    report = resumed.run()
    assert report.status == "completed"
    assert read_pause_state(output) is None
    finished = read_clock(output)
    assert finished is not None
    assert finished.state == "finished"
    assert "resumed from the action boundary" in report.final_answer


def test_resumed_runner_enforces_the_accumulated_wall_budget(tmp_path: Path) -> None:
    output = tmp_path / "accumulated-budget"
    t0 = datetime(2026, 8, 15, tzinfo=UTC)
    begin_or_resume_clock(output, now=t0)
    pause_at_boundary(output, iterations=0, now=t0 + timedelta(seconds=2))
    client = ScriptedClient([])
    config = MVPAgentConfig(
        max_wall_seconds=1,
        max_command_seconds=1,
        max_workspace_bytes=8 * 1024 * 1024,
        max_file_bytes=1024 * 1024,
        max_memory_bytes=256 * 1024 * 1024,
        enforce_repair_loop=False,
    )
    runner = MVPAgentRunner(
        hypothesis="A resume cannot replenish an exhausted wall-time envelope.",
        output_directory=output,
        completion_client=client,
        sandbox=BubblewrapSandbox(output / "workspace", config),
        config=config,
    )
    report = runner.run()
    assert report.status == "budget_exhausted"
    assert report.elapsed_wall_seconds >= 2
    assert report.started_at == t0
    assert client.calls == []
