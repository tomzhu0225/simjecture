"""Evidence-governed software-engineering campaigns.

The engineering domain is the dual of a scientific campaign: the acceptance
contract and its checks stay fixed while candidate implementations evolve in
isolated Git worktrees.  A failed check is recorded as a counterexample to a
patch hypothesis; a passing patch is still only accepted inside the bounded
contract.

This first implementation deliberately keeps model orchestration out of the
module.  It provides the deterministic contract, Git, worktree, and CI
receipt primitives that a future engineering agent can call.
"""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import subprocess
import time
from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import Field, model_validator

from .models import StrictModel, utc_now

ENGINEERING_SCHEMA_VERSION = "0.1.0"
CONTRACT_FILE = "contract.json"
CAMPAIGN_FILE = "campaign.json"
PATCH_DIRECTORY = "patches"
EVIDENCE_DIRECTORY = "evidence"
ADJUDICATION_DIRECTORY = "adjudications"
WORKTREE_DIRECTORY = "worktrees"


class EngineeringError(RuntimeError):
    """The engineering campaign cannot safely perform the requested action."""


class EngineeringCheckStage(StrEnum):
    COMMISSIONING = "commissioning"
    TARGETED = "targeted"
    FULL = "full"
    HOLDOUT = "holdout"


class EngineeringCheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class EngineeringPatchStatus(StrEnum):
    CREATED = "created"
    VALIDATED = "validated"
    ACCEPTED = "accepted"
    COUNTEREXAMPLE = "counterexample"
    REJECTED = "rejected"


class EngineeringDiffReviewStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class EngineeringAdjudicationStatus(StrEnum):
    ACCEPTED = "accepted"
    COUNTEREXAMPLE = "counterexample"
    REJECTED = "rejected"


class EngineeringCheck(StrictModel):
    """One shell-free command in the immutable acceptance contract."""

    schema_version: Literal["0.1.0"] = ENGINEERING_SCHEMA_VERSION
    name: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    command: tuple[str, ...] = Field(min_length=1)
    stage: EngineeringCheckStage = EngineeringCheckStage.FULL
    timeout_seconds: float = Field(default=900.0, gt=0, le=86_400)
    environment: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_process_contract(self) -> EngineeringCheck:
        if any(not item or "\x00" in item for item in self.command):
            raise ValueError("engineering check command arguments must be non-empty")
        if any("\x00" in key or "\x00" in value for key, value in self.environment.items()):
            raise ValueError("engineering check environment cannot contain NUL bytes")
        if any(not key or "=" in key for key in self.environment):
            raise ValueError("engineering check environment keys must be valid names")
        return self


def _validate_relative_patterns(patterns: Sequence[str], *, label: str) -> None:
    for pattern in patterns:
        path = PurePosixPath(pattern)
        if (
            not pattern
            or path.is_absolute()
            or ".." in path.parts
            or "\x00" in pattern
        ):
            raise ValueError(f"{label} must contain safe repository-relative patterns")


class EngineeringContract(StrictModel):
    """Frozen goal, repository identity, path policy, and validation commands."""

    schema_version: Literal["0.1.0"] = ENGINEERING_SCHEMA_VERSION
    campaign_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    goal: str = Field(min_length=1)
    repository: str = Field(min_length=1)
    base_commit: str | None = None
    editable_paths: tuple[str, ...] = Field(min_length=1)
    protected_paths: tuple[str, ...] = (
        "tests/**",
        ".github/**",
        "pyproject.toml",
        "uv.lock",
    )
    checks: tuple[EngineeringCheck, ...] = Field(min_length=1)
    require_clean_repository: bool = True
    max_patch_attempts: int = Field(default=32, ge=1, le=10_000)
    max_output_chars: int = Field(default=30_000, ge=1_000, le=2_000_000)

    @model_validator(mode="after")
    def validate_contract(self) -> EngineeringContract:
        _validate_relative_patterns(self.editable_paths, label="editable_paths")
        _validate_relative_patterns(self.protected_paths, label="protected_paths")
        if set(self.editable_paths).intersection(self.protected_paths):
            raise ValueError("editable and protected path patterns must not overlap")
        names = [check.name for check in self.checks]
        if len(names) != len(set(names)):
            raise ValueError("engineering check names must be unique")
        if any(check.stage is EngineeringCheckStage.HOLDOUT for check in self.checks):
            raise ValueError(
                "holdout checks must be supplied in an external "
                "EngineeringHoldoutContract, not the visible campaign contract"
            )
        if self.base_commit == "":
            raise ValueError("base_commit must be null or a non-empty revision")
        return self


class EngineeringHoldoutContract(StrictModel):
    """A host-controlled validation suite withheld from the patch proposer.

    This object is deliberately separate from EngineeringContract.  The
    campaign records only its content hash and execution receipt after the
    candidate has passed the visible checks.  The caller must keep the JSON
    file and its path outside the agent's worktree and prompt surface.
    """

    schema_version: Literal["0.1.0"] = ENGINEERING_SCHEMA_VERSION
    holdout_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    campaign_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    repository: str = Field(min_length=1)
    base_commit: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    checks: tuple[EngineeringCheck, ...] = Field(min_length=1)
    max_output_chars: int = Field(default=30_000, ge=1_000, le=2_000_000)

    @model_validator(mode="after")
    def validate_holdout(self) -> EngineeringHoldoutContract:
        names = [check.name for check in self.checks]
        if len(names) != len(set(names)):
            raise ValueError("holdout check names must be unique")
        if any(check.stage is not EngineeringCheckStage.HOLDOUT for check in self.checks):
            raise ValueError("every external holdout check must use stage='holdout'")
        return self


class EngineeringCheckResult(StrictModel):
    """Bounded receipt for one command execution."""

    schema_version: Literal["0.1.0"] = ENGINEERING_SCHEMA_VERSION
    name: str
    stage: EngineeringCheckStage
    command: tuple[str, ...]
    status: EngineeringCheckStatus
    exit_code: int | None
    duration_seconds: float = Field(ge=0)
    stdout: str
    stderr: str
    stdout_sha256: str
    stderr_sha256: str


class EngineeringPatchRecord(StrictModel):
    """A patch hypothesis and the evidence attached to its exact commit."""

    schema_version: Literal["0.1.0"] = ENGINEERING_SCHEMA_VERSION
    patch_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    parent_patch_id: str | None = None
    diagnosis: str = Field(min_length=1)
    prediction: str = Field(min_length=1)
    branch: str
    worktree: str
    parent_commit: str
    commit: str | None = None
    status: EngineeringPatchStatus = EngineeringPatchStatus.CREATED
    changed_paths: tuple[str, ...] = ()
    diff_sha256: str | None = None
    checks: tuple[EngineeringCheckResult, ...] = ()
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    validated_at: datetime | None = None


class EngineeringDiffReview(StrictModel):
    """A deterministic review of the exact committed patch, independent of CI."""

    schema_version: Literal["0.1.0"] = ENGINEERING_SCHEMA_VERSION
    patch_id: str
    commit: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    parent_commit: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    diff_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    changed_paths: tuple[str, ...]
    status: EngineeringDiffReviewStatus
    violations: tuple[str, ...] = ()
    reviewer: str = Field(min_length=1)
    reviewed_at: datetime = Field(default_factory=utc_now)


class EngineeringAdjudicationRecord(StrictModel):
    """Final host-side verdict combining hidden checks and diff review."""

    schema_version: Literal["0.1.0"] = ENGINEERING_SCHEMA_VERSION
    campaign_id: str
    patch_id: str
    patch_commit: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    holdout_id: str
    holdout_contract_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    holdout_base_commit: str = Field(pattern=r"^[0-9a-f]{40,64}$")
    diff_review: EngineeringDiffReview
    checks: tuple[EngineeringCheckResult, ...] = ()
    status: EngineeringAdjudicationStatus
    failure_reason: str | None = None
    reviewer: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    half = max(1, limit // 2)
    return text[:half] + "\n... output truncated by engineering contract ...\n" + text[-half:]


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EngineeringError(f"invalid engineering record: {path}") from error
    if not isinstance(payload, dict):
        raise EngineeringError(f"engineering record must be an object: {path}")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(_canonical_json(payload) + b"\n")
    os.replace(temporary, path)


def _safe_patch_id(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]*", value):
        raise EngineeringError(
            "patch id must begin with a lowercase letter or digit and contain only "
            "lowercase letters, digits, dot, underscore, or hyphen"
        )
    return value


def _matches_path(path: str, patterns: Sequence[str]) -> bool:
    normalized = PurePosixPath(path).as_posix()
    return any(
        fnmatch.fnmatchcase(normalized, pattern)
        or PurePosixPath(normalized).match(pattern)
        for pattern in patterns
    )


def _generated_path(path: str) -> bool:
    parts = PurePosixPath(path).parts
    return (
        "__pycache__" in parts
        or ".pytest_cache" in parts
        or ".mypy_cache" in parts
        or ".ruff_cache" in parts
        or path.endswith((".pyc", ".pyo"))
    )


class GitRepository:
    """Small host-controlled Git surface used by an engineering campaign."""

    def __init__(self, path: str | Path) -> None:
        requested = Path(path).expanduser().resolve()
        if not requested.is_dir():
            raise EngineeringError(f"repository directory does not exist: {requested}")
        result = self._run(("rev-parse", "--show-toplevel"), cwd=requested)
        self.root = Path(result.stdout.strip()).resolve()

    @staticmethod
    def _run(
        args: Sequence[str],
        *,
        cwd: Path,
        timeout: float = 60.0,
        text: bool = True,
    ) -> subprocess.CompletedProcess[Any]:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=cwd,
                capture_output=True,
                text=text,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise EngineeringError(f"git command failed: git {' '.join(args)}") from error
        if result.returncode != 0:
            detail = (
                result.stderr.strip()
                if text
                else result.stderr.decode(errors="replace").strip()
            )
            raise EngineeringError(
                f"git command failed ({result.returncode}): git {' '.join(args)}\n{detail}"
            )
        return result

    def resolve_commit(self, revision: str) -> str:
        if not revision or "\x00" in revision:
            raise EngineeringError("base revision must be non-empty")
        return self._run(
            ("rev-parse", "--verify", f"{revision}^{{commit}}"),
            cwd=self.root,
        ).stdout.strip()

    def head_commit(self) -> str:
        return self.resolve_commit("HEAD")

    def worktree_head_commit(self, worktree: Path) -> str:
        """Resolve the commit actually checked out in an isolated worktree."""

        return self._run(("rev-parse", "--verify", "HEAD^{commit}"), cwd=worktree).stdout.strip()

    def is_clean(self) -> bool:
        result = self._run(
            ("status", "--porcelain", "--untracked-files=all"),
            cwd=self.root,
        )
        return not result.stdout.strip()

    def worktree_add(self, path: Path, revision: str, *, branch: str | None = None) -> None:
        if path.exists():
            raise EngineeringError(f"worktree path already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        if branch is None:
            args = ("worktree", "add", "--detach", str(path), revision)
        else:
            args = ("worktree", "add", "-b", branch, str(path), revision)
        self._run(args, cwd=self.root)

    def worktree_remove(self, path: Path) -> None:
        self._run(("worktree", "remove", "--force", str(path)), cwd=self.root)

    def changed_paths(self, worktree: Path, revision: str) -> tuple[str, ...]:
        result = self._run(
            ("diff", "--name-only", "--no-renames", revision),
            cwd=worktree,
        )
        staged = self._run(
            ("diff", "--cached", "--name-only", "--no-renames", revision),
            cwd=worktree,
        )
        untracked = self._run(
            ("ls-files", "--others", "--exclude-standard"),
            cwd=worktree,
        )
        paths = {
            line.strip()
            for output in (result.stdout, staged.stdout, untracked.stdout)
            for line in output.splitlines()
            if line.strip()
        }
        return tuple(sorted(paths))

    def unstaged_paths(self, worktree: Path) -> tuple[str, ...]:
        result = self._run(
            ("diff", "--name-only", "--no-renames"),
            cwd=worktree,
        )
        staged = self._run(
            ("diff", "--cached", "--name-only", "--no-renames"),
            cwd=worktree,
        )
        untracked = self._run(
            ("ls-files", "--others", "--exclude-standard"),
            cwd=worktree,
        )
        paths = {
            line.strip()
            for output in (result.stdout, staged.stdout, untracked.stdout)
            for line in output.splitlines()
            if line.strip()
        }
        return tuple(sorted(paths))

    def stage_paths(self, worktree: Path, paths: Sequence[str]) -> None:
        self._run(("reset", "--"), cwd=worktree)
        self._run(("add", "-A", "--", *paths), cwd=worktree)

    def commit(self, worktree: Path, message: str) -> str:
        if not message.strip():
            raise EngineeringError("patch commit message must not be empty")
        self._run(("commit", "-m", message), cwd=worktree)
        return self._run(("rev-parse", "HEAD"), cwd=worktree).stdout.strip()

    def diff_hash(self, worktree: Path, revision: str) -> str:
        result = self._run(("diff", "--binary", "--no-renames", revision), cwd=worktree, text=False)
        return _sha256(result.stdout)


def _check_result(
    check: EngineeringCheck,
    *,
    worktree: Path,
    max_output_chars: int,
) -> EngineeringCheckResult:
    environment = os.environ.copy()
    environment.update(check.environment)
    started = time.monotonic()
    try:
        process = subprocess.run(
            list(check.command),
            cwd=worktree,
            env=environment,
            capture_output=True,
            text=True,
            timeout=check.timeout_seconds,
            check=False,
        )
        stdout = process.stdout or ""
        stderr = process.stderr or ""
        status = (
            EngineeringCheckStatus.PASSED
            if process.returncode == 0
            else EngineeringCheckStatus.FAILED
        )
        exit_code: int | None = process.returncode
    except subprocess.TimeoutExpired as error:
        raw_stdout = error.stdout or ""
        raw_stderr = error.stderr or ""
        stdout = (
            raw_stdout.decode(errors="replace")
            if isinstance(raw_stdout, bytes)
            else raw_stdout
        )
        stderr = (
            raw_stderr.decode(errors="replace")
            if isinstance(raw_stderr, bytes)
            else raw_stderr
        )
        status = EngineeringCheckStatus.TIMED_OUT
        exit_code = None
    except OSError as error:
        stdout = ""
        stderr = str(error)
        status = EngineeringCheckStatus.FAILED
        exit_code = None
    duration = max(0.0, time.monotonic() - started)
    return EngineeringCheckResult(
        name=check.name,
        stage=check.stage,
        command=check.command,
        status=status,
        exit_code=exit_code,
        duration_seconds=duration,
        stdout=_truncate(stdout, max_output_chars),
        stderr=_truncate(stderr, max_output_chars),
        stdout_sha256=_sha256(stdout.encode("utf-8", errors="replace")),
        stderr_sha256=_sha256(stderr.encode("utf-8", errors="replace")),
    )


class EngineeringDiffJudge:
    """Review patch identity and policy without consulting its check results."""

    @staticmethod
    def review(
        record: EngineeringPatchRecord,
        *,
        contract: EngineeringContract,
        repository: GitRepository,
        reviewer: str,
    ) -> EngineeringDiffReview:
        if record.commit is None:
            raise EngineeringError("a diff review requires a committed patch")
        worktree = (Path(record.worktree)).resolve()
        if not worktree.is_dir():
            raise EngineeringError(f"patch worktree is unavailable: {worktree}")
        violations: list[str] = []
        current_head = repository.worktree_head_commit(worktree)
        if current_head != record.commit:
            violations.append(
                "worktree HEAD does not match the patch record: "
                f"{record.commit} -> {current_head}"
            )
        try:
            actual_parent = repository.resolve_commit(f"{record.commit}^")
        except EngineeringError:
            actual_parent = ""
        if actual_parent != record.parent_commit:
            violations.append(
                "patch commit parent does not match the recorded parent: "
                f"{record.parent_commit} -> {actual_parent or '<missing>'}"
            )
        dirty = tuple(
            path
            for path in repository.unstaged_paths(worktree)
            if not _generated_path(path)
        )
        if dirty:
            violations.append(
                "worktree is not clean after validation: " + ", ".join(dirty)
            )
        changed = tuple(
            path
            for path in repository.changed_paths(worktree, record.parent_commit)
            if not _generated_path(path)
        )
        protected = tuple(
            path for path in changed if _matches_path(path, contract.protected_paths)
        )
        outside = tuple(
            path for path in changed if not _matches_path(path, contract.editable_paths)
        )
        if protected:
            violations.append("protected paths changed: " + ", ".join(protected))
        if outside:
            violations.append("paths outside editable policy: " + ", ".join(outside))
        if not changed:
            violations.append("committed patch contains no editable changes")
        diff_sha256 = repository.diff_hash(worktree, record.parent_commit)
        return EngineeringDiffReview(
            patch_id=record.patch_id,
            commit=record.commit,
            parent_commit=record.parent_commit,
            diff_sha256=diff_sha256,
            changed_paths=changed,
            status=(
                EngineeringDiffReviewStatus.REJECTED
                if violations
                else EngineeringDiffReviewStatus.ACCEPTED
            ),
            violations=tuple(violations),
            reviewer=reviewer,
        )


class EngineeringCampaign:
    """Create and validate an immutable patch-hypothesis campaign."""

    def __init__(
        self,
        output: Path,
        contract: EngineeringContract,
        repository: GitRepository,
    ) -> None:
        self.output = output.resolve()
        self.contract = contract
        self.repository = repository

    @property
    def contract_hash(self) -> str:
        return _sha256(_canonical_json(self.contract.model_dump(mode="json")))

    @classmethod
    def create(cls, contract: EngineeringContract, output: str | Path) -> EngineeringCampaign:
        repository = GitRepository(contract.repository)
        if contract.require_clean_repository and not repository.is_clean():
            raise EngineeringError(
                "repository must be clean before an engineering campaign starts; "
                "capture local work in an explicit seed commit first"
            )
        target = Path(output).expanduser().resolve()
        if target == repository.root or target.is_relative_to(repository.root):
            raise EngineeringError("campaign output must not be inside the target repository")
        if target.exists() and any(target.iterdir()):
            raise EngineeringError(f"campaign output must be empty: {target}")
        target.mkdir(parents=True, exist_ok=True)
        base_commit = (
            repository.resolve_commit(contract.base_commit)
            if contract.base_commit is not None
            else repository.head_commit()
        )
        frozen = contract.model_copy(
            update={
                "repository": str(repository.root),
                "base_commit": base_commit,
            }
        )
        campaign = cls(target, frozen, repository)
        if (target / CONTRACT_FILE).exists() or (target / CAMPAIGN_FILE).exists():
            raise EngineeringError(f"campaign output already contains a contract: {target}")
        _write_json(target / CONTRACT_FILE, frozen.model_dump(mode="json"))
        _write_json(
            target / CAMPAIGN_FILE,
            {
                "schema_version": ENGINEERING_SCHEMA_VERSION,
                "campaign_id": frozen.campaign_id,
                "goal": frozen.goal,
                "repository": frozen.repository,
                "base_commit": frozen.base_commit,
                "contract_sha256": campaign.contract_hash,
                "created_at": utc_now().isoformat(),
            },
        )
        (target / PATCH_DIRECTORY).mkdir()
        (target / EVIDENCE_DIRECTORY).mkdir()
        (target / ADJUDICATION_DIRECTORY).mkdir()
        return campaign

    @classmethod
    def load(cls, output: str | Path) -> EngineeringCampaign:
        target = Path(output).expanduser().resolve()
        contract = EngineeringContract.model_validate(_read_json(target / CONTRACT_FILE))
        if contract.base_commit is None:
            raise EngineeringError("campaign contract has no frozen base_commit")
        repository = GitRepository(contract.repository)
        resolved = repository.resolve_commit(contract.base_commit)
        if resolved != contract.base_commit:
            raise EngineeringError("campaign base commit cannot be resolved exactly")
        campaign = cls(target, contract, repository)
        record = _read_json(target / CAMPAIGN_FILE)
        if record.get("contract_sha256") != campaign.contract_hash:
            raise EngineeringError("engineering contract hash changed after campaign creation")
        return campaign

    def _patch_path(self, patch_id: str) -> Path:
        return self.output / PATCH_DIRECTORY / f"{_safe_patch_id(patch_id)}.json"

    def _load_patch(self, patch_id: str) -> EngineeringPatchRecord:
        return EngineeringPatchRecord.model_validate(_read_json(self._patch_path(patch_id)))

    def _write_patch(self, record: EngineeringPatchRecord) -> None:
        _write_json(self._patch_path(record.patch_id), record.model_dump(mode="json"))

    def _adjudication_path(self, patch_id: str) -> Path:
        return (
            self.output
            / ADJUDICATION_DIRECTORY
            / f"{_safe_patch_id(patch_id)}.json"
        )

    def _branch_name(self, patch_id: str) -> str:
        return f"simj/{self.contract.campaign_id}/{_safe_patch_id(patch_id)}"

    def _expected_worktree(self, patch_id: str) -> Path:
        return (self.output / WORKTREE_DIRECTORY / _safe_patch_id(patch_id)).resolve()

    def _assert_patch_identity(self, record: EngineeringPatchRecord) -> Path:
        """Reject mutable record fields that could redirect host execution."""

        expected_worktree = self._expected_worktree(record.patch_id)
        worktree = Path(record.worktree).resolve()
        if worktree != expected_worktree:
            raise EngineeringError(
                f"patch {record.patch_id!r} worktree does not match its campaign path"
            )
        if record.branch != self._branch_name(record.patch_id):
            raise EngineeringError(
                f"patch {record.patch_id!r} branch does not match its campaign branch"
            )
        return worktree

    def commission(self) -> tuple[EngineeringCheckResult, ...]:
        """Run the frozen checks once on the base commit in a disposable worktree."""

        if (self.output / "commission.json").exists():
            raise EngineeringError("commissioning evidence is already recorded")
        worktree = self.output / WORKTREE_DIRECTORY / "commissioning"
        if worktree.exists():
            raise EngineeringError(f"commissioning worktree already exists: {worktree}")
        self.repository.worktree_add(worktree, self.contract.base_commit or "HEAD")
        try:
            results = tuple(
                _check_result(
                    check,
                    worktree=worktree,
                    max_output_chars=self.contract.max_output_chars,
                )
                for check in self.contract.checks
            )
        finally:
            self.repository.worktree_remove(worktree)
        _write_json(
            self.output / "commission.json",
            {
                "schema_version": ENGINEERING_SCHEMA_VERSION,
                "campaign_id": self.contract.campaign_id,
                "base_commit": self.contract.base_commit,
                "contract_sha256": self.contract_hash,
                "status": (
                    "passed"
                    if all(item.status is EngineeringCheckStatus.PASSED for item in results)
                    else "counterexample"
                ),
                "checks": [item.model_dump(mode="json") for item in results],
                "created_at": utc_now().isoformat(),
            },
        )
        return results

    def create_patch(
        self,
        patch_id: str,
        *,
        diagnosis: str,
        prediction: str,
        parent_patch_id: str | None = None,
    ) -> EngineeringPatchRecord:
        patch_id = _safe_patch_id(patch_id)
        path = self._patch_path(patch_id)
        if path.exists():
            raise EngineeringError(f"patch id already exists: {patch_id}")
        existing = list((self.output / PATCH_DIRECTORY).glob("*.json"))
        if len(existing) >= self.contract.max_patch_attempts:
            raise EngineeringError("engineering patch-attempt budget exhausted")
        parent_commit = self.contract.base_commit
        if parent_patch_id is not None:
            parent = self._load_patch(parent_patch_id)
            if parent.commit is None:
                raise EngineeringError("parent patch must have a committed hypothesis")
            parent_commit = parent.commit
        assert parent_commit is not None
        branch = self._branch_name(patch_id)
        worktree = self._expected_worktree(patch_id)
        self.repository.worktree_add(worktree, parent_commit, branch=branch)
        record = EngineeringPatchRecord(
            patch_id=patch_id,
            parent_patch_id=parent_patch_id,
            diagnosis=diagnosis,
            prediction=prediction,
            branch=branch,
            worktree=str(worktree),
            parent_commit=parent_commit,
        )
        self._write_patch(record)
        return record

    def validate_patch(self, patch_id: str, *, commit_message: str) -> EngineeringPatchRecord:
        record = self._load_patch(patch_id)
        if record.status is not EngineeringPatchStatus.CREATED:
            raise EngineeringError(f"patch {patch_id!r} is already terminal: {record.status.value}")
        worktree = self._assert_patch_identity(record)
        if not worktree.is_dir():
            raise EngineeringError(f"patch worktree is unavailable: {worktree}")
        if self.repository.worktree_head_commit(worktree) != record.parent_commit:
            raise EngineeringError(
                f"patch {patch_id!r} worktree no longer starts at its recorded parent commit"
            )
        changed = self.repository.changed_paths(worktree, self.contract.base_commit or "HEAD")
        relevant = tuple(path for path in changed if not _generated_path(path))
        protected = tuple(
            path for path in relevant if _matches_path(path, self.contract.protected_paths)
        )
        outside = tuple(
            path for path in relevant if not _matches_path(path, self.contract.editable_paths)
        )
        if protected or outside:
            reason_parts = []
            if protected:
                reason_parts.append(f"protected paths changed: {', '.join(protected)}")
            if outside:
                reason_parts.append(f"paths outside editable policy: {', '.join(outside)}")
            rejected = record.model_copy(
                update={
                    "status": EngineeringPatchStatus.REJECTED,
                    "changed_paths": relevant,
                    "failure_reason": "; ".join(reason_parts),
                    "validated_at": utc_now(),
                }
            )
            self._write_patch(rejected)
            return rejected
        if not relevant:
            raise EngineeringError("patch contains no editable changes")
        self.repository.stage_paths(worktree, relevant)
        commit = self.repository.commit(worktree, commit_message)
        results = tuple(
            _check_result(
                check,
                worktree=worktree,
                max_output_chars=self.contract.max_output_chars,
            )
            for check in self.contract.checks
        )
        post_check_changes = tuple(
            path
            for path in self.repository.unstaged_paths(worktree)
            if not _generated_path(path)
        )
        post_check_head = self.repository.worktree_head_commit(worktree)
        if post_check_head != commit:
            status = EngineeringPatchStatus.REJECTED
            failure_reason = (
                "validation commands changed the worktree HEAD after the candidate commit: "
                f"{commit} -> {post_check_head}"
            )
        elif post_check_changes:
            status = EngineeringPatchStatus.REJECTED
            failure_reason = (
                "validation commands modified the worktree after commit: "
                + ", ".join(post_check_changes)
            )
        else:
            passed = all(item.status is EngineeringCheckStatus.PASSED for item in results)
            status = (
                EngineeringPatchStatus.VALIDATED
                if passed
                else EngineeringPatchStatus.COUNTEREXAMPLE
            )
            failed = next(
                (
                    item
                    for item in results
                    if item.status is not EngineeringCheckStatus.PASSED
                ),
                None,
            )
            failure_reason = (
                None
                if failed is None
                else f"check failed: {failed.name} ({failed.status.value})"
            )
        diff_sha256 = self.repository.diff_hash(
            worktree,
            self.contract.base_commit or "HEAD",
        )
        updated = record.model_copy(
            update={
                "commit": commit,
                "status": status,
                "changed_paths": relevant,
                "diff_sha256": diff_sha256,
                "checks": results,
                "failure_reason": failure_reason,
                "validated_at": utc_now(),
            }
        )
        self._write_patch(updated)
        _write_json(
            self.output / EVIDENCE_DIRECTORY / f"{record.patch_id}.json",
            {
                "schema_version": ENGINEERING_SCHEMA_VERSION,
                "campaign_id": self.contract.campaign_id,
                "contract_sha256": self.contract_hash,
                "patch": updated.model_dump(mode="json"),
            },
        )
        return updated

    def adjudicate_patch(
        self,
        patch_id: str,
        holdout: EngineeringHoldoutContract,
        *,
        reviewer: str = "simjecture-diff-judge/v1",
    ) -> EngineeringAdjudicationRecord:
        """Run withheld checks and an independent diff review exactly once."""

        record = self._load_patch(patch_id)
        adjudication_path = self._adjudication_path(record.patch_id)
        if adjudication_path.exists():
            raise EngineeringError(
                f"patch {record.patch_id!r} already has an adjudication record"
            )
        if record.status is not EngineeringPatchStatus.VALIDATED:
            raise EngineeringError(
                f"patch {patch_id!r} must pass visible checks before adjudication; "
                f"current status is {record.status.value}"
            )
        self._assert_patch_identity(record)
        if holdout.campaign_id != self.contract.campaign_id:
            raise EngineeringError(
                "holdout campaign_id does not match the engineering campaign"
            )
        holdout_repository = Path(holdout.repository).expanduser().resolve()
        if holdout_repository != self.repository.root:
            raise EngineeringError(
                "holdout repository does not match the frozen campaign repository"
            )
        if holdout.base_commit != self.contract.base_commit:
            raise EngineeringError(
                "holdout base_commit does not match the frozen campaign base commit"
            )
        holdout_hash = _sha256(_canonical_json(holdout.model_dump(mode="json")))
        diff_review = EngineeringDiffJudge.review(
            record,
            contract=self.contract,
            repository=self.repository,
            reviewer=reviewer,
        )
        checks: tuple[EngineeringCheckResult, ...] = ()
        status: EngineeringAdjudicationStatus
        failure_reason: str | None
        if diff_review.status is EngineeringDiffReviewStatus.REJECTED:
            status = EngineeringAdjudicationStatus.REJECTED
            failure_reason = "; ".join(diff_review.violations)
        else:
            worktree = self._assert_patch_identity(record)
            checks = tuple(
                _check_result(
                    check,
                    worktree=worktree,
                    max_output_chars=holdout.max_output_chars,
                )
                for check in holdout.checks
            )
            # A holdout is an observer, not an editor. Re-review after it runs
            # so a check cannot silently commit or modify the candidate.
            diff_review = EngineeringDiffJudge.review(
                record,
                contract=self.contract,
                repository=self.repository,
                reviewer=reviewer,
            )
            failed = next(
                (
                    item
                    for item in checks
                    if item.status is not EngineeringCheckStatus.PASSED
                ),
                None,
            )
            if diff_review.status is EngineeringDiffReviewStatus.REJECTED:
                status = EngineeringAdjudicationStatus.REJECTED
                failure_reason = "; ".join(diff_review.violations)
            elif failed is not None:
                status = EngineeringAdjudicationStatus.COUNTEREXAMPLE
                failure_reason = f"holdout check failed: {failed.name} ({failed.status.value})"
            else:
                status = EngineeringAdjudicationStatus.ACCEPTED
                failure_reason = None
        patch_status = {
            EngineeringAdjudicationStatus.ACCEPTED: EngineeringPatchStatus.ACCEPTED,
            EngineeringAdjudicationStatus.COUNTEREXAMPLE: (
                EngineeringPatchStatus.COUNTEREXAMPLE
            ),
            EngineeringAdjudicationStatus.REJECTED: EngineeringPatchStatus.REJECTED,
        }[status]
        self._write_patch(
            record.model_copy(
                update={
                    "status": patch_status,
                    "failure_reason": failure_reason,
                }
            )
        )
        adjudication = EngineeringAdjudicationRecord(
            campaign_id=self.contract.campaign_id,
            patch_id=record.patch_id,
            patch_commit=record.commit or "",
            holdout_id=holdout.holdout_id,
            holdout_contract_sha256=holdout_hash,
            holdout_base_commit=holdout.base_commit,
            diff_review=diff_review,
            checks=checks,
            status=status,
            failure_reason=failure_reason,
            reviewer=reviewer,
        )
        _write_json(adjudication_path, adjudication.model_dump(mode="json"))
        _write_json(
            self.output / EVIDENCE_DIRECTORY / f"{record.patch_id}-adjudication.json",
            {
                "schema_version": ENGINEERING_SCHEMA_VERSION,
                "campaign_id": self.contract.campaign_id,
                "contract_sha256": self.contract_hash,
                "adjudication": adjudication.model_dump(mode="json"),
            },
        )
        return adjudication

    def status(self) -> dict[str, Any]:
        records = [
            EngineeringPatchRecord.model_validate(_read_json(path))
            for path in sorted((self.output / PATCH_DIRECTORY).glob("*.json"))
        ]
        commission = None
        commission_path = self.output / "commission.json"
        if commission_path.exists():
            commission = _read_json(commission_path)
        adjudications = [
            EngineeringAdjudicationRecord.model_validate(_read_json(path))
            for path in sorted(
                (self.output / ADJUDICATION_DIRECTORY).glob("*.json")
            )
        ]
        return {
            "campaign_id": self.contract.campaign_id,
            "goal": self.contract.goal,
            "repository": self.contract.repository,
            "base_commit": self.contract.base_commit,
            "contract_sha256": self.contract_hash,
            "commission": commission,
            "patches": [record.model_dump(mode="json") for record in records],
            "adjudications": [record.model_dump(mode="json") for record in adjudications],
        }
