"""Host-enforced, expiring repair grants for isolated experimental components.

This prototype applies only to a private component tree. It cannot authorize
modification or hot-patching of the installed production research supervisor.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .events import digest, put


class AuthorityVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["grant", "deny", "diagnose"]
    rationale: str = Field(min_length=16, max_length=4000)
    evidence: list[str] = Field(min_length=1, max_length=16)
    files: list[str] = Field(default_factory=list, max_length=4)
    seconds: int = Field(default=180, ge=10, le=600)


class RepairProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    grant_id: str
    explanation: str = Field(min_length=16, max_length=4000)
    replacements: dict[str, str]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def scoped(root, name):
    path = Path(name)
    if not name or path.is_absolute() or ".." in path.parts or path == Path("."):
        raise ValueError("Repair path must be relative without parent traversal")
    target = root / path
    if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("Repair path escapes its component")
    return target


class RepairAuthority:
    def __init__(self, component, records, *, allowed_files, test_source, maximum_seconds=300):
        self.component = Path(component).resolve()
        self.records = Path(records).resolve()
        self.records.mkdir(parents=True, exist_ok=True)
        self.allowed_files = frozenset(allowed_files)
        self.test_source = test_source
        self.maximum_seconds = maximum_seconds
        # Policy and verification are host-owned inputs, never chosen by a model.
        self.policy_sha256 = digest(
            dict(
                files=sorted(self.allowed_files),
                test_source=test_source,
                maximum_seconds=maximum_seconds,
            )
        )
        self.grants = {}

    def issue(self, incident, verdict, *, judge_receipt):
        verdict = AuthorityVerdict.model_validate(verdict)
        if verdict.decision != "grant":
            return dict(status=verdict.decision, rationale=verdict.rationale)
        files = set(verdict.files)
        if not files or not files <= self.allowed_files:
            raise ValueError("Judge requested authority outside operator policy")
        originals = {name: sha(scoped(self.component, name)) for name in files}
        grant = dict(
            id="grant_" + uuid.uuid4().hex,
            incident_sha256=digest(incident),
            policy_sha256=self.policy_sha256,
            judge_receipt_sha256=digest(judge_receipt),
            created_at=time.time(),
            expires_at=time.time() + min(verdict.seconds, self.maximum_seconds),
            originals=originals,
            status="issued",
            rationale=verdict.rationale,
        )
        self.grants[grant["id"]] = grant
        put(self.records / (grant["id"] + ".json"), grant)
        return json.loads(json.dumps(grant))

    def apply(self, proposal):
        proposal = RepairProposal.model_validate(proposal)
        grant = self.grants.get(proposal.grant_id)
        if grant is None or grant["status"] != "issued":
            raise ValueError("Unknown or consumed repair grant")
        if time.time() >= grant["expires_at"]:
            raise ValueError("Repair grant expired")
        if not proposal.replacements or not set(proposal.replacements) <= set(grant["originals"]):
            raise ValueError("Patch exceeds the granted files")
        if sum(len(text.encode()) for text in proposal.replacements.values()) > 32768:
            raise ValueError("Repair patch exceeds its byte allowance")
        for name, expected in grant["originals"].items():
            if sha(scoped(self.component, name)) != expected:
                raise ValueError("Component changed since authority was granted")
        # Consume the attempt before running candidate code; a retry needs a fresh grant.
        grant["status"] = "validating"
        put(self.records / (grant["id"] + ".json"), grant)
        stage = self.records / grant["id"]
        stage.mkdir()
        for name in grant["originals"]:
            destination = scoped(stage, name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(scoped(self.component, name), destination)
            backup = stage / "before" / name
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(scoped(self.component, name), backup)
        for name, text in proposal.replacements.items():
            scoped(stage, name).write_text(text)
        (stage / "verify_component.py").write_text(self.test_source)
        command = [
            "bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--clearenv",
            "--ro-bind",
            "/usr",
            "/usr",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--ro-bind",
            str(stage),
            "/work",
            "--chdir",
            "/work",
            "--setenv",
            "PATH",
            "/usr/bin:/bin",
            "--setenv",
            "PYTHONDONTWRITEBYTECODE",
            "1",
            "/usr/bin/python3",
            "verify_component.py",
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=min(20, max(0.1, grant["expires_at"] - time.time())),
            )
            receipt = dict(
                returncode=result.returncode,
                stdout=result.stdout[-16000:],
                stderr=result.stderr[-4000:],
                command=command,
                checked_at=time.time(),
                test_sha256=digest(self.test_source),
            )
            if result.returncode:
                raise ValueError("Isolated verification rejected the proposed repair")
            if time.time() >= grant["expires_at"]:
                raise ValueError("Repair grant expired during verification")
            for name, expected in grant["originals"].items():
                if sha(scoped(self.component, name)) != expected:
                    raise ValueError("Component changed during verification")
            if len(proposal.replacements) != 1:
                raise ValueError("Prototype deployment supports one atomic file per grant")
            name, text = next(iter(proposal.replacements.items()))
            target = scoped(self.component, name)
            temporary = target.with_name(".repair-" + uuid.uuid4().hex)
            temporary.write_text(text)
            os.replace(temporary, target)
            grant.update(
                status="applied",
                applied_at=time.time(),
                result_sha256=sha(target),
                verification=receipt,
            )
        except Exception as error:
            grant.update(status="rejected", error=str(error))
            if "receipt" in locals():
                grant["verification"] = receipt
            raise
        finally:
            put(self.records / (grant["id"] + ".json"), grant)
        return json.loads(json.dumps(grant))

    def rollback(self, grant_id):
        grant = self.grants.get(grant_id)
        if grant is None or grant["status"] != "applied":
            raise ValueError("Only an applied repair can be rolled back")
        if len(grant["originals"]) != 1:
            raise ValueError("Rollback requires a single component file")
        name = next(iter(grant["originals"]))
        target = scoped(self.component, name)
        if sha(target) != grant["result_sha256"]:
            raise ValueError("Component changed after repair; refusing to overwrite it")
        original = self.records / grant_id / "before" / name
        if sha(original) != grant["originals"][name]:
            raise ValueError("Rollback snapshot integrity failed")
        temporary = target.with_name(".rollback-" + uuid.uuid4().hex)
        shutil.copyfile(original, temporary)
        os.replace(temporary, target)
        grant.update(status="rolled_back", rolled_back_at=time.time())
        put(self.records / (grant_id + ".json"), grant)
        return json.loads(json.dumps(grant))
