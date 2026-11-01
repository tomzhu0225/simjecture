"""Check reference identities and conditional error-to-work lemmas."""

import json
from pathlib import Path

from lean_check import check

THEOREMS = {
    "ContactReference.lean": [
        "ContactReference.contact_pressure",
        "ContactReference.contact_velocity",
        "ContactReference.transported_contact_residual",
        "ContactReference.sinusoidal_transport_jet",
        "ContactReference.density_controls_components",
    ],
    "WaveDerivative.lean": ["WaveDerivative.wave_derivative", "WaveDerivative.phase_transport"],
    "ErrorWork.lean": [
        "ErrorWork.stencil_nonexpansive",
        "ErrorWork.accumulate_error",
        "ErrorWork.first_order_budget",
        "ErrorWork.total_work_bound",
        "ErrorWork.smallest_certified_grid_minimizes_work",
    ],
}
results = {
    name: check(name, names, output=Path(name).stem, timeout=90) for name, names in THEOREMS.items()
}
Path("formal-results.json").write_text(json.dumps(results, indent=2) + "\n")
assert all(r["checked"] for r in results.values()), results
