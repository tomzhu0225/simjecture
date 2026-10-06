"""A tenant-scoped adapter for the normal workspace's presentation contract."""

import base64
import json
import math
import os
import tempfile
from pathlib import Path

from ..research_service import ResearchService, sha
from .native import OUTPUTS, registry
from .store import TERMINAL


class HostedWorkspace:
    def __init__(self, store, settings, login):
        self.store, self.settings, self.login = store, settings, login

    def provider(self):
        p = self.store.root / "provider.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def agent(self):
        return {
            "backend": "builtin",
            "model": self.provider().get("model", ""),
            "reasoning_effort": "",
        }

    def limits(self, owner):
        p = self.settings()
        if self.is_owner(owner):
            return {"interactive": None, "research": None}
        member = bool(self.store.account(owner))
        return {
            "interactive": p.get(
                "member_interactive" if member else "guest_interactive", 20 if member else 5
            ),
            "research": p.get(
                "member_research" if member else "guest_research", 2 if member else 1
            ),
        }

    def is_owner(self, owner):
        account = self.store.account(owner)
        return bool(
            account
            and str(account["github_id"])
            in {str(value) for value in self.settings().get("owner_github_ids", [])}
        )

    def hosting(self, owner):
        quota = self.store.quota(owner, self.limits(owner))
        quota.pop("key")
        if self.is_owner(owner):
            quota["tier"] = "owner"
        return {
            "account": self.store.account(owner),
            "quota": quota,
            "login_available": self.login.ready(),
            "wall_seconds": None
            if self.is_owner(owner)
            else self.settings().get("wall_seconds", 600),
            "permissions": {
                "change_model": False,
                "install_tools": False,
                "manage_machines": False,
                "upload_files": bool(self.store.account(owner)),
                "general_execution": bool(self.settings().get("executor_qualified")),
                "native_commands": False,
            },
        }

    def require_project(self, identifier, owner):
        project = self.store.project(identifier, owner)
        if not project:
            raise LookupError("Project not found")
        return project

    def require_job(self, identifier, owner):
        job = self.store.job(identifier, owner=owner)
        if not job:
            raise LookupError("Study not found")
        return job

    def service(self, job):
        root = self.store.root / "jobs" / job["id"] / "study"
        return ResearchService(root) if (root / "research.json").exists() else None

    def simulations(self, job):
        service = self.service(job)
        if not service:
            return []
        rows = []
        for record in service._all("experiments"):
            workspace = service.root / "experiments" / record["id"] / "workspace"
            files = []
            for name in record.get("artifacts", {}):
                if (name in OUTPUTS or name.startswith("generated/")) and (
                    workspace / name
                ).is_file():
                    files.append(
                        {"name": name, "size": (workspace / name).stat().st_size, "role": "output"}
                    )
            result = {}
            request = {}
            general_command = (workspace / "lab-request.json").is_file()
            for filename in ("lab-request.json", "native-case.json"):
                if (workspace / filename).is_file():
                    request = json.loads((workspace / filename).read_text())
                    break
            meta = record.get("artifacts", {}).get("result.json")
            if meta and sha(workspace / "result.json") == meta["sha256"]:
                value = json.loads((workspace / "result.json").read_text())
                result = (
                    value
                    if "tool" in value
                    else {
                        "moments_match": value["moments_match"],
                        "cases": [
                            {
                                k: value[name][k]
                                for k in (
                                    "distribution",
                                    "effective_growth_rate",
                                    "classification",
                                    "relative_energy_drift",
                                )
                            }
                            for name in ("maxwellian", "two_stream")
                        ],
                    }
                )
            rows.append(
                {
                    "id": job["id"] + "." + record["id"],
                    "kind": request.get("kind")
                    if request.get("kind") in ("command", "simulation")
                    else "command"
                    if general_command or result.get("tool") == "project-command"
                    else "simulation",
                    "name": result.get("name", request.get("name", "Numerical experiment")),
                    "status": record["status"],
                    "live": record["status"] in {"queued", "running"},
                    "created_at": record.get("created_at"),
                    "elapsed_seconds": record.get("execution", {}).get("wall_seconds", 0),
                    "output": json.dumps(result, indent=2)
                    if result
                    else record.get("execution", {}).get("stderr", ""),
                    "files": files,
                    "command": request.get(
                        "command", result.get("tool", "Installed numerical tool")
                    ),
                    "work_directory": "Recorded experiment workspace",
                    "file_provenance": "verified",
                    "inputs": [],
                    "native": False,
                }
            )
        return rows

    def project(self, identifier, owner):
        p = self.require_project(identifier, owner)
        studies = [
            {
                "campaign": j["id"],
                "campaign_id": j["id"][:12],
                "question": j["hypothesis"],
                "path": "Private recorded study",
                "explain_on_finish": False,
                "report_turn": next(
                    (
                        m["id"]
                        for m in p["messages"]
                        if m["job"] == j["id"] and m["role"] == "assistant"
                    ),
                    None,
                ),
            }
            for j in p["jobs"]
            if j["mode"] == "research"
        ]
        messages = [
            {
                "role": m["role"],
                "turn": m["id"],
                "text": m["content"],
                "content": m["content"],
                "agent": self.agent(),
                "steps": [],
                "files": [],
            }
            for m in p["messages"]
        ]
        running = next((j for j in p["jobs"] if j["status"] in {"queued", "running"}), None)
        if running:
            events = self.store.events(running["id"])
            labels = {
                "thinking": "Agent working",
                "experiment_started": "Simulation running",
                "experiment_finished": "Simulation completed",
                "review": "Independent review",
                "usage": "Model response received",
                "brief_prepared": "Study brief prepared",
                "provider_error": "Reconnecting to the model",
            }
            recent = [
                {
                    "label": (
                        "Command running"
                        if e["kind"] == "experiment_started"
                        else "Command completed"
                    )
                    if e.get("execution_kind") == "command"
                    and e["kind"] in ("experiment_started", "experiment_finished")
                    else labels[e["kind"]],
                    "status": "recorded",
                    "detail": e.get("message", ""),
                }
                for e in events
                if e["kind"] in labels
            ]
            messages.append(
                {
                    "role": "assistant",
                    "turn": "job-" + running["id"],
                    "content": "",
                    "agent": self.agent(),
                    "running": True,
                    "started_at": running["started"] or running["created"],
                    "last_activity_at": events[-1]["created"] if events else running["created"],
                    "monitored_runs": len(self.simulations(running)),
                    "activity": {
                        "label": recent[-1]["label"] if recent else "Waiting in queue",
                        "detail": "Your task continues if you close this page."
                        if self.store.account(owner)
                        else "Sign in to keep this investigation after leaving the site.",
                        "recent_actions": recent[-5:],
                    },
                }
            )
        return {
            "id": p["id"],
            "name": p["name"],
            "created_at": p["created"],
            "agent": self.agent(),
            "messages": messages,
            "studies": studies,
            "brief": p["brief"],
            "brief_launched": bool(p["brief_launched"]),
            "running": bool(running),
            "activity": running["status"] if running else "",
            "files": self.project_files(p["id"]),
            "files_directory": "Private hosted project files",
            "simulations": [r for j in p["jobs"] for r in self.simulations(j)],
            "hosting": self.hosting(owner),
        }

    def files_root(self, identifier):
        root = self.store.root / "projects" / identifier / "files"
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        return root

    def project_files(self, identifier):
        root = self.store.root / "projects" / identifier / "files"
        return [
            {"name": str(p.relative_to(root)), "size": p.stat().st_size}
            for p in sorted(root.rglob("*"))
            if p.is_file() and not p.is_symlink()
        ]

    def project_file(self, identifier, name, owner):
        from .lab_broker import safe_name

        self.require_project(identifier, owner)
        root = self.store.root / "projects" / identifier / "files"
        path = root / safe_name(name)
        if (
            not path.resolve().is_relative_to(root.resolve())
            or path.is_symlink()
            or not path.is_file()
        ):
            raise LookupError("Project file not found")
        return path

    def bootstrap(self, owner, csrf):
        projects = self.store.projects(owner)
        if not projects:
            legacy = [j for j in self.store.jobs(owner) if not j.get("project")]
            if legacy:
                p = self.store.create_project(owner, "Earlier investigations")
                with self.store.connect(write=True) as db:
                    for j in legacy:
                        db.execute("UPDATE jobs SET project=? WHERE id=?", (p["id"], j["id"]))
                for j in legacy:
                    j["project"] = p["id"]
                    if j["status"] in TERMINAL:
                        self.store.finish_project_job(j, j["summary"])
                projects = self.store.projects(owner)
        return {
            "control_token": csrf,
            "allow_mutations": True,
            "hosting": self.hosting(owner),
            "settings": {
                "default_agent": self.agent(),
                "api_configured": True,
                "has_key": True,
                "runtime_installed": True,
                "machine": "Simjecture hosted compute",
                "platform": "Managed",
                "clis": [],
                "execution": {"backend": "trusted-template", "available": True},
            },
            "projects": [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "running": any(j["status"] in {"queued", "running"} for j in p["jobs"]),
                    "agent": self.agent(),
                }
                for p in projects
            ],
        }

    def tools(self):
        tools = []
        entries = registry(self.store.root)
        general = bool(self.settings().get("executor_qualified"))
        descriptions = {
            "flash": "Hydrodynamics and MHD. Change inputs or build custom applications "
            "from installed read-only FLASH source.",
            "warpx": "GPU particle-in-cell simulations. Prepare custom input files and "
            "analyze fields and particles with Python.",
            "iter": "Fusion data and synthetic diagnostics with IMAS, Raysect and CHERAB. "
            "Prepare custom Python studies.",
        }
        for family, identifier, name in (
            ("flash", "flash", "FLASH 4.8"),
            ("warpx", "warpx-cuda", "WarpX · CUDA"),
            ("iter", "iter-pack", "ITER pack"),
        ):
            rows = [entry for entry in entries if entry["family"] == family]
            if not rows:
                continue
            description = descriptions[family]
            if family == "warpx" and any(
                r.get("features", {}).get("collisional_photons_qualified") for r in rows
            ):
                description = (
                    "GPU particle-in-cell with verified bremsstrahlung photon emission and "
                    "absorption. Prepare custom inputs and Python diagnostics."
                )
            tools.append(
                {
                    "id": identifier,
                    "name": name,
                    "installed": True,
                    "registered": True,
                    "readiness": "passed",
                    "action": "hosted",
                    "general_execution": general,
                    "path": "hosted-tools",
                    "description": description
                    if general
                    else " · ".join(row["name"] for row in rows),
                    "variants": [
                        {
                            "label": row["name"],
                            "path": "hosted-tools",
                            "description": row["scope"],
                            "tool_id": row["id"],
                        }
                        for row in rows
                    ],
                    "report": {
                        "checks": [
                            {"status": "pass", "detail": row["qualification"]} for row in rows
                        ]
                    },
                }
            )
        return tools

    def enqueue(self, owner, mode, text, project, action=None):
        p = self.require_project(project, owner)
        if any(j["status"] in {"queued", "running"} for j in p["jobs"]):
            raise ValueError("Wait for your current task or stop it first")
        settings = self.settings()
        owner_tier = self.is_owner(owner)
        requested = (
            math.ceil(
                (p.get("brief") or {}).get(
                    "hours", 0 if owner_tier else settings.get("wall_seconds", 600) / 3600
                )
                * 3600
            )
            if mode == "research"
            else 0
            if owner_tier
            else 180
        )
        return self.store.enqueue(
            owner,
            mode,
            text,
            project=project,
            action=action,
            limits=self.limits(owner),
            max_queue=settings.get("max_queue", 20),
            wall_seconds=requested
            if owner_tier
            else min(settings.get("wall_seconds", 600), requested),
            privileged=owner_tier,
            study_brief=p.get("brief") if mode == "research" else None,
        )

    def brief(self, p, values):
        question = str(
            values.get("question")
            or ("Formulate and test a scientific hypothesis using recorded numerical evidence.")
        ).strip()
        if not 16 <= len(question) <= 4000:
            raise ValueError("Question must be 16–4000 characters")
        owner = self.is_owner(p["owner"])
        hours = values.get("hours", 0 if owner else self.settings().get("wall_seconds", 600) / 3600)
        if (
            isinstance(hours, bool)
            or not isinstance(hours, (int, float))
            or not math.isfinite(hours)
            or not math.isfinite(hours * 3600)
            or hours * 3600 >= 2**63
            or hours < 0
            or (hours == 0 and not owner)
        ):
            raise ValueError("Choose a positive time budget")
        if not owner and hours * 3600 > self.settings().get("wall_seconds", 600) + 0.001:
            raise ValueError("Hosted research currently allows up to 10 minutes")
        for key in ("success_criteria", "constraints"):
            if not isinstance(values.get(key, ""), str) or len(values.get(key, "")) > 4000:
                raise ValueError("Brief text is too long")
        if values.get("capability_directory") not in (
            None,
            "",
            "hosted-pic",
            "hosted-tools",
        ) or values.get("machine_ids"):
            raise PermissionError("Compute and tools are provided by the host")
        brief = {
            "question": question,
            "success_criteria": values.get(
                "success_criteria",
                "Recorded evidence, numerical validity checks and independent review.",
            ),
            "constraints": values.get("constraints", ""),
            "hours": hours,
            "completion_policy": "answer",
            "capability_directory": "hosted-tools",
            "machine_ids": [],
        }
        self.store.save_brief(p["id"], brief)
        return brief

    def get(self, name, query, owner, csrf):
        identifier = query.get("id", "")
        if name == "bootstrap":
            return self.bootstrap(owner, csrf)
        if name == "project":
            return self.project(identifier, owner)
        if name == "tools":
            return self.tools()
        if name == "benchmarks":
            from ..llm_bench.leaderboard import public_grade, published_reports, summarize
            from ..llm_bench.official import dashboard
            from ..llm_bench.pack import catalogue

            pack = catalogue()
            reports = [r for r in published_reports() if r.get("pack_version") == pack["version"]]
            return pack | {
                "official": dashboard(),
                "leaderboard": summarize(reports),
                "local_leaderboard": summarize([]),
                "grade_reports": [public_grade(r) for r in reports],
                "published_trials": len(reports),
                "community_trials": 0,
                "imported_trials": 0,
                "projects": [],
                "campaigns": [],
            }
        if name == "machines":
            return {"machines": [], "local_defaults": {}, "enabled": False}
        if name == "simulation":
            p = self.project(identifier, owner)
            row = next((r for r in p["simulations"] if r["id"] == query.get("simulation")), None)
            if not row:
                raise LookupError("Simulation not found")
            return row
        if name == "study":
            return self.study(identifier, owner)
        raise PermissionError("This operation is managed by the host")

    def post(self, name, values, owner):
        if name == "delete-project":
            from .deletion import ProjectDeletion

            if set(values) != {"project", "confirm"} or values["confirm"] != values["project"]:
                raise ValueError("Confirm the conversation identifier before deletion")
            self.require_project(values["project"], owner)
            return ProjectDeletion(self.store).request(values["project"], owner)
        if name == "upload":
            if not self.store.account(owner):
                raise PermissionError("Sign in to add files")
            if set(values) != {"project", "name", "data"}:
                raise ValueError("Invalid upload fields")
            p = self.require_project(values["project"], owner)
            from .lab_broker import safe_name

            name = safe_name(values["name"])
            if len(name.parts) != 1:
                raise ValueError("Upload a filename, not a directory path")
            if not isinstance(values["data"], str) or len(values["data"]) > 90 * 1024**2:
                raise ValueError("File exceeds the upload allowance")
            content = base64.b64decode(values["data"], validate=True)
            if len(content) > 64 * 1024**2:
                raise ValueError("File exceeds 64 MiB")
            with self.store.connect(write=True) as db:
                if not db.execute(
                    "SELECT id FROM projects WHERE id=? AND deleting=0 AND "
                    + self.store.owner_clause(),
                    (p["id"], owner, owner),
                ).fetchone():
                    raise LookupError("Conversation not found")
                root = self.files_root(p["id"])
                path = root / name
                if path.is_symlink():
                    raise ValueError("Invalid file target")
                existing = path.stat().st_size if path.is_file() else 0
                if (
                    sum(f["size"] for f in self.project_files(p["id"])) - existing + len(content)
                    > 512 * 1024**2
                ):
                    raise ValueError("Project file storage allowance reached")
                fd, temporary = tempfile.mkstemp(prefix=".executor-upload-", dir=root)
                try:
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(content)
                    os.replace(temporary, path)
                finally:
                    Path(temporary).unlink(missing_ok=True)
            return {"name": str(name), "size": len(content), "sha256": sha(path)}
        if name == "tool-demo":
            if set(values) != {"name"}:
                raise ValueError("Choose an installed example")
            entry = next((r for r in registry(self.store.root) if r["id"] == values["name"]), None)
            if not entry:
                raise ValueError("This native example is not qualified")
            p = self.store.create_project(owner, entry["name"])
            job = self.enqueue(
                owner,
                "reproduce",
                "Run the qualified " + entry["name"] + " example.",
                p["id"],
                action="native:" + entry["id"],
            )
            return {"project": p["id"], "job": job["id"]}
        if name == "models":
            if values.get("backend", "builtin") != "builtin":
                raise PermissionError("The agent is assigned by the host")
            return {
                "models": [{"id": self.agent()["model"], "name": self.agent()["model"]}],
                "default": self.agent()["model"],
                "note": "Provided by Simjecture · model settings managed by the host",
            }
        if name == "agent":
            if any(values.get(k, v) != v for k, v in self.agent().items()):
                raise PermissionError("Model settings are managed by the host")
            return self.agent()
        if name == "projects":
            if set(values) - {"name", "agent"}:
                raise ValueError("Unsupported project field")
            name = values.get("name", "New investigation")
            if not isinstance(name, str) or not 1 <= len(name) <= 100:
                raise ValueError("Choose a short project name")
            p = self.store.create_project(owner, name)
            return self.project(p["id"], owner)
        allowed = {
            "message": {"project", "message"},
            "stop": {"project"},
            "prepare": {"project", "approach"},
            "brief": {
                "project",
                "question",
                "success_criteria",
                "constraints",
                "hours",
                "completion_policy",
                "capability_directory",
                "machine_ids",
            },
            "launch": {
                "project",
                "request_key",
                "capability_directory",
                "execution_backend",
                "director_enabled",
                "judge_model",
                "judge_reasoning_effort",
            },
            "new-study": {"project"},
            "explain-study": {"project", "campaign"},
            "stop-simulation": {"project", "simulation"},
        }
        if name not in allowed:
            raise PermissionError("This operation is managed by the host")
        if set(values) - allowed[name]:
            raise ValueError("Unsupported operation field")
        p = self.require_project(values.get("project"), owner)
        if name == "message":
            message = values.get("message", "")
            if not isinstance(message, str) or not 1 <= len(message) <= 4000:
                raise ValueError("Message must be 1–4000 characters")
            j = self.enqueue(owner, "interactive", message, p["id"])
            return {"id": j["id"], "message": "Your agent is queued"}
        if name == "brief":
            return self.brief(p, values)
        if name == "prepare":
            approach = values.get("approach")
            if approach not in {"draft", "interview"}:
                raise ValueError("Choose draft or interview")
            message = (
                "Prepare an autonomous study from this conversation."
                if approach == "draft"
                else "Ask me the missing questions needed to prepare an autonomous study."
            )
            j = self.enqueue(owner, "interactive", message, p["id"], action=approach)
            return {"id": j["id"]}
        if name == "new-study":
            self.store.save_brief(p["id"], None)
            return {"message": "Ready to prepare another study"}
        if name == "launch":
            if values.get("capability_directory") not in (
                None,
                "",
                "hosted-pic",
                "hosted-tools",
            ) or values.get("execution_backend") not in (None, "", "trusted-template"):
                raise PermissionError("Execution is provided by the host")
            if values.get("judge_model") not in (
                None,
                "",
                self.provider().get("reviewer_model"),
            ) or values.get("judge_reasoning_effort"):
                raise PermissionError("Reviewer settings are managed by the host")
            if not p["brief"]:
                raise ValueError("Prepare a study brief first")
            # Idempotent launch: repeat clicks return this already launched draft.
            if p["brief_launched"]:
                prior = [j for j in p["jobs"] if j["mode"] == "research"]
                if prior:
                    return {"campaign": prior[-1]["id"]}
            j = self.enqueue(owner, "research", p["brief"]["question"], p["id"])
            with self.store.connect(write=True) as db:
                db.execute("UPDATE projects SET brief_launched=1 WHERE id=?", (p["id"],))
            return {"campaign": j["id"]}
        if name == "explain-study":
            j = self.require_job(values.get("campaign"), owner)
            if j["project"] != p["id"]:
                raise LookupError("Study not found in this project")
            self.enqueue(
                owner, "interactive", "Explain the completed study and its limitations.", p["id"]
            )
            return {"message": "Explanation queued"}
        if name == "stop-simulation":
            identifier = values.get("simulation", "")
            if not isinstance(identifier, str) or "." not in identifier:
                raise LookupError("Simulation not found")
            job_id, experiment = identifier.split(".", 1)
            job = self.require_job(job_id, owner)
            if job["project"] != p["id"]:
                raise LookupError("Simulation not found in this project")
            service = self.service(job)
            if not service or experiment not in {r["id"] for r in service._all("experiments")}:
                raise LookupError("Simulation not found")
            service.cancel(experiment, reason="Stopped by the owner of this investigation")
            return {"message": "Experiment stop requested; the agent can continue its task"}
        if name == "stop":
            for j in p["jobs"]:
                if j["status"] in {"queued", "running"}:
                    self.store.cancel(j["id"], owner)
            return {"message": "Stop requested; recorded evidence remains available"}
        raise PermissionError("Operation unavailable")

    def projection(self, job):
        from ..web.application import SimjectureWebApplication

        service = self.service(job)
        if not service:
            return None
        app = SimjectureWebApplication(
            initial_run=service.root,
            scan_roots=(service.root / ".no-discovery",),
            runs_root=service.root / ".public-view",
            allow_mutations=False,
        )
        snapshot = app.campaign_snapshot(app.initial_campaign)
        if job.get("project"):
            project = self.store.project(job["project"])
            snapshot["workspace_context"] = {
                "project_id": project["id"],
                "project_name": project["name"],
            }
        return snapshot

    def campaigns(self, owner):
        return [
            {
                "id": j["id"],
                "display_name": j["hypothesis"][:120],
                "hypothesis": j["hypothesis"],
                "execution_status": j["status"],
                "campaign_id": j["id"][:12],
                "path": "Private recorded study",
            }
            for j in self.store.jobs(owner)
            if j["mode"] == "research"
        ]

    def study(self, identifier, owner):
        import time

        j = self.require_job(identifier, owner)
        service = self.service(j)
        snapshot = self.projection(j) or {"snapshot": {}, "executions": [], "artifacts": []}
        snapshot["controls"] = {
            "can_pause": False,
            "can_resume": False,
            "can_cancel": j["status"] not in TERMINAL,
        }
        return {
            "snapshot": snapshot,
            "report": {
                "status": j["status"],
                "experiments": service._all("experiments") if service else [],
                "reviews": service._all("reviews") if service else [],
            },
            "live": {
                "status": j["status"],
                "mode": "hosted",
                "usage": j["usage"],
                "remaining": max(0, j["deadline"] - time.time()) if j["deadline"] else None,
                "activity": j["summary"][:300],
            },
            "results": j["summary"],
        }

    def artifact(self, identifier, relative, owner):
        j = self.require_job(identifier, owner)
        service = self.service(j)
        if not service:
            raise LookupError("Artifact not found")
        parts = Path(relative).parts
        if (
            len(parts) >= 4
            and parts[0] == "experiments"
            and parts[2] == "workspace"
            and (parts[3] in OUTPUTS and len(parts) == 4 or parts[3] == "generated")
        ):
            record = service._read("experiments", parts[1])
            if ".." in parts or Path(relative).is_absolute():
                raise LookupError("Artifact not found")
            meta = record.get("artifacts", {}).get("/".join(parts[3:]))
            path = service.root / relative
            if meta and path.is_file() and not path.is_symlink() and sha(path) == meta["sha256"]:
                return path
        if relative in {
            "STUDY_LEDGER.md",
            "RESULTS_INDEX.md",
            "research_report.json",
            "TRANSCRIPT.md",
        }:
            path = service.root / relative
            if path.is_file() and not path.is_symlink():
                return path
        raise LookupError("Verified artifact not found")
