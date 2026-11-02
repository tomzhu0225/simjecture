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
  let n := `EulerAdmissible.flux_splitting_admissible
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerAdmissible.flux_splitting_admissible"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerAdmissible.flux_splitting_admissible: {axioms.toList}"
  let n := `EulerAdmissible.computedRatio_bounds
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerAdmissible.computedRatio_bounds"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerAdmissible.computedRatio_bounds: {axioms.toList}"
  let n := `EulerAdmissible.computed_nonlinear_step_admissible
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerAdmissible.computed_nonlinear_step_admissible"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerAdmissible.computed_nonlinear_step_admissible: {axioms.toList}"
  let n := `EulerAdmissible.computed_step_conservation
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerAdmissible.computed_step_conservation"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerAdmissible.computed_step_conservation: {axioms.toList}"
  let n := `EulerAdmissible.unsafe_split_counterexample
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerAdmissible.unsafe_split_counterexample"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerAdmissible.unsafe_split_counterexample: {axioms.toList}"
  let n := `EulerPrimitiveEnergy.metric_positive
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPrimitiveEnergy.metric_positive"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPrimitiveEnergy.metric_positive: {axioms.toList}"
  let n := `EulerPrimitiveEnergy.symmetric_principal_part
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerPrimitiveEnergy.symmetric_principal_part"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerPrimitiveEnergy.symmetric_principal_part: {axioms.toList}"
  let n := `EulerConservativePrimitive.conserved_derivative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerConservativePrimitive.conserved_derivative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerConservativePrimitive.conserved_derivative: {axioms.toList}"
  let n := `EulerConservativePrimitive.canonical_flux_derivative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerConservativePrimitive.canonical_flux_derivative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerConservativePrimitive.canonical_flux_derivative: {axioms.toList}"
  let n := `EulerConservativePrimitive.euler_residual_equivalence
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerConservativePrimitive.euler_residual_equivalence"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerConservativePrimitive.euler_residual_equivalence: {axioms.toList}"
  let n := `EulerDiscreteEnergy.principal_quadratic_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerDiscreteEnergy.principal_quadratic_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerDiscreteEnergy.principal_quadratic_bound: {axioms.toList}"
  let n := `EulerDiscreteEnergy.energy_jensen
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerDiscreteEnergy.energy_jensen"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerDiscreteEnergy.energy_jensen: {axioms.toList}"
  let n := `EulerDiscreteEnergy.frozen_linearized_energy_contraction
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerDiscreteEnergy.frozen_linearized_energy_contraction"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerDiscreteEnergy.frozen_linearized_energy_contraction: {axioms.toList}"
  let n := `EulerEnergyBounds.box_coercivity
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEnergyBounds.box_coercivity"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEnergyBounds.box_coercivity: {axioms.toList}"
  let n := `EulerEnergyBounds.box_upper_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerEnergyBounds.box_upper_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerEnergyBounds.box_upper_bound: {axioms.toList}"
  let n := `EulerVariableEnergy.variable_principal_energy_defect
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerVariableEnergy.variable_principal_energy_defect"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerVariableEnergy.variable_principal_energy_defect: {axioms.toList}"
  let n := `EulerGridSobolev.three_dimensional_embedding
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerGridSobolev.three_dimensional_embedding"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerGridSobolev.three_dimensional_embedding: {axioms.toList}"
  let n := `EulerCoefficientBounds.metric_variation
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerCoefficientBounds.metric_variation"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerCoefficientBounds.metric_variation: {axioms.toList}"
  let n := `EulerVariableStability.variable_principal_energy_growth
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerVariableStability.variable_principal_energy_growth"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerVariableStability.variable_principal_energy_growth: {axioms.toList}"
  let n := `EulerVariableStability.varying_metric_energy_increase
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerVariableStability.varying_metric_energy_increase"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerVariableStability.varying_metric_energy_increase: {axioms.toList}"
