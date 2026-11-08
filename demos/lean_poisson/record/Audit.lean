import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `Poisson.solve_correct
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Poisson.solve_correct"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Poisson.solve_correct: {axioms.toList}"
  let n := `Poisson.solve_unique
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Poisson.solve_unique"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Poisson.solve_unique: {axioms.toList}"
  let n := `Poisson.trace_correct
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Poisson.trace_correct"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Poisson.trace_correct: {axioms.toList}"
  let n := `Poisson.solve_cost
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Poisson.solve_cost"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Poisson.solve_cost: {axioms.toList}"
  let n := `Poisson.any_solver_lower_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Poisson.any_solver_lower_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Poisson.any_solver_lower_bound: {axioms.toList}"
  let n := `Poisson.work_optimal
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Poisson.work_optimal"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Poisson.work_optimal: {axioms.toList}"
