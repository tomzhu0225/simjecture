"""Recover a crashed controller without changing its original study or deadline."""

import json
import subprocess
import sys
import time
from pathlib import Path


def read(path):
    return json.loads(path.read_text()) if path.exists() else {}


task = Path(sys.argv[1]).resolve()
config = read(task / "operator/launch.json")
campaign = Path(config["campaign"])
attempt = 0
while True:
    manifest = read(campaign / "research.json")
    state = read(campaign / "supervisor/state.json")
    control = read(campaign / "supervisor/control.json")
    status = state.get("status", "")
    if (
        (manifest and time.time() >= manifest["deadline"])
        or status in {"completed", "budget_exhausted", "cancelled"}
        or status.startswith("paused")
        or control.get("command") in {"pause", "cancel"}
        or (campaign / "campaign_closeout.json").exists()
    ):
        print(json.dumps({"event": "watchdog_finished", "status": status}), flush=True)
        break
    attempt += 1
    with (task / "operator/controller.log").open("ab", buffering=0) as log:
        child = subprocess.Popen(config["command"], cwd=task / "source", stdout=log, stderr=log)
        print(
            json.dumps({"event": "controller_started", "attempt": attempt, "pid": child.pid}),
            flush=True,
        )
        code = child.wait()
    print(
        json.dumps({"event": "controller_exited", "attempt": attempt, "returncode": code}),
        flush=True,
    )
    # Re-read authoritative state before a restart, including operator controls.
    if attempt >= 3 and not (campaign / "study-launch.json").exists():
        raise SystemExit("Repeated launch failure before a durable supervisor contract")
    time.sleep(min(60, 5 * attempt))
