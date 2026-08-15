from __future__ import annotations

import sys
from pathlib import Path

import pytest

from conjecture_solver.action_handlers import (
    QUALIFIED_WARPX_CONFIRMATION_ACTION,
    build_qualified_warpx_campaign_graph,
    qualified_warpx_campaign_handlers,
)
from conjecture_solver.adapters.warpx import (
    SubprocessWarpXScheduler,
    WarpXAdapter,
)
from conjecture_solver.control import CampaignControl, CampaignPaused, ControlDirective
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.models import ClaimDisposition, InterventionType
from conjecture_solver.orchestration import (
    ActionStatus,
    MultiActionCampaignRunner,
    OrchestrationDisposition,
)
from conjecture_solver.outbox import ExternalOutbox, InjectedOutboxCrash, OutboxCrashPoint
from conjecture_solver.search import (
    BlindedSearchRequest,
    offline_ai_fixture_strategy,
    offline_qualified_warpx_fixture_strategy,
)
from conjecture_solver.warpx_campaign import (
    QualifiedWarpXCampaignPackage,
    build_qualified_warpx_campaign_package,
)
from conjecture_solver.warpx_confirmation import (
    InjectedWarpXConfirmationCrash,
    WarpXConfirmationCrashPoint,
    WarpXConfirmationDisposition,
    WarpXConfirmationRunner,
    default_warpx_confirmation_design,
    register_qualified_warpx_instrument,
)
from tests.test_warpx import FIXTURE_RUNNER
from tests.test_warpx_qualification import passing_qualification


def qualified_fixture(tmp_path: Path):
    qualification = passing_qualification()
    instrument = register_qualified_warpx_instrument(qualification)
    scheduler = SubprocessWarpXScheduler(
        work_root=tmp_path / "jobs",
        command=(sys.executable, str(FIXTURE_RUNNER)),
        profile=instrument.execution_profile,
        timeout_seconds=10,
    )
    return instrument, WarpXAdapter(scheduler, physics_qualification=qualification)


def test_integrated_campaign_exports_qualified_evidence_and_claim(tmp_path: Path) -> None:
    instrument, adapter = qualified_fixture(tmp_path)
    request = BlindedSearchRequest()
    graph = build_qualified_warpx_campaign_graph(
        request,
        offline_qualified_warpx_fixture_strategy(request),
        instrument,
    )
    campaign_id = "campaign_integrated_qualified_warpx"
    with SQLiteEventLedger(tmp_path / "campaign.sqlite3") as ledger:
        report = MultiActionCampaignRunner(
            campaign_id=campaign_id,
            ledger=ledger,
            graph=graph,
            handlers=qualified_warpx_campaign_handlers(
                instrument=instrument,
                adapter=adapter,
            ),
        ).run()
        package = build_qualified_warpx_campaign_package(
            campaign_id=campaign_id,
            ledger=ledger,
            instrument=instrument,
            campaign_report=report,
        )
        path = package.write(tmp_path / "export")

        assert report.disposition is OrchestrationDisposition.COMPLETED
        assert report.spent_units == 44
        assert report.remaining_units == 0
        assert package.confirmation_report.disposition is WarpXConfirmationDisposition.CONFIRMED
        assert len(package.evidence) == 6
        assert all(item.eligible for item in package.evidence)
        assert package.claim.disposition is ClaimDisposition.REFUTED_WITHIN_MODEL
        assert QualifiedWarpXCampaignPackage.read_verified(path) == package
        assert len(ExternalOutbox(campaign_id=campaign_id, ledger=ledger).projection().intents) == 6
        assert ledger.verify_chain(campaign_id)


@pytest.mark.parametrize("crash_point", list(WarpXConfirmationCrashPoint))
def test_confirmation_matrix_recovers_each_durable_boundary(
    tmp_path: Path,
    crash_point: WarpXConfirmationCrashPoint,
) -> None:
    instrument, adapter = qualified_fixture(tmp_path)
    design = default_warpx_confirmation_design(instrument.qualification)
    campaign_id = f"campaign_matrix_crash_{crash_point.value}"
    ordinal = (
        None
        if crash_point
        in {
            WarpXConfirmationCrashPoint.AFTER_CONFIRMATION_STARTED,
            WarpXConfirmationCrashPoint.AFTER_CONFIRMATION_COMPLETED,
        }
        else 2
    )
    with SQLiteEventLedger() as ledger:
        with pytest.raises(InjectedWarpXConfirmationCrash):
            WarpXConfirmationRunner(
                campaign_id=campaign_id,
                ledger=ledger,
                instrument=instrument,
                adapter=adapter,
                design=design,
                crash_at=crash_point,
                crash_ordinal=ordinal,
            ).run()
        report = WarpXConfirmationRunner(
            campaign_id=campaign_id,
            ledger=ledger,
            instrument=instrument,
            adapter=adapter,
            design=design,
        ).run()
        event_count = len(ledger.load(campaign_id))
        replay = WarpXConfirmationRunner(
            campaign_id=campaign_id,
            ledger=ledger,
            instrument=instrument,
            adapter=adapter,
            design=design,
        ).run()

        assert report == replay
        assert report.disposition is WarpXConfirmationDisposition.CONFIRMED
        assert len(list((tmp_path / "jobs").iterdir())) == 6
        assert len(ledger.load(campaign_id)) == event_count
        assert ledger.verify_chain(campaign_id)


def test_outbox_unknown_outcome_reattaches_same_warpx_job(tmp_path: Path) -> None:
    instrument, adapter = qualified_fixture(tmp_path)
    design = default_warpx_confirmation_design(instrument.qualification)
    campaign_id = "campaign_warpx_outbox_unknown"
    with SQLiteEventLedger() as ledger:
        with pytest.raises(InjectedOutboxCrash):
            WarpXConfirmationRunner(
                campaign_id=campaign_id,
                ledger=ledger,
                instrument=instrument,
                adapter=adapter,
                design=design,
                outbox_crash_at=OutboxCrashPoint.AFTER_EXTERNAL_RESPONSE,
            ).run()
        assert len(list((tmp_path / "jobs").iterdir())) == 1
        report = WarpXConfirmationRunner(
            campaign_id=campaign_id,
            ledger=ledger,
            instrument=instrument,
            adapter=adapter,
            design=design,
        ).run()
        assert report.disposition is WarpXConfirmationDisposition.CONFIRMED
        assert len(list((tmp_path / "jobs").iterdir())) == 6
        states = ExternalOutbox(campaign_id=campaign_id, ledger=ledger).projection().intents
        first = next(state for state in states.values() if len(state.attempts) == 2)
        assert first.receipt is not None


def test_pause_between_matrix_points_preserves_completed_work(tmp_path: Path) -> None:
    instrument, adapter = qualified_fixture(tmp_path)
    design = default_warpx_confirmation_design(instrument.qualification)
    campaign_id = "campaign_warpx_pause"
    with SQLiteEventLedger() as ledger:
        with pytest.raises(InjectedWarpXConfirmationCrash):
            WarpXConfirmationRunner(
                campaign_id=campaign_id,
                ledger=ledger,
                instrument=instrument,
                adapter=adapter,
                design=design,
                crash_at=WarpXConfirmationCrashPoint.AFTER_MATRIX_POINT_COMMITTED,
                crash_ordinal=1,
            ).run()
        control = CampaignControl(campaign_id=campaign_id, ledger=ledger)
        control.issue(
            ControlDirective(
                id="pause_warpx_matrix",
                campaign_id=campaign_id,
                actor="human_operator",
                intervention_type=InterventionType.PAUSE,
                reason="inspect first qualified matrix point",
                scope="future_matrix_points",
                expected_revision=0,
            )
        )
        with pytest.raises(CampaignPaused):
            WarpXConfirmationRunner(
                campaign_id=campaign_id,
                ledger=ledger,
                instrument=instrument,
                adapter=adapter,
                design=design,
                control=control,
            ).run()
        assert len(list((tmp_path / "jobs").iterdir())) == 1
        control.issue(
            ControlDirective(
                id="resume_warpx_matrix",
                campaign_id=campaign_id,
                actor="human_operator",
                intervention_type=InterventionType.RESUME,
                reason="continue frozen matrix",
                scope="future_matrix_points",
                expected_revision=1,
            )
        )
        report = WarpXConfirmationRunner(
            campaign_id=campaign_id,
            ledger=ledger,
            instrument=instrument,
            adapter=adapter,
            design=design,
            control=control,
        ).run()
        assert report.disposition is WarpXConfirmationDisposition.CONFIRMED
        assert len(list((tmp_path / "jobs").iterdir())) == 6


def test_candidate_outside_instrument_scope_fails_before_warpx_dispatch(
    tmp_path: Path,
) -> None:
    instrument, adapter = qualified_fixture(tmp_path)
    request = BlindedSearchRequest()
    graph = build_qualified_warpx_campaign_graph(
        request,
        # This fixture's best candidate is not the exact calibrated 0.95/0.95 pair.
        offline_ai_fixture_strategy(request),
        instrument,
    )
    with SQLiteEventLedger() as ledger:
        report = MultiActionCampaignRunner(
            campaign_id="campaign_scope_mismatch",
            ledger=ledger,
            graph=graph,
            handlers=qualified_warpx_campaign_handlers(
                instrument=instrument,
                adapter=adapter,
            ),
        ).run()
    confirmation = next(
        state
        for state in report.action_states
        if state.action.action_type == QUALIFIED_WARPX_CONFIRMATION_ACTION
    )
    assert confirmation.status is ActionStatus.FAILED
    assert "outside the exact qualified WarpX scope" in confirmation.failure.detail
    assert not (tmp_path / "jobs").exists()


def test_nonconverged_matrix_points_consume_budget_but_never_become_evidence(
    tmp_path: Path,
) -> None:
    qualification = passing_qualification()
    instrument = register_qualified_warpx_instrument(qualification)
    scheduler = SubprocessWarpXScheduler(
        work_root=tmp_path / "jobs",
        command=(sys.executable, "-c", "raise SystemExit(2)"),
        profile=instrument.execution_profile,
        timeout_seconds=10,
    )
    adapter = WarpXAdapter(scheduler, physics_qualification=qualification)
    request = BlindedSearchRequest()
    graph = build_qualified_warpx_campaign_graph(
        request,
        offline_qualified_warpx_fixture_strategy(request),
        instrument,
    )
    campaign_id = "campaign_nonconverged_warpx_matrix"
    with SQLiteEventLedger() as ledger:
        report = MultiActionCampaignRunner(
            campaign_id=campaign_id,
            ledger=ledger,
            graph=graph,
            handlers=qualified_warpx_campaign_handlers(
                instrument=instrument,
                adapter=adapter,
            ),
        ).run()
        package = build_qualified_warpx_campaign_package(
            campaign_id=campaign_id,
            ledger=ledger,
            instrument=instrument,
            campaign_report=report,
        )

    assert report.disposition is OrchestrationDisposition.COMPLETED
    assert report.spent_units == 44
    assert package.confirmation_report.disposition is WarpXConfirmationDisposition.INCONCLUSIVE
    assert len(package.confirmation_report.failures) == 6
    assert len(package.evidence) == 6
    assert not any(item.eligible for item in package.evidence)
    assert package.claim.disposition is ClaimDisposition.UNRESOLVED
