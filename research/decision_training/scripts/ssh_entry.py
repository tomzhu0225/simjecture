"""WSL scientific-worker transport through the existing managed Windows SSH route."""

import json
import subprocess
import sys
from pathlib import Path, PureWindowsPath


def main():
    if len(sys.argv) < 3 or sys.argv[-2] not in {"cannlab-science", "cannlab-cpu"}:
        raise ValueError("This project-local transport is for the registered remote science worker")
    root = Path(__file__).resolve().parents[1]
    # Native experiment coordinators deliberately sanitize PYTHONPATH. Keep
    # this project-local helper importable in that subprocess environment.
    sys.path.insert(0, str(root))
    filename = "ssh-route.local.json" if sys.argv[-2] == "cannlab-science" else "ssh-cpu-route.local.json"
    command = json.loads((root / "config" / filename).read_bytes())
    executable = PureWindowsPath(command[0])
    if executable.drive:
        command[0] = "/mnt/" + executable.drive[0].lower() + "/" + "/".join(executable.parts[1:])
    if " -u -c " in sys.argv[-1]:
        result = subprocess.run(command + [sys.argv[-1]], check=False)
    else:
        from research_decision.managed_ssh import run_ssh

        result = run_ssh(command, [sys.argv[-1]], input=sys.stdin.buffer.read(), timeout=3600)
        sys.stdout.buffer.write(result.stdout)
        sys.stderr.buffer.write(result.stderr)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
