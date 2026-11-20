"""Deploy preparation files and inventory solvers. Does not launch research or training."""

import base64
import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

from remote import REMOTE_ROOT, python

ROOT = Path(__file__).resolve().parents[1]


def main():
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for directory in ["research_decision", "config", "schemas", "prompts", "tasks", "plans", "data"]:
            for path in (ROOT / directory).rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts:
                    archive.add(path, arcname=path.relative_to(ROOT).as_posix())
        archive.add(ROOT / "实验协议.md", arcname="实验协议.md")
        archive.add(ROOT / "README.md", arcname="README.md")
        archive.add(ROOT / "运行入口与待验证项.md", arcname="运行入口与待验证项.md")
        source = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT / "vendor/simjecture"),
                "archive",
                "HEAD",
                "src",
                "pyproject.toml",
                "capabilities",
                "schemas",
                "LICENSE",
            ],
            capture_output=True,
            check=True,
        )
        with tarfile.open(fileobj=io.BytesIO(source.stdout), mode="r:") as upstream:
            for member in upstream.getmembers():
                if member.isfile():
                    member.name = "vendor/simjecture/" + member.name
                    archive.addfile(member, upstream.extractfile(member))
    data = buffer.getvalue()
    script = f"""import base64,hashlib,io,json,os,tarfile,subprocess
from pathlib import Path
root=Path({REMOTE_ROOT!r})
root.mkdir(parents=True,exist_ok=True)
payload=base64.b64decode({base64.b64encode(data).decode()!r})
if hashlib.sha256(payload).hexdigest()!={hashlib.sha256(data).hexdigest()!r}:raise ValueError("Transfer checksum mismatch")
with tarfile.open(fileobj=io.BytesIO(payload),mode="r:gz") as archive:
 for member in archive.getmembers():
  path=(root/member.name).resolve()
  if not path.is_relative_to(root) or not member.isfile():raise ValueError("Unexpected archive member")
  path.parent.mkdir(parents=True,exist_ok=True)
  path.write_bytes(archive.extractfile(member).read())
tools=Path('/opt/simjecture-tools')
for name,target in {{'warpx':tools/'warpx','athena-source':tools/'athena','training-python':tools/'decision-runtime/bin/python','simjecture-python':tools/'simjecture-runtime/bin/python'}}.items():
 link=root/'resources'/name
 link.parent.mkdir(exist_ok=True)
 if not link.exists():link.symlink_to(target)
inventory={{'root':str(root),'physics_experiments_started':0,'training_updates_started':0,'solvers':{{}}}}
for name,path in {{'warpx_1d':tools/'warpx/bin/warpx.1d','warpx_2d':tools/'warpx/bin/warpx.2d','warpx_3d':tools/'warpx/bin/warpx.3d','athena':tools/'athena/bin/athena'}}.items():
 with path.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
 check=subprocess.run(['ldd',str(path)],capture_output=True,text=True,timeout=10)
 inventory['solvers'][name]={{'path':str(path),'sha256':sha,'dynamic_dependencies_resolved':'not found' not in check.stdout,'ldd_exit':check.returncode}}
(root/'preparation-status.json').write_text(json.dumps(inventory,indent=2))
print(json.dumps(inventory))
"""
    result = python(script, timeout=60)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace")[-1500:])
    inventory = json.loads(result.stdout)
    (ROOT / "reports" / "remote_preparation.json").write_text(
        json.dumps(inventory, indent=2), encoding="utf-8"
    )
    print(json.dumps(inventory))


if __name__ == "__main__":
    main()
