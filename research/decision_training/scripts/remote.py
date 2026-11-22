"""Compatibility entry for historical helpers using ignored local SSH routes."""

import json
import os
import sys
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
HOST = os.environ.get("SIMJECTURE_TRAINING_HOST", "training-node")
configuration = ROOT / "config/pipeline.local.json"
REMOTE_ROOT = json.loads(configuration.read_bytes())["remote_root"] if configuration.exists() else "/srv/simjecture/research/decision_training"


def connection(host=HOST):
    name = "ssh-cpu-route.local.json" if host == "simulation-node" else "ssh-route.local.json"
    path = ROOT / "config" / name
    argv = json.loads(path.read_bytes()) if path.exists() else ["/usr/bin/ssh", "-o", "BatchMode=yes", host]
    binary = PureWindowsPath(argv[0])
    if os.name != "nt" and binary.drive:
        argv[0] = "/mnt/" + binary.drive[0].lower() + "/" + "/".join(binary.parts[1:])
    return argv


def python(script, *, timeout=60):
    from research_decision.managed_ssh import run_ssh
    return run_ssh(connection(), ["python3", "-"], input=script.encode(), timeout=timeout)
