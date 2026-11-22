"""Hash-verified cold copies for immutable, terminal remote simulation workspaces."""

import base64
import hashlib
import json
import re
import subprocess
import tarfile
from pathlib import Path

from .storage import read_json, write_json


def remote_script(remote, body, *, output=None, timeout=3600):
    from .managed_ssh import run_ssh

    result = run_ssh(
        remote.route, ["python3", "-"],
        input=body.encode(),
        stdout=output,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-1800:])
    return result.stdout


def job_directory(remote, identifier):
    if not re.fullmatch(r"job_[0-9a-f]{40}", identifier):
        raise ValueError("Only an explicitly identified native worker job can be archived")
    return remote.root + "/cpu-worker/jobs/" + identifier


def snapshot_manifest(remote, identifier):
    path = job_directory(remote, identifier)
    body = f"""from pathlib import Path
import hashlib,json
root=Path({path!r}).resolve()
state=json.loads((root/'state.json').read_bytes())
if state['status'] not in {{'succeeded','failed','timed_out','cancelled','interrupted','partial'}}:raise ValueError('Active job cannot be archived')
files={{}}
for p in (root/'workspace').rglob('*'):
 if p.is_symlink():raise ValueError('Linked output cannot enter the cold archive')
 if p.is_file():
  with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
  files[p.relative_to(root).as_posix()]={{'sha256':sha,'bytes':p.stat().st_size}}
print(json.dumps(dict(job_id=state['id'],status=state['status'],files=files)))
"""
    return json.loads(remote_script(remote, body))


def archive_job(remote, identifier, destination, *, evict=False):
    destination = Path(destination) / identifier
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / "workspace.tar.gz"
    manifest = snapshot_manifest(remote, identifier)
    if not archive.exists():
        partial = archive.with_suffix(".partial")
        body = f"""import gzip,sys,tarfile
from pathlib import Path
root=Path({job_directory(remote, identifier)!r}).resolve()
with gzip.GzipFile(fileobj=sys.stdout.buffer,mode='wb',compresslevel=1) as compressed:
 with tarfile.open(fileobj=compressed,mode='w|') as tar:
  tar.add(root/'workspace',arcname='workspace',recursive=True)
"""
        try:
            with partial.open("wb") as output:
                remote_script(remote, body, output=output)
            verify_archive(partial, manifest)
            partial.replace(archive)
        finally:
            partial.unlink(missing_ok=True)
    else:
        saved = read_json(destination / "manifest.json")
        if saved is None:
            verify_archive(archive, manifest)
        elif saved["files"] != manifest["files"] and manifest["files"]:
            raise ValueError("Terminal remote artifacts changed after archival")
        else:
            manifest = saved
    with archive.open("rb") as stream:
        manifest["archive_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    write_json(destination / "manifest.json", manifest, immutable=True)
    if evict:
        expected = base64.b64encode(json.dumps(manifest["files"]).encode()).decode()
        body = f"""import base64,hashlib,json,shutil
from pathlib import Path
root=Path({job_directory(remote, identifier)!r}).resolve()
expected=json.loads(base64.b64decode({expected!r}))
state=json.loads((root/'state.json').read_bytes())
if state['status'] not in {{'succeeded','failed','timed_out','cancelled','interrupted','partial'}}:raise ValueError('Job is active')
workspace=(root/'workspace').resolve()
if not workspace.is_relative_to(root) or workspace==root:raise ValueError('Workspace ownership check failed')
for name,item in expected.items():
 p=(root/name).resolve()
 if not p.is_relative_to(workspace):raise ValueError('Artifact escaped its owned workspace')
 with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
 if sha!=item['sha256']:raise ValueError('Remote output changed before verified eviction')
if workspace.exists():shutil.rmtree(workspace)
workspace.mkdir()
print('verified cold copy retained; terminal metadata retained')
"""
        remote_script(remote, body)
    return dict(
        job_id=identifier, archive=str(archive), manifest=str(destination / "manifest.json"), evicted=evict
    )


def verify_archive(path, manifest):
    found = set()
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            if member.isdir():
                continue
            if not member.isfile() or member.name not in manifest["files"]:
                raise ValueError("Cold archive contains an unexpected member")
            expected = manifest["files"][member.name]
            stream = archive.extractfile(member)
            if (
                hashlib.file_digest(stream, "sha256").hexdigest() != expected["sha256"]
                or member.size != expected["bytes"]
            ):
                raise ValueError("Cold archive failed complete artifact verification")
            found.add(member.name)
    if found != set(manifest["files"]):
        raise ValueError("Cold archive omitted a declared artifact")


def restore_job(remote, identifier, destination):
    destination = Path(destination) / identifier
    manifest = read_json(destination / "manifest.json")
    archive = destination / "workspace.tar.gz"
    verify_archive(archive, manifest)
    # Tar extraction is confined to one validated worker job. It is sent as
    # streaming stdin; model context never contains archive bytes or secrets.
    script = f"""import sys,tarfile
from pathlib import Path
root=Path({job_directory(remote, identifier)!r}).resolve()
with tarfile.open(fileobj=sys.stdin.buffer,mode='r|gz') as tar:
 for member in tar:
  target=(root/member.name).resolve()
  if not target.is_relative_to(root/'workspace') or member.issym() or member.islnk():raise ValueError('Unsafe archive member')
  if member.isdir():target.mkdir(parents=True,exist_ok=True)
  elif member.isfile():
   target.parent.mkdir(parents=True,exist_ok=True)
   with target.open('wb') as out:
    import shutil
    shutil.copyfileobj(tar.extractfile(member),out)
  else:raise ValueError('Unsupported archive member')
"""
    import shlex

    with archive.open("rb") as source:
        result = subprocess.run(
            remote.route + ["python3 -c " + shlex.quote(script)],
            stdin=source,
            capture_output=True,
            timeout=3600,
        )
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-1200:])
    if snapshot_manifest(remote, identifier)["files"] != manifest["files"]:
        raise ValueError("Restored scientific artifact hashes differ")
    return dict(restored=True, job_id=identifier)
