import os
import resource
import sys

import pytest

from conjecture_solver.mvp_agent import BubblewrapSandbox, MVPAgentConfig
from conjecture_solver.resident_memory import process_tree_rss


def test_linux_process_tree_has_resident_memory():
    assert process_tree_rss(os.getpid()) > 0
    assert process_tree_rss(999999999) == 0


def test_gpu_policy_allows_virtual_reservations_and_enforces_resident_budget(tmp_path):
    from conjecture_solver.execution import probe_execution_backend

    if not probe_execution_backend("bubblewrap")["available"]:
        pytest.skip("Linux namespaces unavailable")
    sandbox = BubblewrapSandbox(
        tmp_path, MVPAgentConfig(max_command_seconds=5, max_memory_bytes=128 * 1024**2)
    )
    sandbox._resident_memory_guard = True
    # The same reservation used by a CUDA context must not consume RAM quota.
    result = sandbox._run_command(
        [sys.executable, "-c", "import mmap; x=mmap.mmap(-1,8*1024**3); print('reserved')"]
    )
    assert result.returncode == 0 and "reserved" in result.stdout
    # Actual resident allocation must still stop the process, including children.
    result = sandbox._run_command(
        [
            sys.executable,
            "-c",
            "import subprocess,time,sys; "
            "p=subprocess.Popen([sys.executable,'-c',"
            "'import time; x=bytearray(250*1024**2); time.sleep(4)']); p.wait()",
        ]
    )
    assert result.returncode == 137
    assert "Resident memory budget exceeded" in result.stderr


def test_cpu_address_limit_remains_in_place(tmp_path, monkeypatch):
    calls = []
    sandbox = BubblewrapSandbox(tmp_path, MVPAgentConfig(max_memory_bytes=123456789))
    monkeypatch.setattr(resource, "setrlimit", lambda kind, values: calls.append((kind, values)))
    sandbox._limits()
    assert (resource.RLIMIT_AS, (123456789, 123456789)) in calls
