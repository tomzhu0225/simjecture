"""Record an isolated QE install; leave unrelated environments unchanged."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

prefix = Path(sys.argv[-1]).resolve()
if "--check-disk" in sys.argv:
    target = prefix
    while not target.exists():
        target = target.parent
    if shutil.which("findmnt"):
        fs = subprocess.check_output(
            ["findmnt", "-n", "-o", "FSTYPE", "-T", str(target)], text=True, timeout=10
        ).strip()
        if fs in {"9p", "drvfs"}:
            raise SystemExit(
                "QE requires a Linux-native runtime filesystem; "
                "choose a WSL path backed by sufficient Windows disk space."
            )
    required = (1 if (prefix / "conda-meta/history").is_file() else 3) * 1024**3
    free = shutil.disk_usage(target).free
    if free < required:
        raise SystemExit(f"Insufficient disk: {free} bytes free; need {required} at {target}")
    raise SystemExit(0)
binaries = {}
for name in ("pw.x", "dos.x", "bands.x", "projwfc.x"):
    path = prefix / "bin" / name
    if not path.is_file():
        raise SystemExit(f"Missing QE executable: {path}")
    binaries[name] = hashlib.sha256(path.read_bytes()).hexdigest()
# QE 7.4 does not implement -h: use a bounded EOF startup probe and
# require its exact missing-input diagnostic, rather than accepting arbitrary rc=1.
with tempfile.TemporaryDirectory(prefix="qe-startup-", dir=prefix.parent) as temporary:
    result = subprocess.run(
        [str(prefix / "bin/pw.x")],
        input="",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
        cwd=temporary,
    )
probe_text = result.stdout + result.stderr
if not (
    result.returncode == 1
    and "v.7.4" in result.stdout
    and "Error in routine  read_namelists" in probe_text
    and "could not find namelist &control" in probe_text
):
    raise SystemExit(f"QE startup probe failed (rc={result.returncode}): {probe_text}")
packages = [json.loads(p.read_text()) for p in sorted((prefix / "conda-meta").glob("*.json"))]
record = {
    "profile": "quantum-espresso",
    "version": "7.4",
    "executable_sha256": binaries,
    "availability_probe": {"returncode": result.returncode, "output": probe_text},
    "conda_packages": [
        {k: p.get(k) for k in ("name", "version", "build", "sha256", "url")} for p in packages
    ],
}
(prefix / "share").mkdir(exist_ok=True)
(prefix / "share/build-record.json").write_text(json.dumps(record, indent=2) + "\n")
