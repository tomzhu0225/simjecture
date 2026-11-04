import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `EulerWitness.initial_admissible
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerWitness.initial_admissible"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerWitness.initial_admissible: {axioms.toList}"
  let n := `EulerWitness.negative_density
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerWitness.negative_density"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerWitness.negative_density: {axioms.toList}"
