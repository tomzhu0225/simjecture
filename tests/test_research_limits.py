"""Operating budgets, independent supervision and complete retained evidence."""

import gzip
import io
import json
import os
import threading
import time
from pathlib import Path

import pytest

from conjecture_solver.console_log import ConsoleLog
from conjecture_solver.research_limits import configure_limits, operating_limits
from conjecture_solver.research_service import ResearchService, sha
from conjecture_solver.review_assets import packet_view, read_asset


def test_operating_changes_preserve_authorization_and_reject_partial_invalid_update(tmp_path):
    s = ResearchService.create(
        tmp_path / "study", "A bounded scientific question", wall_seconds=600
    )
    original = (s.root / "research.json").read_bytes()
    assert all(value is None for value in operating_limits(s.root).values())
    configure_limits(
        s.root, {"worker_action_limit": 40, "review_seconds": 900.0}, reason="Long review"
    )
    before = (s.root / "operating_limits.json").read_bytes()
    with pytest.raises(ValueError):
        configure_limits(
            s.root, {"worker_action_limit": 0, "review_seconds": 1000.0}, reason="Invalid"
        )
    assert (s.root / "operating_limits.json").read_bytes() == before
    assert (s.root / "research.json").read_bytes() == original
    configure_limits(s.root, {"worker_action_limit": None}, reason="Use the campaign budget")
    assert operating_limits(s.root)["review_seconds"] == 900


def test_director_runs_alongside_worker_and_preserves_usage(tmp_path):
    from tests.test_research_director import supervisor

    sup = supervisor(tmp_path)
    executable = tmp_path / "reviewer"
    verdict = dict(
        decision="continue",
        rationale="Continue the independently qualified calculation",
        scientific_feasibility="adequate",
        budget_feasibility="feasible",
        park_worker=True,
        stop_experiments=[],
        next_action="Inspect the completed numerical control",
    )
    executable.write_text(
        "#!/usr/bin/env python3\nimport json,time\nfrom pathlib import Path\n"
        "print(json.dumps({'type':'thread.started','thread_id':'independent-review'}),flush=True)\n"
        f"while not Path({str(tmp_path / 'release-review')!r}).exists(): time.sleep(0.02)\n"
        f"print(json.dumps({{'type':'item.completed','item':{{'type':'agent_message','text':{json.dumps(verdict)!r}}}}}),flush=True)\n"
        "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':123,'output_tokens':45}}))\n"
    )
    executable.chmod(0o700)
    sup.args.executable = str(executable)
    sup.args.turn_seconds = 10
    sup.state.update(round=2, child_pid=os.getpid())
    # Large provenance is indexed without losing the policy needed by the prompt.
    packet = sup.director_packet()
    packet["solver_development"]["large_provenance"] = "x" * 200000
    assert "packet_reference" in sup.director_prompt(packet)
    assert sup.worker_slice_seconds is None
    sup.run_director(force=True, background=True)
    pending = sup._director_pending
    assert pending is not None and sup.state["child_pid"] == os.getpid()
    try:
        assert not pending["future"].done()
        sup.service.note("A new worker observation was recorded while the director reviewed")
        (tmp_path / "release-review").touch()
        pending["future"].result(timeout=5)
        sup.run_director()
        assert sup.service.director_status()[0]["decision"] == "continue"
        assert sup.service.director_status()[0]["worker_wait_action"]["status"] == "rejected"
        assert sup.service.waiting_status()["status"] == "active"
        assert sup.state["child_pid"] == os.getpid()
        assert sup.state["usage_by_thread"]["independent-review"]["input_tokens"] == 123
        assert sup.state["usage_roles_by_thread"]["independent-review"] == "director"
    finally:
        sup.stop_background_director()


def test_stopping_background_review_cleans_up_and_does_not_pause_worker(tmp_path):
    import psutil

    from tests.test_research_director import supervisor

    sup = supervisor(tmp_path)
    executable = tmp_path / "reviewer"
    executable.write_text(
        "#!/usr/bin/env python3\nimport time\nprint('ready',flush=True)\ntime.sleep(60)\n"
    )
    executable.chmod(0o700)
    sup.args.executable = str(executable)
    sup.args.turn_seconds = 30
    sup.state.update(round=2, child_pid=os.getpid())
    sup.run_director(force=True, background=True)
    pending = sup._director_pending
    assert pending
    until = time.monotonic() + 5
    while not pending["runner"].state.get("child_pid") and time.monotonic() < until:
        time.sleep(0.02)
    pid = pending["runner"].state.get("child_pid")
    try:
        assert pid and psutil.pid_exists(pid)
    finally:
        sup.stop_background_director()
    assert not psutil.pid_exists(pid)
    assert sup.state["child_pid"] == os.getpid() and sup.state["status"] == "running"
    assert sup.state["usage_unidentified_calls"] == 1  # Interrupted inference is not free.


def test_resume_reaps_verified_orphan_review_and_retains_missing_usage(tmp_path):
    import subprocess
    import sys

    from conjecture_solver.mvp_launch import read_process_identity
    from conjecture_solver.research_service import put
    from tests.test_research_director import supervisor

    sup = supervisor(tmp_path)
    directory = sup.directory / "director-00001"
    directory.mkdir()
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"], cwd=directory, start_new_session=True
    )
    try:
        identity = read_process_identity(child.pid, run_directory=directory)
        assert identity
        put(directory / "child_identity.json", identity.model_dump(mode="json"))
        (directory / "response.json").write_text(
            json.dumps(dict(type="thread.started", thread_id="orphan-review")) + "\n"
        )
        sup.state["background_review"] = dict(directory=str(directory))
        sup.recover_background_director()
        child.wait(timeout=5)
        assert child.returncode != 0 and sup.state["status"] == "running"
        assert sup.state["usage_unreported_threads"]["orphan-review"] == "director"
        assert not sup.state.get("background_review") and not sup.service.director_status()
    finally:
        if child.poll() is None:
            os.killpg(child.pid, 9)
        child.wait()


def test_large_source_and_result_remain_reviewable_and_hash_verified(tmp_path):
    from tests.test_research_service import completed, service

    s = service(tmp_path)
    source = s.work / "calc.py"
    source.write_text(
        "# retained source\n" * 16000 + "import json\nfrom pathlib import Path\n"
        "Path('result.json').write_text(json.dumps({'value':4,'raw':'x'*1100000}))\n"
    )
    method = s.method(
        source="calc.py",
        model="A finite calculation",
        geometry="Finite domain",
        observable="Output value",
        validation="Direct evaluation",
        rationale="Read complete source",
    )
    assert method["source_references"]["calc.py"]["sha256"] == sha(source)
    record = completed(s)
    request = s.review([record["id"]], "The result of the finite calculation is four")
    packet = s.packet(s.review_body(request))
    evidence = packet["experiments"][0]
    reference = evidence["documents"]["result.json"]["reference"]
    assert read_asset(s.root, reference["sha256"], json_path="value")["content"] == "4"
    packet["large_metadata"] = ["provenance" * 1000] * 150
    view = packet_view(s.root, packet)
    assert len(json.dumps(view)) < 32768
    assert (
        read_asset(s.root, view["packet_reference"]["sha256"], json_path="target_claim.id")[
            "content"
        ]
        == '"root"'
    )
    blob = s.root / reference["path"]
    blob.write_text('{"value":5}')
    with pytest.raises(ValueError, match="changed"):
        read_asset(s.root, reference["sha256"], json_path="value")


def test_console_rotation_preserves_every_byte_and_live_tail(tmp_path):
    payload = b"initial diagnostic\n" * 1000 + b"final result\n"
    with (tmp_path / "output.log").open("a+b", buffering=0) as output:
        log = ConsoleLog(io.BytesIO(payload), output, tmp_path, segment_bytes=1024)
        log.join()
        assert log.error is None
    retained = b"".join(gzip.decompress(p.read_bytes()) for p in sorted(tmp_path.glob("*.gz")))
    retained += (tmp_path / "output.log").read_bytes()
    assert retained == payload and (tmp_path / "output.log").stat().st_size <= 1024


@pytest.mark.parametrize("page_bytes", [1, 2, 7, 23])
def test_review_source_pages_preserve_multibyte_text(tmp_path, page_bytes):
    from conjecture_solver.review_assets import freeze_file

    source = tmp_path / "source.py"
    text = "# 中文密度与温度 αβ\n" * 5
    source.write_text(text)
    reference = freeze_file(tmp_path, source)
    offset, fragments = 0, []
    while offset is not None:
        page = read_asset(tmp_path, reference["sha256"], offset=offset, max_bytes=page_bytes)
        fragments.append(page["content"])
        offset = page["next_offset"]
    assert "".join(fragments) == text


def test_run_settings_are_editable_in_monitor(tmp_path):
    playwright = pytest.importorskip("playwright.sync_api")
    from conjecture_solver.web.application import SimjectureWebApplication
    from conjecture_solver.web.server import create_server

    s = ResearchService.create(
        tmp_path / "study", "A bounded scientific question", wall_seconds=600
    )
    app = SimjectureWebApplication(runs_root=tmp_path / "runs", scan_roots=(tmp_path,))
    token = app.registry.register(s.root)
    server = create_server(app, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with playwright.sync_playwright() as runtime:
            if not Path(runtime.chromium.executable_path).is_file():
                pytest.skip("Chromium is not installed")
            browser = runtime.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"http://127.0.0.1:{server.server_port}/monitor?campaign={token}")
            page.get_by_role("button", name="Run settings", exact=True).click()
            dialog = page.get_by_role("dialog", name="Study run settings")
            dialog.get_by_label("Review allowance (seconds)").fill("900")
            dialog.get_by_label("Reason", exact=True).fill("The independent review needs more time")
            dialog.get_by_role("button", name="Save settings").click()
            playwright.expect(dialog).not_to_be_visible()
            assert operating_limits(s.root)["review_seconds"] == 900
            browser.close()
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
