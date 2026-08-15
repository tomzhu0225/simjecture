from __future__ import annotations

from conjecture_solver.adapters.base import JobState, SimulatorAdapter
from conjecture_solver.adapters.fake import DeterministicKineticAdapter
from conjecture_solver.models import ExperimentSpec


def experiment() -> ExperimentSpec:
    return ExperimentSpec(
        id="experiment_kinetic_1",
        hypothesis_ids=("hypothesis_low_moments_sufficient_for_stability",),
        action_type="kinetic_sufficiency",
        physical_parameters={"wavenumber": 0.5},
        required_diagnostics=("dominant_linear_mode", "distribution_moments"),
        predictions={
            "sufficiency": "matched distributions have equal growth rate",
            "counterexample": "matched distributions differ in growth rate",
        },
        falsification_condition="a matched pair differs by more than 0.02",
    )


def test_fake_adapter_satisfies_runtime_protocol() -> None:
    assert isinstance(DeterministicKineticAdapter(), SimulatorAdapter)


def test_fake_adapter_executes_and_normalizes_idempotently() -> None:
    adapter = DeterministicKineticAdapter()
    spec = experiment()
    assert adapter.validate(spec).valid
    run = adapter.compile_input(spec)
    first = adapter.submit(run, idempotency_key="campaign_1:action_1")
    replay = adapter.submit(run, idempotency_key="campaign_1:action_1")

    assert first.job_id == replay.job_id
    assert adapter.monitor(first).state is JobState.COMPLETED
    normalized = adapter.normalize(adapter.retrieve(first))
    assert normalized.experiment_id == spec.id
    assert normalized.observables["moments_match"] is True
    assert normalized.observables["hypothesis_falsified"] is True

