"""Operator-only Linux service setup; does not expose an unrestricted HTTP API."""

import json
import pwd
import subprocess
from pathlib import Path


def main():
    user = pwd.getpwnam("simjecture-public")
    uids = [73000, 73001]
    for index, uid in enumerate(uids):
        name = "simjecture-lab-" + str(index)
        try:
            existing = pwd.getpwnam(name)
            if existing.pw_uid != uid:
                raise ValueError("Executor user identity changed")
        except KeyError:
            subprocess.run(["groupadd", "-g", str(uid), name], check=True)
            subprocess.run(
                [
                    "useradd",
                    "-M",
                    "-u",
                    str(uid),
                    "-g",
                    str(uid),
                    "-d",
                    "/nonexistent",
                    "-s",
                    "/usr/sbin/nologin",
                    name,
                ],
                check=True,
            )
    config = {
        "socket": "/run/simjecture-executor/lab.sock",
        "gateway_uid": user.pw_uid,
        "gateway_gid": user.pw_gid,
        "uids": uids,
        "work_root": "/srv/simjecture-labs",
        "cpus": 4,
        "memory_bytes": 4 * 1024**3,
        "gpu_ids": ["0", "1"],
        "path": "/opt/simjecture-public/tools/bin:/opt/simjecture-public/venv/bin:"
        "/usr/local/bin:/usr/bin:/bin",
        "library_path": "/usr/local/cuda-12.8/targets/x86_64-linux/lib",
        "read_only": [
            "/usr",
            "/bin",
            "/lib",
            "/lib64",
            "/etc",
            "/proc",
            "/sys",
            "/opt/simjecture-public/tools",
            "/opt/simjecture-public/venv",
            "/opt/simjecture-public/python",
            "/opt/simjecture-public/tool-sources",
            "/opt/simjecture/reconnection-20261002/FLASH4.8",
            "/opt/simote/radiation-production-features-20260930/warpx",
        ],
    }
    path = Path("/opt/simjecture-public/executor.json")
    path.write_text(json.dumps(config, indent=2) + "\n")
    path.chmod(0o600)
    aliases = Path("/opt/simjecture-public/tools/bin")
    aliases.mkdir(exist_ok=True)
    for name, binary in {
        "flash-1d": "flash-1d",
        "flash-2d": "flash-2d",
        "flash-rz": "flash-rz",
        "warpx-1d": "warpx-1d-cuda",
        "warpx-2d": "warpx-2d-cuda",
        "warpx-rz": "warpx-rz-cuda",
        "warpx-3d": "warpx-3d-cuda",
    }.items():
        link = aliases / name
        if not link.exists():
            link.symlink_to(aliases.parent / binary)
    conf = Path("/etc/supervisor/conf.d/simjecture-executor.conf")
    conf.write_text("""[program:simjecture-executor]
command=/opt/simjecture-public/venv/bin/python -I -m conjecture_solver.public.lab_broker \
--config /opt/simjecture-public/executor.json
user=root
directory=/opt/simjecture-public
autostart=true
autorestart=true
startsecs=3
stopasgroup=true
killasgroup=true
stdout_logfile=/srv/simjecture-public/logs/executor.log
stderr_logfile=/srv/simjecture-public/logs/executor-error.log
stdout_logfile_maxbytes=10MB
stderr_logfile_maxbytes=10MB
""")
    subprocess.run(["supervisorctl", "reread"], check=True)
    subprocess.run(["supervisorctl", "update"], check=True)
    print(
        "Dedicated executor configured; general tools await qualification "
        "and private gateway transport"
    )


if __name__ == "__main__":
    main()
