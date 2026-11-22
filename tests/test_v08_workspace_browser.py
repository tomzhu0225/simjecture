"""End-to-end Playwright browser tests for v0.8 File Viewer, Direct Steering, and Swarm GUI."""

from __future__ import annotations

import base64
import os
import sys
import threading
from pathlib import Path

import pytest

from conjecture_solver.web.application import SimjectureWebApplication
from conjecture_solver.web.file_viewer import capture_file_baseline
from conjecture_solver.web.server import create_server

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
)


@pytest.fixture(scope="module")
def browser():
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        executable = Path(runtime.chromium.executable_path)
        if not executable.is_file():
            pytest.skip(f"Playwright Chromium executable is not installed: {executable}")
        instance = runtime.chromium.launch(headless=True)
        try:
            yield instance
        finally:
            instance.close()


@pytest.fixture
def page_expect(browser):
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    errors: list[str] = []
    context.on("page", lambda p: p.on("pageerror", lambda err: errors.append(str(err))))
    page = context.new_page()
    try:
        yield page, pytest.importorskip("playwright.sync_api").expect
        assert not errors, f"Unexpected browser pageerrors: {errors}"
    finally:
        context.close()


def _write_fake_codex(binary: Path) -> None:
    binary.write_text(
        f"#!{sys.executable}\n"
        + """
import json, os, sys, time
from pathlib import Path

args = sys.argv[1:]
prompt = args[-1]
if Path("CONTEXT.json").is_file():
    ctx = json.loads(Path("CONTEXT.json").read_text(encoding="utf-8"))
    for rel in ctx.get("outputs", []):
        out = Path(rel)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(f"# Output from {ctx['name']}\\n\\nVerified.\\n", encoding="utf-8")
    Path("HELPER_RESULT.json").write_text(json.dumps({
        "status": "completed",
        "summary": f"{ctx['name']} delivered outputs cleanly.",
        "artifacts": ctx.get("outputs", []),
        "checks": ["ok"],
        "unresolved": [],
    }), encoding="utf-8")
    ev = {"type": "item.completed", "item": {"type": "agent_message", "text": "Worker done."}}
    print(json.dumps(ev), flush=True)
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1}}), flush=True)
    sys.exit(0)

is_steered = "resume" in args or "DIRECT USER STEERING" in prompt
if not is_steered:
    print(json.dumps({"type": "thread.started", "thread_id": "browser-thread-1"}), flush=True)
    Path("turn_running").touch()
    deadline = time.time() + 18
    while time.time() < deadline and not Path(os.environ["SIMJECTURE_GUI_RELEASE"]).exists():
        time.sleep(0.05)
    ev = {"type": "item.completed", "item": {"type": "agent_message", "text": "Initial reply"}}
    print(json.dumps(ev), flush=True)
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 2}}), flush=True)
else:
    Path("steered_note.md").write_text(
        "# Steered\\n\\nApplied: " + prompt + "\\n", encoding="utf-8"
    )
    ev = {
        "type": "item.completed",
        "item": {"type": "agent_message", "text": "Steered reply received!"},
    }
    print(json.dumps(ev), flush=True)
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 3}}), flush=True)
""",
        encoding="utf-8",
    )
    binary.chmod(0o755)


@pytest.fixture
def v08_site(tmp_path: Path, monkeypatch):
    binary = tmp_path / "codex"
    _write_fake_codex(binary)
    release = tmp_path / "release"
    monkeypatch.setenv("SIMJECTURE_GUI_RELEASE", str(release))
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])

    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    project = app.workspace.create(
        {"name": "v0.8 Workbench", "agent": {"backend": "codex", "model": "test"}}
    )
    pid = project["id"]
    pdir = app.workspace.directory(pid)
    files = pdir / "files"
    (files / "solver.py").write_text("def rhs(u):\n    return -u\n", encoding="utf-8")
    (files / "unchanged.txt").write_text("baseline only\n", encoding="utf-8")

    turn_dir = pdir / "turns/0001"
    turn_dir.mkdir(parents=True)
    capture_file_baseline(pdir, turn_dir)

    (files / "solver.py").write_text("def rhs(u):\n    return -2 * u\n", encoding="utf-8")
    (files / "report.md").write_text(
        "# Findings\n\n<img src=x onerror=\"window.__xss=1\">\n\n$a^2 + b^2 = c^2$\n",
        encoding="utf-8",
    )
    (files / "table.csv").write_text("grid,error\n32,0.01\n64,0.0025\n", encoding="utf-8")
    (files / "figure.png").write_bytes(PNG_1X1)

    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", pid, pdir, release
    finally:
        release.touch()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_integrated_file_viewer_diff_xss_and_responsive_layout(v08_site, page_expect):
    base, pid, pdir, _ = v08_site
    page, expect = page_expect
    page.goto(f"{base}/workspace#project={pid}&view=interactive")

    # Edited pill and filter buttons appear
    expect(page.locator("#inspector-edited-pill")).to_be_visible()
    expect(page.locator("#files-filter-edited")).to_contain_text("4")

    # Filter to edited files only -> unchanged.txt disappears
    page.locator("#files-filter-edited").click()
    expect(page.locator('#project-files a[data-view-file="solver.py"]')).to_be_visible()
    expect(page.locator('#project-files a[data-view-file="unchanged.txt"]')).to_have_count(0)

    # Open solver.py inline -> files panel enters viewer-first full-height layout
    page.locator('#project-files a[data-view-file="solver.py"]').click()
    viewer = page.locator("#file-viewer-pane")
    expect(viewer).to_be_visible()
    expect(page.locator(".files-panel-shell.has-active-file")).to_be_visible()
    expect(page.locator("#brief-summary")).to_be_hidden()
    # Viewer-first: the file list steps away and a narrow pane widens for reading
    expect(page.locator("#project-files")).to_be_hidden()
    expect(page.locator("#inspector-wide-toggle")).to_have_attribute("aria-pressed", "true")
    switcher = viewer.locator(".file-viewer-switcher")
    expect(switcher).to_have_value("solver.py")
    expect(viewer).to_contain_text("return -2 * u")
    viewer.locator('button[data-viewer-mode="diff"]').click()
    expect(viewer.locator(".file-diff-line.add")).to_contain_text("-2 * u")
    expect(viewer.locator(".file-diff-line.del")).to_contain_text("-u")

    # Open Markdown file with XSS payload -> sanitized, never executes
    switcher.select_option("report.md")
    expect(viewer.locator(".file-viewer-markdown h1")).to_have_text("Findings")
    assert page.evaluate("window.__xss === undefined")

    # Open CSV -> renders structured table
    switcher.select_option("table.csv")
    expect(viewer.locator(".file-viewer-table th")).to_have_count(2)
    expect(viewer.locator(".file-viewer-table tbody tr")).to_have_count(2)

    # Open PNG -> renders image preview
    switcher.select_option("figure.png")
    expect(viewer.locator("img.file-viewer-image")).to_be_visible()

    # Live auto-refresh when solver.py changes on disk
    switcher.select_option("solver.py")
    (pdir / "files/solver.py").write_text("def rhs(u):\n    return -4 * u\n", encoding="utf-8")
    expect(viewer).to_contain_text("-4 * u", timeout=8000)

    # Toggle wide pane, dark mode, zh-CN, and check zero horizontal overflow at desktop + mobile
    page.locator("#inspector-wide-toggle").click()
    expect(page.locator("#inspector-wide-toggle")).to_have_attribute("aria-pressed", "false")
    page.locator("#inspector-wide-toggle").click()
    expect(page.locator("#inspector-wide-toggle")).to_have_attribute("aria-pressed", "true")
    page.evaluate("WorkspaceTheme.set('dark')")
    page.evaluate("SimjectureI18n.setLanguage('zh-CN')")
    swarm_tab = page.locator('wa-tab[panel="swarm"] [data-i18n="workspace.swarm.tab"]')
    expect(swarm_tab).to_have_text("蜂群")
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_direct_steering_live_bar_queue_and_timeline_marker(v08_site, page_expect):
    base, pid, pdir, _ = v08_site
    page, expect = page_expect
    page.goto(f"{base}/workspace#project={pid}&view=interactive")

    # Configure Queue mode first in Settings (via rail Settings button), plus verify language toggle
    page.locator("#rail-settings").click()
    # The single interface-language picker lives in Settings, not the sidebar.
    expect(page.locator("#view-settings [data-language-select]")).to_have_count(1)
    expect(page.locator(".sidebar [data-language-select]")).to_have_count(0)
    expect(page.locator("[data-language-select]")).to_be_enabled(timeout=5000)
    page.locator("[data-language-select]").select_option("zh-CN")
    expect(page.locator("html")).to_have_attribute("lang", "zh-CN")
    page.locator("[data-language-select]").select_option("en")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    with page.expect_response(
        lambda r: "/api/workspace/steering-settings" in r.url and r.ok
    ):
        page.locator("#setting-steering-mode").select_option("queue")
    expect(page.locator("#toast")).to_be_visible(timeout=5000)

    # Return to conversation and start a long-running turn
    page.goto(f"{base}/workspace#project={pid}&view=interactive")
    page.locator("#chat-input").fill("Begin initial parameter sweep")
    page.locator("#send-message").click()

    # No noisy steering banner pops up; normal arrow button stays active
    expect(page.locator("#steer-message")).to_be_visible(timeout=8000)
    expect(page.locator("#steering-bar")).to_have_count(0)
    expect(page.locator("#send-message")).to_be_hidden()

    # In Queue setting, submitting while running queues a chip, which we can cancel
    page.locator("#chat-input").fill("Follow-up after sweep")
    page.locator("#steer-message").click()
    expect(page.locator("#steering-queue .steering-chip")).to_have_count(1, timeout=5000)
    page.locator("#steering-queue .steering-chip-actions button").last.click()
    expect(page.locator("#steering-queue .steering-chip")).to_have_count(0, timeout=5000)

    # Switch Settings back to default Steer mode and press Enter to steer seamlessly mid-turn
    page.locator("#rail-settings").click()
    with page.expect_response(
        lambda r: "/api/workspace/steering-settings" in r.url and r.ok
    ):
        page.locator("#setting-steering-mode").select_option("steer")
    expect(page.locator("#setting-steering-mode")).to_be_enabled(timeout=5000)
    page.goto(f"{base}/workspace#project={pid}&view=interactive")
    expect(page.locator("#steer-message")).to_be_visible(timeout=5000)
    page.locator("#chat-input").fill("Focus immediately on Courant number 0.5")
    page.locator("#chat-input").press("Enter")

    # Timeline marker renders and agent finishes with steered answer
    expect(page.locator(".steer-timeline-marker")).to_be_visible(timeout=10000)
    expect(page.locator("#messages")).to_contain_text("Steered reply received!", timeout=15000)
    assert (pdir / "files/steered_note.md").is_file()


def test_swarm_gui_launcher_dag_board_and_inline_artifact_import(v08_site, page_expect):
    base, pid, pdir, _ = v08_site
    page, expect = page_expect
    page.goto(f"{base}/workspace#project={pid}&view=interactive")

    # Select Swarm mode right alongside Reasoning effort inside the composer popover
    page.locator("#conversation-agent-picker").click()
    expect(page.locator("#conversation-swarm")).to_be_visible(timeout=5000)
    page.locator("#conversation-swarm").select_option("parallel_explore")
    expect(page.locator("#conversation-agent-picker .agent-swarm-badge")).to_be_visible(
        timeout=5000
    )
    page.keyboard.press("Escape")

    # Open Swarm tab: mode indicator shows active composer swarm mode, custom launcher works
    page.locator('wa-tab[panel="swarm"]').click()
    expect(page.locator("#swarm-mode-indicator")).to_contain_text("Parallel exploration")
    expect(page.locator("#swarm-empty")).to_be_visible()
    page.locator("#swarm-launch-open").click()
    expect(page.locator("#swarm-launch-dialog")).to_be_visible()

    # Choose adversarial_verify preset (Solver + Falsifier -> Verifier)
    page.locator('[data-swarm-preset="adversarial_verify"]').click()
    page.locator("#swarm-title-input").fill("Positivity Audit Swarm")
    page.locator("#swarm-objective-input").fill("Verify discrete positivity preservation.")
    page.locator("#swarm-launch-submit").click()

    expect(page.locator("#swarm-launch-dialog")).to_be_hidden(timeout=5000)
    expect(page.locator("#swarm-detail .swarm-header-card h3")).to_have_text(
        "Positivity Audit Swarm", timeout=8000
    )
    # Wait until all 3 DAG workers complete (3/3 done)
    expect(page.locator("#swarm-detail")).to_contain_text("3/3 done", timeout=20000)
    expect(page.locator(".swarm-stage-label")).to_have_count(2)
    expect(page.locator(".swarm-worker-card")).to_have_count(3)
    # Swarm workers must NOT show up as Simulations or pop up the legacy Subagents header pill
    expect(page.locator("#simulation-count")).to_have_text("0")
    expect(page.locator("#subagent-panel")).to_be_hidden()
    # Inspecting a worker opens inline console inside the Swarm card
    verifier_card = page.locator('.swarm-worker-card[data-worker="Verifier"]')
    verifier_card.locator(".swarm-worker-actions button").first.click()
    expect(verifier_card.locator(".swarm-worker-console")).to_be_visible(timeout=5000)

    # Post a message on the shared swarm board
    page.locator('[data-swarm-view="board"]').click()
    page.locator("#swarm-board-input").fill("Great convergence across all 3 roles")
    page.locator(".swarm-board-composer button[type=submit]").click()
    expect(page.locator(".swarm-board-feed")).to_contain_text(
        "Great convergence across all 3 roles", timeout=5000
    )

    # View a worker deliverable directly in the integrated File Viewer
    page.locator('[data-swarm-view="agents"]').click()
    verifier_card = page.locator('.swarm-worker-card[data-worker="Verifier"]')
    verifier_card.locator(".swarm-artifact-chip button").first.click()
    expect(page.locator("#file-viewer-pane")).to_be_visible(timeout=5000)
    expect(page.locator("#file-viewer-pane")).to_contain_text("Output from Verifier")

    # Switch back to Swarm tab and one-click Import verdict.md into conversation files
    page.locator('wa-tab[panel="swarm"]').click()
    verifier_card.locator(".swarm-artifact-chip button").nth(1).click()
    expect(page.locator("#file-viewer-pane .file-viewer-switcher")).to_have_value(
        "verdict.md", timeout=8000
    )
    # Back to all files restores the list with the imported file
    page.locator("#file-viewer-pane .file-viewer-back").click()
    expect(page.locator('#project-files a[data-view-file="verdict.md"]')).to_be_visible()
    assert (pdir / "files/verdict.md").is_file()
