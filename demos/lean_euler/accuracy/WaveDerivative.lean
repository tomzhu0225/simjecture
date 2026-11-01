import Mathlib.Analysis.SpecialFunctions.Trigonometric.Deriv
import Mathlib.Tactic.Ring

noncomputable section
namespace WaveDerivative

def wave (amplitude frequency offset slope x : ℝ) : ℝ :=
  1 + amplitude * Real.sin (frequency*(offset+slope*x))

theorem wave_derivative (amplitude frequency offset slope x : ℝ) :
    HasDerivAt (wave amplitude frequency offset slope)
      (amplitude*Real.cos (frequency*(offset+slope*x))*(frequency*slope)) x := by
  have argument := ((hasDerivAt_const x offset).add
    ((hasDerivAt_id x).const_mul slope)).const_mul frequency
  have sine := (Real.hasDerivAt_sin _).comp x argument
  have full := (hasDerivAt_const x 1).add (sine.const_mul amplitude)
  simpa only [wave, Pi.add_apply, Function.comp_apply, id_eq,
    mul_one, zero_add, mul_assoc] using full

-- Along time the phase slope is -(vx+vy+vz); along each coordinate it is one.
-- Equal phase values therefore cancel the transport residual exactly.
theorem phase_transport (a w phase vx vy vz : ℝ) :
    a*Real.cos phase*(w*(-(vx+vy+vz))) +
      vx*(a*Real.cos phase*w) + vy*(a*Real.cos phase*w) +
      vz*(a*Real.cos phase*w) = 0 := by ring
end WaveDerivative
