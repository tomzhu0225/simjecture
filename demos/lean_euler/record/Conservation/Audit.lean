import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `FiniteVolume.conservation
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: FiniteVolume.conservation"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS FiniteVolume.conservation: {axioms.toList}"
  let n := `FiniteVolume.conservation3D
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: FiniteVolume.conservation3D"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS FiniteVolume.conservation3D: {axioms.toList}"
  let n := `FiniteVolume.constant_state
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: FiniteVolume.constant_state"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS FiniteVolume.constant_state: {axioms.toList}"
