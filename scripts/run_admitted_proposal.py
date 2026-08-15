"""Execute a previously admitted proposal without making another model call."""

from __future__ import annotations

import argparse
from pathlib import Path

from conjecture_solver.adapters.fake import DeterministicKineticAdapter
from conjecture_solver.adapters.pic import ElectrostaticPICAdapter
from conjecture_solver.campaign import CampaignRunner
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.proposals import ProposalRecord, record_admitted_proposal


def adapter_for(model_family: str) -> DeterministicKineticAdapter | ElectrostaticPICAdapter:
    if model_family == "electrostatic_1d_pic_vlasov_poisson":
        return ElectrostaticPICAdapter()
    if model_family == "linearized_1d_electrostatic_vlasov_poisson":
        return DeterministicKineticAdapter()
    raise ValueError(f"no execution adapter is registered for {model_family}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("proposal")
    parser.add_argument("--campaign-id")
    parser.add_argument("--ledger", default="proposal_campaign.sqlite3")
    parser.add_argument("--output", default="artifacts/proposal_campaign")
    args = parser.parse_args()

    record = ProposalRecord.model_validate_json(Path(args.proposal).read_text())
    campaign_id = args.campaign_id or f"campaign_{record.request.id}"
    adapter = adapter_for(record.draft.hypothesis.domain.model_family)
    adapter_validation = adapter.validate(record.draft.experiment)
    if not adapter_validation.valid:
        raise ValueError("proposal no longer passes adapter validation")

    with SQLiteEventLedger(args.ledger) as ledger:
        record_admitted_proposal(ledger, campaign_id=campaign_id, record=record)
        package = CampaignRunner(
            campaign_id=campaign_id,
            ledger=ledger,
            adapter=adapter,
            hypothesis=record.draft.hypothesis,
            experiment=record.draft.experiment,
        ).run()
        if not ledger.verify_chain(campaign_id):
            raise RuntimeError("campaign ledger hash chain failed verification")
        path = package.write(args.output)

    print(f"campaign={campaign_id}")
    print(f"proposal_model={record.model_calls[-1].model}")
    print(f"claim_disposition={package.claim.disposition.value}")
    print(f"package_hash={package.package_hash}")
    print(f"package={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
