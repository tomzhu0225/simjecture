"""Deterministic in-process adapter for the first physics benchmark."""

from __future__ import annotations

import hashlib
import json

from ..benchmarks.kinetic_sufficiency import run_kinetic_sufficiency_benchmark
from ..models import ExperimentSpec
from .base import (
    CapabilityManifest,
    CostEstimate,
    JobReference,
    JobState,
    JobStatus,
    NormalizedResult,
    RawResult,
    RunPackage,
    ValidationReport,
)


class DeterministicKineticScheduler:
    """External-system stand-in whose state can outlive an adapter process."""

    def __init__(self) -> None:
        self.jobs: dict[str, RawResult] = {}
        self.idempotency: dict[str, str] = {}


class DeterministicKineticAdapter:
    def __init__(self, scheduler: DeterministicKineticScheduler | None = None) -> None:
        self._scheduler = scheduler or DeterministicKineticScheduler()

    @property
    def submitted_job_count(self) -> int:
        """Count distinct external jobs, excluding idempotent reattachments."""

        return len(self._scheduler.jobs)

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            adapter_name="deterministic_kinetic",
            adapter_version="0.1.0",
            supported_actions=("kinetic_sufficiency",),
            supported_models=("linearized_1d_electrostatic_vlasov_poisson",),
            supported_diagnostics=("dominant_linear_mode", "distribution_moments"),
            supported_coordinates=("density", "mean_velocity", "variance"),
            supported_observable_kinds=("dominant_linear_growth_rate",),
            supports_checkpoint=False,
            deterministic=True,
        )

    def validate(self, experiment: ExperimentSpec) -> ValidationReport:
        errors: list[str] = []
        if experiment.action_type != "kinetic_sufficiency":
            errors.append("unsupported action_type")
        if experiment.physical_parameters.get("wavenumber") != 0.5:
            errors.append("the planted benchmark is preregistered at wavenumber 0.5")
        required = {"dominant_linear_mode", "distribution_moments"}
        missing = required - set(experiment.required_diagnostics)
        if missing:
            errors.append(f"missing diagnostics: {sorted(missing)}")
        return ValidationReport(valid=not errors, errors=tuple(errors))

    def estimate_cost(self, experiment: ExperimentSpec) -> CostEstimate:
        report = self.validate(experiment)
        if not report.valid:
            raise ValueError("; ".join(report.errors))
        return CostEstimate(compute_units=0.001, wall_seconds=1.0, storage_bytes=20_000)

    def compile_input(self, experiment: ExperimentSpec) -> RunPackage:
        report = self.validate(experiment)
        if not report.valid:
            raise ValueError("; ".join(report.errors))
        payload = {
            "benchmark": "kinetic_sufficiency",
            "wavenumber": experiment.physical_parameters["wavenumber"],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return RunPackage(
            experiment_id=experiment.id,
            adapter_name="deterministic_kinetic",
            payload=payload,
            package_hash=hashlib.sha256(canonical.encode()).hexdigest(),
        )

    def submit(self, run: RunPackage, *, idempotency_key: str) -> JobReference:
        if idempotency_key in self._scheduler.idempotency:
            return JobReference(
                job_id=self._scheduler.idempotency[idempotency_key],
                experiment_id=run.experiment_id,
                idempotency_key=idempotency_key,
            )
        job_identity = hashlib.sha256(
            f"{run.package_hash}:{idempotency_key}".encode()
        ).hexdigest()
        job_id = f"fake-{job_identity[:16]}"
        benchmark = run_kinetic_sufficiency_benchmark(
            wavenumber=float(run.payload["wavenumber"])
        )
        result_payload = {
            "experiment_id": run.experiment_id,
            "benchmark": benchmark.model_dump(mode="json"),
        }
        canonical_result = json.dumps(result_payload, sort_keys=True, separators=(",", ":"))
        self._scheduler.jobs[job_id] = RawResult(
            job_id=job_id,
            payload=result_payload,
            artifact_hashes=(hashlib.sha256(canonical_result.encode()).hexdigest(),),
        )
        self._scheduler.idempotency[idempotency_key] = job_id
        return JobReference(
            job_id=job_id,
            experiment_id=run.experiment_id,
            idempotency_key=idempotency_key,
        )

    def monitor(self, job: JobReference) -> JobStatus:
        state = JobState.COMPLETED if job.job_id in self._scheduler.jobs else JobState.UNKNOWN
        return JobStatus(job_id=job.job_id, state=state)

    def retrieve(self, job: JobReference) -> RawResult:
        try:
            return self._scheduler.jobs[job.job_id]
        except KeyError as error:
            raise LookupError(f"unknown fake job {job.job_id}") from error

    def normalize(self, result: RawResult) -> NormalizedResult:
        payload = result.payload
        benchmark = payload["benchmark"]
        return NormalizedResult(
            experiment_id=str(payload["experiment_id"]),
            observables={
                "maxwellian_growth_rate": float(
                    benchmark["maxwellian"]["mode"]["growth_rate"]
                ),
                "two_stream_growth_rate": float(
                    benchmark["two_stream"]["mode"]["growth_rate"]
                ),
                "moments_match": bool(benchmark["moments_match"]),
                "hypothesis_falsified": bool(benchmark["witness"]["falsifies"]),
            },
            diagnostics=benchmark,
            artifact_hashes=result.artifact_hashes,
        )

    def cancel(self, job: JobReference) -> JobStatus:
        if job.job_id in self._scheduler.jobs:
            return JobStatus(
                job_id=job.job_id,
                state=JobState.COMPLETED,
                detail="deterministic in-process jobs complete atomically",
            )
        return JobStatus(job_id=job.job_id, state=JobState.UNKNOWN)
