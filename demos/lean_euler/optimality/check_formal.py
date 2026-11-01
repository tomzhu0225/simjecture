"""Assemble and audit the exact scope, retaining a failed algorithm mutation."""

import argparse
import hashlib
import json
from pathlib import Path

from assemble import assemble

try:
    from lean_check import check
except ImportError:
    from conjecture_solver.lean_check import check

THEOREMS = [
    "Certificate.admissible_is_classical_euler",
    "Certificate.family_nonempty",
    "ShearEuler.pressure_of_conserved",
    "ShearEuler.inverse_flow",
    "ShearEuler.flow_inverse",
    "Grid.center_covers_cube",
    "Grid.centers_separated",
    "Recovery.exists_base_bump",
    "Recovery.perturb_admissible",
    "Optimality.exists_unqueried_cell",
    "Optimality.accuracy_at_tolerance",
    "Optimality.sampling_values",
    "Optimality.euler_algorithm_queries",
    "Work.solver_program_matches_query_algorithm",
    "Work.solver_work_exact",
    "Work.total_work_upper",
    "Machines.same_answers",
    "Machines.tree_correct",
    "Machines.general_machine_work_lower",
    "Machines.certified_general_optimality",
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--negative-control", action="store_true")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.output / "Combined.lean"
    assemble(source)
    result = check(source, THEOREMS, output=args.output / "proof", timeout=120)
    report = {"positive": result}
    if args.negative_control:
        content = source.read_text()
        before = "def resolution (L eps : ℝ) : ℕ := ⌈3*L/(4*eps)⌉₊"
        after = "def resolution (L eps : ℝ) : ℕ := ⌈L/(4*eps)⌉₊"
        assert content.count(before) == 1
        altered = args.output / "InsufficientResolution.lean"
        altered.write_text(content.replace(before, after))
        report["negative"] = check(
            altered,
            ["Machines.certified_general_optimality"],
            output=args.output / "negative",
            timeout=120,
        )
        report["negative_explanation"] = (
            "Reduce the solver resolution by a factor of three. Its previous "
            "accuracy proof no longer checks; this is not itself a formal "
            "disproof of the modified solver."
        )
    here = Path(__file__).resolve().parent
    report["component_sha256"] = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(here.glob("*.lean"))
    }
    report["scope"] = (
        "Exact-real classical Euler solution and minimax-order work "
        "optimality for the frozen affine-shear density-oracle family. No "
        "general Euler or floating-point verification claim."
    )
    (args.output / "formal-results.json").write_text(json.dumps(report, indent=2) + "\n")
    assert result["checked"], result
    if args.negative_control:
        assert not report["negative"]["checked"], report["negative"]
    print(
        json.dumps(
            {
                "status": result["status"],
                "theorems": len(THEOREMS),
                "negative": report.get("negative", {}).get("status"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
