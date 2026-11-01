import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `ContactReference.contact_pressure
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ContactReference.contact_pressure"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ContactReference.contact_pressure: {axioms.toList}"
  let n := `ContactReference.contact_velocity
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ContactReference.contact_velocity"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ContactReference.contact_velocity: {axioms.toList}"
  let n := `ContactReference.transported_contact_residual
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ContactReference.transported_contact_residual"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ContactReference.transported_contact_residual: {axioms.toList}"
  let n := `ContactReference.sinusoidal_transport_jet
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ContactReference.sinusoidal_transport_jet"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ContactReference.sinusoidal_transport_jet: {axioms.toList}"
  let n := `ContactReference.density_controls_components
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: ContactReference.density_controls_components"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS ContactReference.density_controls_components: {axioms.toList}"
