from __future__ import annotations

import asyncio
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from textual.widgets import Input, ListView, Static, TextArea

from conjecture_solver.mvp_launch import (
    ManagedCampaign,
    MVPLaunchPlan,
    MVPLaunchRequest,
    ProcessIdentity,
    load_supervisor_record,
    read_process_identity,
    request_graceful_cancel,
    start_managed_campaign,
    write_supervisor_record,
)
from conjecture_solver.mvp_monitor import RunPhase
from conjecture_solver.tui.app import ConjectureSolverApp
from conjecture_solver.tui.screens import (
    ArtifactsScreen,
    AuditLedgerScreen,
    ClaimDetailScreen,
    ContractReviewScreen,
    DashboardScreen,
    NewRunScreen,
)

from .test_mvp_monitor import (
    _action,
    _append_transcript,
    _claim,
    _ledger,
    _manifest,
    _write,
)


def _run(app: ConjectureSolverApp, scenario) -> None:
    async def _inner() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await scenario(pilot)

    asyncio.run(_inner())


def _sleep_command() -> list[str]:
    return [
        sys.executable,
        "-c",
        (
            "import signal, sys, time\n"
            "signal.signal(signal.SIGINT, lambda *_: sys.exit(0))\n"
            "time.sleep(30)\n"
        ),
    ]


def test_tui_loads_existing_run_and_renders_claims(tmp_path: Path) -> None:
    root = tmp_path / "attached"
    root.mkdir()
    hypothesis = (
        "Attach-only dashboards preserve density [cm^-3] and literal [bold] notation."
    )
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _write(
        root / "hypothesis_ledger.json",
        _ledger(
            hypothesis,
            [
                _claim("claim_root", statement=hypothesis),
                _claim(
                    "claim_instrument",
                    statement="The instrument interface was commissioned.",
                    status="supported",
                    kind="instrument",
                    relation="instrument_of",
                    parent_id="claim_root",
                    evidence=2,
                    closed_reason="Commissioning checks passed.",
                ),
            ],
        ),
    )
    _append_transcript(
        root,
        {
            "kind": "assistant",
            "iteration": 4,
            "model": "test-model",
            "usage": {"prompt_tokens": 40, "completion_tokens": 8, "total_tokens": 48},
            "content": _action(
                action="run_capability",
                research_note="Collect the next observation.",
                capability="example-runtime",
                argv=["program.py"],
                stage="evidence",
                active_claim_id="claim_instrument",
            ),
        },
        {
            "kind": "tool_heartbeat",
            "iteration": 4,
            "elapsed_wall_seconds": 12.0,
            "workspace_bytes": 2048,
        },
    )
    app = ConjectureSolverApp(root)

    async def scenario(pilot) -> None:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, DashboardScreen)
        assert screen.snapshot is not None
        assert screen.snapshot.phase is RunPhase.INCOMPLETE
        assert screen.snapshot.current_action is not None
        assert screen.snapshot.current_action.action_name == "run_capability"
        assert any(claim.id == "claim_instrument" for claim in screen.snapshot.claims)
        status = str(app.query_one("#status-line", Static).content)
        assert "RUNNING" not in status
        assert "incomplete" in status.lower()
        current = str(app.query_one("#current-action", Static).content)
        assert "example-runtime" in current
        assert [row.claim.id for row in screen.hypothesis_rows] == ["claim_root"]
        assert [row.claim.id for row in screen.validation_rows] == [
            "claim_instrument"
        ]
        tree = app.query_one("#hypothesis-tree", ListView)
        tree_label = tree.children[0].query_one(Static)
        assert "Attach-only dashboards preserve density" in str(tree_label.content)
        assert "[cm^-3]" in str(tree_label.render())
        validation = app.query_one("#validation-claims", ListView)
        assert "instrument" in str(validation.children[0].query_one(Static).content)
        assert screen.snapshot.token_usage.total_tokens == 48
        usage = str(app.query_one("#usage-line", Static).content)
        assert "48 total" in usage

    _run(app, scenario)


def test_tui_separates_hypothesis_tree_validation_and_audit_ledger(
    tmp_path: Path,
) -> None:
    root = tmp_path / "claim-projections"
    root.mkdir()
    hypothesis = "The root proposition has competing scientific explanations."
    claims = [
        _claim("claim_root", statement=hypothesis),
        _claim(
            "claim_refined",
            statement="A bounded daughter hypothesis refines the root.",
            kind="scientific",
            relation="refines",
            parent_id="claim_root",
        ),
        _claim(
            "claim_alternate",
            statement="A competing daughter hypothesis offers an alternate mechanism.",
            kind="scientific",
            relation="alternate",
            parent_id="claim_root",
        ),
        _claim(
            "claim_instrument",
            statement="The root experiment is numerically qualified.",
            kind="instrument",
            relation="instrument_of",
            parent_id="claim_root",
        ),
        _claim(
            "claim_instrument_v2",
            statement="A revised instrument succeeds the first qualification.",
            kind="instrument",
            relation="succeeds",
            parent_id="claim_instrument",
        ),
        _claim(
            "claim_diagnostic",
            statement="The daughter observable distinguishes the predicted outcome.",
            kind="diagnostic",
            relation="diagnostic_of",
            parent_id="claim_refined",
        ),
    ]
    _write(root / "mvp_manifest.json", _manifest(hypothesis))
    _write(root / "hypothesis_ledger.json", _ledger(hypothesis, claims))
    app = ConjectureSolverApp(root)

    async def scenario(pilot) -> None:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, DashboardScreen)
        assert [row.claim.id for row in screen.hypothesis_rows] == [
            "claim_root",
            "claim_refined",
            "claim_alternate",
        ]
        assert [row.depth for row in screen.hypothesis_rows] == [0, 1, 1]
        assert [row.claim.id for row in screen.validation_rows] == [
            "claim_instrument",
            "claim_instrument_v2",
        ]

        tree = screen.query_one("#hypothesis-tree", ListView)
        tree.focus()
        tree.index = 1
        await pilot.pause()
        assert screen.selected_hypothesis_id == "claim_refined"
        assert [row.claim.id for row in screen.validation_rows] == [
            "claim_diagnostic"
        ]
        hypothesis_items = tuple(tree.children)
        validation = screen.query_one("#validation-claims", ListView)
        validation_items = tuple(validation.children)
        assert "claim_refined" in str(
            screen.query_one("#validation-title", Static).content
        )
        for _ in range(3):
            screen.refresh_snapshot()
            await pilot.pause()
        assert screen.selected_hypothesis_id == "claim_refined"
        assert [row.claim.id for row in screen.validation_rows] == [
            "claim_diagnostic"
        ]
        assert all(
            before is after
            for before, after in zip(hypothesis_items, tree.children, strict=True)
        )
        assert all(
            before is after
            for before, after in zip(validation_items, validation.children, strict=True)
        )

        claims[1]["status"] = "supported"
        claims[1]["closed_reason"] = "A bounded test supports the daughter."
        _write(root / "hypothesis_ledger.json", _ledger(hypothesis, claims))
        screen.refresh_snapshot()
        await pilot.pause()
        assert hypothesis_items[1] is tree.children[1]
        assert "supported" in str(tree.children[1].query_one(Static).content)

        screen.action_claim_detail()
        await pilot.pause()
        assert isinstance(app.screen, ClaimDetailScreen)
        detail = str(app.screen.query_one("#claim-detail", Static).content)
        assert "kind: scientific" in detail
        assert "relation: refines" in detail
        app.screen.action_close()
        await pilot.pause()

        assert isinstance(app.screen, DashboardScreen)
        app.screen.action_audit_ledger()
        await pilot.pause()
        assert isinstance(app.screen, AuditLedgerScreen)
        assert len(app.screen.claims) == len(claims)
        audit = app.screen.query_one("#audit-claims", ListView)
        labels = [str(item.query_one(Static).content) for item in audit.children]
        assert any("scientific" in label for label in labels)
        assert any("instrument" in label for label in labels)
        assert any("diagnostic" in label for label in labels)

    _run(app, scenario)


def test_tui_new_run_form_validation(tmp_path: Path) -> None:
    app = ConjectureSolverApp(scan_roots=[tmp_path])

    async def scenario(pilot) -> None:
        await pilot.pause()
        await app.push_screen(NewRunScreen())
        screen = app.screen
        assert isinstance(screen, NewRunScreen)
        screen.action_review()
        await pilot.pause()
        assert screen.last_error == "A root hypothesis is required."
        screen.query_one("#hypothesis-input", TextArea).text = "short"
        screen.action_review()
        await pilot.pause()
        assert "at least 8 characters" in screen.last_error
        screen.query_one("#hypothesis-input", TextArea).text = (
            "A sufficiently long root hypothesis for the form."
        )
        screen.query_one("#campaign-id", Input).value = "bad id"
        screen.action_review()
        await pilot.pause()
        assert "campaign id" in screen.last_error
        assert not isinstance(app.screen, ContractReviewScreen)
        screen.query_one("#campaign-id", Input).value = "campaign-form-test"
        screen.query_one("#output-directory", Input).value = str(tmp_path / "out")
        request = screen.validate()
        assert request is not None
        assert screen.last_error == ""
        await app.push_screen(ContractReviewScreen(request))
        assert isinstance(app.screen, ContractReviewScreen)
        assert app.screen.request.campaign_id == "campaign-form-test"
        assert app.screen.request.hypothesis.startswith("A sufficiently long")

    _run(app, scenario)


def test_tui_launch_uses_hypothesis_file(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_start(plan: MVPLaunchPlan) -> ManagedCampaign:
        captured["plan"] = plan
        identity = ProcessIdentity(
            pid=1,
            starttime="test",
            argv=plan.argv,
            launched_at="2026-08-14T00:00:00+00:00",
        )
        return ManagedCampaign(
            plan=plan,
            process=subprocess.Popen(  # noqa: S603 - argv is a no-op test process
                [sys.executable, "-c", "pass"],
            ),
            identity=identity,
            log_handle=Path(plan.controller_log).open("ab"),
        )

    monkeypatch.setattr(
        "conjecture_solver.tui.screens.start_managed_campaign",
        fake_start,
    )
    app = ConjectureSolverApp(scan_roots=[tmp_path])

    async def scenario(pilot) -> None:
        await pilot.pause()
        await app.push_screen(NewRunScreen())
        form = app.screen
        assert isinstance(form, NewRunScreen)
        form.query_one("#hypothesis-input", TextArea).text = (
            "Launch must preserve the hypothesis in a file, not a shell string."
        )
        form.query_one("#instruction-input", TextArea).text = (
            "Prefer installed capabilities."
        )
        form.query_one("#campaign-id", Input).value = "campaign-launch-test"
        output = tmp_path / "campaign-launch-test"
        form.query_one("#output-directory", Input).value = str(output)
        request = form.validate()
        assert request is not None
        await app.push_screen(ContractReviewScreen(request))
        assert isinstance(app.screen, ContractReviewScreen)
        app.screen.action_launch()
        await pilot.pause()
        assert "plan" in captured
        plan = captured["plan"]
        assert "--hypothesis-file" in plan.argv
        assert "--hypothesis" not in plan.argv
        assert Path(plan.hypothesis_file).read_text().startswith("Launch must preserve")
        assert plan.instruction_file is not None
        assert isinstance(app.screen, DashboardScreen)
        app.detach_managed()

    _run(app, scenario)


def test_graceful_cancel_signals_only_verified_identity() -> None:
    process = subprocess.Popen(  # noqa: S603 - deterministic local test process
        _sleep_command(),
        start_new_session=True,
    )
    try:
        identity = read_process_identity(process.pid, _sleep_command())
        assert identity is not None
        forged = ProcessIdentity(
            pid=identity.pid,
            starttime="not-the-real-starttime",
            argv=identity.argv,
            launched_at=identity.launched_at,
        )
        assert request_graceful_cancel(forged, wait_interrupt_seconds=0.2) == (
            "process identity does not match; no signal sent"
        )
        assert process.poll() is None
        forged_argv = identity.model_copy(update={"argv": ("not-the-real-command",)})
        assert request_graceful_cancel(
            forged_argv,
            wait_interrupt_seconds=0.2,
        ) == "process identity does not match; no signal sent"
        assert process.poll() is None
        result = request_graceful_cancel(
            identity,
            wait_interrupt_seconds=2.0,
            wait_terminate_seconds=1.0,
        )
        assert result in {"interrupted", "terminated"}
        process.wait(timeout=3)
        assert process.poll() is not None
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=3)


def test_tui_cancel_uses_managed_process(tmp_path: Path) -> None:
    output = tmp_path / "managed"
    output.mkdir()
    request = MVPLaunchRequest(
        hypothesis="Cancel must use a verified child process identity.",
        campaign_id="campaign-cancel-ui",
        output_directory=str(output),
    )
    from conjecture_solver.mvp_launch import materialize_operator_input

    plan = materialize_operator_input(request).model_copy(
        update={"argv": tuple(_sleep_command())}
    )
    campaign = start_managed_campaign(plan)
    app = ConjectureSolverApp(output)
    app.managed = campaign

    async def scenario(pilot) -> None:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, DashboardScreen)
        started = time.monotonic()
        screen.action_cancel()
        assert time.monotonic() - started < 0.1
        await pilot.pause()
        deadline = time.monotonic() + 3
        while (
            screen.last_cancel_message == "cancellation requested"
            and time.monotonic() < deadline
        ):
            await pilot.pause()
        assert screen.last_cancel_message in {"interrupted", "terminated"}
        while campaign.poll() is None and time.monotonic() < deadline:
            await pilot.pause()
        assert campaign.poll() == 0

    try:
        _run(app, scenario)
    finally:
        if campaign.poll() is None:
            campaign.process.send_signal(signal.SIGTERM)
            campaign.process.wait(timeout=3)
        campaign.close()


def test_attach_only_cancel_does_not_signal_unverified_pid(tmp_path: Path) -> None:
    root = tmp_path / "readonly-attach"
    root.mkdir()
    _write(
        root / "mvp_manifest.json",
        _manifest("Attach-only mode must not kill an unverified process."),
    )
    process = subprocess.Popen(  # noqa: S603
        _sleep_command(),
        start_new_session=True,
    )
    app = ConjectureSolverApp(root)

    async def scenario(pilot) -> None:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, DashboardScreen)
        await pilot.press("c")
        await pilot.pause()
        assert "read-only" in screen.last_cancel_message
        assert process.poll() is None

    try:
        _run(app, scenario)
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=3)


def test_crafted_supervisor_cannot_bind_an_unrelated_process(tmp_path: Path) -> None:
    root = tmp_path / "crafted-supervisor"
    root.mkdir()
    crafted_argv = [*_sleep_command(), "mvp", "--output", str(root)]
    process = subprocess.Popen(  # noqa: S603 - deterministic local test process
        crafted_argv,
        start_new_session=True,
    )
    try:
        identity = read_process_identity(process.pid, crafted_argv)
        assert identity is not None
        write_supervisor_record(root, identity)
        assert load_supervisor_record(root) is None
        assert process.poll() is None
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=3)


def test_tui_pause_without_live_process_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "pause-readonly"
    root.mkdir()
    _write(
        root / "mvp_manifest.json",
        _manifest("Pause requires a verified live runner."),
    )
    app = ConjectureSolverApp(root)

    async def scenario(pilot) -> None:
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, DashboardScreen)
        screen.action_pause()
        await pilot.pause()
        assert "no verified running process" in screen.last_control_message

    _run(app, scenario)


def test_help_and_leave_do_not_require_a_live_process(tmp_path: Path) -> None:
    root = tmp_path / "help-run"
    root.mkdir()
    _write(root / "mvp_manifest.json", _manifest("Help describes real controls only."))
    app = ConjectureSolverApp(root)

    async def scenario(pilot) -> None:
        await pilot.pause()
        from conjecture_solver.tui.screens import HelpScreen

        await app.push_screen(HelpScreen())
        assert isinstance(app.screen, HelpScreen)
        help_text = str(app.screen.query_one("#help-body", Static).content)
        assert "next action boundary" in help_text
        assert "Token counts" in help_text
        assert "percentage" in help_text
        app.screen.action_close()
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)
        app.screen.action_leave()
        await pilot.pause()

    _run(app, scenario)


def test_artifact_browser_mounts_populated_list_and_previews_text(
    tmp_path: Path,
) -> None:
    root = tmp_path / "artifact-browser"
    workspace = root / "workspace"
    workspace.mkdir(parents=True)
    _write(root / "mvp_manifest.json", _manifest("Artifacts remain inspectable."))
    _write(workspace / "result.txt", "qualified observation\n")
    app = ConjectureSolverApp(root)

    async def scenario(pilot) -> None:
        await pilot.pause()
        assert isinstance(app.screen, DashboardScreen)
        app.screen.action_artifacts()
        await pilot.pause()
        assert isinstance(app.screen, ArtifactsScreen)
        index = next(
            index
            for index, entry in enumerate(app.screen.entries)
            if entry.relative_path == "workspace/result.txt"
        )
        listing = app.screen.query_one("#artifact-list", ListView)
        listing.index = index
        app.screen.action_preview()
        assert "qualified observation" in str(
            app.screen.query_one("#artifact-preview", Static).content
        )

    _run(app, scenario)
