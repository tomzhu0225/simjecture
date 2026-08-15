"""Opt-in live blinded candidate selection; no physics evaluator is called."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.llm import ModelRoute, OpenAICompatibleClient
from conjecture_solver.outbox import JournaledCompletionClient
from conjecture_solver.search import AISearchStrategyGenerator, BlindedSearchRequest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/live_blinded_strategy.json")
    parser.add_argument("--max-tokens", type=int, default=16384)
    parser.add_argument("--use-glm", action="store_true")
    parser.add_argument("--reason")
    parser.add_argument("--journal-ledger", default="model_calls.sqlite3")
    parser.add_argument("--journal-campaign-id", default="model_journal_blinded_search_v1")
    args = parser.parse_args()

    route = ModelRoute.DEFAULT
    if args.use_glm:
        if not args.reason:
            parser.error("--use-glm requires --reason")
        route = ModelRoute.ESCALATION

    with SQLiteEventLedger(args.journal_ledger) as ledger:
        strategy = AISearchStrategyGenerator(
            JournaledCompletionClient(
                campaign_id=args.journal_campaign_id,
                ledger=ledger,
                client=OpenAICompatibleClient.from_environment(),
            )
        ).generate(
            BlindedSearchRequest(),
            route=route,
            escalation_reason=args.reason,
            max_tokens=args.max_tokens,
        )
        if not ledger.verify_chain(args.journal_campaign_id):
            raise RuntimeError("model-call journal hash chain failed verification")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(strategy.model_dump_json(indent=2) + "\n")
    os.replace(temporary, output)
    print(f"strategy={output}")
    print(f"model={strategy.model_calls[-1].model}")
    print(f"attempts={len(strategy.model_calls)}")
    print(f"candidates={len(strategy.proposals)}")
    print(f"model_journal={args.journal_ledger}")
    print("admission=valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
