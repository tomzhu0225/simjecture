"""In-process adapter for the independent electrostatic PIC benchmark."""

from __future__ import annotations

import hashlib
import json

from ..benchmarks.electrostatic_pic import (
    PICConfig,
    PICSufficiencyResult,
    run_pic_sufficiency_benchmark,
)
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


class DeterministicPICScheduler:
    """External-scheduler stand-in shared across restarted adapter instances."""

    def __init__(self) -> None:
        self.jobs: dict[str, RawResult] = {}
        self.idempotency: dict[str, str] = {}


class ElectrostaticPICAdapter:
    _NUMERICAL_KEYS = {
        "grid_cells",
        "velocity_beams",
        "particles_per_beam",
        "time_step",
        "final_time",
        "diagnostic_interval",
        "seed",
    }
    _PHYSICAL_KEYS = {"wavenumber", "perturbation_amplitude", "stream_drift"}

    def __init__(self, scheduler: DeterministicPICScheduler | None = None) -> None:
        self._scheduler = scheduler or DeterministicPICScheduler()

    @property
    def submitted_job_count(self) -> int:
        return len(self._scheduler.jobs)

    def capabilities(self) -> CapabilityManifest:
        return CapabilityManifest(
            adapter_name="electrostatic_pic",
            adapter_version="0.1.0",
            supported_actions=("kinetic_sufficiency",),
            supported_models=("electrostatic_1d_pic_vlasov_poisson",),
            supported_diagnostics=(
                "dominant_linear_mode",
                "distribution_moments",
                "energy_conservation",
                "gauss_residual",
            ),
            supported_coordinates=("density", "mean_velocity", "variance"),
            supported_observable_kinds=("effective_fundamental_growth_rate",),
            supports_checkpoint=False,
            deterministic=True,
        )

    def _config(self, experiment: ExperimentSpec) -> PICConfig:
        values = {
            **experiment.physical_parameters,
            **experiment.numerical_parameters,
        }
        return PICConfig.model_validate(values)

    def validate(self, experiment: ExperimentSpec) -> ValidationReport:
        errors: list[str] = []
        warnings: list[str] = []
        if experiment.action_type != "kinetic_sufficiency":
            errors.append("unsupported action_type")
        unknown_physical = set(experiment.physical_parameters) - self._PHYSICAL_KEYS
        unknown_numerical = set(experiment.numerical_parameters) - self._NUMERICAL_KEYS
        if unknown_physical:
            errors.append(f"unknown physical parameters: {sorted(unknown_physical)}")
        if unknown_numerical:
            errors.append(f"unknown numerical parameters: {sorted(unknown_numerical)}")
        missing_diagnostics = set(experiment.required_diagnostics) - set(
            self.capabilities().supported_diagnostics
        )
        if missing_diagnostics:
            errors.append(f"unsupported diagnostics: {sorted(missing_diagnostics)}")
        if not errors:
            try:
                config = self._config(experiment)
            except ValueError as error:
                errors.append(f"invalid PIC configuration: {error}")
            else:
                particle_count = config.velocity_beams * config.particles_per_beam
                if particle_count > 1_000_000:
                    warnings.append("PIC request contains more than one million particles")
        return ValidationReport(valid=not errors, errors=tuple(errors), warnings=tuple(warnings))

    def estimate_cost(self, experiment: ExperimentSpec) -> CostEstimate:
        report = self.validate(experiment)
        if not report.valid:
            raise ValueError("; ".join(report.errors))
        config = self._config(experiment)
        particle_count = config.velocity_beams * config.particles_per_beam
        step_count = round(config.final_time / config.time_step)
        work = 2 * particle_count * step_count
        return CostEstimate(
            compute_units=work / 100_000_000,
            wall_seconds=work / 20_000_000,
            storage_bytes=(round(config.final_time / config.diagnostic_interval) + 1) * 128,
        )

    def compile_input(self, experiment: ExperimentSpec) -> RunPackage:
        report = self.validate(experiment)
        if not report.valid:
            raise ValueError("; ".join(report.errors))
        payload = {
            "benchmark": "electrostatic_pic_sufficiency",
            "config": self._config(experiment).model_dump(mode="json"),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return RunPackage(
            experiment_id=experiment.id,
            adapter_name="electrostatic_pic",
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
        identity = hashlib.sha256(f"{run.package_hash}:{idempotency_key}".encode()).hexdigest()
        job_id = f"pic-{identity[:16]}"
        result = run_pic_sufficiency_benchmark(PICConfig.model_validate(run.payload["config"]))
        result_payload = {
            "experiment_id": run.experiment_id,
            "benchmark": result.model_dump(mode="json"),
        }
        canonical = json.dumps(result_payload, sort_keys=True, separators=(",", ":"))
        self._scheduler.jobs[job_id] = RawResult(
            job_id=job_id,
            payload=result_payload,
            artifact_hashes=(hashlib.sha256(canonical.encode()).hexdigest(),),
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
            raise LookupError(f"unknown PIC job {job.job_id}") from error

    def normalize(self, result: RawResult) -> NormalizedResult:
        benchmark = PICSufficiencyResult.model_validate(result.payload["benchmark"])
        if not benchmark.maxwellian.validity_passed or not benchmark.two_stream.validity_passed:
            raise ValueError("PIC result failed numerical validity gates")
        return NormalizedResult(
            experiment_id=str(result.payload["experiment_id"]),
            observables={
                "maxwellian_growth_rate": benchmark.maxwellian.effective_growth_rate,
                "two_stream_growth_rate": benchmark.two_stream.effective_growth_rate,
                "moments_match": benchmark.moments_match,
                "hypothesis_falsified": benchmark.hypothesis_falsified,
            },
            diagnostics=benchmark.model_dump(mode="json"),
            artifact_hashes=result.artifact_hashes,
        )

    def cancel(self, job: JobReference) -> JobStatus:
        if job.job_id in self._scheduler.jobs:
            return JobStatus(
                job_id=job.job_id,
                state=JobState.COMPLETED,
                detail="in-process PIC jobs complete synchronously",
            )
        return JobStatus(job_id=job.job_id, state=JobState.UNKNOWN)
