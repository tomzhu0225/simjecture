from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from conjecture_solver.adapters.base import JobState, RawResult, SimulatorAdapter
from conjecture_solver.adapters.warpx import (
    SubprocessWarpXScheduler,
    WarpXAdapter,
    WarpXExecutionProfile,
    WarpXNumericalConfig,
    WarpXPairSummary,
    WarpXPhysicalConfig,
    WarpXRunnerKind,
    build_warpx_experiment,
    qualify_warpx_picmi_compiler,
)
from conjecture_solver.campaign import CampaignRunner, planted_campaign_problem
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.models import ClaimDisposition

FIXTURE_RUNNER = Path(__file__).parent / "fixtures" / "fake_warpx_runner.py"


def with_payload_hash(job_id: str, payload: dict[str, object]) -> RawResult:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return RawResult(
        job_id=job_id,
        payload=payload,
        artifact_hashes=(hashlib.sha256(canonical.encode()).hexdigest(),),
    )


def adapter(tmp_path: Path) -> WarpXAdapter:
    profile = WarpXExecutionProfile(
        profile_id="ci_contract_fixture",
        runner_kind=WarpXRunnerKind.CONTRACT_FIXTURE,
        warpx_version="26.07",
    )
    scheduler = SubprocessWarpXScheduler(
        work_root=tmp_path / "jobs",
        command=(sys.executable, str(FIXTURE_RUNNER)),
        profile=profile,
        timeout_seconds=10,
    )
    return WarpXAdapter(scheduler)


def test_warpx_adapter_satisfies_protocol_and_declares_nondeterminism(tmp_path: Path) -> None:
    subject = adapter(tmp_path)
    assert isinstance(subject, SimulatorAdapter)
    capabilities = subject.capabilities()
    assert capabilities.supports_checkpoint
    assert not capabilities.deterministic
    assert capabilities.supported_models == ("warpx_electrostatic_1d3v_pic",)


def test_restricted_compiler_is_deterministic_and_contains_only_typed_values(
    tmp_path: Path,
) -> None:
    subject = adapter(tmp_path)
    experiment = build_warpx_experiment()
    first = subject.compile_input(experiment)
    second = subject.compile_input(experiment)
    assert first == second
    assert first.package_hash == "0bf1453c1f8da5ab830dbc6cfc4856fed9e07c779884ade1639221ed3d057b0d"
    assert {case["case_name"] for case in first.payload["cases"]} == {
        "unit_maxwellian_reference",
        "symmetric_mixture_candidate",
    }
    for case in first.payload["cases"]:
        compile(case["script"], case["case_name"], "exec")
        assert "eval(" not in case["script"]
        assert "exec(" not in case["script"]
        assert 'warpx_openpmd_backend="h5"' in case["script"]
        assert "--compile-only" in case["script"]


def test_validation_rejects_unknown_knobs_and_bad_discretization(tmp_path: Path) -> None:
    subject = adapter(tmp_path)
    valid = build_warpx_experiment()
    injected = valid.model_copy(
        update={
            "physical_parameters": {
                **valid.physical_parameters,
                "python_expression": "__import__('os').system('false')",
            }
        }
    )
    report = subject.validate(injected)
    assert not report.valid
    assert "python_expression" in report.errors[0]
    with pytest.raises(ValidationError, match="power of two"):
        WarpXNumericalConfig(grid_cells=63)
    with pytest.raises(ValidationError, match="divisible by four"):
        WarpXNumericalConfig(electron_macroparticles_per_cell=66)
    with pytest.raises(ValidationError, match="0.25 c"):
        WarpXPhysicalConfig(velocity_unit_m_s=2.0e7, inner_drift=0.0, outer_drift=0.0)


def test_fixture_runner_is_idempotent_but_never_scientific_evidence(tmp_path: Path) -> None:
    subject = adapter(tmp_path)
    run = subject.compile_input(build_warpx_experiment())
    first = subject.submit(run, idempotency_key="campaign:warpx:pair")
    replay = subject.submit(run, idempotency_key="campaign:warpx:pair")
    assert first == replay
    assert len(list((tmp_path / "jobs").iterdir())) == 1
    assert subject.monitor(first).state is JobState.COMPLETED

    raw = subject.retrieve(first)
    normalized = subject.normalize(raw)
    assert normalized.observables["numerical_validity_passed"] is True
    assert normalized.diagnostics["raw_witness_satisfies_predicate"] is True
    assert normalized.diagnostics["scientific_evidence_eligible"] is False
    assert normalized.observables["hypothesis_falsified"] is False
    assert normalized.observables["outcome_separation"] == pytest.approx(0.4)


def test_orphaned_running_marker_is_recovered_without_losing_partial_outputs(
    tmp_path: Path,
) -> None:
    subject = adapter(tmp_path)
    run = subject.compile_input(build_warpx_experiment())
    idempotency_key = "campaign:warpx:orphaned-controller"
    job_id = subject.scheduler._job_id(run, idempotency_key)
    job_dir = tmp_path / "jobs" / job_id
    (job_dir / "execution").mkdir(parents=True)
    (job_dir / "execution" / "partial.log").write_text("controller stopped\n")
    (job_dir / "status.json").write_text(
        json.dumps(
            {
                "state": JobState.RUNNING.value,
                "package_hash": run.package_hash,
            }
        )
    )

    job = subject.submit(run, idempotency_key=idempotency_key)

    assert job.job_id == job_id
    assert subject.monitor(job).state is JobState.COMPLETED
    assert (job_dir / "interrupted_1_execution" / "partial.log").read_text() == (
        "controller stopped\n"
    )


def test_completed_orphan_result_is_committed_without_rerunning(tmp_path: Path) -> None:
    subject = adapter(tmp_path)
    run = subject.compile_input(build_warpx_experiment())
    idempotency_key = "campaign:warpx:orphaned-result"
    job = subject.submit(run, idempotency_key=idempotency_key)
    job_dir = tmp_path / "jobs" / job.job_id
    pair_summary_before = (job_dir / "pair_summary.json").read_bytes()
    (job_dir / "raw_result.json").unlink()
    (job_dir / "status.json").write_text(
        json.dumps(
            {
                "state": JobState.RUNNING.value,
                "package_hash": run.package_hash,
            }
        )
    )

    attached = subject.submit(run, idempotency_key=idempotency_key)

    assert attached == job
    assert subject.monitor(job).state is JobState.COMPLETED
    assert (job_dir / "pair_summary.json").read_bytes() == pair_summary_before
    assert not list(job_dir.glob("interrupted_*"))


def test_campaign_preserves_adapter_ineligibility_in_evidence_and_claim(
    tmp_path: Path,
) -> None:
    subject = adapter(tmp_path)
    hypothesis, _ = planted_campaign_problem()
    with SQLiteEventLedger(tmp_path / "campaign.sqlite3") as ledger:
        package = CampaignRunner(
            campaign_id="campaign_warpx_contract_fixture",
            ledger=ledger,
            adapter=subject,
            hypothesis=hypothesis,
            experiment=build_warpx_experiment(),
        ).run()
    assert not package.evidence.eligible
    assert package.claim.disposition is ClaimDisposition.UNRESOLVED


def test_normalizer_vetoes_numerically_invalid_witness(tmp_path: Path) -> None:
    subject = adapter(tmp_path)
    run = subject.compile_input(build_warpx_experiment())
    job = subject.submit(run, idempotency_key="campaign:warpx:invalid")
    raw = subject.retrieve(job)
    payload = json.loads(json.dumps(raw.payload))
    payload["pair_summary"]["candidate"]["solver_converged"] = False
    with pytest.raises(ValueError, match="artifact hash"):
        subject.normalize(RawResult(job_id=raw.job_id, payload=payload))
    invalid = with_payload_hash(raw.job_id, payload)
    normalized = subject.normalize(invalid)
    assert normalized.observables["numerical_validity_passed"] is False
    assert normalized.diagnostics["raw_witness_satisfies_predicate"] is False
    assert normalized.observables["hypothesis_falsified"] is False


def test_runtime_version_mismatch_vetoes_result(tmp_path: Path) -> None:
    subject = adapter(tmp_path)
    run = subject.compile_input(build_warpx_experiment())
    job = subject.submit(run, idempotency_key="campaign:warpx:version")
    raw = subject.retrieve(job)
    payload = json.loads(json.dumps(raw.payload))
    payload["pair_summary"]["runtime_warpx_version"] = "99.99"
    normalized = subject.normalize(with_payload_hash(raw.job_id, payload))
    assert not normalized.diagnostics["validity_gates"]["runtime_version_matches_profile"]
    assert normalized.observables["numerical_validity_passed"] is False


def test_failed_subprocess_is_visible_and_not_retrievable(tmp_path: Path) -> None:
    profile = WarpXExecutionProfile(
        profile_id="failing_fixture",
        runner_kind=WarpXRunnerKind.CONTRACT_FIXTURE,
        warpx_version="26.07",
    )
    scheduler = SubprocessWarpXScheduler(
        work_root=tmp_path / "failed",
        command=(sys.executable, "-c", "raise SystemExit(3)"),
        profile=profile,
        timeout_seconds=10,
    )
    subject = WarpXAdapter(scheduler)
    run = subject.compile_input(build_warpx_experiment())
    job = subject.submit(run, idempotency_key="campaign:warpx:failure")
    assert subject.monitor(job).state is JobState.FAILED
    with pytest.raises(LookupError, match="no completed result"):
        subject.retrieve(job)


def test_malformed_runner_result_becomes_failed_job(tmp_path: Path) -> None:
    profile = WarpXExecutionProfile(
        profile_id="malformed_fixture",
        runner_kind=WarpXRunnerKind.CONTRACT_FIXTURE,
        warpx_version="26.07",
    )
    write_malformed = (
        "import pathlib, sys; "
        "path = pathlib.Path(sys.argv[sys.argv.index('--result') + 1]); "
        "path.write_text('{}')"
    )
    scheduler = SubprocessWarpXScheduler(
        work_root=tmp_path / "malformed",
        command=(sys.executable, "-c", write_malformed),
        profile=profile,
        timeout_seconds=10,
    )
    subject = WarpXAdapter(scheduler)
    run = subject.compile_input(build_warpx_experiment())
    job = subject.submit(run, idempotency_key="campaign:warpx:malformed")
    status = subject.monitor(job)
    assert status.state is JobState.FAILED
    assert "schema validation" in status.detail


def test_contract_fixture_cannot_claim_qualification() -> None:
    with pytest.raises(ValidationError, match="can never be qualified"):
        WarpXExecutionProfile(
            profile_id="lying_fixture",
            runner_kind=WarpXRunnerKind.CONTRACT_FIXTURE,
            warpx_version="26.07",
            qualification_hash="a" * 64,
            qualified_for_scientific_evidence=True,
        )


def test_pair_summary_rejects_swapped_roles() -> None:
    case = {
        "case_name": "symmetric_mixture_candidate",
        "solver_converged": True,
        "finite_values": True,
        "diagnostic_samples": 10,
        "effective_growth_rate_omega_pe": 0.1,
        "early_rms_amplitude_v_m": 1.0,
        "late_rms_amplitude_v_m": 2.0,
        "amplitude_ratio": 2.0,
        "early_window_sample_count": 41,
        "late_window_sample_count": 41,
        "classification": "unstable",
        "fundamental_amplitude_initial_v_m": 1.0,
        "fundamental_amplitude_final_v_m": 2.0,
        "initial_density_normalized": 1.0,
        "initial_mean_velocity_normalized": 0.0,
        "initial_variance_normalized": 1.0,
        "relative_energy_drift": 0.0,
        "relative_gauss_residual": 0.0,
        "relative_charge_imbalance": 0.0,
        "diagnostic_manifest_hash": "a" * 64,
    }
    with pytest.raises(ValidationError, match="reference summary"):
        WarpXPairSummary(
            runtime_warpx_version="26.07",
            reference=case,
            candidate=case,
        )


def test_missing_runtime_produces_failed_compile_qualification(tmp_path: Path) -> None:
    subject = adapter(tmp_path)
    run = subject.compile_input(build_warpx_experiment())
    record = qualify_warpx_picmi_compiler(
        run,
        python_executable=tmp_path / "missing-python",
        work_directory=tmp_path / "qualification",
    )
    assert not record.passed
    assert not record.scientific_evidence_eligible
    assert not record.checks["runtime_import"]
