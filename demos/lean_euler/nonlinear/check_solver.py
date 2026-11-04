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
    "EulerLogMean.jump_identity",
    "EulerLogMean.between",
    "EulerEntropyConservativeFlux.canonical_entropy_conservation",
    "EulerEntropyConservativeFlux.dissipative_flux_consistency",
    "EulerEntropyConservativeFlux.face_entropy_stable",
    "EulerEntropyCandidateStep.gradient_strict_monotonicity",
    "EulerEntropyCandidateStep.total_entropy_trial_derivative",
    "EulerEntropyCandidateStep.zero_dissipation_stationary",
    "EulerEntropyCandidateStep.exists_acceptable_halving",
    "EulerEntropyCandidateStep.backtracked_step",
    "EulerEntropyCandidateStep.earlier_trials_rejected",
    "EulerPressurePolynomial.hessian_polynomial",
    "EulerPressurePolynomial.path_curvature_bound",
    "EulerEntropyStepBounds.trial_path_bound",
    "EulerEntropyStepBounds.total_entropy_upper",
    "EulerEntropyStepBounds.below_cap_acceptable",
    "EulerEntropyStepBounds.quantitative_retry_bound",
    "EulerEntropyStepBounds.accepted_ratio_lower_bound",
    "EulerECFluxBounds.flux_consistency_bound",
    "EulerECFluxBounds.flux_consistency_bound_right",
    "EulerECFluxBounds.flux_symmetric",
    "EulerRegionEscape.initial_in_region",
    "EulerRegionEscape.center_energy_increment",
    "EulerRegionEscape.accepted_step_leaves_region",
    "EulerGridPoincare.vector_poincare",
    "EulerEntropyDecay.entropy_excess_nonnegative",
    "EulerEntropyDecay.entropy_excess_poincare",
    "EulerEntropyDecay.backtracked_step_decay",
    "EulerEntropyDecay.computed_trace_entropy_loss",
    "EulerEntropyError.entropy_lipschitz",
    "EulerEntropyError.integrated_entropy_error",
    "EulerEntropyError.entropy_gap_error_lower_bound",
    "EulerEntropyIntegral.entropy_divergence_zero",
    "EulerEntropyIntegral.periodic_entropy_conservation",
    "EulerEntropyIntegral.periodic_conserved_integral",
    "EulerEntropyIntegral.cube_measure_univ",
    "EulerEntropyIntegral.normalized_entropy_conservation",
    "EulerEntropyIntegral.normalized_conserved_integral",
    "EulerEntropyIntegral.normalized_error_lower_bound",
    "EulerEntropyIntegral.physical_error_from_initial_entropy",
    "EulerHatReconstruction.weight3_sum",
    "EulerHatReconstruction.weight3_integral",
    "EulerHatReconstruction.reconstruction_continuous",
    "EulerHatReconstruction.reconstruction_in_region",
    "EulerHatReconstruction.reconstruction_mean",
    "EulerHatReconstruction.reconstruction_entropy",
    "EulerHatReconstruction.reconstruction_boundary",
    "EulerHatReconstruction.reconstruction_nodes",
    "EulerHatReconstruction.reconstructed_physical_error_lower_bound",
    "EulerInitialAverages.initial_integral_mean",
    "EulerInitialAverages.average_density_pressure_error",
    "EulerInitialExcess.initial_entropy_nonnegative",
    "EulerInitialExcess.uniform_initial_excess",
    "EulerExcessAccuracy.reconstruction_excess_accuracy",
    "EulerExcessAccuracy.family_final_excess_bound",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = args.output / "Solver.lean"
    assemble(source)
    # The previous 77-statement assembly took 145.30 seconds. Allow the added
    # space-time integral proofs to finish without changing kernel proof limits.
    result = check(source, THEOREMS, output=args.output / "proof", timeout=240)
    here = Path(__file__).resolve().parent
    record = dict(
        result=result,
        component_sha256={
            name: hashlib.sha256((here / "formal" / name).read_bytes()).hexdigest()
            for name in COMPONENTS
        },
        scope=(
            "Checked nonlinear Euler foundations, not a completed solver-optimality theorem. "
            "The actual Rusanov step has positivity/conservation; a separate principal map "
            "has frozen and conditional variable-coefficient energy estimates. Exact "
            "counterexamples expose varying-metric noncontraction, a failed global "
            "diffusion criterion, and noninvariance of the chosen state region for general "
            "compression data outside the target family. Actual physical entropy calculus "
            "and flux consistency are checked. The alternative existing logarithmic-mean "
            "EC+LF flux has face entropy stability and a terminating exact-real one-step "
            "halving search, with state-dependent acceptance/retry bounds. Conditional "
            "finite-trace entropy loss follows from a periodic Poincare estimate. These "
            "results do not prove target-time completion or verify floating-point guards. "
            "Differentiable positive periodic Euler fields have proved global entropy and "
            "conserved-state integrals. The actual continuous cell-centered tensor-hat "
            "reconstruction has nonnegative partition weights, proved integrals, periodic "
            "faces, exact center interpolation, region membership, mean preservation and "
            "an integral entropy bound. Entropy gaps give necessary physical L1 error "
            "lower bounds. Exact global initial averages and a uniform initial entropy "
            "excess of at least 1/33 are proved for the entire target parameter family. "
            "For an actual smooth periodic Euler solution with those initial data and "
            "final exact/grid states in the region, physical reconstruction error e "
            "forces normalized final grid excess at least 1/33-320e, without assuming "
            "matching numerical and continuum means. The actual cell-average initializer, "
            "common smooth existence, uniform numerical trajectories, full spatial/time "
            "accuracy upper bound, justified competitor class and matching complete "
            "computational-work bounds remain unproved."
        ),
    )
    (args.output / "solver-formal.json").write_text(json.dumps(record, indent=2) + "\n")
    assert result["checked"], result
    print(json.dumps({"status": result["status"], "theorems": len(THEOREMS)}))


if __name__ == "__main__":
    main()
