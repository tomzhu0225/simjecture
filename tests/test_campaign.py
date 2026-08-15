from __future__ import annotations

from pathlib import Path

import pytest

from conjecture_solver.adapters.fake import (
    DeterministicKineticAdapter,
    DeterministicKineticScheduler,
)
from conjecture_solver.campaign import (
    CampaignRunner,
    CrashPoint,
    InjectedCrash,
    planted_campaign_problem,
)
from conjecture_solver.discovery import DiscoveryPackage
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.models import AttemptOutcome, ClaimDisposition, EvidenceRole

EXPECTED_EVENTS = [
    "campaign_created",
    "action_planned",
    "attempt_recorded",
    "job_submitted",
    "result_retrieved",
    "attempt_completed",
    "evidence_ingested",
    "claim_evaluated",
    "campaign_completed",
]


def runner(
    ledger: SQLiteEventLedger,
    adapter: DeterministicKineticAdapter,
    *,
    crash_at: CrashPoint | None = None,
    campaign_id: str = "campaign_test",
) -> CampaignRunner:
    hypothesis, experiment = planted_campaign_problem()
    return CampaignRunner(
        campaign_id=campaign_id,
        ledger=ledger,
        adapter=adapter,
        hypothesis=hypothesis,
        experiment=experiment,
        crash_at=crash_at,
    )


def test_campaign_produces_scoped_refutation_and_hash_chain() -> None:
    scheduler = DeterministicKineticScheduler()
    adapter = DeterministicKineticAdapter(scheduler)
    with SQLiteEventLedger() as ledger:
        package = runner(ledger, adapter).run()
        events = ledger.load("campaign_test")

        assert [event.event_type for event in events] == EXPECTED_EVENTS
        assert ledger.verify_chain("campaign_test")
        assert package.verify_hash()
        assert package.attempt.outcome is AttemptOutcome.SUCCESS
        assert package.evidence.role is EvidenceRole.DISCOVERY
        assert package.claim.disposition is ClaimDisposition.REFUTED_WITHIN_MODEL
        assert adapter.submitted_job_count == 1
        assert events.index(next(e for e in events if e.event_type == "attempt_recorded")) < (
            events.index(next(e for e in events if e.event_type == "job_submitted"))
        )


@pytest.mark.parametrize("crash_at", list(CrashPoint))
def test_every_transaction_boundary_recovers_exactly_once(
    tmp_path: Path,
    crash_at: CrashPoint,
) -> None:
    ledger_path = tmp_path / f"{crash_at.value}.sqlite3"
    scheduler = DeterministicKineticScheduler()
    adapter = DeterministicKineticAdapter(scheduler)
    with SQLiteEventLedger(ledger_path) as ledger:
        with pytest.raises(InjectedCrash) as raised:
            runner(ledger, adapter, crash_at=crash_at).run()
        assert raised.value.point is crash_at

    # A fresh ledger connection models a process restart. The adapter's
    # stable submission key models reattachment to an external scheduler.
    with SQLiteEventLedger(ledger_path) as recovered:
        recovered_adapter = DeterministicKineticAdapter(scheduler)
        package = runner(recovered, recovered_adapter).run()
        first_count = len(recovered.load("campaign_test"))
        replayed = runner(recovered, DeterministicKineticAdapter(scheduler)).run()
        events = recovered.load("campaign_test")

        assert [event.event_type for event in events] == EXPECTED_EVENTS
        assert len(events) == len(set(event.idempotency_key for event in events))
        assert len(events) == first_count
        assert recovered.verify_chain("campaign_test")
        assert package.package_hash == replayed.package_hash
        assert recovered_adapter.submitted_job_count == 1


def test_discovery_package_round_trip_detects_tampering(tmp_path: Path) -> None:
    with SQLiteEventLedger() as ledger:
        package = runner(ledger, DeterministicKineticAdapter()).run()
    path = package.write(tmp_path)
    loaded = DiscoveryPackage.read_verified(path)
    assert loaded == package

    document = path.read_text().replace(
        "refuted_within_model",
        "unresolved",
        1,
    )
    path.write_text(document)
    with pytest.raises(ValueError, match="hash does not match"):
        DiscoveryPackage.read_verified(path)
