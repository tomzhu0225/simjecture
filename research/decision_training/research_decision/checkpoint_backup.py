"""CPU/I/O-only, verified secondary copies of this pilot's immutable checkpoints."""

import hashlib
import json
import time
from pathlib import Path

from .archive import remote_script, verify_archive
from .remote_control import Remote
from .storage import read_json, write_json


def backup_checkpoint(remote, checkpoint, destination):
    # Check both the checkpoint location and each manifest filename on the
    # remote owner. No optimizer/model deserialization is needed for a backup.
    body = f"""from pathlib import Path
import hashlib,json
project=Path({remote.root!r}).resolve()
root=Path({checkpoint!r}).resolve()
if not root.is_relative_to(project/'checkpoints') or root==project/'checkpoints':raise ValueError('Checkpoint ownership')
manifest=json.loads((root/'manifest.json').read_bytes())
files={{}}
for name,expected in manifest.items():
 p=root/name
 if Path(name).name!=name or p.is_symlink() or not p.is_file():raise ValueError('Unsafe checkpoint member')
 with p.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
 if actual!=expected:raise ValueError('Checkpoint changed')
 files[name]={{'sha256':actual,'bytes':p.stat().st_size}}
p=root/'manifest.json'
with p.open('rb') as f:files[p.name]={{'sha256':hashlib.file_digest(f,'sha256').hexdigest(),'bytes':p.stat().st_size}}
print(json.dumps(dict(files=files,checkpoint=str(root))))
"""
    manifest = json.loads(remote_script(remote, body, timeout=300))
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "checkpoint.tar.gz"
    receipt_path = destination / "backup-receipt.json"
    previous = read_json(receipt_path)
    if previous and archive.exists():
        if previous["files"] != manifest["files"]:
            raise ValueError("An immutable checkpoint changed after its secondary copy")
        return previous
    partial = destination / "checkpoint.tar.gz.partial"
    stream_code = f"""from pathlib import Path
import gzip,sys,tarfile,time
root=Path({checkpoint!r}).resolve()
names={list(manifest['files'])!r}
class LimitedOutput:
 def __init__(self):self.started=time.monotonic();self.sent=0
 def write(self,data):
  count=sys.stdout.buffer.write(data);self.sent+=count
  delay=self.sent/(1024*1024)-(time.monotonic()-self.started)
  if delay>0:time.sleep(delay)
  return count
 def flush(self):sys.stdout.buffer.flush()
with gzip.GzipFile(fileobj=LimitedOutput(),mode='wb',compresslevel=1) as compressed:
 with tarfile.open(fileobj=compressed,mode='w|') as archive:
  for name in names:
   p=root/name
   if Path(name).name!=name or p.is_symlink() or not p.is_file():raise ValueError('Unsafe member')
   archive.add(p,arcname=name,recursive=False)
"""
    try:
        with partial.open("wb") as output:
            remote_script(remote, stream_code, output=output, timeout=1800)
        verify_archive(partial, manifest)
        partial.replace(archive)
    finally:
        partial.unlink(missing_ok=True)
    with archive.open("rb") as stream:
        archive_sha = hashlib.file_digest(stream, "sha256").hexdigest()
    receipt = dict(
        manifest,
        archive_sha256=archive_sha,
        archive_bytes=archive.stat().st_size,
        completed_at=time.time(),
        optimizer_and_rank_RNG_preserved=True,
        remote_checkpoint_deleted=False,
    )
    write_json(receipt_path, receipt, immutable=True)
    return receipt


def main():
    root = Path(__file__).resolve().parents[1]
    cfg = read_json(root / "config/pipeline.local.json")
    remote = Remote(cfg)
    copied = set()
    deadline = read_json(root / "pilot/plan.json")["deadline_epoch"]
    while time.time() < deadline:
        if read_json(root / "pilot/status.json", {}).get("phase") == "autonomous_student_RLOO_running":
            write_json(root / "pilot/backup-status.json", dict(
                deferred_until_collection_finishes=True, remote_durable_checkpoints_unchanged=True,
                reason="prioritize live sampling and small SSH control messages", at=time.time(),
            ))
            time.sleep(60)
            continue
        try:
            request = remote.read("data/pilot/rloo-inbox/rollout-request.json") or {}
            autonomous = remote.read("data/pilot-autonomous/rloo-inbox/rollout-request.json") or {}
        except Exception as error:
            write_json(root / "pilot/backup-status.json", dict(error=repr(error), at=time.time(), retrying=True))
            time.sleep(60)
            continue
        candidates = [cfg["remote_root"] + "/checkpoints/pilot-sft/sft-epoch-2"]
        if request.get("policy_path"):
            candidates.append(request["policy_path"])
        if autonomous.get("policy_path"):
            candidates.append(autonomous["policy_path"])
        for checkpoint in dict.fromkeys(candidates):
            if checkpoint in copied:
                continue
            relative = Path(checkpoint).relative_to(Path(cfg["remote_root"]) / "checkpoints")
            try:
                receipt = backup_checkpoint(remote, checkpoint, root / "checkpoint-backups" / relative)
            except Exception as error:
                write_json(root / "pilot/backup-status.json", dict(error=repr(error), at=time.time()))
                continue
            copied.add(checkpoint)
            write_json(
                root / "pilot/backup-status.json",
                dict(copied=sorted(copied), latest_archive_sha256=receipt["archive_sha256"], at=time.time()),
            )
        if read_json(root / "pilot/status.json", {}).get("phase") in {"complete", "deadline_reached"}:
            break
        time.sleep(60)


if __name__ == "__main__":
    main()
