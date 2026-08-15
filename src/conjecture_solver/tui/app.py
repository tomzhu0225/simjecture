"""Interactive terminal application for Simjecture."""

from __future__ import annotations

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from ..mvp_launch import ManagedCampaign, load_supervisor_record, process_identity_matches
from .screens import DashboardScreen, HomeScreen

APP_CSS = """
Screen {
    background: #101418;
    color: #e8edf2;
}

Header {
    background: #1a222b;
    color: #e8edf2;
    text-style: bold;
}

Footer {
    background: #1a222b;
}

.panel {
    border: tall #3a4654;
    padding: 0 1;
    margin: 0 0 1 0;
    height: auto;
}

.panel-title {
    color: #9ecbff;
    text-style: bold;
    height: 1;
}

#status-line, #clock-line, #model-line, #usage-line {
    height: 1;
}

.phase-running { color: #7dcea0; text-style: bold; }
.phase-completed { color: #7dcea0; text-style: bold; }
.phase-cancelled { color: #f0c674; text-style: bold; }
.phase-failed { color: #e07a5f; text-style: bold; }
.phase-incomplete { color: #9ecbff; }
.phase-initialized { color: #9aa7b5; }
.phase-paused { color: #f0c674; text-style: bold; }

#instruction, #hypothesis-tree, #validation-claims, #current-action, #activity,
#final-answer {
    height: auto;
}

#hypothesis-tree {
    min-height: 6;
    max-height: 14;
    border: tall #3a4654;
}

#validation-claims {
    min-height: 3;
    max-height: 10;
    border: tall #3a4654;
}

#activity {
    min-height: 5;
    max-height: 10;
}

#final-answer {
    min-height: 3;
}

.form-label {
    color: #9aa7b5;
    height: 1;
    margin-top: 1;
}

.form-error {
    color: #e07a5f;
    height: auto;
}

#hypothesis-input, #instruction-input {
    height: 8;
    min-height: 5;
}

#capabilities {
    height: auto;
    min-height: 3;
    max-height: 8;
    color: #c5d0da;
}

#recent-runs {
    height: 1fr;
    min-height: 8;
    border: tall #3a4654;
}

#contract-body, #help-body, #claim-detail, #log-body, #artifact-preview,
#audit-claim-detail {
    height: 1fr;
}

#audit-claims {
    height: 1fr;
    min-height: 8;
    border: tall #3a4654;
}

.toolbar {
    height: 3;
    align: left middle;
}

Button {
    margin-right: 1;
}
"""


class ConjectureSolverApp(App[None]):
    """Human-facing projection of durable MVP campaign records."""

    TITLE = "Simjecture"
    CSS = APP_CSS
    BINDINGS = [
        Binding("question_mark", "help", "Help", show=True),
    ]

    def __init__(
        self,
        run_directory: str | Path | None = None,
        *,
        scan_roots: list[str | Path] | None = None,
    ) -> None:
        super().__init__()
        self.initial_run = (
            Path(run_directory).expanduser().resolve() if run_directory else None
        )
        self.scan_roots = scan_roots
        self.managed: ManagedCampaign | None = None

    def get_default_screen(self) -> HomeScreen | DashboardScreen:
        if self.initial_run is not None:
            return DashboardScreen(self.initial_run)
        return HomeScreen(scan_roots=self.scan_roots)

    def action_help(self) -> None:
        from .screens import HelpScreen

        self.push_screen(HelpScreen())

    def attach_managed(self, campaign: ManagedCampaign) -> None:
        self.detach_managed()
        self.managed = campaign

    def detach_managed(self) -> None:
        if self.managed is not None:
            self.managed.close()
        self.managed = None

    def live_identity_for(self, run_directory: str | Path) -> bool:
        if self.managed is not None and self.managed.is_alive():
            return Path(self.managed.plan.output_directory).resolve() == Path(
                run_directory
            ).resolve()
        record = load_supervisor_record(run_directory)
        return bool(record and process_identity_matches(record))

    def cancel_run(self, run_directory: str | Path) -> str:
        if self.managed is not None and Path(self.managed.plan.output_directory).resolve() == Path(
            run_directory
        ).resolve():
            return self.managed.cancel()
        record = load_supervisor_record(run_directory)
        if record is None:
            return "no verified process record for this run"
        from ..mvp_launch import request_graceful_cancel

        return request_graceful_cancel(record)

    def on_unmount(self) -> None:
        self.detach_managed()


def run_tui(
    run_directory: str | Path | None = None,
    *,
    scan_roots: list[str | Path] | None = None,
) -> int:
    ConjectureSolverApp(run_directory, scan_roots=scan_roots).run()
    return 0
