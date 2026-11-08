import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `CacheSchedule.reference_legal
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: CacheSchedule.reference_legal"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS CacheSchedule.reference_legal: {axioms.toList}"
  let n := `CacheSchedule.cold_use_rejected
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: CacheSchedule.cold_use_rejected"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS CacheSchedule.cold_use_rejected: {axioms.toList}"
  let n := `CacheSchedule.evicted_use_rejected
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: CacheSchedule.evicted_use_rejected"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS CacheSchedule.evicted_use_rejected: {axioms.toList}"
  let n := `CacheSchedule.cache_optimal
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: CacheSchedule.cache_optimal"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS CacheSchedule.cache_optimal: {axioms.toList}"
  let n := `CacheSchedule.saves_two_evaluations_per_cell
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: CacheSchedule.saves_two_evaluations_per_cell"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS CacheSchedule.saves_two_evaluations_per_cell: {axioms.toList}"
  let n := `CacheSchedule.cached_library_cost
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: CacheSchedule.cached_library_cost"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS CacheSchedule.cached_library_cost: {axioms.toList}"
  let n := `CacheSchedule.reference_library_cost
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: CacheSchedule.reference_library_cost"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS CacheSchedule.reference_library_cost: {axioms.toList}"
  let n := `CacheSchedule.weighted_cache_optimal
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: CacheSchedule.weighted_cache_optimal"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS CacheSchedule.weighted_cache_optimal: {axioms.toList}"
  let n := `CacheSchedule.weighted_saving
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: CacheSchedule.weighted_saving"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS CacheSchedule.weighted_saving: {axioms.toList}"
  let n := `CacheSchedule.weighted_strict_improvement
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: CacheSchedule.weighted_strict_improvement"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS CacheSchedule.weighted_strict_improvement: {axioms.toList}"
