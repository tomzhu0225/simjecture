"""Exercise reconnect semantics with fake subprocesses; no model/simulation."""

import json
import subprocess
from unittest.mock import patch

from research_decision import managed_ssh


def main():
    failed = subprocess.CompletedProcess([], 255, stdout=b"", stderr=b"ssh: connect to host 127.0.0.1 port 36485: Connection refused")
    success = subprocess.CompletedProcess([], 0, stdout=b'{"ok":true}', stderr=b"")
    with patch.object(managed_ssh.subprocess, "run", side_effect=[failed, success]) as execute, patch.object(
        managed_ssh, "restore_existing_forward", return_value=True
    ) as restore:
        result = managed_ssh.run_ssh(["pinned-ssh"], ["python3", "-"], input=b"same immutable request")
        assert result.returncode == 0 and execute.call_count == 2 and restore.call_count == 1
        assert all(call.kwargs["input"] == b"same immutable request" for call in execute.call_args_list)
    logical = subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"ValueError: scientific data mismatch")
    with patch.object(managed_ssh.subprocess, "run", return_value=logical) as execute, patch.object(
        managed_ssh, "restore_existing_forward"
    ) as restore:
        assert managed_ssh.run_ssh(["pinned-ssh"], ["python3"]).returncode == 1
        assert execute.call_count == 1 and restore.call_count == 0
    # Never append a restarted binary stream to existing archive bytes.
    with patch.object(managed_ssh.subprocess, "run", return_value=failed) as execute, patch.object(
        managed_ssh, "restore_existing_forward", return_value=True
    ):
        assert managed_ssh.run_ssh(["pinned-ssh"], ["python3"], stdout=object()).returncode == 255
        assert execute.call_count == 1
    print(json.dumps(dict(passed=3, model_calls=0, simulations=0)))


if __name__ == "__main__":
    main()
