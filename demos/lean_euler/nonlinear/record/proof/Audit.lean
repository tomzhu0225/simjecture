import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `NonlinearEuler.pressure_z_derivative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: NonlinearEuler.pressure_z_derivative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS NonlinearEuler.pressure_z_derivative: {axioms.toList}"
  let n := `NonlinearEuler.nonzero_initial_pressure_force
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: NonlinearEuler.nonzero_initial_pressure_force"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS NonlinearEuler.nonzero_initial_pressure_force: {axioms.toList}"
  let n := `NonlinearEuler.positive_initial_pressure_force
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: NonlinearEuler.positive_initial_pressure_force"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS NonlinearEuler.positive_initial_pressure_force: {axioms.toList}"
  let n := `NonlinearEuler.vertical_momentum_must_change
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: NonlinearEuler.vertical_momentum_must_change"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS NonlinearEuler.vertical_momentum_must_change: {axioms.toList}"
