"""Evaluate an admitted strategy and independently confirm its frozen witness."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from conjecture_solver.confirmation import (
    PICConfirmationRunner,
    confirmation_design_from_search,
)
from conjecture_solver.ledger import SQLiteEventLedger
from conjecture_solver.search import (
    BlindedSearchRequest,
    BlindedSearchRunner,
    SearchStrategy,
    baseline_strategies,
)


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("strategy")
    parser.add_argument("--campaign-id", default="campaign_blinded_search_v1")
    parser.add_argument("--ledger", default="blinded_search.sqlite3")
    parser.add_argument("--output", default="artifacts/blinded_search")
    parser.add_argument("--skip-confirmation", action="store_true")
    args = parser.parse_args()

    request = BlindedSearchRequest()
    ai_strategy = SearchStrategy.model_validate_json(Path(args.strategy).read_text())
    output = Path(args.output)
    with SQLiteEventLedger(args.ledger) as ledger:
        report = BlindedSearchRunner(
            campaign_id=args.campaign_id,
            ledger=ledger,
            request=request,
            strategies=(ai_strategy, *baseline_strategies(request)),
        ).run()
        _write_atomic(
            output / "blinded_search_report.json",
            report.model_dump_json(indent=2) + "\n",
        )
        confirmation = None
        if not args.skip_confirmation:
            confirmation = PICConfirmationRunner(
                campaign_id=args.campaign_id,
                ledger=ledger,
                design=confirmation_design_from_search(report),
            ).run()
            _write_atomic(
                output / "pic_confirmation_report.json",
                confirmation.model_dump_json(indent=2) + "\n",
            )
        if not ledger.verify_chain(args.campaign_id):
            raise RuntimeError("search ledger hash chain failed verification")

    print(f"campaign={args.campaign_id}")
    for result in report.method_results:
        print(
            f"method={result.method.value} "
            f"first_witness={result.first_falsifying_ordinal} "
            f"best_separation={result.best_outcome_separation}"
        )
    print(f"confirmation_candidate={report.confirmation_candidate_id}")
    if confirmation is not None:
        print(f"confirmation={confirmation.disposition.value}")
        print(
            f"confirmation_attempts={confirmation.confirming_attempts}/"
            f"{len(confirmation.attempts)}"
        )
    print(f"output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
