"""Screens for the optional Simjecture terminal UI."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    ListItem,
    ListView,
    TextArea,
)
from textual.widgets import (
    Label as TextualLabel,
)
from textual.widgets import (
    Static as TextualStatic,
)

from ..mvp_launch import (
    MVPLaunchRequest,
    ResumeError,
    load_supervisor_record,
    materialize_operator_input,
    prepare_resume,
    process_identity_matches,
    request_verified_pause,
    start_managed_campaign,
    validate_campaign_id,
)
from ..mvp_monitor import (
    ClaimSummary,
    MVPRunMonitor,
    MVPRunSnapshot,
    RunPhase,
    contained_path,
    discover_recent_runs,
    format_age,
    format_bytes,
    format_duration,
    installed_capability_descriptors,
    list_contained_artifacts,
)
from .claim_views import (
    ClaimTreeRow,
    audit_row_label,
    build_hypothesis_tree,
    build_validation_tree,
    hypothesis_row_label,
    scientific_ancestor_id,
    validation_row_label,
)

if TYPE_CHECKING:
    from .app import ConjectureSolverApp


class Static(TextualStatic):
    """Static text that preserves scientific notation instead of parsing markup."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("markup", False)
        super().__init__(*args, **kwargs)


class Label(TextualLabel):
    """Plain label used for hypotheses, claims, paths, and audit records."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("markup", False)
        super().__init__(*args, **kwargs)


def _app(screen: Screen[object]) -> ConjectureSolverApp:
    return screen.app  # type: ignore[return-value]


def _phase_class(label: str) -> str:
    lowered = label.lower()
    if lowered == "running":
        return "phase-running"
    if lowered == "completed":
        return "phase-completed"
    if "cancel" in lowered:
        return "phase-cancelled"
    if "fail" in lowered:
        return "phase-failed"
    if lowered == "initialized":
        return "phase-initialized"
    if "pause" in lowered:
        return "phase-paused"
    return "phase-incomplete"


def _default_campaign_id(now: datetime | None = None) -> str:
    stamp = (now or datetime.now(UTC)).strftime("%Y%m%d-%H%M%S")
    return f"campaign-{stamp}"


def _claim_detail_body(claim: ClaimSummary) -> str:
    parent = claim.parent_id or "(none)"
    reason = claim.closed_reason or "(open)"
    return "\n".join(
        [
            f"id: {claim.id}",
            f"kind: {claim.kind or 'unknown'}",
            f"relation: {claim.relation or 'unknown'}",
            f"parent: {parent}",
            f"status: {claim.status}",
            f"evidence contracts: {claim.contract_count}",
            f"linked evidence: {claim.evidence_count}",
            f"closed reason: {reason}",
            "",
            claim.statement or "(empty statement)",
            "",
            "Status is read from the durable ledger, not model prose.",
        ]
    )


def _sync_list_labels(
    listing: ListView,
    labels: tuple[str, ...],
    previous: tuple[str, ...] | None,
) -> tuple[str, ...]:
    """Update claim rows without unmounting an unchanged list every timer tick."""

    if labels == previous:
        return labels

    items = tuple(listing.children)
    shared_count = min(len(items), len(labels))
    for index in range(shared_count):
        if (
            previous is None
            or index >= len(previous)
            or previous[index] != labels[index]
        ):
            items[index].query_one(Label).update(labels[index])

    if len(items) > len(labels):
        for item in items[len(labels) :]:
            item.remove()
    elif len(items) < len(labels):
        listing.extend(
            ListItem(Label(label)) for label in labels[len(items) :]
        )
    return labels


class HomeScreen(Screen[None]):
    BINDINGS = [
        Binding("n", "new_run", "New run", priority=True),
        Binding("enter", "attach", "Attach"),
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("q", "leave", "Quit", priority=True),
    ]

    def __init__(self, scan_roots: list[str | Path] | None = None) -> None:
        super().__init__()
        self.scan_roots = scan_roots
        self.runs: list[tuple[str, Path]] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(
            "Attach to a durable run directory or start a new campaign. "
            "Audit artifacts remain the source of truth.",
            id="home-intro",
        )
        yield Label("Recent runs", classes="panel-title")
        yield ListView(id="recent-runs")
        yield Static("", id="home-status")
        with Horizontal(classes="toolbar"):
            yield Button("New run", id="new-run", variant="primary")
            yield Button("Refresh", id="refresh")
            yield Button("Quit", id="quit")
        yield Footer()

    def on_mount(self) -> None:
        self.action_refresh()

    def action_refresh(self) -> None:
        listing = self.query_one("#recent-runs", ListView)
        listing.clear()
        self.runs = []
        found = discover_recent_runs(self.scan_roots, limit=20)
        if not found:
            listing.append(ListItem(Label("(no recent run directories found)")))
            self.query_one("#home-status", Static).update(
                "No mvp_manifest.json files were found under the current artifacts tree."
            )
            return
        for item in found:
            path = Path(item.run_directory)
            hypothesis = (item.hypothesis or "").replace("\n", " ")
            if len(hypothesis) > 72:
                hypothesis = hypothesis[:69] + "..."
            record = load_supervisor_record(path)
            live = bool(record and process_identity_matches(record))
            badge = "live" if live else item.phase.value
            label = f"{path.name}  {badge}  {hypothesis or '(no hypothesis)'}"
            listing.append(ListItem(Label(label)))
            self.runs.append((label, path))
        self.query_one("#home-status", Static).update(
            f"{len(self.runs)} recent run{'s' if len(self.runs) != 1 else ''} found."
        )

    def action_new_run(self) -> None:
        self.app.push_screen(NewRunScreen())

    def action_attach(self) -> None:
        listing = self.query_one("#recent-runs", ListView)
        index = listing.index
        if index is None or index >= len(self.runs):
            self.query_one("#home-status", Static).update("Select a run to attach.")
            return
        self.app.push_screen(DashboardScreen(self.runs[index][1]))

    def action_leave(self) -> None:
        self.app.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "new-run":
            self.action_new_run()
        elif event.button.id == "refresh":
            self.action_refresh()
        elif event.button.id == "quit":
            self.action_leave()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        del event
        self.action_attach()


class NewRunScreen(Screen[None]):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("ctrl+s", "review", "Review"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.last_error = ""
        self.campaign_default = _default_campaign_id()
        self.output_follows_campaign = True

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll():
            yield Static("New campaign", classes="panel-title")
            yield Static(
                "The hypothesis is the scientific contract. The instruction is an "
                "optional operational constraint and does not change claim identity.",
                id="form-intro",
            )
            yield Label("Root hypothesis", classes="form-label")
            yield TextArea(id="hypothesis-input")
            yield Label("Optional operational instruction", classes="form-label")
            yield TextArea(id="instruction-input")
            yield Label("Campaign ID", classes="form-label")
            yield Input(value=self.campaign_default, id="campaign-id")
            yield Label("Output directory", classes="form-label")
            yield Input(
                value=str(Path.cwd() / "artifacts" / self.campaign_default),
                id="output-directory",
            )
            yield Label("Maximum wall time (seconds)", classes="form-label")
            yield Input(value="21600", id="max-wall-seconds", type="number")
            yield Label("Maximum command time (seconds)", classes="form-label")
            yield Input(value="600", id="max-command-seconds", type="number")
            yield Label("Workspace limit (MB)", classes="form-label")
            yield Input(value="512", id="max-workspace-mb", type="number")
            yield Label("Memory limit (MB)", classes="form-label")
            yield Input(value="4096", id="max-memory-mb", type="number")
            yield Label("Installed capabilities", classes="form-label")
            yield Static(self._capability_text(), id="capabilities", classes="panel")
            yield Static("", id="form-error", classes="form-error")
            with Horizontal(classes="toolbar"):
                yield Button("Review contract", id="review", variant="primary")
                yield Button("Back", id="back")
        yield Footer()

    def _capability_text(self) -> str:
        try:
            descriptors = installed_capability_descriptors()
        except Exception as error:  # noqa: BLE001 - operator display of discovery failure
            return f"Capability discovery failed: {error}"
        if not descriptors:
            return "No installed capabilities detected. The Python sandbox remains available."
        lines = []
        for item in descriptors:
            name = item.get("name") or "unnamed"
            version = item.get("version") or ""
            description = item.get("description") or ""
            skill = item.get("skill") or ""
            lines.append(f"• {name} {version}".rstrip())
            if description:
                lines.append(f"  {description}")
            if skill:
                lines.append(f"  skill: {skill}")
        return "\n".join(lines)

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_review(self) -> None:
        request = self.validate()
        if request is None:
            return
        self.app.push_screen(ContractReviewScreen(request))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "review":
            self.action_review()
        elif event.button.id == "back":
            self.action_back()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "campaign-id" and self.output_follows_campaign:
            campaign = event.value.strip() or self.campaign_default
            self.query_one("#output-directory", Input).value = str(
                Path.cwd() / "artifacts" / campaign
            )
        elif event.input.id == "output-directory":
            campaign = self.query_one("#campaign-id", Input).value.strip()
            expected = str(Path.cwd() / "artifacts" / (campaign or self.campaign_default))
            self.output_follows_campaign = event.value.strip() in {"", expected}

    def validate(self) -> MVPLaunchRequest | None:
        error_widget = self.query_one("#form-error", Static)
        hypothesis = self.query_one("#hypothesis-input", TextArea).text.strip()
        instruction = self.query_one("#instruction-input", TextArea).text.strip()
        campaign = self.query_one("#campaign-id", Input).value.strip()
        output = self.query_one("#output-directory", Input).value.strip()
        try:
            wall = float(self.query_one("#max-wall-seconds", Input).value)
            command = float(self.query_one("#max-command-seconds", Input).value)
            workspace = int(float(self.query_one("#max-workspace-mb", Input).value))
            memory = int(float(self.query_one("#max-memory-mb", Input).value))
        except ValueError:
            self.last_error = "Resource fields must be positive numbers."
            error_widget.update(self.last_error)
            return None
        if not hypothesis:
            self.last_error = "A root hypothesis is required."
            error_widget.update(self.last_error)
            return None
        if len(hypothesis) < 8:
            self.last_error = "The hypothesis must be at least 8 characters."
            error_widget.update(self.last_error)
            return None
        try:
            campaign = validate_campaign_id(campaign)
        except ValueError as error:
            self.last_error = str(error)
            error_widget.update(self.last_error)
            return None
        if not output:
            self.last_error = "An output directory is required."
            error_widget.update(self.last_error)
            return None
        if min(wall, command, workspace, memory) <= 0:
            self.last_error = "Resource limits must be greater than zero."
            error_widget.update(self.last_error)
            return None
        self.last_error = ""
        error_widget.update("")
        return MVPLaunchRequest(
            hypothesis=hypothesis,
            instruction=instruction or None,
            campaign_id=campaign,
            output_directory=str(Path(output).expanduser()),
            max_wall_seconds=wall,
            max_command_seconds=command,
            max_workspace_mb=workspace,
            max_memory_mb=memory,
        )


class ContractReviewScreen(Screen[None]):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("enter", "launch", "Launch"),
    ]

    def __init__(self, request: MVPLaunchRequest) -> None:
        super().__init__()
        self.request = request
        self.last_error = ""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Contract review", classes="panel-title")
        yield Static(self._body(), id="contract-body", classes="panel")
        yield Static("", id="launch-error", classes="form-error")
        with Horizontal(classes="toolbar"):
            yield Button("Launch campaign", id="launch", variant="primary")
            yield Button("Back", id="back")
        yield Footer()

    def _body(self) -> str:
        request = self.request
        instruction = request.instruction or "(none)"
        return "\n".join(
            [
                f"Campaign: {request.campaign_id}",
                f"Output: {Path(request.output_directory).expanduser()}",
                (
                    f"Envelope: wall {format_duration(request.max_wall_seconds)}, "
                    f"command {int(request.max_command_seconds)} s, "
                    f"workspace {request.max_workspace_mb} MB, "
                    f"memory {request.max_memory_mb} MB"
                ),
                "",
                "Root hypothesis",
                request.hypothesis,
                "",
                "Operational instruction",
                instruction,
                "",
                "Launch will write operator_input/hypothesis.txt and invoke "
                "--hypothesis-file. No shell string is constructed. The durable "
                "manifest, transcript, ledger, and report remain authoritative.",
            ]
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_launch(self) -> None:
        error_widget = self.query_one("#launch-error", Static)
        try:
            plan = materialize_operator_input(self.request)
            campaign = start_managed_campaign(plan)
        except Exception as error:  # noqa: BLE001 - surface launch failure to operator
            self.last_error = f"Launch failed: {error}"
            error_widget.update(self.last_error)
            return
        _app(self).attach_managed(campaign)
        while len(self.app.screen_stack) > 1:
            self.app.pop_screen()
        self.app.push_screen(DashboardScreen(plan.output_directory))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "launch":
            self.action_launch()
        elif event.button.id == "back":
            self.action_back()


class DashboardScreen(Screen[None]):
    BINDINGS = [
        Binding("c", "cancel", "Cancel", priority=True),
        Binding("p", "pause", "Pause", priority=True),
        Binding("r", "resume", "Resume", priority=True),
        Binding("l", "logs", "Logs", priority=True),
        Binding("a", "artifacts", "Artifacts", priority=True),
        Binding("v", "audit_ledger", "Audit ledger", priority=True),
        Binding("enter", "claim_detail", "Claim"),
        Binding("q", "leave", "Leave UI", priority=True),
    ]

    def __init__(self, run_directory: str | Path) -> None:
        super().__init__()
        self.run_directory = Path(run_directory).expanduser().resolve()
        self.monitor = MVPRunMonitor(self.run_directory)
        self.snapshot: MVPRunSnapshot | None = None
        self.last_cancel_message = ""
        self.cancel_in_progress = False
        self.last_control_message = ""
        self.selected_claim_id: str | None = None
        self.selected_hypothesis_id: str | None = None
        self.selected_validation_id: str | None = None
        self.hypothesis_rows: tuple[ClaimTreeRow, ...] = ()
        self.validation_rows: tuple[ClaimTreeRow, ...] = ()
        self._hypothesis_labels: tuple[str, ...] | None = None
        self._validation_labels: tuple[str, ...] | None = None
        self._rendering_claim_views = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with VerticalScroll():
            yield Static("", id="status-line")
            yield Static("", id="clock-line")
            yield Static("", id="model-line")
            yield Static("", id="usage-line")
            yield Static("Hypothesis tree", classes="panel-title")
            yield ListView(id="hypothesis-tree")
            yield Static(
                "Validation claims for selected hypothesis",
                id="validation-title",
                classes="panel-title",
            )
            yield ListView(id="validation-claims")
            yield Static("Current action", classes="panel-title")
            yield Static("", id="current-action", classes="panel")
            yield Static("Recent activity", classes="panel-title")
            yield Static("", id="activity", classes="panel")
            yield Static("Terminal report", classes="panel-title")
            yield Static("", id="final-answer", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_snapshot()
        self.set_interval(0.5, self.refresh_snapshot)

    def refresh_snapshot(self) -> None:
        try:
            snapshot = self.monitor.snapshot()
        except (FileNotFoundError, NotADirectoryError, OSError) as error:
            self.query_one("#status-line", Static).update(f"Cannot read run directory: {error}")
            return
        self.snapshot = snapshot
        live = _app(self).live_identity_for(self.run_directory)
        phase_text = "RUNNING" if live else snapshot.phase_label
        campaign = snapshot.identity.campaign_id or self.run_directory.name
        status = self.query_one("#status-line", Static)
        status.update(f"Campaign: {campaign}       {phase_text}")
        status.set_class(False, "phase-running")
        status.set_classes(_phase_class(phase_text))
        elapsed = format_duration(snapshot.elapsed_wall_seconds)
        budget = format_duration(snapshot.configured_wall_seconds)
        estimate = "~" if snapshot.elapsed_is_estimate else ""
        heartbeat = "heartbeat --"
        if snapshot.latest_heartbeat is not None:
            heartbeat = f"heartbeat {format_age(snapshot.latest_heartbeat.age_seconds)}"
        self.query_one("#clock-line", Static).update(
            f"elapsed {estimate}{elapsed} / {budget}     {heartbeat}"
        )
        model = snapshot.last_model or "-"
        capability = snapshot.last_capability or "-"
        if snapshot.current_action and snapshot.current_action.capability:
            capability = snapshot.current_action.capability
        self.query_one("#model-line", Static).update(
            f"model: {model}                 capability: {capability}"
        )
        usage = snapshot.token_usage.label
        if snapshot.pending_control:
            usage = f"{usage}     pending {snapshot.pending_control}"
        self.query_one("#usage-line", Static).update(usage)
        self._render_claim_views(snapshot)
        self.query_one("#current-action", Static).update(self._current_action_text(snapshot, live))
        events = snapshot.recent_events[-8:]
        activity = "\n".join(event.summary for event in events) or "(no transcript events yet)"
        self.query_one("#activity", Static).update(activity)
        if snapshot.report is None:
            self.query_one("#final-answer", Static).update(
                "No terminal report yet. Incomplete is not a scientific result."
            )
        else:
            notes = "\n".join(snapshot.report.finish_claim_notes)
            answer = snapshot.report.final_answer.strip() or "(empty final answer)"
            body = f"status: {snapshot.report.status}\n{answer}"
            if notes:
                body += f"\n\nFinish notes\n{notes}"
            self.query_one("#final-answer", Static).update(body)

    def _render_claim_views(self, snapshot: MVPRunSnapshot) -> None:
        self._rendering_claim_views = True
        try:
            self.hypothesis_rows = build_hypothesis_tree(snapshot.claims)
            selected = self.selected_hypothesis_id
            available = {row.claim.id for row in self.hypothesis_rows}
            if selected not in available:
                active = next((claim for claim in snapshot.claims if claim.active), None)
                selected = (
                    scientific_ancestor_id(snapshot.claims, active.id)
                    if active is not None
                    else None
                )
            if selected not in available:
                selected = self.hypothesis_rows[0].claim.id if self.hypothesis_rows else None
            self.selected_hypothesis_id = selected

            tree = self.query_one("#hypothesis-tree", ListView)
            if not self.hypothesis_rows:
                hypothesis = snapshot.identity.hypothesis or "hypothesis not yet recorded"
                labels = (f"(claim ledger not initialized)  {hypothesis}",)
                selected_index = 0
            else:
                labels = tuple(
                    hypothesis_row_label(row) for row in self.hypothesis_rows
                )
                selected_index = next(
                    (
                        index
                        for index, row in enumerate(self.hypothesis_rows)
                        if row.claim.id == selected
                    ),
                    0,
                )
            self._hypothesis_labels = _sync_list_labels(
                tree,
                labels,
                self._hypothesis_labels,
            )
            if tree.index != selected_index:
                tree.index = selected_index
            self._render_validation_claims(snapshot)
        finally:
            self._rendering_claim_views = False

    def _render_validation_claims(self, snapshot: MVPRunSnapshot) -> None:
        listing = self.query_one("#validation-claims", ListView)
        selected = self.selected_hypothesis_id
        title = "Validation claims for selected hypothesis"
        if selected is None:
            self.validation_rows = ()
            labels = ("(select a hypothesis)",)
            selected_index = 0
        else:
            title += f" · {selected}"
            self.validation_rows = build_validation_tree(snapshot.claims, selected)
            available = {row.claim.id for row in self.validation_rows}
            if self.selected_validation_id not in available:
                self.selected_validation_id = (
                    self.validation_rows[0].claim.id if self.validation_rows else None
                )
            if not self.validation_rows:
                labels = ("(no linked validation claims)",)
                selected_index = 0
            else:
                labels = tuple(
                    validation_row_label(row) for row in self.validation_rows
                )
                selected_index = next(
                    (
                        index
                        for index, row in enumerate(self.validation_rows)
                        if row.claim.id == self.selected_validation_id
                    ),
                    0,
                )
        self._validation_labels = _sync_list_labels(
            listing,
            labels,
            self._validation_labels,
        )
        if listing.index != selected_index:
            listing.index = selected_index
        self.query_one("#validation-title", Static).update(title)

    def _current_action_text(self, snapshot: MVPRunSnapshot, live: bool) -> str:
        if snapshot.current_action is None:
            if snapshot.phase in {
                RunPhase.COMPLETED,
                RunPhase.CANCELLED,
                RunPhase.PROVIDER_FAILED,
                RunPhase.BUDGET_EXHAUSTED,
            }:
                return "Campaign has a terminal report."
            if snapshot.phase is RunPhase.PAUSED:
                return "Paused at an action boundary. Press r to resume the same contract."
            if live:
                return "Waiting for the next durable action."
            return "No pending action. Process liveness is unknown unless this UI launched it."
        action = snapshot.current_action
        details = [f"iteration={action.iteration}"]
        if action.stage:
            details.append(f"stage={action.stage}")
        if snapshot.latest_heartbeat and snapshot.latest_heartbeat.elapsed_wall_seconds is not None:
            details.append(f"elapsed={int(snapshot.latest_heartbeat.elapsed_wall_seconds)} s")
        details.append(f"workspace={format_bytes(snapshot.workspace_bytes)}")
        return f"{action.description}\n" + ", ".join(details)

    def action_leave(self) -> None:
        _app(self).detach_managed()
        if len(self.app.screen_stack) > 1:
            self.app.pop_screen()
        else:
            self.app.exit()

    def action_cancel(self) -> None:
        if self.snapshot is not None and self.snapshot.phase in {
            RunPhase.COMPLETED,
            RunPhase.CANCELLED,
            RunPhase.PROVIDER_FAILED,
            RunPhase.BUDGET_EXHAUSTED,
        }:
            self.last_cancel_message = "campaign already has a terminal report"
            self.notify(self.last_cancel_message)
            return
        if self.cancel_in_progress:
            self.notify("cancellation is already in progress")
            return
        if not _app(self).live_identity_for(self.run_directory):
            self.last_cancel_message = (
                "cancel is only offered for a process this UI launched or a verified "
                "supervisor record; this attach is read-only"
            )
            self.notify(self.last_cancel_message)
            return
        self.cancel_in_progress = True
        self.last_cancel_message = "cancellation requested"
        self.notify(self.last_cancel_message)
        self._cancel_campaign()

    @work(thread=True, exclusive=True, group="campaign-cancel")
    def _cancel_campaign(self) -> None:
        try:
            message = _app(self).cancel_run(self.run_directory)
        except Exception as error:
            message = f"cancellation failed: {type(error).__name__}: {error}"
        self.app.call_from_thread(self._finish_cancel, message)

    def _finish_cancel(self, message: str) -> None:
        self.cancel_in_progress = False
        self.last_cancel_message = message
        self.notify(message)
        self.refresh_snapshot()

    def action_pause(self) -> None:
        if self.snapshot is not None and self.snapshot.phase in {
            RunPhase.COMPLETED,
            RunPhase.CANCELLED,
            RunPhase.PROVIDER_FAILED,
            RunPhase.BUDGET_EXHAUSTED,
            RunPhase.PAUSED,
        }:
            self.last_control_message = "campaign is not running"
            self.notify(self.last_control_message)
            return
        self.last_control_message = request_verified_pause(
            self.run_directory,
            source="tui",
        )
        self.notify(self.last_control_message)
        self.refresh_snapshot()

    def action_resume(self) -> None:
        try:
            plan = prepare_resume(self.run_directory)
        except ResumeError as error:
            self.last_control_message = str(error)
            self.notify(self.last_control_message)
            return
        try:
            campaign = start_managed_campaign(plan)
        except Exception as error:  # noqa: BLE001 - surface resume failure
            self.last_control_message = f"resume failed: {error}"
            self.notify(self.last_control_message)
            return
        _app(self).attach_managed(campaign)
        self.last_control_message = f"resumed pid={campaign.identity.pid}"
        self.notify(self.last_control_message)
        self.monitor = MVPRunMonitor(self.run_directory)
        self.refresh_snapshot()

    def action_logs(self) -> None:
        self.app.push_screen(LogsScreen(self.run_directory))

    def action_artifacts(self) -> None:
        self.app.push_screen(ArtifactsScreen(self.run_directory))

    def action_audit_ledger(self) -> None:
        claims = self.snapshot.claims if self.snapshot is not None else ()
        self.app.push_screen(AuditLedgerScreen(claims))

    def action_claim_detail(self) -> None:
        focused = self.focused
        if not isinstance(focused, ListView):
            return
        index = focused.index
        if index is None:
            return
        claim = self._claim_at(focused.id, index)
        if claim is None:
            return
        self._open_claim(claim)

    def _claim_at(self, listing_id: str | None, index: int) -> ClaimSummary | None:
        if listing_id == "hypothesis-tree" and index < len(self.hypothesis_rows):
            return self.hypothesis_rows[index].claim
        if listing_id == "validation-claims" and index < len(self.validation_rows):
            return self.validation_rows[index].claim
        return None

    def _open_claim(self, claim: ClaimSummary) -> None:
        self.selected_claim_id = claim.id
        self.app.push_screen(ClaimDetailScreen(claim))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        claim = self._claim_at(event.list_view.id, event.index)
        if claim is not None:
            self._open_claim(claim)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if self._rendering_claim_views or event.list_view.index is None:
            return
        index = event.list_view.index
        if event.list_view.id == "hypothesis-tree" and index < len(
            self.hypothesis_rows
        ):
            selected = self.hypothesis_rows[index].claim.id
            if selected != self.selected_hypothesis_id:
                self.selected_hypothesis_id = selected
                self.selected_validation_id = None
                if self.snapshot is not None:
                    self._render_validation_claims(self.snapshot)
        elif event.list_view.id == "validation-claims" and index < len(
            self.validation_rows
        ):
            self.selected_validation_id = self.validation_rows[index].claim.id


class HelpScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "close", "Close"), Binding("q", "close", "Close")]

    def compose(self) -> ComposeResult:
        yield Static("Keyboard help", classes="panel-title")
        yield Static(
            "\n".join(
                [
                    "The terminal UI is a projection of durable records.",
                    "mvp_report.json, hypothesis_ledger.json, and transcript.jsonl "
                    "remain authoritative.",
                    "There is no fabricated scientific completion percentage.",
                    "",
                    "[n] new run          [enter] attach or open claim",
                    "[c] cancel           verified process; writes a cancelled report",
                    "[p] pause            next action boundary; does not SIGSTOP",
                    "[r] resume           repeat the stored launch contract",
                    "[l] controller log   [a] artifacts inside the run directory",
                    "[v] audit ledger     every scientific and validation claim",
                    "[q] leave UI         detaches; does not cancel or pause",
                    "[?] help             [esc] close this panel",
                    "",
                    "The hypothesis tree contains scientific claims only. Instrument,",
                    "diagnostic, and control claims follow the selected hypothesis.",
                    "status, watch, pause, and resume work without this optional extra.",
                    "Token counts come from provider usage on assistant transcript rows.",
                    "Install the extra with: uv sync --extra tui",
                ]
            ),
            id="help-body",
            classes="panel",
        )

    def action_close(self) -> None:
        self.app.pop_screen()


class ClaimDetailScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "close", "Close"), Binding("q", "close", "Close")]

    def __init__(self, claim: ClaimSummary) -> None:
        super().__init__()
        self.claim = claim

    def compose(self) -> ComposeResult:
        claim_type = "Hypothesis" if self.claim.kind == "scientific" else "Validation claim"
        yield Static(f"{claim_type} · {self.claim.id}", classes="panel-title")
        yield Static(
            _claim_detail_body(self.claim),
            id="claim-detail",
            classes="panel",
        )

    def action_close(self) -> None:
        self.app.pop_screen()


class AuditLedgerScreen(ModalScreen[None]):
    """Complete claim ledger retained alongside the human-first projections."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
        Binding("enter", "preview", "Inspect"),
    ]

    def __init__(self, claims: tuple[ClaimSummary, ...]) -> None:
        super().__init__()
        self.claims = claims

    def compose(self) -> ComposeResult:
        yield Static("Complete audit ledger", classes="panel-title")
        items = (
            [ListItem(Label(audit_row_label(claim))) for claim in self.claims]
            if self.claims
            else [ListItem(Label("(no claims recorded)"))]
        )
        yield ListView(*items, id="audit-claims")
        yield Static(
            "Select a claim to inspect its typed relation and evidence counts.",
            id="audit-claim-detail",
            classes="panel",
        )

    def action_preview(self) -> None:
        listing = self.query_one("#audit-claims", ListView)
        index = listing.index
        if index is None or index >= len(self.claims):
            return
        self.query_one("#audit-claim-detail", Static).update(
            _claim_detail_body(self.claims[index])
        )

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        del event
        self.action_preview()


class LogsScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "close", "Close"), Binding("q", "close", "Close")]

    def __init__(self, run_directory: Path) -> None:
        super().__init__()
        self.run_directory = run_directory

    def compose(self) -> ComposeResult:
        yield Static("Controller log", classes="panel-title")
        yield Static(self._load(), id="log-body", classes="panel")

    def _load(self) -> str:
        path = contained_path(self.run_directory, "controller.log")
        if path is None or not path.is_file():
            return (
                "No controller.log in this run directory. The TUI writes this file "
                "only for campaigns it launches."
            )
        try:
            data = path.read_bytes()[-16_384:]
        except OSError as error:
            return f"Unable to read controller.log: {error}"
        return data.decode("utf-8", errors="replace") or "(empty log)"

    def action_close(self) -> None:
        self.app.pop_screen()


class ArtifactsScreen(ModalScreen[None]):
    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("q", "close", "Close"),
        Binding("enter", "preview", "Preview"),
    ]

    def __init__(self, run_directory: Path) -> None:
        super().__init__()
        self.run_directory = run_directory
        self.entries = list_contained_artifacts(run_directory)

    def compose(self) -> ComposeResult:
        yield Static("Run artifacts (contained paths only)", classes="panel-title")
        items = (
            [
                ListItem(
                    Label(
                        f"{entry.relative_path}  {format_bytes(entry.bytes)}  "
                        f"{entry.kind}"
                    )
                )
                for entry in self.entries
            ]
            if self.entries
            else [ListItem(Label("(no files)"))]
        )
        yield ListView(*items, id="artifact-list")
        yield Static(
            "Select a contained file to preview text.",
            id="artifact-preview",
            classes="panel",
        )

    def action_preview(self) -> None:
        listing = self.query_one("#artifact-list", ListView)
        index = listing.index
        if index is None or index >= len(self.entries):
            return
        entry = self.entries[index]
        preview = self.query_one("#artifact-preview", Static)
        path = contained_path(self.run_directory, entry.relative_path)
        if path is None:
            preview.update("Refusing to open a path outside the run directory.")
            return
        if entry.kind == "symlink" or path.is_symlink():
            preview.update("Symlink; content is not opened.")
            return
        if not path.is_file():
            preview.update("Not a regular file.")
            return
        if entry.bytes > 32_768:
            preview.update(
                f"{entry.relative_path}: {format_bytes(entry.bytes)} (too large to preview)"
            )
            return
        try:
            text = path.read_text(errors="replace")
        except OSError as error:
            preview.update(f"Unable to read file: {error}")
            return
        preview.update(text[:4000] if text else "(empty file)")

    def action_close(self) -> None:
        self.app.pop_screen()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        del event
        self.action_preview()
