import Mathlib.Data.Real.Basic
import Mathlib.Data.Fin.VecNotation
import Mathlib.Tactic.FinCases
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity

noncomputable section
namespace EulerPrimitiveEnergy
abbrev State := Fin 5 → ℝ

-- Coordinates are specific volume q=1/rho, three velocities, and pressure.
-- Their smooth Euler equations have quadratic first-derivative nonlinearities:
-- D_t q=q div(v), D_t v=-q grad(p), D_t p=-2p div(v).
-- ConservativePrimitive.lean connects this system to the actual conservative flux
-- by differentiation; no numerical stability estimate follows from this identity alone.
def principal (q p vd : ℝ) (d : Fin 3) (h : State) : State :=
  let hd := h ⟨d.val+1,by omega⟩
  ![vd*h 0-q*hd,
    vd*h 1+(if d=0 then q*h 4 else 0),
    vd*h 2+(if d=1 then q*h 4 else 0),
    vd*h 3+(if d=2 then q*h 4 else 0),
    vd*h 4+2*p*hd]

def metric (q p : ℝ) (x y : State) : ℝ :=
  x 4*y 4/(2*p)+(x 1*y 1+x 2*y 2+x 3*y 3)/q+
    (x 0/q+x 4/(2*p))*(y 0/q+y 4/(2*p))

theorem metric_symmetric (q p : ℝ) (x y : State) : metric q p x y = metric q p y x := by
  dsimp [metric]
  ring

theorem metric_squares (q p : ℝ) (h : State) :
    metric q p h h = h 4^2/(2*p)+(h 1^2+h 2^2+h 3^2)/q+(h 0/q+h 4/(2*p))^2 := by
  dsimp [metric]
  ring

theorem metric_nonnegative (q p : ℝ) (hq : 0 < q) (hp : 0 < p) (h : State) :
    0 ≤ metric q p h h := by
  rw [metric_squares]
  positivity

theorem metric_zero_iff (q p : ℝ) (hq : 0 < q) (hp : 0 < p) (h : State) :
    metric q p h h=0 ↔ h=0 := by
  constructor
  · intro he
    rw [metric_squares] at he
    have hA : 0 ≤ h 4^2/(2*p) := by positivity
    have hB : 0 ≤ (h 1^2+h 2^2+h 3^2)/q := by positivity
    have hC := sq_nonneg (h 0/q+h 4/(2*p))
    have hAz : h 4^2/(2*p)=0 := by linarith
    have hBz : (h 1^2+h 2^2+h 3^2)/q=0 := by linarith
    have hCz : (h 0/q+h 4/(2*p))^2=0 := by linarith
    have h4 : h 4=0 := by
      have hh := (div_eq_zero_iff).mp hAz
      rcases hh with hh | hh
      · nlinarith
      · nlinarith
    have hsum : h 1^2+h 2^2+h 3^2=0 := by
      rcases (div_eq_zero_iff).mp hBz with hh | hh
      · exact hh
      · linarith
    have h1 : h 1=0 := by nlinarith [sq_nonneg (h 1),sq_nonneg (h 2),sq_nonneg (h 3)]
    have h2 : h 2=0 := by nlinarith [sq_nonneg (h 1),sq_nonneg (h 2),sq_nonneg (h 3)]
    have h3 : h 3=0 := by nlinarith [sq_nonneg (h 1),sq_nonneg (h 2),sq_nonneg (h 3)]
    have h0 : h 0=0 := by
      have hh : h 0/q=0 := by simpa [h4] using (sq_eq_zero_iff.mp hCz)
      rcases (div_eq_zero_iff).mp hh with hh | hh
      · exact hh
      · linarith
    funext i
    fin_cases i <;> simp [h0,h1,h2,h3,h4]
  · rintro rfl
    simp [metric]

theorem metric_positive (q p : ℝ) (hq : 0 < q) (hp : 0 < p) (h : State) (hh : h ≠ 0) :
    0 < metric q p h h := by
  have hn : metric q p h h ≠ 0 := fun hz => hh ((metric_zero_iff q p hq hp h).mp hz)
  exact lt_of_le_of_ne (metric_nonnegative q p hq hp h) (Ne.symm hn)

theorem principal_metric_identity (q p vd : ℝ) (hq : 0 < q) (hp : 0 < p)
    (d : Fin 3) (x y : State) :
    metric q p x (principal q p vd d y) =
      vd*metric q p x y+x 4*y ⟨d.val+1,by omega⟩+x ⟨d.val+1,by omega⟩*y 4 := by
  have hqn : q ≠ 0 := ne_of_gt hq
  have hpn : p ≠ 0 := ne_of_gt hp
  fin_cases d <;> simp [metric,principal] <;> field_simp <;> ring

theorem symmetric_principal_part (q p vd : ℝ) (hq : 0 < q) (hp : 0 < p)
    (d : Fin 3) (x y : State) :
    metric q p x (principal q p vd d y) = metric q p (principal q p vd d x) y := by
  rw [metric_symmetric q p (principal q p vd d x) y,
    principal_metric_identity q p vd hq hp d x y,
    principal_metric_identity q p vd hq hp d y x,metric_symmetric q p y x]
  ring
end EulerPrimitiveEnergy
