"""Regression cases discovered by two real temporary workers reviewing this feature."""

import json
import os
import signal
import time
from contextlib import suppress

import pytest

from conjecture_solver.mvp_launch import (
    ProcessIdentity,
    process_identity_matches,
    read_process_identity,
)
from conjecture_solver.research_helpers import finish_helper
from conjecture_solver.research_service import ResearchService
from tests.test_research_director import supervisor
from tests.test_research_helpers import assignment, fake_backend, request, wait_until


def setup_task(tmp_path, timeout=30):
    sup = supervisor(tmp_path)
    item = request(sup.service)
    task = sup.service.assign_helpers(
        [assignment(item["id"], timeout_seconds=timeout)], [], director="director_probe"
    )[0]
    folder = sup.root / "helpers" / task
    return sup, item, task, folder


def identity_from(path):
    return ProcessIdentity.model_validate_json(path.read_text())


def current_native(folder):
    recorded = identity_from(folder / "turn-00001/child_identity.json")
    current = read_process_identity(recorded.pid)
    assert current is not None
    return current


def clean_process(identity):
    if identity and process_identity_matches(identity):
        with suppress(ProcessLookupError):
            os.killpg(identity.pid, signal.SIGKILL)


def test_cancel_after_controller_death_reaps_native_process(tmp_path):
    sup, item, task, folder = setup_task(tmp_path)
    s = sup.service
    options = fake_backend(tmp_path, "Path('started').touch()\ntime.sleep(40)\n")
    native = None
    try:
        s.dispatch_helpers(options)
        wait_until(lambda: (folder / "research/started").exists())
        native = current_native(folder)
        controller = ProcessIdentity.model_validate(
            s._read("helper_tasks", task)["process_identity"]
        )
        os.kill(controller.pid, signal.SIGKILL)
        wait_until(lambda: not process_identity_matches(controller))
        s.cancel_helpers("Stop after controller failure")
        assert s._read("helper_tasks", task)["status"] == "cancelled"
        assert s.help_status(item["id"])["status"] == "resolved"
        wait_until(lambda: not process_identity_matches(native))
    finally:
        clean_process(native)
        s.cancel_helpers("Probe cleanup")


def test_exec_transition_preserves_process_ownership(tmp_path):
    sup, item, task, folder = setup_task(tmp_path)
    s = sup.service
    options = fake_backend(
        tmp_path,
        "import sys\n"
        "Path('started').touch()\n"
        "while not Path('exec_release').exists(): time.sleep(.01)\n"
        "os.execv(sys.executable,[sys.executable,'-c',"
        "\"from pathlib import Path; import time; Path('exec_done').touch(); time.sleep(40)\"])\n",
    )
    native = None
    try:
        s.dispatch_helpers(options)
        wait_until(lambda: (folder / "research/started").exists())
        recorded = identity_from(folder / "turn-00001/child_identity.json")
        (folder / "research/exec_release").touch()
        wait_until(lambda: (folder / "research/exec_done").exists())
        native = current_native(folder)
        assert native.pid == recorded.pid and native.starttime == recorded.starttime
        assert native.argv != recorded.argv
        controller = ProcessIdentity.model_validate(
            s._read("helper_tasks", task)["process_identity"]
        )
        os.kill(controller.pid, signal.SIGKILL)
        wait_until(lambda: not process_identity_matches(controller))
        s.reconcile_helpers()
        assert s._read("helper_tasks", task)["status"] == "failed"
        wait_until(lambda: not process_identity_matches(native))
    finally:
        clean_process(native)
        s.cancel_helpers("Probe cleanup")


@pytest.mark.parametrize("mode", ["cancel", "timeout"])
def test_termination_reaps_term_ignoring_descendant(tmp_path, mode):
    sup, item, task, folder = setup_task(tmp_path, timeout=3 if mode == "timeout" else 30)
    s = sup.service
    body = (
        "import signal\n"
        "pid=os.fork()\n"
        "if pid == 0:\n"
        " signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        " Path('descendant_pid').write_text(str(os.getpid()))\n"
        " time.sleep(40)\n"
        " os._exit(0)\n"
        "while not Path('descendant_pid').exists(): time.sleep(.01)\n"
        "Path('started').touch()\ntime.sleep(40)\n"
    )
    options = fake_backend(tmp_path, body)
    native = descendant = None
    try:
        s.dispatch_helpers(options)
        wait_until(lambda: (folder / "research/started").exists())
        native = current_native(folder)
        descendant = read_process_identity(int((folder / "research/descendant_pid").read_text()))
        assert descendant is not None
        if mode == "cancel":
            s.cancel_helpers("Cancel process tree")
        wait_until(lambda: s.help_status(item["id"])["status"] == "resolved")
        terminal = s._read("helper_tasks", task)["status"]
        assert terminal == ("cancelled" if mode == "cancel" else "timed_out")
        assert not process_identity_matches(native)
        wait_until(lambda: not process_identity_matches(descendant))
    finally:
        if descendant and process_identity_matches(descendant):
            os.kill(descendant.pid, signal.SIGKILL)
        clean_process(native)
        s.cancel_helpers("Probe cleanup")


def test_crash_reconciliation_recovers_available_usage(tmp_path):
    sup, item, task, folder = setup_task(tmp_path)
    s = sup.service
    options = fake_backend(
        tmp_path,
        "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':101,'output_tokens':17}}),flush=True)\n"
        "Path('started').touch()\ntime.sleep(40)\n",
    )
    native = None
    try:
        s.dispatch_helpers(options)
        wait_until(lambda: (folder / "research/started").exists())
        native = current_native(folder)
        controller = ProcessIdentity.model_validate(
            s._read("helper_tasks", task)["process_identity"]
        )
        os.kill(controller.pid, signal.SIGKILL)
        wait_until(lambda: not process_identity_matches(controller))
        s.reconcile_helpers()
        assert s._read("helper_tasks", task)["status"] == "failed"
        sup.process_helpers()
        assert task in sup.state["helper_usage_collected"]
        assert sum(c["input_tokens"] for c in sup.state["usage_by_thread"].values()) == 101
        assert not sup.state.get("usage_unreported_threads")
        assert sup.state.get("usage_incomplete_turns", 0) == 0
        assert "101" in (folder / "turn-00001/response.json").read_text()
    finally:
        clean_process(native)
        s.cancel_helpers("Probe cleanup")


def test_helper_collection_preserves_unidentified_call_count(tmp_path):
    sup, item, task, folder = setup_task(tmp_path)
    finish_helper(
        sup.service,
        task,
        1,
        usage={
            "usage_incomplete_turns": 1,
            "usage_unidentified_calls": 1,
            "usage_unreported_threads": {},
        },
    )
    sup.process_helpers()
    assert sup.service._read("helper_tasks", task)["usage"]["usage_unidentified_calls"] == 1
    assert sup.state["usage_incomplete_turns"] == 1
    assert sup.state.get("usage_unidentified_calls", 0) == 1
    sup.process_helpers(dispatch=False)
    assert sup.state["usage_unidentified_calls"] == 1


def test_parent_shutdown_collects_final_helper_usage(tmp_path):
    sup, item, task, folder = setup_task(tmp_path)
    s = sup.service
    options = fake_backend(
        tmp_path,
        "print(json.dumps({'type':'turn.completed','usage':{'input_tokens':101,'output_tokens':17}}),flush=True)\n"
        "Path('started').touch()\ntime.sleep(40)\n",
    )
    native = None
    try:
        s.dispatch_helpers(options)
        wait_until(lambda: (folder / "research/started").exists())
        native = current_native(folder)
        sup.cancelled = True
        assert sup.run() == 0
        wait_until(lambda: s.help_status(item["id"])["status"] == "resolved")
        record = s._read("helper_tasks", task)
        assert record["status"] == "cancelled"
        assert sum(c["input_tokens"] for c in record["usage"]["usage_by_thread"].values()) == 101
        persisted = json.loads(sup.path.read_text())
        assert sum(c["input_tokens"] for c in persisted["usage_by_thread"].values()) == 101
        assert task in persisted["helper_usage_collected"]
    finally:
        clean_process(native)
        s.cancel_helpers("Probe cleanup")


def test_assignment_retry_repairs_request_link(tmp_path, monkeypatch):
    import conjecture_solver.research_service as module

    sup = supervisor(tmp_path)
    s = sup.service
    item = request(s)
    spec = assignment(item["id"])
    original = module.put

    def fail_request_update(path, value):
        if path.parent.name == "help_requests" and value.get("status") == "running":
            raise OSError("Injected failure between task and request persistence")
        return original(path, value)

    with monkeypatch.context() as patch:
        patch.setattr(module, "put", fail_request_update)
        with pytest.raises(OSError, match="Injected failure"):
            s.assign_helpers([spec], [], director="director_probe")
    recovered = ResearchService(s.root)
    ids = recovered.assign_helpers([spec], [], director="director_retry")
    assert len(ids) == 1
    assert recovered._read("helper_tasks", ids[0])["status"] == "queued"
    status = recovered.help_status(item["id"])
    assert status["status"] == "running" and status["tasks"] == ids
    finish_helper(recovered, ids[0], 1)
    assert recovered.help_status(item["id"])["status"] == "resolved"


def test_dispatch_persistence_failure_leaves_retryable_task(tmp_path, monkeypatch):
    import conjecture_solver.research_helpers as helper_module
    import conjecture_solver.research_service as module

    sup, item, task, folder = setup_task(tmp_path)
    s = sup.service
    options = fake_backend(tmp_path, "Path('started').touch()\n")
    original_put = module.put
    original_popen = helper_module.subprocess.Popen
    children = []

    def fail_identity_commit(path, value):
        if path.parent.name == "helper_tasks" and value.get("process_identity"):
            raise OSError("Injected failure after controller spawn before identity commit")
        return original_put(path, value)

    def capture_popen(*args, **kwargs):
        process = original_popen(*args, **kwargs)
        children.append(process)
        return process

    try:
        with monkeypatch.context() as patch:
            patch.setattr(module, "put", fail_identity_commit)
            patch.setattr(helper_module.subprocess, "Popen", capture_popen)
            with pytest.raises(OSError, match="Injected failure"):
                s.dispatch_helpers(options)
        assert len(children) == 1
        children[0].wait(timeout=10)
        assert children[0].returncode != 0
        record = s._read("helper_tasks", task)
        assert record["status"] == "queued" and not record.get("process_identity")
        assert record["deadline"] > time.time()
        recovered = ResearchService(s.root)
        assert recovered.dispatch_helpers(options) == [task]
        wait_until(lambda: recovered.help_status(item["id"])["status"] == "resolved")
    finally:
        for process in children:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
        s.cancel_helpers("Probe cleanup")
