"""General hosted research tools around a separately confined executor service."""

import json
import shutil
import time
import uuid
from pathlib import Path

from ..research_journal import sync_journal
from ..research_service import put, sha
from .lab_broker import safe_name

PROGRAM = """import base64,hashlib,io,json,socket,sys,zipfile
from pathlib import Path

request=json.loads(Path("lab-request.json").read_text())
archive=io.BytesIO()
with zipfile.ZipFile(archive,"w",compression=zipfile.ZIP_DEFLATED) as z:
    for name in request["inputs"]:
        source=Path("payload")/name
        info=zipfile.ZipInfo(name)
        info.external_attr=(0o100000 | request["modes"][name])<<16
        info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,source.read_bytes())
message={"command":request["command"],"inputs":base64.b64encode(archive.getvalue()).decode(),
         "outputs":request["outputs"],"timeout":request["timeout"]}
with socket.socket(socket.AF_UNIX) as client:
    client.settimeout(request["timeout"]+45)
    client.connect(request["socket"])
    client.sendall(json.dumps(message).encode()+b"\\n")
    with client.makefile("rb") as stream:
        response=json.loads(stream.readline(256*1024**2))
if "error" in response: raise RuntimeError(response["error"])
data=base64.b64decode(response.pop("outputs"),validate=True)
Path("raw-output.zip").write_bytes(data)
files=[]
with zipfile.ZipFile(io.BytesIO(data)) as z:
    for entry in z.infolist():
        name=Path(entry.filename)
        if name.is_absolute() or ".." in name.parts or not name.parts:
            raise ValueError("Unsafe output")
        target=Path("generated")/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(z.read(entry))
        target.chmod(0o700 if entry.external_attr>>16 & 0o111 else 0o600)
        files.append({"name":str(target),"sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
                      "bytes":target.stat().st_size})
metrics={k:response[k] for k in ("returncode","stop_reason","seconds","stdout","stderr","missing")}
result={"tool":"project-command","name":request["name"],"kind":request["kind"],"parameters":{},
        "scope":"Agent-authored command and analysis; independent review is separate.",
        "metrics":metrics,"files":files,
        "confinement":{"uid":response["uid"],"landlock_abi":response["landlock_abi"],
                       "executor_revision":response.get("executor_revision")}}
Path("result.json").write_text(json.dumps(result,indent=2)+"\\n")
provenance={"command":request["command"],"kind":request["kind"],"inputs":request["inputs"],
            "outputs":request["outputs"],"runtime_index":request["runtime_index"],
            "confinement":result["confinement"]}
Path("provenance.json").write_text(json.dumps(provenance,indent=2)+"\\n")
print(json.dumps(result))
if metrics["returncode"] != 0 or metrics["stop_reason"] or metrics["missing"]: sys.exit(1)
"""


class HostedLab:
    def __init__(self, store, job, service):
        self.store, self.job, self.service = store, job, service
        self.settings = json.loads((store.root / "settings.json").read_text())
        self.files = store.root / "projects" / job["project"] / "files"
        self.files.mkdir(parents=True, exist_ok=True, mode=0o700)

    def path(self, name):
        path = self.files / safe_name(name)
        if not path.resolve().is_relative_to(self.files.resolve()) or path.is_symlink():
            raise ValueError("Use a project-relative file path")
        return path

    def write(self, name, content):
        if not isinstance(content, str) or len(content.encode()) > 128 * 1024:
            raise ValueError("Write at most 128 KiB of text per file")
        path = self.path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return {"path": name, "bytes": path.stat().st_size, "sha256": sha(path)}

    def read(self, name, start_line=1, lines=200):
        if not start_line >= 1 or not 1 <= lines <= 400:
            raise ValueError("Read a bounded line range")
        if Path(name).is_absolute():
            path = Path(name).resolve()
            roots = [Path(r).resolve() for r in self.settings.get("source_roots", [])]
            if not any(path.is_relative_to(r) for r in roots):
                raise PermissionError("Read only project files or installed scientific sources")
        else:
            path = self.path(name)
        if not path.is_file() or path.stat().st_size > 8 * 1024**2:
            raise ValueError("Use a numerical analysis command for large or binary files")
        content = path.read_text().splitlines()
        return {
            "path": name,
            "start_line": start_line,
            "total_lines": len(content),
            "text": "\n".join(content[start_line - 1 : start_line - 1 + lines])[:40000],
        }

    def run(
        self, command, outputs, inputs=None, timeout=120, name="Scientific command", kind="command"
    ):
        from .worker import check_running

        identifier = self.job["id"]
        check_running(self.store, identifier)
        if kind not in ("command", "simulation"):
            raise ValueError("Choose command or simulation as the execution kind")
        if not self.job.get("privileged") and len(
            self.service._all("experiments")
        ) >= self.settings.get("experiments_per_job", 6):
            return {"status": "simulation_allowance_reached", "remaining_experiments": 0}
        if not isinstance(command, str) or not 1 <= len(command) <= 12000:
            raise ValueError("Use a bounded command")
        if (
            not isinstance(timeout, (int, float))
            or isinstance(timeout, bool)
            or not 0 < timeout <= (86400 if self.job.get("privileged") else 180)
        ):
            raise ValueError("Choose a valid experiment timeout")
        if not isinstance(outputs, list) or len(outputs) > 64:
            raise ValueError("Declare output paths or glob patterns")
        for pattern in outputs:
            safe_name(pattern)
        names = (
            inputs
            if inputs is not None
            else [
                str(p.relative_to(self.files))
                for p in self.files.rglob("*")
                if p.is_file() and not p.is_symlink()
            ]
        )
        if not isinstance(names, list) or len(names) > 4096:
            raise ValueError("Use a bounded list of input files")
        for filename in names:
            source = self.path(filename)
            if not source.is_file():
                raise ValueError("Missing project input: " + filename)
            target = self.service.work / "payload" / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        from .native import registry

        remaining = (
            self.store.job(identifier)["deadline"] or (time.time() + timeout + 60)
        ) - time.time()
        timeout = min(timeout, max(0.1, remaining - 1))
        request = {
            "command": command,
            "inputs": names,
            "outputs": outputs,
            "modes": {n: 0o700 if self.path(n).stat().st_mode & 0o111 else 0o600 for n in names},
            "timeout": timeout,
            "name": name[:100],
            "kind": kind,
            "socket": self.settings["executor_socket"],
            "runtime_index": [
                {k: e.get(k) for k in ("id", "binary_sha256", "source_root")}
                for e in registry(self.store.root)
            ],
        }
        put(self.service.work / "lab-request.json", request)
        (self.service.work / "lab-execute.py").write_text(PROGRAM)
        record = self.service.run(
            "lab-execute.py",
            key="hosted-attempt-" + uuid.uuid4().hex,
            inputs=["lab-request.json", *("payload/" + n for n in names)],
            outputs=["result.json", "provenance.json", "raw-output.zip"],
            review_documents=["result.json", "provenance.json"],
            timeout=min(timeout + 45, remaining),
            purpose="comparison",
        )
        self.store.event(
            identifier,
            "experiment_started",
            {"experiment": record["id"], "name": name, "execution_kind": kind},
        )
        while record["status"] in {"running", "queued"}:
            check_running(self.store, identifier)
            time.sleep(0.3)
            record = self.service._read("experiments", record["id"])
        sync_journal(self.service)
        workspace = self.service.root / "experiments" / record["id"] / "workspace"
        if not (workspace / "result.json").exists():
            return {
                "experiment": record["id"],
                "status": record["status"],
                "error": record.get("error"),
                "execution": record.get("execution"),
            }
        result = json.loads((workspace / "result.json").read_text())
        for row in result["files"]:
            source = workspace / row["name"]
            if sha(source) != row["sha256"]:
                raise ValueError("Scientific output changed after recording")
            relative = str(Path(row["name"]).relative_to("generated"))
            target = self.path(relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        result["experiment"] = record["id"]
        result["workspace_note"] = (
            "Each command starts in a fresh scratch directory populated from project inputs. "
            "Only declared outputs return to the persistent project. Combine unpacking and "
            "analysis in one command, or declare extracted files as outputs to use them later."
        )
        result["status"] = (
            "succeeded"
            if result["metrics"]["returncode"] == 0
            and not result["metrics"]["stop_reason"]
            and not result["metrics"]["missing"]
            else "command_failed"
        )
        result["figures"] = [
            f"simulation:{identifier}.{record['id']}/{r['name']}"
            for r in result["files"]
            if r["name"].endswith(".png")
        ]
        self.store.event(
            identifier,
            "experiment_finished",
            {"experiment": record["id"], "status": result["status"], "execution_kind": kind},
        )
        return result


def agent_tools(store, job, service):
    from smolagents import tool

    if not job.get("project"):
        return []
    settings = json.loads((store.root / "settings.json").read_text())
    if not settings.get("executor_qualified") or not settings.get("executor_socket"):
        return []
    lab = HostedLab(store, job, service)

    @tool
    def write_file(path: str, content: str) -> str:
        """Write a project file: solver inputs, scripts, custom initial conditions or analysis.

        Args:
            path: Project-relative filename.
            content: UTF-8 text, at most 128 KiB.
        """
        return json.dumps(lab.write(path, content))

    @tool
    def read_file(path: str, start_line: int = 1, lines: int = 200) -> str:
        """Read project files or installed read-only solver sources and documentation.

        Args:
            path: Project-relative filename or an installed scientific source path.
            start_line: First line, starting at 1.
            lines: Up to 400 lines.
        """
        return json.dumps(lab.read(path, start_line, lines))

    @tool
    def run_command(
        command: str,
        outputs: list[str],
        inputs: list[str] | None = None,
        timeout: int = 120,
        name: str = "Scientific command",
        kind: str = "command",
    ) -> str:
        """Run custom scientific commands in an isolated job account with installed solvers.

        Each call uses fresh scratch space; only declared outputs persist between calls.
        Unpack and analyze an archive in the same command, or retain extracted files.
        Create output directories before saving files (for example mkdir -p generated).

        Args:
            command: Shell command; may run Python, installed solvers, compilers or analysis.
            outputs: Output files or glob patterns to retain. Use [] for inspection-only commands;
                stdout and stderr are always recorded. Named outputs must actually be written.
            inputs: Project input files; omit to include all current project files.
            timeout: Experiment time limit in seconds; guests up to 180, owners up to 86400.
            name: Short descriptive label for the GUI.
            kind: Use simulation for running a numerical solver or integrating a physical model.
                Use command for analysis, plots, compilation and inspection, even with outputs.
        """
        return json.dumps(lab.run(command, outputs, inputs, timeout, name, kind))

    return [write_file, read_file, run_command]
