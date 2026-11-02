import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `EulerAdmissible.convex_sum_admissible
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerAdmissible.convex_sum_admissible"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerAdmissible.convex_sum_admissible: {axioms.toList}"
run_cmd do
  let n := `EulerAdmissible.flux_splitting_admissible
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerAdmissible.flux_splitting_admissible"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerAdmissible.flux_splitting_admissible: {axioms.toList}"
run_cmd do
  let n := `EulerAdmissible.computedRatio_bounds
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerAdmissible.computedRatio_bounds"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerAdmissible.computedRatio_bounds: {axioms.toList}"
run_cmd do
  let n := `EulerAdmissible.computed_nonlinear_step_admissible
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerAdmissible.computed_nonlinear_step_admissible"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerAdmissible.computed_nonlinear_step_admissible: {axioms.toList}"
run_cmd do
  let n := `EulerAdmissible.computed_step_conservation
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerAdmissible.computed_step_conservation"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerAdmissible.computed_step_conservation: {axioms.toList}"
run_cmd do
  let n := `EulerAdmissible.unsafe_split_counterexample
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerAdmissible.unsafe_split_counterexample"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerAdmissible.unsafe_split_counterexample: {axioms.toList}"
run_cmd do
  let n := `EulerPrimitiveEnergy.metric_positive
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPrimitiveEnergy.metric_positive"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPrimitiveEnergy.metric_positive: {axioms.toList}"
run_cmd do
  let n := `EulerPrimitiveEnergy.symmetric_principal_part
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPrimitiveEnergy.symmetric_principal_part"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPrimitiveEnergy.symmetric_principal_part: {axioms.toList}"
run_cmd do
  let n := `EulerConservativePrimitive.conserved_derivative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerConservativePrimitive.conserved_derivative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerConservativePrimitive.conserved_derivative: {axioms.toList}"
run_cmd do
  let n := `EulerConservativePrimitive.canonical_flux_derivative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerConservativePrimitive.canonical_flux_derivative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerConservativePrimitive.canonical_flux_derivative: {axioms.toList}"
run_cmd do
  let n := `EulerConservativePrimitive.euler_residual_equivalence
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerConservativePrimitive.euler_residual_equivalence"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerConservativePrimitive.euler_residual_equivalence: {axioms.toList}"
run_cmd do
  let n := `EulerDiscreteEnergy.principal_quadratic_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerDiscreteEnergy.principal_quadratic_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerDiscreteEnergy.principal_quadratic_bound: {axioms.toList}"
run_cmd do
  let n := `EulerDiscreteEnergy.energy_jensen
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerDiscreteEnergy.energy_jensen"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerDiscreteEnergy.energy_jensen: {axioms.toList}"
run_cmd do
  let n := `EulerDiscreteEnergy.frozen_linearized_energy_contraction
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerDiscreteEnergy.frozen_linearized_energy_contraction"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerDiscreteEnergy.frozen_linearized_energy_contraction: {axioms.toList}"
run_cmd do
  let n := `EulerEnergyBounds.box_coercivity
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEnergyBounds.box_coercivity"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEnergyBounds.box_coercivity: {axioms.toList}"
run_cmd do
  let n := `EulerEnergyBounds.box_upper_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEnergyBounds.box_upper_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEnergyBounds.box_upper_bound: {axioms.toList}"
run_cmd do
  let n := `EulerVariableEnergy.variable_principal_energy_defect
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerVariableEnergy.variable_principal_energy_defect"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerVariableEnergy.variable_principal_energy_defect: {axioms.toList}"
run_cmd do
  let n := `EulerGridSobolev.three_dimensional_embedding
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerGridSobolev.three_dimensional_embedding"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerGridSobolev.three_dimensional_embedding: {axioms.toList}"
run_cmd do
  let n := `EulerCoefficientBounds.metric_variation
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerCoefficientBounds.metric_variation"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerCoefficientBounds.metric_variation: {axioms.toList}"
run_cmd do
  let n := `EulerVariableStability.variable_principal_energy_growth
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerVariableStability.variable_principal_energy_growth"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerVariableStability.variable_principal_energy_growth: {axioms.toList}"
run_cmd do
  let n := `EulerVariableStability.varying_metric_energy_increase
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerVariableStability.varying_metric_energy_increase"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerVariableStability.varying_metric_energy_increase: {axioms.toList}"
run_cmd do
  let n := `EulerEntropy.entropy_derivative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropy.entropy_derivative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropy.entropy_derivative: {axioms.toList}"
run_cmd do
  let n := `EulerEntropy.conservative_hessian_derivative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropy.conservative_hessian_derivative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropy.conservative_hessian_derivative: {axioms.toList}"
run_cmd do
  let n := `EulerEntropy.entropy_second_directional
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropy.entropy_second_directional"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropy.entropy_second_directional: {axioms.toList}"
run_cmd do
  let n := `EulerEntropy.hessian_positive
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropy.hessian_positive"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropy.hessian_positive: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyConvexity.entropy_convex
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyConvexity.entropy_convex"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyConvexity.entropy_convex: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyConvexity.averaging_entropy_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyConvexity.averaging_entropy_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyConvexity.averaging_entropy_bound: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyDynamics.canonical_entropy_potential
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyDynamics.canonical_entropy_potential"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyDynamics.canonical_entropy_potential: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyDynamics.smooth_entropy_balance
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyDynamics.smooth_entropy_balance"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyDynamics.smooth_entropy_balance: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyTaylor.entropy_taylor_upper
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyTaylor.entropy_taylor_upper"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyTaylor.entropy_taylor_upper: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyGeometry.hessian_flux_compatibility
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyGeometry.hessian_flux_compatibility"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyGeometry.hessian_flux_compatibility: {axioms.toList}"
run_cmd do
  let n := `EulerFaceEntropy.rusanov_face_entropy_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerFaceEntropy.rusanov_face_entropy_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerFaceEntropy.rusanov_face_entropy_bound: {axioms.toList}"
run_cmd do
  let n := `EulerFiniteVolumeEntropy.update_pairing
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerFiniteVolumeEntropy.update_pairing"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerFiniteVolumeEntropy.update_pairing: {axioms.toList}"
run_cmd do
  let n := `EulerFiniteVolumeEntropy.total_increment_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerFiniteVolumeEntropy.total_increment_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerFiniteVolumeEntropy.total_increment_bound: {axioms.toList}"
run_cmd do
  let n := `EulerFiniteVolumeEntropy.entropy_step_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerFiniteVolumeEntropy.entropy_step_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerFiniteVolumeEntropy.entropy_step_bound: {axioms.toList}"
run_cmd do
  let n := `EulerFiniteVolumeEntropy.entropy_step_dissipation
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerFiniteVolumeEntropy.entropy_step_dissipation"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerFiniteVolumeEntropy.entropy_step_dissipation: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyRegion.nonlinear_step_entropy_from_region
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyRegion.nonlinear_step_entropy_from_region"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyRegion.nonlinear_step_entropy_from_region: {axioms.toList}"
run_cmd do
  let n := `EulerPhysicalRegion.region_convex
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPhysicalRegion.region_convex"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPhysicalRegion.region_convex: {axioms.toList}"
run_cmd do
  let n := `EulerPhysicalRegion.conservative_hessian_squares
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPhysicalRegion.conservative_hessian_squares"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPhysicalRegion.conservative_hessian_squares: {axioms.toList}"
run_cmd do
  let n := `EulerInitialRegion.initial_family_in_region
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerInitialRegion.initial_family_in_region"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerInitialRegion.initial_family_in_region: {axioms.toList}"
run_cmd do
  let n := `EulerPhysicalFluxBounds.flux_derivative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPhysicalFluxBounds.flux_derivative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPhysicalFluxBounds.flux_derivative: {axioms.toList}"
run_cmd do
  let n := `EulerPhysicalFluxBounds.concrete_region_bounds
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPhysicalFluxBounds.concrete_region_bounds"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPhysicalFluxBounds.concrete_region_bounds: {axioms.toList}"
run_cmd do
  let n := `EulerPhysicalFluxBounds.coarse_viscosity_requirement
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPhysicalFluxBounds.coarse_viscosity_requirement"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPhysicalFluxBounds.coarse_viscosity_requirement: {axioms.toList}"
run_cmd do
  let n := `EulerPhysicalFluxBounds.initial_family_contains_rest
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPhysicalFluxBounds.initial_family_contains_rest"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPhysicalFluxBounds.initial_family_contains_rest: {axioms.toList}"
run_cmd do
  let n := `EulerPhysicalFluxBounds.current_speeds_fail_any_region_constants
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPhysicalFluxBounds.current_speeds_fail_any_region_constants"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPhysicalFluxBounds.current_speeds_fail_any_region_constants: {axioms.toList}"
run_cmd do
  let n := `EulerLogMean.jump_identity
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerLogMean.jump_identity"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerLogMean.jump_identity: {axioms.toList}"
run_cmd do
  let n := `EulerLogMean.between
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerLogMean.between"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerLogMean.between: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyConservativeFlux.canonical_entropy_conservation
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyConservativeFlux.canonical_entropy_conservation"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyConservativeFlux.canonical_entropy_conservation: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyConservativeFlux.dissipative_flux_consistency
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyConservativeFlux.dissipative_flux_consistency"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyConservativeFlux.dissipative_flux_consistency: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyConservativeFlux.face_entropy_stable
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyConservativeFlux.face_entropy_stable"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyConservativeFlux.face_entropy_stable: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyCandidateStep.gradient_strict_monotonicity
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyCandidateStep.gradient_strict_monotonicity"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyCandidateStep.gradient_strict_monotonicity: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyCandidateStep.total_entropy_trial_derivative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyCandidateStep.total_entropy_trial_derivative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyCandidateStep.total_entropy_trial_derivative: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyCandidateStep.zero_dissipation_stationary
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyCandidateStep.zero_dissipation_stationary"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyCandidateStep.zero_dissipation_stationary: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyCandidateStep.exists_acceptable_halving
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyCandidateStep.exists_acceptable_halving"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyCandidateStep.exists_acceptable_halving: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyCandidateStep.backtracked_step
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyCandidateStep.backtracked_step"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyCandidateStep.backtracked_step: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyCandidateStep.earlier_trials_rejected
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyCandidateStep.earlier_trials_rejected"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyCandidateStep.earlier_trials_rejected: {axioms.toList}"
run_cmd do
  let n := `EulerPressurePolynomial.hessian_polynomial
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPressurePolynomial.hessian_polynomial"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPressurePolynomial.hessian_polynomial: {axioms.toList}"
run_cmd do
  let n := `EulerPressurePolynomial.path_curvature_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPressurePolynomial.path_curvature_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPressurePolynomial.path_curvature_bound: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyStepBounds.trial_path_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyStepBounds.trial_path_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyStepBounds.trial_path_bound: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyStepBounds.total_entropy_upper
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyStepBounds.total_entropy_upper"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyStepBounds.total_entropy_upper: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyStepBounds.below_cap_acceptable
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyStepBounds.below_cap_acceptable"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyStepBounds.below_cap_acceptable: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyStepBounds.quantitative_retry_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyStepBounds.quantitative_retry_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyStepBounds.quantitative_retry_bound: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyStepBounds.accepted_ratio_lower_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyStepBounds.accepted_ratio_lower_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyStepBounds.accepted_ratio_lower_bound: {axioms.toList}"
run_cmd do
  let n := `EulerECFluxBounds.flux_consistency_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerECFluxBounds.flux_consistency_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerECFluxBounds.flux_consistency_bound: {axioms.toList}"
run_cmd do
  let n := `EulerECFluxBounds.flux_consistency_bound_right
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerECFluxBounds.flux_consistency_bound_right"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerECFluxBounds.flux_consistency_bound_right: {axioms.toList}"
run_cmd do
  let n := `EulerECFluxBounds.flux_symmetric
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerECFluxBounds.flux_symmetric"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerECFluxBounds.flux_symmetric: {axioms.toList}"
run_cmd do
  let n := `EulerRegionEscape.initial_in_region
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerRegionEscape.initial_in_region"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerRegionEscape.initial_in_region: {axioms.toList}"
run_cmd do
  let n := `EulerRegionEscape.center_energy_increment
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerRegionEscape.center_energy_increment"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerRegionEscape.center_energy_increment: {axioms.toList}"
run_cmd do
  let n := `EulerRegionEscape.accepted_step_leaves_region
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerRegionEscape.accepted_step_leaves_region"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerRegionEscape.accepted_step_leaves_region: {axioms.toList}"
run_cmd do
  let n := `EulerGridPoincare.vector_poincare
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerGridPoincare.vector_poincare"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerGridPoincare.vector_poincare: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyDecay.entropy_excess_nonnegative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyDecay.entropy_excess_nonnegative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyDecay.entropy_excess_nonnegative: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyDecay.entropy_excess_poincare
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyDecay.entropy_excess_poincare"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyDecay.entropy_excess_poincare: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyDecay.backtracked_step_decay
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyDecay.backtracked_step_decay"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyDecay.backtracked_step_decay: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyDecay.computed_trace_entropy_loss
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyDecay.computed_trace_entropy_loss"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyDecay.computed_trace_entropy_loss: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyError.entropy_lipschitz
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyError.entropy_lipschitz"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyError.entropy_lipschitz: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyError.integrated_entropy_error
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyError.integrated_entropy_error"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyError.integrated_entropy_error: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyError.entropy_gap_error_lower_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyError.entropy_gap_error_lower_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyError.entropy_gap_error_lower_bound: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyIntegral.entropy_divergence_zero
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyIntegral.entropy_divergence_zero"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyIntegral.entropy_divergence_zero: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyIntegral.periodic_entropy_conservation
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyIntegral.periodic_entropy_conservation"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyIntegral.periodic_entropy_conservation: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyIntegral.periodic_conserved_integral
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyIntegral.periodic_conserved_integral"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyIntegral.periodic_conserved_integral: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyIntegral.cube_measure_univ
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyIntegral.cube_measure_univ"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyIntegral.cube_measure_univ: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyIntegral.normalized_entropy_conservation
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyIntegral.normalized_entropy_conservation"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyIntegral.normalized_entropy_conservation: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyIntegral.normalized_conserved_integral
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyIntegral.normalized_conserved_integral"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyIntegral.normalized_conserved_integral: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyIntegral.normalized_error_lower_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyIntegral.normalized_error_lower_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyIntegral.normalized_error_lower_bound: {axioms.toList}"
run_cmd do
  let n := `EulerEntropyIntegral.physical_error_from_initial_entropy
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEntropyIntegral.physical_error_from_initial_entropy"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEntropyIntegral.physical_error_from_initial_entropy: {axioms.toList}"
