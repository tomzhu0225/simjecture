import Candidate
import Lean
open Lean Elab Command
run_cmd do
  let n := `WaveDerivative.wave_derivative
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: WaveDerivative.wave_derivative"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS WaveDerivative.wave_derivative: {axioms.toList}"
  let n := `WaveDerivative.phase_transport
  match (← getEnv).find? n with
  | some (.thmInfo _) => pure ()
  | _ => throwError "Not a theorem: WaveDerivative.phase_transport"
  let axioms ← collectAxioms n
  logInfo m!"SIMJECTURE_AXIOMS WaveDerivative.phase_transport: {axioms.toList}"
