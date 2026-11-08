"""Run under the installed lean-4.24.0 capability."""

import json
from pathlib import Path

from lean_check import check

claims = {}
for source, names in {
    "Decay.lean": ["Decay.nonnegative", "Decay.counterexample"],
    "Conservation.lean": [
        "FiniteVolume.conservation",
        "FiniteVolume.conservation3D",
        "FiniteVolume.constant_state",
    ],
    "Witness.lean": ["EulerWitness.initial_admissible", "EulerWitness.negative_density"],
}.items():
    claims[source] = check(source, names, output=source.removesuffix(".lean"), timeout=60)
Path("proofs.json").write_text(json.dumps(claims, indent=2) + "\n")
assert all(c["checked"] for c in claims.values())
