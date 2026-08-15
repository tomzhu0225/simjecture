"""Generic subprocess boundary for model-visible research capabilities."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from pydantic import Field

from .adapters.base import (
    CostEstimate,
    JobState,
    SimulatorAdapter,
    ValidationReport,
)
from .autonomous_research import (
    ResearchToolManifest,
    ResearchToolResult,
)
from .models import ExperimentSpec, StrictModel


class SubprocessResearchToolConfig(StrictModel):
    manifest: ResearchToolManifest
    command: tuple[str, ...] = Field(min_length=1)
    working_directory: str | None = None
    timeout_seconds: float = Field(gt=0)
    estimated_cost: CostEstimate
    environment: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def read(cls, path: str | Path) -> SubprocessResearchToolConfig:
        return cls.model_validate_json(Path(path).read_text())


def _json_type_matches(value: object, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return False


def _validate_schema(value: object, schema: dict[str, Any], path: str = "$") -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")
    if isinstance(expected, list):
        if not any(_json_type_matches(value, str(item)) for item in expected):
            return [f"{path} does not match any allowed JSON type"]
    elif isinstance(expected, str) and not _json_type_matches(value, expected):
        return [f"{path} must have JSON type {expected}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path} is not in the allowed enum")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for name in required:
            if name not in value:
                errors.append(f"{path}.{name} is required")
        if schema.get("additionalProperties") is False:
            extras = set(value) - set(properties)
            if extras:
                errors.append(f"{path} has unsupported properties: {sorted(extras)}")
        for name, item in value.items():
            child_schema = properties.get(name)
            if isinstance(child_schema, dict):
                errors.extend(_validate_schema(item, child_schema, f"{path}.{name}"))
    elif isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            errors.extend(_validate_schema(item, schema["items"], f"{path}[{index}]"))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path} is below its minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path} exceeds its maximum")
    return errors


class SubprocessResearchTool:
    """Run an explicitly installed JSON-in/JSON-out tool without a shell."""

    def __init__(self, config: SubprocessResearchToolConfig) -> None:
        self.config = config
        self.manifest = config.manifest

    def validate(self, arguments: dict[str, Any]) -> ValidationReport:
        errors = tuple(_validate_schema(arguments, self.manifest.input_schema))
        return ValidationReport(valid=not errors, errors=errors)

    def estimate_cost(self, arguments: dict[str, Any]) -> CostEstimate:
        del arguments
        return self.config.estimated_cost

    def execute(
        self,
        arguments: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> ResearchToolResult:
        validation = self.validate(arguments)
        if not validation.valid:
            raise ValueError("invalid subprocess tool arguments: " + "; ".join(validation.errors))
        envelope = {
            "schema_version": "0.1.0",
            "tool": self.manifest.name,
            "tool_version": self.manifest.version,
            "idempotency_key": idempotency_key,
            "arguments": arguments,
        }
        environment = os.environ.copy()
        environment.update(self.config.environment)
        started = time.monotonic()
        completed = subprocess.run(
            list(self.config.command),
            input=json.dumps(envelope, sort_keys=True),
            capture_output=True,
            text=True,
            cwd=self.config.working_directory,
            env=environment,
            timeout=self.config.timeout_seconds,
            check=False,
        )
        elapsed = time.monotonic() - started
        if completed.returncode != 0:
            detail = completed.stderr.strip() or f"exit status {completed.returncode}"
            return ResearchToolResult(
                completed=False,
                validity_checks={"subprocess_exit_zero": False},
                diagnostics={"returncode": completed.returncode},
                cost=self.config.estimated_cost.model_copy(
                    update={"wall_seconds": elapsed}
                ),
                scientific_scope=f"failed execution of {self.manifest.name}",
                failure_detail=detail[:2000],
            )
        try:
            result = ResearchToolResult.model_validate_json(completed.stdout)
        except ValueError as error:
            raise ValueError(
                f"research tool {self.manifest.name} returned invalid JSON: {error}"
            ) from error
        output_errors = _validate_schema(result.observables, self.manifest.output_schema)
        if output_errors:
            raise ValueError(
                "research tool output violated its manifest: " + "; ".join(output_errors)
            )
        return result


class SimulatorAdapterResearchTool:
    """Expose any simulator adapter as a model-visible generic research tool."""

    def __init__(
        self,
        adapter: SimulatorAdapter,
        *,
        name: str | None = None,
        description: str | None = None,
        supported_observables: tuple[str, ...] | None = None,
        poll_interval_seconds: float = 0.1,
        monitor_timeout_seconds: float = 3600.0,
    ) -> None:
        capabilities = adapter.capabilities()
        self.adapter = adapter
        self.poll_interval_seconds = poll_interval_seconds
        self.monitor_timeout_seconds = monitor_timeout_seconds
        observables = supported_observables or capabilities.supported_observable_kinds
        self.manifest = ResearchToolManifest(
            name=name or capabilities.adapter_name.replace("_", "-"),
            version=capabilities.adapter_version,
            description=description or f"Simulator adapter {capabilities.adapter_name}",
            kind="simulator",
            input_schema={
                "type": "object",
                "properties": {"experiment": ExperimentSpec.model_json_schema()},
                "required": ["experiment"],
                "additionalProperties": False,
            },
            output_schema={
                "type": "object",
                "properties": {name: {} for name in observables},
            },
            supported_model_families=capabilities.supported_models,
            supported_coordinates=capabilities.supported_coordinates,
            supported_observables=observables,
        )

    def _experiment(self, arguments: dict[str, Any]) -> ExperimentSpec:
        try:
            return ExperimentSpec.model_validate(arguments["experiment"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(f"invalid simulator experiment: {error}") from error

    def validate(self, arguments: dict[str, Any]) -> ValidationReport:
        try:
            experiment = self._experiment(arguments)
        except ValueError as error:
            return ValidationReport(valid=False, errors=(str(error),))
        return self.adapter.validate(experiment)

    def estimate_cost(self, arguments: dict[str, Any]) -> CostEstimate:
        experiment = self._experiment(arguments)
        report = self.adapter.validate(experiment)
        if not report.valid:
            raise ValueError("invalid simulator experiment: " + "; ".join(report.errors))
        return self.adapter.estimate_cost(experiment)

    def execute(
        self,
        arguments: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> ResearchToolResult:
        experiment = self._experiment(arguments)
        validation = self.adapter.validate(experiment)
        if not validation.valid:
            raise ValueError("invalid simulator experiment: " + "; ".join(validation.errors))
        estimate = self.adapter.estimate_cost(experiment)
        run = self.adapter.compile_input(experiment)
        job = self.adapter.submit(run, idempotency_key=idempotency_key)
        deadline = time.monotonic() + self.monitor_timeout_seconds
        while True:
            status = self.adapter.monitor(job)
            if status.state is JobState.COMPLETED:
                break
            if status.state in {JobState.FAILED, JobState.CANCELLED, JobState.UNKNOWN}:
                return ResearchToolResult(
                    completed=False,
                    diagnostics={"job_state": status.state.value, "detail": status.detail},
                    validity_checks={"job_completed": False},
                    cost=estimate,
                    scientific_scope=f"failed {self.manifest.name} execution",
                    failure_detail=status.detail or f"job ended in {status.state.value}",
                )
            if time.monotonic() >= deadline:
                return ResearchToolResult(
                    completed=False,
                    diagnostics={"job_state": status.state.value},
                    validity_checks={"job_completed_before_timeout": False},
                    cost=estimate,
                    scientific_scope=f"timed-out {self.manifest.name} execution",
                    failure_detail="simulator monitor timeout",
                )
            time.sleep(self.poll_interval_seconds)
        normalized = self.adapter.normalize(self.adapter.retrieve(job))
        checks = {"adapter_admission": True, "job_completed": True}
        gate = normalized.observables.get("instrument_gates_passed")
        if isinstance(gate, bool):
            checks["instrument_gates_passed"] = gate
        evidence = normalized.observables.get("scientific_evidence_eligible")
        if isinstance(evidence, bool):
            checks["scientific_evidence_eligible"] = evidence
        return ResearchToolResult(
            completed=True,
            observables=normalized.observables,
            diagnostics=normalized.diagnostics,
            validity_checks=checks,
            artifact_hashes=normalized.artifact_hashes,
            cost=estimate,
            scientific_scope=(
                f"{self.manifest.name} in model families "
                + ", ".join(self.manifest.supported_model_families)
            ),
        )
