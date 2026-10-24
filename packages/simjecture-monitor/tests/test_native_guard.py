import json
import os
import subprocess
import sys
import time

from simjecture_monitor.events import put


def test_native_guard_caps_all_invocations_and_records_actual_starts(tmp_path):
    executable = tmp_path / "subject"
    executable.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(.3)\n")
    executable.chmod(0o700)
    path = tmp_path / "budget.json"
    put(
        path,
        dict(
            deadline=time.time() + 20,
            maximum_starts=2,
            maximum_per_continuation=2,
            maximum_concurrent=1,
            executable=str(executable),
            starts=[],
        ),
    )
    env = dict(
        os.environ,
        SIMJECTURE_NATIVE_BUDGET=str(path),
        SIMJECTURE_CONTINUATION="one",
        SIMJECTURE_CONTINUATION_DEADLINE=str(time.time() + 20),
    )
    command = [sys.executable, "-m", "simjecture_monitor.native_guard", "exec", "prompt"]
    first = subprocess.Popen(command, env=env, start_new_session=True)
    second = subprocess.Popen(command, env=env, start_new_session=True)
    assert first.wait(timeout=10) == second.wait(timeout=10) == 0
    assert (
        subprocess.run(command, env=env, start_new_session=True, capture_output=True).returncode
        == 125
    )
    rows = json.loads(path.read_text())["starts"]
    assert len(rows) == 2 and all(r.get("native") for r in rows)
    rows.sort(key=lambda r: r["started_at"])
    assert rows[0]["ended_at"] <= rows[1]["started_at"]
