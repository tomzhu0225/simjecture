import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `EulerCache.face_consistency
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerCache.face_consistency"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerCache.face_consistency: {axioms.toList}"
  let n := `EulerCache.step_equivalence
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerCache.step_equivalence"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerCache.step_equivalence: {axioms.toList}"
  let n := `EulerCache.admissible_step_equivalence
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerCache.admissible_step_equivalence"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerCache.admissible_step_equivalence: {axioms.toList}"
  let n := `EulerCache.trajectory_equivalence
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerCache.trajectory_equivalence"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerCache.trajectory_equivalence: {axioms.toList}"
  let n := `EulerCache.cached_conservation
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerCache.cached_conservation"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerCache.cached_conservation: {axioms.toList}"
