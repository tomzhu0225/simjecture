import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `Certificate.admissible_is_classical_euler
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Certificate.admissible_is_classical_euler"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Certificate.admissible_is_classical_euler: {axioms.toList}"
  let n := `Certificate.family_nonempty
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Certificate.family_nonempty"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Certificate.family_nonempty: {axioms.toList}"
  let n := `ShearEuler.pressure_of_conserved
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ShearEuler.pressure_of_conserved"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ShearEuler.pressure_of_conserved: {axioms.toList}"
  let n := `ShearEuler.inverse_flow
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ShearEuler.inverse_flow"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ShearEuler.inverse_flow: {axioms.toList}"
  let n := `ShearEuler.flow_inverse
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ShearEuler.flow_inverse"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ShearEuler.flow_inverse: {axioms.toList}"
  let n := `Grid.center_covers_cube
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Grid.center_covers_cube"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Grid.center_covers_cube: {axioms.toList}"
  let n := `Grid.centers_separated
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Grid.centers_separated"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Grid.centers_separated: {axioms.toList}"
  let n := `Recovery.exists_base_bump
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Recovery.exists_base_bump"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Recovery.exists_base_bump: {axioms.toList}"
  let n := `Recovery.perturb_admissible
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Recovery.perturb_admissible"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Recovery.perturb_admissible: {axioms.toList}"
  let n := `Optimality.exists_unqueried_cell
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Optimality.exists_unqueried_cell"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Optimality.exists_unqueried_cell: {axioms.toList}"
  let n := `Optimality.accuracy_at_tolerance
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Optimality.accuracy_at_tolerance"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Optimality.accuracy_at_tolerance: {axioms.toList}"
  let n := `Optimality.sampling_values
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Optimality.sampling_values"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Optimality.sampling_values: {axioms.toList}"
  let n := `Optimality.euler_algorithm_queries
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Optimality.euler_algorithm_queries"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Optimality.euler_algorithm_queries: {axioms.toList}"
  let n := `Work.solver_program_matches_query_algorithm
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Work.solver_program_matches_query_algorithm"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Work.solver_program_matches_query_algorithm: {axioms.toList}"
  let n := `Work.solver_work_exact
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Work.solver_work_exact"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Work.solver_work_exact: {axioms.toList}"
  let n := `Work.total_work_upper
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Work.total_work_upper"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Work.total_work_upper: {axioms.toList}"
  let n := `Machines.same_answers
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Machines.same_answers"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Machines.same_answers: {axioms.toList}"
  let n := `Machines.tree_correct
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Machines.tree_correct"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Machines.tree_correct: {axioms.toList}"
  let n := `Machines.general_machine_work_lower
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Machines.general_machine_work_lower"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Machines.general_machine_work_lower: {axioms.toList}"
  let n := `Machines.certified_general_optimality
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: Machines.certified_general_optimality"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS Machines.certified_general_optimality: {axioms.toList}"
