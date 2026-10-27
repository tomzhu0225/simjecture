"""One bounded control check; scheduled only until the existing R11 lease ends."""
from pathlib import Path
import json
import os
import shlex
import subprocess
import time

from remote_transport import DIAL

ROOT = Path(__file__).parent
LEASE = json.loads((ROOT / "r11-lease.json").read_text())
PYTHON = "/home/tomzhu0225/.local/share/uv/tools/google-colab-cli/bin/python"
STATUS = dict(started_at=time.time(), pid=os.getpid(), endpoint=LEASE["endpoint"])


def save():
    path = ROOT / "r11-control-once-status.tmp"
    path.write_text(json.dumps(STATUS, indent=2))
    path.replace(ROOT / "r11-control-once-status.json")


def released(evidence):
    record = dict(endpoint=LEASE["endpoint"], released=True, at=time.time(), evidence=evidence)
    (ROOT / "r11-verified-released.json").write_text(json.dumps(record, indent=2))
    STATUS.update(stage="released", evidence=evidence)
    # Only the temporary task created for this exact bounded lease is removed.
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command",
         "$ErrorActionPreference='Stop'; $task=Get-ScheduledTask -TaskName Simjecture-R11-20261027 -ErrorAction SilentlyContinue; if ($task) { Unregister-ScheduledTask -TaskName Simjecture-R11-20261027 -Confirm:$false }; exit 0"],
        capture_output=True, timeout=20,
    )
    STATUS["task_cleanup_returncode"] = result.returncode


try:
    save()
    if time.time() < LEASE["stop_by"]:
        query = (
            "from pathlib import Path;import json;"
            "r=Path('/home/simjecture/investigations/scientific-attention-20261025');"
            "print(json.dumps(dict(guard=json.loads((r/'r11-guard-status.json').read_text()),"
            "endpoint=json.loads((r/'r11-lease.json').read_text())['endpoint'])))"
        )
        probe = subprocess.run(
            DIAL + ["python3 -c " + shlex.quote(query)],
            capture_output=True, text=True, timeout=45,
        )
        remote = json.loads(probe.stdout) if probe.returncode == 0 else {}
        if remote.get("endpoint") == LEASE["endpoint"] and remote["guard"]["stage"] == "released":
            released("Matching remote guard release receipt")
        else:
            result = subprocess.run(
                [PYTHON, str(ROOT / "export_colab_access.py")],
                capture_output=True, timeout=120,
            )
            STATUS.update(stage="renewed" if result.returncode == 0 else "renewal_failed",
                          renewal_returncode=result.returncode,
                          remote_guard_stage=remote.get("guard", {}).get("stage"))
    else:
        # Deadline enforcement concerns only the endpoint in this immutable lease.
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request, AuthorizedSession
        from colab_cli.client import Client, Prod

        for key in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"]:
            os.environ[key] = "http://127.0.0.1:9682"

        class Session(AuthorizedSession):
            def request(self, *args, **kwargs):
                kwargs.setdefault("timeout", 30)
                return super().request(*args, **kwargs)

        scopes = ["openid", "https://www.googleapis.com/auth/userinfo.email",
                  "https://www.googleapis.com/auth/userinfo.profile",
                  "https://www.googleapis.com/auth/colaboratory"]
        credentials = Credentials.from_authorized_user_info(
            json.loads((Path.home() / ".config/colab-cli/token.json").read_text()), scopes=scopes)
        credentials.refresh(Request())
        api = Client(Prod(), Session(credentials))
        if any(item.endpoint == LEASE["endpoint"] for item in api.list_assignments()):
            api.unassign(LEASE["endpoint"])
        if any(item.endpoint == LEASE["endpoint"] for item in api.list_assignments()):
            raise RuntimeError("Owned endpoint still assigned after release request")
        released("Owned endpoint absent after local account reconciliation")
except Exception as error:
    STATUS.update(stage="error", error_type=type(error).__name__)
finally:
    STATUS["ended_at"] = time.time()
    save()
print(json.dumps(STATUS), flush=True)
