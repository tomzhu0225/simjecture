"""Domain-neutral working-claim ledger for the natural-language MVP.

This is not a domain-specific daughter schema. Claims are free-text scientific,
instrument, diagnostic, or control statements with lineage and evidence links.
The agent still designs all physics and experiments; the ledger only forces
identity, parent relation, and disposition so audits do not depend on scanning
the full transcript.
"""

from __future__ import annotations

import json
import math
import os
import re
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from pydantic import Field, model_validator

from .models import StrictModel

CLAIM_ID_PATTERN = re.compile(r"^claim_[a-z0-9_]+$")
ROOT_CLAIM_ID = "claim_root"


class ClaimKind(StrEnum):
    SCIENTIFIC = "scientific"
    INSTRUMENT = "instrument"
    DIAGNOSTIC = "diagnostic"
    CONTROL = "control"


class ClaimRelation(StrEnum):
    ROOT = "root"
    REFINES = "refines"
    ALTERNATE = "alternate"
    DIAGNOSTIC_OF = "diagnostic_of"
    INSTRUMENT_OF = "instrument_of"
    CONTROL_FOR = "control_for"
    SUCCEEDS = "succeeds"


class ClaimDisposition(StrEnum):
    OPEN = "open"
    SUPPORTED = "supported"
    WEAKENED = "weakened"
    FALSIFIED = "falsified"
    SUPERSEDED = "superseded"
    UNRESOLVED = "unresolved"
    INSTRUMENT_LIMITED = "instrument_limited"


class CommissioningAspect(StrEnum):
    """Domain-neutral aspects required before a scientific capability run."""

    INTERFACE = "interface"
    REPRESENTATION = "representation"
    PHYSICS_CONTROLS = "physics_controls"
    BOUNDARIES = "boundaries"
    DIAGNOSTICS = "diagnostics"
    NUMERICAL_REGIME = "numerical_regime"


REQUIRED_SCIENTIFIC_COMMISSIONING_ASPECTS = frozenset(
    {
        CommissioningAspect.REPRESENTATION,
        CommissioningAspect.PHYSICS_CONTROLS,
        CommissioningAspect.BOUNDARIES,
        CommissioningAspect.DIAGNOSTICS,
        CommissioningAspect.NUMERICAL_REGIME,
    }
)


def _validation_scalars_equal(actual: Any, expected: Any) -> bool:
    """Compare JSON scalars without treating booleans as numeric values."""

    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return (
            math.isfinite(actual)
            and math.isfinite(expected)
            and actual == expected
        )
    return type(actual) is type(expected) and actual == expected


class ClaimEvidenceValidationCheck(StrictModel):
    """One exact assertion over a JSON evidence summary."""

    aspect: CommissioningAspect | None = Field(
        default=None,
        description=(
            "Commissioning aspect tested by this assertion. Instrument evidence "
            "used to unlock scientific capability execution must cover every required "
            "aspect in one prospectively registered contract."
        ),
    )
    json_path: str = Field(
        pattern=r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$",
        description="Dot-separated object keys; array indexing is deliberately unsupported",
    )
    expected_value: str | int | float | bool | None


class ClaimEvidenceValidationResult(StrictModel):
    """Deterministic evaluation of one prospective JSON assertion."""

    aspect: CommissioningAspect | None = None
    json_path: str
    expected_value: str | int | float | bool | None
    actual_value: str | int | float | bool | None = None
    passed: bool
    error: str | None = None


class ClaimExecutionBinding(StrictModel):
    """Prospective command identity for commissioning and later science runs."""

    capability: str = Field(pattern=r"^[a-z][a-z0-9_.-]*$")
    program_path: str = Field(min_length=1)
    program_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        description=(
            "Runner-attested source identity sealed before the first bound "
            "capability execution"
        ),
    )
    commissioning_argv: tuple[str, ...] = Field(min_length=1)
    allowed_scientific_argv: tuple[tuple[str, ...], ...] = ()

    @model_validator(mode="after")
    def paths_and_commands_are_consistent(self) -> ClaimExecutionBinding:
        path = PurePosixPath(self.program_path)
        if (
            path.is_absolute()
            or self.program_path in {"", "."}
            or ".." in path.parts
            or "\x00" in self.program_path
        ):
            raise ValueError("execution binding program_path must stay in the workspace")
        commands = (self.commissioning_argv, *self.allowed_scientific_argv)
        for argv in commands:
            if not argv:
                raise ValueError("execution binding commands cannot be empty")
            if argv[0] != self.program_path:
                raise ValueError(
                    "every bound command must use program_path as argv[0]"
                )
            if any("\x00" in item for item in argv):
                raise ValueError("execution binding arguments cannot contain NUL bytes")
        if len(set(self.allowed_scientific_argv)) != len(
            self.allowed_scientific_argv
        ):
            raise ValueError("allowed_scientific_argv cannot contain duplicates")
        return self

    def allows_evidence_argv(self, argv: tuple[str, ...], *, instrument: bool) -> bool:
        """Return whether a prospectively bound command may produce claim evidence."""

        if instrument:
            return argv == self.commissioning_argv
        return argv in self.allowed_scientific_argv


class ClaimEvidenceContract(StrictModel):
    """Prospective, domain-neutral rule for interpreting evidence for one claim."""

    version: int = Field(ge=1)
    observable: str = Field(min_length=8)
    expected_outcomes: str = Field(min_length=8)
    decision_rule: str = Field(min_length=8)
    required_observation: str = Field(min_length=8)
    uncertainty_criterion: str = Field(min_length=8)
    inconclusive_conditions: str = Field(min_length=8)
    validation_checks: tuple[ClaimEvidenceValidationCheck, ...] = ()
    execution_binding: ClaimExecutionBinding | None = None
    additional_execution_bindings: tuple[ClaimExecutionBinding, ...] = ()
    registered_iteration: int = Field(ge=0)

    @model_validator(mode="after")
    def execution_pipeline_is_unambiguous(self) -> ClaimEvidenceContract:
        if self.additional_execution_bindings and self.execution_binding is None:
            raise ValueError(
                "additional_execution_bindings require a primary execution_binding"
            )
        seen_commands: set[tuple[str, tuple[str, ...]]] = set()
        for binding in self.all_execution_bindings():
            for argv in binding.allowed_scientific_argv:
                identity = (binding.capability, argv)
                if identity in seen_commands:
                    raise ValueError(
                        "scientific execution commands cannot be duplicated across "
                        "execution bindings"
                    )
                seen_commands.add(identity)
        return self

    def all_execution_bindings(self) -> tuple[ClaimExecutionBinding, ...]:
        """Return the primary and any prospectively declared pipeline stages."""

        if self.execution_binding is None:
            return ()
        return (self.execution_binding, *self.additional_execution_bindings)


class ClaimEvidenceProvenance(StrictModel):
    """Immutable identity and generating-action metadata for a workspace artifact."""

    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=0)
    tracked: bool
    generated_iteration: int | None = Field(default=None, ge=0)
    action: str | None = None
    action_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    command_argv: tuple[str, ...] = ()
    capability: str | None = None
    program_path: str | None = None
    program_sha256: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
    )
    execution_succeeded: bool | None = None
    execution_returncode: int | None = None
    execution_timed_out: bool | None = None
    execution_workspace_exceeded: bool | None = None
    execution_stage: Literal["workbench", "evidence"] | None = None
    evidence_eligible: bool = True


class ClaimEvidenceLink(StrictModel):
    path: str = Field(min_length=1)
    note: str = Field(min_length=1)
    iteration: int = Field(ge=0)
    contract_version: int | None = Field(default=None, ge=1)
    observation_sufficient: bool | None = None
    observation_note: str | None = None
    validation_passed: bool | None = None
    validation_results: tuple[ClaimEvidenceValidationResult, ...] = ()
    commissioning_claim_id: str | None = Field(
        default=None,
        pattern=r"^claim_[a-z0-9_]+$",
    )
    provenance: ClaimEvidenceProvenance | None = None


class MVPClaim(StrictModel):
    id: str = Field(pattern=r"^claim_[a-z0-9_]+$")
    statement: str = Field(min_length=8)
    kind: ClaimKind
    relation: ClaimRelation
    parent_id: str | None = None
    status: ClaimDisposition = ClaimDisposition.OPEN
    rationale: str = Field(min_length=8)
    evidence_contracts: tuple[ClaimEvidenceContract, ...] = ()
    evidence: tuple[ClaimEvidenceLink, ...] = ()
    closed_reason: str | None = None
    created_iteration: int = Field(ge=0)
    updated_iteration: int = Field(ge=0)

    @model_validator(mode="after")
    def relation_and_parent_are_consistent(self) -> MVPClaim:
        if self.relation == ClaimRelation.ROOT:
            if self.id != ROOT_CLAIM_ID:
                raise ValueError("only claim_root may use relation=root")
            if self.parent_id is not None:
                raise ValueError("root claim cannot have a parent_id")
        else:
            if self.parent_id is None:
                raise ValueError("non-root claims require parent_id")
            if not CLAIM_ID_PATTERN.match(self.parent_id):
                raise ValueError("parent_id must match claim_[a-z0-9_]+")
        if self.status != ClaimDisposition.OPEN and (
            self.closed_reason is None or not self.closed_reason.strip()
        ):
            raise ValueError("closed claims require closed_reason")
        if self.status == ClaimDisposition.OPEN and self.closed_reason is not None:
            raise ValueError("open claims cannot carry closed_reason")
        return self


class MVPClaimLedger(StrictModel):
    schema_version: Literal[
        "0.1.0",
        "0.2.0",
        "0.3.0",
        "0.4.0",
        "0.5.0",
        "0.6.0",
        "0.7.0",
        "0.8.0",
    ] = (
        "0.8.0"
    )
    root_hypothesis: str = Field(min_length=1)
    claims: tuple[MVPClaim, ...] = ()

    def by_id(self) -> dict[str, MVPClaim]:
        return {claim.id: claim for claim in self.claims}

    def open_claims(self) -> tuple[MVPClaim, ...]:
        return tuple(
            claim for claim in self.claims if claim.status == ClaimDisposition.OPEN
        )

    def compact_summary(self, *, max_claims: int = 24) -> dict[str, Any]:
        """Short ledger view safe to inject into tool results / context."""
        ordered = sorted(self.claims, key=lambda claim: claim.updated_iteration)
        tail = ordered[-max_claims:]
        return {
            "schema_version": self.schema_version,
            "root_hypothesis": self.root_hypothesis,
            "claim_count": len(self.claims),
            "open_count": len(self.open_claims()),
            "claims": [
                {
                    "id": claim.id,
                    "kind": claim.kind.value,
                    "relation": claim.relation.value,
                    "parent_id": claim.parent_id,
                    "status": claim.status.value,
                    "statement": claim.statement,
                    "evidence_contract_count": len(claim.evidence_contracts),
                    "evidence_count": len(claim.evidence),
                }
                for claim in tail
            ],
        }


class MVPClaimLedgerStore:
    """Durable claim ledger beside the MVP report and transcript."""

    def __init__(self, path: str | Path, *, root_hypothesis: str) -> None:
        self.path = Path(path).resolve()
        self.root_hypothesis = root_hypothesis.strip()
        if not self.root_hypothesis:
            raise ValueError("root hypothesis cannot be empty")
        self._ledger = self._load_or_create()

    @property
    def ledger(self) -> MVPClaimLedger:
        return self._ledger

    def _load_or_create(self) -> MVPClaimLedger:
        if self.path.exists():
            ledger = MVPClaimLedger.model_validate_json(self.path.read_text())
            if ledger.root_hypothesis != self.root_hypothesis:
                raise ValueError("claim ledger belongs to a different root hypothesis")
            return ledger
        root = MVPClaim(
            id=ROOT_CLAIM_ID,
            statement=self.root_hypothesis,
            kind=ClaimKind.SCIENTIFIC,
            relation=ClaimRelation.ROOT,
            parent_id=None,
            status=ClaimDisposition.OPEN,
            rationale="Immutable root hypothesis supplied by the campaign operator.",
            evidence_contracts=(),
            evidence=(),
            closed_reason=None,
            created_iteration=0,
            updated_iteration=0,
        )
        ledger = MVPClaimLedger(root_hypothesis=self.root_hypothesis, claims=(root,))
        self._persist(ledger)
        return ledger

    def _persist(self, ledger: MVPClaimLedger) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(ledger.model_dump_json(indent=2) + "\n")
        os.replace(temporary, self.path)

    def _replace_claim(self, claim: MVPClaim) -> MVPClaimLedger:
        claims = [existing for existing in self._ledger.claims if existing.id != claim.id]
        claims.append(claim)
        claims.sort(key=lambda item: (item.created_iteration, item.id))
        self._ledger = MVPClaimLedger(
            root_hypothesis=self.root_hypothesis,
            claims=tuple(claims),
        )
        self._persist(self._ledger)
        return self._ledger

    def register(
        self,
        *,
        claim_id: str,
        statement: str,
        kind: ClaimKind,
        relation: ClaimRelation,
        parent_id: str,
        rationale: str,
        iteration: int,
    ) -> dict[str, Any]:
        claim_id = claim_id.strip().casefold()
        parent_id = parent_id.strip().casefold()
        if relation == ClaimRelation.ROOT:
            raise ValueError("cannot re-register the root claim")
        if claim_id == ROOT_CLAIM_ID:
            raise ValueError("claim_root is reserved")
        if not CLAIM_ID_PATTERN.match(claim_id):
            raise ValueError("claim_id must match claim_[a-z0-9_]+")
        existing = self._ledger.by_id()
        if claim_id in existing:
            raise ValueError(f"claim_id already exists: {claim_id}")
        if parent_id not in existing:
            raise ValueError(f"unknown parent_id: {parent_id}")
        parent = existing[parent_id]
        relation_kinds = {
            ClaimRelation.INSTRUMENT_OF: ClaimKind.INSTRUMENT,
            ClaimRelation.DIAGNOSTIC_OF: ClaimKind.DIAGNOSTIC,
            ClaimRelation.CONTROL_FOR: ClaimKind.CONTROL,
        }
        expected_kind = relation_kinds.get(relation)
        if expected_kind is not None:
            if kind != expected_kind or parent.kind != ClaimKind.SCIENTIFIC:
                if relation == ClaimRelation.CONTROL_FOR:
                    raise ValueError(
                        f"relation={relation.value} requires a "
                        f"{expected_kind.value} claim whose parent is scientific "
                        f"(got kind={kind.value}, parent_kind={parent.kind.value}); "
                        "for non-scientific exact-reuse smokes use control_for "
                        "with parent_id of a scientific claim such as claim_root, "
                        "not an instrument claim"
                    )
                raise ValueError(
                    f"relation={relation.value} requires a {expected_kind.value} "
                    "claim whose parent is scientific"
                )
        elif relation in {ClaimRelation.REFINES, ClaimRelation.ALTERNATE}:
            if kind != ClaimKind.SCIENTIFIC or parent.kind != ClaimKind.SCIENTIFIC:
                raise ValueError(
                    f"relation={relation.value} requires scientific child and parent"
                )
        elif relation == ClaimRelation.SUCCEEDS:
            if kind != parent.kind:
                raise ValueError(
                    "relation=succeeds requires child and predecessor to have the "
                    "same claim kind"
                )
            if parent.status == ClaimDisposition.OPEN:
                raise ValueError(
                    "relation=succeeds requires a closed predecessor claim"
                )
        claim = MVPClaim(
            id=claim_id,
            statement=statement,
            kind=kind,
            relation=relation,
            parent_id=parent_id,
            status=ClaimDisposition.OPEN,
            rationale=rationale,
            evidence_contracts=(),
            evidence=(),
            closed_reason=None,
            created_iteration=iteration,
            updated_iteration=iteration,
        )
        ledger = self._replace_claim(claim)
        return {
            "registered": claim.model_dump(mode="json"),
            "claim_ledger": ledger.compact_summary(),
        }

    def register_evidence_contract(
        self,
        *,
        claim_id: str,
        observable: str,
        expected_outcomes: str,
        decision_rule: str,
        required_observation: str,
        uncertainty_criterion: str,
        inconclusive_conditions: str,
        validation_checks: tuple[ClaimEvidenceValidationCheck, ...] = (),
        execution_binding: ClaimExecutionBinding | None = None,
        additional_execution_bindings: tuple[ClaimExecutionBinding, ...] = (),
        iteration: int,
    ) -> dict[str, Any]:
        claim_id = claim_id.strip().casefold()
        existing = self._ledger.by_id()
        if claim_id not in existing:
            raise ValueError(f"unknown claim_id: {claim_id}")
        claim = existing[claim_id]
        if claim.status != ClaimDisposition.OPEN:
            raise ValueError(f"claim is already closed: {claim_id}")
        declared_aspects = {
            check.aspect for check in validation_checks if check.aspect is not None
        }
        is_complete_instrument_contract = (
            claim.kind == ClaimKind.INSTRUMENT
            and claim.relation == ClaimRelation.INSTRUMENT_OF
            and REQUIRED_SCIENTIFIC_COMMISSIONING_ASPECTS.issubset(
                declared_aspects
            )
        )
        if is_complete_instrument_contract and (
            execution_binding is None
            or not execution_binding.allowed_scientific_argv
        ):
            raise ValueError(
                "complete instrument commissioning requires a prospective "
                "execution_binding with at least one exact allowed_scientific_argv "
                "command"
            )
        if claim.kind == ClaimKind.INSTRUMENT and additional_execution_bindings:
            raise ValueError(
                "instrument claims bind one program; register a separate instrument_of "
                "claim for each additional evidence-pipeline program"
            )
        contract = ClaimEvidenceContract(
            version=len(claim.evidence_contracts) + 1,
            observable=observable,
            expected_outcomes=expected_outcomes,
            decision_rule=decision_rule,
            required_observation=required_observation,
            uncertainty_criterion=uncertainty_criterion,
            inconclusive_conditions=inconclusive_conditions,
            validation_checks=validation_checks,
            execution_binding=execution_binding,
            additional_execution_bindings=additional_execution_bindings,
            registered_iteration=iteration,
        )
        updated = MVPClaim(
            id=claim.id,
            statement=claim.statement,
            kind=claim.kind,
            relation=claim.relation,
            parent_id=claim.parent_id,
            status=claim.status,
            rationale=claim.rationale,
            evidence_contracts=claim.evidence_contracts + (contract,),
            evidence=claim.evidence,
            closed_reason=claim.closed_reason,
            created_iteration=claim.created_iteration,
            updated_iteration=iteration,
        )
        ledger = self._replace_claim(updated)
        result: dict[str, Any] = {
            "registered_evidence_contract": contract.model_dump(mode="json"),
            "claim_ledger": ledger.compact_summary(),
        }
        if claim.evidence:
            result["adaptive_contract_warning"] = (
                "This contract was registered after evidence was already linked. "
                "Only evidence generated under this contract can justify a new "
                "supported or falsified disposition."
            )
        return result

    @staticmethod
    def _evaluate_validation_checks(
        checks: tuple[ClaimEvidenceValidationCheck, ...],
        *,
        evidence_document: Any | None,
        evidence_document_error: str | None,
    ) -> tuple[bool | None, tuple[ClaimEvidenceValidationResult, ...]]:
        if not checks:
            return None, ()
        results: list[ClaimEvidenceValidationResult] = []
        for check in checks:
            actual: Any = evidence_document
            error = evidence_document_error
            if error is None:
                for key in check.json_path.split("."):
                    if not isinstance(actual, dict) or key not in actual:
                        error = f"JSON path is missing: {check.json_path}"
                        actual = None
                        break
                    actual = actual[key]
            if error is None and not isinstance(
                actual,
                (str, int, float, bool, type(None)),
            ):
                error = f"JSON path is not a scalar: {check.json_path}"
                actual = None
            passed = error is None and _validation_scalars_equal(
                actual, check.expected_value
            )
            results.append(
                ClaimEvidenceValidationResult(
                    aspect=check.aspect,
                    json_path=check.json_path,
                    expected_value=check.expected_value,
                    actual_value=actual,
                    passed=passed,
                    error=error,
                )
            )
        frozen = tuple(results)
        return all(result.passed for result in frozen), frozen

    @staticmethod
    def _qualifying_contract_evidence(claim: MVPClaim) -> tuple[ClaimEvidenceLink, ...]:
        contracts = {contract.version: contract for contract in claim.evidence_contracts}
        qualifying: list[ClaimEvidenceLink] = []
        for evidence in claim.evidence:
            contract = contracts.get(evidence.contract_version)
            provenance = evidence.provenance
            if (
                contract is None
                or evidence.observation_sufficient is not True
                or provenance is None
                or not provenance.tracked
                or provenance.generated_iteration is None
                or provenance.generated_iteration < contract.registered_iteration
            ):
                continue
            if (
                claim.kind == ClaimKind.INSTRUMENT
                and provenance.capability is not None
                and provenance.execution_succeeded is not True
            ):
                continue
            if contract.validation_checks and evidence.validation_passed is not True:
                continue
            qualifying.append(evidence)
        return tuple(qualifying)

    def _validate_commissioning_claim(
        self,
        *,
        scientific_claim: MVPClaim,
        commissioning_claim_id: str | None,
        scientific_provenance: ClaimEvidenceProvenance,
    ) -> str:
        if commissioning_claim_id is None:
            raise ValueError(
                f"capability evidence for scientific claim {scientific_claim.id} "
                "requires commissioning_claim_id"
            )
        commissioning_claim_id = commissioning_claim_id.strip().casefold()
        claims = self._ledger.by_id()
        if commissioning_claim_id not in claims:
            raise ValueError(f"unknown commissioning_claim_id: {commissioning_claim_id}")
        commissioning = claims[commissioning_claim_id]
        if (
            commissioning.kind != ClaimKind.INSTRUMENT
            or commissioning.relation != ClaimRelation.INSTRUMENT_OF
            or commissioning.parent_id != scientific_claim.id
        ):
            raise ValueError(
                "commissioning claim must be kind=instrument, relation=instrument_of, "
                f"and parent_id={scientific_claim.id}"
            )
        if commissioning.status != ClaimDisposition.SUPPORTED:
            raise ValueError(
                f"commissioning claim {commissioning_claim_id} is not supported"
            )
        if not commissioning.evidence_contracts or not any(
            contract.validation_checks for contract in commissioning.evidence_contracts
        ):
            raise ValueError(
                f"commissioning claim {commissioning_claim_id} requires prospective "
                "machine-checkable validation_checks"
            )
        if scientific_provenance.program_sha256 is None:
            raise ValueError(
                "scientific capability evidence requires a stable workspace program "
                "whose source hash can be matched to commissioning"
            )
        generated_iteration = scientific_provenance.generated_iteration
        if generated_iteration is None or commissioning.updated_iteration >= generated_iteration:
            raise ValueError(
                f"commissioning claim {commissioning_claim_id} must be supported before "
                "the scientific artifact is generated"
            )
        contracts = {
            contract.version: contract for contract in commissioning.evidence_contracts
        }
        qualifying: list[ClaimEvidenceLink] = []
        observed_aspects: set[CommissioningAspect] = set()
        complete_same_capability = False
        complete_same_source = False
        complete_binding_present = False
        for evidence in self._qualifying_contract_evidence(commissioning):
            contract = contracts.get(evidence.contract_version)
            if (
                contract is None
                or not contract.validation_checks
                or evidence.validation_passed is not True
            ):
                continue
            if scientific_provenance.capability is not None and (
                evidence.provenance is None
                or evidence.provenance.capability != scientific_provenance.capability
            ):
                continue
            contract_aspects = {
                check.aspect
                for check in contract.validation_checks
                if check.aspect is not None
            }
            observed_aspects.update(contract_aspects)
            if contract_aspects >= REQUIRED_SCIENTIFIC_COMMISSIONING_ASPECTS:
                complete_same_capability = True
                if (
                    evidence.provenance is not None
                    and evidence.provenance.program_sha256
                    == scientific_provenance.program_sha256
                ):
                    complete_same_source = True
                    binding = contract.execution_binding
                    if (
                        binding is None
                        or not binding.allowed_scientific_argv
                    ):
                        continue
                    complete_binding_present = True
                    if (
                        scientific_provenance.capability != binding.capability
                        or scientific_provenance.program_path
                        != binding.program_path
                        or (
                            binding.program_sha256 is not None
                            and scientific_provenance.program_sha256
                            != binding.program_sha256
                        )
                        or scientific_provenance.command_argv
                        not in binding.allowed_scientific_argv
                    ):
                        continue
                    qualifying.append(evidence)
        if not qualifying:
            missing_aspects = sorted(
                aspect.value
                for aspect in REQUIRED_SCIENTIFIC_COMMISSIONING_ASPECTS - observed_aspects
            )
            if missing_aspects:
                raise ValueError(
                    f"commissioning claim {commissioning_claim_id} is missing required "
                    f"machine-checked aspects {missing_aspects}; one qualifying evidence "
                    "contract must cover representation, physics_controls, boundaries, "
                    "diagnostics, and numerical_regime"
                )
            if complete_same_capability:
                if not complete_same_source:
                    raise ValueError(
                        f"commissioning claim {commissioning_claim_id} has complete "
                        "machine-checked evidence for the capability but not for the "
                        "same program source; parameterize and reuse the commissioned "
                        "program or recommission the changed source"
                    )
                if not complete_binding_present:
                    raise ValueError(
                        f"commissioning claim {commissioning_claim_id} requires a "
                        "prospective execution_binding with at least one exact "
                        "allowed_scientific_argv command"
                    )
                raise ValueError(
                    f"scientific command {list(scientific_provenance.command_argv)!r} "
                    f"is outside commissioning claim {commissioning_claim_id}'s "
                    "prospectively allowed scientific argv"
                )
            raise ValueError(
                f"commissioning claim {commissioning_claim_id} has no qualifying "
                "complete machine-checked evidence from the scientific capability"
            )
        return commissioning_claim_id

    @staticmethod
    def _matching_execution_binding(
        contract: ClaimEvidenceContract,
        *,
        capability: str | None,
        program_path: str | None,
        program_sha256: str | None,
        argv: tuple[str, ...],
        instrument: bool,
    ) -> tuple[int, ClaimExecutionBinding] | None:
        """Resolve one exact command within a prospectively declared pipeline."""

        for index, binding in enumerate(contract.all_execution_bindings()):
            if (
                capability == binding.capability
                and program_path == binding.program_path
                and binding.allows_evidence_argv(argv, instrument=instrument)
                and (
                    binding.program_sha256 is None
                    or binding.program_sha256 == program_sha256
                )
            ):
                return index, binding
        return None

    def _seal_scientific_execution_binding(
        self,
        *,
        claim: MVPClaim,
        binding_index: int,
        program_sha256: str,
        iteration: int,
    ) -> MVPClaim:
        """Persist the first runner-attested hash for one scientific pipeline stage."""

        contract = claim.evidence_contracts[-1]
        bindings = list(contract.all_execution_bindings())
        binding = bindings[binding_index]
        if binding.program_sha256 is not None:
            return claim
        bindings[binding_index] = binding.model_copy(
            update={"program_sha256": program_sha256}
        )
        updated_contract = contract.model_copy(
            update={
                "execution_binding": bindings[0],
                "additional_execution_bindings": tuple(bindings[1:]),
            }
        )
        updated_claim = claim.model_copy(
            update={
                "evidence_contracts": (
                    *claim.evidence_contracts[:-1],
                    updated_contract,
                ),
                "updated_iteration": iteration,
            }
        )
        self._replace_claim(updated_claim)
        return updated_claim

    def validate_capability_execution(
        self,
        *,
        claim_id: str,
        capability: str,
        argv: tuple[str, ...],
        program_sha256: str | None,
        iteration: int,
    ) -> str | None:
        """Validate stage ordering before a capability can create side effects."""
        claim_id = claim_id.strip().casefold()
        claims = self._ledger.by_id()
        if claim_id not in claims:
            raise ValueError(f"unknown active_claim_id: {claim_id}")
        claim = claims[claim_id]
        if claim.status != ClaimDisposition.OPEN:
            raise ValueError(
                f"active_claim_id {claim_id} is not open ({claim.status.value})"
            )
        if not claim.evidence_contracts:
            raise ValueError(
                f"cannot execute capability {capability!r} for claim {claim_id}: "
                "register a prospective evidence contract on the active claim before "
                "capability execution"
            )
        if claim.evidence_contracts[-1].registered_iteration >= iteration:
            raise ValueError(
                f"cannot execute capability {capability!r} for claim {claim_id}: "
                "the active evidence contract must be registered in an earlier turn"
            )
        active_contract = claim.evidence_contracts[-1]
        active_binding = active_contract.execution_binding
        if (
            claim.kind == ClaimKind.INSTRUMENT
            and active_binding is not None
            and (
                active_binding.capability != capability
                or active_binding.commissioning_argv != argv
            )
        ):
            raise ValueError(
                f"capability execution for bound instrument claim {claim_id} "
                "must exactly match execution_binding.capability and "
                "commissioning_argv; use a separate prospective interface claim "
                "for scouting probes"
            )
        if claim.kind == ClaimKind.INSTRUMENT and active_binding is not None:
            if program_sha256 is None:
                raise ValueError(
                    f"capability execution for bound instrument claim {claim_id} "
                    "requires a stable workspace program source"
                )
            if active_binding.program_sha256 is None:
                active_binding = active_binding.model_copy(
                    update={"program_sha256": program_sha256}
                )
                active_contract = claim.evidence_contracts[-1].model_copy(
                    update={"execution_binding": active_binding}
                )
                claim = claim.model_copy(
                    update={
                        "evidence_contracts": (
                            *claim.evidence_contracts[:-1],
                            active_contract,
                        ),
                        "updated_iteration": iteration,
                    }
                )
                self._replace_claim(claim)
                claims = self._ledger.by_id()
            elif active_binding.program_sha256 != program_sha256:
                raise ValueError(
                    f"capability execution for bound instrument claim {claim_id} "
                    "does not match its sealed program source; register a new "
                    "prospective contract and recommission the changed source"
                )
        if (
            claim.kind == ClaimKind.INSTRUMENT
            and claim.relation == ClaimRelation.INSTRUMENT_OF
        ):
            prior_interface_claims: list[str] = []
            for sibling in claims.values():
                if (
                    sibling.id == claim.id
                    or sibling.kind != ClaimKind.INSTRUMENT
                    or sibling.relation != ClaimRelation.INSTRUMENT_OF
                    or sibling.parent_id != claim.parent_id
                    or sibling.status != ClaimDisposition.SUPPORTED
                ):
                    continue
                contracts = {
                    contract.version: contract
                    for contract in sibling.evidence_contracts
                }
                for evidence in self._qualifying_contract_evidence(sibling):
                    contract = contracts.get(evidence.contract_version)
                    provenance = evidence.provenance
                    if contract is None or provenance is None:
                        continue
                    aspects = {
                        check.aspect
                        for check in contract.validation_checks
                        if check.aspect is not None
                    }
                    if (
                        provenance.capability == capability
                        and aspects
                        and aspects <= {CommissioningAspect.INTERFACE}
                    ):
                        prior_interface_claims.append(sibling.id)
                        break
            active_aspects = {
                check.aspect
                for check in claim.evidence_contracts[-1].validation_checks
                if check.aspect is not None
            }
            if (
                prior_interface_claims
                and not active_aspects >= REQUIRED_SCIENTIFIC_COMMISSIONING_ASPECTS
            ):
                raise ValueError(
                    f"cannot execute another incomplete instrument_of stage for "
                    f"capability {capability!r} and parent {claim.parent_id}: supported "
                    f"interface discovery already exists in {sorted(prior_interface_claims)}; "
                    "the active contract must now cover representation, "
                    "physics_controls, boundaries, diagnostics, and "
                    "numerical_regime together"
                )
        if claim.kind != ClaimKind.SCIENTIFIC:
            return None
        if program_sha256 is None:
            raise ValueError(
                f"cannot execute capability {capability!r} for scientific claim "
                f"{claim_id}: use a stable workspace program that can be matched to "
                "commissioning"
            )
        matched_binding = self._matching_execution_binding(
            active_contract,
            capability=capability,
            program_path=argv[0],
            program_sha256=program_sha256,
            argv=argv,
            instrument=False,
        )
        if active_contract.all_execution_bindings() and matched_binding is None:
            raise ValueError(
                f"capability execution for scientific claim {claim_id} does not "
                "match an allowed_scientific_argv command in its active prospective "
                "execution_binding pipeline"
            )
        if matched_binding is not None:
            binding_index, binding = matched_binding
            if binding.program_sha256 is None:
                claim = self._seal_scientific_execution_binding(
                    claim=claim,
                    binding_index=binding_index,
                    program_sha256=program_sha256,
                    iteration=iteration,
                )

        synthetic_provenance = ClaimEvidenceProvenance(
            sha256="0" * 64,
            bytes=0,
            tracked=True,
            generated_iteration=iteration,
            action="capability_execution_preflight",
            command_argv=argv,
            capability=capability,
            program_path=argv[0],
            program_sha256=program_sha256,
        )
        candidates = sorted(
            child.id
            for child in claims.values()
            if child.kind == ClaimKind.INSTRUMENT
            and child.relation == ClaimRelation.INSTRUMENT_OF
            and child.parent_id == claim_id
            and child.status == ClaimDisposition.SUPPORTED
        )
        for candidate in candidates:
            try:
                return self._validate_commissioning_claim(
                    scientific_claim=claim,
                    commissioning_claim_id=candidate,
                    scientific_provenance=synthetic_provenance,
                )
            except ValueError:
                continue
        raise ValueError(
            f"cannot execute capability {capability!r} for scientific claim {claim_id}: "
            "require a supported machine-checked instrument_of claim from the same "
            "capability, closed before this execution, with one contract covering "
            "representation, physics_controls, boundaries, diagnostics, and "
            "numerical_regime for the "
            "same program source and a prospective execution_binding that allows "
            "this exact scientific argv; bind scouting and commissioning runs to "
            "an instrument claim"
        )

    def link_evidence(
        self,
        *,
        claim_id: str,
        path: str,
        note: str,
        observation_sufficient: bool,
        observation_note: str,
        provenance: ClaimEvidenceProvenance,
        commissioning_claim_id: str | None = None,
        evidence_document: Any | None = None,
        evidence_document_error: str | None = None,
        iteration: int,
    ) -> dict[str, Any]:
        claim_id = claim_id.strip().casefold()
        existing = self._ledger.by_id()
        if claim_id not in existing:
            raise ValueError(f"unknown claim_id: {claim_id}")
        claim = existing[claim_id]
        if claim.status != ClaimDisposition.OPEN:
            raise ValueError(f"claim is already closed: {claim_id}")
        contract = claim.evidence_contracts[-1] if claim.evidence_contracts else None
        contract_version = contract.version if contract is not None else None
        validation_passed, validation_results = self._evaluate_validation_checks(
            contract.validation_checks if contract is not None else (),
            evidence_document=evidence_document,
            evidence_document_error=evidence_document_error,
        )
        if observation_sufficient:
            if contract is None:
                raise ValueError(
                    f"cannot mark evidence sufficient for {claim_id} without a "
                    "prospective evidence contract"
                )
            if not provenance.evidence_eligible:
                raise ValueError(
                    "cannot mark a workbench artifact sufficient; freeze and promote "
                    "the program through prospective commissioning, then generate a "
                    "fresh evidence-stage artifact"
                )
            if (
                not provenance.tracked
                or provenance.generated_iteration is None
                or provenance.generated_iteration < contract.registered_iteration
            ):
                raise ValueError(
                    "cannot mark evidence sufficient unless it is provenance-tracked "
                    "and generated after the active contract"
                )
            if contract.validation_checks and validation_passed is not True:
                failures = [
                    result.json_path
                    for result in validation_results
                    if not result.passed
                ]
                raise ValueError(
                    "cannot mark evidence sufficient: machine-checkable validation "
                    f"failed for {failures}"
                )
            bindings = contract.all_execution_bindings()
            if bindings and self._matching_execution_binding(
                contract,
                capability=provenance.capability,
                program_path=provenance.program_path,
                program_sha256=provenance.program_sha256,
                argv=provenance.command_argv,
                instrument=claim.kind == ClaimKind.INSTRUMENT,
            ) is None:
                raise ValueError(
                    "cannot mark evidence sufficient: artifact provenance does not "
                    "match a prospectively authorized evidence command in the "
                    "execution_binding pipeline"
                )
            if (
                claim.kind == ClaimKind.INSTRUMENT
                and claim.relation == ClaimRelation.INSTRUMENT_OF
                and provenance.capability is not None
                and provenance.execution_succeeded is not True
            ):
                raise ValueError(
                    "cannot mark commissioning evidence sufficient unless the "
                    "runner witnessed a successful capability execution (return code "
                    "zero, no timeout, and no workspace-limit termination)"
                )
            if claim.kind == ClaimKind.SCIENTIFIC and provenance.capability is not None:
                commissioning_claim_id = self._validate_commissioning_claim(
                    scientific_claim=claim,
                    commissioning_claim_id=commissioning_claim_id,
                    scientific_provenance=provenance,
                )
        link = ClaimEvidenceLink(
            path=path,
            note=note,
            iteration=iteration,
            contract_version=contract_version,
            observation_sufficient=observation_sufficient,
            observation_note=observation_note,
            validation_passed=validation_passed,
            validation_results=validation_results,
            commissioning_claim_id=commissioning_claim_id,
            provenance=provenance,
        )
        updated = MVPClaim(
            id=claim.id,
            statement=claim.statement,
            kind=claim.kind,
            relation=claim.relation,
            parent_id=claim.parent_id,
            status=claim.status,
            rationale=claim.rationale,
            evidence_contracts=claim.evidence_contracts,
            evidence=claim.evidence + (link,),
            closed_reason=claim.closed_reason,
            created_iteration=claim.created_iteration,
            updated_iteration=iteration,
        )
        ledger = self._replace_claim(updated)
        return {
            "updated": updated.model_dump(mode="json"),
            "artifact_exists": True,
            "artifact_provenance": provenance.model_dump(mode="json"),
            "claim_ledger": ledger.compact_summary(),
        }

    def close(
        self,
        *,
        claim_id: str,
        status: ClaimDisposition,
        reason: str,
        iteration: int,
    ) -> dict[str, Any]:
        claim_id = claim_id.strip().casefold()
        if status == ClaimDisposition.OPEN:
            raise ValueError("close_claim requires a non-open disposition")
        existing = self._ledger.by_id()
        if claim_id not in existing:
            raise ValueError(f"unknown claim_id: {claim_id}")
        claim = existing[claim_id]
        if claim.status != ClaimDisposition.OPEN:
            raise ValueError(f"claim is already closed: {claim_id}")
        if status in {ClaimDisposition.SUPPORTED, ClaimDisposition.FALSIFIED}:
            if not claim.evidence_contracts:
                raise ValueError(
                    f"cannot close {claim_id} as {status.value} without a registered "
                    "evidence contract"
                )
            active_contract = claim.evidence_contracts[-1]
            if (
                status == ClaimDisposition.SUPPORTED
                and claim.kind == ClaimKind.INSTRUMENT
                and claim.relation == ClaimRelation.INSTRUMENT_OF
                and active_contract.execution_binding is not None
                and active_contract.execution_binding.allowed_scientific_argv
            ):
                active_aspects = {
                    check.aspect
                    for check in active_contract.validation_checks
                    if check.aspect is not None
                }
                missing_aspects = sorted(
                    aspect.value
                    for aspect in (
                        REQUIRED_SCIENTIFIC_COMMISSIONING_ASPECTS
                        - active_aspects
                    )
                )
                if missing_aspects:
                    raise ValueError(
                        f"cannot close capability-bound instrument claim {claim_id} "
                        "as supported: its active contract is intended to authorize "
                        "scientific execution but is missing required machine-checked "
                        f"aspects {missing_aspects}; one contract must cover "
                        "representation, physics_controls, boundaries, diagnostics, "
                        "and numerical_regime"
                    )
            active_contract_version = claim.evidence_contracts[-1].version
            prior_contract_evidence = [
                evidence
                for evidence in claim.evidence
                if evidence.contract_version is not None
                and evidence.contract_version < active_contract_version
            ]
            if prior_contract_evidence:
                raise ValueError(
                    f"cannot close {claim_id} as {status.value} under an adaptive "
                    "contract registered after evidence was already linked; close "
                    "non-decisively or register a successor/refinement claim with a "
                    "prospective pipeline and collect fresh observations"
                )
            qualifying_evidence = list(self._qualifying_contract_evidence(claim))
            if claim.kind == ClaimKind.SCIENTIFIC:
                commissioned: list[ClaimEvidenceLink] = []
                for evidence in qualifying_evidence:
                    provenance = evidence.provenance
                    assert provenance is not None
                    if provenance.capability is None:
                        commissioned.append(evidence)
                        continue
                    try:
                        self._validate_commissioning_claim(
                            scientific_claim=claim,
                            commissioning_claim_id=evidence.commissioning_claim_id,
                            scientific_provenance=provenance,
                        )
                    except ValueError:
                        continue
                    commissioned.append(evidence)
                qualifying_evidence = commissioned
            if not qualifying_evidence:
                raise ValueError(
                    f"cannot close {claim_id} as {status.value}: require linked, "
                    "provenance-tracked evidence generated under an evidence contract "
                    "and marked observation_sufficient=true; capability-generated "
                    "scientific evidence also requires prior machine-checked commissioning"
                )
        updated = MVPClaim(
            id=claim.id,
            statement=claim.statement,
            kind=claim.kind,
            relation=claim.relation,
            parent_id=claim.parent_id,
            status=status,
            rationale=claim.rationale,
            evidence_contracts=claim.evidence_contracts,
            evidence=claim.evidence,
            closed_reason=reason,
            created_iteration=claim.created_iteration,
            updated_iteration=iteration,
        )
        ledger = self._replace_claim(updated)
        result: dict[str, Any] = {
            "closed": updated.model_dump(mode="json"),
            "claim_ledger": ledger.compact_summary(),
        }
        # Non-evidentiary dispositions remain available so a bounded campaign can
        # finish honestly even when no decisive artifact was produced.
        if not claim.evidence and claim_id != ROOT_CLAIM_ID:
            result["evidence_warning"] = (
                f"closed {claim_id} with status={status.value} and no linked evidence; "
                "prefer link_claim_evidence before close_claim when workspace "
                "artifacts exist"
            )
        return result

    def list_claims(self) -> dict[str, Any]:
        return {
            "claim_ledger": self._ledger.compact_summary(max_claims=200),
            "claims": [claim.model_dump(mode="json") for claim in self._ledger.claims],
        }

    def snapshot(self) -> dict[str, Any]:
        return json.loads(self._ledger.model_dump_json())
