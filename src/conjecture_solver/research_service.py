"""Experimental small evidence service for agent-owned investigations.

Native tools remain available. Recorded experiments use the existing numerical
sandbox. This local API assumes cooperative same-account agents, not hostile ones.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .mvp_agent import BubblewrapSandbox
from .mvp_skills import MVPCapabilityRegistry
from .research_control import ControlService, ExperimentMonitor
from .research_guidance import GuidedResearch
from .research_methods import MethodService
from .research_notebook import NotebookService
from .research_progress import ProgressService


class ResearchVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_id: str = Field(min_length=1, description="ID of the target claim being adjudicated")
    decision: Literal["approved", "needs_revision"]
    disposition: Literal["supported", "falsified", "unresolved"]
    rationale: str = Field(min_length=16)
    evidence_gaps: list[str]
    next_test: str | None

    @model_validator(mode="after")
    def coherent(self):
        if self.decision == "approved" and (self.evidence_gaps or self.disposition == "unresolved"):
            raise ValueError("Approval cannot retain gaps or uncertainty")
        if self.decision == "needs_revision" and not self.evidence_gaps:
            raise ValueError("Revision requires explicit evidence gaps")
        return self


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def put(path, value):
    path = Path(path)
    temp = path.with_name("." + path.name + "." + uuid.uuid4().hex)
    with temp.open("w") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def _positive_finite_seconds(value):
    # Compare without converting arbitrary-size integers to float. This rejects
    # NaN/infinity before creating directories or persisting partial records.
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 < value <= sys.float_info.max
    )


class ResearchService(
    GuidedResearch, MethodService, NotebookService, ProgressService, ControlService
):
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self.manifest = json.loads((self.root / "research.json").read_text())
        self.work = self.root / "research"
        self.verify_guidance()
        if self.manifest.get("continuation"):
            from .research_continuation import verify

            verify(self)

    @classmethod
    def create(
        cls,
        root,
        hypothesis,
        *,
        wall_seconds=3600,
        capabilities=None,
        execution_backend=None,
        completion_policy=None,
        execution_pool=None,
    ):
        root = Path(root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        if (root / "research.json").exists():
            existing = cls(root)
            if existing.manifest["hypothesis"] != hypothesis:
                raise ValueError("Original hypothesis is immutable")
            if (
                completion_policy
                and existing.manifest.get("completion_policy", "repair") != completion_policy
            ):
                raise ValueError("Completion policy is immutable within a study")
            if (
                execution_backend
                and existing.manifest.get("execution_backend", "bubblewrap") != execution_backend
            ):
                raise ValueError("Execution backend is immutable within a study")
            if execution_pool is not None and execution_pool != existing.manifest.get(
                "execution_pool"
            ):
                raise ValueError("Execution pool is immutable within a study")
            return existing
        execution_backend = execution_backend or "bubblewrap"
        completion_policy = completion_policy or "repair"
        if completion_policy not in {"answer", "repair"}:
            raise ValueError("Unknown completion policy")
        if execution_backend not in {"bubblewrap", "proot-cooperative", "process-cooperative"}:
            raise ValueError("Unknown execution backend")
        if any(root.iterdir()):
            raise ValueError(
                "New minimal study requires an empty directory; never convert a campaign"
            )
        if not hypothesis.strip() or not _positive_finite_seconds(wall_seconds):
            raise ValueError("Require a hypothesis and positive finite deadline")
        for name in ["research", "experiments", "commitments", "reviews"]:
            (root / name).mkdir(exist_ok=True)
        registry = (
            MVPCapabilityRegistry.discover(capabilities)
            if capabilities
            else MVPCapabilityRegistry()
        )
        now = time.time()
        remote_capabilities = {
            name: entry["runtime_sha256"]
            for name, entry in (execution_pool or {}).get("capabilities", {}).items()
        }
        if set(registry.hashes) & set(remote_capabilities):
            raise ValueError("Local and worker capability names collide")
        put(
            root / "research.json",
            dict(
                schema_version=3,
                study_id=uuid.uuid4().hex,
                methods_required=bool(registry.hashes or remote_capabilities),
                workflow="minimal",
                completion_policy=completion_policy,
                execution_backend=execution_backend,
                hypothesis=hypothesis,
                created_at=now,
                deadline=now + wall_seconds,
                capabilities=str(Path(capabilities).resolve()) if capabilities else None,
                capability_hashes=registry.hashes | remote_capabilities,
                max_experiment_bytes=4 * 1024**3,
                max_total_bytes=max(
                    8,
                    sum(
                        w["profile"]["config"]["max_jobs"]
                        for w in (execution_pool or {}).get("workers", {}).values()
                    )
                    * 4,
                )
                * 1024**3,
                **({"execution_pool": execution_pool} if execution_pool else {}),
            ),
        )
        return cls(root)

    @contextmanager
    def lock(self):
        with (self.root / ".service.lock").open("a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            yield

    def _read(self, kind, identifier):
        if not identifier or any(
            c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in identifier
        ):
            raise ValueError("Invalid receipt ID")
        return json.loads((self.root / kind / (identifier + ".json")).read_text())

    def _all(self, kind):
        return [json.loads(p.read_text()) for p in sorted((self.root / kind).glob("*.json"))]

    def freeze_protocol(self, protocol):
        """Bind operator requirements before research begins, including reviewer context."""
        if not isinstance(protocol, str):
            raise ValueError("Operator protocol must be text")
        with self.lock():
            manifest = json.loads((self.root / "research.json").read_text())
            if manifest.get("operator_protocol") is not None:
                if manifest["operator_protocol"] != protocol:
                    raise ValueError("Operator protocol is immutable within a study")
            else:
                if self._all("experiments") or self._all("commitments"):
                    raise ValueError("Cannot add an operator protocol retrospectively")
                manifest["operator_protocol"] = protocol
                manifest["protocol_sha256"] = hashlib.sha256(protocol.encode()).hexdigest()
                put(self.root / "research.json", manifest)
            self.manifest = manifest

    def _source(self, path):
        p = self.work / path
        if ".." in Path(path).parts:
            raise ValueError("Source paths cannot contain parent traversal")
        if Path(path).is_absolute() or not p.resolve().is_relative_to(self.work.resolve()):
            raise ValueError("Use a source path inside the research directory")
        if not p.is_file() or p.is_symlink():
            raise ValueError("Source/input must be a regular local file")
        return p

    def _binding(self, source, args, inputs, capability):
        paths = list(dict.fromkeys([source, *inputs]))
        hashes = {p: sha(self._source(p)) for p in paths}
        runtime = None
        remote = self.manifest.get("execution_pool", {}).get("capabilities", {}).get(capability)
        if capability:
            if remote:
                runtime = remote["runtime_sha256"]
            else:
                registry = MVPCapabilityRegistry.discover(self.manifest["capabilities"])
                runtime = registry.get(capability).contract_hash
            if runtime != self.capability_hashes().get(capability):
                raise ValueError("Capability identity changed since study creation")
        return dict(
            source=source,
            args=list(args),
            inputs=hashes,
            capability=capability,
            runtime_sha256=runtime,
            **({"worker_capability": remote["worker_capability"]} if remote else {}),
        )

    def lineage(self, claim):
        """Return immutable ancestors in root-to-parent order; detect corrupted links."""
        nodes, seen = [], set()
        while claim != "root":
            if claim in seen:
                raise ValueError("Cyclic hypothesis ancestry")
            seen.add(claim)
            node = self._read("commitments", claim)
            nodes.append(node)
            claim = node["parent"]
        return [
            dict(id="root", statement=self.manifest["hypothesis"], parent=None),
            *reversed(nodes),
        ]

    def commit(
        self,
        statement,
        *,
        source,
        cases,
        acceptance,
        numerical_bounds=(),
        inputs=(),
        capability=None,
        parent="root",
        rationale=None,
    ):
        """Freeze a repaired prediction and exact planned commands before testing it."""
        if not statement.strip() or not acceptance.strip() or not cases:
            raise ValueError("A repair needs a statement, acceptance rule and planned cases")
        ancestors = self.lineage(parent)
        if statement.strip() == ancestors[-1]["statement"].strip():
            raise ValueError("A repair must change its parent statement")
        if self.manifest["schema_version"] >= 2 and (not rationale or not rationale.strip()):
            raise ValueError("Explain the smallest justified repair in rationale")
        bindings = [self._binding(source, args, inputs, capability) for args in cases]
        body = dict(
            statement=statement,
            parent=parent,
            acceptance=acceptance,
            rationale=rationale,
            bindings=bindings,
        )
        if numerical_bounds:
            from .research_acceptance import acceptance_bounds

            body["numerical_bounds"] = acceptance_bounds(numerical_bounds)
        identifier = "commit_" + fingerprint(body)[:24]
        with self.lock():
            path = self.root / "commitments" / (identifier + ".json")
            if not path.exists():
                put(path, dict(id=identifier, created_at=time.time(), **body))
        return self._read("commitments", identifier)

    def analyze(self, source, args=(), **kwargs):
        """Record frozen exploratory postprocessing without claiming method approval."""
        if "stage" in kwargs or "purpose" in kwargs or kwargs.get("commitment"):
            raise ValueError(
                "lab.analyze records exploration with purpose='diagnostic'. "
                "Use lab.run with an approved method for claim evidence."
            )
        return self.run(source, args, stage="exploration", purpose="diagnostic", **kwargs)

    def run(
        self,
        source,
        args=(),
        *,
        inputs=(),
        outputs=(),
        capability=None,
        commitment=None,
        timeout=600,
        key=None,
        stage="evidence",
        method=None,
        review_documents=None,
        parent_experiment=None,
        purpose=None,
        plan=None,
        machine=None,
        resources=None,
        monitor=None,
    ):
        """Snapshot inputs, launch a bounded experiment, return an immediate receipt."""
        if not outputs or not _positive_finite_seconds(timeout):
            raise ValueError("Declare result paths and a positive finite timeout")
        for p in outputs:
            if Path(p).is_absolute() or ".." in Path(p).parts:
                raise ValueError("Result paths must stay inside the experiment workspace")
        binding = self._binding(source, args, inputs, capability)
        pool = self.manifest.get("execution_pool")
        selected_machine = None
        if pool and (not capability or capability in pool["capabilities"] or machine):
            from .worker_protocol import Resources

            resources = Resources.model_validate(resources or {}).model_dump(mode="json")
        elif machine or resources:
            raise ValueError("Configure a study execution pool before selecting worker resources")
        if stage not in {"exploration", "evidence"}:
            raise ValueError("stage must be exploration or evidence")
        if review_documents is not None and (
            not review_documents or any(p not in outputs for p in review_documents)
        ):
            raise ValueError("review_documents must be nonempty declared outputs")
        if set(outputs) & set(binding["inputs"]):
            raise ValueError("Declared outputs cannot also be supplied inputs")
        self.check_method(binding, method, stage)
        self.validate_experiment_context(parent_experiment, purpose, plan)
        sizes = [self._source(p).stat().st_size for p in binding["inputs"]]
        if sum(sizes) > self.manifest["max_experiment_bytes"] or max(sizes) > 512 * 1024**2:
            raise ValueError("Declared inputs exceed experiment storage limits")
        if commitment:
            frozen = self._read("commitments", commitment)
            if binding not in frozen["bindings"]:
                raise ValueError("Execution differs from the prospective commitment")
        identity = dict(binding=binding, outputs=list(outputs), commitment=commitment, key=key)
        if monitor is not None:
            identity["monitor"] = ExperimentMonitor.model_validate(monitor).model_dump(mode="json")
        if resources is not None:
            # Automatic placement is durable allocation, not part of retry identity.
            identity.update(execution_target=machine or "auto", resources=resources)
        # Preserve legacy idempotency identities for calls without the new options.
        if stage != "evidence" or method is not None or review_documents is not None:
            identity.update(stage=stage, method=method, review_documents=review_documents)
        if parent_experiment is not None or purpose is not None or plan is not None:
            identity.update(parent_experiment=parent_experiment, purpose=purpose, plan=plan)
        identifier = "exp_" + fingerprint(identity)[:24]
        with self.lock():
            path = self.root / "experiments" / (identifier + ".json")
            if path.exists():
                return self._read("experiments", identifier)
            self.check_director(stage, purpose, timeout)
            if time.time() >= self.manifest["deadline"]:
                raise ValueError("Study deadline exhausted")
            used = BubblewrapSandbox._tree_bytes(self.root / "experiments")
            reserved = sum(
                max(
                    0,
                    x.get("workspace_limit_bytes", self.manifest["max_experiment_bytes"])
                    - BubblewrapSandbox._tree_bytes(
                        self.root / "experiments" / x["id"] / "workspace"
                    ),
                )
                for x in self._all("experiments")
                if x["status"] in ["queued", "running"]
            )
            workspace_limit = min(
                self.manifest["max_experiment_bytes"],
                self.manifest["max_total_bytes"] - used - reserved,
            )
            if workspace_limit < sum(sizes) + 1024**2:
                raise ValueError("Insufficient study storage reservation; await active experiments")
            if resources is not None:
                from .execution_pool import job_identifier, reserve_worker

                selected_machine, resources = reserve_worker(
                    pool,
                    capability,
                    machine,
                    resources,
                    reservation=job_identifier(self, {"id": identifier}),
                    receipt=path,
                    deadline=self.manifest["deadline"],
                    require_monitor=monitor is not None,
                )
            workspace = self.root / "experiments" / identifier / "workspace"
            workspace.mkdir(parents=True)
            for relative, expected in binding["inputs"].items():
                target = workspace / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(self._source(relative), target)
                if sha(target) != expected:
                    raise ValueError("Input changed while snapshotting")
            from .research_continuation import steering

            record = dict(
                id=identifier,
                status="queued",
                operator_guidance_ids=[r["id"] for r in steering(self.root)],
                created_at=time.time(),
                timeout=min(timeout, self.manifest["deadline"] - time.time()),
                workspace_limit_bytes=workspace_limit,
                **identity,
                **({"machine": selected_machine} if selected_machine else {}),
            )
            put(path, record)
            self._spawn_experiment(record)
            put(path, record)
        return record

    def _spawn_experiment(self, record):
        from .mvp_launch import read_process_identity

        directory = self.root / "experiments" / record["id"]
        env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]))
        with (directory / "worker.log").open("a") as log:
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "conjecture_solver.research_service",
                    "--root",
                    str(self.root),
                    "--execute",
                    record["id"],
                ],
                env=env,
                stdout=log,
                stderr=log,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        record["pid"] = child.pid
        identity = read_process_identity(child.pid, argv=getattr(child, "args", ()))
        record["worker_identity"] = identity.model_dump(mode="json") if identity else None

    def execute(self, identifier):
        from .mvp_launch import read_process_identity

        path = self.root / "experiments" / (identifier + ".json")
        with self.lock():
            record = self._read("experiments", identifier)
            if record["status"] != "queued":
                return
            if record.get("cancel_requested") and not record.get("machine"):
                record.update(
                    status="cancelled", finished_at=time.time(), cancellation_confirmed=True
                )
                put(path, record)
                return
            identity = read_process_identity(os.getpid())
            if identity:
                record["worker_identity"] = identity.model_dump(mode="json")
            record.update(status="running", started_at=time.time())
            put(path, record)
        if record.get("machine"):
            from .execution_pool import dispatch

            try:
                dispatch(self, record)
            except Exception as error:
                with self.lock():
                    current = self._read("experiments", identifier)
                    if current["status"] not in {"cancelled", "succeeded", "timed_out"}:
                        current.update(status="failed", error=str(error), finished_at=time.time())
                        put(path, current)
            return
        workspace = self.root / "experiments" / identifier / "workspace"
        interrupted = [False]
        previous_handler = None
        if threading.current_thread() is threading.main_thread():
            # Retain the executor long enough to harvest the stopped sandbox.
            # Its descendants receive the process-group TERM independently.
            def retain_partial_outputs(signum, frame):
                interrupted[0] = True

            previous_handler = signal.signal(signal.SIGTERM, retain_partial_outputs)
        try:
            from .experiment_executor import execute_frozen

            timeout = min(record["timeout"], self.manifest["deadline"] - time.time())
            if timeout <= 0:
                raise ValueError("Study deadline exhausted before launch")
            record.update(
                execute_frozen(
                    workspace,
                    record["binding"],
                    record["outputs"],
                    timeout=timeout,
                    execution_backend=self.manifest.get("execution_backend", "bubblewrap"),
                    capabilities=self.manifest.get("capabilities"),
                    max_workspace_bytes=record.get(
                        "workspace_limit_bytes", self.manifest["max_experiment_bytes"]
                    ),
                    cancel_check=lambda: (
                        interrupted[0]
                        or self._read("experiments", identifier).get("cancel_requested", False)
                    ),
                    progress_callback=lambda event: self._execution_progress(identifier, event),
                    monitor=record.get("monitor"),
                )
            )
        except Exception as error:
            record.update(status="failed", error=str(error))
        finally:
            if previous_handler is not None:
                signal.signal(signal.SIGTERM, previous_handler)
        if interrupted[0]:
            record["status"] = "cancelled"
        record["finished_at"] = time.time()
        with self.lock():
            current = self._read("experiments", identifier)
            if current["status"] == "cancelled" or current.get("cancel_requested"):
                record["status"] = "cancelled"
                record["cancellation_confirmed"] = True
            for k in ["stop_reason", "stop_requested_at", "cancel_requested", "telemetry"]:
                if k in current:
                    record[k] = current[k]
            put(path, record)

    def _execution_progress(self, identifier, event):
        with self.lock():
            current = self._read("experiments", identifier)
            if current["status"] in {"queued", "running"}:
                current.update(event)
                put(self.root / "experiments" / (identifier + ".json"), current)

    def review(
        self, experiments, conclusion, *, claim="root", disposition="supported", challenge=None
    ):
        """Submit a durable review request. This never approves or closes a claim."""
        if disposition not in ["supported", "falsified", "unresolved"] or not conclusion.strip():
            raise ValueError("Invalid disposition or empty conclusion")
        if not experiments or len(set(experiments)) != len(experiments):
            raise ValueError("Supply distinct recorded experiments")
        body = dict(
            experiments=list(experiments),
            conclusion=conclusion,
            claim=claim,
            disposition=disposition,
        )
        if challenge is not None:
            body["challenge"] = challenge
        # Validate before issuing a receipt; the host revalidates before judging.
        self.packet(body)
        identifier = "review_" + fingerprint(body)[:24]
        with self.lock():
            path = self.root / "reviews" / (identifier + ".json")
            if not path.exists():
                put(path, dict(id=identifier, status="queued", created_at=time.time(), **body))
        return self.review_status(identifier)

    def review_status(self, identifier):
        request = self._read("reviews", identifier)
        if request["status"] == "queued":
            request["blocked_by_claims"] = self.review_blockers(request)
        return request

    def review_blockers(self, request):
        """Claims whose falsification must be accepted before reviewing repair support."""
        claim = request.get("claim", "root")
        if (
            self.manifest["schema_version"] < 2
            or claim == "root"
            or request.get("disposition") != "supported"
        ):
            return []
        failures = {
            r["claim"]
            for r in self._all("reviews")
            if r.get("verdict", {}).get("decision") == "approved"
            and r["verdict"]["disposition"] == "falsified"
        }
        return [a["id"] for a in self.lineage(claim)[:-1] if a["id"] not in failures]

    @staticmethod
    def review_body(request):
        return {
            k: request[k]
            for k in ["experiments", "conclusion", "claim", "disposition", "challenge"]
            if k in request
        }

    def packet(self, request, *, include_history=True):
        from .research_continuation import steering
        from .research_methods import instrument_requirement

        claim = request["claim"]
        if self.manifest["schema_version"] >= 2 and request["disposition"] == "supported":
            challenge = request.get("challenge")
            if (
                not isinstance(challenge, dict)
                or set(challenge) != {"strategy", "experiments", "outcome"}
                or not all(
                    isinstance(challenge[k], str) and challenge[k].strip()
                    for k in ["strategy", "outcome"]
                )
                or not isinstance(challenge["experiments"], list)
                or not challenge["experiments"]
                or any(e not in request["experiments"] for e in challenge["experiments"])
            ):
                raise ValueError(
                    "Support requires challenge={strategy, experiments, outcome}; "
                    "cite submitted experiments that tried to disprove the claim"
                )
        commitment = self._read("commitments", claim) if claim != "root" else None
        packet = dict(
            target_claim=dict(
                id=claim,
                kind="repair" if commitment else "original",
                statement=commitment["statement"] if commitment else self.manifest["hypothesis"],
            ),
            original_hypothesis=self.manifest["hypothesis"],
            operator_protocol=self.manifest.get("operator_protocol"),
            operator_steering=steering(self.root),
            protocol_sha256=self.manifest.get("protocol_sha256"),
            requirements=self.manifest.get("requirements", {}),
            requirements_evaluation=instrument_requirement(
                self.manifest, available=self.capability_hashes()
            ),
            guided_commissioning=self.manifest.get("guided_commissioning"),
            request=request,
            commitment=commitment,
            experiments=[],
        )
        if commitment and include_history:
            packet["ancestry"] = self.lineage(commitment["parent"])
            ancestor_ids = {a["id"] for a in packet["ancestry"]}
            failures = [
                r
                for r in self._all("reviews")
                if r["claim"] in ancestor_ids
                and r.get("verdict", {}).get("decision") == "approved"
                and r["verdict"]["disposition"] == "falsified"
            ]
            # Include actual counterexample source/results, not only an agent's retelling.
            packet["counterexamples"] = [
                dict(
                    review=r,
                    evidence=self.packet(self.review_body(r), include_history=False)["experiments"],
                )
                for r in failures
            ]
        for identifier in request["experiments"]:
            record = self._read("experiments", identifier)
            if record["status"] != "succeeded":
                raise ValueError(f"{identifier} is not a successful recorded experiment")
            if record.get("stage", "evidence") != "evidence":
                raise ValueError("Exploration is not claim evidence; run fresh evidence")
            self.check_method(record["binding"], record.get("method"), "evidence")
            if commitment and (
                record["commitment"] != claim or record["created_at"] < commitment["created_at"]
            ):
                raise ValueError("Repair evidence must be generated under its prior commitment")
            workspace = self.root / "experiments" / identifier / "workspace"
            for relative, meta in record["artifacts"].items():
                if sha(workspace / relative) != meta["sha256"]:
                    raise ValueError("Recorded artifact was changed after execution")
            sources = {}
            for p in record["binding"]["inputs"]:
                code = p == record["binding"]["source"] or p.endswith((".py", ".sh"))
                size = (workspace / p).stat().st_size
                if code and size > 131072:
                    raise ValueError("Review requires complete source files of at most 128 KiB")
                if code or (p.endswith((".json", ".txt", ".par")) and size <= 131072):
                    sources[p] = (workspace / p).read_text()
            from .research_audit import review_documents

            documents, raw_artifacts, findings = review_documents(workspace, record)
            packet["experiments"].append(
                dict(
                    record=record,
                    sources=sources,
                    documents=documents,
                    raw_artifacts=raw_artifacts,
                    output_findings=findings,
                )
            )
        if commitment:
            tested = [e["record"]["binding"] for e in packet["experiments"]]
            if any(b not in tested for b in commitment["bindings"]):
                raise ValueError("Repair evidence omits a prospectively required case")
        if len(json.dumps(packet).encode()) > 1_000_000:
            raise ValueError("Review packet exceeds 1 MB; use compact summaries")
        return packet

    def record_verdict(self, identifier, verdict, *, packet_sha256):
        """Host-only entry point, deliberately absent from the worker client."""
        verdict = ResearchVerdict.model_validate(verdict).model_dump(mode="json")
        with self.lock():
            request = self._read("reviews", identifier)
            packet = self.packet(self.review_body(request))
            if fingerprint(packet) != packet_sha256:
                raise ValueError("Review packet changed")
            if request["status"] != "queued":
                raise ValueError("Review is already resolved")
            if verdict["claim_id"] != request["claim"]:
                raise ValueError("Verdict addresses a different claim")
            if verdict["decision"] == "approved":
                if self.manifest["schema_version"] >= 2:
                    if verdict["disposition"] == "supported":
                        # A reviewer may correct the requested disposition; support must
                        # still meet the same challenge validation as a support request.
                        self.packet(self.review_body(request) | {"disposition": "supported"})
                    if request["claim"] != "root" and verdict["disposition"] == "supported":
                        failures = {
                            r["claim"]
                            for r in self._all("reviews")
                            if r.get("verdict", {}).get("decision") == "approved"
                            and r["verdict"]["disposition"] == "falsified"
                        }
                        ancestors = self.lineage(request["claim"])[:-1]
                        if any(a["id"] not in failures for a in ancestors):
                            raise ValueError(
                                "Repair support requires accepted ancestor falsifications"
                            )
                prior = [
                    r
                    for r in self._all("reviews")
                    if r["claim"] == request["claim"]
                    and r.get("verdict", {}).get("decision") == "approved"
                ]
                if any(r["verdict"]["disposition"] != verdict["disposition"] for r in prior):
                    raise ValueError("Contradictory claim closure needs explicit recovery")
            if set(verdict) != {
                "claim_id",
                "decision",
                "disposition",
                "rationale",
                "evidence_gaps",
                "next_test",
            }:
                raise ValueError("Invalid review fields")
            if verdict["decision"] not in ["approved", "needs_revision"]:
                raise ValueError("Invalid review decision")
            if verdict["disposition"] not in ["supported", "falsified", "unresolved"]:
                raise ValueError("Invalid scientific disposition")
            if verdict["decision"] == "approved" and (
                verdict["evidence_gaps"] or verdict["disposition"] == "unresolved"
            ):
                raise ValueError("Approval cannot retain evidence gaps or uncertainty")
            if not isinstance(verdict["rationale"], str) or len(verdict["rationale"]) < 16:
                raise ValueError("Review requires a substantive rationale")
            request.update(
                status="resolved",
                verdict=verdict,
                packet_sha256=packet_sha256,
                resolved_at=time.time(),
            )
            put(self.root / "reviews" / (identifier + ".json"), request)
        return self.status()

    def reconcile_workers(self):
        """A dead experiment process is a recorded failure, never an eternal wait."""
        from .mvp_launch import ProcessIdentity, process_identity_matches

        with self.lock():
            for record in self._all("experiments"):
                identity = record.get("worker_identity")
                if record["status"] not in {"queued", "running"} or not identity:
                    continue
                if process_identity_matches(ProcessIdentity.model_validate(identity)):
                    continue
                if record.get("machine"):
                    # A coordinator restart does not establish remote experiment failure.
                    record.update(status="queued", recovery_started_at=time.time())
                    self._spawn_experiment(record)
                    put(self.root / "experiments" / (record["id"] + ".json"), record)
                    continue
                record.update(
                    status="failed",
                    finished_at=time.time(),
                    error="Experiment worker disappeared before writing a terminal receipt",
                )
                put(self.root / "experiments" / (record["id"] + ".json"), record)

    def status(self, *, compact=False):
        self.reconcile_workers()
        reviews = self._all("reviews")
        for request in reviews:
            if request["status"] == "queued":
                request["blocked_by_claims"] = self.review_blockers(request)
        accepted = [r for r in reviews if r.get("verdict", {}).get("decision") == "approved"]
        original_supported = any(
            r["claim"] == "root" and r["verdict"]["disposition"] == "supported" for r in accepted
        )
        original_falsified = any(
            r["claim"] == "root" and r["verdict"]["disposition"] == "falsified" for r in accepted
        )
        repair_supported = any(
            r["claim"] != "root" and r["verdict"]["disposition"] == "supported" for r in accepted
        )
        snapshot = dict(
            workflow="minimal",
            hypothesis=self.manifest["hypothesis"],
            remaining_seconds=max(0, self.manifest["deadline"] - time.time()),
            deadline=self.manifest["deadline"],
            resource_limits={
                k: self.manifest[k] for k in ["max_experiment_bytes", "max_total_bytes"]
            },
            completion_policy=self.manifest.get("completion_policy", "repair"),
            completed=original_supported
            or (
                original_falsified
                and (repair_supported or self.manifest.get("completion_policy") == "answer")
            ),
            experiments=self._all("experiments"),
            commitments=self._all("commitments"),
            reviews=reviews,
            methods=self._all("methods"),
            capability_additions=self._all("capability_additions"),
            progress=self.progress_summary(max(0, self.manifest["deadline"] - time.time())),
        )
        for experiment in snapshot["experiments"]:
            linked = [r for r in reviews if experiment["id"] in r.get("experiments", [])]
            experiment["review_ids"] = [r["id"] for r in linked]
            experiment["scientific_status"] = (
                "reviewed"
                if any(r["status"] == "resolved" for r in linked)
                else "review_pending"
                if linked
                else "unreviewed"
            )
        from .research_audit import study_findings

        snapshot["audit"] = study_findings(snapshot, self.manifest)

        if compact:
            snapshot["methods"] = [
                {k: m.get(k) for k in ["id", "created_at", "status", "binding", "verdict"]}
                for m in snapshot["methods"]
            ]
            snapshot["experiments"] = [
                dict(
                    id=e["id"],
                    created_at=e["created_at"],
                    status=e["status"],
                    parent_experiment=e.get("parent_experiment"),
                    started_at=e.get("started_at"),
                    timeout=e.get("timeout"),
                    monitor=e.get("monitor"),
                    telemetry=e.get("telemetry"),
                    cancel_requested=e.get("cancel_requested", False),
                    stop_reason=e.get("stop_reason"),
                    purpose=e.get("purpose"),
                    plan=e.get("plan"),
                    machine=e.get("machine", "local"),
                    resources=e.get("resources"),
                    remote_job=e.get("remote_job"),
                    transport_status=e.get("transport_status"),
                    assigned_gpu_ids=e.get("assigned_gpu_ids"),
                    commitment=e.get("commitment"),
                    outputs=e["outputs"],
                    stage=e.get("stage", "evidence"),
                    method=e.get("method"),
                    scientific_status=e.get("scientific_status", "unreviewed"),
                    review_ids=e.get("review_ids", []),
                    output_findings=e.get("output_findings", []),
                    workspace=str(self.root / "experiments" / e["id"] / "workspace"),
                    receipt=str(self.root / "experiments" / (e["id"] + ".json")),
                )
                for e in snapshot["experiments"]
            ]
            snapshot["commitments"] = [
                {
                    k: c.get(k)
                    for k in [
                        "id",
                        "parent",
                        "statement",
                        "rationale",
                        "acceptance",
                        "numerical_bounds",
                    ]
                }
                for c in snapshot["commitments"]
            ]
            snapshot["reviews"] = [
                {
                    k: r.get(k)
                    for k in ["id", "created_at", "claim", "status", "verdict", "blocked_by_claims"]
                }
                for r in snapshot["reviews"]
            ]
        return snapshot

    def cancel_active(self):
        from .execution_pool import cancel_remote

        for record in self._all("experiments"):
            if record.get("machine") and record["status"] in {"queued", "running"}:
                cancel_remote(self, record)
        with self.lock():
            for record in self._all("experiments"):
                if record["status"] in ["queued", "running"]:
                    if record.get("machine"):
                        continue
                    if record.get("worker_identity"):
                        from .mvp_launch import ProcessIdentity, process_identity_matches

                        identity = ProcessIdentity.model_validate(record["worker_identity"])
                        if process_identity_matches(identity):
                            with suppress(ProcessLookupError):
                                os.killpg(identity.pid, signal.SIGTERM)
                    record.update(status="cancelled", finished_at=time.time())
                    put(self.root / "experiments" / (record["id"] + ".json"), record)

    def machines(self):
        """Frozen execution pool and machine-scoped instrument identities."""
        pool = self.manifest.get("execution_pool")
        if not pool:
            return {"local": {"execution_backend": self.manifest.get("execution_backend")}}
        return {
            name: {
                "label": worker["profile"]["label"],
                "capacity": worker["profile"]["config"],
                "capabilities": {
                    alias: cap
                    for alias, cap in pool["capabilities"].items()
                    if cap["machine"] == name
                },
            }
            for name, worker in pool["workers"].items()
        }

    def fetch_remote(self, experiment, path):
        from .execution_pool import MachineRegistry, download

        record = self._read("experiments", experiment)
        pool = self.manifest.get("execution_pool")
        if (
            not pool
            or not record.get("remote_job")
            or record["status"]
            not in {"succeeded", "failed", "timed_out", "cancelled", "interrupted"}
        ):
            raise ValueError("Select a completed worker experiment")
        metadata = record.get("remote_artifacts", {}).get(path)
        if not metadata:
            raise ValueError("Remote artifact was not recorded")
        workspace = self.root / "experiments" / experiment / "workspace"
        from .worker_protocol import contained

        destination = contained(workspace, path)
        used = BubblewrapSandbox._tree_bytes(workspace)
        if destination.is_file():
            used -= destination.stat().st_size
        if used + metadata["bytes"] > record["workspace_limit_bytes"]:
            raise ValueError("Artifact exceeds the coordinator storage reservation")

        transport = MachineRegistry(pool["registry"]).transport(
            record["machine"], frozen=pool["workers"][record["machine"]]
        )
        download(transport, record["remote_job"], path, metadata, destination)
        with self.lock():
            current = self._read("experiments", experiment)
            current["artifacts"][path] = metadata
            put(self.root / "experiments" / (experiment + ".json"), current)
        return {"path": str(workspace / path), **metadata}

    def read_instrument(self, capability, **kwargs):
        from .execution_pool import MachineRegistry

        pool = self.manifest.get("execution_pool") or {}
        entry = pool.get("capabilities", {}).get(capability)
        if not entry:
            raise ValueError("Choose a machine-scoped instrument alias")
        transport = MachineRegistry(pool["registry"]).transport(
            entry["machine"], frozen=pool["workers"][entry["machine"]]
        )
        return transport.call("read_instrument", capability=entry["worker_capability"], **kwargs)


class Lab:
    """Worker API. Authority to accept reviews stays with the supervisor."""

    def __init__(self, root):
        self._service = ResearchService(root)

    def run(self, source, args=(), **kwargs):
        return self._service.run(source, args, **kwargs)

    def analyze(self, source, args=(), **kwargs):
        return self._service.analyze(source, args, **kwargs)

    def progress(self, **kwargs):
        return self._service.progress(**kwargs)

    def machines(self):
        return self._service.machines()

    def fetch_remote(self, **kwargs):
        return self._service.fetch_remote(**kwargs)

    def read_instrument(self, capability, **kwargs):
        return self._service.read_instrument(capability, **kwargs)

    def reproduce_anchor(self, **kwargs):
        return self._service.reproduce_anchor(**kwargs)

    def status(self, *, compact=True):
        return self._service.status(compact=compact)

    def cancel(self, experiment, *, reason):
        return self._service.cancel(experiment, reason=reason)

    def director_status(self):
        return self._service.director_status()

    def director_ack(self, decision, **kwargs):
        return self._service.director_ack(decision, **kwargs)

    def commit(self, statement, **kwargs):
        return self._service.commit(statement, **kwargs)

    def review(self, experiments, conclusion, **kwargs):
        return self._service.review(experiments, conclusion, **kwargs)

    def review_status(self, identifier):
        return self._service.review_status(identifier)

    def method(self, **kwargs):
        return self._service.method(**kwargs)

    def register_capability(self, name):
        return self._service.register_capability(name)

    def note(self, statement, **kwargs):
        return self._service.note(statement, **kwargs)

    def notes(self, **kwargs):
        return self._service.notes(**kwargs)

    def brief(self, **kwargs):
        return self._service.brief(**kwargs)

    def compare(self, experiments, metrics):
        return self._service.compare(experiments, metrics)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execute")
    group.add_argument(
        "--call",
        choices=[
            "run",
            "cancel",
            "director_status",
            "director_ack",
            "analyze",
            "progress",
            "reproduce_anchor",
            "status",
            "commit",
            "review",
            "review_status",
            "method",
            "register_capability",
            "note",
            "notes",
            "brief",
            "compare",
            "machines",
            "fetch_remote",
            "read_instrument",
        ],
    )
    a = parser.parse_args()
    service = ResearchService(a.root)
    if a.execute:
        service.execute(a.execute)
    else:
        try:
            arguments = json.load(sys.stdin)
            result = getattr(service, a.call)(**arguments)
            print(json.dumps(dict(ok=True, result=result)))
        except Exception as error:
            print(json.dumps(dict(ok=False, error=str(error))))
            raise SystemExit(1) from error


if __name__ == "__main__":
    main()
