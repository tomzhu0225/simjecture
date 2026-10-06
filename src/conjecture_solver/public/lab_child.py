"""Single-threaded, operator-owned privilege-drop entry point for the broker."""

import json
import math
import os
import resource
import sys
from pathlib import Path

from .confinement import confine


def main():
    policy = Path(sys.argv[1])
    config = json.loads(policy.read_text())
    policy.unlink()
    uid = config["uid"]
    if os.getuid() != 0 or not isinstance(uid, int) or uid < 60000:
        raise ValueError("The executor requires a dedicated unprivileged UID")
    os.setgroups([])
    os.setgid(uid)
    os.setuid(uid)
    os.umask(0o077)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[: config["cpus"]])
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))
    resource.setrlimit(resource.RLIMIT_NPROC, (128, 128))
    resource.setrlimit(resource.RLIMIT_FSIZE, (128 * 1024**2, 128 * 1024**2))
    seconds = math.ceil(config["timeout"] + 10)
    resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds))
    confine(config["work"], config["read_only"], config["devices"])
    os.execve("/bin/bash", ["bash", "--noprofile", "--norc"], config["environment"])


if __name__ == "__main__":
    main()
