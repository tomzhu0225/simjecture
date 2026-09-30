"""Address-only SSH onboarding and bounded operator maintenance commands."""

import os
import re
import shlex
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from .worker_protocol import AutomaticSetup, Machine, WorkerConfig, fingerprint


def parse_address(address):
    """Accept an SSH address or the usual ssh -p PORT user@host command."""
    if not isinstance(address, str) or not address.strip() or len(address) > 1000:
        raise ValueError("Enter an SSH address, for example ssh -p 23 root@host")
    tokens = shlex.split(address.strip())
    port, user = None, None
    if tokens[0] == "ssh":
        tokens = tokens[1:]
        while tokens and tokens[0].startswith("-"):
            option = tokens.pop(0)
            if option in {"-p", "-l"} and tokens:
                value = tokens.pop(0)
                if option == "-p":
                    port = int(value)
                else:
                    user = value
            elif re.fullmatch(r"-p[0-9]+", option):
                port = int(option[2:])
            else:
                raise ValueError("Use ssh -p PORT user@host; put key paths in advanced settings")
    if len(tokens) != 1:
        raise ValueError("Enter one SSH address")
    authority = tokens[0]
    parsed = urlsplit(authority if authority.startswith("ssh://") else "ssh://" + authority)
    if (
        parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Enter an SSH host; put the password in its separate field")
    values = {
        "host": parsed.hostname or "",
        "port": port if port is not None else parsed.port if parsed.port is not None else 22,
        "user": user or parsed.username or "",
    }
    Machine.model_validate({"id": "validate", "root": "/tmp/validation", **values})
    return values


def basic_profile(address, overrides=None):
    connection = parse_address(address)
    identifier = "ssh-" + fingerprint(connection)[:10]
    setup = AutomaticSetup.model_validate(overrides or {})
    values = setup.model_dump(exclude_none=True)
    config = WorkerConfig.model_validate(
        {
            key: values[key]
            for key in ("cpus", "memory_mb", "gpu_ids", "max_jobs", "capabilities")
            if key in values
        }
    )
    if setup.execution_backend != "auto":
        config.execution_backend = setup.execution_backend
    return Machine(
        id=identifier,
        label=connection["host"],
        **connection,
        root=setup.root or f"/tmp/simjecture-onboarding-{identifier}",
        config=config,
        automatic_setup=setup,
    ).model_dump(mode="json")


def hardware():
    """Visible CPU/RAM/GPU inventory; conservative default reservations."""
    cpus = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count() or 1
    quota = Path("/sys/fs/cgroup/cpu.max")
    if quota.is_file():
        count, period = quota.read_text().split()
        if count != "max":
            cpus = min(cpus, max(1, int(count) // int(period)))
    memory = next(
        int(line.split()[1]) * 1024
        for line in Path("/proc/meminfo").read_text().splitlines()
        if line.startswith("MemTotal:")
    )
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        if Path(path).is_file():
            limit = Path(path).read_text().strip()
            if limit.isdigit():
                memory = min(memory, int(limit))
    devices = []
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,uuid,name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        devices = [
            dict(zip(("index", "uuid", "name", "memory_mb"), line.split(", ", 3), strict=True))
            for line in result.stdout.splitlines()
            if line.strip()
        ]
    except (OSError, subprocess.SubprocessError):
        pass
    # Keep a small worker reservation even on a large host. Operators can raise it.
    return {
        "cpus": min(cpus, 8),
        "memory_mb": max(128, min(int(memory * 0.7 / 1024**2), 16384)),
        "max_jobs": min(cpus, 2),
        "gpu_ids": [d["index"] for d in devices],
        "hardware": {"cpus": cpus, "memory_mb": memory // 1024**2, "gpus": devices},
        "inventory_schema": "simjecture-hardware/1",
    }


DISCOVER = r"""
import json,os,pathlib,pwd
account=pwd.getpwuid(os.geteuid())
print(json.dumps({'ok':True,'result':{'uid':os.geteuid(),'home':account.pw_dir,'user':account.pw_name}}))
"""

INSTALL_BACKEND = r"""
import json,os,shutil,subprocess,sys
r=json.load(sys.stdin);name='proot' if r['backend']=='proot-cooperative' else 'bwrap'
if not shutil.which(name):
 if os.geteuid()!=0 or not shutil.which('apt-get'):
  raise ValueError('Install '+name+' on this host, or use Prepare with agent')
 subprocess.run(['apt-get','update'],check=True,stdout=sys.stderr,stderr=sys.stderr)
 subprocess.run(['apt-get','install','-y','proot' if name=='proot' else 'bubblewrap'],
                check=True,stdout=sys.stderr,stderr=sys.stderr)
print(json.dumps({'ok':True,'result':True}))
"""

MAINTENANCE = r"""
import json,os,signal,subprocess,sys,tempfile,time
r=json.load(sys.stdin)
with tempfile.TemporaryFile() as out,tempfile.TemporaryFile() as err:
 child=subprocess.Popen(r['command'],shell=True,executable='/bin/bash',stdout=out,stderr=err,start_new_session=True)
 timed_out=False
 try: code=child.wait(timeout=r['timeout'])
 except subprocess.TimeoutExpired:
  timed_out=True
  try:os.killpg(child.pid,signal.SIGTERM)
  except ProcessLookupError:pass
  try:code=child.wait(timeout=3)
  except subprocess.TimeoutExpired:
   try:os.killpg(child.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   code=child.wait()
 result={'returncode':code,'timed_out':timed_out}
 for name,stream in [('stdout',out),('stderr',err)]:
  size=stream.tell();stream.seek(max(0,size-24000))
  result[name]=stream.read().decode(errors='replace');result[name+'_truncated']=size>24000
print(json.dumps({'ok':True,'result':result}))
"""
