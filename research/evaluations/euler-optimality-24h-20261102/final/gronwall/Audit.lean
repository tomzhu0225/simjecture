import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `EulerGronwall.scalar_bound
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerGronwall.scalar_bound"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerGronwall.scalar_bound: {axioms.toList}"
run_cmd do
  let n := `EulerGronwall.coefficient_nonneg
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerGronwall.coefficient_nonneg"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerGronwall.coefficient_nonneg: {axioms.toList}"
run_cmd do
  let n := `EulerGronwall.gronwall_energy
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerGronwall.gronwall_energy"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerGronwall.gronwall_energy: {axioms.toList}"
run_cmd do
  let n := `EulerGronwall.physical_gronwall_energy
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerGronwall.physical_gronwall_energy"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerGronwall.physical_gronwall_energy: {axioms.toList}"
run_cmd do
  let n := `EulerGronwall.zero_growth_energy
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerGronwall.zero_growth_energy"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerGronwall.zero_growth_energy: {axioms.toList}"
run_cmd do
  let n := `EulerGronwall.zero_residual_energy
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerGronwall.zero_residual_energy"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerGronwall.zero_residual_energy: {axioms.toList}"
run_cmd do
  let n := `EulerGronwall.zero_growth_control
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerGronwall.zero_growth_control"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerGronwall.zero_growth_control: {axioms.toList}"
run_cmd do
  let n := `EulerTimeEnergy.metric_coefficient_control
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerTimeEnergy.metric_coefficient_control"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerTimeEnergy.metric_coefficient_control: {axioms.toList}"
run_cmd do
  let n := `EulerErrorField.full_definition_control
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerErrorField.full_definition_control"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerErrorField.full_definition_control: {axioms.toList}"
run_cmd do
  let n := `EulerMetricEnergy.changing_metric_control
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerMetricEnergy.changing_metric_control"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerMetricEnergy.changing_metric_control: {axioms.toList}"
run_cmd do
  let n := `EulerTransport.periodic_divergence_control
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerTransport.periodic_divergence_control"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerTransport.periodic_divergence_control: {axioms.toList}"
run_cmd do
  let n := `EulerTransport.nonperiodic_boundary_control
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: EulerTransport.nonperiodic_boundary_control"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS EulerTransport.nonperiodic_boundary_control: {axioms.toList}"
