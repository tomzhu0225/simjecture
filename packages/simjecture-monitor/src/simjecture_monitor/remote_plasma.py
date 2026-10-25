"""Run bounded plasma controls on an explicitly configured SSH machine.

The coordinator receives saved diagnostics and an execution receipt. This is a
cooperative research backend, not an adversarial worker sandbox. No solver runs
on the coordinator. SSH credentials stay in its existing machine profile.
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import hashlib
import json
import os
import re
import shlex
import subprocess
import tarfile
import time
import uuid
from pathlib import Path

from .events import put

REMOTE = r"""
import base64,fcntl,hashlib,json,os,subprocess,sys,tarfile,time
from pathlib import Path
job=json.loads(base64.b64decode(PAYLOAD))
root=Path(job['remote_root'])
root.mkdir(parents=True,exist_ok=True)
os.chdir(root)
folder=root/job['id']
folder.mkdir(exist_ok=False)
(folder/'inputs').write_text(job['inputs'])
binary=Path(job['binary'])
hasher=hashlib.sha256()
with binary.open('rb') as stream:
 for chunk in iter(lambda:stream.read(1048576),b''):hasher.update(chunk)
command=[str(binary),'inputs',*job['overrides'],f"amr.n_cell={job['cells']}",
 f"max_step={job['steps']}",'amr.max_level=0','diagnostics.diags_names=diag1',
 'diag1.file_prefix=plot',f"diag1.intervals={job['steps']}",
 'amrex.the_arena_init_size=67108864','warpx.verbose=0']
receipt=dict(name=job['name'],request_id=job['id'],cells=job['cells'],steps=job['steps'],
 command=command,binary_sha256=hasher.hexdigest(),
 input_sha256=hashlib.sha256(job['inputs'].encode()).hexdigest(),
 remote_host=os.uname().nodename,status='queued',queued_at=time.time())
with (root/'gpu.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 receipt.update(status='running',started_at=time.time())
 (folder/'receipt.json').write_text(json.dumps(receipt))
 start=time.monotonic()
 try:
  with (folder/'run.log').open('w') as log:
   p=subprocess.run(command,cwd=folder,stdout=log,stderr=subprocess.STDOUT,
    env=dict(os.environ,OMP_NUM_THREADS='2',CUDA_VISIBLE_DEVICES=str(job['gpu'])),timeout=90)
  receipt.update(returncode=p.returncode,status='succeeded' if p.returncode==0 else 'failed')
 except subprocess.TimeoutExpired:receipt.update(returncode=None,status='timeout')
 finally:
  receipt.update(wall_seconds=time.monotonic()-start,ended_at=time.time())
  (folder/'receipt.json').write_text(json.dumps(receipt,indent=2))
# Stream files without reading plot data into memory. Include failures for diagnosis.
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as archive:
 for path in sorted(folder.rglob('*')):
  if path.is_file():archive.add(path,arcname=str(path.relative_to(folder)),recursive=False)
"""


def extract_records(archive_path, destination):
    """Reject links, traversal, duplicates and unexpectedly large transfers."""
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        names = [m.name for m in members]
        if len(names) != len(set(names)) or sum(m.size for m in members) > 100_000_000:
            raise ValueError("Unexpected remote diagnostic archive")
        for member in members:
            path = Path(member.name)
            if not member.isfile() or path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError("Unsafe remote diagnostic member")
        archive.extractall(destination, members=members, filter="data")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--input", type=Path, default=Path("inputs"))
    parser.add_argument("--cells", type=int, required=True)
    parser.add_argument("--steps", type=int, required=True)
    parser.add_argument("--set", action="append", default=[])
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,60}", args.name):
        raise ValueError("Use a simple unique run name")
    if not 16 <= args.cells <= 1024 or not 1 <= args.steps <= 4096:
        raise ValueError("Run exceeds the simulation size budget")
    work = Path.cwd().resolve()
    source = args.input.resolve()
    if not source.is_relative_to(work):
        raise ValueError("Input must be within the research workspace")
    settings = json.loads((work / "environment.json").read_text())
    backend = json.loads(Path(os.environ["SIMJECTURE_PLASMA_BACKEND"]).read_text())
    machine = json.loads(Path(backend["machine_profile"]).read_text())["machine"]
    runs = work / "runs"
    runs.mkdir(exist_ok=True)
    folder = runs / args.name
    job = dict(
        id=uuid.uuid4().hex,
        name=args.name,
        cells=args.cells,
        steps=args.steps,
        inputs=source.read_text(),
        overrides=args.set,
        binary=backend["binary"],
        remote_root=backend["remote_root"],
        gpu=backend["gpu"],
    )
    with (work / ".run-budget.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if len(list(runs.glob("*/receipt.json"))) >= settings["max_runs"]:
            raise RuntimeError("Simulation budget exhausted")
        folder.mkdir(exist_ok=False)
        queued = dict(
            status="queued",
            request_id=job["id"],
            queued_at=time.time(),
            name=args.name,
            cells=args.cells,
            steps=args.steps,
        )
        put(folder / "receipt.json", queued)
    payload = base64.b64encode(json.dumps(job).encode()).decode()
    program = REMOTE.replace("PAYLOAD", repr(payload))
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=15",
        "-o",
        "UserKnownHostsFile=" + machine["known_hosts"],
        "-i",
        machine["identity_file"],
        "-p",
        str(machine["port"]),
        machine["user"] + "@" + machine["host"],
        shlex.join(["runuser", "-u", machine["run_as"], "--", "python3", "-"]),
    ]
    archive = folder / "transfer.tar"
    started = time.time()
    result = None
    try:
        with archive.open("wb") as output, (folder / "transport.log").open("wb") as error:
            result = subprocess.run(
                command, input=program.encode(), stdout=output, stderr=error, timeout=180
            )
        if result.returncode:
            raise RuntimeError(
                "Remote solver transport failed; inspect transport.log before retrying"
            )
        staging = folder / "received"
        staging.mkdir()
        extract_records(archive, staging)
        receipt = json.loads((staging / "receipt.json").read_text())
        if (
            receipt["request_id"] != job["id"]
            or receipt["input_sha256"] != hashlib.sha256(job["inputs"].encode()).hexdigest()
            or receipt["cells"] != args.cells
            or receipt["steps"] != args.steps
        ):
            raise ValueError("Remote execution identity mismatch")
    except Exception as failure:
        # Loss of transport does not establish whether the remote solver ran.
        # Preserve the request identity and budget reservation for reconciliation;
        # never leave a stale queued/running claim or silently submit another job.
        put(
            folder / "receipt.json",
            queued
            | dict(
                status="unknown",
                returncode=None,
                transport_status="timeout"
                if isinstance(failure, subprocess.TimeoutExpired)
                else "failed",
                transport_returncode=result.returncode if result is not None else None,
                transport_error_type=type(failure).__name__,
                transport_ended_at=time.time(),
                reconciliation_required=True,
            ),
        )
        raise
    for item in staging.iterdir():
        item.replace(folder / item.name)
    staging.rmdir()
    archive.unlink()
    receipt.update(coordinator_roundtrip_seconds=time.time() - started)
    (folder / "receipt.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))
    if receipt["status"] != "succeeded":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
