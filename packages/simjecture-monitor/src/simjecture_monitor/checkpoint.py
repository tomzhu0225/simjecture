"""Verified artifact forks and public-context replay, not provider-state cloning."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from .events import digest, put


def inventory(root):
    root = Path(root)
    files = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Checkpoint trees cannot contain symbolic links")
        if path.is_file():
            files[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def freeze(work, destination, *, transcript, criteria, worker_config, downstream_policy):
    """Caller must quiesce all writers/processes before taking this checkpoint."""
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Checkpoint destination already exists")
    before = inventory(work)
    shutil.copytree(work, destination / "artifacts")
    after = inventory(work)
    copied = inventory(destination / "artifacts")
    if before != after or copied != before:
        raise ValueError("Checkpoint changed while copying")
    body = dict(
        schema=1,
        artifacts=before,
        public_transcript=transcript,
        criteria=criteria,
        worker_config=worker_config,
        downstream_policy=downstream_policy,
        state_scope="Quiescent artifacts and public transcript; no private provider state",
    )
    body["common_prefix_sha256"] = digest(body)
    for key in ("criteria", "worker_config", "downstream_policy"):
        body[key + "_sha256"] = digest(body[key])
    put(destination / "checkpoint.json", body)
    return body


def restore(checkpoint, destination):
    checkpoint, destination = Path(checkpoint), Path(destination)
    manifest = json.loads((checkpoint / "checkpoint.json").read_text())
    if inventory(checkpoint / "artifacts") != manifest["artifacts"]:
        raise ValueError("Checkpoint artifact hash mismatch")
    original = {k: v for k, v in manifest.items() if not k.endswith("_sha256")}
    if digest(original) != manifest["common_prefix_sha256"]:
        raise ValueError("Checkpoint manifest hash mismatch")
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Restore requires an empty destination")
    shutil.copytree(checkpoint / "artifacts", destination, dirs_exist_ok=True)
    if inventory(destination) != manifest["artifacts"]:
        raise ValueError("Restored artifact hash mismatch")
    return manifest
