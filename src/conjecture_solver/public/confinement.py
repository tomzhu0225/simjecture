"""Linux filesystem and syscall confinement, independent of namespaces.

The executor also uses a dedicated UID for each concurrent job. Landlock is a
filesystem boundary, not a network namespace. Never silently skip enforcement.
"""

import ctypes
import errno
import os
from pathlib import Path


class Ruleset(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class PathRule(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


def landlock_abi():
    libc = ctypes.CDLL(None, use_errno=True)
    value = libc.syscall(444, 0, 0, 1)
    if value < 1:
        raise OSError(ctypes.get_errno(), "Landlock is required for hosted general execution")
    return value


def confine(work, read_only, devices=()):
    """Called by a single-threaded child AFTER dropping to its allocated UID."""
    abi = landlock_abi()
    libc = ctypes.CDLL(None, use_errno=True)
    rights = (1 << 13) - 1
    if abi >= 2:
        rights |= 1 << 13  # REFER
    if abi >= 3:
        rights |= 1 << 14  # TRUNCATE
    attributes = Ruleset(rights)
    descriptor = libc.syscall(444, ctypes.byref(attributes), ctypes.sizeof(attributes), 0)
    if descriptor < 0:
        raise OSError(ctypes.get_errno(), "Unable to construct filesystem policy")
    try:
        paths = [(str(work), rights & ~((1 << 6) | (1 << 11)))]
        # MPI/CUDA use POSIX shared memory. Distinct job UIDs and umask 077
        # isolate these objects; the broker removes its UID's objects on exit.
        if Path("/dev/shm").exists():
            paths.append(("/dev/shm", rights & ~((1 << 6) | (1 << 11))))
        paths += [(str(path), 1 | 4 | 8) for path in read_only]
        # NVIDIA names its own threads via /proc/<pid>/task/<tid>/comm.
        # Separate job UIDs enforce ownership here; no process-memory syscalls
        # or privileged kernel files become available to this UID.
        paths.append(("/proc", 2 | 4 | 8))
        # CUDA enumerates device names. Grant listing without read access to
        # unrelated device nodes; leaf device permissions remain explicit.
        paths.append(("/dev", 8))
        paths += [(str(path), 2 | 4) for path in devices]
        for name, access in paths:
            path = Path(name)
            if not path.exists():
                continue
            if not path.is_dir():
                access &= 1 | 2 | 4 | (1 << 14)
            fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = PathRule(access & rights, fd)
                if libc.syscall(445, descriptor, 1, ctypes.byref(rule), 0):
                    raise OSError(ctypes.get_errno(), "Unable to grant filesystem path: " + name)
            finally:
                os.close(fd)
        if libc.prctl(38, 1, 0, 0, 0) or libc.syscall(446, descriptor, 0):
            raise OSError(ctypes.get_errno(), "Unable to enforce filesystem policy")
    finally:
        os.close(descriptor)
    syscall_policy()


def syscall_policy():
    seccomp = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    seccomp.seccomp_init.argtypes = [ctypes.c_uint32]
    seccomp.seccomp_init.restype = ctypes.c_void_p
    seccomp.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    seccomp.seccomp_rule_add.argtypes = [
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_uint,
    ]
    seccomp.seccomp_load.argtypes = [ctypes.c_void_p]
    seccomp.seccomp_release.argtypes = [ctypes.c_void_p]
    context = seccomp.seccomp_init(0x7FFF0000)  # ALLOW
    if not context:
        raise OSError("Unable to initialize syscall policy")
    try:
        for name in (
            "ptrace",
            "process_vm_readv",
            "process_vm_writev",
            "pidfd_getfd",
            "kcmp",
            "mount",
            "umount2",
            "pivot_root",
            "chroot",
            "setns",
            "bpf",
            "keyctl",
            "perf_event_open",
            "userfaultfd",
            "reboot",
            "open_by_handle_at",
        ):
            number = seccomp.seccomp_syscall_resolve_name(name.encode())
            if number >= 0 and seccomp.seccomp_rule_add(
                context, 0x00050000 | errno.EPERM, number, 0
            ):
                raise OSError("Unable to deny syscall " + name)
        if seccomp.seccomp_load(context):
            raise OSError("Unable to enforce syscall policy")
    finally:
        seccomp.seccomp_release(context)
