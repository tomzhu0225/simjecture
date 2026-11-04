import Mathlib.Analysis.SpecialFunctions.Trigonometric.Deriv
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum

noncomputable section
namespace NonlinearEuler

def initialPressure (a x y z : ℝ) : ℝ :=
  1+(a^2/16)*(Real.cos (2*x)+Real.cos (2*y))*(Real.cos (2*z)+2)

theorem pressure_z_derivative (a x y z : ℝ) :
    HasDerivAt (fun s => initialPressure a x y s)
      (-(a^2/8)*(Real.cos (2*x)+Real.cos (2*y))*Real.sin (2*z)) z := by
  have argument := (hasDerivAt_id z).const_mul 2
  have cosine := (Real.hasDerivAt_cos _).comp z argument
  have full := ((cosine.add_const 2).const_mul
    ((a^2/16)*(Real.cos (2*x)+Real.cos (2*y)))).const_add 1
  convert full using 1; simp; ring

theorem nonzero_initial_pressure_force (a : ℝ) :
    -deriv (fun z => initialPressure a 0 0 z) (Real.pi/4) = a^2/4 := by
  rw [(pressure_z_derivative a 0 0 (Real.pi/4)).deriv]
  have hp : (2:ℝ)*(Real.pi/4) = Real.pi/2 := by ring
  simp [hp]
  ring

theorem positive_initial_pressure_force (a : ℝ) (ha : 1/2 ≤ a) :
    (1:ℝ)/16 ≤ -deriv (fun z => initialPressure a 0 0 z) (Real.pi/4) := by
  rw [nonzero_initial_pressure_force]
  nlinarith [sq_nonneg (a-1/2)]

-- The initial vertical velocity is identically zero, hence the advective
-- vertical-momentum fluxes are zero. The z flux is the initial pressure.
-- This statement records the consequence of the vertical Euler equation;
-- it is a nontriviality diagnostic, not a solver accuracy or optimality proof.
theorem vertical_momentum_must_change (a mt : ℝ)
    (euler_at_initial_point : mt + deriv (fun z => initialPressure a 0 0 z) (Real.pi/4) = 0) :
    mt = a^2/4 := by
  have h := nonzero_initial_pressure_force a
  linarith
end NonlinearEuler
