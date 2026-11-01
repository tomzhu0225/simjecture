"""Run the Poisson theorem suite inside the Lean capability."""

import json
from pathlib import Path

from lean_check import check

THEOREMS = [
    "Poisson.solve_correct",
    "Poisson.solve_unique",
    "Poisson.trace_correct",
    "Poisson.solve_cost",
    "Poisson.any_solver_lower_bound",
    "Poisson.work_optimal",
]
result = check("Optimality.lean", THEOREMS, output="proof", timeout=90)
Path("proof.json").write_text(json.dumps(result, indent=2) + "\n")
assert result["checked"], result
