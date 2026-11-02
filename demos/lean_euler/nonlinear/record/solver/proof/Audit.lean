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
