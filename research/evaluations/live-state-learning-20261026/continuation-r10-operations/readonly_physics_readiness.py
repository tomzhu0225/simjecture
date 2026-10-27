"""Retry only a read-only SSH executable check before assigning a workflow."""
import shlex
import subprocess
import time
from pathlib import Path

HARD_ERRORS = (
    'REMOTE HOST IDENTIFICATION HAS CHANGED', 'Host key verification failed',
    'Permission denied', 'Bad owner or permissions', 'UNPROTECTED PRIVATE KEY FILE',
    'no such identity', 'Bad configuration option',
)


def wait_for_ready(command, *, stop_by, on_attempt, maximum_attempts=6,
                   run=None, clock=None, sleep=None):
    run, clock, sleep = run or subprocess.run, clock or time.time, sleep or time.sleep
    parts = shlex.split(command[-1])
    if Path(command[0]).name != 'ssh' or len(parts) != 3 or parts[:2] != ['test', '-x']:
        raise ValueError('Only a read-only SSH test -x may be retried')
    deadline = min(stop_by, clock() + 180)
    attempts = []
    for index in range(maximum_attempts):
        remaining = deadline - clock()
        if remaining <= 0:
            break
        record = dict(attempt=index + 1, started_at=clock())
        try:
            result = run(command, capture_output=True, text=True, timeout=min(55, remaining))
            record.update(returncode=result.returncode, stderr_tail=result.stderr[-2048:],
                          stdout_tail=result.stdout[-256:])
        except subprocess.TimeoutExpired as error:
            detail = error.stderr or b''
            if isinstance(detail, bytes):
                detail = detail.decode(errors='replace')
            record.update(returncode=None, timeout=True, stderr_tail=detail[-2048:])
        record['ended_at'] = clock()
        attempts.append(record)
        on_attempt(record)
        if record['returncode'] == 0:
            return dict(ready=True, reason='read_only_check_passed', attempts=attempts)
        if record['returncode'] not in (None, 255) or any(
            marker.lower() in record['stderr_tail'].lower() for marker in HARD_ERRORS
        ):
            return dict(ready=False, reason='nonretryable_readiness_failure', attempts=attempts)
        if index + 1 < maximum_attempts:
            remaining = deadline - clock()
            if remaining > 0:
                sleep(min(5, remaining))
    return dict(ready=False, reason='bounded_readiness_attempts_exhausted', attempts=attempts)
