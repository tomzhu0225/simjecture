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
    "EulerDiscreteEnergy.principal_quadratic_bound",
    "EulerDiscreteEnergy.energy_jensen",
    "EulerDiscreteEnergy.frozen_linearized_energy_contraction",
    "EulerEnergyBounds.box_coercivity",
    "EulerEnergyBounds.box_upper_bound",
    "EulerVariableEnergy.variable_principal_energy_defect",
    "EulerGridSobolev.three_dimensional_embedding",
    "EulerCoefficientBounds.metric_variation",
    "EulerVariableStability.variable_principal_energy_growth",
    "EulerVariableStability.varying_metric_energy_increase",
    "EulerEntropy.entropy_derivative",
    "EulerEntropy.conservative_hessian_derivative",
    "EulerEntropy.entropy_second_directional",
    "EulerEntropy.hessian_positive",
    "EulerEntropyConvexity.entropy_convex",
    "EulerEntropyConvexity.averaging_entropy_bound",
    "EulerEntropyDynamics.canonical_entropy_potential",
    "EulerEntropyDynamics.smooth_entropy_balance",
    "EulerEntropyTaylor.entropy_taylor_upper",
    "EulerEntropyGeometry.hessian_flux_compatibility",
    "EulerFaceEntropy.rusanov_face_entropy_bound",
    "EulerFiniteVolumeEntropy.update_pairing",
    "EulerFiniteVolumeEntropy.total_increment_bound",
    "EulerFiniteVolumeEntropy.entropy_step_bound",
    "EulerFiniteVolumeEntropy.entropy_step_dissipation",
    "EulerEntropyRegion.nonlinear_step_entropy_from_region",
    "EulerPhysicalRegion.region_convex",
    "EulerPhysicalRegion.conservative_hessian_squares",
    "EulerInitialRegion.initial_family_in_region",
    "EulerPhysicalFluxBounds.flux_derivative",
    "EulerPhysicalFluxBounds.concrete_region_bounds",
    "EulerPhysicalFluxBounds.coarse_viscosity_requirement",
    "EulerPhysicalFluxBounds.initial_family_contains_rest",
    "EulerPhysicalFluxBounds.current_speeds_fail_any_region_constants",
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
            "Nonlinear update admissibility/conservation; conservative-to-primitive derivative "
            "connection; frozen and spatially varying principal-update energy estimates; "
            "grid-independent 3D embedding; exact noncontraction witness; actual entropy "
            "derivatives, convexity, finite averaging bound and local Euler entropy balance. "
            "The variable-coefficient estimate assumes explicit state and spatial-difference "
            "bounds. Existence, nonlinear full-solve stability, continuum solver accuracy "
            "and matching work optimality remain unproved. Actual nonlinear finite-step "
            "entropy dissipation is checked under explicit convex-region, curvature, flux, "
            "viscosity and timestep conditions. Uniform trajectory membership and those "
            "conditions for the current numerical settings remain unproved."
            " Concrete physical-region bounds and initial-family membership are checked. "
            "A checked obstruction shows that the global sufficient viscosity criterion "
            "cannot certify the current wave-speed recipe on that region, even with "
            "improved valid curvature constants. It does not refute actual solver stability."
        ),
    )
    (args.output / "solver-formal.json").write_text(json.dumps(record, indent=2) + "\n")
    assert result["checked"], result
    print(json.dumps({"status": result["status"], "theorems": len(THEOREMS)}))


if __name__ == "__main__":
    main()
