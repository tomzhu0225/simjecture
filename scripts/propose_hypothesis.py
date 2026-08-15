"""Opt-in live generation of a typed proposal; no simulation is submitted."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from conjecture_solver.adapters.fake import DeterministicKineticAdapter
from conjecture_solver.adapters.pic import ElectrostaticPICAdapter
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.llm import ModelRoute, OpenAICompatibleClient
from conjecture_solver.outbox import JournaledCompletionClient
from conjecture_solver.proposals import (
    ProposalGenerator,
    pic_proposal_request,
    planted_proposal_request,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/proposal_record.json")
    parser.add_argument("--task", choices=("pic", "analytic"), default="pic")
    parser.add_argument("--max-tokens", type=int, default=16384)
    parser.add_argument("--use-glm", action="store_true")
    parser.add_argument("--reason")
    parser.add_argument("--journal-ledger", default="model_calls.sqlite3")
    parser.add_argument("--journal-campaign-id")
    args = parser.parse_args()

    route = ModelRoute.DEFAULT
    if args.use_glm:
        if not args.reason:
            parser.error("--use-glm requires --reason")
        route = ModelRoute.ESCALATION

    if args.task == "pic":
        adapter = ElectrostaticPICAdapter()
        request = pic_proposal_request()
    else:
        adapter = DeterministicKineticAdapter()
        request = planted_proposal_request()
    journal_campaign_id = args.journal_campaign_id or f"model_journal_{request.id}"
    with SQLiteEventLedger(args.journal_ledger) as ledger:
        client = JournaledCompletionClient(
            campaign_id=journal_campaign_id,
            ledger=ledger,
            client=OpenAICompatibleClient.from_environment(),
        )
        generator = ProposalGenerator(
            client=client,
            adapter=adapter,
        )
        record = generator.generate(
            request,
            route=route,
            escalation_reason=args.reason,
            max_tokens=args.max_tokens,
        )
        if not ledger.verify_chain(journal_campaign_id):
            raise RuntimeError("model-call journal hash chain failed verification")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(record.model_dump_json(indent=2) + "\n")
    os.replace(temporary, output)
    print(f"proposal={output}")
    print(f"model={record.model_calls[-1].model}")
    print(f"attempts={len(record.model_calls)}")
    print(f"model_journal={args.journal_ledger}")
    print("admission=valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
