import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `ErrorWork.stencil_nonexpansive
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ErrorWork.stencil_nonexpansive"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ErrorWork.stencil_nonexpansive: {axioms.toList}"
  let n := `ErrorWork.accumulate_error
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ErrorWork.accumulate_error"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ErrorWork.accumulate_error: {axioms.toList}"
  let n := `ErrorWork.first_order_budget
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ErrorWork.first_order_budget"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ErrorWork.first_order_budget: {axioms.toList}"
  let n := `ErrorWork.total_work_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ErrorWork.total_work_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ErrorWork.total_work_bound: {axioms.toList}"
  let n := `ErrorWork.smallest_certified_grid_minimizes_work
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ErrorWork.smallest_certified_grid_minimizes_work"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ErrorWork.smallest_certified_grid_minimizes_work: {axioms.toList}"
