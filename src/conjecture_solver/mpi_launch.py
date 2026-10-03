"""Dependency-free single-node Open MPI launcher using an explicit CPU reservation.

This file is also mounted as a standalone helper inside numerical runtimes.
No SSH or other hosts are launched by this helper. A CPU slot is an allocated
logical CPU, not an assertion about physical-core topology or solver scaling.
"""

from __future__ import annotations

import argparse
import os


def mpi_command(ranks, executable, args=(), *, launcher="/usr/bin/orterun", slots=None):
    if type(ranks) is not int or ranks < 1:
        raise ValueError("MPI ranks must be a positive integer")
    reserved = os.environ.get("SIMJECTURE_CPU_SLOTS")
    if reserved is not None:
        try:
            allocated = int(reserved)
        except ValueError as error:
            raise ValueError("SIMJECTURE_CPU_SLOTS must be a positive integer") from error
    else:
        allocated = (
            len(os.sched_getaffinity(0))
            if hasattr(os, "sched_getaffinity")
            else (os.cpu_count() or 1)
        )
    if allocated < 1:
        raise ValueError("The CPU reservation must contain at least one slot")
    if slots is None:
        slots = allocated
    if type(slots) is not int or not 1 <= slots <= allocated:
        raise ValueError(f"MPI slots must be within the allocated {allocated} CPU slots")
    if ranks > slots:
        raise ValueError(
            f"Requested {ranks} MPI ranks but this job has {slots} CPU slots. "
            f"Reserve resources={{'cpus': {ranks}, ...}} before launch; "
            "do not use --oversubscribe to bypass the reservation."
        )
    if not executable or not launcher:
        raise ValueError("Choose an MPI launcher and executable")
    return [
        launcher,
        "--host",
        f"localhost:{slots}",
        "--map-by",
        "slot",
        "--bind-to",
        "none",
        "--nooversubscribe",
        *(
            ["--mca", "mpi_yield_when_idle", "1"]
            if os.environ.get("SIMJECTURE_EXECUTION_BACKEND") == "proot-cooperative"
            else []
        ),
        "-n",
        str(ranks),
        executable,
        *args,
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ranks", required=True, type=int)
    parser.add_argument("--slots", type=int)
    parser.add_argument("--launcher", default="/usr/bin/orterun")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Supply an executable after --")
    try:
        argv = mpi_command(
            args.ranks, command[0], command[1:], launcher=args.launcher, slots=args.slots
        )
    except ValueError as error:
        parser.error(str(error))
    os.execvpe(argv[0], argv, os.environ)


if __name__ == "__main__":
    main()
