import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `Decay.nonnegative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Decay.nonnegative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Decay.nonnegative: {axioms.toList}"
  let n := `Decay.counterexample
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Decay.counterexample"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Decay.counterexample: {axioms.toList}"
