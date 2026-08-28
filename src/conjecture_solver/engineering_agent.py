"""Host-controlled model loop for software-engineering campaigns.

The model proposes edits; it never receives a write-capable repository tool.
The host applies only typed, path-checked edits in a disposable worktree and
then delegates acceptance to the deterministic engineering campaign.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import time
from collections.abc import Mapping
from contextlib import suppress
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from .engineering import (
    EngineeringAdjudicationStatus,
    EngineeringCampaign,
    EngineeringError,
    EngineeringHoldoutContract,
    EngineeringPatchRecord,
    EngineeringPatchStatus,
    _generated_path,
    _matches_path,
    _write_json,
)
from .llm import ModelRoute
from .models import StrictModel, utc_now

ENGINEERING_AGENT_SCHEMA_VERSION = "0.1.0"
AGENT_REPORT_FILE = "agent.json"


class EngineeringEditOperation(StrEnum):
    WRITE = "write"
    REPLACE = "replace"


class EngineeringFileEdit(StrictModel):
    """One text edit admitted into a candidate worktree."""

    # File contents and replacement anchors are byte-significant; the shared
    # StrictModel's user-facing whitespace stripping must not touch them.
    model_config = ConfigDict(str_strip_whitespace=False)
    schema_version: Literal["0.1.0"] = ENGINEERING_AGENT_SCHEMA_VERSION
    operation: EngineeringEditOperation = EngineeringEditOperation.WRITE
    path: str = Field(min_length=1)
    content: str
    expected_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        description="Hash of the existing file bytes, required for overwrites.",
    )
    old_text: str | None = None

    @model_validator(mode="after")
    def validate_edit(self) -> EngineeringFileEdit:
        path = PurePosixPath(self.path)
        if (
            not self.path
            or self.path in {".", ".."}
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in self.path
            or "\x00" in self.path
        ):
            raise ValueError("engineering edit path must be a safe POSIX-relative path")
        if "\x00" in self.content:
            raise ValueError("engineering edit content cannot contain NUL bytes")
        if self.operation is EngineeringEditOperation.REPLACE:
            if not self.old_text:
                raise ValueError("replace edits require non-empty old_text")
            if "\x00" in self.old_text:
                raise ValueError("engineering edit old_text cannot contain NUL bytes")
        elif self.old_text is not None:
            raise ValueError("write edits must not provide old_text")
        return self


class EngineeringPatchProposal(StrictModel):
    """The only model output accepted by the automatic engineering loop."""

    schema_version: Literal["0.1.0"] = ENGINEERING_AGENT_SCHEMA_VERSION
    diagnosis: str = Field(min_length=8, max_length=20_000)
    prediction: str = Field(min_length=8, max_length=20_000)
    commit_message: str = Field(min_length=3, max_length=200)
    edits: tuple[EngineeringFileEdit, ...] = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def unique_paths(self) -> EngineeringPatchProposal:
        paths = [edit.path for edit in self.edits]
        if len(paths) != len(set(paths)):
            raise ValueError("a patch proposal must contain at most one edit per path")
        return self


class EngineeringAgentAttemptStatus(StrEnum):
    VALIDATED = "validated"
    ACCEPTED = "accepted"
    COUNTEREXAMPLE = "counterexample"
    REJECTED = "rejected"
    PROPOSAL_ERROR = "proposal_error"
    PROVIDER_ERROR = "provider_error"


class EngineeringAgentStatus(StrEnum):
    RUNNING = "running"
    VALIDATED = "validated"
    ACCEPTED = "accepted"
    EXHAUSTED = "exhausted"
    PROVIDER_FAILED = "provider_failed"
    REJECTED = "rejected"


class EngineeringAgentAttempt(StrictModel):
    """Durable provenance for one model proposal or host rejection."""

    schema_version: Literal["0.1.0"] = ENGINEERING_AGENT_SCHEMA_VERSION
    attempt: int = Field(ge=1)
    patch_id: str | None = None
    status: EngineeringAgentAttemptStatus
    model: str | None = None
    route: str | None = None
    request_id: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    prompt_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    response_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class EngineeringAgentReport(StrictModel):
    """Durable summary of the host-controlled automatic coding loop."""

    schema_version: Literal["0.1.0"] = ENGINEERING_AGENT_SCHEMA_VERSION
    campaign_id: str
    status: EngineeringAgentStatus
    attempts: tuple[EngineeringAgentAttempt, ...] = ()
    selected_patch_id: str | None = None
    holdout_contract_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    detail: str
    started_at: datetime
    finished_at: datetime = Field(default_factory=utc_now)
    elapsed_wall_seconds: float = Field(ge=0)


class EngineeringAgentConfig(StrictModel):
    """Safety and prompt-size limits for the model-facing loop."""

    max_attempts: int | None = Field(default=None, ge=1, le=10_000)
    max_wall_seconds: float = Field(default=21_600.0, gt=0)
    max_snapshot_chars: int = Field(default=120_000, ge=1_000, le=2_000_000)
    max_edit_chars: int = Field(default=1_000_000, ge=1_000, le=10_000_000)
    max_model_tokens: int | None = Field(default=None, ge=1, le=2_000_000)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _holdout_hash(holdout: EngineeringHoldoutContract | None) -> str | None:
    if holdout is None:
        return None
    encoded = json.dumps(
        holdout.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _parse_proposal_object(content: str) -> EngineeringPatchProposal:
    stripped = content.strip()
    fence = chr(96) * 3
    if stripped.startswith(fence) and stripped.endswith(fence):
        lines = stripped.splitlines()
        stripped = "\n".join(lines[1:-1]).strip()
    try:
        return EngineeringPatchProposal.model_validate_json(stripped)
    except ValueError as original_error:
        decoder = json.JSONDecoder()
        candidates: dict[str, EngineeringPatchProposal] = {}
        for index, character in enumerate(stripped):
            if character != "{":
                continue
            try:
                value, _end = decoder.raw_decode(stripped[index:])
                proposal = EngineeringPatchProposal.model_validate(value)
            except ValueError:
                continue
            candidates[proposal.model_dump_json()] = proposal
        if len(candidates) == 1:
            return next(iter(candidates.values()))
        if len(candidates) > 1:
            raise ValueError(
                "model response contains multiple distinct engineering proposals"
            ) from original_error
        raise original_error


class EngineeringEditApplier:
    """Apply a proposal only after validating every edit against the contract."""

    @staticmethod
    def _target(worktree: Path, edit: EngineeringFileEdit) -> Path:
        root = worktree.resolve()
        unresolved = worktree / PurePosixPath(edit.path)
        if unresolved.is_symlink():
            raise EngineeringError(f"refusing to edit symlink path: {edit.path}")
        try:
            target = unresolved.resolve()
        except RuntimeError as error:
            raise EngineeringError(
                f"unable to resolve edit path safely: {edit.path}"
            ) from error
        if not target.is_relative_to(root):
            raise EngineeringError(f"edit path escapes the patch worktree: {edit.path}")
        for parent in unresolved.parents:
            if parent == worktree:
                break
            if parent.is_symlink():
                raise EngineeringError(f"refusing to traverse symlink path: {edit.path}")
        return target

    @classmethod
    def apply(
        cls,
        campaign: EngineeringCampaign,
        patch: EngineeringPatchRecord,
        proposal: EngineeringPatchProposal,
        *,
        max_edit_chars: int,
    ) -> tuple[str, ...]:
        worktree = campaign._assert_patch_identity(patch)
        if not worktree.is_dir():
            raise EngineeringError(f"patch worktree is unavailable: {worktree}")
        if sum(len(edit.content) for edit in proposal.edits) > max_edit_chars:
            raise EngineeringError("patch proposal exceeds max_edit_chars")
        targets: dict[Path, bytes] = {}
        changed_paths: list[str] = []
        for edit in proposal.edits:
            if _generated_path(edit.path):
                raise EngineeringError(f"generated path is not editable: {edit.path}")
            if _matches_path(edit.path, campaign.contract.protected_paths):
                raise EngineeringError(f"protected path in patch proposal: {edit.path}")
            if not _matches_path(edit.path, campaign.contract.editable_paths):
                raise EngineeringError(
                    f"path outside editable policy in patch proposal: {edit.path}"
                )
            target = cls._target(worktree, edit)
            if target.exists() and not target.is_file():
                raise EngineeringError(f"edit target is not a regular file: {edit.path}")
            current_bytes: bytes | None = None
            current_text: str | None = None
            if target.exists():
                current_bytes = target.read_bytes()
                try:
                    current_text = current_bytes.decode("utf-8")
                except UnicodeDecodeError as error:
                    raise EngineeringError(
                        f"edit target is not UTF-8 text: {edit.path}"
                    ) from error
                current_hash = hashlib.sha256(current_bytes).hexdigest()
                if edit.operation is EngineeringEditOperation.WRITE:
                    if edit.expected_sha256 is None:
                        raise EngineeringError(
                            f"overwriting an existing file requires expected_sha256: {edit.path}"
                        )
                    if current_hash != edit.expected_sha256:
                        raise EngineeringError(
                            f"edit target hash changed since proposal: {edit.path}"
                        )
                elif (
                    edit.expected_sha256 is not None
                    and current_hash != edit.expected_sha256
                ):
                    raise EngineeringError(
                        f"edit target hash changed since proposal: {edit.path}"
                    )
            elif edit.expected_sha256 is not None:
                raise EngineeringError(
                    f"new edit target must not provide expected_sha256: {edit.path}"
                )
            if edit.operation is EngineeringEditOperation.WRITE:
                updated_text = edit.content
            else:
                if current_text is None:
                    raise EngineeringError(
                        f"replace target does not exist: {edit.path}"
                    )
                assert edit.old_text is not None
                occurrences = current_text.count(edit.old_text)
                if occurrences != 1:
                    raise EngineeringError(
                        f"replace requires exactly one old_text occurrence in {edit.path}; "
                        f"found {occurrences}"
                    )
                updated_text = current_text.replace(edit.old_text, edit.content, 1)
            updated = updated_text.encode("utf-8")
            if len(updated) > max_edit_chars:
                raise EngineeringError(f"edited file exceeds max_edit_chars: {edit.path}")
            targets[target] = updated
            changed_paths.append(edit.path)

        for target, content in targets.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            existing_mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else None
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{target.name}.simjecture-",
                dir=str(target.parent),
            )
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    if existing_mode is not None:
                        os.fchmod(stream.fileno(), existing_mode)
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary_name, target)
            except Exception:
                with suppress(FileNotFoundError):
                    os.unlink(temporary_name)
                raise
        return tuple(sorted(changed_paths))


class EngineeringAgentRunner:
    """Iteratively propose, validate, and refine patches in a campaign."""

    def __init__(
        self,
        campaign: EngineeringCampaign,
        completion_client: Any,
        *,
        config: EngineeringAgentConfig | None = None,
        route: ModelRoute = ModelRoute.DEFAULT,
        escalation_reason: str | None = None,
    ) -> None:
        self.campaign = campaign
        self.completion_client = completion_client
        self.config = config or EngineeringAgentConfig()
        self.route = route
        self.escalation_reason = escalation_reason
        self.report_path = campaign.output / AGENT_REPORT_FILE

    def _next_patch_id(self) -> str:
        index = len(tuple((self.campaign.output / "patches").glob("*.json"))) + 1
        while (self.campaign.output / "patches" / f"patch-{index:03d}.json").exists():
            index += 1
        return f"patch-{index:03d}"

    def _messages(
        self,
        *,
        parent_commit: str,
        snapshot: Mapping[str, str],
        snapshot_truncated: bool,
        feedback: tuple[str, ...],
    ) -> list[dict[str, str]]:
        system = (
            "You are the implementation scientist in an evidence-governed coding "
            "campaign. Return exactly one JSON object matching the supplied "
            "EngineeringPatchProposal schema. Propose a falsifiable diagnosis and "
            "prediction, then minimal text edits only in editable_paths. Do not "
            "modify tests, CI, lockfiles, or other protected paths. The visible "
            "checks are bounded evidence, not proof of general correctness; an "
            "unseen host holdout may reject an overfit patch. Do not return private "
            "chain-of-thought or Markdown outside the JSON object."
        )
        user = {
            "goal": self.campaign.contract.goal,
            "base_commit_for_this_attempt": parent_commit,
            "editable_paths": self.campaign.contract.editable_paths,
            "protected_paths": self.campaign.contract.protected_paths,
            "visible_checks": [
                {
                    "name": check.name,
                    "stage": check.stage.value,
                    "command": check.command,
                }
                for check in self.campaign.contract.checks
            ],
            "source_snapshot": dict(snapshot),
            "source_snapshot_sha256": {
                path: _sha256_text(content)
                for path, content in snapshot.items()
            },
            "source_snapshot_truncated": snapshot_truncated,
            "prior_feedback": feedback,
            "proposal_schema": EngineeringPatchProposal.model_json_schema(),
        }
        return [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": json.dumps(user, ensure_ascii=False, sort_keys=True),
            },
        ]

    def _persist(
        self,
        *,
        status: EngineeringAgentStatus,
        attempts: list[EngineeringAgentAttempt],
        selected_patch_id: str | None,
        holdout_contract_sha256: str | None,
        detail: str,
        started_at: datetime,
        started_monotonic: float,
    ) -> EngineeringAgentReport:
        report = EngineeringAgentReport(
            campaign_id=self.campaign.contract.campaign_id,
            status=status,
            attempts=tuple(attempts),
            selected_patch_id=selected_patch_id,
            holdout_contract_sha256=holdout_contract_sha256,
            detail=detail,
            started_at=started_at,
            elapsed_wall_seconds=max(0.0, time.monotonic() - started_monotonic),
        )
        _write_json(self.report_path, report.model_dump(mode="json"))
        return report

    def _existing_report(self) -> EngineeringAgentReport | None:
        if not self.report_path.exists():
            return None
        try:
            payload = json.loads(self.report_path.read_text(encoding="utf-8"))
            report = EngineeringAgentReport.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise EngineeringError(
                f"invalid engineering agent report: {self.report_path}"
            ) from error
        if report.status is EngineeringAgentStatus.RUNNING:
            raise EngineeringError(
                "an engineering agent report is already marked running; "
                "inspect the campaign before starting another loop"
            )
        return report

    def run(
        self,
        *,
        holdout: EngineeringHoldoutContract | None = None,
    ) -> EngineeringAgentReport:
        existing = self._existing_report()
        holdout_hash = _holdout_hash(holdout)
        if existing is not None:
            if existing.campaign_id != self.campaign.contract.campaign_id:
                raise EngineeringError("engineering agent report belongs to another campaign")
            if existing.holdout_contract_sha256 != holdout_hash:
                raise EngineeringError(
                    "engineering agent report was created with a different holdout contract"
                )
            return existing
        started_at = utc_now()
        started_monotonic = time.monotonic()
        attempts: list[EngineeringAgentAttempt] = []
        feedback: list[str] = []
        parent_patch_id: str | None = None
        last_patch_id: str | None = None
        max_attempts = self.config.max_attempts or self.campaign.contract.max_patch_attempts
        model_turn_limit = max(2, max_attempts * 2)
        turns = 0
        while len([attempt for attempt in attempts if attempt.patch_id is not None]) < max_attempts:
            if turns >= model_turn_limit:
                break
            if time.monotonic() - started_monotonic >= self.config.max_wall_seconds:
                break
            turns += 1
            if parent_patch_id is None:
                parent_commit = self.campaign.contract.base_commit or "HEAD"
            else:
                parent = self.campaign._load_patch(parent_patch_id)
                parent_commit = parent.commit or self.campaign.contract.base_commit or "HEAD"
            snapshot, snapshot_truncated = self.campaign.repository.text_snapshot(
                parent_commit,
                self.campaign.contract.editable_paths,
                max_chars=self.config.max_snapshot_chars,
            )
            messages = self._messages(
                parent_commit=parent_commit,
                snapshot=snapshot,
                snapshot_truncated=snapshot_truncated,
                feedback=tuple(feedback[-8:]),
            )
            prompt_hash = _sha256_text(json.dumps(messages, sort_keys=True))
            try:
                result = self.completion_client.complete(
                    messages,
                    route=self.route,
                    escalation_reason=self.escalation_reason,
                    max_tokens=self.config.max_model_tokens,
                    temperature=0.0,
                )
            except Exception as error:
                attempts.append(
                    EngineeringAgentAttempt(
                        attempt=turns,
                        status=EngineeringAgentAttemptStatus.PROVIDER_ERROR,
                        prompt_sha256=prompt_hash,
                        failure_reason=f"{type(error).__name__}: {error}",
                    )
                )
                return self._persist(
                    status=EngineeringAgentStatus.PROVIDER_FAILED,
                    attempts=attempts,
                    selected_patch_id=last_patch_id,
                    holdout_contract_sha256=holdout_hash,
                    detail="model completion failed before a safe patch was created",
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                )
            response_hash = _sha256_text(result.content)
            try:
                if result.finish_reason != "stop":
                    raise ValueError(
                        f"model completion ended with {result.finish_reason!r}"
                    )
                proposal = _parse_proposal_object(result.content)
            except ValueError as error:
                attempts.append(
                    EngineeringAgentAttempt(
                        attempt=turns,
                        status=EngineeringAgentAttemptStatus.PROPOSAL_ERROR,
                        model=result.model,
                        route=result.route.value,
                        request_id=result.request_id,
                        usage=result.usage,
                        prompt_sha256=prompt_hash,
                        response_sha256=response_hash,
                        failure_reason=str(error),
                    )
                )
                feedback.append(
                    "The previous response was not an admissible single JSON patch proposal. "
                    "Return only the requested schema."
                )
                continue
            patch_id = self._next_patch_id()
            patch: EngineeringPatchRecord | None = None
            try:
                patch = self.campaign.create_patch(
                    patch_id,
                    diagnosis=proposal.diagnosis,
                    prediction=proposal.prediction,
                    parent_patch_id=parent_patch_id,
                )
                last_patch_id = patch_id
                EngineeringEditApplier.apply(
                    self.campaign,
                    patch,
                    proposal,
                    max_edit_chars=self.config.max_edit_chars,
                )
                validated = self.campaign.validate_patch(
                    patch_id,
                    commit_message=proposal.commit_message,
                )
            except (EngineeringError, OSError, UnicodeError, ValueError) as error:
                if patch is not None:
                    with suppress(EngineeringError):
                        self.campaign.reject_patch(
                            patch_id,
                            reason=f"host rejected model proposal: {error}",
                        )
                attempts.append(
                    EngineeringAgentAttempt(
                        attempt=turns,
                        patch_id=patch_id if patch is not None else None,
                        status=EngineeringAgentAttemptStatus.REJECTED,
                        model=result.model,
                        route=result.route.value,
                        request_id=result.request_id,
                        usage=result.usage,
                        prompt_sha256=prompt_hash,
                        response_sha256=response_hash,
                        failure_reason=str(error),
                    )
                )
                feedback.append(
                    f"Host rejected {patch_id}: {error}. Keep the next proposal within "
                    "the editable path and file-integrity contract."
                )
                continue
            attempt_status = {
                EngineeringPatchStatus.VALIDATED: EngineeringAgentAttemptStatus.VALIDATED,
                EngineeringPatchStatus.COUNTEREXAMPLE: (
                    EngineeringAgentAttemptStatus.COUNTEREXAMPLE
                ),
                EngineeringPatchStatus.REJECTED: EngineeringAgentAttemptStatus.REJECTED,
            }[validated.status]
            adjudication = None
            if validated.status is EngineeringPatchStatus.VALIDATED and holdout is not None:
                adjudication = self.campaign.adjudicate_patch(patch_id, holdout)
                attempt_status = {
                    EngineeringAdjudicationStatus.ACCEPTED: EngineeringAgentAttemptStatus.ACCEPTED,
                    EngineeringAdjudicationStatus.COUNTEREXAMPLE: (
                        EngineeringAgentAttemptStatus.COUNTEREXAMPLE
                    ),
                    EngineeringAdjudicationStatus.REJECTED: EngineeringAgentAttemptStatus.REJECTED,
                }[adjudication.status]
            attempts.append(
                EngineeringAgentAttempt(
                    attempt=turns,
                    patch_id=patch_id,
                    status=attempt_status,
                    model=result.model,
                    route=result.route.value,
                    request_id=result.request_id,
                    usage=result.usage,
                    prompt_sha256=prompt_hash,
                    response_sha256=response_hash,
                    failure_reason=(
                        (
                            "host holdout rejected candidate; details are withheld"
                            if adjudication.status
                            is EngineeringAdjudicationStatus.COUNTEREXAMPLE
                            else adjudication.failure_reason
                        )
                        if adjudication is not None
                        else validated.failure_reason
                    ),
                )
            )
            if adjudication is not None:
                if adjudication.status is EngineeringAdjudicationStatus.ACCEPTED:
                    return self._persist(
                        status=EngineeringAgentStatus.ACCEPTED,
                        attempts=attempts,
                        selected_patch_id=patch_id,
                        holdout_contract_sha256=holdout_hash,
                        detail="patch passed visible checks, the external holdout, and diff review",
                        started_at=started_at,
                        started_monotonic=started_monotonic,
                    )
                if adjudication.status is EngineeringAdjudicationStatus.REJECTED:
                    return self._persist(
                        status=EngineeringAgentStatus.REJECTED,
                        attempts=attempts,
                        selected_patch_id=patch_id,
                        holdout_contract_sha256=holdout_hash,
                        detail=adjudication.failure_reason or "host rejected the candidate",
                        started_at=started_at,
                        started_monotonic=started_monotonic,
                    )
                parent_patch_id = patch_id
                feedback.append(
                    "The host holdout found a counterexample. Its details remain hidden; "
                    "form a strictly better repair from the recorded candidate."
                )
                continue
            if validated.status is EngineeringPatchStatus.VALIDATED:
                detail = (
                    "patch passed visible checks; host adjudication is still required"
                    if holdout is None
                    else "patch validated"
                )
                return self._persist(
                    status=EngineeringAgentStatus.VALIDATED,
                    attempts=attempts,
                    selected_patch_id=patch_id,
                    holdout_contract_sha256=holdout_hash,
                    detail=detail,
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                )
            if validated.status is EngineeringPatchStatus.COUNTEREXAMPLE:
                parent_patch_id = patch_id
                feedback.append(
                    f"{patch_id} is a visible-check counterexample: "
                    f"{validated.failure_reason or 'one or more checks failed'}"
                )
            else:
                return self._persist(
                    status=EngineeringAgentStatus.REJECTED,
                    attempts=attempts,
                    selected_patch_id=patch_id,
                    holdout_contract_sha256=holdout_hash,
                    detail=validated.failure_reason or "host rejected the patch",
                    started_at=started_at,
                    started_monotonic=started_monotonic,
                )
        return self._persist(
            status=EngineeringAgentStatus.EXHAUSTED,
            attempts=attempts,
            selected_patch_id=last_patch_id,
            holdout_contract_sha256=holdout_hash,
            detail=(
                "patch-attempt or model-turn budget exhausted before a validated patch "
                "was produced"
            ),
            started_at=started_at,
            started_monotonic=started_monotonic,
        )
