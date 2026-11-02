"""Audit solver foundations; this is not a continuum-accuracy certificate."""

import argparse
import hashlib
import json
from pathlib import Path

from assemble_solver import COMPONENTS, assemble

try:
    from lean_check import check
except ImportError:
    from conjecture_solver.lean_check import check

THEOREMS = [
    "EulerAdmissible.convex_sum_admissible",
    "EulerAdmissible.flux_splitting_admissible",
    "EulerAdmissible.computedRatio_bounds",
    "EulerAdmissible.computed_nonlinear_step_admissible",
    "EulerAdmissible.computed_step_conservation",
    "EulerAdmissible.unsafe_split_counterexample",
    "EulerPrimitiveEnergy.metric_positive",
    "EulerPrimitiveEnergy.symmetric_principal_part",
    "EulerConservativePrimitive.conserved_derivative",
    "EulerConservativePrimitive.canonical_flux_derivative",
    "EulerConservativePrimitive.euler_residual_equivalence",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.output / "Solver.lean"
    assemble(source)
    result = check(source, THEOREMS, output=args.output / "proof", timeout=150)
    here = Path(__file__).resolve().parent
    record = dict(
        result=result,
        component_sha256={
            name: hashlib.sha256((here / "formal" / name).read_bytes()).hexdigest()
            for name in COMPONENTS
        },
        scope=(
            "Nonlinear update admissibility/conservation and a differentiated conservative-to-"
            "primitive energy-form connection. Existence, global stability, continuum solver "
            "accuracy and matching work optimality remain unproved."
        ),
    )
    (args.output / "solver-formal.json").write_text(json.dumps(record, indent=2) + "\n")
    assert result["checked"], result
    print(json.dumps({"status": result["status"], "theorems": len(THEOREMS)}))


if __name__ == "__main__":
    main()
