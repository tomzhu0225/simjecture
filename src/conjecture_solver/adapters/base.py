"""Simulator-neutral execution contract."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from ..models import ExperimentSpec, StrictModel


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class CapabilityManifest(StrictModel):
    adapter_name: str
    adapter_version: str
    supported_actions: tuple[str, ...]
    supported_models: tuple[str, ...]
    supported_diagnostics: tuple[str, ...]
    supported_coordinates: tuple[str, ...]
    supported_observable_kinds: tuple[str, ...]
    supports_checkpoint: bool
    deterministic: bool


class ValidationReport(StrictModel):
    valid: bool
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class CostEstimate(StrictModel):
    compute_units: float = Field(ge=0)
    wall_seconds: float = Field(ge=0)
    storage_bytes: int = Field(ge=0)


class RunPackage(StrictModel):
    experiment_id: str
    adapter_name: str
    payload: dict[str, Any]
    package_hash: str


class JobReference(StrictModel):
    job_id: str
    experiment_id: str
    idempotency_key: str


class JobStatus(StrictModel):
    job_id: str
    state: JobState
    detail: str = ""


class RawResult(StrictModel):
    job_id: str
    payload: dict[str, Any]
    artifact_hashes: tuple[str, ...] = ()


class NormalizedResult(StrictModel):
    experiment_id: str
    observables: dict[str, float | bool | str]
    diagnostics: dict[str, Any]
    artifact_hashes: tuple[str, ...] = ()


@runtime_checkable
class SimulatorAdapter(Protocol):
    def capabilities(self) -> CapabilityManifest: ...

    def validate(self, experiment: ExperimentSpec) -> ValidationReport: ...

    def estimate_cost(self, experiment: ExperimentSpec) -> CostEstimate: ...

    def compile_input(self, experiment: ExperimentSpec) -> RunPackage: ...

    def submit(self, run: RunPackage, *, idempotency_key: str) -> JobReference: ...

    def monitor(self, job: JobReference) -> JobStatus: ...

    def retrieve(self, job: JobReference) -> RawResult: ...

    def normalize(self, result: RawResult) -> NormalizedResult: ...

    def cancel(self, job: JobReference) -> JobStatus: ...
