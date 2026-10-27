"""The parent enforces helper deadlines even when a live controller is stalled."""

import json
import os
import signal
from contextlib import suppress
from types import SimpleNamespace

import pytest

from conjecture_solver import research_helpers
from conjecture_solver.research_helper_runtime import owned_alive, process_stat
from tests.test_research_director import supervisor
from tests.test_research_helpers import assignment, fake_backend, request, wait_until


@pytest.mark.parametrize("cancel_requested", [False, True])
def test_parent_expires_stopped_controller_and_frees_helper_slot(
    tmp_path, monkeypatch, cancel_requested
):
    service = supervisor(tmp_path).service
    item = request(service)
    tasks = service.assign_helpers(
        [assignment(item["id"], name, timeout_seconds=120) for name in ["first.txt", "next.txt"]],
        [],
        director="fixture",
    )
    options = fake_backend(
        tmp_path,
        "import subprocess,sys\n"
        "child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
        "Path('started').write_text(str(child.pid))\ntime.sleep(60)\n",
    )
    controller = native = descendant = None
    try:
        assert service.dispatch_helpers(options, maximum=1) == [tasks[0]]
        work = service.root / "helpers" / tasks[0] / "research"
        wait_until(lambda: (work / "started").exists())
        task = service._read("helper_tasks", tasks[0])
        controller = task["process_identity"]
        native = json.loads((work.parent / "turn-00001/child_identity.json").read_text())
        descendant = process_stat(int((work / "started").read_text()))
        assert owned_alive(controller) and owned_alive(native) and owned_alive(descendant)
        os.kill(controller["pid"], signal.SIGSTOP)
        service.help_status()
        assert service._read("helper_tasks", tasks[0])["status"] == "running"
        assert owned_alive(controller)
        if cancel_requested:
            service.cancel_helpers("Operator cancelled before the deadline watchdog")

        # Advance only the parent's view of the deadline. The stopped controller
        # cannot execute its own watchdog; no actual provider or long sleep is needed.
        with monkeypatch.context() as patch:
            patch.setattr(
                research_helpers, "time", SimpleNamespace(time=lambda: task["deadline"] + 1)
            )
            service.help_status()

        expired = service._read("helper_tasks", tasks[0])
        assert expired["status"] == ("cancelled" if cancel_requested else "timed_out")
        wait_until(lambda: not any(owned_alive(i) for i in [controller, native, descendant]))
        assert expired["usage"]["usage_incomplete_turns"] == 1
        if cancel_requested:
            assert service.help_status(item["id"])["status"] == "resolved"
            assert service.dispatch_helpers(options, maximum=1) == []
        else:
            assert service.dispatch_helpers(options, maximum=1) == [tasks[1]]
            assert service._read("helper_tasks", tasks[1])["process_identity"]
    finally:
        if owned_alive(controller):
            with suppress(ProcessLookupError):
                os.kill(controller["pid"], signal.SIGCONT)
        service.cancel_helpers("Test cleanup")
        wait_until(
            lambda: all(
                t["status"] not in research_helpers.ACTIVE for t in service.help_status()["tasks"]
            )
        )
        for identity in [controller, native, descendant]:
            if owned_alive(identity):
                with suppress(ProcessLookupError):
                    os.kill(identity["pid"], signal.SIGKILL)
