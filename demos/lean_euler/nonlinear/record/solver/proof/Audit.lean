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
