"""Metadata-enabled dedicated F: view; keep controller artifacts off the small C: VHD."""

import json
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    target = "/mnt/simjecture-f"
    inspect = subprocess.run(
        ["wsl.exe", "-d", "Ubuntu", "-u", "root", "--", "findmnt", "-J", target],
        capture_output=True,
        text=True,
    )
    if inspect.returncode:
        subprocess.run(["wsl.exe", "-d", "Ubuntu", "-u", "root", "--", "mkdir", "-p", target], check=True)
        subprocess.run(
            [
                "wsl.exe",
                "-d",
                "Ubuntu",
                "-u",
                "root",
                "--",
                "mount",
                "-t",
                "drvfs",
                "F:",
                target,
                "-o",
                "metadata,uid=1000,gid=1000,umask=077",
            ],
            check=True,
        )
    else:
        mounted = json.loads(inspect.stdout)["filesystems"][0]
        if "metadata" not in mounted["options"] or mounted["target"] != target:
            raise ValueError("Dedicated controller mount has unexpected semantics; do not replace it")
    check = subprocess.run(
        [
            "wsl.exe",
            "-d",
            "Ubuntu",
            "--",
            "python3",
            "-c",
            "from pathlib import Path;import os,json; p=Path('/mnt/simjecture-f/Simjecture_Qwen35_9B_20261116/controller-runtime');p.mkdir(exist_ok=True);t=p/'permission-fixture';fd=os.open(t,os.O_CREAT|os.O_RDWR,0o600);mode=os.fstat(fd).st_mode&0o777;os.close(fd);t.unlink();assert mode==0o600,oct(mode);print(json.dumps(dict(file_mode=oct(mode),metadata_mount_ready=True)))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(check.stdout)
    (root / "reports/controller_storage.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
