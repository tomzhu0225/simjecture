"""Offline independent checks for the live Codex/Grok integration record."""

import hashlib
import json
from decimal import Decimal, localcontext
from pathlib import Path

root = Path(__file__).resolve().parent
hashes = json.loads((root / "sha256.json").read_text())
for name, expected in hashes.items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
ledger = json.loads((root / "record/hypothesis_ledger.json").read_text())
claims = {claim["id"]: claim for claim in ledger["claims"]}
validation = json.loads((root / "validation.json").read_text())
assert claims["claim_root"]["status"] == "falsified"
assert claims[validation["repair_claim_id"]]["status"] == "supported"
report = json.loads((root / "record/mvp_report.json").read_text())
assert report["status"] == "completed" and report["open_claim_ids"] == []
metrics = json.loads(
    (root / "record/workspace/artifacts/euler_bound_002_prospective.json").read_text()
)["metrics"]
value = 1.0
for _ in range(10):
    value *= 0.9
assert value == metrics["x10"]
with localcontext() as context:
    context.prec = 80
    error = abs(Decimal(-1).exp() - Decimal.from_float(value))
    assert (
        Decimal.from_float(metrics["error_lower"])
        <= error
        <= Decimal.from_float(metrics["error_upper"])
    )
    assert Decimal("0.001") < error < Decimal("0.02")
assert validation["recovery"]["identical_successful_replies"] >= 2
print(
    f"PASS: {len(hashes)} hashes, closed claim frontier, and independent 80-digit error enclosure"
)
