import Mathlib.Data.Real.Sqrt
import Mathlib.Data.Fin.VecNotation
import Mathlib.Data.Finset.Lattice.Fold
import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Algebra.Order.BigOperators.Group.Finset
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Tactic.FinCases
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import Mathlib.Data.Real.Basic
import Mathlib.Analysis.Calculus.Deriv.Add
import Mathlib.Analysis.Calculus.Deriv.Prod
import Mathlib.Analysis.Calculus.Deriv.Pow
import Mathlib.Analysis.Calculus.Deriv.Inv
import Mathlib.Tactic.LinearCombination
import Mathlib.Algebra.BigOperators.Intervals
import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Tactic.NormNum
import Mathlib.Analysis.SpecialFunctions.Log.Deriv
import Mathlib.Analysis.Convex.Deriv
import Mathlib.Analysis.Convex.Jensen
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic
import Mathlib.Data.Nat.Log
import Mathlib.Algebra.Order.Floor.Semiring
import Mathlib.Algebra.Group.Fin.Basic
import Mathlib.MeasureTheory.Integral.Bochner.Basic
import Mathlib.MeasureTheory.Integral.DivergenceTheorem
import Mathlib.MeasureTheory.Integral.Pi
import Mathlib.Analysis.SpecialFunctions.Integrals.Basic
import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.MeasureTheory.Integral.Bochner.ContinuousLinearMap


noncomputable section
namespace EulerAdmissible
open scoped BigOperators
abbrev Vec := Fin 3 → ℝ
abbrev State := Fin 5 → ℝ

def kinetic (v : Vec) : ℝ := (v 0^2+v 1^2+v 2^2)/2
def primitive (r p : ℝ) (v : Vec) : State := ![r,r*v 0,r*v 1,r*v 2,p+r*kinetic v]
def pressure (u : State) : ℝ := u 4-(u 1^2+u 2^2+u 3^2)/(2*u 0)
def Admissible (u : State) : Prop := 0 < u 0 ∧ 0 < pressure u

def eulerFlux (u : State) (d : Fin 3) : State :=
  let vd := u ⟨d.val+1,by omega⟩/u 0
  ![u ⟨d.val+1,by omega⟩,u 1*vd+(if d=0 then pressure u else 0),
    u 2*vd+(if d=1 then pressure u else 0),
    u 3*vd+(if d=2 then pressure u else 0),(u 4+pressure u)*vd]

def primitiveFlux (r p : ℝ) (v : Vec) (d : Fin 3) : State :=
  ![r*v d,r*v 0*v d+(if d=0 then p else 0),
    r*v 1*v d+(if d=1 then p else 0),r*v 2*v d+(if d=2 then p else 0),
    (2*p+r*kinetic v)*v d]

theorem pressure_primitive (r p : ℝ) (v : Vec) : pressure (primitive r p v) = p := by
  simp [pressure,primitive,kinetic]
  field_simp
  ring

theorem flux_primitive (r p : ℝ) (v : Vec) (hr : 0 < r) (d : Fin 3) :
    eulerFlux (primitive r p v) d = primitiveFlux r p v d := by
  have hp := pressure_primitive r p v
  have hn : r ≠ 0 := ne_of_gt hr
  simp only [eulerFlux,hp]
  funext i
  fin_cases d <;> fin_cases i <;> simp [primitive,primitiveFlux,hn]
  all_goals ring_nf
  all_goals simp

def fromVelocity (u : State) : Vec := ![u 1/u 0,u 2/u 0,u 3/u 0]

theorem primitive_reconstruct (u : State) (hr : 0 < u 0) :
    primitive (u 0) (pressure u) (fromVelocity u) = u := by
  have hn : u 0 ≠ 0 := ne_of_gt hr
  funext i
  fin_cases i <;> simp [primitive,fromVelocity,pressure,kinetic]
  all_goals field_simp
  all_goals ring

-- Linear supporting functional for the convex positive-pressure set.
def supportEnergy (u : State) (v : Vec) : ℝ :=
  u 4-(u 1*v 0+u 2*v 1+u 3*v 2)+u 0*kinetic v

theorem complete_square (u : State) (v : Vec) (hr : 0 < u 0) :
    supportEnergy u v = pressure u + u 0/2*
      ((u 1/u 0-v 0)^2+(u 2/u 0-v 1)^2+(u 3/u 0-v 2)^2) := by
  dsimp [supportEnergy,pressure,kinetic]
  have hn : u 0 ≠ 0 := ne_of_gt hr
  field_simp
  ring

theorem supportEnergy_positive (u : State) (hu : Admissible u) (v : Vec) :
    0 < supportEnergy u v := by
  rw [complete_square u v hu.1]
  have hq : 0 ≤ (u 1/u 0-v 0)^2+(u 2/u 0-v 1)^2+(u 3/u 0-v 2)^2 := by positivity
  have hr := hu.1
  have hp := hu.2
  positivity

theorem supportEnergy_at_velocity (u : State) (hr : 0 < u 0) :
    supportEnergy u (fromVelocity u) = pressure u := by
  rw [complete_square u (fromVelocity u) hr]
  simp [fromVelocity]

theorem positive_convex_pair (x y theta : ℝ) (hx : 0 < x) (hy : 0 < y)
    (ht0 : 0 ≤ theta) (ht1 : theta ≤ 1) : 0 < theta*x+(1-theta)*y := by
  by_cases ht : theta=0
  · simp [ht,hy]
  · have hp : 0 < theta := lt_of_le_of_ne ht0 (Ne.symm ht)
    exact add_pos_of_pos_of_nonneg (mul_pos hp hx) (mul_nonneg (sub_nonneg.mpr ht1) hy.le)

theorem convex_admissible (u v : State) (hu : Admissible u) (hv : Admissible v)
    (theta : ℝ) (ht0 : 0 ≤ theta) (ht1 : theta ≤ 1) :
    Admissible (theta • u+(1-theta) • v) := by
  let w := theta • u+(1-theta) • v
  have hr : 0 < w 0 := by
    dsimp [w]
    exact positive_convex_pair _ _ _ hu.1 hv.1 ht0 ht1
  refine ⟨hr,?_⟩
  have heq : supportEnergy w (fromVelocity w) =
      theta*supportEnergy u (fromVelocity w)+(1-theta)*supportEnergy v (fromVelocity w) := by
    dsimp [supportEnergy,w]
    ring
  rw [← supportEnergy_at_velocity w hr,heq]
  have h1 := supportEnergy_positive u hu (fromVelocity w)
  have h2 := supportEnergy_positive v hv (fromVelocity w)
  exact positive_convex_pair _ _ _ h1 h2 ht0 ht1

def split (u : State) (a sign : ℝ) (d : Fin 3) : State := u+(sign/a) • eulerFlux u d

-- Algebraic flux-splitting identity for gamma=2, with either sign.
theorem split_pressure (r p a sign : ℝ) (v : Vec) (d : Fin 3)
    (hr : 0 < r) (ha : a ≠ 0) (hs : sign^2=1) (hb : a+sign*v d ≠ 0) :
    pressure (split (primitive r p v) a sign d) =
      p*(2*r*(a+sign*v d)^2-p)/(2*r*a*(a+sign*v d)) := by
  rw [split,flux_primitive r p v hr d]
  have hn : r ≠ 0 := ne_of_gt hr
  have hs' : sign=1 ∨ sign=-1 := by
    have h : (sign-1)*(sign+1)=0 := by nlinarith
    rcases mul_eq_zero.mp h with h | h
    · left; linarith
    · right; linarith
  rcases hs' with rfl | rfl <;> fin_cases d <;>
    simp [pressure,primitive,primitiveFlux,kinetic] at * <;> field_simp <;> ring

theorem wave_bound (r p a sign v : ℝ) (hr : 0 < r) (hp : 0 < p)
    (hs : sign^2=1) (ha : |v|+Real.sqrt (2*p/r) ≤ a) :
    0 < a ∧ 0 < a+sign*v ∧ 0 < 2*r*(a+sign*v)^2-p := by
  have hc : 0 < Real.sqrt (2*p/r) := Real.sqrt_pos.2 (by positivity)
  have hcsq := Real.sq_sqrt (by positivity : 0 ≤ 2*p/r)
  have hmul : r*(Real.sqrt (2*p/r))^2=2*p := by
    have hh := (eq_div_iff (ne_of_gt hr)).mp hcsq
    nlinarith
  have habs := abs_nonneg v
  have ha' : 0 < a := by linarith
  have hs' : sign=1 ∨ sign=-1 := sq_eq_one_iff.mp hs
  have hb : Real.sqrt (2*p/r) ≤ a+sign*v := by
    rcases hs' with rfl | rfl
    · have hv := neg_le_abs v
      nlinarith
    · have hv := le_abs_self v
      nlinarith
  have hbpos : 0 < a+sign*v := lt_of_lt_of_le hc hb
  have hsq : (Real.sqrt (2*p/r))^2 ≤ (a+sign*v)^2 := by nlinarith
  have hh := mul_le_mul_of_nonneg_left hsq hr.le
  exact ⟨ha',hbpos,by nlinarith⟩

theorem primitive_split_admissible (r p a sign : ℝ) (v : Vec) (d : Fin 3)
    (hr : 0 < r) (hp : 0 < p) (hs : sign^2=1)
    (ha : |v d|+Real.sqrt (2*p/r) ≤ a) :
    Admissible (split (primitive r p v) a sign d) := by
  obtain ⟨ha',hb,hpressure⟩ := wave_bound r p a sign (v d) hr hp hs ha
  constructor
  · have eq : (split (primitive r p v) a sign d) 0 = r*(a+sign*v d)/a := by
      rw [split,flux_primitive r p v hr d]
      simp [primitive,primitiveFlux]
      field_simp
    rw [eq]
    positivity
  · rw [split_pressure r p a sign v d hr (ne_of_gt ha') hs (ne_of_gt hb)]
    positivity

theorem flux_splitting_admissible (u : State) (hu : Admissible u) (d : Fin 3)
    (a sign : ℝ) (hs : sign^2=1)
    (ha : |fromVelocity u d|+Real.sqrt (2*pressure u/u 0) ≤ a) :
    Admissible (split u a sign d) := by
  have h := primitive_split_admissible (u 0) (pressure u) a sign (fromVelocity u) d hu.1 hu.2 hs ha
  simpa only [primitive_reconstruct u hu.1] using h

theorem weighted_positive {I : Type*} [Fintype I] (w x : I → ℝ)
    (hw : ∀ i, 0 ≤ w i) (hws : ∑ i, w i = 1) (hx : ∀ i, 0 < x i) :
    0 < ∑ i, w i*x i := by
  have hex : ∃ i, 0 < w i := by
    by_contra hnone
    have hz : ∀ i, w i=0 := fun i => le_antisymm
      (le_of_not_gt (fun hi => hnone ⟨i,hi⟩)) (hw i)
    have h : ∑ i, w i = 0 := by simp [hz]
    linarith
  obtain ⟨i,hi⟩ := hex
  exact Finset.sum_pos' (fun j _ => mul_nonneg (hw j) (hx j).le)
    ⟨i,Finset.mem_univ i,mul_pos hi (hx i)⟩

theorem supportEnergy_sum {I : Type*} [Fintype I] (w : I → ℝ) (u : I → State) (v : Vec) :
    supportEnergy (∑ i, w i • u i) v = ∑ i, w i*supportEnergy (u i) v := by
  simp [supportEnergy,Finset.sum_apply,Finset.sum_add_distrib,Finset.sum_sub_distrib,
    Finset.sum_mul,mul_add,mul_sub,mul_assoc]

theorem convex_sum_admissible {I : Type*} [Fintype I] (w : I → ℝ) (u : I → State)
    (hw : ∀ i, 0 ≤ w i) (hws : ∑ i, w i = 1) (hu : ∀ i, Admissible (u i)) :
    Admissible (∑ i, w i • u i) := by
  have hr : 0 < (∑ i, w i • u i) 0 := by
    simpa only [Finset.sum_apply,Pi.smul_apply,smul_eq_mul] using
      weighted_positive w (fun i => u i 0) hw hws (fun i => (hu i).1)
  refine ⟨hr,?_⟩
  rw [← supportEnergy_at_velocity _ hr,supportEnergy_sum]
  exact weighted_positive w _ hw hws (fun i => supportEnergy_positive (u i) (hu i) _)

def faceFlux (u v : State) (a : ℝ) (d : Fin 3) : State :=
  (1/2 : ℝ) • (eulerFlux u d+eulerFlux v d-a • (v-u))

def update (u : State) (plus minus : Fin 3 → State) (ratio : ℝ) (a : Vec) : State :=
  u-ratio • ((faceFlux u (plus 0) (a 0) 0-faceFlux (minus 0) u (a 0) 0)+
    (faceFlux u (plus 1) (a 1) 1-faceFlux (minus 1) u (a 1) 1)+
    (faceFlux u (plus 2) (a 2) 2-faceFlux (minus 2) u (a 2) 2))

def updateWeights (ratio : ℝ) (a : Vec) : Fin 7 → ℝ :=
  ![1-ratio*(a 0+a 1+a 2),ratio*a 0/2,ratio*a 0/2,
    ratio*a 1/2,ratio*a 1/2,ratio*a 2/2,ratio*a 2/2]

def updateStates (u : State) (plus minus : Fin 3 → State) (a : Vec) : Fin 7 → State :=
  ![u,split (plus 0) (a 0) (-1) 0,split (minus 0) (a 0) 1 0,
    split (plus 1) (a 1) (-1) 1,split (minus 1) (a 1) 1 1,
    split (plus 2) (a 2) (-1) 2,split (minus 2) (a 2) 1 2]

theorem update_as_convex_sum (u : State) (plus minus : Fin 3 → State) (ratio : ℝ)
    (a : Vec) (ha : ∀ d, a d ≠ 0) :
    update u plus minus ratio a = ∑ i, updateWeights ratio a i • updateStates u plus minus a i := by
  funext j
  have h0 := ha 0
  have h1 := ha 1
  have h2 := ha 2
  simp [update,updateWeights,updateStates,faceFlux,split,Fin.sum_univ_succ]
  field_simp
  ring

theorem update_weights_sum (ratio : ℝ) (a : Vec) : ∑ i, updateWeights ratio a i = 1 := by
  simp [updateWeights,Fin.sum_univ_succ]
  ring

def waveSpeed (u : State) (d : Fin 3) : ℝ :=
  |fromVelocity u d|+Real.sqrt (2*pressure u/u 0)

theorem nonlinear_update_admissible (u : State) (plus minus : Fin 3 → State)
    (hu : Admissible u) (hp : ∀ d, Admissible (plus d)) (hm : ∀ d, Admissible (minus d))
    (ratio : ℝ) (a : Vec) (hr : 0 ≤ ratio)
    (hcentral : ∀ d, waveSpeed u d ≤ a d)
    (hplus : ∀ d, waveSpeed (plus d) d ≤ a d)
    (hminus : ∀ d, waveSpeed (minus d) d ≤ a d)
    (cfl : ratio*(a 0+a 1+a 2) ≤ 1) :
    Admissible (update u plus minus ratio a) := by
  have ha : ∀ d, 0 < a d := by
    intro d
    exact (wave_bound (u 0) (pressure u) (a d) 1 (fromVelocity u d)
      hu.1 hu.2 (by norm_num) (hcentral d)).1
  rw [update_as_convex_sum u plus minus ratio a (fun d => ne_of_gt (ha d))]
  apply convex_sum_admissible
  · intro i
    have h0 := ha 0
    have h1 := ha 1
    have h2 := ha 2
    fin_cases i <;> dsimp [updateWeights]
    · exact sub_nonneg.mpr cfl
    all_goals positivity
  · exact update_weights_sum ratio a
  · intro i
    fin_cases i
    · exact hu
    · exact flux_splitting_admissible (plus 0) (hp 0) 0 (a 0) (-1) (by norm_num) (hplus 0)
    · exact flux_splitting_admissible (minus 0) (hm 0) 0 (a 0) 1 (by norm_num) (hminus 0)
    · exact flux_splitting_admissible (plus 1) (hp 1) 1 (a 1) (-1) (by norm_num) (hplus 1)
    · exact flux_splitting_admissible (minus 1) (hm 1) 1 (a 1) 1 (by norm_num) (hminus 1)
    · exact flux_splitting_admissible (plus 2) (hp 2) 2 (a 2) (-1) (by norm_num) (hplus 2)
    · exact flux_splitting_admissible (minus 2) (hm 2) 2 (a 2) 1 (by norm_num) (hminus 2)

def globalSpeed {I : Type*} [Fintype I] [Nonempty I] (u : I → State) (d : Fin 3) : ℝ :=
  Finset.univ.sup' Finset.univ_nonempty (fun i => waveSpeed (u i) d)

theorem globalSpeed_bound {I : Type*} [Fintype I] [Nonempty I] (u : I → State) (d : Fin 3) (i : I) :
    waveSpeed (u i) d ≤ globalSpeed u d := by
  exact Finset.le_sup' (f := fun i => waveSpeed (u i) d) (Finset.mem_univ i)

theorem waveSpeed_positive (u : State) (hu : Admissible u) (d : Fin 3) :
    0 < waveSpeed u d := by
  have hr := hu.1
  have hp := hu.2
  exact add_pos_of_nonneg_of_pos (abs_nonneg _) (Real.sqrt_pos.2 (by positivity))

theorem globalSpeed_positive {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (hu : ∀ i, Admissible (u i)) (d : Fin 3) : 0 < globalSpeed u d := by
  let i : I := Classical.choice (inferInstance : Nonempty I)
  exact (waveSpeed_positive (u i) (hu i) d).trans_le (globalSpeed_bound u d i)

def computedRatio {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (cfl remaining dx : ℝ) : ℝ :=
  min (remaining/dx) (cfl/(globalSpeed u 0+globalSpeed u 1+globalSpeed u 2))

theorem computedRatio_bounds {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (hu : ∀ i, Admissible (u i)) (cfl remaining dx : ℝ)
    (hc0 : 0 < cfl) (hc1 : cfl ≤ 1) (ht : 0 < remaining) (hx : 0 < dx) :
    0 < computedRatio u cfl remaining dx ∧
    computedRatio u cfl remaining dx*dx ≤ remaining ∧
    computedRatio u cfl remaining dx*(globalSpeed u 0+globalSpeed u 1+globalSpeed u 2) ≤ 1 := by
  have h0 := globalSpeed_positive u hu 0
  have h1 := globalSpeed_positive u hu 1
  have h2 := globalSpeed_positive u hu 2
  have hs : 0 < globalSpeed u 0+globalSpeed u 1+globalSpeed u 2 := by positivity
  refine ⟨lt_min (by positivity) (by positivity),?_,?_⟩
  · exact (le_div_iff₀ hx).mp (min_le_left _ _)
  · have hh := (le_div_iff₀ hs).mp (min_le_right (remaining/dx) (cfl/(globalSpeed u 0+globalSpeed u 1+globalSpeed u 2)))
    exact hh.trans hc1

def computedUpdate {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (right left : Fin 3 → I → I) (cfl remaining dx : ℝ) (i : I) : State :=
  update (u i) (fun d => u (right d i)) (fun d => u (left d i))
    (computedRatio u cfl remaining dx) (globalSpeed u)

theorem computed_nonlinear_step_admissible {I : Type*} [Fintype I] [Nonempty I]
    (u : I → State) (hu : ∀ i, Admissible (u i)) (right left : Fin 3 → I → I)
    (cfl remaining dx : ℝ) (hc0 : 0 < cfl) (hc1 : cfl ≤ 1)
    (ht : 0 < remaining) (hx : 0 < dx) :
    ∀ i, Admissible (computedUpdate u right left cfl remaining dx i) := by
  intro i
  obtain ⟨hr,_,hcf⟩ := computedRatio_bounds u hu cfl remaining dx hc0 hc1 ht hx
  apply nonlinear_update_admissible (u i) _ _ (hu i) (fun d => hu (right d i))
    (fun d => hu (left d i)) _ _ hr.le
  · intro d
    exact globalSpeed_bound u d i
  · intro d
    exact globalSpeed_bound u d (right d i)
  · intro d
    exact globalSpeed_bound u d (left d i)
  · exact hcf

theorem computed_step_conservation {I : Type*} [Fintype I] [Nonempty I]
    (u : I → State) (neighbor : Fin 3 → Equiv.Perm I) (cfl remaining dx : ℝ) :
    ∑ i, computedUpdate u (fun d => neighbor d) (fun d => (neighbor d).symm) cfl remaining dx i = ∑ i, u i := by
  have hd (d : Fin 3) :
      ∑ i, (faceFlux (u i) (u (neighbor d i)) (globalSpeed u d) d-
        faceFlux (u ((neighbor d).symm i)) (u i) (globalSpeed u d) d) = 0 := by
    let f : I → State := fun i => faceFlux (u i) (u (neighbor d i)) (globalSpeed u d) d
    have heq (i : I) : faceFlux (u ((neighbor d).symm i)) (u i) (globalSpeed u d) d = f ((neighbor d).symm i) := by
      simp [f]
    simp only [heq,Finset.sum_sub_distrib]
    change (∑ i, f i)-(∑ i, f ((neighbor d).symm i))=0
    rw [Equiv.sum_comp]
    simp
  simp only [computedUpdate,update,Finset.sum_sub_distrib,← Finset.smul_sum,
    Finset.sum_add_distrib,hd,add_zero,smul_zero,sub_zero]

theorem unsafe_split_counterexample :
    pressure (split ![1,0,0,0,1] (1/10) 1 0) = -49 := by
  have h := split_pressure 1 1 (1/10) 1 (fun _ => 0) 0
    (by norm_num) (by norm_num) (by norm_num) (by norm_num)
  norm_num [primitive,kinetic] at h
  exact h
end EulerAdmissible


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


-- Assemble after Admissible.lean and PrimitiveEnergy.lean.
noncomputable section
namespace EulerConservativePrimitive
open scoped Topology
abbrev State := Fin 5 → ℝ

def kinetic (w : State) : ℝ := (w 1^2+w 2^2+w 3^2)/2
def kineticD (w h : State) : ℝ := w 1*h 1+w 2*h 2+w 3*h 3

def conserved (w : State) : State :=
  ![1/w 0,w 1/w 0,w 2/w 0,w 3/w 0,w 4+kinetic w/w 0]

def jacobian (w h : State) : State :=
  ![-h 0/(w 0)^2,(h 1*w 0-w 1*h 0)/(w 0)^2,
    (h 2*w 0-w 2*h 0)/(w 0)^2,(h 3*w 0-w 3*h 0)/(w 0)^2,
    h 4+(kineticD w h*w 0-kinetic w*h 0)/(w 0)^2]

theorem kinetic_derivative {w : ℝ → State} {h : State} {s : ℝ}
    (hw : HasDerivAt w h s) : HasDerivAt (fun t => kinetic (w t)) (kineticD (w s) h) s := by
  have hk := (((((hasDerivAt_pi.mp hw) 1).pow 2).add
    (((hasDerivAt_pi.mp hw) 2).pow 2)).add (((hasDerivAt_pi.mp hw) 3).pow 2)).div_const 2
  convert hk using 1; simp [kineticD]; ring

theorem conserved_derivative {w : ℝ → State} {h : State} {s : ℝ}
    (hw : HasDerivAt w h s) (hq : w s 0 ≠ 0) :
    HasDerivAt (fun t => conserved (w t)) (jacobian (w s) h) s := by
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · have hi := ((hasDerivAt_pi.mp hw) 0).inv hq
    simpa only [conserved,jacobian,one_div,Pi.inv_apply] using hi
  · exact ((hasDerivAt_pi.mp hw) 1).div ((hasDerivAt_pi.mp hw) 0) hq
  · exact ((hasDerivAt_pi.mp hw) 2).div ((hasDerivAt_pi.mp hw) 0) hq
  · exact ((hasDerivAt_pi.mp hw) 3).div ((hasDerivAt_pi.mp hw) 0) hq
  · exact ((hasDerivAt_pi.mp hw) 4).add ((kinetic_derivative hw).div ((hasDerivAt_pi.mp hw) 0) hq)

theorem jacobian_add (w x y : State) : jacobian w (x+y) = jacobian w x+jacobian w y := by
  funext i
  fin_cases i <;> simp [jacobian,kineticD] <;> ring

theorem jacobian_zero (w : State) : jacobian w 0=0 := by
  funext i
  fin_cases i <;> simp [jacobian,kineticD]

theorem jacobian_injective (w : State) (hq : w 0 ≠ 0) : Function.Injective (jacobian w) := by
  intro x y h
  have hh (i : Fin 5) := congrFun h i
  have h0 : x 0=y 0 := by
    have hi := hh 0
    dsimp [jacobian] at hi
    have heq := (div_left_inj' (pow_ne_zero 2 hq)).mp hi
    linarith
  have h1 : x 1=y 1 := by
    have hi := hh 1
    dsimp [jacobian] at hi
    have heq := (div_left_inj' (pow_ne_zero 2 hq)).mp hi
    rw [h0] at heq
    exact (mul_right_cancel₀ hq) (by linarith [heq])
  have h2 : x 2=y 2 := by
    have hi := hh 2
    dsimp [jacobian] at hi
    have heq := (div_left_inj' (pow_ne_zero 2 hq)).mp hi
    rw [h0] at heq
    exact (mul_right_cancel₀ hq) (by linarith [heq])
  have h3 : x 3=y 3 := by
    have hi := hh 3
    dsimp [jacobian] at hi
    have heq := (div_left_inj' (pow_ne_zero 2 hq)).mp hi
    rw [h0] at heq
    exact (mul_right_cancel₀ hq) (by linarith [heq])
  have h4 : x 4=y 4 := by
    have hi := hh 4
    simpa [jacobian,kineticD,h0,h1,h2,h3] using hi
  funext i
  fin_cases i <;> simp [h0,h1,h2,h3,h4]

def primitiveFlux (w : State) (d : Fin 3) : State :=
  let vd := w ⟨d.val+1,by omega⟩
  ![vd/w 0,w 1*vd/w 0+(if d=0 then w 4 else 0),
    w 2*vd/w 0+(if d=1 then w 4 else 0),
    w 3*vd/w 0+(if d=2 then w 4 else 0),(2*w 4+kinetic w/w 0)*vd]

def primitiveFluxD (w h : State) (d : Fin 3) : State :=
  let vd := w ⟨d.val+1,by omega⟩
  let hd := h ⟨d.val+1,by omega⟩
  ![(hd*w 0-vd*h 0)/(w 0)^2,
    ((h 1*vd+w 1*hd)*w 0-w 1*vd*h 0)/(w 0)^2+(if d=0 then h 4 else 0),
    ((h 2*vd+w 2*hd)*w 0-w 2*vd*h 0)/(w 0)^2+(if d=1 then h 4 else 0),
    ((h 3*vd+w 3*hd)*w 0-w 3*vd*h 0)/(w 0)^2+(if d=2 then h 4 else 0),
    (2*h 4+(kineticD w h*w 0-kinetic w*h 0)/(w 0)^2)*vd+(2*w 4+kinetic w/w 0)*hd]

theorem flux_derivative {w : ℝ → State} {h : State} {s : ℝ}
    (hw : HasDerivAt w h s) (hq : w s 0 ≠ 0) (d : Fin 3) :
    HasDerivAt (fun t => primitiveFlux (w t) d) (primitiveFluxD (w s) h d) s := by
  let k : Fin 5 := ⟨d.val+1,by omega⟩
  have hd := hasDerivAt_pi.mp hw k
  have h0 := hasDerivAt_pi.mp hw 0
  have h4 := hasDerivAt_pi.mp hw 4
  have hc (j : Fin 3) : HasDerivAt (fun t => if d=j then w t 4 else 0)
      (if d=j then h 4 else 0) s := by
    by_cases heq : d=j
    · simpa only [heq,if_true] using h4
    · simpa only [heq,if_false] using hasDerivAt_const s (0 : ℝ)
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · exact hd.div h0 hq
  · exact (((hasDerivAt_pi.mp hw 1).mul hd).div h0 hq).add (hc 0)
  · exact (((hasDerivAt_pi.mp hw 2).mul hd).div h0 hq).add (hc 1)
  · exact (((hasDerivAt_pi.mp hw 3).mul hd).div h0 hq).add (hc 2)
  · have he := ((h4.const_mul 2).add ((kinetic_derivative hw).div h0 hq)).mul hd
    exact he

theorem principal_flux_identity (w h : State) (hq : w 0 ≠ 0) (d : Fin 3) :
    primitiveFluxD w h d = jacobian w
      (EulerPrimitiveEnergy.principal (w 0) (w 4) (w ⟨d.val+1,by omega⟩) d h) := by
  funext i
  fin_cases d <;> fin_cases i <;>
    simp [primitiveFluxD,jacobian,EulerPrimitiveEnergy.principal,kinetic,kineticD] <;> field_simp <;> ring

theorem conserved_as_primitive (w : State) :
    conserved w = EulerAdmissible.primitive (1/w 0) (w 4) ![w 1,w 2,w 3] := by
  funext i
  fin_cases i <;> simp [conserved,EulerAdmissible.primitive,kinetic,EulerAdmissible.kinetic] <;> ring

theorem canonical_flux (w : State) (hq : 0 < w 0) (d : Fin 3) :
    EulerAdmissible.eulerFlux (conserved w) d = primitiveFlux w d := by
  have hr : 0 < 1/w 0 := by positivity
  rw [conserved_as_primitive,EulerAdmissible.flux_primitive _ _ _ hr d]
  funext i
  fin_cases d <;> fin_cases i <;> dsimp [primitiveFlux,EulerAdmissible.primitiveFlux,kinetic,EulerAdmissible.kinetic] <;> ring

theorem canonical_flux_derivative {w : ℝ → State} {h : State} {s : ℝ}
    (hw : HasDerivAt w h s) (hq : 0 < w s 0) (d : Fin 3) :
    HasDerivAt (fun t => EulerAdmissible.eulerFlux (conserved (w t)) d)
      (jacobian (w s) (EulerPrimitiveEnergy.principal (w s 0) (w s 4)
        (w s ⟨d.val+1,by omega⟩) d h)) s := by
  have hpos : ∀ᶠ t in 𝓝 s, 0 < w t 0 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hw) 0).continuousAt hq
  have heq : (fun t => EulerAdmissible.eulerFlux (conserved (w t)) d) =ᶠ[𝓝 s]
      (fun t => primitiveFlux (w t) d) := hpos.mono (fun t ht => canonical_flux (w t) ht d)
  have hder := (flux_derivative hw (ne_of_gt hq) d).congr_of_eventuallyEq heq
  rwa [principal_flux_identity (w s) h (ne_of_gt hq) d] at hder

-- The derivative curves pass through one common physical point. No solution
-- existence or numerical stability is inferred from this equivalence.
theorem euler_residual_equivalence (w ht : State) (hx : Fin 3 → State)
    (timeCurve : ℝ → State) (spaceCurve : Fin 3 → ℝ → State)
    (hqt : 0 < w 0) (hvt : timeCurve 0=w) (hvx : ∀ d, spaceCurve d 0=w)
    (hdt : HasDerivAt timeCurve ht 0) (hdx : ∀ d, HasDerivAt (spaceCurve d) (hx d) 0) :
    (deriv (fun t => conserved (timeCurve t)) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 0 t)) 0) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 1 t)) 1) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 2 t)) 2) 0=0) ↔
    ht+EulerPrimitiveEnergy.principal (w 0) (w 4) (w 1) 0 (hx 0)+
      EulerPrimitiveEnergy.principal (w 0) (w 4) (w 2) 1 (hx 1)+
      EulerPrimitiveEnergy.principal (w 0) (w 4) (w 3) 2 (hx 2)=0 := by
  have htime := (conserved_derivative hdt (by rw [hvt]; exact ne_of_gt hqt)).deriv
  have hspace (d : Fin 3) := (canonical_flux_derivative (hdx d) (by rw [hvx]; exact hqt) d).deriv
  rw [htime,hspace 0,hspace 1,hspace 2]
  simp only [hvt,hvx]
  rw [← jacobian_add,← jacobian_add,← jacobian_add]
  constructor
  · intro h
    apply jacobian_injective w (ne_of_gt hqt)
    simpa only [jacobian_zero] using h
  · intro h
    exact (congrArg (jacobian w) h).trans (jacobian_zero w)
end EulerConservativePrimitive


-- Assemble after PrimitiveEnergy.lean. These estimates concern the principal
-- linearized Euler step; nonlinear coefficient-variation bounds are separate.
noncomputable section
namespace EulerDiscreteEnergy
open EulerPrimitiveEnergy
open scoped BigOperators

theorem metric_add_right (q p : ℝ) (x y z : State) :
    metric q p x (y+z) = metric q p x y+metric q p x z := by
  dsimp [metric]
  ring

theorem metric_sub_right (q p : ℝ) (x y z : State) :
    metric q p x (y-z) = metric q p x y-metric q p x z := by
  dsimp [metric]
  ring

theorem metric_smul_right (q p a : ℝ) (x y : State) :
    metric q p x (a • y) = a*metric q p x y := by
  dsimp [metric]
  ring

theorem metric_sub_left (q p : ℝ) (x y z : State) :
    metric q p (x-y) z = metric q p x z-metric q p y z := by
  rw [metric_symmetric q p (x-y) z,metric_sub_right,
    metric_symmetric q p z x,metric_symmetric q p z y]

theorem metric_sum_right {I : Type*} [Fintype I] (q p : ℝ) (x : State) (y : I → State) :
    metric q p x (∑ i, y i) = ∑ i, metric q p x (y i) := by
  simp [metric,Finset.sum_apply,Finset.sum_add_distrib,div_eq_mul_inv,
    Finset.mul_sum,Finset.sum_mul,mul_add,add_mul,mul_assoc]

theorem acoustic_square_identity (q p c x y : ℝ) (hq : q ≠ 0) (hp : p ≠ 0)
    (hc : c ≠ 0) (hc2 : c^2=2*p*q) :
    c*(x^2/(2*p)+y^2/q)-2*x*y = (q*x-c*y)^2/(q*c) := by
  field_simp
  linear_combination q*x^2*hc2

theorem acoustic_cross_bound (q p c x y : ℝ) (hq : 0 < q) (hp : 0 < p)
    (hc : 0 < c) (hc2 : c^2=2*p*q) :
    |2*x*y| ≤ c*(x^2/(2*p)+y^2/q) := by
  have h1 := acoustic_square_identity q p c x y (ne_of_gt hq) (ne_of_gt hp) (ne_of_gt hc) hc2
  have h2 := acoustic_square_identity q p c x (-y) (ne_of_gt hq) (ne_of_gt hp) (ne_of_gt hc) hc2
  have hA : 0 ≤ (q*x-c*y)^2/(q*c) := by positivity
  have hB : 0 ≤ (q*x-c*(-y))^2/(q*c) := by positivity
  simp only [neg_sq] at h2
  apply abs_le.mpr
  constructor <;> nlinarith

theorem acoustic_part_le_metric (q p : ℝ) (hq : 0 < q) (h : State) (d : Fin 3) :
    h 4^2/(2*p)+h ⟨d.val+1,by omega⟩^2/q ≤ metric q p h h := by
  have hd : h ⟨d.val+1,by omega⟩^2 ≤ h 1^2+h 2^2+h 3^2 := by
    fin_cases d <;> dsimp <;> nlinarith [sq_nonneg (h 1),sq_nonneg (h 2),sq_nonneg (h 3)]
  calc
    _ ≤ h 4^2/(2*p)+(h 1^2+h 2^2+h 3^2)/q :=
      add_le_add_left (div_le_div_of_nonneg_right hd hq.le) _
    _ ≤ metric q p h h := by rw [metric_squares]; nlinarith [sq_nonneg (h 0/q+h 4/(2*p))]

theorem principal_quadratic_bound (q p vd : ℝ) (hq : 0 < q) (hp : 0 < p)
    (h : State) (d : Fin 3) :
    |metric q p h (principal q p vd d h)| ≤
      (|vd|+Real.sqrt (2*p*q))*metric q p h h := by
  let c := Real.sqrt (2*p*q)
  have hc : 0 < c := Real.sqrt_pos.2 (by positivity)
  have hc2 : c^2=2*p*q := Real.sq_sqrt (by positivity)
  have hcross := acoustic_cross_bound q p c (h 4) (h ⟨d.val+1,by omega⟩) hq hp hc hc2
  have hac := acoustic_part_le_metric q p hq h d
  have he := metric_nonnegative q p hq hp h
  rw [principal_metric_identity q p vd hq hp d h h]
  have heq : vd*metric q p h h+h 4*h ⟨d.val+1,by omega⟩+h ⟨d.val+1,by omega⟩*h 4 =
      vd*metric q p h h+2*h 4*h ⟨d.val+1,by omega⟩ := by ring
  rw [heq]
  calc
    _ ≤ |vd*metric q p h h|+|2*h 4*h ⟨d.val+1,by omega⟩| := abs_add_le _ _
    _ ≤ |vd| *metric q p h h+c*(h 4^2/(2*p)+h ⟨d.val+1,by omega⟩^2/q) := by
      rw [abs_mul,abs_of_nonneg he]
      exact add_le_add_left hcross _
    _ ≤ (|vd|+Real.sqrt (2*p*q))*metric q p h h := by
      have hh := mul_le_mul_of_nonneg_left hac hc.le
      dsimp [c] at hh
      nlinarith

theorem split_operator_nonnegative (q p vd a sign : ℝ) (hq : 0 < q) (hp : 0 < p)
    (ha : |vd|+Real.sqrt (2*p*q) ≤ a) (hs : sign^2=1) (h : State) (d : Fin 3) :
    0 ≤ metric q p h (a • h+sign • principal q p vd d h) := by
  rw [metric_add_right,metric_smul_right,metric_smul_right]
  have hbound := abs_le.mp (principal_quadratic_bound q p vd hq hp h d)
  have he := metric_nonnegative q p hq hp h
  have hh := mul_le_mul_of_nonneg_right ha he
  rcases sq_eq_one_iff.mp hs with rfl | rfl <;> nlinarith

theorem metric_add_left (q p : ℝ) (x y z : State) :
    metric q p (x+y) z = metric q p x z+metric q p y z := by
  dsimp [metric]
  ring

theorem metric_smul_left (q p a : ℝ) (x y : State) :
    metric q p (a • x) y = a*metric q p x y := by
  dsimp [metric]
  ring

-- Matrix-weighted Jensen inequality. Positive self-adjoint actions partition
-- the identity; the conclusion is proved by expanding nonnegative squares.
theorem energy_jensen {I : Type*} [Fintype I] (q p : ℝ)
    (A : I → State → State)
    (hsub : ∀ i x y, A i (x-y)=A i x-A i y)
    (hself : ∀ i x y, metric q p x (A i y)=metric q p (A i x) y)
    (hpos : ∀ i x, 0 ≤ metric q p x (A i x))
    (hpartition : ∀ x, ∑ i, A i x=x) (x : I → State) :
    metric q p (∑ i, A i (x i)) (∑ i, A i (x i)) ≤ ∑ i, metric q p (x i) (A i (x i)) := by
  let y := ∑ i, A i (x i)
  have hnonneg : 0 ≤ ∑ i, metric q p (x i-y) (A i (x i-y)) :=
    Finset.sum_nonneg (fun i _ => hpos i (x i-y))
  have heach (i : I) : metric q p (x i-y) (A i (x i-y)) =
      metric q p (x i) (A i (x i))-metric q p y (A i (x i))-
        metric q p y (A i (x i))+metric q p y (A i y) := by
    rw [hsub,metric_sub_right,metric_sub_left,metric_sub_left,
      hself i (x i) y,metric_symmetric q p (A i (x i)) y]
    ring
  have hsum : (∑ i, metric q p (x i-y) (A i (x i-y))) =
      (∑ i, metric q p (x i) (A i (x i)))-metric q p y y := by
    simp_rw [heach,Finset.sum_add_distrib,Finset.sum_sub_distrib,← metric_sum_right]
    rw [hpartition]
    change (∑ i, metric q p (x i) (A i (x i)))-metric q p y y-
      metric q p y y+metric q p y y = _
    ring
  rw [hsum] at hnonneg
  exact sub_nonneg.mp hnonneg

def splitAction (q p vd a ratio sign : ℝ) (d : Fin 3) (x : State) : State :=
  (ratio/2) • (a • x+sign • principal q p vd d x)

theorem splitAction_sub (q p vd a ratio sign : ℝ) (d : Fin 3) (x y : State) :
    splitAction q p vd a ratio sign d (x-y) =
      splitAction q p vd a ratio sign d x-splitAction q p vd a ratio sign d y := by
  funext i
  fin_cases d <;> fin_cases i <;> dsimp [splitAction,principal] <;> ring

theorem splitAction_symmetric (q p vd a ratio sign : ℝ) (hq : 0 < q) (hp : 0 < p)
    (d : Fin 3) (x y : State) :
    metric q p x (splitAction q p vd a ratio sign d y) =
      metric q p (splitAction q p vd a ratio sign d x) y := by
  simp only [splitAction,metric_smul_right,metric_smul_left,metric_add_right,
    metric_add_left,symmetric_principal_part q p vd hq hp d x y]

theorem splitAction_nonnegative (q p vd a ratio sign : ℝ) (hq : 0 < q) (hp : 0 < p)
    (hr : 0 ≤ ratio) (ha : |vd|+Real.sqrt (2*p*q) ≤ a) (hs : sign^2=1)
    (d : Fin 3) (x : State) : 0 ≤ metric q p x (splitAction q p vd a ratio sign d x) := by
  rw [splitAction,metric_smul_right]
  exact mul_nonneg (by positivity) (split_operator_nonnegative q p vd a sign hq hp ha hs x d)

def actions (q p ratio : ℝ) (v a : Fin 3 → ℝ) (i : Fin 7) (x : State) : State :=
  ![(1-ratio*(a 0+a 1+a 2)) • x,
    splitAction q p (v 0) (a 0) ratio (-1) 0 x,splitAction q p (v 0) (a 0) ratio 1 0 x,
    splitAction q p (v 1) (a 1) ratio (-1) 1 x,splitAction q p (v 1) (a 1) ratio 1 1 x,
    splitAction q p (v 2) (a 2) ratio (-1) 2 x,splitAction q p (v 2) (a 2) ratio 1 2 x] i

theorem actions_sub (q p ratio : ℝ) (v a : Fin 3 → ℝ) (i : Fin 7) (x y : State) :
    actions q p ratio v a i (x-y) = actions q p ratio v a i x-actions q p ratio v a i y := by
  fin_cases i <;> dsimp [actions]
  · simp only [smul_sub]
  all_goals apply splitAction_sub

theorem actions_partition (q p ratio : ℝ) (v a : Fin 3 → ℝ) (x : State) :
    ∑ i, actions q p ratio v a i x = x := by
  funext j
  simp [actions,splitAction,Fin.sum_univ_succ]
  ring

theorem actions_symmetric (q p ratio : ℝ) (v a : Fin 3 → ℝ) (hq : 0 < q) (hp : 0 < p)
    (i : Fin 7) (x y : State) :
    metric q p x (actions q p ratio v a i y) = metric q p (actions q p ratio v a i x) y := by
  fin_cases i <;> dsimp [actions]
  · simp only [metric_smul_right,metric_smul_left]
  all_goals exact splitAction_symmetric _ _ _ _ _ _ hq hp _ x y

theorem actions_nonnegative (q p ratio : ℝ) (v a : Fin 3 → ℝ) (hq : 0 < q) (hp : 0 < p)
    (hr : 0 ≤ ratio) (ha : ∀ d, |v d|+Real.sqrt (2*p*q) ≤ a d)
    (hcf : ratio*(a 0+a 1+a 2) ≤ 1) (i : Fin 7) (x : State) :
    0 ≤ metric q p x (actions q p ratio v a i x) := by
  fin_cases i <;> dsimp [actions]
  · rw [metric_smul_right]
    exact mul_nonneg (sub_nonneg.mpr hcf) (metric_nonnegative q p hq hp x)
  · exact splitAction_nonnegative _ _ _ _ _ _ hq hp hr (ha 0) (by norm_num) _ x
  · exact splitAction_nonnegative _ _ _ _ _ _ hq hp hr (ha 0) (by norm_num) _ x
  · exact splitAction_nonnegative _ _ _ _ _ _ hq hp hr (ha 1) (by norm_num) _ x
  · exact splitAction_nonnegative _ _ _ _ _ _ hq hp hr (ha 1) (by norm_num) _ x
  · exact splitAction_nonnegative _ _ _ _ _ _ hq hp hr (ha 2) (by norm_num) _ x
  · exact splitAction_nonnegative _ _ _ _ _ _ hq hp hr (ha 2) (by norm_num) _ x

def linearizedUpdate {I : Type*} (q p ratio : ℝ) (v a : Fin 3 → ℝ)
    (shift : Fin 7 → Equiv.Perm I) (u : I → State) (i : I) : State :=
  ∑ j, actions q p ratio v a j (u (shift j i))

theorem frozen_linearized_energy_contraction {I : Type*} [Fintype I]
    (q p ratio : ℝ) (v a : Fin 3 → ℝ) (hq : 0 < q) (hp : 0 < p)
    (hr : 0 ≤ ratio) (ha : ∀ d, |v d|+Real.sqrt (2*p*q) ≤ a d)
    (hcf : ratio*(a 0+a 1+a 2) ≤ 1) (shift : Fin 7 → Equiv.Perm I) (u : I → State) :
    (∑ i, metric q p (linearizedUpdate q p ratio v a shift u i)
      (linearizedUpdate q p ratio v a shift u i)) ≤ ∑ i, metric q p (u i) (u i) := by
  have hpoint (i : I) := energy_jensen q p (actions q p ratio v a)
    (actions_sub q p ratio v a) (actions_symmetric q p ratio v a hq hp)
    (actions_nonnegative q p ratio v a hq hp hr ha hcf)
    (actions_partition q p ratio v a) (fun j => u (shift j i))
  have hs (j : Fin 7) :
      (∑ i, metric q p (u (shift j i)) (actions q p ratio v a j (u (shift j i)))) =
      ∑ i, metric q p (u i) (actions q p ratio v a j (u i)) :=
    Equiv.sum_comp (shift j) (fun i => metric q p (u i) (actions q p ratio v a j (u i)))
  calc
    _ ≤ ∑ i, ∑ j, metric q p (u (shift j i)) (actions q p ratio v a j (u (shift j i))) :=
      Finset.sum_le_sum (fun i _ => hpoint i)
    _ = ∑ i, metric q p (u i) (u i) := by
      rw [Finset.sum_comm]
      simp_rw [hs]
      rw [Finset.sum_comm]
      simp_rw [← metric_sum_right,actions_partition]
end EulerDiscreteEnergy

-- Assemble after PrimitiveEnergy.lean. These are explicit uniform norm bounds
-- on a declared positive state box, not a proof that the solution stays there.
noncomputable section
namespace EulerEnergyBounds
open EulerPrimitiveEnergy

def sizeSquared (h : State) : ℝ := h 0^2+h 1^2+h 2^2+h 3^2+h 4^2

theorem metric_components (q p : ℝ) (hq : 0 < q) (hp : 0 < p) (h : State) :
    h 4^2/(2*p) ≤ metric q p h h ∧
    (h 1^2+h 2^2+h 3^2)/q ≤ metric q p h h ∧
    (h 0/q+h 4/(2*p))^2 ≤ metric q p h h := by
  have hA : 0 ≤ h 4^2/(2*p) := by positivity
  have hB : 0 ≤ (h 1^2+h 2^2+h 3^2)/q := by positivity
  have hC := sq_nonneg (h 0/q+h 4/(2*p))
  rw [metric_squares]
  exact ⟨by linarith,by linarith,by linarith⟩

theorem pressure_coercivity (q p : ℝ) (hq : 0 < q) (hp : 0 < p) (h : State) :
    h 4^2 ≤ 2*p*metric q p h h := by
  have h := (div_le_iff₀ (by positivity : 0 < 2*p)).mp (metric_components q p hq hp h).1
  nlinarith

theorem velocity_coercivity (q p : ℝ) (hq : 0 < q) (hp : 0 < p) (h : State) :
    h 1^2+h 2^2+h 3^2 ≤ q*metric q p h h := by
  have h := (div_le_iff₀ hq).mp (metric_components q p hq hp h).2.1
  nlinarith

theorem box_coercivity (q p : ℝ) (hq0 : 1/4 ≤ q) (hq1 : q ≤ 4)
    (hp0 : 1/4 ≤ p) (hp1 : p ≤ 4) (h : State) :
    sizeSquared h ≤ 108*metric q p h h := by
  have hq : 0 < q := by linarith
  have hp : 0 < p := by linarith
  have he := metric_nonnegative q p hq hp h
  obtain ⟨ha,hb,hc⟩ := metric_components q p hq hp h
  have hpressure : h 4^2 ≤ 8*metric q p h h := by
    have hh := pressure_coercivity q p hq hp h
    have hh2 := mul_le_mul_of_nonneg_right hp1 he
    nlinarith
  have hvel : h 1^2+h 2^2+h 3^2 ≤ 4*metric q p h h := by
    exact (velocity_coercivity q p hq hp h).trans (mul_le_mul_of_nonneg_right hq1 he)
  have hsmallpressure : (h 4/(2*p))^2 ≤ 2*metric q p h h := by
    calc
      _ = (h 4^2/(2*p))/(2*p) := by ring
      _ ≤ metric q p h h/(2*p) := div_le_div_of_nonneg_right ha (by positivity)
      _ ≤ 2*metric q p h h := by
        apply (div_le_iff₀ (by positivity : 0 < 2*p)).mpr
        nlinarith
  have hscaled : (h 0/q)^2 ≤ 6*metric q p h h := by
    nlinarith [sq_nonneg ((h 0/q+h 4/(2*p))+(h 4/(2*p)))]
  have hq2 : q^2 ≤ 16 := by nlinarith
  have h0 : h 0^2 ≤ 96*metric q p h h := by
    calc
      _ = q^2*(h 0/q)^2 := by field_simp
      _ ≤ q^2*(6*metric q p h h) := mul_le_mul_of_nonneg_left hscaled (sq_nonneg q)
      _ ≤ 16*(6*metric q p h h) := mul_le_mul_of_nonneg_right hq2 (by positivity)
      _ = 96*metric q p h h := by ring
  dsimp [sizeSquared]
  linarith

theorem box_upper_bound (q p : ℝ) (hq0 : 1/4 ≤ q) (hp0 : 1/4 ≤ p) (h : State) :
    metric q p h h ≤ 32*sizeSquared h := by
  have hq : 0 < q := by linarith
  have hp : 0 < p := by linarith
  have hqi : 1/q ≤ 4 := (div_le_iff₀ hq).mpr (by linarith)
  have hpi : 1/(2*p) ≤ 2 := (div_le_iff₀ (by positivity : 0 < 2*p)).mpr (by linarith)
  have hqin : 0 ≤ 1/q := by positivity
  have hpin : 0 ≤ 1/(2*p) := by positivity
  have hqisq : (1/q)^2 ≤ 16 := by nlinarith
  have hpisq : (1/(2*p))^2 ≤ 4 := by nlinarith
  have hqterm : (h 0/q)^2 ≤ 16*(h 0)^2 := by
    calc
      _ = (1/q)^2*(h 0)^2 := by ring
      _ ≤ 16*(h 0)^2 := mul_le_mul_of_nonneg_right hqisq (sq_nonneg _)
  have hpterm : (h 4/(2*p))^2 ≤ 4*(h 4)^2 := by
    calc
      _ = (1/(2*p))^2*(h 4)^2 := by ring
      _ ≤ 4*(h 4)^2 := mul_le_mul_of_nonneg_right hpisq (sq_nonneg _)
  have ha : h 4^2/(2*p) ≤ 2*(h 4)^2 := by
    simpa [div_eq_mul_inv,mul_comm] using
      mul_le_mul_of_nonneg_right hpi (sq_nonneg (h 4))
  have hb : (h 1^2+h 2^2+h 3^2)/q ≤ 4*(h 1^2+h 2^2+h 3^2) := by
    simpa [div_eq_mul_inv,mul_comm] using
      mul_le_mul_of_nonneg_right hqi (by positivity : 0 ≤ h 1^2+h 2^2+h 3^2)
  rw [metric_squares]
  dsimp [sizeSquared]
  nlinarith [sq_nonneg (h 0/q-h 4/(2*p)),sq_nonneg (h 1),sq_nonneg (h 2),sq_nonneg (h 3),sq_nonneg (h 4)]
end EulerEnergyBounds

-- Assemble after DiscreteEnergy.lean and EnergyBounds.lean. The first inequality
-- displays the exact coefficient-variation defect rather than hiding it in an
-- assumed stability constant. Uniform control of that defect is still needed.
noncomputable section
namespace EulerVariableEnergy
open EulerPrimitiveEnergy EulerDiscreteEnergy
open scoped BigOperators

def localContribution {I : Type*} (q p : I → ℝ) (ratio : ℝ)
    (v : I → Fin 3 → ℝ) (a : Fin 3 → ℝ) (i : I) (j : Fin 7) (x : State) : ℝ :=
  metric (q i) (p i) x (actions (q i) (p i) ratio (v i) a j x)

def variableUpdate {I : Type*} (q p : I → ℝ) (ratio : ℝ)
    (v : I → Fin 3 → ℝ) (a : Fin 3 → ℝ)
    (shift : Fin 7 → Equiv.Perm I) (u : I → State) (i : I) : State :=
  ∑ j, actions (q i) (p i) ratio (v i) a j (u (shift j i))

def variationDefect {I : Type*} [Fintype I] (q p : I → ℝ) (ratio : ℝ)
    (v : I → Fin 3 → ℝ) (a : Fin 3 → ℝ)
    (shift : Fin 7 → Equiv.Perm I) (u : I → State) : ℝ :=
  ∑ i, ∑ j, (localContribution q p ratio v a ((shift j).symm i) j (u i)-
    localContribution q p ratio v a i j (u i))

theorem variable_principal_energy_defect {I : Type*} [Fintype I]
    (q p : I → ℝ) (ratio : ℝ) (v : I → Fin 3 → ℝ) (a : Fin 3 → ℝ)
    (hq : ∀ i, 0 < q i) (hp : ∀ i, 0 < p i) (hr : 0 ≤ ratio)
    (ha : ∀ i d, |v i d|+Real.sqrt (2*p i*q i) ≤ a d)
    (hcf : ratio*(a 0+a 1+a 2) ≤ 1)
    (shift : Fin 7 → Equiv.Perm I) (u : I → State) :
    (∑ i, metric (q i) (p i) (variableUpdate q p ratio v a shift u i)
      (variableUpdate q p ratio v a shift u i)) ≤
      (∑ i, metric (q i) (p i) (u i) (u i))+variationDefect q p ratio v a shift u := by
  have hpoint (i : I) := energy_jensen (q i) (p i) (actions (q i) (p i) ratio (v i) a)
    (actions_sub (q i) (p i) ratio (v i) a)
    (actions_symmetric (q i) (p i) ratio (v i) a (hq i) (hp i))
    (actions_nonnegative (q i) (p i) ratio (v i) a (hq i) (hp i) hr (ha i) hcf)
    (actions_partition (q i) (p i) ratio (v i) a) (fun j => u (shift j i))
  have hs (j : Fin 7) :
      (∑ i, localContribution q p ratio v a i j (u (shift j i))) =
      ∑ i, localContribution q p ratio v a ((shift j).symm i) j (u i) := by
    have h := Equiv.sum_comp (shift j)
      (fun i => localContribution q p ratio v a ((shift j).symm i) j (u i))
    simpa only [Equiv.symm_apply_apply] using h
  have hpresent (i : I) : ∑ j, localContribution q p ratio v a i j (u i) =
      metric (q i) (p i) (u i) (u i) := by
    simp only [localContribution,← metric_sum_right,actions_partition]
  calc
    _ ≤ ∑ i, ∑ j, localContribution q p ratio v a i j (u (shift j i)) :=
      Finset.sum_le_sum (fun i _ => hpoint i)
    _ = (∑ i, metric (q i) (p i) (u i) (u i))+variationDefect q p ratio v a shift u := by
      rw [Finset.sum_comm]
      simp_rw [hs]
      rw [Finset.sum_comm]
      simp only [variationDefect,Finset.sum_sub_distrib,hpresent]
      ring

-- The acoustic pressure-velocity cross term is constant in the symmetrized
-- flux. Its spatial coefficient variation cancels exactly.
theorem principal_form_variation (q p q' p' v v' : ℝ)
    (hq : 0 < q) (hp : 0 < p) (hq' : 0 < q') (hp' : 0 < p')
    (d : Fin 3) (x y : State) :
    metric q' p' x (principal q' p' v' d y)-metric q p x (principal q p v d y) =
      v'*metric q' p' x y-v*metric q p x y := by
  rw [principal_metric_identity q' p' v' hq' hp' d x y,
    principal_metric_identity q p v hq hp d x y]
  ring
end EulerVariableEnergy


-- Mesh-independent control of grid values by averaged difference energies.
-- This does not assert a bound on an Euler trajectory's derivative energies.
noncomputable section
namespace EulerGridSobolev
open scoped BigOperators

theorem ordered_oscillation (f : ℕ → ℝ) (n i j : ℕ)
    (hij : i ≤ j) (hj : j < n) :
    (f j-f i)^2 ≤ (n : ℝ)*∑ k ∈ Finset.range n, (f (k+1)-f k)^2 := by
  have htel := Finset.sum_Ico_sub f hij
  have hcauchy := Finset.sum_mul_sq_le_sq_mul_sq (Finset.Ico i j)
    (fun _ => (1 : ℝ)) (fun k => f (k+1)-f k)
  simp only [one_mul,one_pow,Finset.sum_const,nsmul_eq_mul,mul_one,Nat.card_Ico] at hcauchy
  rw [htel] at hcauchy
  have hsub : Finset.Ico i j ⊆ Finset.range n := by
    intro k hk
    simp only [Finset.mem_Ico] at hk
    exact Finset.mem_range.mpr (lt_trans hk.2 hj)
  have hs : (∑ k ∈ Finset.Ico i j, (f (k+1)-f k)^2) ≤
      ∑ k ∈ Finset.range n, (f (k+1)-f k)^2 :=
    Finset.sum_le_sum_of_subset_of_nonneg hsub (fun k _ _ => sq_nonneg _)
  have hcard : ((j-i : ℕ) : ℝ) ≤ n := by exact_mod_cast (show j-i ≤ n by omega)
  calc
    _ ≤ ((j-i : ℕ) : ℝ)*(∑ k ∈ Finset.Ico i j, (f (k+1)-f k)^2) := hcauchy
    _ ≤ (n : ℝ)*(∑ k ∈ Finset.Ico i j, (f (k+1)-f k)^2) :=
      mul_le_mul_of_nonneg_right hcard (Finset.sum_nonneg (fun k _ => sq_nonneg _))
    _ ≤ _ := mul_le_mul_of_nonneg_left hs (Nat.cast_nonneg _)

theorem oscillation (f : ℕ → ℝ) (n i j : ℕ) (hi : i < n) (hj : j < n) :
    (f i-f j)^2 ≤ (n : ℝ)*∑ k ∈ Finset.range n, (f (k+1)-f k)^2 := by
  rcases le_total i j with hij | hji
  · have h := ordered_oscillation f n i j hij hj
    nlinarith
  · exact ordered_oscillation f n j i hji hi

theorem one_dimensional_embedding (f : ℕ → ℝ) (n i : ℕ) (hi : i < n) :
    f i^2 ≤ (2/(n : ℝ))*(∑ k ∈ Finset.range n, f k^2)+
      2*(n : ℝ)*(∑ k ∈ Finset.range n, (f (k+1)-f k)^2) := by
  have hn : 0 < (n : ℝ) := by exact_mod_cast (show 0 < n by omega)
  have hpoint (j : ℕ) (hj : j ∈ Finset.range n) :
      f i^2 ≤ 2*f j^2+2*(n : ℝ)*(∑ k ∈ Finset.range n, (f (k+1)-f k)^2) := by
    have h := oscillation f n i j hi (Finset.mem_range.mp hj)
    nlinarith [sq_nonneg (f i-2*f j)]
  have hs := Finset.sum_le_sum hpoint
  simp only [Finset.sum_add_distrib,Finset.sum_const,Finset.card_range,nsmul_eq_mul,
    ← Finset.mul_sum] at hs
  have hdiv := (div_le_div_of_nonneg_right hs hn.le)
  calc
    _ = ((n : ℝ)*f i^2)/(n : ℝ) := by field_simp
    _ ≤ _ := hdiv
    _ = _ := by field_simp

def energy1 (n : ℕ) (f : ℕ → ℝ) : ℝ :=
  (1/(n : ℝ))*(∑ k ∈ Finset.range n, f k^2)+
    (n : ℝ)*(∑ k ∈ Finset.range n, (f (k+1)-f k)^2)

def energy2 (n : ℕ) (f : ℕ → ℕ → ℝ) : ℝ :=
  (1/(n : ℝ))*(∑ k ∈ Finset.range n, energy1 n (f k))+
    (n : ℝ)*(∑ k ∈ Finset.range n, energy1 n (fun j => f (k+1) j-f k j))

def energy3 (n : ℕ) (f : ℕ → ℕ → ℕ → ℝ) : ℝ :=
  (1/(n : ℝ))*(∑ k ∈ Finset.range n, energy2 n (f k))+
    (n : ℝ)*(∑ k ∈ Finset.range n, energy2 n (fun j l => f (k+1) j l-f k j l))

theorem embedding1 (f : ℕ → ℝ) (n i : ℕ) (hi : i < n) :
    f i^2 ≤ 2*energy1 n f := by
  calc
    _ ≤ _ := one_dimensional_embedding f n i hi
    _ = _ := by dsimp [energy1]; ring

theorem embedding_step (f e de : ℕ → ℝ) (C : ℝ) (n i : ℕ) (hi : i < n)
    (he : ∀ k ∈ Finset.range n, f k^2 ≤ C*e k)
    (hde : ∀ k ∈ Finset.range n, (f (k+1)-f k)^2 ≤ C*de k) :
    f i^2 ≤ 2*C*((1/(n : ℝ))*(∑ k ∈ Finset.range n, e k)+
      (n : ℝ)*(∑ k ∈ Finset.range n, de k)) := by
  have hs := Finset.sum_le_sum he
  have hds := Finset.sum_le_sum hde
  rw [← Finset.mul_sum] at hs hds
  calc
    _ ≤ _ := one_dimensional_embedding f n i hi
    _ ≤ (2/(n : ℝ))*(C*∑ k ∈ Finset.range n, e k)+
        2*(n : ℝ)*(C*∑ k ∈ Finset.range n, de k) :=
      add_le_add (mul_le_mul_of_nonneg_left hs (by positivity))
        (mul_le_mul_of_nonneg_left hds (by positivity))
    _ = _ := by ring

theorem embedding2 (f : ℕ → ℕ → ℝ) (n i j : ℕ) (hi : i < n) (hj : j < n) :
    f i j^2 ≤ 4*energy2 n f := by
  have h := embedding_step (fun x => f x j) (fun x => energy1 n (f x))
    (fun x => energy1 n (fun y => f (x+1) y-f x y)) 2 n i hi
    (fun x _ => embedding1 (f x) n j hj)
    (fun x _ => embedding1 (fun y => f (x+1) y-f x y) n j hj)
  simpa only [energy2,show (2 : ℝ)*2 = 4 by norm_num] using h

-- The constant 8 is independent of the grid size. The recursively defined
-- energy contains the eight mixed forward differences with each coordinate
-- differentiated at most once, scaled to the unit periodic cube.
theorem three_dimensional_embedding (f : ℕ → ℕ → ℕ → ℝ) (n i j k : ℕ)
    (hi : i < n) (hj : j < n) (hk : k < n) :
    f i j k^2 ≤ 8*energy3 n f := by
  have h := embedding_step (fun x => f x j k) (fun x => energy2 n (f x))
    (fun x => energy2 n (fun y z => f (x+1) y z-f x y z)) 4 n i hi
    (fun x _ => embedding2 (f x) n j k hj hk)
    (fun x _ => embedding2 (fun y z => f (x+1) y z-f x y z) n j k hj hk)
  simpa only [energy3,show (2 : ℝ)*4 = 8 by norm_num] using h

end EulerGridSobolev

-- Assemble after EnergyBounds.lean. Quantitative coefficient bounds on an
-- explicit positive state region; remaining in that region is a separate task.
noncomputable section
namespace EulerCoefficientBounds
open EulerPrimitiveEnergy EulerEnergyBounds

theorem reciprocal_bounds (x : ℝ) (hx : 1/4 ≤ x) : 0 ≤ 1/x ∧ 1/x ≤ 4 := by
  have hp : 0 < x := by linarith
  exact ⟨by positivity,(div_le_iff₀ hp).mpr (by linarith)⟩

theorem reciprocal_variation (x y : ℝ) (hx : 1/4 ≤ x) (hy : 1/4 ≤ y) :
    |1/x-1/y| ≤ 16*|x-y| := by
  have hxp : 0 < x := by linarith
  have hyp : 0 < y := by linarith
  have heq : 1/x-1/y = (y-x)/(x*y) := by field_simp
  have hprod : 1/16 ≤ x*y := by
    calc
      _ = (1/4 : ℝ)*(1/4) := by norm_num
      _ ≤ x*y := mul_le_mul hx hy (by norm_num) hxp.le
  rw [heq,abs_div,abs_of_pos (mul_pos hxp hyp),abs_sub_comm]
  apply (div_le_iff₀ (mul_pos hxp hyp)).mpr
  nlinarith [mul_le_mul_of_nonneg_right hprod (abs_nonneg (x-y))]

theorem metric_coefficients (q p : ℝ) (x : State) :
    metric q p x x = (1/(2*p)+(1/(2*p))^2)*x 4^2+
      (1/q)*(x 1^2+x 2^2+x 3^2)+(1/q)^2*x 0^2+
      ((1/q)*(1/(2*p)))*(2*x 0*x 4) := by
  dsimp [metric]
  ring

theorem quadratic_coefficient_bound (A B C D : ℝ) (x : State) :
    |A*x 4^2+B*(x 1^2+x 2^2+x 3^2)+C*x 0^2+D*(2*x 0*x 4)| ≤
      (|A|+|B|+|C|+|D|)*sizeSquared x := by
  have hv : 0 ≤ x 1^2+x 2^2+x 3^2 := by positivity
  have h0 : x 0^2 ≤ sizeSquared x := by
    dsimp [sizeSquared]; nlinarith [sq_nonneg (x 1),sq_nonneg (x 2),sq_nonneg (x 3),sq_nonneg (x 4)]
  have h4 : x 4^2 ≤ sizeSquared x := by
    dsimp [sizeSquared]; nlinarith [sq_nonneg (x 0),sq_nonneg (x 1),sq_nonneg (x 2),sq_nonneg (x 3)]
  have hvb : x 1^2+x 2^2+x 3^2 ≤ sizeSquared x := by
    dsimp [sizeSquared]; nlinarith [sq_nonneg (x 0),sq_nonneg (x 4)]
  have hc : |2*x 0*x 4| ≤ sizeSquared x := by
    apply abs_le.mpr
    dsimp [sizeSquared]
    constructor <;> nlinarith [sq_nonneg (x 0-x 4),sq_nonneg (x 0+x 4),
      sq_nonneg (x 1),sq_nonneg (x 2),sq_nonneg (x 3)]
  calc
    _ ≤ |A*x 4^2+B*(x 1^2+x 2^2+x 3^2)+C*x 0^2|+|D*(2*x 0*x 4)| := abs_add_le _ _
    _ ≤ (|A*x 4^2+B*(x 1^2+x 2^2+x 3^2)|+|C*x 0^2|)+|D*(2*x 0*x 4)| :=
      add_le_add_right (abs_add_le _ _) _
    _ ≤ ((|A*x 4^2|+|B*(x 1^2+x 2^2+x 3^2)|)+|C*x 0^2|)+|D*(2*x 0*x 4)| :=
      add_le_add_right (add_le_add_right (abs_add_le _ _) _) _
    _ = |A| *x 4^2+|B| *(x 1^2+x 2^2+x 3^2)+|C| *x 0^2+|D| *|2*x 0*x 4| := by
      rw [abs_mul,abs_mul,abs_mul,abs_mul,abs_sq,abs_sq,abs_of_nonneg hv]
    _ ≤ |A| *sizeSquared x+|B| *sizeSquared x+|C| *sizeSquared x+|D| *sizeSquared x :=
      add_le_add (add_le_add (add_le_add
        (mul_le_mul_of_nonneg_left h4 (abs_nonneg _))
        (mul_le_mul_of_nonneg_left hvb (abs_nonneg _)))
        (mul_le_mul_of_nonneg_left h0 (abs_nonneg _)))
        (mul_le_mul_of_nonneg_left hc (abs_nonneg _))
    _ = _ := by ring

theorem reciprocal_coefficient_variation (r s r' s' R S : ℝ)
    (hr : 0 ≤ r) (hr' : 0 ≤ r') (hr4 : r ≤ 4) (hr4' : r' ≤ 4)
    (hs : 0 ≤ s) (hs' : 0 ≤ s') (hs2 : s ≤ 2) (hs2' : s' ≤ 2)
    (hR : |r'-r| ≤ R) (hS : |s'-s| ≤ S) :
    |(s'+s'^2)-(s+s^2)|+|r'-r|+|r'^2-r^2|+|r'*s'-r*s| ≤ 11*R+9*S := by
  have hRn : 0 ≤ R := (abs_nonneg _).trans hR
  have hSn : 0 ≤ S := (abs_nonneg _).trans hS
  have hsquares : |s'^2-s^2| ≤ 4*S := by
    calc
      _ = |s'-s| *(s'+s) := by rw [sq_sub_sq,abs_mul,abs_of_nonneg (add_nonneg hs' hs),mul_comm]
      _ ≤ S*(s'+s) := mul_le_mul_of_nonneg_right hS (add_nonneg hs' hs)
      _ ≤ S*4 := mul_le_mul_of_nonneg_left (by linarith) hSn
      _ = _ := by ring
  have hfirst : |(s'+s'^2)-(s+s^2)| ≤ 5*S := by
    calc
      _ = |(s'-s)+(s'^2-s^2)| := by congr 1; ring
      _ ≤ |s'-s|+|s'^2-s^2| := abs_add_le _ _
      _ ≤ S+4*S := add_le_add hS hsquares
      _ = _ := by ring
  have hrsquares : |r'^2-r^2| ≤ 8*R := by
    calc
      _ = |r'-r| *(r'+r) := by rw [sq_sub_sq,abs_mul,abs_of_nonneg (add_nonneg hr' hr),mul_comm]
      _ ≤ R*(r'+r) := mul_le_mul_of_nonneg_right hR (add_nonneg hr' hr)
      _ ≤ R*8 := mul_le_mul_of_nonneg_left (by linarith) hRn
      _ = _ := by ring
  have hcross : |r'*s'-r*s| ≤ 2*R+4*S := by
    calc
      _ = |(r'-r)*s'+r*(s'-s)| := by congr 1; ring
      _ ≤ |(r'-r)*s'|+|r*(s'-s)| := abs_add_le _ _
      _ = |r'-r| *s'+r*|s'-s| := by rw [abs_mul,abs_mul,abs_of_nonneg hs',abs_of_nonneg hr]
      _ ≤ R*s'+r*S := add_le_add (mul_le_mul_of_nonneg_right hR hs')
        (mul_le_mul_of_nonneg_left hS hr)
      _ ≤ R*2+4*S := add_le_add (mul_le_mul_of_nonneg_left hs2' hRn)
        (mul_le_mul_of_nonneg_right hr4 hSn)
      _ = _ := by ring
  linarith

theorem metric_variation (q p q' p' : ℝ)
    (hq : 1/4 ≤ q) (hp : 1/4 ≤ p) (hq' : 1/4 ≤ q') (hp' : 1/4 ≤ p')
    (x : State) : |metric q' p' x x-metric q p x x| ≤
      256*(|q'-q|+|p'-p|)*sizeSquared x := by
  obtain ⟨hr,hr4⟩ := reciprocal_bounds q hq
  obtain ⟨hr',hr4'⟩ := reciprocal_bounds q' hq'
  obtain ⟨ht,ht4⟩ := reciprocal_bounds p hp
  obtain ⟨ht',ht4'⟩ := reciprocal_bounds p' hp'
  have hs : 0 ≤ 1/(2*p) := by positivity
  have hs' : 0 ≤ 1/(2*p') := by positivity
  have hs2 : 1/(2*p) ≤ 2 := by
    have he : 1/(2*p) = (1/p)/2 := by ring
    linarith
  have hs2' : 1/(2*p') ≤ 2 := by
    have he : 1/(2*p') = (1/p')/2 := by ring
    linarith
  have hR := reciprocal_variation q' q hq' hq
  have hS : |1/(2*p')-1/(2*p)| ≤ 8*|p'-p| := by
    have h := reciprocal_variation p' p hp' hp
    have he : 1/(2*p')-1/(2*p) = (1/p'-1/p)/2 := by ring
    rw [he,abs_div,abs_of_pos (by norm_num : (0 : ℝ)<2)]
    linarith
  have hcoeff := reciprocal_coefficient_variation (1/q) (1/(2*p)) (1/q') (1/(2*p'))
    (16*|q'-q|) (8*|p'-p|) hr hr' hr4 hr4' hs hs' hs2 hs2' hR hS
  have hbound := quadratic_coefficient_bound
    ((1/(2*p')+(1/(2*p'))^2)-(1/(2*p)+(1/(2*p))^2))
    (1/q'-1/q) ((1/q')^2-(1/q)^2) ((1/q')*(1/(2*p'))-(1/q)*(1/(2*p))) x
  have he : metric q' p' x x-metric q p x x =
      ((1/(2*p')+(1/(2*p'))^2)-(1/(2*p)+(1/(2*p))^2))*x 4^2+
      (1/q'-1/q)*(x 1^2+x 2^2+x 3^2)+((1/q')^2-(1/q)^2)*x 0^2+
      ((1/q')*(1/(2*p'))-(1/q)*(1/(2*p)))*(2*x 0*x 4) := by
    rw [metric_coefficients,metric_coefficients]; ring
  rw [he]
  have hsn : 0 ≤ sizeSquared x := by dsimp [sizeSquared]; positivity
  refine hbound.trans (mul_le_mul_of_nonneg_right ?_ hsn)
  nlinarith [abs_nonneg (q'-q),abs_nonneg (p'-p)]

theorem relative_metric_variation (q p q' p' : ℝ)
    (hq : 1/4 ≤ q) (hp : 1/4 ≤ p) (hq4 : q ≤ 4) (hp4 : p ≤ 4)
    (hq' : 1/4 ≤ q') (hp' : 1/4 ≤ p') (x : State) :
    |metric q' p' x x-metric q p x x| ≤
      27648*(|q'-q|+|p'-p|)*metric q p x x := by
  calc
    _ ≤ 256*(|q'-q|+|p'-p|)*sizeSquared x := metric_variation q p q' p' hq hp hq' hp' x
    _ ≤ 256*(|q'-q|+|p'-p|)*(108*metric q p x x) :=
      mul_le_mul_of_nonneg_left (box_coercivity q p hq hq4 hp hp4 x) (by positivity)
    _ = _ := by ring

theorem weighted_metric_variation (q p q' p' v v' B : ℝ)
    (hq : 1/4 ≤ q) (hp : 1/4 ≤ p) (hq' : 1/4 ≤ q') (hp' : 1/4 ≤ p')
    (hB : |v'| ≤ B) (x : State) :
    |v'*metric q' p' x x-v*metric q p x x| ≤
      (256*B*(|q'-q|+|p'-p|)+32*|v'-v|)*sizeSquared x := by
  have hg := metric_nonnegative q p (by linarith) (by linarith) x
  have hgn := box_upper_bound q p hq hp x
  have hsn : 0 ≤ sizeSquared x := by dsimp [sizeSquared]; positivity
  calc
    _ = |v'*(metric q' p' x x-metric q p x x)+(v'-v)*metric q p x x| := by congr 1; ring
    _ ≤ |v'*(metric q' p' x x-metric q p x x)|+|(v'-v)*metric q p x x| := abs_add_le _ _
    _ = |v'| *|metric q' p' x x-metric q p x x|+|v'-v| *metric q p x x := by
      rw [abs_mul,abs_mul,abs_of_nonneg hg]
    _ ≤ B*(256*(|q'-q|+|p'-p|)*sizeSquared x)+|v'-v| *(32*sizeSquared x) :=
      add_le_add (mul_le_mul hB (metric_variation q p q' p' hq hp hq' hp' x)
        (abs_nonneg _) ((abs_nonneg _).trans hB))
        (mul_le_mul_of_nonneg_left hgn (abs_nonneg _))
    _ = _ := by ring

end EulerCoefficientBounds

-- Assemble after VariableEnergy.lean and CoefficientBounds.lean. This concerns
-- the variable-coefficient principal update, not the complete nonlinear map.
noncomputable section
namespace EulerVariableStability
open EulerPrimitiveEnergy EulerDiscreteEnergy EulerEnergyBounds
open EulerVariableEnergy EulerCoefficientBounds
open scoped BigOperators

theorem split_contribution_formula (q p v a ratio sign : ℝ) (hq : 0 < q) (hp : 0 < p)
    (d : Fin 3) (x : State) :
    metric q p x (splitAction q p v a ratio sign d x) =
      (ratio/2)*((a+sign*v)*metric q p x x+sign*(2*x 4*x ⟨d.val+1,by omega⟩)) := by
  simp only [splitAction,metric_smul_right,metric_add_right,
    principal_metric_identity q p v hq hp d x x]
  ring

theorem split_contribution_variation (q p q' p' v v' a ratio sign B : ℝ)
    (hq : 1/4 ≤ q) (hp : 1/4 ≤ p) (hq' : 1/4 ≤ q') (hp' : 1/4 ≤ p')
    (hr : 0 ≤ ratio) (hs : sign^2=1) (hB : |a+sign*v'| ≤ B) (d : Fin 3) (x : State) :
    |metric q' p' x (splitAction q' p' v' a ratio sign d x)-
      metric q p x (splitAction q p v a ratio sign d x)| ≤
      (ratio/2)*(256*B*(|q'-q|+|p'-p|)+32*|v'-v|)*sizeSquared x := by
  have hsign : |sign| = 1 := by nlinarith [sq_abs sign,abs_nonneg sign]
  have he : |(a+sign*v')-(a+sign*v)| = |v'-v| := by
    rw [show (a+sign*v')-(a+sign*v)=sign*(v'-v) by ring,abs_mul,hsign,one_mul]
  have heq : metric q' p' x (splitAction q' p' v' a ratio sign d x)-
      metric q p x (splitAction q p v a ratio sign d x) =
      (ratio/2)*((a+sign*v')*metric q' p' x x-(a+sign*v)*metric q p x x) := by
    rw [split_contribution_formula q' p' v' a ratio sign (by linarith) (by linarith),
      split_contribution_formula q p v a ratio sign (by linarith) (by linarith)]
    ring
  have hb := weighted_metric_variation q p q' p' (a+sign*v) (a+sign*v') B hq hp hq' hp' hB x
  rw [he] at hb
  rw [heq,abs_mul,abs_of_nonneg (by positivity : 0 ≤ ratio/2)]
  calc
    _ ≤ (ratio/2)*((256*B*(|q'-q|+|p'-p|)+32*|v'-v|)*sizeSquared x) :=
      mul_le_mul_of_nonneg_left hb (by positivity)
    _ = _ := by ring

theorem split_gradient_bound (q p q' p' v v' a ratio sign B h K D : ℝ)
    (hq : 1/4 ≤ q) (hp : 1/4 ≤ p) (hq' : 1/4 ≤ q') (hp' : 1/4 ≤ p')
    (hr : 0 ≤ ratio) (hs : sign^2=1) (hB : |a+sign*v'| ≤ B)
    (hh : 0 ≤ h) (hK : 0 ≤ K) (hD : 0 ≤ D)
    (hqp : |q'-q|+|p'-p| ≤ h*K) (hv : |v'-v| ≤ h*D) (d : Fin 3) (x : State) :
    |metric q' p' x (splitAction q' p' v' a ratio sign d x)-
      metric q p x (splitAction q p v a ratio sign d x)| ≤
      ratio*h*(256*B*K+32*D)*sizeSquared x := by
  have hBn : 0 ≤ B := (abs_nonneg _).trans hB
  have hsn : 0 ≤ sizeSquared x := by dsimp [sizeSquared]; positivity
  calc
    _ ≤ (ratio/2)*(256*B*(|q'-q|+|p'-p|)+32*|v'-v|)*sizeSquared x :=
      split_contribution_variation q p q' p' v v' a ratio sign B hq hp hq' hp' hr hs hB d x
    _ ≤ (ratio/2)*(256*B*(h*K)+32*(h*D))*sizeSquared x :=
      mul_le_mul_of_nonneg_right (mul_le_mul_of_nonneg_left
        (add_le_add (mul_le_mul_of_nonneg_left hqp (by positivity))
          (mul_le_mul_of_nonneg_left hv (by norm_num))) (by positivity)) hsn
    _ ≤ ratio*h*(256*B*K+32*D)*sizeSquared x := by
      have hn : 0 ≤ ratio*h*(256*B*K+32*D)*sizeSquared x := by positivity
      nlinarith

theorem variable_principal_energy_growth {I : Type*} [Fintype I]
    (q p : I → ℝ) (ratio : ℝ) (v : I → Fin 3 → ℝ) (a : Fin 3 → ℝ)
    (hq : ∀ i, 1/4 ≤ q i) (hp : ∀ i, 1/4 ≤ p i)
    (hq4 : ∀ i, q i ≤ 4) (hp4 : ∀ i, p i ≤ 4)
    (hr : 0 ≤ ratio) (ha : ∀ i d, |v i d|+Real.sqrt (2*p i*q i) ≤ a d)
    (hcf : ratio*(a 0+a 1+a 2) ≤ 1)
    (shift : Fin 7 → Equiv.Perm I) (hcenter : shift 0 = Equiv.refl I)
    (B h K D : ℝ) (hBn : 0 ≤ B) (hh : 0 ≤ h) (hK : 0 ≤ K) (hD : 0 ≤ D)
    (hB : ∀ i d, |a d|+|v i d| ≤ B)
    (hqp : ∀ i j, |q ((shift j).symm i)-q i|+|p ((shift j).symm i)-p i| ≤ h*K)
    (hv : ∀ i j d, |v ((shift j).symm i) d-v i d| ≤ h*D) (u : I → State) :
    (∑ i, metric (q i) (p i) (variableUpdate q p ratio v a shift u i)
      (variableUpdate q p ratio v a shift u i)) ≤
      (1+756*ratio*h*(256*B*K+32*D))*(∑ i, metric (q i) (p i) (u i) (u i)) := by
  have hqpos (i : I) : 0 < q i := by linarith [hq i]
  have hppos (i : I) : 0 < p i := by linarith [hp i]
  have hsn (i : I) : 0 ≤ sizeSquared (u i) := by dsimp [sizeSquared]; positivity
  have hsplit (i : I) (j : Fin 7) (d : Fin 3) (sign : ℝ) (hs : sign^2=1) :
      |metric (q ((shift j).symm i)) (p ((shift j).symm i)) (u i)
        (splitAction (q ((shift j).symm i)) (p ((shift j).symm i))
          (v ((shift j).symm i) d) (a d) ratio sign d (u i))-
      metric (q i) (p i) (u i) (splitAction (q i) (p i) (v i d) (a d) ratio sign d (u i))| ≤
        ratio*h*(256*B*K+32*D)*sizeSquared (u i) := by
    apply split_gradient_bound _ _ _ _ _ _ _ _ _ _ _ _ _
      (hq i) (hp i) (hq _) (hp _) hr hs _ hh hK hD (hqp i j) (hv i j d) d (u i)
    have hsign : |sign| = 1 := by nlinarith [sq_abs sign,abs_nonneg sign]
    calc
      _ ≤ |a d|+|sign*v ((shift j).symm i) d| := abs_add_le _ _
      _ = |a d|+|v ((shift j).symm i) d| := by rw [abs_mul,hsign,one_mul]
      _ ≤ B := hB _ d
  have hlocal (i : I) (j : Fin 7) :
      |localContribution q p ratio v a ((shift j).symm i) j (u i)-
        localContribution q p ratio v a i j (u i)| ≤
      ratio*h*(256*B*K+32*D)*sizeSquared (u i) := by
    fin_cases j
    · change |localContribution q p ratio v a ((shift 0).symm i) 0 (u i)-
        localContribution q p ratio v a i 0 (u i)| ≤ _
      rw [hcenter]
      change |localContribution q p ratio v a i 0 (u i)-localContribution q p ratio v a i 0 (u i)| ≤ _
      rw [sub_self,abs_zero]
      exact mul_nonneg (by positivity) (hsn i)
    · exact hsplit i 1 0 (-1) (by norm_num)
    · exact hsplit i 2 0 1 (by norm_num)
    · exact hsplit i 3 1 (-1) (by norm_num)
    · exact hsplit i 4 1 1 (by norm_num)
    · exact hsplit i 5 2 (-1) (by norm_num)
    · exact hsplit i 6 2 1 (by norm_num)
  have hsum (i : I) :
      (∑ j, (localContribution q p ratio v a ((shift j).symm i) j (u i)-
        localContribution q p ratio v a i j (u i))) ≤
      7*(ratio*h*(256*B*K+32*D)*sizeSquared (u i)) := by
    have hb := Finset.sum_le_sum (fun (j : Fin 7) (_ : j ∈ Finset.univ) =>
      (le_abs_self _).trans (hlocal i j))
    simpa only [Finset.sum_const,Finset.card_univ,Fintype.card_fin,nsmul_eq_mul,Nat.cast_ofNat] using hb
  have hdef : variationDefect q p ratio v a shift u ≤
      (756*ratio*h*(256*B*K+32*D))*(∑ i, metric (q i) (p i) (u i) (u i)) := by
    calc
      _ ≤ ∑ i, 7*(ratio*h*(256*B*K+32*D)*sizeSquared (u i)) :=
        Finset.sum_le_sum (fun i _ => hsum i)
      _ ≤ ∑ i, 7*(ratio*h*(256*B*K+32*D)*(108*metric (q i) (p i) (u i) (u i))) :=
        Finset.sum_le_sum (fun i _ => mul_le_mul_of_nonneg_left
          (mul_le_mul_of_nonneg_left (box_coercivity (q i) (p i) (hq i) (hq4 i) (hp i) (hp4 i) (u i))
            (by positivity)) (by norm_num))
      _ = _ := by simp only [← Finset.mul_sum]; ring
  have henergy := variable_principal_energy_defect q p ratio v a hqpos hppos hr ha hcf shift u
  calc
    _ ≤ (∑ i, metric (q i) (p i) (u i) (u i))+variationDefect q p ratio v a shift u := henergy
    _ ≤ (∑ i, metric (q i) (p i) (u i) (u i))+
        (756*ratio*h*(256*B*K+32*D))*(∑ i, metric (q i) (p i) (u i) (u i)) :=
      add_le_add_left hdef _
    _ = _ := by ring

def witnessQ : Fin 2 → ℝ := ![1,2]
def entropyError (c : ℝ) : State := fun k => if k=0 then c else 0
def witnessError (i : Fin 2) : State := entropyError (if i=0 then 1 else 4)
def witnessShift (j : Fin 7) : Equiv.Perm (Fin 2) :=
  if j=0 then Equiv.refl _ else Equiv.swap 0 1

theorem principal_entropy (q p c : ℝ) (d : Fin 3) :
    principal q p 0 d (entropyError c) = 0 := by
  funext j
  fin_cases d <;> fin_cases j <;> norm_num [principal,entropyError,Fin.ext_iff]

theorem split_entropy (q p a ratio sign c : ℝ) (d : Fin 3) :
    splitAction q p 0 a ratio sign d (entropyError c) = (ratio*a/2) • entropyError c := by
  simp only [splitAction,principal_entropy,smul_zero,add_zero,smul_smul]
  congr 1
  ring

theorem metric_entropy (q p c : ℝ) :
    metric q p (entropyError c) (entropyError c) = (c/q)^2 := by
  norm_num [metric,entropyError,show (1 : Fin 5) ≠ 0 by decide,
    show (2 : Fin 5) ≠ 0 by decide,show (3 : Fin 5) ≠ 0 by decide,
    show (4 : Fin 5) ≠ 0 by decide]
  ring

theorem witness_update (i : Fin 2) :
    variableUpdate witnessQ (fun _ => 1) (1/12) (fun _ _ => 0) (fun _ => 2)
      witnessShift witnessError i = entropyError (5/2) := by
  funext j
  fin_cases i <;> fin_cases j <;>
    norm_num [variableUpdate,witnessError,witnessShift,actions,split_entropy,
      entropyError,Fin.sum_univ_succ,Equiv.swap_apply_def]

-- With positive coefficients and CFL=1/2, the varying local metric need not
-- contract. This is an error-field witness, not an alternative flow family.
theorem varying_metric_energy_increase :
    (∀ i : Fin 2, 0 < witnessQ i ∧ Real.sqrt (2*witnessQ i) ≤ 2) ∧
    (1/12 : ℝ)*(2+2+2) ≤ 1 ∧
    (∑ i, metric (witnessQ i) 1 (witnessError i) (witnessError i)) = 5 ∧
    (∑ i, metric (witnessQ i) 1
      (variableUpdate witnessQ (fun _ => 1) (1/12) (fun _ _ => 0) (fun _ => 2)
        witnessShift witnessError i)
      (variableUpdate witnessQ (fun _ => 1) (1/12) (fun _ _ => 0) (fun _ => 2)
        witnessShift witnessError i)) = 125/16 ∧ (5 : ℝ) < 125/16 := by
  constructor
  · intro i
    fin_cases i <;> norm_num [witnessQ,Real.sqrt_le_iff]
  · simp only [witness_update]
    norm_num [Fin.sum_univ_succ,witnessQ,witnessError,metric_entropy]

end EulerVariableStability


-- Actual derivatives of the gamma=2 convex mathematical entropy. These local
-- identities do not establish entropy dissipation of a finite-volume step.
noncomputable section
namespace EulerEntropy
open EulerConservativePrimitive
open scoped Topology
abbrev State := Fin 5 → ℝ

def dot (x y : State) : ℝ := x 0*y 0+x 1*y 1+x 2*y 2+x 3*y 3+x 4*y 4

def entropy (u : State) : ℝ :=
  -u 0*(Real.log (EulerAdmissible.pressure u)-2*Real.log (u 0))

def pressureD (u k : State) : ℝ :=
  k 4-(u 1*k 1+u 2*k 2+u 3*k 3)/u 0+
    (u 1^2+u 2^2+u 3^2)*k 0/(2*(u 0)^2)

def gradient (u : State) : State :=
  let p := EulerAdmissible.pressure u
  ![2-(Real.log p-2*Real.log (u 0))-(u 1^2+u 2^2+u 3^2)/(2*u 0*p),
    u 1/p,u 2/p,u 3/p,-u 0/p]

theorem entropy_log_ratio (u : State) (hu : EulerAdmissible.Admissible u) :
    entropy u = -u 0*Real.log (EulerAdmissible.pressure u/(u 0)^2) := by
  rw [Real.log_div (ne_of_gt hu.2) (pow_ne_zero 2 (ne_of_gt hu.1)),Real.log_pow]
  rfl

theorem pressure_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : u t 0 ≠ 0) :
    HasDerivAt (fun s => EulerAdmissible.pressure (u s)) (pressureD (u t) k) t := by
  have hnum := ((((hasDerivAt_pi.mp hu) 1).pow 2).add
    (((hasDerivAt_pi.mp hu) 2).pow 2)).add (((hasDerivAt_pi.mp hu) 3).pow 2)
  have hh := ((hasDerivAt_pi.mp hu) 4).sub
    (hnum.div (((hasDerivAt_pi.mp hu) 0).const_mul 2) (mul_ne_zero (by norm_num) hr))
  convert hh using 1
  dsimp [pressureD]
  field_simp
  ring

theorem entropy_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : u t 0 ≠ 0) (hp : EulerAdmissible.pressure (u t) ≠ 0) :
    HasDerivAt (fun s => entropy (u s)) (dot (gradient (u t)) k) t := by
  have hh := (((hasDerivAt_pi.mp hu) 0).mul
    (((pressure_derivative hu hr).log hp).sub ((((hasDerivAt_pi.mp hu) 0).log hr).const_mul 2))).neg
  convert hh using 1
  · funext s
    dsimp [entropy]
    ring
  · dsimp [dot,gradient,pressureD]
    field_simp
    ring

def logState (w : State) : ℝ := Real.log (w 4)+2*Real.log (w 0)
def primitiveEntropy (w : State) : ℝ := -logState w/w 0
def entropyVariables (w : State) : State :=
  ![2-logState w-kinetic w/(w 0*w 4),
    w 1/(w 0*w 4),w 2/(w 0*w 4),w 3/(w 0*w 4),-1/(w 0*w 4)]

def variablesD (w h : State) : State :=
  let R := w 0*w 4
  let dR := h 0*w 4+w 0*h 4
  ![-(h 4/w 4+2*h 0/w 0)-(kineticD w h*R-kinetic w*dR)/R^2,
    (h 1*R-w 1*dR)/R^2,(h 2*R-w 2*dR)/R^2,(h 3*R-w 3*dR)/R^2,dR/R^2]

theorem pressure_conserved (w : State) : EulerAdmissible.pressure (conserved w) = w 4 := by
  rw [conserved_as_primitive,EulerAdmissible.pressure_primitive]

theorem entropy_conserved (w : State) : entropy (conserved w) = primitiveEntropy w := by
  simp only [entropy,pressure_conserved]
  dsimp [conserved,primitiveEntropy,logState]
  rw [one_div,Real.log_inv]
  ring

theorem gradient_conserved (w : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0) :
    gradient (conserved w) = entropyVariables w := by
  simp only [gradient,pressure_conserved]
  funext i
  fin_cases i
  all_goals dsimp [conserved,entropyVariables,kinetic,logState]
  all_goals try simp only [one_div,Real.log_inv]
  all_goals field_simp
  all_goals ring

theorem variables_derivative {w : ℝ → State} {h : State} {t : ℝ}
    (hw : HasDerivAt w h t) (hq : w t 0 ≠ 0) (hp : w t 4 ≠ 0) :
    HasDerivAt (fun s => entropyVariables (w s)) (variablesD (w t) h) t := by
  have hR := ((hasDerivAt_pi.mp hw) 0).mul ((hasDerivAt_pi.mp hw) 4)
  have hRn : w t 0*w t 4 ≠ 0 := mul_ne_zero hq hp
  have hlog := (((hasDerivAt_pi.mp hw) 4).log hp).add
    ((((hasDerivAt_pi.mp hw) 0).log hq).const_mul 2)
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · have hh := ((hasDerivAt_const t (2 : ℝ)).sub hlog).sub ((kinetic_derivative hw).div hR hRn)
    convert hh using 1
    dsimp [variablesD]
    ring
  · exact ((hasDerivAt_pi.mp hw) 1).div hR hRn
  · exact ((hasDerivAt_pi.mp hw) 2).div hR hRn
  · exact ((hasDerivAt_pi.mp hw) 3).div hR hRn
  · have hh := (hR.inv hRn).neg
    convert hh using 1
    · funext s
      dsimp [entropyVariables]
      ring
    · dsimp [variablesD]
      ring

def hessianForm (w h : State) : ℝ :=
  h 4^2/(2*(w 4)^2*w 0)+(h 1^2+h 2^2+h 3^2)/(w 4*(w 0)^2)+
    (2/w 0)*(h 0/w 0+h 4/(2*w 4))^2

theorem hessian_pullback (w h : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0) :
    dot (variablesD w h) (jacobian w h) = hessianForm w h := by
  dsimp [dot,variablesD,jacobian,kinetic,kineticD,hessianForm]
  field_simp
  ring

theorem hessian_nonnegative (w h : State) (hq : 0 < w 0) (hp : 0 < w 4) :
    0 ≤ hessianForm w h := by
  dsimp [hessianForm]
  positivity

theorem metric_le_entropy_factor (w h : State) (hq : 0 < w 0) (hp : 0 < w 4) :
    EulerPrimitiveEnergy.metric (w 0) (w 4) h h ≤
      (w 0*w 4+w 0/2+1)*hessianForm w h := by
  let A := h 4^2/(2*(w 4)^2*w 0)+(h 1^2+h 2^2+h 3^2)/(w 4*(w 0)^2)
  let B := (2/w 0)*(h 0/w 0+h 4/(2*w 4))^2
  have hA : 0 ≤ A := by dsimp [A]; positivity
  have hB : 0 ≤ B := by dsimp [B]; positivity
  have hq0 := ne_of_gt hq
  have hp0 := ne_of_gt hp
  calc
    _ = (w 0*w 4)*A+(w 0/2)*B := by
      dsimp [A,B,EulerPrimitiveEnergy.metric]
      field_simp
    _ ≤ (w 0*w 4+w 0/2+1)*A+(w 0*w 4+w 0/2+1)*B :=
      add_le_add (mul_le_mul_of_nonneg_right (by nlinarith) hA)
        (mul_le_mul_of_nonneg_right (by nlinarith) hB)
    _ = _ := by dsimp [A,B,hessianForm]; ring

theorem hessian_positive (w h : State) (hq : 0 < w 0) (hp : 0 < w 4) (hh : h ≠ 0) :
    0 < hessianForm w h := by
  have hg := EulerPrimitiveEnergy.metric_positive (w 0) (w 4) hq hp h hh
  have hb := metric_le_entropy_factor w h hq hp
  have hcoef : 0 ≤ w 0*w 4+w 0/2+1 := by positivity
  by_contra hnot
  have hn := mul_nonpos_of_nonneg_of_nonpos hcoef (le_of_not_gt hnot)
  linarith

theorem gradient_conserved_derivative {w : ℝ → State} {h : State} {t : ℝ}
    (hw : HasDerivAt w h t) (hq : 0 < w t 0) (hp : 0 < w t 4) :
    HasDerivAt (fun s => gradient (conserved (w s))) (variablesD (w t) h) t := by
  have hqp : ∀ᶠ s in 𝓝 t, 0 < w s 0 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hw) 0).continuousAt hq
  have hpp : ∀ᶠ s in 𝓝 t, 0 < w s 4 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hw) 4).continuousAt hp
  have heq : (fun s => gradient (conserved (w s))) =ᶠ[𝓝 t]
      (fun s => entropyVariables (w s)) := (hqp.and hpp).mono
    (fun s hs => gradient_conserved (w s) (ne_of_gt hs.1) (ne_of_gt hs.2))
  exact (variables_derivative hw (ne_of_gt hq) (ne_of_gt hp)).congr_of_eventuallyEq heq

theorem dot_derivative {f : ℝ → State} {h : State} {t : ℝ}
    (hf : HasDerivAt f h t) (k : State) :
    HasDerivAt (fun s => dot (f s) k) (dot h k) t := by
  exact ((((((hasDerivAt_pi.mp hf) 0).mul_const (k 0)).add
    (((hasDerivAt_pi.mp hf) 1).mul_const (k 1))).add
    (((hasDerivAt_pi.mp hf) 2).mul_const (k 2))).add
    (((hasDerivAt_pi.mp hf) 3).mul_const (k 3))).add
    (((hasDerivAt_pi.mp hf) 4).mul_const (k 4))

-- This differentiates the actual conservative entropy gradient and evaluates
-- it against the conservative tangent. It is not a definition of a Hessian.
theorem conservative_hessian_derivative {w : ℝ → State} {h : State} {t : ℝ}
    (hw : HasDerivAt w h t) (hq : 0 < w t 0) (hp : 0 < w t 4) :
    HasDerivAt (fun s => dot (gradient (conserved (w s))) (jacobian (w t) h))
      (hessianForm (w t) h) t := by
  have hh := dot_derivative (gradient_conserved_derivative hw hq hp) (jacobian (w t) h)
  rwa [hessian_pullback (w t) h (ne_of_gt hq) (ne_of_gt hp)] at hh

def toPrimitive (u : State) : State :=
  ![1/u 0,u 1/u 0,u 2/u 0,u 3/u 0,EulerAdmissible.pressure u]

def primitiveD (u k : State) : State :=
  ![-k 0/(u 0)^2,(k 1*u 0-u 1*k 0)/(u 0)^2,
    (k 2*u 0-u 2*k 0)/(u 0)^2,(k 3*u 0-u 3*k 0)/(u 0)^2,pressureD u k]

theorem primitive_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : u t 0 ≠ 0) :
    HasDerivAt (fun s => toPrimitive (u s)) (primitiveD (u t) k) t := by
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · simpa only [toPrimitive,primitiveD,one_div,Pi.inv_apply] using
      ((hasDerivAt_pi.mp hu) 0).inv hr
  · exact ((hasDerivAt_pi.mp hu) 1).div ((hasDerivAt_pi.mp hu) 0) hr
  · exact ((hasDerivAt_pi.mp hu) 2).div ((hasDerivAt_pi.mp hu) 0) hr
  · exact ((hasDerivAt_pi.mp hu) 3).div ((hasDerivAt_pi.mp hu) 0) hr
  · exact pressure_derivative hu hr

theorem conserved_toPrimitive (u : State) (hr : u 0 ≠ 0) : conserved (toPrimitive u) = u := by
  funext i
  fin_cases i <;> dsimp [conserved,toPrimitive,kinetic,EulerAdmissible.pressure]
  all_goals field_simp
  all_goals ring

theorem jacobian_primitiveD (u k : State) (hr : u 0 ≠ 0) :
    jacobian (toPrimitive u) (primitiveD u k) = k := by
  funext i
  fin_cases i <;> dsimp [jacobian,toPrimitive,primitiveD,pressureD,kinetic,kineticD]
  all_goals field_simp
  all_goals ring

theorem gradient_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : 0 < u t 0) (hp : 0 < EulerAdmissible.pressure (u t)) :
    HasDerivAt (fun s => gradient (u s))
      (variablesD (toPrimitive (u t)) (primitiveD (u t) k)) t := by
  have hq : 0 < toPrimitive (u t) 0 := by dsimp [toPrimitive]; positivity
  have hh := gradient_conserved_derivative (primitive_derivative hu (ne_of_gt hr)) hq hp
  have hpos : ∀ᶠ s in 𝓝 t, 0 < u s 0 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hu) 0).continuousAt hr
  have heq : (fun s => gradient (u s)) =ᶠ[𝓝 t]
      (fun s => gradient (conserved (toPrimitive (u s)))) := hpos.mono
    (fun s hs => congrArg gradient (conserved_toPrimitive (u s) (ne_of_gt hs)).symm)
  exact hh.congr_of_eventuallyEq heq

theorem entropy_second_directional {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : 0 < u t 0) (hp : 0 < EulerAdmissible.pressure (u t)) :
    HasDerivAt (fun s => dot (gradient (u s)) k)
      (hessianForm (toPrimitive (u t)) (primitiveD (u t) k)) t := by
  have hh := dot_derivative (gradient_derivative hu hr hp) k
  have he : dot (variablesD (toPrimitive (u t)) (primitiveD (u t) k)) k =
      hessianForm (toPrimitive (u t)) (primitiveD (u t) k) := by
    calc
      _ = dot (variablesD (toPrimitive (u t)) (primitiveD (u t) k))
          (jacobian (toPrimitive (u t)) (primitiveD (u t) k)) := by
        rw [jacobian_primitiveD (u t) k (ne_of_gt hr)]
      _ = _ := hessian_pullback _ _ (by dsimp [toPrimitive]; positivity) (ne_of_gt hp)
  rwa [he] at hh

def entropyDifferential (w h : State) : ℝ :=
  (logState w-2)*h 0/(w 0)^2-h 4/(w 0*w 4)

theorem entropy_jacobian_pairing (w h : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0) :
    dot (entropyVariables w) (jacobian w h) = entropyDifferential w h := by
  dsimp [dot,entropyVariables,jacobian,entropyDifferential,kinetic,kineticD]
  field_simp
  ring

theorem primitive_entropy_derivative {w : ℝ → State} {h : State} {t : ℝ}
    (hw : HasDerivAt w h t) (hq : w t 0 ≠ 0) (hp : w t 4 ≠ 0) :
    HasDerivAt (fun s => primitiveEntropy (w s)) (entropyDifferential (w t) h) t := by
  have hr : conserved (w t) 0 ≠ 0 := by dsimp [conserved]; positivity
  have hpr : EulerAdmissible.pressure (conserved (w t)) ≠ 0 := by rwa [pressure_conserved]
  have hh := entropy_derivative (conserved_derivative hw hq) hr hpr
  simpa only [entropy_conserved,gradient_conserved (w t) hq hp,
    entropy_jacobian_pairing (w t) h hq hp] using hh

theorem principal_entropy_compatibility (w h : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0)
    (d : Fin 3) :
    entropyDifferential w
      (EulerPrimitiveEnergy.principal (w 0) (w 4) (w ⟨d.val+1,by omega⟩) d h) =
    w ⟨d.val+1,by omega⟩*entropyDifferential w h+
      primitiveEntropy w*h ⟨d.val+1,by omega⟩ := by
  fin_cases d <;> dsimp [entropyDifferential,EulerPrimitiveEnergy.principal,primitiveEntropy] <;>
    field_simp <;> ring

theorem primitive_entropy_potential (w : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0)
    (d : Fin 3) : dot (entropyVariables w) (primitiveFlux w d)-
      primitiveEntropy w*w ⟨d.val+1,by omega⟩ = w ⟨d.val+1,by omega⟩/w 0 := by
  fin_cases d <;> dsimp [dot,entropyVariables,primitiveFlux,primitiveEntropy,kinetic] <;>
    field_simp <;> ring

end EulerEntropy


-- Assemble after Entropy.lean. Convexity is derived from actual directional
-- derivatives of the conserved-variable entropy, not assumed as a solver property.
noncomputable section
namespace EulerEntropyConvexity
open EulerEntropy
open scoped BigOperators

def stateDomain : Set State := {u | EulerAdmissible.Admissible u}

theorem domain_convex : Convex ℝ stateDomain := by
  intro x hx y hy a b ha hb hab
  have ha1 : a ≤ 1 := by linarith
  have h := EulerAdmissible.convex_admissible x y hx hy a ha ha1
  have hbeq : 1-a=b := by linarith
  simpa only [hbeq] using h

def segment (x y : State) (t : ℝ) : State := x+t • (y-x)

theorem segment_mix (x y : State) (t : ℝ) : segment x y t = (1-t) • x+t • y := by
  funext i
  simp only [segment,Pi.add_apply,Pi.smul_apply,Pi.sub_apply,smul_eq_mul]
  ring

theorem segment_admissible (x y : State) (hx : x ∈ stateDomain) (hy : y ∈ stateDomain)
    (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : EulerAdmissible.Admissible (segment x y t) := by
  rw [segment_mix]
  exact domain_convex hx hy (sub_nonneg.mpr ht.2) ht.1 (by ring)

theorem segment_derivative (x y : State) (t : ℝ) : HasDerivAt (segment x y) (y-x) t := by
  have hh := (hasDerivAt_const t x).add ((hasDerivAt_id t).smul_const (y-x))
  simpa only [zero_add,one_smul] using hh

theorem entropy_convex_on_segment (x y : State) (hx : x ∈ stateDomain) (hy : y ∈ stateDomain) :
    ConvexOn ℝ (Set.Icc (0 : ℝ) 1) (fun t => entropy (segment x y t)) := by
  let df := fun t => dot (gradient (segment x y t)) (y-x)
  let ddf := fun t => hessianForm (toPrimitive (segment x y t)) (primitiveD (segment x y t) (y-x))
  have hder (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
      HasDerivAt (fun s => entropy (segment x y s)) (df t) t := by
    obtain ⟨hr,hp⟩ := segment_admissible x y hx hy t ht
    exact entropy_derivative (segment_derivative x y t) (ne_of_gt hr) (ne_of_gt hp)
  have hder2 (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt df (ddf t) t := by
    obtain ⟨hr,hp⟩ := segment_admissible x y hx hy t ht
    exact entropy_second_directional (segment_derivative x y t) hr hp
  apply convexOn_of_hasDerivWithinAt2_nonneg (convex_Icc (0 : ℝ) 1)
    (fun t ht => (hder t ht).continuousAt.continuousWithinAt)
    (fun t ht => (hder t (interior_subset ht)).hasDerivWithinAt)
    (fun t ht => (hder2 t (interior_subset ht)).hasDerivWithinAt)
  intro t ht
  obtain ⟨hr,hp⟩ := segment_admissible x y hx hy t (interior_subset ht)
  exact hessian_nonnegative _ _ (by dsimp [toPrimitive]; positivity) hp

theorem entropy_convex : ConvexOn ℝ stateDomain entropy := by
  refine ⟨domain_convex,?_⟩
  intro x hx y hy a b ha hb hab
  have hc := entropy_convex_on_segment x y hx hy
  have hi0 : (0 : ℝ) ∈ Set.Icc (0 : ℝ) 1 := by norm_num
  have hi1 : (1 : ℝ) ∈ Set.Icc (0 : ℝ) 1 := by norm_num
  have hm := hc.2 hi0 hi1 ha hb hab
  have h0 : segment x y 0=x := by simp [segment]
  have h1 : segment x y 1=y := by simp [segment]
  have he : segment x y (a • (0 : ℝ)+b • (1 : ℝ)) = a • x+b • y := by
    rw [segment_mix]
    have hb1 : 1-b=a := by linarith
    simp only [smul_eq_mul,mul_zero,mul_one,zero_add,hb1]
  simpa only [he,h0,h1] using hm

theorem entropy_convex_mixture {I : Type*} [Fintype I] (a : I → ℝ) (u : I → State)
    (ha : ∀ i, 0 ≤ a i) (hs : ∑ i, a i=1) (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    entropy (∑ i, a i • u i) ≤ ∑ i, a i*entropy (u i) := by
  simpa only [smul_eq_mul] using entropy_convex.map_sum_le (fun i _ => ha i) hs (fun i _ => hu i)

-- A finite averaging map with unit row and column sums cannot restore convex
-- entropy lost by evolution. Continuous output integration is a separate bridge.
theorem averaging_entropy_bound {I : Type*} [Fintype I] (weights : I → I → ℝ) (u : I → State)
    (hw : ∀ i j, 0 ≤ weights i j) (hrow : ∀ i, ∑ j, weights i j=1)
    (hcol : ∀ j, ∑ i, weights i j=1) (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    (∑ i, entropy (∑ j, weights i j • u j)) ≤ ∑ i, entropy (u i) := by
  calc
    _ ≤ ∑ i, ∑ j, weights i j*entropy (u j) :=
      Finset.sum_le_sum (fun i _ => entropy_convex_mixture (weights i) u (hw i) (hrow i) hu)
    _ = _ := by
      rw [Finset.sum_comm]
      simp only [← Finset.sum_mul,hcol,one_mul]

end EulerEntropyConvexity

-- Assemble after Entropy.lean. Local consequences of differentiable Euler
-- balance; existence and periodic space-time integration remain separate work.
noncomputable section
namespace EulerEntropyDynamics
open EulerEntropy EulerConservativePrimitive
open scoped Topology
abbrev State := Fin 5 → ℝ

def entropyFlux (u : State) (d : Fin 3) : ℝ :=
  entropy u*(u ⟨d.val+1,by omega⟩/u 0)

theorem entropy_flux_conserved (w : State) (hq : w 0 ≠ 0) (d : Fin 3) :
    entropyFlux (conserved w) d = primitiveEntropy w*w ⟨d.val+1,by omega⟩ := by
  rw [entropyFlux,entropy_conserved]
  congr 1
  fin_cases d <;> dsimp [conserved] <;> field_simp

theorem canonical_entropy_potential (u : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    dot (gradient u) (EulerAdmissible.eulerFlux u d)-entropyFlux u d = u ⟨d.val+1,by omega⟩ := by
  let w := toPrimitive u
  have hq : 0 < w 0 := by dsimp [w,toPrimitive]; exact one_div_pos.mpr hu.1
  have hp : w 4 ≠ 0 := ne_of_gt hu.2
  have hh : dot (gradient (conserved w)) (EulerAdmissible.eulerFlux (conserved w) d)-
      entropyFlux (conserved w) d = (conserved w) ⟨d.val+1,by omega⟩ := by
    rw [gradient_conserved w (ne_of_gt hq) hp,canonical_flux w hq d,
      entropy_flux_conserved w (ne_of_gt hq) d]
    have hr : (conserved w) ⟨d.val+1,by omega⟩ = w ⟨d.val+1,by omega⟩/w 0 := by
      fin_cases d <;> rfl
    rw [hr]
    exact primitive_entropy_potential w (ne_of_gt hq) hp d
  simpa only [w,conserved_toPrimitive u (ne_of_gt hu.1)] using hh

theorem entropy_flux_derivative {w : ℝ → State} {h : State} {t : ℝ}
    (hw : HasDerivAt w h t) (hq : 0 < w t 0) (hp : w t 4 ≠ 0) (d : Fin 3) :
    HasDerivAt (fun s => entropyFlux (conserved (w s)) d)
      (entropyDifferential (w t) (EulerPrimitiveEnergy.principal (w t 0) (w t 4)
        (w t ⟨d.val+1,by omega⟩) d h)) t := by
  have hh := (primitive_entropy_derivative hw (ne_of_gt hq) hp).mul
    ((hasDerivAt_pi.mp hw) ⟨d.val+1,by omega⟩)
  have hpos : ∀ᶠ s in 𝓝 t, 0 < w s 0 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hw) 0).continuousAt hq
  have heq : (fun s => entropyFlux (conserved (w s)) d) =ᶠ[𝓝 t]
      (fun s => primitiveEntropy (w s)*w s ⟨d.val+1,by omega⟩) := hpos.mono
    (fun s hs => entropy_flux_conserved (w s) (ne_of_gt hs) d)
  have hder := hh.congr_of_eventuallyEq heq
  convert hder using 1
  rw [principal_entropy_compatibility (w t) h (ne_of_gt hq) hp d]
  ring

theorem entropyDifferential_add (w x y : State) :
    entropyDifferential w (x+y) = entropyDifferential w x+entropyDifferential w y := by
  dsimp [entropyDifferential]
  ring

theorem entropyDifferential_zero (w : State) : entropyDifferential w 0=0 := by
  simp [entropyDifferential]

theorem smooth_entropy_balance (w ht : State) (hx : Fin 3 → State)
    (timeCurve : ℝ → State) (spaceCurve : Fin 3 → ℝ → State)
    (hq : 0 < w 0) (hp : 0 < w 4) (hvt : timeCurve 0=w) (hvx : ∀ d, spaceCurve d 0=w)
    (hdt : HasDerivAt timeCurve ht 0) (hdx : ∀ d, HasDerivAt (spaceCurve d) (hx d) 0)
    (heuler : deriv (fun t => conserved (timeCurve t)) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 0 t)) 0) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 1 t)) 1) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 2 t)) 2) 0=0) :
    deriv (fun t => entropy (conserved (timeCurve t))) 0+
      deriv (fun t => entropyFlux (conserved (spaceCurve 0 t)) 0) 0+
      deriv (fun t => entropyFlux (conserved (spaceCurve 1 t)) 1) 0+
      deriv (fun t => entropyFlux (conserved (spaceCurve 2 t)) 2) 0=0 := by
  have hprim := (euler_residual_equivalence w ht hx timeCurve spaceCurve hq hvt hvx hdt hdx).mp heuler
  have htime := (primitive_entropy_derivative hdt (by rw [hvt]; exact ne_of_gt hq)
    (by rw [hvt]; exact ne_of_gt hp)).deriv
  have hspace (d : Fin 3) := (entropy_flux_derivative (hdx d)
    (by rw [hvx]; exact hq) (by rw [hvx]; exact ne_of_gt hp) d).deriv
  simp only [entropy_conserved]
  rw [htime,hspace 0,hspace 1,hspace 2]
  simp only [hvt,hvx]
  rw [← entropyDifferential_add,← entropyDifferential_add,← entropyDifferential_add]
  change entropyDifferential w (ht+
    EulerPrimitiveEnergy.principal (w 0) (w 4) (w 1) 0 (hx 0)+
    EulerPrimitiveEnergy.principal (w 0) (w 4) (w 2) 1 (hx 1)+
    EulerPrimitiveEnergy.principal (w 0) (w 4) (w 3) 2 (hx 2))=0
  rw [hprim,entropyDifferential_zero]

end EulerEntropyDynamics

-- Assemble after EntropyConvexity.lean. The finite-step remainder is derived
-- from the actual entropy Hessian along the segment between the two states.
noncomputable section
namespace EulerEntropyTaylor
open EulerEntropy EulerEntropyConvexity EulerEnergyBounds

theorem scalar_first_derivative_lower (f df : ℝ → ℝ) (C : ℝ)
    (hf : ∀ t ∈ Set.Icc (0 : ℝ) 1, HasDerivAt f (df t) t)
    (hdf : ∀ t ∈ Set.Icc (0 : ℝ) 1, C ≤ df t) : C ≤ f 1-f 0 := by
  let g := fun t => f t-C*t
  have hg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt g (df t-C) t := by
    convert (hf t ht).sub ((hasDerivAt_id t).const_mul C) using 1
    ring
  have hm := monotoneOn_of_hasDerivWithinAt_nonneg (convex_Icc (0 : ℝ) 1)
    (fun t ht => (hg t ht).continuousAt.continuousWithinAt)
    (fun t ht => (hg t (interior_subset ht)).hasDerivWithinAt)
    (fun t ht => sub_nonneg.mpr (hdf t (interior_subset ht)))
  have hh := hm (by norm_num : (0 : ℝ) ∈ Set.Icc (0 : ℝ) 1)
    (by norm_num : (1 : ℝ) ∈ Set.Icc (0 : ℝ) 1) (by norm_num : (0 : ℝ) ≤ 1)
  simp only [g,mul_zero,mul_one,sub_zero] at hh
  linarith

theorem scalar_first_derivative_upper (f df : ℝ → ℝ) (C : ℝ)
    (hf : ∀ t ∈ Set.Icc (0 : ℝ) 1, HasDerivAt f (df t) t)
    (hdf : ∀ t ∈ Set.Icc (0 : ℝ) 1, df t ≤ C) : f 1-f 0 ≤ C := by
  have hh := scalar_first_derivative_lower (fun t => -f t) (fun t => -df t) (-C)
    (fun t ht => (hf t ht).neg) (fun t ht => neg_le_neg (hdf t ht))
  linarith

theorem scalar_second_derivative_upper (f df ddf : ℝ → ℝ) (C : ℝ)
    (hf : ∀ t ∈ Set.Icc (0 : ℝ) 1, HasDerivAt f (df t) t)
    (hdf : ∀ t ∈ Set.Icc (0 : ℝ) 1, HasDerivAt df (ddf t) t)
    (hddf : ∀ t ∈ Set.Icc (0 : ℝ) 1, ddf t ≤ C) :
    f 1 ≤ f 0+df 0+C/2 := by
  let g := fun t => f t-(C/2)*t^2
  let dg := fun t => df t-C*t
  have hg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt g (dg t) t := by
    convert (hf t ht).sub (((hasDerivAt_id t).pow 2).const_mul (C/2)) using 1
    dsimp [dg]
    ring
  have hdg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt dg (ddf t-C) t := by
    convert (hdf t ht).sub ((hasDerivAt_id t).const_mul C) using 1
    ring
  have hc : ConcaveOn ℝ (Set.Icc (0 : ℝ) 1) g :=
    concaveOn_of_hasDerivWithinAt2_nonpos (convex_Icc (0 : ℝ) 1)
      (fun t ht => (hg t ht).continuousAt.continuousWithinAt)
      (fun t ht => (hg t (interior_subset ht)).hasDerivWithinAt)
      (fun t ht => (hdg t (interior_subset ht)).hasDerivWithinAt)
      (fun t ht => sub_nonpos.mpr (hddf t (interior_subset ht)))
  have hi0 : (0 : ℝ) ∈ Set.Icc (0 : ℝ) 1 := by norm_num
  have hi1 : (1 : ℝ) ∈ Set.Icc (0 : ℝ) 1 := by norm_num
  have hb := hc.slope_le_of_hasDerivAt hi0 hi1 (by norm_num) (hg 0 hi0)
  simp only [slope_def_field,g,dg,zero_pow (by norm_num : (2 : ℕ) ≠ 0),
    one_pow,mul_zero,mul_one,sub_zero,div_one] at hb
  linarith

def conservativeHessian (u k : State) : ℝ := hessianForm (toPrimitive u) (primitiveD u k)

theorem entropy_taylor_upper (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v) (M : ℝ)
    (hH : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      conservativeHessian (segment u v t) (v-u) ≤ M*sizeSquared (v-u)) :
    entropy v ≤ entropy u+dot (gradient u) (v-u)+(M/2)*sizeSquared (v-u) := by
  let f := fun t => entropy (segment u v t)
  let df := fun t => dot (gradient (segment u v t)) (v-u)
  let ddf := fun t => conservativeHessian (segment u v t) (v-u)
  have hf (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t := by
    obtain ⟨hr,hp⟩ := segment_admissible u v hu hv t ht
    exact entropy_derivative (segment_derivative u v t) (ne_of_gt hr) (ne_of_gt hp)
  have hdf (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt df (ddf t) t := by
    obtain ⟨hr,hp⟩ := segment_admissible u v hu hv t ht
    exact entropy_second_directional (segment_derivative u v t) hr hp
  have hb := scalar_second_derivative_upper f df ddf (M*sizeSquared (v-u)) hf hdf hH
  simp [f,df,EulerEntropyConvexity.segment] at hb
  nlinarith

end EulerEntropyTaylor

-- Finite-dimensional real identities used by the actual finite-volume update.
noncomputable section
namespace EulerVectorEstimates
open EulerEntropy EulerEnergyBounds
open scoped BigOperators

theorem dot_add_left (x y z : State) : dot (x+y) z=dot x z+dot y z := by dsimp [dot]; ring
theorem dot_add_right (x y z : State) : dot x (y+z)=dot x y+dot x z := by dsimp [dot]; ring
theorem dot_sub_left (x y z : State) : dot (x-y) z=dot x z-dot y z := by dsimp [dot]; ring
theorem dot_sub_right (x y z : State) : dot x (y-z)=dot x y-dot x z := by dsimp [dot]; ring
theorem dot_smul_left (a : ℝ) (x y : State) : dot (a • x) y=a*dot x y := by dsimp [dot]; ring
theorem dot_smul_right (a : ℝ) (x y : State) : dot x (a • y)=a*dot x y := by dsimp [dot]; ring
theorem dot_neg_right (x y : State) : dot x (-y)= -dot x y := by dsimp [dot]; ring
theorem dot_self (x : State) : dot x x=sizeSquared x := by dsimp [dot,sizeSquared]; ring

theorem dot_sum_right {I : Type*} [Fintype I] (x : State) (u : I → State) :
    dot x (∑ i, u i) = ∑ i, dot x (u i) := by
  simp only [dot,Finset.sum_apply,Finset.sum_add_distrib,Finset.mul_sum]

theorem size_nonnegative (x : State) : 0 ≤ sizeSquared x := by dsimp [sizeSquared]; positivity
theorem size_smul (a : ℝ) (x : State) : sizeSquared (a • x)=a^2*sizeSquared x := by
  dsimp [sizeSquared]
  ring
theorem size_sub_comm (x y : State) : sizeSquared (x-y)=sizeSquared (y-x) := by
  dsimp [sizeSquared]
  ring
theorem size_as_sum (x : State) : sizeSquared x=∑ j, x j^2 := by
  simp [sizeSquared,Fin.sum_univ_succ]
  ring

theorem size_add_bound (x y : State) : sizeSquared (x+y) ≤ 2*sizeSquared x+2*sizeSquared y := by
  dsimp [sizeSquared]
  nlinarith [sq_nonneg (x 0-y 0),sq_nonneg (x 1-y 1),sq_nonneg (x 2-y 2),
    sq_nonneg (x 3-y 3),sq_nonneg (x 4-y 4)]

theorem size_sum_bound {I : Type*} [Fintype I] (u : I → State) :
    sizeSquared (∑ i, u i) ≤ (Fintype.card I : ℝ)*∑ i, sizeSquared (u i) := by
  have hpoint (j : Fin 5) : (∑ i, u i j)^2 ≤ (Fintype.card I : ℝ)*∑ i, (u i j)^2 := by
    have hh := Finset.sum_mul_sq_le_sq_mul_sq Finset.univ (fun _ : I => (1 : ℝ)) (fun i => u i j)
    simpa [nsmul_eq_mul] using hh
  rw [size_as_sum]
  simp only [Finset.sum_apply]
  calc
    _ ≤ ∑ j, (Fintype.card I : ℝ)*∑ i, (u i j)^2 := Finset.sum_le_sum (fun j _ => hpoint j)
    _ = (Fintype.card I : ℝ)*∑ i, ∑ j, (u i j)^2 := by
      rw [← Finset.mul_sum,Finset.sum_comm]
    _ = _ := by simp only [← size_as_sum]

end EulerVectorEstimates

-- Actual conservative entropy Hessian as a bilinear form, with its physical
-- flux compatibility. Uniform Hessian constants are explicit hypotheses below.
noncomputable section
namespace EulerEntropyGeometry
open EulerEntropy EulerEntropyTaylor EulerVectorEstimates EulerEnergyBounds
open EulerConservativePrimitive
abbrev State := Fin 5 → ℝ

def hessianVector (u k : State) : State := variablesD (toPrimitive u) (primitiveD u k)
def hessianPair (u k z : State) : ℝ := dot (hessianVector u k) z

def primitivePair (w h k : State) : ℝ :=
  h 4*k 4/(2*(w 4)^2*w 0)+(h 1*k 1+h 2*k 2+h 3*k 3)/(w 4*(w 0)^2)+
    (2/w 0)*(h 0/w 0+h 4/(2*w 4))*(k 0/w 0+k 4/(2*w 4))

theorem hessian_pullback_bilinear (w h k : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0) :
    dot (variablesD w h) (jacobian w k)=primitivePair w h k := by
  dsimp [dot,variablesD,jacobian,kinetic,kineticD,primitivePair]
  field_simp
  ring

theorem hessian_pair_primitive (u k z : State) (hu : EulerAdmissible.Admissible u) :
    hessianPair u k z=primitivePair (toPrimitive u) (primitiveD u k) (primitiveD u z) := by
  have hh := hessian_pullback_bilinear (toPrimitive u) (primitiveD u k) (primitiveD u z)
    (by dsimp [toPrimitive]; exact ne_of_gt (one_div_pos.mpr hu.1)) (ne_of_gt hu.2)
  rw [jacobian_primitiveD u z (ne_of_gt hu.1)] at hh
  exact hh

theorem hessian_pair_self (u k : State) (hu : EulerAdmissible.Admissible u) :
    hessianPair u k k=conservativeHessian u k := by
  rw [hessian_pair_primitive u k k hu]
  dsimp [primitivePair,conservativeHessian,hessianForm]
  ring

theorem hessian_pair_symmetric (u k z : State) (hu : EulerAdmissible.Admissible u) :
    hessianPair u k z=hessianPair u z k := by
  rw [hessian_pair_primitive u k z hu,hessian_pair_primitive u z k hu]
  dsimp [primitivePair]
  ring

theorem primitiveD_sub (u k z : State) : primitiveD u (k-z)=primitiveD u k-primitiveD u z := by
  funext i
  fin_cases i <;> dsimp [primitiveD,pressureD] <;> ring

theorem variablesD_sub (w k z : State) : variablesD w (k-z)=variablesD w k-variablesD w z := by
  funext i
  fin_cases i <;> dsimp [variablesD,kineticD] <;> ring

theorem hessian_pair_sub_left (u x y z : State) :
    hessianPair u (x-y) z=hessianPair u x z-hessianPair u y z := by
  simp only [hessianPair,hessianVector,primitiveD_sub,variablesD_sub,dot_sub_left]

theorem hessian_pair_sub_right (u x y z : State) :
    hessianPair u x (y-z)=hessianPair u x y-hessianPair u x z := by
  simp only [hessianPair,dot_sub_right]

theorem hessian_young_bound (u k z : State) (hu : EulerAdmissible.Admissible u) (M : ℝ)
    (hk : conservativeHessian u k ≤ M*sizeSquared k)
    (hz : conservativeHessian u z ≤ M*sizeSquared z) :
    hessianPair u k z ≤ (M/2)*(sizeSquared k+sizeSquared z) := by
  have hn : 0 ≤ hessianPair u (k-z) (k-z) := by
    rw [hessian_pair_self u _ hu]
    exact hessian_nonnegative _ _ (by dsimp [toPrimitive]; exact one_div_pos.mpr hu.1) hu.2
  rw [hessian_pair_sub_left,hessian_pair_sub_right,hessian_pair_sub_right,
    hessian_pair_symmetric u z k hu,hessian_pair_self u k hu,hessian_pair_self u z hu] at hn
  linarith

theorem primitive_hessian_flux (w h : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0) (d : Fin 3) :
    dot (variablesD w h) (primitiveFlux w d)=(jacobian w h) ⟨d.val+1,by omega⟩ := by
  fin_cases d <;> dsimp [dot,variablesD,primitiveFlux,jacobian,kinetic,kineticD] <;>
    field_simp <;> ring

theorem hessian_flux_compatibility (u k : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    hessianPair u k (EulerAdmissible.eulerFlux u d)=k ⟨d.val+1,by omega⟩ := by
  have hq : 0 < toPrimitive u 0 := by dsimp [toPrimitive]; exact one_div_pos.mpr hu.1
  have hc := canonical_flux (toPrimitive u) hq d
  rw [conserved_toPrimitive u (ne_of_gt hu.1)] at hc
  dsimp [hessianPair,hessianVector]
  rw [hc,primitive_hessian_flux _ _ (ne_of_gt hq) (ne_of_gt hu.2) d,
    jacobian_primitiveD u k (ne_of_gt hu.1)]

theorem gradient_pair_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hder : HasDerivAt u k t) (hu : EulerAdmissible.Admissible (u t)) (z : State) :
    HasDerivAt (fun s => dot (gradient (u s)) z) (hessianPair (u t) k z) t :=
  dot_derivative (gradient_derivative hder hu.1 hu.2) z

end EulerEntropyGeometry

-- Actual Rusanov face entropy residual from proved entropy calculus. The
-- quantitative Hessian and flux bounds on the state segment are explicit.
noncomputable section
namespace EulerFaceEntropy
open EulerEntropy EulerEntropyTaylor EulerEntropyConvexity EulerEntropyGeometry
open EulerVectorEstimates EulerEnergyBounds
abbrev State := Fin 5 → ℝ

def meanFlux (u v : State) (d : Fin 3) : State :=
  (1/2 : ℝ) • (EulerAdmissible.eulerFlux u d+EulerAdmissible.eulerFlux v d)

theorem flux_midpoint_bound (u v w : State) (d : Fin 3) (L : ℝ)
    (h0 : sizeSquared (EulerAdmissible.eulerFlux w d-EulerAdmissible.eulerFlux u d) ≤
      L^2*sizeSquared (v-u))
    (h1 : sizeSquared (EulerAdmissible.eulerFlux w d-EulerAdmissible.eulerFlux v d) ≤
      L^2*sizeSquared (v-u)) :
    sizeSquared (meanFlux u v d-EulerAdmissible.eulerFlux w d) ≤ L^2*sizeSquared (v-u) := by
  have he : meanFlux u v d-EulerAdmissible.eulerFlux w d = (1/2 : ℝ) •
      ((EulerAdmissible.eulerFlux u d-EulerAdmissible.eulerFlux w d)+
        (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux w d)) := by
    funext j
    dsimp [meanFlux]
    ring
  rw [he,size_smul]
  have hh := size_add_bound (EulerAdmissible.eulerFlux u d-EulerAdmissible.eulerFlux w d)
    (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux w d)
  rw [size_sub_comm (EulerAdmissible.eulerFlux u d) _,size_sub_comm (EulerAdmissible.eulerFlux v d) _] at hh
  nlinarith

theorem residual_derivative (u v : State) (d : Fin 3) (t : ℝ)
    (ht : EulerAdmissible.Admissible (EulerEntropyConvexity.segment u v t)) :
    HasDerivAt (fun s => dot (gradient (EulerEntropyConvexity.segment u v s)) (meanFlux u v d)-
      (EulerEntropyConvexity.segment u v s) ⟨d.val+1,by omega⟩)
      (hessianPair (EulerEntropyConvexity.segment u v t) (v-u)
        (meanFlux u v d-EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d)) t := by
  have hcurve := segment_derivative u v t
  have hh := (gradient_pair_derivative hcurve ht (meanFlux u v d)).sub
    ((hasDerivAt_pi.mp hcurve) ⟨d.val+1,by omega⟩)
  simpa only [hessian_pair_sub_right,hessian_flux_compatibility _ _ ht d] using hh

theorem central_entropy_residual (u v : State) (d : Fin 3) (M L : ℝ)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v) (hM : 0 ≤ M)
    (hH : ∀ t ∈ Set.Icc (0 : ℝ) 1, ∀ k,
      conservativeHessian (EulerEntropyConvexity.segment u v t) k ≤ M*sizeSquared k)
    (hF : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      sizeSquared (EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d-
        EulerAdmissible.eulerFlux u d) ≤ L^2*sizeSquared (v-u) ∧
      sizeSquared (EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d-
        EulerAdmissible.eulerFlux v d) ≤ L^2*sizeSquared (v-u)) :
    dot (gradient v-gradient u) (meanFlux u v d)-(v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) ≤
      (M/2)*(1+L^2)*sizeSquared (v-u) := by
  let f := fun t => dot (gradient (EulerEntropyConvexity.segment u v t)) (meanFlux u v d)-
    (EulerEntropyConvexity.segment u v t) ⟨d.val+1,by omega⟩
  let df := fun t => hessianPair (EulerEntropyConvexity.segment u v t) (v-u)
    (meanFlux u v d-EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d)
  have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t :=
    residual_derivative u v d t (segment_admissible u v hu hv t ht)
  have hb (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
      df t ≤ (M/2)*(1+L^2)*sizeSquared (v-u) := by
    have hh := hessian_young_bound (EulerEntropyConvexity.segment u v t) (v-u)
      (meanFlux u v d-EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d)
      (segment_admissible u v hu hv t ht) M
      (hH t ht _) (hH t ht _)
    have hflux := flux_midpoint_bound u v (EulerEntropyConvexity.segment u v t) d L
      (hF t ht).1 (hF t ht).2
    have hmult := mul_le_mul_of_nonneg_left hflux (by positivity : 0 ≤ M/2)
    dsimp [df]
    nlinarith
  have hs := scalar_first_derivative_upper f df ((M/2)*(1+L^2)*sizeSquared (v-u)) hd hb
  simp [f,EulerEntropyConvexity.segment] at hs
  rw [dot_sub_left]
  linarith

theorem gradient_strong_monotonicity (u v : State) (lambda : ℝ)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v)
    (hH : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      lambda*sizeSquared (v-u) ≤ conservativeHessian (EulerEntropyConvexity.segment u v t) (v-u)) :
    lambda*sizeSquared (v-u) ≤ dot (gradient v-gradient u) (v-u) := by
  let f := fun t => dot (gradient (EulerEntropyConvexity.segment u v t)) (v-u)
  let df := fun t => conservativeHessian (EulerEntropyConvexity.segment u v t) (v-u)
  have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t := by
    have h := segment_admissible u v hu hv t ht
    exact entropy_second_directional (segment_derivative u v t) h.1 h.2
  have hs := scalar_first_derivative_lower f df (lambda*sizeSquared (v-u)) hd hH
  simpa [f,EulerEntropyConvexity.segment,dot_sub_left] using hs

theorem rusanov_face_entropy_bound (u v : State) (d : Fin 3) (a M L lambda : ℝ)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v)
    (ha : 0 ≤ a) (hM : 0 ≤ M)
    (hHupper : ∀ t ∈ Set.Icc (0 : ℝ) 1, ∀ k,
      conservativeHessian (EulerEntropyConvexity.segment u v t) k ≤ M*sizeSquared k)
    (hHlower : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      lambda*sizeSquared (v-u) ≤ conservativeHessian (EulerEntropyConvexity.segment u v t) (v-u))
    (hF : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      sizeSquared (EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d-
        EulerAdmissible.eulerFlux u d) ≤ L^2*sizeSquared (v-u) ∧
      sizeSquared (EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d-
        EulerAdmissible.eulerFlux v d) ≤ L^2*sizeSquared (v-u))
    (hvisc : M*(1+L^2) ≤ a*lambda/2) :
    dot (gradient v-gradient u) (EulerAdmissible.faceFlux u v a d)-
      (v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) ≤
      -(a*lambda/4)*sizeSquared (v-u) := by
  have hcentral := central_entropy_residual u v d M L hu hv hM hHupper hF
  have hmono := gradient_strong_monotonicity u v lambda hu hv hHlower
  have hmult := mul_le_mul_of_nonneg_left hmono (by positivity : 0 ≤ a/2)
  have hmargin := mul_le_mul_of_nonneg_right hvisc (size_nonnegative (v-u))
  have he : dot (gradient v-gradient u) (EulerAdmissible.faceFlux u v a d) =
      dot (gradient v-gradient u) (meanFlux u v d)-(a/2)*dot (gradient v-gradient u) (v-u) := by
    simp only [EulerAdmissible.faceFlux,meanFlux,dot_smul_right,dot_sub_right,dot_add_right]
    ring
  rw [he]
  nlinarith

end EulerFaceEntropy

-- Algebra and quadratic estimates for the actual nonlinear Rusanov update.
-- Spatial entropy residuals and Hessian bounds are still required to obtain
-- a quantitative finite-step dissipation theorem.
noncomputable section
namespace EulerFiniteVolumeEntropy
open EulerEntropy EulerEnergyBounds EulerVectorEstimates
open scoped BigOperators

def gridFace {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (d : Fin 3) (i : I) : State :=
  EulerAdmissible.faceFlux (u i) (u (neighbor d i)) (a d) d

def gridIncrement {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (i : I) : State :=
  -(∑ d, (gridFace u neighbor a d i-gridFace u neighbor a d ((neighbor d).symm i)))

def gridUpdate {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (ratio : ℝ) (i : I) : State :=
  EulerAdmissible.update (u i) (fun d => u (neighbor d i))
    (fun d => u ((neighbor d).symm i)) ratio a

theorem update_increment {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (ratio : ℝ) (i : I) :
    gridUpdate u neighbor a ratio i=u i+ratio • gridIncrement u neighbor a i := by
  funext j
  simp [gridUpdate,EulerAdmissible.update,gridIncrement,gridFace,Fin.sum_univ_succ]
  ring

theorem periodic_pairing {I : Type*} [Fintype I] (neighbor : Equiv.Perm I) (g flux : I → State) :
    (∑ i, dot (g i) (flux i-flux (neighbor.symm i))) =
      -(∑ i, dot (g (neighbor i)-g i) (flux i)) := by
  have heq : (∑ i, dot (g i) (flux (neighbor.symm i))) =
      ∑ i, dot (g (neighbor i)) (flux i) := by
    have h := Equiv.sum_comp neighbor (fun i => dot (g i) (flux (neighbor.symm i)))
    simpa only [Equiv.symm_apply_apply] using h.symm
  simp only [dot_sub_right,dot_sub_left,Finset.sum_sub_distrib,heq]
  ring

theorem increment_pairing {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (g : I → State) :
    (∑ i, dot (g i) (gridIncrement u neighbor a i)) =
      ∑ d, ∑ i, dot (g (neighbor d i)-g i) (gridFace u neighbor a d i) := by
  simp only [gridIncrement,dot_neg_right,dot_sum_right,Finset.sum_neg_distrib]
  rw [Finset.sum_comm]
  simp only [periodic_pairing,Finset.sum_neg_distrib,neg_neg]

theorem update_pairing {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio : ℝ) (g : I → State) :
    (∑ i, dot (g i) (gridUpdate u neighbor a ratio i-u i)) =
      ratio*(∑ d, ∑ i, dot (g (neighbor d i)-g i) (gridFace u neighbor a d i)) := by
  simp only [update_increment,add_sub_cancel_left,dot_smul_right,← Finset.mul_sum,increment_pairing]

def edgeAction (u v : State) (a sign : ℝ) (d : Fin 3) : State :=
  a • (v-u)+sign • (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux u d)

theorem edge_action_bound (u v : State) (a sign A L : ℝ) (d : Fin 3)
    (ha : a^2 ≤ A^2) (hs : sign^2=1)
    (hF : sizeSquared (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux u d) ≤
      L^2*sizeSquared (v-u)) :
    sizeSquared (edgeAction u v a sign d) ≤ 2*(A^2+L^2)*sizeSquared (v-u) := by
  have hh := size_add_bound (a • (v-u))
    (sign • (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux u d))
  simp only [size_smul,hs,one_mul] at hh
  have hmult := mul_le_mul_of_nonneg_right ha (size_nonnegative (v-u))
  dsimp [edgeAction]
  nlinarith

def neighborState {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (i : I) : Fin 6 → State :=
  ![u (neighbor 0 i),u ((neighbor 0).symm i),u (neighbor 1 i),u ((neighbor 1).symm i),
    u (neighbor 2 i),u ((neighbor 2).symm i)]

def contributions {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (i : I) : Fin 6 → State :=
  ![edgeAction (u i) (u (neighbor 0 i)) (a 0) (-1) 0,
    edgeAction (u i) (u ((neighbor 0).symm i)) (a 0) 1 0,
    edgeAction (u i) (u (neighbor 1 i)) (a 1) (-1) 1,
    edgeAction (u i) (u ((neighbor 1).symm i)) (a 1) 1 1,
    edgeAction (u i) (u (neighbor 2 i)) (a 2) (-1) 2,
    edgeAction (u i) (u ((neighbor 2).symm i)) (a 2) 1 2]

theorem increment_six_neighbors {I : Type*} (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (i : I) :
    gridIncrement u neighbor a i=(1/2 : ℝ) • ∑ j, contributions u neighbor a i j := by
  funext k
  simp [gridIncrement,gridFace,contributions,edgeAction,EulerAdmissible.faceFlux,Fin.sum_univ_succ]
  ring

theorem point_increment_bound {I : Type*} (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (A L : ℝ)
    (ha : ∀ d, (a d)^2 ≤ A^2)
    (hF : ∀ i j d, sizeSquared (EulerAdmissible.eulerFlux (neighborState u neighbor i j) d-
      EulerAdmissible.eulerFlux (u i) d) ≤ L^2*sizeSquared (neighborState u neighbor i j-u i))
    (i : I) : sizeSquared (gridIncrement u neighbor a i) ≤
      3*(A^2+L^2)*(∑ j, sizeSquared (neighborState u neighbor i j-u i)) := by
  have hc (j : Fin 6) : sizeSquared (contributions u neighbor a i j) ≤
      2*(A^2+L^2)*sizeSquared (neighborState u neighbor i j-u i) := by
    fin_cases j
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 0) (by norm_num) (hF i 0 0)
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 0) (by norm_num) (hF i 1 0)
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 1) (by norm_num) (hF i 2 1)
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 1) (by norm_num) (hF i 3 1)
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 2) (by norm_num) (hF i 4 2)
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 2) (by norm_num) (hF i 5 2)
  have hs := Finset.sum_le_sum (fun j (_ : j ∈ Finset.univ) => hc j)
  rw [← Finset.mul_sum] at hs
  have hb := size_sum_bound (contributions u neighbor a i)
  norm_num only [Fintype.card_fin,Nat.cast_ofNat] at hb
  rw [increment_six_neighbors,size_smul]
  nlinarith

def edgeEnergy {I : Type*} [Fintype I] (u : I → State) (neighbor : Fin 3 → Equiv.Perm I) : ℝ :=
  ∑ d, ∑ i, sizeSquared (u (neighbor d i)-u i)

theorem neighbor_energy_sum {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) :
    (∑ i, ∑ j, sizeSquared (neighborState u neighbor i j-u i)) = 2*edgeEnergy u neighbor := by
  have heq (d : Fin 3) : (∑ i, sizeSquared (u ((neighbor d).symm i)-u i)) =
      ∑ i, sizeSquared (u (neighbor d i)-u i) := by
    have hh := Equiv.sum_comp (neighbor d) (fun i => sizeSquared (u ((neighbor d).symm i)-u i))
    simpa only [Equiv.symm_apply_apply,size_sub_comm] using hh.symm
  simp [neighborState,Fin.sum_univ_succ,Finset.sum_add_distrib,heq,edgeEnergy]
  ring

theorem total_increment_bound {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (A L : ℝ)
    (ha : ∀ d, (a d)^2 ≤ A^2)
    (hF : ∀ i j d, sizeSquared (EulerAdmissible.eulerFlux (neighborState u neighbor i j) d-
      EulerAdmissible.eulerFlux (u i) d) ≤ L^2*sizeSquared (neighborState u neighbor i j-u i)) :
    (∑ i, sizeSquared (gridIncrement u neighbor a i)) ≤
      6*(A^2+L^2)*edgeEnergy u neighbor := by
  calc
    _ ≤ ∑ i, 3*(A^2+L^2)*(∑ j, sizeSquared (neighborState u neighbor i j-u i)) :=
      Finset.sum_le_sum (fun i _ => point_increment_bound u neighbor a A L ha hF i)
    _ = _ := by rw [← Finset.mul_sum,neighbor_energy_sum]; ring

theorem edge_energy_nonnegative {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) : 0 ≤ edgeEnergy u neighbor :=
  Finset.sum_nonneg (fun _ _ => Finset.sum_nonneg (fun _ _ => size_nonnegative _))

theorem face_entropy_sum_bound {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (C : ℝ)
    (hface : ∀ d i, dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)-
      (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩) ≤
        -C*sizeSquared (u (neighbor d i)-u i)) :
    (∑ d, ∑ i, dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)) ≤
      -C*edgeEnergy u neighbor := by
  have hp (d : Fin 3) : (∑ i, (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩))=0 := by
    rw [Finset.sum_sub_distrib]
    have hh := Equiv.sum_comp (neighbor d) (fun i => u i ⟨d.val+1,by omega⟩)
    rw [hh,sub_self]
  have hd (d : Fin 3) :
      (∑ i, dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)) ≤
        -C*(∑ i, sizeSquared (u (neighbor d i)-u i)) := by
    calc
      _ ≤ ∑ i, ((u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩)-
          C*sizeSquared (u (neighbor d i)-u i)) :=
        Finset.sum_le_sum (fun i _ => by linarith [hface d i])
      _ = _ := by rw [Finset.sum_sub_distrib,hp,← Finset.mul_sum]; ring
  calc
    _ ≤ ∑ d, -C*(∑ i, sizeSquared (u (neighbor d i)-u i)) := Finset.sum_le_sum (fun d _ => hd d)
    _ = _ := by rw [← Finset.mul_sum]; rfl

theorem entropy_step_bound {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio A L M C : ℝ)
    (hr : 0 ≤ ratio) (hM : 0 ≤ M)
    (hu : ∀ i, EulerAdmissible.Admissible (u i))
    (hv : ∀ i, EulerAdmissible.Admissible (gridUpdate u neighbor a ratio i))
    (ha : ∀ d, (a d)^2 ≤ A^2)
    (hF : ∀ i j d, sizeSquared (EulerAdmissible.eulerFlux (neighborState u neighbor i j) d-
      EulerAdmissible.eulerFlux (u i) d) ≤ L^2*sizeSquared (neighborState u neighbor i j-u i))
    (hH : ∀ i t, t ∈ Set.Icc (0 : ℝ) 1 →
      EulerEntropyTaylor.conservativeHessian
        (EulerEntropyConvexity.segment (u i) (gridUpdate u neighbor a ratio i) t)
        (gridUpdate u neighbor a ratio i-u i) ≤ M*sizeSquared (gridUpdate u neighbor a ratio i-u i))
    (hface : ∀ d i, dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)-
      (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩) ≤
        -C*sizeSquared (u (neighbor d i)-u i)) :
    (∑ i, entropy (gridUpdate u neighbor a ratio i)) ≤ (∑ i, entropy (u i))-
      ratio*C*edgeEnergy u neighbor+3*M*ratio^2*(A^2+L^2)*edgeEnergy u neighbor := by
  have hlinear : (∑ i, dot (gradient (u i)) (gridUpdate u neighbor a ratio i-u i)) ≤
      -ratio*C*edgeEnergy u neighbor := by
    rw [update_pairing]
    have hh := mul_le_mul_of_nonneg_left (face_entropy_sum_bound u neighbor a C hface) hr
    convert hh using 1
    ring
  have hquad : (∑ i, sizeSquared (gridUpdate u neighbor a ratio i-u i)) ≤
      ratio^2*(6*(A^2+L^2)*edgeEnergy u neighbor) := by
    simp only [update_increment,add_sub_cancel_left,size_smul,← Finset.mul_sum]
    exact mul_le_mul_of_nonneg_left (total_increment_bound u neighbor a A L ha hF) (sq_nonneg ratio)
  have ht (i : I) := EulerEntropyTaylor.entropy_taylor_upper (u i) (gridUpdate u neighbor a ratio i)
    (hu i) (hv i) M (hH i)
  have hs := Finset.sum_le_sum (fun i (_ : i ∈ Finset.univ) => ht i)
  simp only [Finset.sum_add_distrib,← Finset.mul_sum] at hs
  have hquadratic := mul_le_mul_of_nonneg_left hquad (by positivity : 0 ≤ M/2)
  nlinarith

theorem entropy_step_dissipation {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio A L M C : ℝ)
    (hr : 0 ≤ ratio) (hM : 0 ≤ M)
    (hu : ∀ i, EulerAdmissible.Admissible (u i))
    (hv : ∀ i, EulerAdmissible.Admissible (gridUpdate u neighbor a ratio i))
    (ha : ∀ d, (a d)^2 ≤ A^2)
    (hF : ∀ i j d, sizeSquared (EulerAdmissible.eulerFlux (neighborState u neighbor i j) d-
      EulerAdmissible.eulerFlux (u i) d) ≤ L^2*sizeSquared (neighborState u neighbor i j-u i))
    (hH : ∀ i t, t ∈ Set.Icc (0 : ℝ) 1 →
      EulerEntropyTaylor.conservativeHessian
        (EulerEntropyConvexity.segment (u i) (gridUpdate u neighbor a ratio i) t)
        (gridUpdate u neighbor a ratio i-u i) ≤ M*sizeSquared (gridUpdate u neighbor a ratio i-u i))
    (hface : ∀ d i, dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)-
      (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩) ≤
        -C*sizeSquared (u (neighbor d i)-u i))
    (hstep : 3*M*ratio*(A^2+L^2) ≤ C/2) :
    (∑ i, entropy (gridUpdate u neighbor a ratio i)) ≤ (∑ i, entropy (u i))-
      (ratio*C/2)*edgeEnergy u neighbor := by
  have hb := entropy_step_bound u neighbor a ratio A L M C hr hM hu hv ha hF hH hface
  have hs := mul_le_mul_of_nonneg_right hstep (mul_nonneg hr (edge_energy_nonnegative u neighbor))
  nlinarith

end EulerFiniteVolumeEntropy

-- Conditional finite-step theorem for the actual nonlinear method. The region
-- is defined by actual entropy-Hessian and physical-flux bounds; proving the
-- full trajectory stays in such a region remains an explicit obligation.
noncomputable section
namespace EulerEntropyRegion
open EulerEntropy EulerEntropyTaylor EulerEntropyGeometry EulerFaceEntropy
open EulerFiniteVolumeEntropy EulerVectorEstimates EulerEnergyBounds
open scoped BigOperators
abbrev State := Fin 5 → ℝ

structure RegionBounds (K : Set State) (M lambda L : ℝ) : Prop where
  convex : Convex ℝ K
  admissible : ∀ u ∈ K, EulerAdmissible.Admissible u
  hessian_upper : ∀ u ∈ K, ∀ k, conservativeHessian u k ≤ M*sizeSquared k
  hessian_lower : ∀ u ∈ K, ∀ k, lambda*sizeSquared k ≤ conservativeHessian u k
  flux_bound : ∀ u ∈ K, ∀ v ∈ K, ∀ d,
    sizeSquared (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux u d) ≤ L^2*sizeSquared (v-u)

theorem segment_in_region (K : Set State) (hc : Convex ℝ K) (u v : State)
    (hu : u ∈ K) (hv : v ∈ K) (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
    EulerEntropyConvexity.segment u v t ∈ K := by
  rw [EulerEntropyConvexity.segment_mix]
  exact hc hu hv (sub_nonneg.mpr ht.2) ht.1 (by ring)

theorem segment_distance_bounds (u v : State) (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
    sizeSquared (EulerEntropyConvexity.segment u v t-u) ≤ sizeSquared (v-u) ∧
    sizeSquared (EulerEntropyConvexity.segment u v t-v) ≤ sizeSquared (v-u) := by
  have hS := size_nonnegative (v-u)
  have ht2 : t^2 ≤ 1 := by nlinarith [ht.1,ht.2]
  have htm2 : (t-1)^2 ≤ 1 := by nlinarith [ht.1,ht.2]
  have he0 : EulerEntropyConvexity.segment u v t-u=t • (v-u) := by
    simp [EulerEntropyConvexity.segment]
  have he1 : EulerEntropyConvexity.segment u v t-v=(t-1) • (v-u) := by
    funext j
    dsimp [EulerEntropyConvexity.segment]
    ring
  rw [he0,he1,size_smul,size_smul]
  constructor
  · simpa only [one_mul] using mul_le_mul_of_nonneg_right ht2 hS
  · simpa only [one_mul] using mul_le_mul_of_nonneg_right htm2 hS

theorem region_face_entropy (K : Set State) (M lambda L a : ℝ)
    (hK : RegionBounds K M lambda L) (u v : State) (hu : u ∈ K) (hv : v ∈ K)
    (d : Fin 3) (ha : 0 ≤ a) (hM : 0 ≤ M) (hvisc : M*(1+L^2) ≤ a*lambda/2) :
    dot (gradient v-gradient u) (EulerAdmissible.faceFlux u v a d)-
      (v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) ≤ -(a*lambda/4)*sizeSquared (v-u) := by
  have hseg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) := segment_in_region K hK.convex u v hu hv t ht
  apply rusanov_face_entropy_bound u v d a M L lambda (hK.admissible u hu) (hK.admissible v hv)
    ha hM (fun t ht k => hK.hessian_upper _ (hseg t ht) k)
    (fun t ht => hK.hessian_lower _ (hseg t ht) _) _ hvisc
  intro t ht
  obtain ⟨h0,h1⟩ := segment_distance_bounds u v t ht
  constructor
  · exact (hK.flux_bound u hu _ (hseg t ht) d).trans (mul_le_mul_of_nonneg_left h0 (sq_nonneg L))
  · exact (hK.flux_bound v hv _ (hseg t ht) d).trans (mul_le_mul_of_nonneg_left h1 (sq_nonneg L))

theorem nonlinear_step_entropy_from_region {I : Type*} [Fintype I]
    (K : Set State) (M lambda L : ℝ) (hK : RegionBounds K M lambda L)
    (u : I → State) (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio amin A : ℝ)
    (hu : ∀ i, u i ∈ K) (hv : ∀ i, gridUpdate u neighbor a ratio i ∈ K)
    (hr : 0 ≤ ratio) (hM : 0 ≤ M) (hlambda : 0 ≤ lambda) (hamin : 0 ≤ amin)
    (ha : ∀ d, amin ≤ a d) (haA : ∀ d, (a d)^2 ≤ A^2)
    (hvisc : M*(1+L^2) ≤ amin*lambda/2)
    (hstep : 3*M*ratio*(A^2+L^2) ≤ amin*lambda/8) :
    (∑ i, entropy (gridUpdate u neighbor a ratio i)) ≤ (∑ i, entropy (u i))-
      (ratio*amin*lambda/8)*edgeEnergy u neighbor := by
  have hneighbor (i : I) (j : Fin 6) : neighborState u neighbor i j ∈ K := by
    fin_cases j
    all_goals exact hu _
  have hface (d : Fin 3) (i : I) :
      dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)-
      (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩) ≤
        -(amin*lambda/4)*sizeSquared (u (neighbor d i)-u i) := by
    have hb := region_face_entropy K M lambda L (a d) hK (u i) (u (neighbor d i)) (hu i) (hu _)
      d (hamin.trans (ha d)) hM
      (hvisc.trans (by nlinarith [mul_le_mul_of_nonneg_right (ha d) hlambda]))
    have hm := mul_le_mul_of_nonneg_right (ha d) hlambda
    have hs := mul_le_mul_of_nonneg_right hm (size_nonnegative (u (neighbor d i)-u i))
    exact hb.trans (by nlinarith)
  have hH (i : I) (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :=
    hK.hessian_upper _ (segment_in_region K hK.convex _ _ (hu i) (hv i) t ht)
      (gridUpdate u neighbor a ratio i-u i)
  have hb := entropy_step_dissipation u neighbor a ratio A L M (amin*lambda/4) hr hM
    (fun i => hK.admissible _ (hu i)) (fun i => hK.admissible _ (hv i)) haA
    (fun i j d => hK.flux_bound _ (hu i) _ (hneighbor i j) d) hH hface
    (by
      convert hstep using 1
      ring)
  convert hb using 1
  ring

end EulerEntropyRegion

-- A concrete convex physical-state region. Membership of a whole evolved
-- trajectory is not asserted by these pointwise geometric bounds.
noncomputable section
namespace EulerPhysicalRegion
open EulerEntropy EulerEntropyTaylor EulerEnergyBounds EulerVectorEstimates
abbrev State := Fin 5 → ℝ

def region : Set State := {u | 1/4 ≤ u 0 ∧ u 0 ≤ 4 ∧ u 4 ≤ 4 ∧ 1/4 ≤ EulerAdmissible.pressure u}

theorem region_admissible (u : State) (hu : u ∈ region) : EulerAdmissible.Admissible u := by
  exact ⟨by linarith [hu.1],by linarith [hu.2.2.2]⟩

theorem pressure_le_support (u : State) (hr : 0 < u 0) (v : EulerAdmissible.Vec) :
    EulerAdmissible.pressure u ≤ EulerAdmissible.supportEnergy u v := by
  rw [EulerAdmissible.complete_square u v hr]
  have hh : 0 ≤ u 0/2*((u 1/u 0-v 0)^2+(u 2/u 0-v 1)^2+(u 3/u 0-v 2)^2) := by positivity
  linarith

theorem pressure_concave_pair (u v : State) (hr : 0 < u 0) (hs : 0 < v 0)
    (a b : ℝ) (ha : 0 ≤ a) (hb : 0 ≤ b) (hab : a+b=1) :
    a*EulerAdmissible.pressure u+b*EulerAdmissible.pressure v ≤
      EulerAdmissible.pressure (a • u+b • v) := by
  let w := a • u+b • v
  have hw : 0 < w 0 := by
    have hh := EulerAdmissible.positive_convex_pair (u 0) (v 0) a hr hs ha (by linarith)
    have he : 1-a=b := by linarith
    simpa only [he] using hh
  let z := EulerAdmissible.fromVelocity w
  have he : a*EulerAdmissible.supportEnergy u z+b*EulerAdmissible.supportEnergy v z =
      EulerAdmissible.supportEnergy w z := by dsimp [EulerAdmissible.supportEnergy,w]; ring
  calc
    _ ≤ a*EulerAdmissible.supportEnergy u z+b*EulerAdmissible.supportEnergy v z :=
      add_le_add (mul_le_mul_of_nonneg_left (pressure_le_support u hr z) ha)
        (mul_le_mul_of_nonneg_left (pressure_le_support v hs z) hb)
    _ = _ := he.trans (EulerAdmissible.supportEnergy_at_velocity w hw)

theorem region_convex : Convex ℝ region := by
  intro u hu v hv a b ha hb hab
  have hr := region_admissible u hu
  have hs := region_admissible v hv
  refine ⟨?_,?_,?_,?_⟩
  · change 1/4 ≤ a*u 0+b*v 0
    nlinarith [mul_le_mul_of_nonneg_left hu.1 ha,mul_le_mul_of_nonneg_left hv.1 hb]
  · change a*u 0+b*v 0 ≤ 4
    nlinarith [mul_le_mul_of_nonneg_left hu.2.1 ha,mul_le_mul_of_nonneg_left hv.2.1 hb]
  · change a*u 4+b*v 4 ≤ 4
    nlinarith [mul_le_mul_of_nonneg_left hu.2.2.1 ha,mul_le_mul_of_nonneg_left hv.2.2.1 hb]
  · have hh := pressure_concave_pair u v hr.1 hs.1 a b ha hb hab
    have h1 := mul_le_mul_of_nonneg_left hu.2.2.2 ha
    have h2 := mul_le_mul_of_nonneg_left hv.2.2.2 hb
    linarith

theorem pressure_upper (u : State) (hu : u ∈ region) : EulerAdmissible.pressure u ≤ 4 := by
  have hr := (region_admissible u hu).1
  have hn : 0 ≤ (u 1^2+u 2^2+u 3^2)/(2*u 0) := by positivity
  dsimp [EulerAdmissible.pressure]
  linarith [hu.2.2.1]

def velocitySquared (u : State) : ℝ := (u 1/u 0)^2+(u 2/u 0)^2+(u 3/u 0)^2
def shiftedMomentumSquared (u k : State) : ℝ :=
  (k 1-(u 1/u 0)*k 0)^2+(k 2-(u 2/u 0)*k 0)^2+(k 3-(u 3/u 0)*k 0)^2
def thermalShift (u k : State) : ℝ := pressureD u k/EulerAdmissible.pressure u-k 0/u 0

theorem kinetic_pressure_identity (u : State) (hr : u 0 ≠ 0) :
    u 0*velocitySquared u = 2*(u 4-EulerAdmissible.pressure u) := by
  dsimp [velocitySquared,EulerAdmissible.pressure]
  field_simp
  ring

theorem velocity_squared_bound (u : State) (hu : u ∈ region) : velocitySquared u ≤ 30 := by
  have hr := (region_admissible u hu).1
  have hn : 0 ≤ velocitySquared u := by dsimp [velocitySquared]; positivity
  have he := kinetic_pressure_identity u (ne_of_gt hr)
  have hm := mul_le_mul_of_nonneg_right hu.1 hn
  nlinarith [hu.2.2.1,hu.2.2.2]

theorem conservative_hessian_squares (u k : State) (hu : EulerAdmissible.Admissible u) :
    conservativeHessian u k = (k 0)^2/u 0+u 0*(thermalShift u k)^2+
      shiftedMomentumSquared u k/EulerAdmissible.pressure u := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  dsimp [conservativeHessian,hessianForm,toPrimitive,primitiveD,thermalShift,shiftedMomentumSquared]
  field_simp
  ring

theorem hessian_components (u k : State) (hu : u ∈ region) :
    (k 0)^2 ≤ 4*conservativeHessian u k ∧
    shiftedMomentumSquared u k ≤ 4*conservativeHessian u k ∧
    (thermalShift u k)^2 ≤ 4*conservativeHessian u k := by
  have hadm := region_admissible u hu
  have hr := hadm.1
  have h0 : 0 ≤ (k 0)^2/u 0 := by positivity
  have h1 : 0 ≤ u 0*(thermalShift u k)^2 := mul_nonneg hadm.1.le (sq_nonneg _)
  have hy : 0 ≤ shiftedMomentumSquared u k := by dsimp [shiftedMomentumSquared]; positivity
  have h2 : 0 ≤ shiftedMomentumSquared u k/EulerAdmissible.pressure u := div_nonneg hy hadm.2.le
  have he := conservative_hessian_squares u k hadm
  have hEn : 0 ≤ conservativeHessian u k := by linarith
  have hk : (k 0)^2/u 0 ≤ conservativeHessian u k := by linarith
  have hY : shiftedMomentumSquared u k/EulerAdmissible.pressure u ≤ conservativeHessian u k := by linarith
  have hZ : u 0*(thermalShift u k)^2 ≤ conservativeHessian u k := by linarith
  refine ⟨?_,?_,?_⟩
  · have hh := (div_le_iff₀ hadm.1).mp hk
    have hm := mul_le_mul_of_nonneg_right hu.2.1 hEn
    nlinarith
  · have hh := (div_le_iff₀ hadm.2).mp hY
    have hm := mul_le_mul_of_nonneg_right (pressure_upper u hu) hEn
    nlinarith
  · have hm := mul_le_mul_of_nonneg_right hu.1 (sq_nonneg (thermalShift u k))
    nlinarith

def momentumSquared (k : State) : ℝ := k 1^2+k 2^2+k 3^2
def velocityPair (u k : State) : ℝ := (u 1/u 0)*k 1+(u 2/u 0)*k 2+(u 3/u 0)*k 3
def shiftedPair (u k : State) : ℝ :=
  (u 1/u 0)*(k 1-(u 1/u 0)*k 0)+(u 2/u 0)*(k 2-(u 2/u 0)*k 0)+
    (u 3/u 0)*(k 3-(u 3/u 0)*k 0)

theorem three_cauchy (a b c x y z : ℝ) :
    (a*x+b*y+c*z)^2 ≤ (a^2+b^2+c^2)*(x^2+y^2+z^2) := by
  nlinarith [sq_nonneg (a*y-b*x),sq_nonneg (a*z-c*x),sq_nonneg (b*z-c*y)]

theorem three_sum_bound (x y z : ℝ) : (x+y+z)^2 ≤ 3*(x^2+y^2+z^2) := by
  nlinarith [sq_nonneg (x-y),sq_nonneg (x-z),sq_nonneg (y-z)]

theorem size_parts (k : State) : k 0^2 ≤ sizeSquared k ∧ momentumSquared k ≤ sizeSquared k ∧
    k 4^2 ≤ sizeSquared k := by
  dsimp [sizeSquared,momentumSquared]
  constructor
  · nlinarith [sq_nonneg (k 1),sq_nonneg (k 2),sq_nonneg (k 3),sq_nonneg (k 4)]
  constructor
  · nlinarith [sq_nonneg (k 0),sq_nonneg (k 4)]
  · nlinarith [sq_nonneg (k 0),sq_nonneg (k 1),sq_nonneg (k 2),sq_nonneg (k 3)]

theorem velocity_pair_bound (u k : State) (hu : u ∈ region) :
    (velocityPair u k)^2 ≤ 30*momentumSquared k := by
  have hh := three_cauchy (u 1/u 0) (u 2/u 0) (u 3/u 0) (k 1) (k 2) (k 3)
  have hm := mul_le_mul_of_nonneg_right (velocity_squared_bound u hu)
    (show 0 ≤ momentumSquared k by dsimp [momentumSquared]; positivity)
  change (velocityPair u k)^2 ≤ velocitySquared u*momentumSquared k at hh
  exact hh.trans hm

theorem shifted_pair_bound (u k : State) (hu : u ∈ region) :
    (shiftedPair u k)^2 ≤ 30*shiftedMomentumSquared u k := by
  have hh := three_cauchy (u 1/u 0) (u 2/u 0) (u 3/u 0)
    (k 1-(u 1/u 0)*k 0) (k 2-(u 2/u 0)*k 0) (k 3-(u 3/u 0)*k 0)
  have hm := mul_le_mul_of_nonneg_right (velocity_squared_bound u hu)
    (show 0 ≤ shiftedMomentumSquared u k by dsimp [shiftedMomentumSquared]; positivity)
  change (shiftedPair u k)^2 ≤ velocitySquared u*shiftedMomentumSquared u k at hh
  exact hh.trans hm

theorem pressureD_decomposition (u k : State) (hr : u 0 ≠ 0) :
    pressureD u k=k 4-velocityPair u k+(velocitySquared u/2)*k 0 := by
  dsimp [pressureD,velocityPair,velocitySquared]
  field_simp

theorem pressureD_bound (u k : State) (hu : u ∈ region) :
    (pressureD u k)^2 ≤ 768*sizeSquared k := by
  have hadm := region_admissible u hu
  have hparts := size_parts k
  have hvel := velocity_squared_bound u hu
  have hvel0 : 0 ≤ velocitySquared u := by dsimp [velocitySquared]; positivity
  have hkin : (velocitySquared u/2)^2 ≤ 225 := by nlinarith
  have hterm : ((velocitySquared u/2)*k 0)^2 ≤ 225*sizeSquared k := by
    calc
      _ = (velocitySquared u/2)^2*k 0^2 := by ring
      _ ≤ 225*k 0^2 := mul_le_mul_of_nonneg_right hkin (sq_nonneg _)
      _ ≤ _ := mul_le_mul_of_nonneg_left hparts.1 (by norm_num)
  have hpair := (velocity_pair_bound u k hu).trans
    (mul_le_mul_of_nonneg_left hparts.2.1 (by norm_num : (0 : ℝ) ≤ 30))
  have hs := three_sum_bound (k 4) (-velocityPair u k) ((velocitySquared u/2)*k 0)
  rw [pressureD_decomposition u k (ne_of_gt hadm.1)]
  nlinarith [hparts.2.2]

theorem shifted_momentum_bound (u k : State) (hu : u ∈ region) :
    shiftedMomentumSquared u k ≤ 62*sizeSquared k := by
  have he : shiftedMomentumSquared u k ≤ 2*momentumSquared k+2*velocitySquared u*k 0^2 := by
    dsimp [shiftedMomentumSquared,momentumSquared,velocitySquared]
    nlinarith [sq_nonneg (k 1+(u 1/u 0)*k 0),sq_nonneg (k 2+(u 2/u 0)*k 0),
      sq_nonneg (k 3+(u 3/u 0)*k 0)]
  have hparts := size_parts k
  have hm := mul_le_mul_of_nonneg_right (velocity_squared_bound u hu) (sq_nonneg (k 0))
  nlinarith

theorem thermal_shift_bound (u k : State) (hu : u ∈ region) :
    (thermalShift u k)^2 ≤ 24608*sizeSquared k := by
  obtain ⟨hr0,hr4⟩ := EulerCoefficientBounds.reciprocal_bounds (u 0) hu.1
  obtain ⟨hp0,hp4⟩ := EulerCoefficientBounds.reciprocal_bounds (EulerAdmissible.pressure u) hu.2.2.2
  have hr2 : (1/u 0)^2 ≤ 16 := by nlinarith
  have hp2 : (1/EulerAdmissible.pressure u)^2 ≤ 16 := by nlinarith
  have hrterm : (k 0/u 0)^2 ≤ 16*sizeSquared k := by
    calc
      _ = (1/u 0)^2*k 0^2 := by ring
      _ ≤ 16*k 0^2 := mul_le_mul_of_nonneg_right hr2 (sq_nonneg _)
      _ ≤ _ := mul_le_mul_of_nonneg_left (size_parts k).1 (by norm_num)
  have hpterm : (pressureD u k/EulerAdmissible.pressure u)^2 ≤ 12288*sizeSquared k := by
    calc
      _ = (1/EulerAdmissible.pressure u)^2*(pressureD u k)^2 := by ring
      _ ≤ 16*(pressureD u k)^2 := mul_le_mul_of_nonneg_right hp2 (sq_nonneg _)
      _ ≤ 16*(768*sizeSquared k) := mul_le_mul_of_nonneg_left (pressureD_bound u k hu) (by norm_num)
      _ = _ := by ring
  dsimp [thermalShift]
  nlinarith [sq_nonneg (pressureD u k/EulerAdmissible.pressure u+k 0/u 0)]

theorem hessian_upper_bound (u k : State) (hu : u ∈ region) :
    conservativeHessian u k ≤ 100000*sizeSquared k := by
  obtain ⟨hr0,hr4⟩ := EulerCoefficientBounds.reciprocal_bounds (u 0) hu.1
  obtain ⟨hp0,hp4⟩ := EulerCoefficientBounds.reciprocal_bounds (EulerAdmissible.pressure u) hu.2.2.2
  have h0 : k 0^2/u 0 ≤ 4*sizeSquared k := by
    calc
      _ = (1/u 0)*k 0^2 := by ring
      _ ≤ 4*k 0^2 := mul_le_mul_of_nonneg_right hr4 (sq_nonneg _)
      _ ≤ _ := mul_le_mul_of_nonneg_left (size_parts k).1 (by norm_num)
  have h1 : u 0*(thermalShift u k)^2 ≤ 98432*sizeSquared k := by
    calc
      _ ≤ 4*(thermalShift u k)^2 := mul_le_mul_of_nonneg_right hu.2.1 (sq_nonneg _)
      _ ≤ 4*(24608*sizeSquared k) := mul_le_mul_of_nonneg_left (thermal_shift_bound u k hu) (by norm_num)
      _ = _ := by ring
  have h2 : shiftedMomentumSquared u k/EulerAdmissible.pressure u ≤ 248*sizeSquared k := by
    have hy : 0 ≤ shiftedMomentumSquared u k := by dsimp [shiftedMomentumSquared]; positivity
    calc
      _ = (1/EulerAdmissible.pressure u)*shiftedMomentumSquared u k := by ring
      _ ≤ 4*shiftedMomentumSquared u k := mul_le_mul_of_nonneg_right hp4 hy
      _ ≤ 4*(62*sizeSquared k) := mul_le_mul_of_nonneg_left (shifted_momentum_bound u k hu) (by norm_num)
      _ = _ := by ring
  rw [conservative_hessian_squares u k (region_admissible u hu)]
  nlinarith [size_nonnegative k]

theorem momentum_recovery_bound (u k : State) (hu : u ∈ region) :
    momentumSquared k ≤ 248*conservativeHessian u k := by
  obtain ⟨hr,hY,hZ⟩ := hessian_components u k hu
  have he : momentumSquared k ≤ 2*shiftedMomentumSquared u k+2*velocitySquared u*k 0^2 := by
    dsimp [shiftedMomentumSquared,momentumSquared,velocitySquared]
    nlinarith [sq_nonneg (k 1-2*(u 1/u 0)*k 0),sq_nonneg (k 2-2*(u 2/u 0)*k 0),
      sq_nonneg (k 3-2*(u 3/u 0)*k 0)]
  have hm := mul_le_mul_of_nonneg_right (velocity_squared_bound u hu) (sq_nonneg (k 0))
  nlinarith

theorem energy_recovery_identity (u k : State) (hu : EulerAdmissible.Admissible u) :
    k 4=EulerAdmissible.pressure u*thermalShift u k+
      (EulerAdmissible.pressure u/u 0+velocitySquared u/2)*k 0+shiftedPair u k := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  dsimp [thermalShift,pressureD,velocitySquared,shiftedPair]
  field_simp
  all_goals ring

theorem energy_recovery_bound (u k : State) (hu : u ∈ region) :
    k 4^2 ≤ 12084*conservativeHessian u k := by
  have hadm := region_admissible u hu
  obtain ⟨hr,hY,hZ⟩ := hessian_components u k hu
  have hp4 := pressure_upper u hu
  have hp2 : (EulerAdmissible.pressure u)^2 ≤ 16 := by nlinarith [hadm.2]
  have hpdiv : EulerAdmissible.pressure u/u 0 ≤ 16 :=
    (div_le_iff₀ hadm.1).mpr (by nlinarith [hu.1])
  have hpdiv0 : 0 ≤ EulerAdmissible.pressure u/u 0 := div_nonneg hadm.2.le hadm.1.le
  have hvel := velocity_squared_bound u hu
  have hvel0 : 0 ≤ velocitySquared u := by dsimp [velocitySquared]; positivity
  have hcoef : (EulerAdmissible.pressure u/u 0+velocitySquared u/2)^2 ≤ 961 := by nlinarith
  have ht0 : (EulerAdmissible.pressure u*thermalShift u k)^2 ≤ 64*conservativeHessian u k := by
    calc
      _ = (EulerAdmissible.pressure u)^2*(thermalShift u k)^2 := by ring
      _ ≤ 16*(thermalShift u k)^2 := mul_le_mul_of_nonneg_right hp2 (sq_nonneg _)
      _ ≤ 16*(4*conservativeHessian u k) := mul_le_mul_of_nonneg_left hZ (by norm_num)
      _ = _ := by ring
  have ht1 : ((EulerAdmissible.pressure u/u 0+velocitySquared u/2)*k 0)^2 ≤
      3844*conservativeHessian u k := by
    calc
      _ = (EulerAdmissible.pressure u/u 0+velocitySquared u/2)^2*k 0^2 := by ring
      _ ≤ 961*k 0^2 := mul_le_mul_of_nonneg_right hcoef (sq_nonneg _)
      _ ≤ 961*(4*conservativeHessian u k) := mul_le_mul_of_nonneg_left hr (by norm_num)
      _ = _ := by ring
  have ht2 := (shifted_pair_bound u k hu).trans (mul_le_mul_of_nonneg_left hY (by norm_num : (0 : ℝ) ≤ 30))
  have hh := three_sum_bound (EulerAdmissible.pressure u*thermalShift u k)
    ((EulerAdmissible.pressure u/u 0+velocitySquared u/2)*k 0) (shiftedPair u k)
  rw [energy_recovery_identity u k hadm]
  nlinarith

theorem hessian_coercivity (u k : State) (hu : u ∈ region) :
    (1/12500 : ℝ)*sizeSquared k ≤ conservativeHessian u k := by
  have hr := (hessian_components u k hu).1
  have hm := momentum_recovery_bound u k hu
  have he := energy_recovery_bound u k hu
  have hEn := hessian_nonnegative (toPrimitive u) (primitiveD u k)
    (by dsimp [toPrimitive]; exact one_div_pos.mpr (region_admissible u hu).1) (region_admissible u hu).2
  change 0 ≤ conservativeHessian u k at hEn
  dsimp [sizeSquared,momentumSquared] at *
  nlinarith

end EulerPhysicalRegion


-- The complete initial family enters the concrete physical region. This is
-- an initial-data statement, not invariance of the region under Euler evolution.
noncomputable section
namespace EulerInitialRegion
open EulerPhysicalRegion

def density (delta x y z : ℝ) : ℝ := 1+delta*(Real.sin x*Real.sin y*Real.sin z)
def pressure (A x y z : ℝ) : ℝ :=
  1+(A^2/16)*((Real.cos (2*x)+Real.cos (2*y))*(Real.cos (2*z)+2))
def velocity (A x y z : ℝ) : EulerAdmissible.Vec :=
  ![A*Real.sin x*Real.cos y*Real.cos z,-A*Real.cos x*Real.sin y*Real.cos z,0]
def initialState (A delta x y z : ℝ) : EulerAdmissible.State :=
  EulerAdmissible.primitive (density delta x y z) (pressure A x y z) (velocity A x y z)

theorem abs_product_bound (a b : ℝ) (ha : |a| ≤ 1) (hb : |b| ≤ 1) : |a*b| ≤ 1 := by
  simpa only [abs_mul,one_mul] using mul_le_mul ha hb (abs_nonneg b) (by norm_num : (0 : ℝ) ≤ 1)

theorem density_bounds (delta x y z : ℝ) (hd0 : -1/20 ≤ delta) (hd1 : delta ≤ 1/20) :
    19/20 ≤ density delta x y z ∧ density delta x y z ≤ 21/20 := by
  have hd : |delta| ≤ 1/20 := abs_le.mpr ⟨by linarith,hd1⟩
  have hs := abs_product_bound (Real.sin x*Real.sin y) (Real.sin z)
    (abs_product_bound _ _ (Real.abs_sin_le_one x) (Real.abs_sin_le_one y)) (Real.abs_sin_le_one z)
  have hh := mul_le_mul hd hs (abs_nonneg (Real.sin x*Real.sin y*Real.sin z))
    (by norm_num : (0 : ℝ) ≤ 1/20)
  rw [← abs_mul,mul_one] at hh
  obtain ⟨hl,hr⟩ := abs_le.mp hh
  dsimp [density]
  constructor <;> linarith

theorem pressure_bounds (A x y z : ℝ) (hA0 : 1/2 ≤ A) (hA1 : A ≤ 1) :
    5/8 ≤ pressure A x y z ∧ pressure A x y z ≤ 11/8 := by
  have hA : |A| ≤ 1 := abs_le.mpr ⟨by linarith,hA1⟩
  have hA2 : A^2 ≤ 1 := (sq_le_one_iff_abs_le_one A).mpr hA
  have hxy : |Real.cos (2*x)+Real.cos (2*y)| ≤ 2 :=
    (abs_add_le _ _).trans (by linarith [Real.abs_cos_le_one (2*x),Real.abs_cos_le_one (2*y)])
  have hz : |Real.cos (2*z)+2| ≤ 3 := by
    have hh := abs_add_le (Real.cos (2*z)) (2 : ℝ)
    norm_num at hh
    linarith [Real.abs_cos_le_one (2*z)]
  have hprod : |(Real.cos (2*x)+Real.cos (2*y))*(Real.cos (2*z)+2)| ≤ 6 := by
    have hh := mul_le_mul hxy hz (abs_nonneg _) (by norm_num : (0 : ℝ) ≤ 2)
    simpa only [← abs_mul,show (2 : ℝ)*3=6 by norm_num] using hh
  have hterm : |(A^2/16)*((Real.cos (2*x)+Real.cos (2*y))*(Real.cos (2*z)+2))| ≤ 3/8 := by
    rw [abs_mul,abs_of_nonneg (by positivity : 0 ≤ A^2/16)]
    have hh := mul_le_mul (show A^2/16 ≤ 1/16 by linarith) hprod (abs_nonneg _)
      (by norm_num : (0 : ℝ) ≤ 1/16)
    norm_num at hh
    simpa only [abs_mul] using hh
  obtain ⟨hl,hr⟩ := abs_le.mp hterm
  dsimp [pressure]
  constructor <;> linarith

theorem initial_kinetic_bound (A x y z : ℝ) (hA0 : 1/2 ≤ A) (hA1 : A ≤ 1) :
    EulerAdmissible.kinetic (velocity A x y z) ≤ 1 := by
  have hA : |A| ≤ 1 := abs_le.mpr ⟨by linarith,hA1⟩
  have hnA : |-A| ≤ 1 := by simpa only [abs_neg] using hA
  have hx := abs_product_bound _ _
    (abs_product_bound _ _ (abs_product_bound _ _ hA (Real.abs_sin_le_one x)) (Real.abs_cos_le_one y))
    (Real.abs_cos_le_one z)
  have hy := abs_product_bound _ _
    (abs_product_bound _ _ (abs_product_bound _ _ hnA (Real.abs_cos_le_one x)) (Real.abs_sin_le_one y))
    (Real.abs_cos_le_one z)
  have hx2 := (sq_le_one_iff_abs_le_one _).mpr hx
  have hy2 := (sq_le_one_iff_abs_le_one _).mpr hy
  dsimp [EulerAdmissible.kinetic,velocity]
  nlinarith

theorem initial_family_in_region (A delta x y z : ℝ)
    (hA0 : 1/2 ≤ A) (hA1 : A ≤ 1) (hd0 : -1/20 ≤ delta) (hd1 : delta ≤ 1/20) :
    initialState A delta x y z ∈ region := by
  obtain ⟨hr0,hr1⟩ := density_bounds delta x y z hd0 hd1
  obtain ⟨hp0,hp1⟩ := pressure_bounds A x y z hA0 hA1
  have hr : 0 ≤ density delta x y z := by linarith
  have hk := mul_le_mul_of_nonneg_left (initial_kinetic_bound A x y z hA0 hA1) hr
  change 1/4 ≤ density delta x y z ∧ density delta x y z ≤ 4 ∧
    pressure A x y z+density delta x y z*EulerAdmissible.kinetic (velocity A x y z) ≤ 4 ∧
    1/4 ≤ EulerAdmissible.pressure
      (EulerAdmissible.primitive (density delta x y z) (pressure A x y z) (velocity A x y z))
  rw [EulerAdmissible.pressure_primitive]
  refine ⟨by linarith,by linarith,by nlinarith,by linarith⟩

end EulerInitialRegion

-- Explicit derivative and finite-difference bounds for the actual Euler flux
-- on the concrete convex physical region. Constants are intentionally coarse.
noncomputable section
namespace EulerPhysicalFluxBounds
open EulerEntropy EulerEntropyTaylor EulerPhysicalRegion EulerEnergyBounds EulerVectorEstimates
open scoped BigOperators
abbrev State := Fin 5 → ℝ

def normalVelocity (u : State) (d : Fin 3) : ℝ := u ⟨d.val+1,by omega⟩/u 0
def normalShift (u k : State) (d : Fin 3) : ℝ := k ⟨d.val+1,by omega⟩-normalVelocity u d*k 0
def normalVelocityD (u k : State) (d : Fin 3) : ℝ := normalShift u k d/u 0

def fluxD (u k : State) (d : Fin 3) : State :=
  let v := normalVelocity u d
  let dv := normalVelocityD u k d
  ![k ⟨d.val+1,by omega⟩,
    k 1*v+u 1*dv+(if d=0 then pressureD u k else 0),
    k 2*v+u 2*dv+(if d=1 then pressureD u k else 0),
    k 3*v+u 3*dv+(if d=2 then pressureD u k else 0),
    (k 4+pressureD u k)*v+(u 4+EulerAdmissible.pressure u)*dv]

theorem normal_velocity_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : u t 0 ≠ 0) (d : Fin 3) :
    HasDerivAt (fun s => normalVelocity (u s) d) (normalVelocityD (u t) k d) t := by
  have hh := ((hasDerivAt_pi.mp hu) ⟨d.val+1,by omega⟩).div ((hasDerivAt_pi.mp hu) 0) hr
  convert hh using 1
  dsimp [normalVelocityD,normalShift,normalVelocity]
  field_simp

theorem flux_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : u t 0 ≠ 0) (d : Fin 3) :
    HasDerivAt (fun s => EulerAdmissible.eulerFlux (u s) d) (fluxD (u t) k d) t := by
  have hv := normal_velocity_derivative hu hr d
  have hp := pressure_derivative hu hr
  have hif (j : Fin 3) : HasDerivAt (fun s => if d=j then EulerAdmissible.pressure (u s) else 0)
      (if d=j then pressureD (u t) k else 0) t := by
    by_cases h : d=j
    · simpa only [h,if_true] using hp
    · simpa only [h,if_false] using hasDerivAt_const t (0 : ℝ)
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · exact (hasDerivAt_pi.mp hu) ⟨d.val+1,by omega⟩
  · exact (((hasDerivAt_pi.mp hu) 1).mul hv).add (hif 0)
  · exact (((hasDerivAt_pi.mp hu) 2).mul hv).add (hif 1)
  · exact (((hasDerivAt_pi.mp hu) 3).mul hv).add (hif 2)
  · exact (((hasDerivAt_pi.mp hu) 4).add hp).mul hv

theorem component_square_bound (k : State) (j : Fin 5) : k j^2 ≤ sizeSquared k := by
  rw [size_as_sum]
  exact Finset.single_le_sum (fun i _ => sq_nonneg (k i)) (Finset.mem_univ j)

theorem normal_velocity_bound (u : State) (hu : u ∈ region) (d : Fin 3) :
    (normalVelocity u d)^2 ≤ 30 := by
  have hv := velocity_squared_bound u hu
  fin_cases d <;> dsimp [normalVelocity,velocitySquared] at * <;>
    nlinarith [sq_nonneg (u 1/u 0),sq_nonneg (u 2/u 0),sq_nonneg (u 3/u 0)]

theorem normal_shift_bound (u k : State) (hu : u ∈ region) (d : Fin 3) :
    (normalShift u k d)^2 ≤ 62*sizeSquared k := by
  have hy := shifted_momentum_bound u k hu
  fin_cases d <;> dsimp [normalShift,normalVelocity,shiftedMomentumSquared] at * <;>
    nlinarith [sq_nonneg (k 1-(u 1/u 0)*k 0),sq_nonneg (k 2-(u 2/u 0)*k 0),
      sq_nonneg (k 3-(u 3/u 0)*k 0)]

theorem fluxD_momentum_bound (u k : State) (hu : u ∈ region) (d j : Fin 3) :
    (k ⟨j.val+1,by omega⟩*normalVelocity u d+u ⟨j.val+1,by omega⟩*normalVelocityD u k d+
      (if d=j then pressureD u k else 0))^2 ≤ 7974*sizeSquared k := by
  have h0 : (k ⟨j.val+1,by omega⟩*normalVelocity u d)^2 ≤ 30*sizeSquared k := by
    calc
      _ = (normalVelocity u d)^2*k ⟨j.val+1,by omega⟩^2 := by ring
      _ ≤ 30*k ⟨j.val+1,by omega⟩^2 :=
        mul_le_mul_of_nonneg_right (normal_velocity_bound u hu d) (sq_nonneg _)
      _ ≤ _ := mul_le_mul_of_nonneg_left (component_square_bound k _) (by norm_num)
  have h1 : (u ⟨j.val+1,by omega⟩*normalVelocityD u k d)^2 ≤ 1860*sizeSquared k := by
    have he : u ⟨j.val+1,by omega⟩*normalVelocityD u k d=
        normalVelocity u j*normalShift u k d := by dsimp [normalVelocityD,normalVelocity]; ring
    rw [he]
    calc
      _ = (normalVelocity u j)^2*(normalShift u k d)^2 := by ring
      _ ≤ 30*(normalShift u k d)^2 :=
        mul_le_mul_of_nonneg_right (normal_velocity_bound u hu j) (sq_nonneg _)
      _ ≤ 30*(62*sizeSquared k) := mul_le_mul_of_nonneg_left (normal_shift_bound u k hu d) (by norm_num)
      _ = _ := by ring
  have h2 : (if d=j then pressureD u k else 0)^2 ≤ 768*sizeSquared k := by
    by_cases hd : d=j
    · simpa only [hd,if_true] using pressureD_bound u k hu
    · simp only [hd,if_false,zero_pow (by norm_num : (2 : ℕ) ≠ 0)]
      exact mul_nonneg (by norm_num) (size_nonnegative k)
  have hh := three_sum_bound (k ⟨j.val+1,by omega⟩*normalVelocity u d)
    (u ⟨j.val+1,by omega⟩*normalVelocityD u k d) (if d=j then pressureD u k else 0)
  linarith

theorem fluxD_energy_bound (u k : State) (hu : u ∈ region) (d : Fin 3) :
    ((k 4+pressureD u k)*normalVelocity u d+
      (u 4+EulerAdmissible.pressure u)*normalVelocityD u k d)^2 ≤ 219256*sizeSquared k := by
  have hadm := region_admissible u hu
  have hsum : (k 4+pressureD u k)^2 ≤ 1538*sizeSquared k := by
    nlinarith [component_square_bound k 4,pressureD_bound u k hu,sq_nonneg (k 4-pressureD u k)]
  have h0 : ((k 4+pressureD u k)*normalVelocity u d)^2 ≤ 46140*sizeSquared k := by
    calc
      _ = (normalVelocity u d)^2*(k 4+pressureD u k)^2 := by ring
      _ ≤ 30*(k 4+pressureD u k)^2 :=
        mul_le_mul_of_nonneg_right (normal_velocity_bound u hu d) (sq_nonneg _)
      _ ≤ 30*(1538*sizeSquared k) := mul_le_mul_of_nonneg_left hsum (by norm_num)
      _ = _ := by ring
  have hpE : EulerAdmissible.pressure u ≤ u 4 := by
    have hr := hadm.1
    have hn : 0 ≤ (u 1^2+u 2^2+u 3^2)/(2*u 0) := by positivity
    dsimp [EulerAdmissible.pressure]
    linarith
  have hc0 : 0 ≤ (u 4+EulerAdmissible.pressure u)/u 0 := by
    apply div_nonneg _ hadm.1.le
    linarith [hadm.2]
  have hc32 : (u 4+EulerAdmissible.pressure u)/u 0 ≤ 32 :=
    (div_le_iff₀ hadm.1).mpr (by linarith [hu.1,hu.2.2.1,pressure_upper u hu])
  have hc2 : ((u 4+EulerAdmissible.pressure u)/u 0)^2 ≤ 1024 := by nlinarith
  have h1 : ((u 4+EulerAdmissible.pressure u)*normalVelocityD u k d)^2 ≤ 63488*sizeSquared k := by
    calc
      _ = ((u 4+EulerAdmissible.pressure u)/u 0)^2*(normalShift u k d)^2 := by
        dsimp [normalVelocityD]; ring
      _ ≤ 1024*(normalShift u k d)^2 := mul_le_mul_of_nonneg_right hc2 (sq_nonneg _)
      _ ≤ 1024*(62*sizeSquared k) := mul_le_mul_of_nonneg_left (normal_shift_bound u k hu d) (by norm_num)
      _ = _ := by ring
  nlinarith [sq_nonneg ((k 4+pressureD u k)*normalVelocity u d-
    (u 4+EulerAdmissible.pressure u)*normalVelocityD u k d)]

theorem fluxD_bound (u k : State) (hu : u ∈ region) (d : Fin 3) :
    sizeSquared (fluxD u k d) ≤ 250000*sizeSquared k := by
  have h0 := component_square_bound k ⟨d.val+1,by omega⟩
  have h1 := fluxD_momentum_bound u k hu d 0
  have h2 := fluxD_momentum_bound u k hu d 1
  have h3 := fluxD_momentum_bound u k hu d 2
  have h4 := fluxD_energy_bound u k hu d
  change (k 1*normalVelocity u d+u 1*normalVelocityD u k d+
    (if d=0 then pressureD u k else 0))^2 ≤ _ at h1
  change (k 2*normalVelocity u d+u 2*normalVelocityD u k d+
    (if d=1 then pressureD u k else 0))^2 ≤ _ at h2
  change (k 3*normalVelocity u d+u 3*normalVelocityD u k d+
    (if d=2 then pressureD u k else 0))^2 ≤ _ at h3
  change k ⟨d.val+1,by omega⟩^2+
    (k 1*normalVelocity u d+u 1*normalVelocityD u k d+(if d=0 then pressureD u k else 0))^2+
    (k 2*normalVelocity u d+u 2*normalVelocityD u k d+(if d=1 then pressureD u k else 0))^2+
    (k 3*normalVelocity u d+u 3*normalVelocityD u k d+(if d=2 then pressureD u k else 0))^2+
    ((k 4+pressureD u k)*normalVelocity u d+(u 4+EulerAdmissible.pressure u)*normalVelocityD u k d)^2 ≤
      250000*sizeSquared k
  nlinarith [size_nonnegative k]

theorem physical_flux_lipschitz (u v : State) (hu : u ∈ region) (hv : v ∈ region) (d : Fin 3) :
    sizeSquared (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux u d) ≤
      (1200 : ℝ)^2*sizeSquared (v-u) := by
  have hseg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :=
    EulerEntropyRegion.segment_in_region region region_convex u v hu hv t ht
  have hcomponent (j : Fin 5) :
      (EulerAdmissible.eulerFlux v d j-EulerAdmissible.eulerFlux u d j)^2 ≤ 250000*sizeSquared (v-u) := by
    let f := fun t => EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d j
    let df := fun t => fluxD (EulerEntropyConvexity.segment u v t) (v-u) d j
    have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t :=
      (hasDerivAt_pi.mp (flux_derivative (EulerEntropyConvexity.segment_derivative u v t)
        (ne_of_gt (region_admissible _ (hseg t ht)).1) d)) j
    obtain ⟨t,ht,he⟩ := exists_hasDerivAt_eq_slope f df (by norm_num : (0 : ℝ) < 1)
      (fun t ht => (hd t ht).continuousAt.continuousWithinAt)
      (fun t ht => hd t ⟨ht.1.le,ht.2.le⟩)
    simp [f,df,EulerEntropyConvexity.segment] at he
    rw [← he]
    exact (component_square_bound _ j).trans (fluxD_bound _ _ (hseg t ⟨ht.1.le,ht.2.le⟩) d)
  rw [size_as_sum]
  simp only [Pi.sub_apply]
  calc
    _ ≤ ∑ j : Fin 5, 250000*sizeSquared (v-u) := Finset.sum_le_sum (fun j _ => hcomponent j)
    _ = 1250000*sizeSquared (v-u) := by simp; ring
    _ ≤ _ := by nlinarith [size_nonnegative (v-u)]

theorem concrete_region_bounds : EulerEntropyRegion.RegionBounds region 100000 (1/12500) 1200 := by
  exact ⟨region_convex,region_admissible,(fun u hu k => hessian_upper_bound u k hu),
    (fun u hu k => hessian_coercivity u k hu),(fun u hu v hv d => physical_flux_lipschitz u v hu hv d)⟩

theorem region_wave_speed_bound (u : State) (hu : u ∈ region) (d : Fin 3) :
    EulerAdmissible.waveSpeed u d ≤ 12 := by
  have hadm := region_admissible u hu
  have hv2 := normal_velocity_bound u hu d
  have hv : |normalVelocity u d| ≤ 6 := by nlinarith [sq_abs (normalVelocity u d),abs_nonneg (normalVelocity u d)]
  have hc : Real.sqrt (2*EulerAdmissible.pressure u/u 0) ≤ 6 := by
    apply Real.sqrt_le_iff.mpr
    refine ⟨by norm_num,?_⟩
    apply (div_le_iff₀ hadm.1).mpr
    nlinarith [pressure_upper u hu,hu.1]
  have he : EulerAdmissible.fromVelocity u d=normalVelocity u d := by
    fin_cases d <;> rfl
  dsimp [EulerAdmissible.waveSpeed]
  rw [he]
  linarith

theorem regional_global_speed_bound {I : Type*} [Fintype I] [Nonempty I]
    (u : I → State) (hu : ∀ i, u i ∈ region) (d : Fin 3) : EulerAdmissible.globalSpeed u d ≤ 12 := by
  exact (Finset.sup'_le_iff Finset.univ_nonempty _).mpr
    (fun i _ => region_wave_speed_bound (u i) (hu i) d)

theorem coarse_viscosity_requirement (a : ℝ)
    (h : (100000 : ℝ)*(1+1200^2) ≤ a*(1/12500)/2) : 3600002500000000 ≤ a := by
  linarith

-- This rejects these coarse constants as a certificate for the present
-- wave-speed recipe. It does not reject the method's actual entropy behavior.
theorem current_speeds_fail_coarse_viscosity {I : Type*} [Fintype I] [Nonempty I]
    (u : I → State) (hu : ∀ i, u i ∈ region) (d : Fin 3) :
    ¬ ((100000 : ℝ)*(1+1200^2) ≤ EulerAdmissible.globalSpeed u d*(1/12500)/2) := by
  intro h
  have hlo := coarse_viscosity_requirement _ h
  have hhi := regional_global_speed_bound u hu d
  linarith

def restState : State := ![1,0,0,0,1]
def softDirection : State := ![1,0,0,0,2]
def hardDirection : State := ![2,0,0,0,-1]

theorem rest_state_in_region : restState ∈ region := by
  norm_num [restState,region,EulerAdmissible.pressure,Matrix.cons_val_two,Matrix.cons_val_three,
    Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail]

theorem initial_family_contains_rest (A delta : ℝ) :
    EulerInitialRegion.initialState A delta 0 (Real.pi/2) (Real.pi/2)=restState := by
  have hpi : (2 : ℝ)*(Real.pi/2)=Real.pi := by ring
  simp [EulerInitialRegion.initialState,EulerInitialRegion.density,EulerInitialRegion.pressure,
    EulerInitialRegion.velocity,EulerAdmissible.primitive,EulerAdmissible.kinetic,restState,hpi]

theorem rest_hessian_values : conservativeHessian restState softDirection=2 ∧
    sizeSquared softDirection=5 ∧ conservativeHessian restState hardDirection=13 ∧
    sizeSquared hardDirection=5 := by
  norm_num [restState,softDirection,hardDirection,conservativeHessian,hessianForm,toPrimitive,
    primitiveD,pressureD,sizeSquared,EulerAdmissible.pressure,Matrix.cons_val_two,Matrix.cons_val_three,
    Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail]

theorem rest_curvature_constraints (K : Set State) (M lambda L : ℝ)
    (hK : EulerEntropyRegion.RegionBounds K M lambda L) (hrest : restState ∈ K) :
    13/5 ≤ M ∧ lambda ≤ 2/5 := by
  obtain ⟨hs,hss,hh,hhs⟩ := rest_hessian_values
  have hupper := hK.hessian_upper restState hrest hardDirection
  have hlower := hK.hessian_lower restState hrest softDirection
  rw [hh,hhs] at hupper
  rw [hs,hss] at hlower
  constructor <;> linarith

-- Even optimal global Euclidean curvature constants on a region containing
-- this rest state cannot meet this sufficient criterion when a<=12. A sharper
-- entropy estimate is needed; this is not an impossibility theorem for Euler.
theorem global_criterion_obstruction (K : Set State) (M lambda L a : ℝ)
    (hK : EulerEntropyRegion.RegionBounds K M lambda L) (hrest : restState ∈ K)
    (ha0 : 0 ≤ a) (ha12 : a ≤ 12) : ¬ (M*(1+L^2) ≤ a*lambda/2) := by
  obtain ⟨hM,hlambda⟩ := rest_curvature_constraints K M lambda L hK hrest
  have hprod := mul_le_mul_of_nonneg_left hlambda ha0
  have hnonneg := mul_nonneg (by linarith : 0 ≤ M) (sq_nonneg L)
  intro h
  nlinarith

theorem current_speeds_fail_any_region_constants {I : Type*} [Fintype I] [Nonempty I]
    (u : I → State) (hu : ∀ i, u i ∈ region) (M lambda L : ℝ)
    (hK : EulerEntropyRegion.RegionBounds region M lambda L) (d : Fin 3) :
    ¬ (M*(1+L^2) ≤ EulerAdmissible.globalSpeed u d*lambda/2) := by
  exact global_criterion_obstruction region M lambda L _ hK rest_state_in_region
    (EulerAdmissible.globalSpeed_positive u (fun i => region_admissible (u i) (hu i)) d).le
    (regional_global_speed_bound u hu d)

end EulerPhysicalFluxBounds

-- Exact-real logarithmic mean, including its equal-argument branch.
noncomputable section
namespace EulerLogMean

def logMean (a b : ℝ) : ℝ := if a=b then a else (b-a)/(Real.log b-Real.log a)

theorem diagonal (a : ℝ) : logMean a a=a := by simp [logMean]

theorem log_difference_ne (a b : ℝ) (ha : 0 < a) (hb : 0 < b) (hab : a ≠ b) :
    Real.log b-Real.log a ≠ 0 := by
  intro h
  have he := Real.log_injOn_pos hb ha (sub_eq_zero.mp h)
  exact hab he.symm

theorem jump_identity (a b : ℝ) (ha : 0 < a) (hb : 0 < b) :
    logMean a b*(Real.log b-Real.log a)=b-a := by
  by_cases hab : a=b
  · subst b
    simp
  · rw [logMean,if_neg hab]
    exact div_mul_cancel₀ (b-a) (log_difference_ne a b ha hb hab)

theorem symmetric (a b : ℝ) (ha : 0 < a) (hb : 0 < b) : logMean a b=logMean b a := by
  by_cases hab : a=b
  · subst b
    rfl
  · rw [logMean,logMean,if_neg hab,if_neg (Ne.symm hab)]
    apply (div_eq_div_iff (log_difference_ne a b ha hb hab)
      (log_difference_ne b a hb ha (Ne.symm hab))).mpr
    ring

theorem ordered_mean_value (a b : ℝ) (ha : 0 < a) (hab : a < b) :
    ∃ c, a < c ∧ c < b ∧ logMean a b=c := by
  have hb : 0 < b := ha.trans hab
  have hd (t : ℝ) (ht : t ∈ Set.Icc a b) : HasDerivAt Real.log (1/t) t := by
    simpa only [one_div] using Real.hasDerivAt_log (ne_of_gt (lt_of_lt_of_le ha ht.1))
  obtain ⟨c,hc,he⟩ := exists_hasDerivAt_eq_slope Real.log (fun t => 1/t) hab
    (fun t ht => (hd t ht).continuousAt.continuousWithinAt)
    (fun t ht => hd t ⟨ht.1.le,ht.2.le⟩)
  refine ⟨c,hc.1,hc.2,?_⟩
  have hc0 : c ≠ 0 := ne_of_gt (ha.trans hc.1)
  have hba0 : b-a ≠ 0 := sub_ne_zero.mpr (ne_of_gt hab)
  have hx := (div_eq_div_iff hc0 hba0).mp he
  rw [logMean,if_neg (ne_of_lt hab)]
  apply (div_eq_iff (log_difference_ne a b ha hb (ne_of_lt hab))).mpr
  nlinarith

theorem between (a b : ℝ) (ha : 0 < a) (hb : 0 < b) :
    min a b ≤ logMean a b ∧ logMean a b ≤ max a b := by
  rcases lt_trichotomy a b with hab | hab | hab
  · obtain ⟨c,hca,hcb,he⟩ := ordered_mean_value a b ha hab
    rw [he,min_eq_left hab.le,max_eq_right hab.le]
    exact ⟨hca.le,hcb.le⟩
  · subst b
    simp [diagonal]
  · obtain ⟨c,hcb,hca,he⟩ := ordered_mean_value b a hb hab
    rw [symmetric a b ha hb,he,min_eq_right hab.le,max_eq_left hab.le]
    exact ⟨hcb.le,hca.le⟩

theorem positive (a b : ℝ) (ha : 0 < a) (hb : 0 < b) : 0 < logMean a b :=
  (lt_min ha hb).trans_le (between a b ha hb).1

end EulerLogMean

-- Gamma=2, three-dimensional version of the logarithmic-mean flux of
-- Chandrashekar (2013), not a claim of a new numerical-flux invention.
noncomputable section
namespace EulerEntropyConservativeFlux
open EulerEntropy EulerLogMean
open EulerVectorEstimates EulerEnergyBounds
abbrev State := Fin 5 → ℝ
abbrev Vec := Fin 3 → ℝ

def average (a b : ℝ) : ℝ := (a+b)/2
def speedSquared (v : Vec) : ℝ := v 0^2+v 1^2+v 2^2
def parameterState (r beta : ℝ) (v : Vec) : State := EulerAdmissible.primitive r (r/(2*beta)) v
def parameterGradient (r beta : ℝ) (v : Vec) : State :=
  ![2+Real.log 2+Real.log r+Real.log beta-beta*speedSquared v,
    2*beta*v 0,2*beta*v 1,2*beta*v 2,-2*beta]

theorem canonical_parameter_gradient (r beta : ℝ) (v : Vec) (hr : 0 < r) (hb : 0 < beta) :
    gradient (parameterState r beta v)=parameterGradient r beta v := by
  have hr0 := ne_of_gt hr
  have hb0 := ne_of_gt hb
  have hlog : Real.log (r/(2*beta))=Real.log r-Real.log 2-Real.log beta := by
    rw [Real.log_div hr0 (mul_ne_zero (by norm_num) hb0),Real.log_mul (by norm_num) hb0]
    ring
  simp only [parameterState,gradient,EulerAdmissible.pressure_primitive]
  funext i
  fin_cases i
  all_goals dsimp [EulerAdmissible.primitive,EulerAdmissible.kinetic,parameterGradient,speedSquared]
  all_goals try rw [hlog]
  all_goals field_simp
  all_goals ring

def fluxWithMeans (rL rR bL bR lr lb : ℝ) (vL vR : Vec) (d : Fin 3) : State :=
  let vd := average (vL d) (vR d)
  let vx := average (vL 0) (vR 0)
  let vy := average (vL 1) (vR 1)
  let vz := average (vL 2) (vR 2)
  let mass := lr*vd
  let p := average rL rR/(2*average bL bR)
  let mx := mass*vx+(if d=0 then p else 0)
  let my := mass*vy+(if d=1 then p else 0)
  let mz := mass*vz+(if d=2 then p else 0)
  ![mass,mx,my,mz,
    mass*(1/(2*lb)-average (speedSquared vL) (speedSquared vR)/2)+vx*mx+vy*my+vz*mz]

def parameterFlux (rL rR bL bR : ℝ) (vL vR : Vec) (d : Fin 3) : State :=
  fluxWithMeans rL rR bL bR (logMean rL rR) (logMean bL bR) vL vR d

theorem entropy_residual_identity (rL rR bL bR lr lb : ℝ) (vL vR : Vec) (d : Fin 3)
    (hbs : bL+bR ≠ 0) (hlb : lb ≠ 0) :
    dot (parameterGradient rR bR vR-parameterGradient rL bL vL)
      (fluxWithMeans rL rR bL bR lr lb vL vR d)-(rR*vR d-rL*vL d) =
      average (vL d) (vR d)*(lr*(Real.log rR-Real.log rL)-(rR-rL))+
      (lr*average (vL d) (vR d)/lb)*(lb*(Real.log bR-Real.log bL)-(bR-bL)) := by
  fin_cases d
  all_goals dsimp [dot,parameterGradient,fluxWithMeans,average,speedSquared]
  all_goals field_simp
  all_goals ring

theorem parameter_entropy_conservation (rL rR bL bR : ℝ) (vL vR : Vec) (d : Fin 3)
    (hrL : 0 < rL) (hrR : 0 < rR) (hbL : 0 < bL) (hbR : 0 < bR) :
    dot (gradient (parameterState rR bR vR)-gradient (parameterState rL bL vL))
      (parameterFlux rL rR bL bR vL vR d)=rR*vR d-rL*vL d := by
  rw [canonical_parameter_gradient rR bR vR hrR hbR,canonical_parameter_gradient rL bL vL hrL hbL]
  have hh := entropy_residual_identity rL rR bL bR (logMean rL rR) (logMean bL bR) vL vR d
    (ne_of_gt (add_pos hbL hbR)) (ne_of_gt (positive bL bR hbL hbR))
  rw [jump_identity rL rR hrL hrR,jump_identity bL bR hbL hbR,sub_self,sub_self,mul_zero,mul_zero,add_zero] at hh
  exact sub_eq_zero.mp hh

theorem parameter_flux_consistency (r beta : ℝ) (v : Vec) (d : Fin 3)
    (hr : 0 < r) (hb : 0 < beta) :
    parameterFlux r r beta beta v v d=EulerAdmissible.eulerFlux (parameterState r beta v) d := by
  rw [parameterState,EulerAdmissible.flux_primitive r (r/(2*beta)) v hr d]
  have hb0 := ne_of_gt hb
  simp only [parameterFlux,diagonal]
  funext i
  fin_cases d <;> fin_cases i <;>
    dsimp [fluxWithMeans,average,speedSquared,EulerAdmissible.primitiveFlux,EulerAdmissible.kinetic]
  all_goals field_simp
  all_goals ring

def beta (u : State) : ℝ := u 0/(2*EulerAdmissible.pressure u)
def ecFlux (u v : State) (d : Fin 3) : State :=
  parameterFlux (u 0) (v 0) (beta u) (beta v)
    (EulerAdmissible.fromVelocity u) (EulerAdmissible.fromVelocity v) d
def esFlux (u v : State) (a : ℝ) (d : Fin 3) : State := ecFlux u v d-(a/2) • (v-u)

theorem beta_positive (u : State) (hu : EulerAdmissible.Admissible u) : 0 < beta u := by
  exact div_pos hu.1 (mul_pos (by norm_num) hu.2)

theorem parameter_reconstruct (u : State) (hu : EulerAdmissible.Admissible u) :
    parameterState (u 0) (beta u) (EulerAdmissible.fromVelocity u)=u := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  have he : u 0/(2*beta u)=EulerAdmissible.pressure u := by
    dsimp [beta]
    field_simp
  rw [parameterState,he,EulerAdmissible.primitive_reconstruct u hu.1]

theorem momentum_reconstruct (u : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    u 0*EulerAdmissible.fromVelocity u d=u ⟨d.val+1,by omega⟩ := by
  have hr := ne_of_gt hu.1
  fin_cases d <;> dsimp [EulerAdmissible.fromVelocity] <;> field_simp

theorem canonical_entropy_conservation (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v) (d : Fin 3) :
    dot (gradient v-gradient u) (ecFlux u v d)=v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩ := by
  have hh := parameter_entropy_conservation (u 0) (v 0) (beta u) (beta v)
    (EulerAdmissible.fromVelocity u) (EulerAdmissible.fromVelocity v) d hu.1 hv.1
    (beta_positive u hu) (beta_positive v hv)
  rw [parameter_reconstruct u hu,parameter_reconstruct v hv,
    momentum_reconstruct u hu d,momentum_reconstruct v hv d] at hh
  exact hh

theorem canonical_flux_consistency (u : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    ecFlux u u d=EulerAdmissible.eulerFlux u d := by
  have hh := parameter_flux_consistency (u 0) (beta u) (EulerAdmissible.fromVelocity u) d hu.1 (beta_positive u hu)
  rwa [parameter_reconstruct u hu] at hh

theorem dissipative_flux_consistency (u : State) (hu : EulerAdmissible.Admissible u)
    (a : ℝ) (d : Fin 3) : esFlux u u a d=EulerAdmissible.eulerFlux u d := by
  simp only [esFlux,sub_self,smul_zero,sub_zero,canonical_flux_consistency u hu d]

theorem dissipative_entropy_identity (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v) (a : ℝ) (d : Fin 3) :
    dot (gradient v-gradient u) (esFlux u v a d)-
      (v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) =
      -(a/2)*dot (gradient v-gradient u) (v-u) := by
  rw [esFlux,dot_sub_right,dot_smul_right,canonical_entropy_conservation u v hu hv d]
  ring

theorem dissipative_face_bound (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v)
    (a lambda : ℝ) (ha : 0 ≤ a) (d : Fin 3)
    (hH : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      lambda*sizeSquared (v-u) ≤ EulerEntropyTaylor.conservativeHessian
        (EulerEntropyConvexity.segment u v t) (v-u)) :
    dot (gradient v-gradient u) (esFlux u v a d)-
      (v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) ≤ -(a*lambda/2)*sizeSquared (v-u) := by
  rw [dissipative_entropy_identity u v hu hv a d]
  have hh := mul_le_mul_of_nonneg_left (EulerFaceEntropy.gradient_strong_monotonicity u v lambda hu hv hH)
    (by positivity : 0 ≤ a/2)
  nlinarith

theorem face_entropy_stable (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v)
    (a : ℝ) (ha : 0 ≤ a) (d : Fin 3) :
    dot (gradient v-gradient u) (esFlux u v a d)-
      (v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) ≤ 0 := by
  have hH (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
      (0 : ℝ)*sizeSquared (v-u) ≤ EulerEntropyTaylor.conservativeHessian
        (EulerEntropyConvexity.segment u v t) (v-u) := by
    have hs := EulerEntropyConvexity.segment_admissible u v hu hv t ht
    have hh := hessian_nonnegative (toPrimitive (EulerEntropyConvexity.segment u v t))
      (primitiveD (EulerEntropyConvexity.segment u v t) (v-u))
      (by dsimp [toPrimitive]; exact one_div_pos.mpr hs.1) hs.2
    simpa only [zero_mul] using hh
  have hh := dissipative_face_bound u v hu hv a 0 ha d hH
  simpa only [mul_zero,zero_div,neg_zero,zero_mul] using hh

end EulerEntropyConservativeFlux

-- Periodic identities for the alternative EC+LF method. The trial parameter
-- scales a residual computed from the same old state throughout a line search.
noncomputable section
namespace EulerEntropyCandidateStep
open EulerEntropy EulerEntropyConservativeFlux EulerVectorEstimates
open scoped BigOperators Topology
abbrev State := Fin 5 → ℝ

def face {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (d : Fin 3) (i : I) : State := esFlux (u i) (u (neighbor d i)) (a d) d

def increment {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (i : I) : State :=
  -(∑ d, (face u neighbor a d i-face u neighbor a d ((neighbor d).symm i)))

def trial {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (ratio : ℝ) (i : I) : State := u i+ratio • increment u neighbor a i

def totalEntropy {I : Type*} [Fintype I] (u : I → State) : ℝ := ∑ i, entropy (u i)

def dissipation {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) : ℝ :=
  ∑ d, ∑ i, (a d/2)*dot (gradient (u (neighbor d i))-gradient (u i)) (u (neighbor d i)-u i)

theorem increment_sum_zero {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) : ∑ i, increment u neighbor a i=0 := by
  have hd (d : Fin 3) : (∑ i, (face u neighbor a d i-face u neighbor a d ((neighbor d).symm i)))=0 := by
    rw [Finset.sum_sub_distrib]
    have hh := Equiv.sum_comp (neighbor d).symm (face u neighbor a d)
    rw [hh,sub_self]
  simp only [increment,Finset.sum_neg_distrib]
  rw [Finset.sum_comm]
  simp only [hd,Finset.sum_const_zero,neg_zero]

theorem trial_conservation {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio : ℝ) :
    ∑ i, trial u neighbor a ratio i=∑ i, u i := by
  simp only [trial,Finset.sum_add_distrib,← Finset.smul_sum,increment_sum_zero,smul_zero,add_zero]

theorem trial_zero {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) : trial u neighbor a 0=u := by
  funext i
  simp [trial]

theorem entropy_residual_pairing {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    (∑ i, dot (gradient (u i)) (increment u neighbor a i)) = -dissipation u neighbor a := by
  have hface (d : Fin 3) (i : I) : dot (gradient (u (neighbor d i))-gradient (u i)) (face u neighbor a d i) =
      (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩)-
      (a d/2)*dot (gradient (u (neighbor d i))-gradient (u i)) (u (neighbor d i)-u i) := by
    have hh := dissipative_entropy_identity (u i) (u (neighbor d i)) (hu i) (hu _) (a d) d
    change dot _ (esFlux (u i) (u (neighbor d i)) (a d) d)=_
    linarith
  have hp (d : Fin 3) : (∑ i, (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩))=0 := by
    rw [Finset.sum_sub_distrib]
    have hh := Equiv.sum_comp (neighbor d) (fun i => u i ⟨d.val+1,by omega⟩)
    rw [hh,sub_self]
  simp only [increment,dot_neg_right,dot_sum_right,Finset.sum_neg_distrib]
  rw [Finset.sum_comm]
  simp only [EulerFiniteVolumeEntropy.periodic_pairing,neg_neg,
    hface,Finset.sum_sub_distrib,hp,zero_sub,dissipation]

theorem dissipation_nonnegative {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 ≤ a d) :
    0 ≤ dissipation u neighbor a := by
  apply Finset.sum_nonneg
  intro d _
  apply Finset.sum_nonneg
  intro i _
  have hh := face_entropy_stable (u i) (u (neighbor d i)) (hu i) (hu _) (a d) (ha d) d
  rw [dissipative_entropy_identity (u i) (u (neighbor d i)) (hu i) (hu _) (a d) d] at hh
  linarith

theorem gradient_strict_monotonicity (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v) (hne : u ≠ v) :
    0 < dot (gradient v-gradient u) (v-u) := by
  let f := fun t => dot (gradient (EulerEntropyConvexity.segment u v t)) (v-u)
  let df := fun t => EulerEntropyTaylor.conservativeHessian (EulerEntropyConvexity.segment u v t) (v-u)
  have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t := by
    have hs := EulerEntropyConvexity.segment_admissible u v hu hv t ht
    exact entropy_second_directional (EulerEntropyConvexity.segment_derivative u v t) hs.1 hs.2
  obtain ⟨c,hc,he⟩ := exists_hasDerivAt_eq_slope f df (by norm_num : (0 : ℝ) < 1)
    (fun t ht => (hd t ht).continuousAt.continuousWithinAt)
    (fun t ht => hd t ⟨ht.1.le,ht.2.le⟩)
  have hs := EulerEntropyConvexity.segment_admissible u v hu hv c ⟨hc.1.le,hc.2.le⟩
  have hk : primitiveD (EulerEntropyConvexity.segment u v c) (v-u) ≠ 0 := by
    intro hz
    have hh := jacobian_primitiveD (EulerEntropyConvexity.segment u v c) (v-u) (ne_of_gt hs.1)
    rw [hz,EulerConservativePrimitive.jacobian_zero] at hh
    exact hne (sub_eq_zero.mp hh.symm).symm
  have hp := hessian_positive (toPrimitive (EulerEntropyConvexity.segment u v c))
    (primitiveD (EulerEntropyConvexity.segment u v c) (v-u))
    (by dsimp [toPrimitive]; exact one_div_pos.mpr hs.1) hs.2 hk
  have hh : 0 < f 1-f 0 := by
    change 0 < df c at hp
    rw [he] at hp
    simpa only [sub_zero,div_one] using hp
  simpa [f,EulerEntropyConvexity.segment,dot_sub_left] using hh

theorem zero_dissipation_neighbors {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d)
    (hD : dissipation u neighbor a=0) : ∀ d i, u (neighbor d i)=u i := by
  have hn (d : Fin 3) (i : I) :
      0 ≤ (a d/2)*dot (gradient (u (neighbor d i))-gradient (u i)) (u (neighbor d i)-u i) := by
    have hh := face_entropy_stable (u i) (u (neighbor d i)) (hu i) (hu _) (a d) (ha d).le d
    rw [dissipative_entropy_identity (u i) (u (neighbor d i)) (hu i) (hu _) (a d) d] at hh
    linarith
  have hd := (Finset.sum_eq_zero_iff_of_nonneg (fun d (_ : d ∈ Finset.univ) =>
    Finset.sum_nonneg (fun i _ => hn d i))).mp hD
  intro d i
  have hi := (Finset.sum_eq_zero_iff_of_nonneg (fun j (_ : j ∈ Finset.univ) => hn d j)).mp
    (hd d (Finset.mem_univ d)) i (Finset.mem_univ i)
  by_contra hne
  have hs := gradient_strict_monotonicity (u i) (u (neighbor d i)) (hu i) (hu _) (Ne.symm hne)
  have hp := mul_pos (div_pos (ha d) (by norm_num : (0 : ℝ) < 2)) hs
  linarith

theorem zero_dissipation_stationary {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d)
    (hD : dissipation u neighbor a=0) (ratio : ℝ) : trial u neighbor a ratio=u := by
  have hn := zero_dissipation_neighbors u neighbor a hu ha hD
  have hf (d : Fin 3) (i : I) : face u neighbor a d i=EulerAdmissible.eulerFlux (u i) d := by
    rw [face,hn d i,dissipative_flux_consistency (u i) (hu i) (a d) d]
  funext i
  have hz (d : Fin 3) : face u neighbor a d i-face u neighbor a d ((neighbor d).symm i)=0 := by
    rw [hf,hf,← hn d ((neighbor d).symm i)]
    simp
  simp only [trial,increment,hz,Finset.sum_const_zero,neg_zero,smul_zero,add_zero]

theorem trial_derivative {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (i : I) :
    HasDerivAt (fun r => trial u neighbor a r i) (increment u neighbor a i) 0 := by
  have hh := (hasDerivAt_const (0 : ℝ) (u i)).add
    ((hasDerivAt_id (0 : ℝ)).smul_const (increment u neighbor a i))
  simpa only [zero_add,one_smul] using hh

theorem total_entropy_trial_derivative {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    HasDerivAt (fun r => totalEntropy (trial u neighbor a r)) (-dissipation u neighbor a) 0 := by
  have hd (i : I) := entropy_derivative (trial_derivative u neighbor a i)
    (by rw [trial_zero]; exact ne_of_gt (hu i).1)
    (by rw [trial_zero]; exact ne_of_gt (hu i).2)
  have hh := HasDerivAt.fun_sum (fun i (_ : i ∈ Finset.univ) => hd i)
  simp only [trial_zero] at hh
  rwa [entropy_residual_pairing u neighbor a hu] at hh

theorem trial_eventually_admissible {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    ∀ᶠ r in 𝓝 (0 : ℝ), ∀ i, EulerAdmissible.Admissible (trial u neighbor a r i) := by
  apply Filter.eventually_all.mpr
  intro i
  have hd := trial_derivative u neighbor a i
  have hr : ∀ᶠ r in 𝓝 (0 : ℝ), 0 < trial u neighbor a r i 0 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hd) 0).continuousAt (by rw [trial_zero]; exact (hu i).1)
  have hp := (pressure_derivative hd (by rw [trial_zero]; exact ne_of_gt (hu i).1)).continuousAt
  have hpp : ∀ᶠ r in 𝓝 (0 : ℝ), 0 < EulerAdmissible.pressure (trial u neighbor a r i) :=
    continuousAt_const.eventually_lt hp (by rw [trial_zero]; exact (hu i).2)
  exact hr.and hpp

-- A positive dissipation rate guarantees acceptable sufficiently small real
-- trial steps. This does not give a uniform timestep or a floating-point cap.
theorem positive_dissipation_small_step {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (hD : 0 < dissipation u neighbor a) :
    ∃ delta : ℝ, 0 < delta ∧ ∀ r, 0 < r → r < delta →
      (∀ i, EulerAdmissible.Admissible (trial u neighbor a r i)) ∧
      totalEntropy (trial u neighbor a r) ≤ totalEntropy u-(r/2)*dissipation u neighbor a := by
  have hd := total_entropy_trial_derivative u neighbor a hu
  have hs := hd.tendsto_slope_zero_right
  have hlimit : -dissipation u neighbor a < -dissipation u neighbor a/2 := by linarith
  have hev := hs.eventually (Iio_mem_nhds hlimit)
  have he : ∀ᶠ r in 𝓝[>] (0 : ℝ),
      totalEntropy (trial u neighbor a r) ≤ totalEntropy u-(r/2)*dissipation u neighbor a := by
    filter_upwards [hev,self_mem_nhdsWithin] with r hr hrpos
    have hq : (totalEntropy (trial u neighbor a r)-totalEntropy u)/r < -dissipation u neighbor a/2 := by
      simpa only [zero_add,trial_zero,smul_eq_mul,div_eq_mul_inv,mul_comm] using hr
    have hh := (div_lt_iff₀ hrpos).mp hq
    linarith
  have hp : ∀ᶠ r in 𝓝[>] (0 : ℝ), ∀ i, EulerAdmissible.Admissible (trial u neighbor a r i) :=
    (trial_eventually_admissible u neighbor a hu).filter_mono nhdsWithin_le_nhds
  obtain ⟨delta,hdelta,hall⟩ := mem_nhdsGT_iff_exists_Ioo_subset.mp (hp.and he)
  exact ⟨delta,hdelta,fun r hr hrd => hall ⟨hr,hrd⟩⟩

-- Exact-real halving terminates at each admissible finite-grid state with
-- positive diffusion coefficients. There is no uniform retry or time bound.
theorem exists_acceptable_halving {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal) :
    ∃ n : ℕ, (∀ i, EulerAdmissible.Admissible (trial u neighbor a (proposal*(1/2)^n) i)) ∧
      totalEntropy (trial u neighbor a (proposal*(1/2)^n)) ≤
        totalEntropy u-(proposal*(1/2)^n/2)*dissipation u neighbor a := by
  have hnonneg := dissipation_nonnegative u neighbor a hu (fun d => (ha d).le)
  rcases eq_or_lt_of_le hnonneg with hz | hp
  · refine ⟨0,?_⟩
    rw [zero_dissipation_stationary u neighbor a hu ha hz.symm,← hz]
    simpa only [mul_zero,sub_zero,le_refl,and_true] using hu
  · obtain ⟨delta,hdelta,hall⟩ := positive_dissipation_small_step u neighbor a hu hp
    obtain ⟨n,hn⟩ := exists_pow_lt_of_lt_one (div_pos hdelta hproposal) (by norm_num : (1/2 : ℝ) < 1)
    have hr : proposal*(1/2 : ℝ)^n < delta := by
      have hh := (lt_div_iff₀ hproposal).mp hn
      simpa only [mul_comm] using hh
    exact ⟨n,hall _ (mul_pos hproposal (pow_pos (by norm_num) n)) hr⟩

-- A mathematical real-arithmetic model of choosing the first accepted trial.
-- This is not a verified floating-point implementation or a uniform cost bound.
def Acceptable {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio : ℝ) : Prop :=
  (∀ i, EulerAdmissible.Admissible (trial u neighbor a ratio i)) ∧
    totalEntropy (trial u neighbor a ratio) ≤ totalEntropy u-(ratio/2)*dissipation u neighbor a

def halvingIndex {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal) : ℕ := by
  classical
  exact Nat.find (exists_acceptable_halving u neighbor a proposal hu ha hproposal)

def acceptedRatio {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal) : ℝ :=
  proposal*(1/2)^halvingIndex u neighbor a proposal hu ha hproposal

theorem backtracked_step {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal) :
    let ratio := acceptedRatio u neighbor a proposal hu ha hproposal
    0 < ratio ∧ Acceptable u neighbor a ratio ∧
      (∑ i, trial u neighbor a ratio i)=∑ i, u i := by
  classical
  dsimp only
  refine ⟨mul_pos hproposal (pow_pos (by norm_num) _),?_,trial_conservation u neighbor a _⟩
  exact Nat.find_spec (exists_acceptable_halving u neighbor a proposal hu ha hproposal)

theorem earlier_trials_rejected {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal)
    (k : ℕ) (hk : k < halvingIndex u neighbor a proposal hu ha hproposal) :
    ¬ Acceptable u neighbor a (proposal*(1/2)^k) := by
  classical
  exact Nat.find_min (exists_acceptable_halving u neighbor a proposal hu ha hproposal) hk

end EulerEntropyCandidateStep

-- Quantitative directional entropy bounds from the actual conserved state.
noncomputable section
namespace EulerPressurePolynomial
open EulerEntropy EulerEntropyTaylor EulerPhysicalRegion
abbrev State := Fin 5 → ℝ

def quadratic (u : State) : ℝ := 2*u 0*u 4-(u 1^2+u 2^2+u 3^2)
def firstCoefficient (u k : State) : ℝ :=
  2*k 0*u 4+2*u 0*k 4-2*(u 1*k 1+u 2*k 2+u 3*k 3)
def secondCoefficient (k : State) : ℝ := 2*k 0*k 4-(k 1^2+k 2^2+k 3^2)

theorem quadratic_pressure (u : State) (hr : u 0 ≠ 0) :
    quadratic u=2*u 0*EulerAdmissible.pressure u := by
  dsimp [quadratic,EulerAdmissible.pressure]
  field_simp

theorem quadratic_positive (u : State) (hu : EulerAdmissible.Admissible u) : 0 < quadratic u := by
  rw [quadratic_pressure u (ne_of_gt hu.1)]
  exact mul_pos (mul_pos (by norm_num) hu.1) hu.2

theorem admissible_of_quadratic (u : State) (hr : 0 < u 0) (hQ : 0 < quadratic u) :
    EulerAdmissible.Admissible u := by
  refine ⟨hr,?_⟩
  rw [quadratic_pressure u (ne_of_gt hr)] at hQ
  exact (mul_pos_iff_of_pos_left (mul_pos (by norm_num) hr)).mp hQ

theorem quadratic_path (u k : State) (s : ℝ) :
    quadratic (u+s • k)=quadratic u+s*firstCoefficient u k+s^2*secondCoefficient k := by
  dsimp [quadratic,firstCoefficient,secondCoefficient]
  ring

theorem first_coefficient_path (u k : State) (s : ℝ) :
    firstCoefficient (u+s • k) k=firstCoefficient u k+2*s*secondCoefficient k := by
  dsimp [firstCoefficient,secondCoefficient]
  ring

theorem first_coefficient_pressure (u k : State) (hr : u 0 ≠ 0) :
    firstCoefficient u k=2*u 0*pressureD u k+2*EulerAdmissible.pressure u*k 0 := by
  dsimp [firstCoefficient,pressureD,EulerAdmissible.pressure]
  field_simp
  ring

theorem hessian_polynomial (u k : State) (hu : EulerAdmissible.Admissible u) :
    conservativeHessian u k=3*k 0^2/u 0-2*k 0*firstCoefficient u k/quadratic u-
      2*u 0*secondCoefficient k/quadratic u+u 0*(firstCoefficient u k/quadratic u)^2 := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  rw [conservative_hessian_squares u k hu,quadratic_pressure u hr,first_coefficient_pressure u k hr]
  dsimp [thermalShift,shiftedMomentumSquared,secondCoefficient,pressureD]
  field_simp
  ring

theorem hessian_smul (u k : State) (s : ℝ) (hu : EulerAdmissible.Admissible u) :
    conservativeHessian u (s • k)=s^2*conservativeHessian u k := by
  rw [hessian_polynomial u (s • k) hu,hessian_polynomial u k hu]
  dsimp [firstCoefficient,secondCoefficient]
  ring

def firstBound (u k : State) : ℝ := |firstCoefficient u k|+2*|secondCoefficient k|
def curvatureBound (u k : State) : ℝ :=
  6*k 0^2/u 0+4*|k 0| *firstBound u k/quadratic u+
    6*u 0*|secondCoefficient k|/quadratic u+6*u 0*(firstBound u k/quadratic u)^2

theorem first_bound_nonnegative (u k : State) : 0 ≤ firstBound u k := by
  dsimp [firstBound]
  positivity

theorem curvature_bound_nonnegative (u k : State) (hu : EulerAdmissible.Admissible u) :
    0 ≤ curvatureBound u k := by
  have hr := hu.1
  have hQ := quadratic_positive u hu
  have hf := first_bound_nonnegative u k
  dsimp [curvatureBound]
  positivity

theorem path_density_bounds (u k : State) (s : ℝ) (hs : 0 ≤ s)
    (hsmall : s*|k 0| ≤ u 0/2) :
    u 0/2 ≤ (u+s • k) 0 ∧ (u+s • k) 0 ≤ 3*u 0/2 := by
  have hlow := mul_le_mul_of_nonneg_left (neg_abs_le (k 0)) hs
  have hupp := mul_le_mul_of_nonneg_left (le_abs_self (k 0)) hs
  change u 0/2 ≤ u 0+s*k 0 ∧ u 0+s*k 0 ≤ 3*u 0/2
  constructor <;> linarith

theorem path_quadratic_bound (u k : State) (s : ℝ) (hs : 0 ≤ s) (hs1 : s ≤ 1)
    (hsmall : s*(|firstCoefficient u k|+|secondCoefficient k|) ≤ quadratic u/2) :
    quadratic u/2 ≤ quadratic (u+s • k) := by
  have h1 := mul_le_mul_of_nonneg_left (neg_abs_le (firstCoefficient u k)) hs
  have h2 := mul_le_mul_of_nonneg_left (neg_abs_le (secondCoefficient k)) (sq_nonneg s)
  have hsq : s^2 ≤ s := by nlinarith
  have hm := mul_le_mul_of_nonneg_right hsq (abs_nonneg (secondCoefficient k))
  rw [quadratic_path]
  nlinarith

theorem path_first_bound (u k : State) (s : ℝ) (hs : 0 ≤ s) (hs1 : s ≤ 1) :
    |firstCoefficient (u+s • k) k| ≤ firstBound u k := by
  rw [first_coefficient_path]
  have hh := abs_add_le (firstCoefficient u k) (2*s*secondCoefficient k)
  rw [abs_mul,abs_mul,abs_of_nonneg (by norm_num : (0 : ℝ) ≤ 2),abs_of_nonneg hs] at hh
  have hm := mul_le_mul_of_nonneg_right hs1 (abs_nonneg (secondCoefficient k))
  dsimp [firstBound]
  nlinarith

theorem reciprocal_half_bound (a b : ℝ) (ha : 0 < a) (hab : a/2 ≤ b) : 1/b ≤ 2/a := by
  calc
    _ ≤ 1/(a/2) := one_div_le_one_div_of_le (by positivity) hab
    _ = _ := by ring

theorem scalar_curvature_upper (R Q x y kr c f W : ℝ)
    (hR : 0 < R) (hQ : 0 < Q) (hx : R/2 ≤ x) (hxup : x ≤ 3*R/2)
    (hy : Q/2 ≤ y) (hf : |f| ≤ W) :
    3*kr^2/x-2*kr*f/y-2*x*c/y+x*(f/y)^2 ≤
      6*kr^2/R+4*|kr| *W/Q+6*R*|c|/Q+6*R*(W/Q)^2 := by
  have hxpos : 0 < x := lt_of_lt_of_le (by positivity) hx
  have hypos : 0 < y := lt_of_lt_of_le (by positivity) hy
  have hW : 0 ≤ W := (abs_nonneg f).trans hf
  have hxi := reciprocal_half_bound R x hR hx
  have hyi := reciprocal_half_bound Q y hQ hy
  have h0 : 3*kr^2/x ≤ 6*kr^2/R := by
    calc
      _ = (3*kr^2)*(1/x) := by ring
      _ ≤ (3*kr^2)*(2/R) := mul_le_mul_of_nonneg_left hxi (by positivity)
      _ = _ := by ring
  have hab : -(kr*f) ≤ |kr| *W := by
    calc
      _ ≤ |kr*f| := neg_le_abs _
      _ = |kr| *|f| := abs_mul _ _
      _ ≤ _ := mul_le_mul_of_nonneg_left hf (abs_nonneg kr)
  have h1 : -(2*kr*f/y) ≤ 4*|kr| *W/Q := by
    calc
      _ = (2/y)*(-(kr*f)) := by ring
      _ ≤ (2/y)*(|kr| *W) := mul_le_mul_of_nonneg_left hab (by positivity)
      _ = (2*|kr| *W)*(1/y) := by ring
      _ ≤ (2*|kr| *W)*(2/Q) := mul_le_mul_of_nonneg_left hyi (by positivity)
      _ = _ := by ring
  have h2 : -(2*x*c/y) ≤ 6*R*|c|/Q := by
    calc
      _ = (2*x/y)*(-c) := by ring
      _ ≤ (2*x/y)*|c| := mul_le_mul_of_nonneg_left (neg_le_abs c) (by positivity)
      _ = (2*|c| *(1/y))*x := by ring
      _ ≤ (2*|c| *(1/y))*(3*R/2) := mul_le_mul_of_nonneg_left hxup (by positivity)
      _ = (3*R*|c|)*(1/y) := by ring
      _ ≤ (3*R*|c|)*(2/Q) := mul_le_mul_of_nonneg_left hyi (by positivity)
      _ = _ := by ring
  have hratio : |f/y| ≤ 2*W/Q := by
    calc
      _ = |f| *(1/y) := by rw [abs_div,abs_of_pos hypos]; ring
      _ ≤ W*(1/y) := mul_le_mul_of_nonneg_right hf (by positivity)
      _ ≤ W*(2/Q) := mul_le_mul_of_nonneg_left hyi hW
      _ = _ := by ring
  have hsquare : (f/y)^2 ≤ (2*W/Q)^2 := by
    have hh := mul_self_le_mul_self (abs_nonneg (f/y)) hratio
    nlinarith [sq_abs (f/y)]
  have h3 : x*(f/y)^2 ≤ 6*R*(W/Q)^2 := by
    calc
      _ ≤ (3*R/2)*(f/y)^2 := mul_le_mul_of_nonneg_right hxup (sq_nonneg _)
      _ ≤ (3*R/2)*(2*W/Q)^2 := mul_le_mul_of_nonneg_left hsquare (by positivity)
      _ = _ := by ring
  linarith

theorem path_curvature_bound (u k : State) (hu : EulerAdmissible.Admissible u)
    (s : ℝ) (hs : 0 ≤ s) (hs1 : s ≤ 1)
    (hrsmall : s*|k 0| ≤ u 0/2)
    (hQsmall : s*(|firstCoefficient u k|+|secondCoefficient k|) ≤ quadratic u/2) :
    EulerAdmissible.Admissible (u+s • k) ∧
      conservativeHessian (u+s • k) k ≤ curvatureBound u k := by
  have hr := path_density_bounds u k s hs hrsmall
  have hQ := path_quadratic_bound u k s hs hs1 hQsmall
  have hQpos := quadratic_positive u hu
  have hnew := admissible_of_quadratic (u+s • k)
    (lt_of_lt_of_le (by linarith [hu.1]) hr.1) (lt_of_lt_of_le (by positivity) hQ)
  refine ⟨hnew,?_⟩
  rw [hessian_polynomial _ _ hnew]
  exact scalar_curvature_upper (u 0) (quadratic u) ((u+s • k) 0) (quadratic (u+s • k))
    (k 0) (secondCoefficient k) (firstCoefficient (u+s • k) k) (firstBound u k)
    hu.1 hQpos hr.1 hr.2 hQ (path_first_bound u k s hs hs1)

end EulerPressurePolynomial


-- A state-dependent quantitative bound for the same exact-real halving search.
-- Uniform trajectory and total-work-to-accuracy bounds are still required.
noncomputable section
namespace EulerEntropyStepBounds
open EulerEntropy EulerPressurePolynomial EulerEntropyCandidateStep
open scoped BigOperators
abbrev State := Fin 5 → ℝ

def localRate (u k : State) : ℝ :=
  |k 0|/u 0+(|firstCoefficient u k|+|secondCoefficient k|)/quadratic u

theorem local_rate_nonnegative (u k : State) (hu : EulerAdmissible.Admissible u) :
    0 ≤ localRate u k := by
  have hr := hu.1
  have hQ := quadratic_positive u hu
  dsimp [localRate]
  positivity

def maximumRate {I : Type*} [Fintype I] [Nonempty I] (u k : I → State) : ℝ :=
  Finset.univ.sup' Finset.univ_nonempty (fun i => localRate (u i) (k i))

theorem maximum_rate_bound {I : Type*} [Fintype I] [Nonempty I]
    (u k : I → State) (i : I) : localRate (u i) (k i) ≤ maximumRate u k :=
  Finset.le_sup' (f := fun i => localRate (u i) (k i)) (Finset.mem_univ i)

theorem maximum_rate_nonnegative {I : Type*} [Fintype I] [Nonempty I]
    (u k : I → State) (hu : ∀ i, EulerAdmissible.Admissible (u i)) : 0 ≤ maximumRate u k := by
  obtain ⟨i⟩ := ‹Nonempty I›
  exact (local_rate_nonnegative (u i) (k i) (hu i)).trans (maximum_rate_bound u k i)

def radius {I : Type*} [Fintype I] [Nonempty I] (u k : I → State) : ℝ :=
  1/(2*(1+maximumRate u k))

theorem radius_bounds {I : Type*} [Fintype I] [Nonempty I]
    (u k : I → State) (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    0 < radius u k ∧ radius u k ≤ 1/2 := by
  have hn := maximum_rate_nonnegative u k hu
  constructor
  · dsimp [radius]
    positivity
  · exact one_div_le_one_div_of_le (by norm_num) (by linarith)

theorem radius_times_rate {I : Type*} [Fintype I] [Nonempty I]
    (u k : I → State) (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    radius u k*maximumRate u k ≤ 1/2 := by
  have hn := maximum_rate_nonnegative u k hu
  dsimp [radius]
  calc
    _ = maximumRate u k/(2*(1+maximumRate u k)) := by ring
    _ ≤ _ := (div_le_iff₀ (by positivity : 0 < 2*(1+maximumRate u k))).mpr (by linarith)

theorem trial_path_bound {I : Type*} [Fintype I] [Nonempty I]
    (u k : I → State) (hu : ∀ i, EulerAdmissible.Admissible (u i))
    (s : ℝ) (hs : 0 ≤ s) (hsr : s ≤ radius u k) (i : I) :
    EulerAdmissible.Admissible (u i+s • k i) ∧
      EulerEntropyTaylor.conservativeHessian (u i+s • k i) (k i) ≤ curvatureBound (u i) (k i) := by
  have hlocal := maximum_rate_bound u k i
  have hr := (hu i).1
  have hQ := quadratic_positive (u i) (hu i)
  have hrate : s*localRate (u i) (k i) ≤ 1/2 := by
    calc
      _ ≤ s*maximumRate u k := mul_le_mul_of_nonneg_left hlocal hs
      _ ≤ radius u k*maximumRate u k :=
        mul_le_mul_of_nonneg_right hsr (maximum_rate_nonnegative u k hu)
      _ ≤ _ := radius_times_rate u k hu
  have hparts : s*|k i 0|/u i 0+
      s*(|firstCoefficient (u i) (k i)|+|secondCoefficient (k i)|)/quadratic (u i) ≤ 1/2 := by
    calc
      _ = s*localRate (u i) (k i) := by dsimp [localRate]; ring
      _ ≤ _ := hrate
  have hrsmall : s*|k i 0| ≤ u i 0/2 := by
    have hh : 0 ≤ s*(|firstCoefficient (u i) (k i)|+|secondCoefficient (k i)|)/quadratic (u i) := by positivity
    have hm : s*|k i 0|/u i 0 ≤ 1/2 := by linarith
    have hx := (div_le_iff₀ hr).mp hm
    linarith
  have hQsmall : s*(|firstCoefficient (u i) (k i)|+|secondCoefficient (k i)|) ≤ quadratic (u i)/2 := by
    have hh : 0 ≤ s*|k i 0|/u i 0 := by positivity
    have hm : s*(|firstCoefficient (u i) (k i)|+|secondCoefficient (k i)|)/quadratic (u i) ≤ 1/2 := by
      linarith
    have hx := (div_le_iff₀ hQ).mp hm
    linarith
  exact path_curvature_bound (u i) (k i) (hu i) s hs
    (hsr.trans ((radius_bounds u k hu).2.trans (by norm_num))) hrsmall hQsmall

theorem line_entropy_upper (u k : State) (r B : ℝ) (hr : 0 ≤ r)
    (hpath : ∀ s ∈ Set.Icc (0 : ℝ) r, EulerAdmissible.Admissible (u+s • k) ∧
      EulerEntropyTaylor.conservativeHessian (u+s • k) k ≤ B) :
    entropy (u+r • k) ≤ entropy u+r*dot (gradient u) k+r^2*B/2 := by
  let v := u+r • k
  let f := fun t => entropy (EulerEntropyConvexity.segment u v t)
  let df := fun t => dot (gradient (EulerEntropyConvexity.segment u v t)) (v-u)
  let ddf := fun t => EulerEntropyTaylor.conservativeHessian (EulerEntropyConvexity.segment u v t) (v-u)
  have he (t : ℝ) : EulerEntropyConvexity.segment u v t=u+(t*r) • k := by
    funext j
    dsimp [EulerEntropyConvexity.segment,v]
    ring
  have hs (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : t*r ∈ Set.Icc (0 : ℝ) r := by
    exact ⟨mul_nonneg ht.1 hr,by nlinarith [mul_le_mul_of_nonneg_right ht.2 hr]⟩
  have hadm (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
      EulerAdmissible.Admissible (EulerEntropyConvexity.segment u v t) := by
    rw [he]
    exact (hpath _ (hs t ht)).1
  have hf (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t :=
    entropy_derivative (EulerEntropyConvexity.segment_derivative u v t)
      (ne_of_gt (hadm t ht).1) (ne_of_gt (hadm t ht).2)
  have hdf (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt df (ddf t) t :=
    entropy_second_directional (EulerEntropyConvexity.segment_derivative u v t)
      (hadm t ht).1 (hadm t ht).2
  have hddf (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : ddf t ≤ r^2*B := by
    dsimp only [ddf]
    have hdiff : v-u=r • k := by dsimp [v]; exact add_sub_cancel_left u (r • k)
    rw [hdiff,hessian_smul _ _ r (hadm t ht),he]
    exact mul_le_mul_of_nonneg_left (hpath _ (hs t ht)).2 (sq_nonneg r)
  have hh := EulerEntropyTaylor.scalar_second_derivative_upper f df ddf (r^2*B) hf hdf hddf
  simpa [f,df,v,EulerEntropyConvexity.segment,EulerVectorEstimates.dot_smul_right] using hh

def curvatureTotal {I : Type*} [Fintype I] (u k : I → State) : ℝ :=
  ∑ i, curvatureBound (u i) (k i)

theorem curvature_total_nonnegative {I : Type*} [Fintype I] (u k : I → State)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) : 0 ≤ curvatureTotal u k :=
  Finset.sum_nonneg (fun i _ => curvature_bound_nonnegative (u i) (k i) (hu i))

theorem total_entropy_upper {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (r : ℝ) (hr : 0 ≤ r)
    (hradius : r ≤ radius u (increment u neighbor a)) :
    totalEntropy (trial u neighbor a r) ≤ totalEntropy u-r*dissipation u neighbor a+
      r^2*curvatureTotal u (increment u neighbor a)/2 := by
  have hi (i : I) : entropy (trial u neighbor a r i) ≤ entropy (u i)+
      r*dot (gradient (u i)) (increment u neighbor a i)+r^2*curvatureBound (u i) (increment u neighbor a i)/2 := by
    exact line_entropy_upper (u i) (increment u neighbor a i) r _ hr
      (fun s hs => trial_path_bound u (increment u neighbor a) hu s hs.1 (hs.2.trans hradius) i)
  have hh := Finset.sum_le_sum (fun i (_ : i ∈ Finset.univ) => hi i)
  simp only [Finset.sum_add_distrib,div_eq_mul_inv,← Finset.sum_mul,← Finset.mul_sum,
    entropy_residual_pairing u neighbor a hu] at hh
  exact hh.trans_eq (by dsimp [totalEntropy,curvatureTotal]; ring)

theorem quantitative_acceptance {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (r : ℝ) (hr : 0 ≤ r)
    (hradius : r ≤ radius u (increment u neighbor a))
    (hbudget : r*curvatureTotal u (increment u neighbor a) ≤ dissipation u neighbor a) :
    Acceptable u neighbor a r := by
  refine ⟨fun i => (trial_path_bound u (increment u neighbor a) hu r hr hradius i).1,?_⟩
  have hh := total_entropy_upper u neighbor a hu r hr hradius
  have hm := mul_le_mul_of_nonneg_left hbudget hr
  nlinarith

def stepCap {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) : ℝ :=
  min (radius u (increment u neighbor a))
    (dissipation u neighbor a/(curvatureTotal u (increment u neighbor a)+dissipation u neighbor a))

theorem step_cap_positive {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (hD : 0 < dissipation u neighbor a) :
    0 < stepCap u neighbor a := by
  have hB := curvature_total_nonnegative u (increment u neighbor a) hu
  exact lt_min (radius_bounds u (increment u neighbor a) hu).1 (div_pos hD (by linarith))

theorem below_cap_acceptable {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (hD : 0 < dissipation u neighbor a)
    (r : ℝ) (hr : 0 ≤ r) (hcap : r ≤ stepCap u neighbor a) : Acceptable u neighbor a r := by
  have hB := curvature_total_nonnegative u (increment u neighbor a) hu
  have hh := le_min_iff.mp hcap
  have hbudget := (le_div_iff₀ (by linarith :
    0 < curvatureTotal u (increment u neighbor a)+dissipation u neighbor a)).mp hh.2
  apply quantitative_acceptance u neighbor a hu r hr hh.1
  nlinarith [mul_nonneg hr hD.le]

def sufficientHalvings (proposal cap : ℝ) : ℕ := Nat.clog 2 (Nat.ceil (proposal/cap))

theorem sufficient_halvings_bound (proposal cap : ℝ) (hcap : 0 < cap) :
    proposal*(1/2 : ℝ)^sufficientHalvings proposal cap ≤ cap := by
  have hc : (Nat.ceil (proposal/cap) : ℝ) ≤ (2 : ℝ)^sufficientHalvings proposal cap := by
    exact_mod_cast Nat.le_pow_clog (by norm_num : 1 < (2 : ℕ)) (Nat.ceil (proposal/cap))
  have hh := (div_le_iff₀ hcap).mp ((Nat.le_ceil (proposal/cap)).trans hc)
  have hp : 0 < (2 : ℝ)^sufficientHalvings proposal cap := by positivity
  calc
    _ = proposal/((2 : ℝ)^sufficientHalvings proposal cap) := by rw [one_div_pow]; ring
    _ ≤ _ := (div_le_iff₀ hp).mpr (by nlinarith)

theorem positive_dissipation_retry_bound {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal)
    (hD : 0 < dissipation u neighbor a) :
    halvingIndex u neighbor a proposal hu ha hproposal ≤
      sufficientHalvings proposal (stepCap u neighbor a) := by
  classical
  apply Nat.find_min'
  exact below_cap_acceptable u neighbor a hu hD _
    (mul_nonneg hproposal.le (pow_nonneg (by norm_num) _))
    (sufficient_halvings_bound proposal _ (step_cap_positive u neighbor a hu hD))

def retryBound {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ) : ℕ :=
  if dissipation u neighbor a=0 then 0 else sufficientHalvings proposal (stepCap u neighbor a)

theorem quantitative_retry_bound {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal) :
    halvingIndex u neighbor a proposal hu ha hproposal ≤ retryBound u neighbor a proposal := by
  classical
  by_cases hD : dissipation u neighbor a=0
  · rw [retryBound,if_pos hD]
    apply Nat.find_min'
    rw [zero_dissipation_stationary u neighbor a hu ha hD,hD]
    simpa only [mul_zero,sub_zero,le_refl,and_true] using hu
  · rw [retryBound,if_neg hD]
    exact positive_dissipation_retry_bound u neighbor a proposal hu ha hproposal
      (lt_of_le_of_ne (dissipation_nonnegative u neighbor a hu (fun d => (ha d).le)) (Ne.symm hD))

theorem accepted_ratio_lower_bound {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal)
    (hD : 0 < dissipation u neighbor a) :
    min proposal (stepCap u neighbor a/2) ≤ acceptedRatio u neighbor a proposal hu ha hproposal := by
  cases he : halvingIndex u neighbor a proposal hu ha hproposal with
  | zero => simpa only [acceptedRatio,he,pow_zero,mul_one] using min_le_left proposal (stepCap u neighbor a/2)
  | succ m =>
    have hrejected := earlier_trials_rejected u neighbor a proposal hu ha hproposal m (by rw [he]; omega)
    have hprev : stepCap u neighbor a < proposal*(1/2 : ℝ)^m := by
      by_contra hnot
      exact hrejected (below_cap_acceptable u neighbor a hu hD _
        (mul_nonneg hproposal.le (pow_nonneg (by norm_num) _)) (le_of_not_gt hnot))
    have hmin := min_le_right proposal (stepCap u neighbor a/2)
    simp only [acceptedRatio,he,pow_succ]
    linarith

end EulerEntropyStepBounds

-- Consistency bounds for the actual logarithmic-mean numerical flux on the
-- concrete physical region. Region membership during evolution is separate.
noncomputable section
namespace EulerECFluxBounds
open EulerEntropy EulerPhysicalRegion EulerEnergyBounds EulerVectorEstimates
open EulerEntropyConservativeFlux EulerLogMean
abbrev State := Fin 5 → ℝ
abbrev Vec := Fin 3 → ℝ

theorem near_add (a b c d h A B : ℝ) (ha : |a-c| ≤ A*h) (hb : |b-d| ≤ B*h) :
    |(a+b)-(c+d)| ≤ (A+B)*h := by
  have he : (a+b)-(c+d)=(a-c)+(b-d) := by ring
  rw [he]
  have hh := abs_add_le (a-c) (b-d)
  linarith

theorem near_sub (a b c d h A B : ℝ) (ha : |a-c| ≤ A*h) (hb : |b-d| ≤ B*h) :
    |(a-b)-(c-d)| ≤ (A+B)*h := by
  have he : (a-b)-(c-d)=(a-c)-(b-d) := by ring
  rw [he]
  have hh := abs_sub (a-c) (b-d)
  linarith

theorem near_mul (a b c d h A D Ca Cb : ℝ)
    (hA : |a| ≤ A) (hD : |d| ≤ D) (ha : |a-c| ≤ Ca*h) (hb : |b-d| ≤ Cb*h) :
    |a*b-c*d| ≤ (A*Cb+D*Ca)*h := by
  have he : a*b-c*d=a*(b-d)+(a-c)*d := by ring
  have h1 := mul_le_mul hA hb (abs_nonneg (b-d)) ((abs_nonneg a).trans hA)
  have h2 := mul_le_mul ha hD (abs_nonneg d) ((abs_nonneg (a-c)).trans ha)
  rw [he]
  have hh := abs_add_le (a*(b-d)) ((a-c)*d)
  simp only [abs_mul] at hh
  nlinarith

theorem near_inv (b c h m C : ℝ) (hm : 0 < m) (hb : m ≤ b) (hc : m ≤ c)
    (he : |b-c| ≤ C*h) : |1/b-1/c| ≤ (C/m^2)*h := by
  have hbpos := hm.trans_le hb
  have hcpos := hm.trans_le hc
  have hn := (abs_nonneg (b-c)).trans he
  have hprod : m^2 ≤ b*c := by nlinarith [mul_le_mul hb hc hm.le hbpos.le]
  have hid : 1/b-1/c=(c-b)/(b*c) := by field_simp
  rw [hid,abs_div,abs_of_pos (mul_pos hbpos hcpos),abs_sub_comm c b]
  calc
    _ ≤ (C*h)/(b*c) := div_le_div_of_nonneg_right he (mul_pos hbpos hcpos).le
    _ ≤ (C*h)/m^2 := div_le_div_of_nonneg_left hn (sq_pos_of_pos hm) hprod
    _ = _ := by ring

theorem near_div (a b c d h m A Ca Cb : ℝ) (hm : 0 < m) (hb : m ≤ b) (hd : m ≤ d)
    (hA : |a| ≤ A) (ha : |a-c| ≤ Ca*h) (hbd : |b-d| ≤ Cb*h) :
    |a/b-c/d| ≤ (A*Cb/m^2+Ca/m)*h := by
  have hi := near_inv b d h m Cb hm hb hd hbd
  have hdi : |1/d| ≤ 1/m := by
    rw [abs_of_pos (one_div_pos.mpr (hm.trans_le hd))]
    exact one_div_le_one_div_of_le hm hd
  have hh := near_mul a (1/b) c (1/d) h A (1/m) Ca (Cb/m^2) hA hdi ha hi
  calc
    _ = |a*(1/b)-c*(1/d)| := by congr 1; ring
    _ ≤ (A*(Cb/m^2)+(1/m)*Ca)*h := hh
    _ = _ := by ring

theorem average_abs_bound (a b B : ℝ) (ha : |a| ≤ B) (hb : |b| ≤ B) : |average a b| ≤ B := by
  have hh := abs_add_le a b
  dsimp [average]
  rw [abs_div,abs_of_pos (by norm_num : (0 : ℝ) < 2)]
  linarith

theorem average_near_left (a b h C : ℝ) (he : |b-a| ≤ C*h) :
    |average a b-a| ≤ (C/2)*h := by
  have hh : average a b-a=(b-a)/2 := by dsimp [average]; ring
  rw [hh,abs_div,abs_of_pos (by norm_num : (0 : ℝ) < 2)]
  linarith

theorem mean_near_left (a b : ℝ) (ha : 0 < a) (hb : 0 < b) :
    |logMean a b-a| ≤ |b-a| := by
  have hh := between a b ha hb
  rcases le_total a b with hab | hba
  · rw [min_eq_left hab,max_eq_right hab] at hh
    rw [abs_of_nonneg (sub_nonneg.mpr hh.1),abs_of_nonneg (sub_nonneg.mpr hab)]
    linarith
  · rw [min_eq_right hba,max_eq_left hba] at hh
    rw [abs_of_nonpos (sub_nonpos.mpr hh.2),abs_of_nonpos (sub_nonpos.mpr hba)]
    linarith

theorem size_from_components (k : State) (h : ℝ) (_hh : 0 ≤ h) (hk : ∀ j, |k j| ≤ h) :
    sizeSquared k ≤ 5*h^2 := by
  have hj (j : Fin 5) : k j^2 ≤ h^2 := by
    have ht := mul_self_le_mul_self (abs_nonneg (k j)) (hk j)
    nlinarith [sq_abs (k j)]
  dsimp [sizeSquared]
  linarith [hj 0,hj 1,hj 2,hj 3,hj 4]

theorem pressure_difference_bound (u v : State) (hu : u ∈ region) (hv : v ∈ region)
    (h : ℝ) (hh : 0 ≤ h) (hnear : ∀ j, |v j-u j| ≤ h) :
    |EulerAdmissible.pressure v-EulerAdmissible.pressure u| ≤ 64*h := by
  have hsize := size_from_components (v-u) h hh hnear
  let f := fun t => EulerAdmissible.pressure (EulerEntropyConvexity.segment u v t)
  let df := fun t => pressureD (EulerEntropyConvexity.segment u v t) (v-u)
  have hseg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :=
    EulerEntropyRegion.segment_in_region region region_convex u v hu hv t ht
  have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t :=
    pressure_derivative (EulerEntropyConvexity.segment_derivative u v t)
      (ne_of_gt (region_admissible _ (hseg t ht)).1)
  obtain ⟨t,ht,he⟩ := exists_hasDerivAt_eq_slope f df (by norm_num : (0 : ℝ) < 1)
    (fun t ht => (hd t ht).continuousAt.continuousWithinAt)
    (fun t ht => hd t ⟨ht.1.le,ht.2.le⟩)
  have hs := pressureD_bound (EulerEntropyConvexity.segment u v t) (v-u) (hseg t ⟨ht.1.le,ht.2.le⟩)
  have habs : |df t| ≤ 64*h := abs_le_of_sq_le_sq (by dsimp [df]; nlinarith) (by positivity)
  simp [f,EulerEntropyConvexity.segment] at he
  rwa [← he]

theorem momentum_abs_bound (u : State) (hu : u ∈ region) (j : Fin 3) :
    |u ⟨j.val+1,by omega⟩| ≤ 6 := by
  have hr := (region_admissible u hu).1
  have hkin : u 1^2+u 2^2+u 3^2=2*u 0*(u 4-EulerAdmissible.pressure u) := by
    dsimp [EulerAdmissible.pressure]
    field_simp
    ring
  have hm : 2*u 0*(u 4-EulerAdmissible.pressure u) ≤ 30 := by
    have he : u 4-EulerAdmissible.pressure u ≤ 15/4 := by linarith [hu.2.2.1,hu.2.2.2]
    nlinarith [mul_le_mul_of_nonneg_left he hr.le,hu.2.1]
  fin_cases j <;> dsimp
  all_goals apply abs_le_of_sq_le_sq _ (by norm_num : (0 : ℝ) ≤ 6)
  all_goals nlinarith [sq_nonneg (u 1),sq_nonneg (u 2),sq_nonneg (u 3)]

theorem velocity_abs_bound (u : State) (hu : u ∈ region) (j : Fin 3) :
    |EulerAdmissible.fromVelocity u j| ≤ 6 := by
  have hh := EulerPhysicalFluxBounds.normal_velocity_bound u hu j
  have he : EulerAdmissible.fromVelocity u j=EulerPhysicalFluxBounds.normalVelocity u j := by
    fin_cases j <;> rfl
  rw [he]
  exact abs_le_of_sq_le_sq (by linarith) (by norm_num)

theorem velocity_difference_bound (u v : State) (hu : u ∈ region) (hv : v ∈ region)
    (h : ℝ) (hnear : ∀ j, |v j-u j| ≤ h) (j : Fin 3) :
    |EulerAdmissible.fromVelocity v j-EulerAdmissible.fromVelocity u j| ≤ 100*h := by
  have hh := near_div (v ⟨j.val+1,by omega⟩) (v 0) (u ⟨j.val+1,by omega⟩) (u 0)
    h (1/4) 6 1 1 (by norm_num) hv.1 hu.1 (momentum_abs_bound v hv j)
    (by simpa only [one_mul] using hnear ⟨j.val+1,by omega⟩) (by simpa only [one_mul] using hnear 0)
  norm_num at hh
  fin_cases j <;> exact hh

theorem beta_bounds (u : State) (hu : u ∈ region) : 1/32 ≤ beta u ∧ beta u ≤ 8 := by
  have hp := (region_admissible u hu).2
  have hpupper := pressure_upper u hu
  dsimp [beta]
  constructor
  · apply (le_div_iff₀ (by positivity : 0 < 2*EulerAdmissible.pressure u)).mpr
    linarith [hu.1]
  · apply (div_le_iff₀ (by positivity : 0 < 2*EulerAdmissible.pressure u)).mpr
    linarith [hu.2.1,hu.2.2.2]

theorem beta_difference_bound (u v : State) (hu : u ∈ region) (hv : v ∈ region)
    (h : ℝ) (hh : 0 ≤ h) (hnear : ∀ j, |v j-u j| ≤ h) : |beta v-beta u| ≤ 2050*h := by
  have hp := pressure_difference_bound u v hu hv h hh hnear
  have hden : |2*EulerAdmissible.pressure v-2*EulerAdmissible.pressure u| ≤ 128*h := by
    have he : 2*EulerAdmissible.pressure v-2*EulerAdmissible.pressure u=
        2*(EulerAdmissible.pressure v-EulerAdmissible.pressure u) := by ring
    rw [he,abs_mul,abs_of_pos (by norm_num : (0 : ℝ) < 2)]
    linarith
  have hr : |v 0| ≤ 4 := by rw [abs_of_pos (region_admissible v hv).1]; exact hv.2.1
  have he := near_div (v 0) (2*EulerAdmissible.pressure v) (u 0) (2*EulerAdmissible.pressure u)
    h (1/2) 4 1 128 (by norm_num) (by linarith [hv.2.2.2]) (by linarith [hu.2.2.2]) hr
    (by simpa only [one_mul] using hnear 0) hden
  norm_num at he
  exact he

theorem near_scale (s a b h C : ℝ) (he : |a-b| ≤ C*h) :
    |s*a-s*b| ≤ (|s| *C)*h := by
  rw [← mul_sub,abs_mul]
  have hh := mul_le_mul_of_nonneg_left he (abs_nonneg s)
  nlinarith

theorem quotient_abs_bound (a b m A : ℝ) (hm : 0 < m) (hb : m ≤ b) (ha : |a| ≤ A) :
    |a/b| ≤ A/m := by
  rw [abs_div,abs_of_pos (hm.trans_le hb)]
  exact (div_le_div_of_nonneg_right ha (hm.trans_le hb).le).trans
    (div_le_div_of_nonneg_left ((abs_nonneg a).trans ha) hm hb)

structure ParameterRegion (r b : ℝ) (v : Vec) : Prop where
  density_lower : 1/4 ≤ r
  density_upper : r ≤ 4
  beta_lower : 1/32 ≤ b
  beta_upper : b ≤ 8
  speed_bound : speedSquared v ≤ 30

theorem parameter_velocity_abs (r b : ℝ) (v : Vec) (hv : ParameterRegion r b v) (j : Fin 3) :
    |v j| ≤ 6 := by
  have hh := hv.speed_bound
  dsimp [speedSquared] at hh
  have h0 : (v 0)^2 ≤ (6 : ℝ)^2 := by nlinarith [sq_nonneg (v 1),sq_nonneg (v 2)]
  have h1 : (v 1)^2 ≤ (6 : ℝ)^2 := by nlinarith [sq_nonneg (v 0),sq_nonneg (v 2)]
  have h2 : (v 2)^2 ≤ (6 : ℝ)^2 := by nlinarith [sq_nonneg (v 0),sq_nonneg (v 1)]
  fin_cases j
  · exact abs_le_of_sq_le_sq h0 (by norm_num)
  · exact abs_le_of_sq_le_sq h1 (by norm_num)
  · exact abs_le_of_sq_le_sq h2 (by norm_num)

theorem physical_parameter_region (u : State) (hu : u ∈ region) :
    ParameterRegion (u 0) (beta u) (EulerAdmissible.fromVelocity u) := by
  refine ⟨hu.1,hu.2.1,(beta_bounds u hu).1,(beta_bounds u hu).2,?_⟩
  exact velocity_squared_bound u hu

theorem average_diagonal (x : ℝ) : average x x=x := by dsimp [average]; ring

theorem parameter_flux_component_bound (rL rR bL bR : ℝ) (vL vR : Vec) (d : Fin 3)
    (hL : ParameterRegion rL bL vL) (hR : ParameterRegion rR bR vR)
    (h : ℝ) (hh : 0 ≤ h) (hrnear : |rR-rL| ≤ h) (hbnear : |bR-bL| ≤ 2050*h)
    (hvnear : ∀ j, |vR j-vL j| ≤ 100*h) (j : Fin 5) :
    |parameterFlux rL rR bL bR vL vR d j-parameterFlux rL rL bL bL vL vL d j| ≤ 100000000*h := by
  have hrLp : 0 < rL := by linarith [hL.density_lower]
  have hrRp : 0 < rR := by linarith [hR.density_lower]
  have hbLp : 0 < bL := by linarith [hL.beta_lower]
  have hbRp : 0 < bR := by linarith [hR.beta_lower]
  let lr := logMean rL rR
  let lb := logMean bL bR
  let rb := average rL rR
  let bb := average bL bR
  let vb : Vec := fun i => average (vL i) (vR i)
  let mass := lr*vb d
  let mass0 := rL*vL d
  let phat := rb/(2*bb)
  let p0 := rL/(2*bL)
  let mom : Vec := fun i => mass*vb i+(if d=i then phat else 0)
  let mom0 : Vec := fun i => mass0*vL i+(if d=i then p0 else 0)
  let thermal := 1/(2*lb)-average (speedSquared vL) (speedSquared vR)/2
  let thermal0 := 1/(2*bL)-speedSquared vL/2
  have hrLabs : |rL| ≤ 4 := by rw [abs_of_pos hrLp]; exact hL.density_upper
  have hrRabs : |rR| ≤ 4 := by rw [abs_of_pos hrRp]; exact hR.density_upper
  have hlrabs : |lr| ≤ 4 := by
    rw [abs_of_pos (positive rL rR hrLp hrRp)]
    exact (between rL rR hrLp hrRp).2.trans (max_le hL.density_upper hR.density_upper)
  have hlb : 1/32 ≤ lb := (le_min hL.beta_lower hR.beta_lower).trans (between bL bR hbLp hbRp).1
  have hbb : 1/32 ≤ bb := by dsimp [bb,average]; linarith [hL.beta_lower,hR.beta_lower]
  have hrbabs : |rb| ≤ 4 := average_abs_bound rL rR 4 hrLabs hrRabs
  have hlrnear : |lr-rL| ≤ 1*h := by simpa only [one_mul] using (mean_near_left rL rR hrLp hrRp).trans hrnear
  have hlbnear : |lb-bL| ≤ 2050*h := (mean_near_left bL bR hbLp hbRp).trans hbnear
  have hrbnear : |rb-rL| ≤ (1/2)*h := average_near_left rL rR h 1 (by simpa only [one_mul] using hrnear)
  have hbbnear : |2*bb-2*bL| ≤ 2050*h := by
    have he := near_scale 2 bb bL h (2050/2) (average_near_left bL bR h 2050 hbnear)
    norm_num at he
    exact he
  have hlbnear2 : |2*lb-2*bL| ≤ 4100*h := by
    have he := near_scale 2 lb bL h 2050 hlbnear
    norm_num at he
    exact he
  have hvL (i : Fin 3) := parameter_velocity_abs rL bL vL hL i
  have hvR (i : Fin 3) := parameter_velocity_abs rR bR vR hR i
  have hvb (i : Fin 3) : |vb i| ≤ 6 := average_abs_bound _ _ _ (hvL i) (hvR i)
  have hvbn (i : Fin 3) : |vb i-vL i| ≤ 50*h := by
    have he := average_near_left (vL i) (vR i) h 100 (hvnear i)
    norm_num at he
    exact he
  have hmass : |mass| ≤ 24 := by
    dsimp [mass]
    rw [abs_mul]
    have he := mul_le_mul hlrabs (hvb d) (abs_nonneg (vb d)) (by norm_num : (0 : ℝ) ≤ 4)
    linarith
  have hmass0 : |mass0| ≤ 24 := by
    dsimp [mass0]
    rw [abs_mul]
    have he := mul_le_mul hrLabs (hvL d) (abs_nonneg (vL d)) (by norm_num : (0 : ℝ) ≤ 4)
    linarith
  have hmassnear : |mass-mass0| ≤ 206*h := by
    have he := near_mul lr (vb d) rL (vL d) h 4 6 1 50 hlrabs (hvL d) hlrnear (hvbn d)
    norm_num at he
    exact he
  have hphat : |phat| ≤ 64 := by
    have he := quotient_abs_bound rb (2*bb) (1/16) 4 (by norm_num) (by linarith) hrbabs
    norm_num at he
    exact he
  have hp0 : |p0| ≤ 64 := by
    have he := quotient_abs_bound rL (2*bL) (1/16) 4 (by norm_num) (by linarith [hL.beta_lower]) hrLabs
    norm_num at he
    exact he
  have hphatnear : |phat-p0| ≤ 2099208*h := by
    have he := near_div rb (2*bb) rL (2*bL) h (1/16) 4 (1/2) 2050
      (by norm_num) (by linarith) (by linarith [hL.beta_lower]) hrbabs hrbnear hbbnear
    norm_num at he
    exact he
  have hmom0 (i : Fin 3) : |mom0 i| ≤ 208 := by
    have hpif : |(if d=i then p0 else 0)| ≤ 64 := by
      by_cases hd : d=i
      · simpa only [hd,if_true] using hp0
      · simp only [hd,if_false,abs_zero]
        norm_num
    have he := mul_le_mul hmass0 (hvL i) (abs_nonneg (vL i)) (by norm_num : (0 : ℝ) ≤ 24)
    have hs := abs_add_le (mass0*vL i) (if d=i then p0 else 0)
    rw [abs_mul] at hs
    dsimp [mom0]
    linarith
  have hmomnear (i : Fin 3) : |mom i-mom0 i| ≤ 2101644*h := by
    have hprod := near_mul mass (vb i) mass0 (vL i) h 24 6 206 50 hmass (hvL i) hmassnear (hvbn i)
    norm_num at hprod
    have hpif : |(if d=i then phat else 0)-(if d=i then p0 else 0)| ≤ 2099208*h := by
      by_cases hd : d=i
      · simpa only [hd,if_true] using hphatnear
      · simp only [hd,if_false,sub_self,abs_zero]
        positivity
    have he := near_add (mass*vb i) (if d=i then phat else 0) (mass0*vL i) (if d=i then p0 else 0)
      h 2436 2099208 hprod hpif
    norm_num at he
    exact he
  have hsL : |speedSquared vL| ≤ 30 := abs_le.mpr ⟨by dsimp [speedSquared]; nlinarith [sq_nonneg (vL 0),sq_nonneg (vL 1),sq_nonneg (vL 2)],hL.speed_bound⟩
  have hsR : |speedSquared vR| ≤ 30 := abs_le.mpr ⟨by dsimp [speedSquared]; nlinarith [sq_nonneg (vR 0),sq_nonneg (vR 1),sq_nonneg (vR 2)],hR.speed_bound⟩
  have hsbar : |average (speedSquared vL) (speedSquared vR)| ≤ 30 := average_abs_bound _ _ _ hsL hsR
  have hsnear : |speedSquared vR-speedSquared vL| ≤ 3600*h := by
    have hsq (i : Fin 3) : |vR i*vR i-vL i*vL i| ≤ 1200*h := by
      have he := near_mul (vR i) (vR i) (vL i) (vL i) h 6 6 100 100 (hvR i) (hvL i) (hvnear i) (hvnear i)
      norm_num at he
      exact he
    have he := near_add (vR 0*vR 0+vR 1*vR 1) (vR 2*vR 2) (vL 0*vL 0+vL 1*vL 1) (vL 2*vL 2)
      h (1200+1200) 1200 (near_add _ _ _ _ h 1200 1200 (hsq 0) (hsq 1)) (hsq 2)
    have hid : speedSquared vR-speedSquared vL=
        (vR 0*vR 0+vR 1*vR 1+vR 2*vR 2)-(vL 0*vL 0+vL 1*vL 1+vL 2*vL 2) := by
      dsimp [speedSquared]
      ring
    rw [hid]
    convert he using 1
    ring
  have hthermalnear : |thermal-thermal0| ≤ 1050500*h := by
    have hi := near_div 1 (2*lb) 1 (2*bL) h (1/16) 1 0 4100
      (by norm_num) (by linarith) (by linarith [hL.beta_lower]) (by norm_num) (by simp) hlbnear2
    have hs := near_div (average (speedSquared vL) (speedSquared vR)) 2 (speedSquared vL) 2 h 2 30 1800 0
      (by norm_num) (by norm_num) (by norm_num) hsbar
      (by convert average_near_left _ _ h 3600 hsnear using 1; ring) (by simp)
    norm_num1 at hi hs
    have he := near_sub _ _ _ _ h 1049600 900 hi hs
    norm_num at he
    simpa only [thermal,thermal0,one_div,mul_inv_rev] using he
  have hthermal0 : |thermal0| ≤ 31 := by
    have hi := quotient_abs_bound 1 (2*bL) (1/16) 1 (by norm_num)
      (by linarith [hL.beta_lower]) (by norm_num)
    have hs := quotient_abs_bound (speedSquared vL) 2 2 30 (by norm_num) (by norm_num) hsL
    have he := abs_sub (1/(2*bL)) (speedSquared vL/2)
    norm_num1 at hi hs
    dsimp [thermal0]
    linarith only [he,hi,hs]
  have henergy : |(mass*thermal+vb 0*mom 0+vb 1*mom 1+vb 2*mom 2)-
      (mass0*thermal0+vL 0*mom0 0+vL 1*mom0 1+vL 2*mom0 2)| ≤ 63079178*h := by
    have ht := near_mul mass thermal mass0 thermal0 h 24 31 206 1050500 hmass hthermal0 hmassnear hthermalnear
    have hv (i : Fin 3) := near_mul (vb i) (mom i) (vL i) (mom0 i) h 6 208 50 2101644
      (hvb i) (hmom0 i) (hvbn i) (hmomnear i)
    norm_num at ht hv
    have he := near_add _ _ _ _ h ((25218386+12620264)+12620264) 12620264
      (near_add _ _ _ _ h (25218386+12620264) 12620264
        (near_add _ _ _ _ h 25218386 12620264 ht (hv 0)) (hv 1)) (hv 2)
    norm_num at he
    exact he
  simp only [parameterFlux,fluxWithMeans,diagonal,average_diagonal]
  fin_cases j
  · change |mass-mass0| ≤ _
    linarith only [hmassnear,hh]
  · change |mom 0-mom0 0| ≤ _
    linarith only [hmomnear 0,hh]
  · change |mom 1-mom0 1| ≤ _
    linarith only [hmomnear 1,hh]
  · change |mom 2-mom0 2| ≤ _
    linarith only [hmomnear 2,hh]
  · change |(mass*thermal+vb 0*mom 0+vb 1*mom 1+vb 2*mom 2)-
        (mass0*thermal0+vL 0*mom0 0+vL 1*mom0 1+vL 2*mom0 2)| ≤ _
    linarith only [henergy,hh]

theorem flux_component_consistency_bound (u v : State) (hu : u ∈ region) (hv : v ∈ region)
    (d : Fin 3) (j : Fin 5) :
    |ecFlux u v d j-EulerAdmissible.eulerFlux u d j| ≤ 100000000*Real.sqrt (sizeSquared (v-u)) := by
  let h := Real.sqrt (sizeSquared (v-u))
  have hh : 0 ≤ h := Real.sqrt_nonneg _
  have hsq : h^2=sizeSquared (v-u) := Real.sq_sqrt (size_nonnegative (v-u))
  have hnear (j : Fin 5) : |v j-u j| ≤ h := by
    apply abs_le_of_sq_le_sq _ hh
    rw [hsq]
    exact EulerPhysicalFluxBounds.component_square_bound (v-u) j
  have he := parameter_flux_component_bound (u 0) (v 0) (beta u) (beta v)
    (EulerAdmissible.fromVelocity u) (EulerAdmissible.fromVelocity v) d
    (physical_parameter_region u hu) (physical_parameter_region v hv) h hh (hnear 0)
    (beta_difference_bound u v hu hv h hh hnear)
    (fun i => velocity_difference_bound u v hu hv h hnear i) j
  rw [← canonical_flux_consistency u (region_admissible u hu) d]
  exact he

theorem flux_consistency_bound (u v : State) (hu : u ∈ region) (hv : v ∈ region) (d : Fin 3) :
    sizeSquared (ecFlux u v d-EulerAdmissible.eulerFlux u d) ≤
      (300000000 : ℝ)^2*sizeSquared (v-u) := by
  have hh := size_from_components (ecFlux u v d-EulerAdmissible.eulerFlux u d)
    (100000000*Real.sqrt (sizeSquared (v-u))) (by positivity)
    (fun j => flux_component_consistency_bound u v hu hv d j)
  have hs := Real.sq_sqrt (size_nonnegative (v-u))
  nlinarith [size_nonnegative (v-u)]

theorem flux_with_means_swap (rL rR bL bR lr lb : ℝ) (vL vR : Vec) (d : Fin 3) :
    fluxWithMeans rL rR bL bR lr lb vL vR d=fluxWithMeans rR rL bR bL lr lb vR vL d := by
  have hr : average rL rR=average rR rL := by dsimp [average]; ring
  have hb : average bL bR=average bR bL := by dsimp [average]; ring
  have hv (i : Fin 3) : average (vL i) (vR i)=average (vR i) (vL i) := by dsimp [average]; ring
  have hs : average (speedSquared vL) (speedSquared vR)=average (speedSquared vR) (speedSquared vL) := by
    dsimp [average]
    ring
  simp only [fluxWithMeans,hr,hb,hv,hs]

theorem flux_symmetric (u v : State) (hu : EulerAdmissible.Admissible u)
    (hv : EulerAdmissible.Admissible v) (d : Fin 3) : ecFlux u v d=ecFlux v u d := by
  dsimp only [ecFlux,parameterFlux]
  rw [symmetric (u 0) (v 0) hu.1 hv.1,
    symmetric (beta u) (beta v) (beta_positive u hu) (beta_positive v hv)]
  exact flux_with_means_swap _ _ _ _ _ _ _ _ d

theorem flux_consistency_bound_right (u v : State) (hu : u ∈ region) (hv : v ∈ region) (d : Fin 3) :
    sizeSquared (ecFlux u v d-EulerAdmissible.eulerFlux v d) ≤
      (300000000 : ℝ)^2*sizeSquared (v-u) := by
  rw [flux_symmetric u v (region_admissible u hu) (region_admissible v hv),size_sub_comm v u]
  exact flux_consistency_bound v u hv hu d

end EulerECFluxBounds

-- Negative control for a proposed global region-invariance shortcut. These
-- compression states are not the Taylor-Green research family.
noncomputable section
namespace EulerRegionEscape
open EulerEntropyConservativeFlux EulerEntropyCandidateStep EulerPhysicalRegion
abbrev State := Fin 5 → ℝ
abbrev Cell := Fin 3 × (Fin 3 × Fin 3)

def cycle : Equiv.Perm (Fin 3) where
  toFun := ![1,2,0]
  invFun := ![2,0,1]
  left_inv := by intro i; fin_cases i <;> rfl
  right_inv := by intro i; fin_cases i <;> rfl

def neighbor : Fin 3 → Equiv.Perm Cell :=
  ![Equiv.prodCongr cycle (Equiv.refl _),
    Equiv.prodCongr (Equiv.refl _) (Equiv.prodCongr cycle (Equiv.refl _)),
    Equiv.prodCongr (Equiv.refl _) (Equiv.prodCongr (Equiv.refl _) cycle)]

def compression (s : ℝ) : State := ![1,s,0,0,4]
def states (i : Cell) : State := compression ((![1,0,-1] : Fin 3 → ℝ) i.1)
def center : Cell := (1,(0,0))

theorem initial_in_region : ∀ i, states i ∈ region := by
  rintro ⟨i,j⟩
  fin_cases i <;> norm_num [states,compression,region,EulerAdmissible.pressure,
    Matrix.cons_val_two,Matrix.cons_val_three,Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail]

theorem initial_admissible : ∀ i, EulerAdmissible.Admissible (states i) :=
  fun i => region_admissible (states i) (initial_in_region i)

theorem compression_beta (s : ℝ) : beta (compression s)=1/(8-s^2) := by
  have hp : EulerAdmissible.pressure (compression s)=4-s^2/2 := by
    norm_num [compression,EulerAdmissible.pressure,
      Matrix.cons_val_two,Matrix.cons_val_three,Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail]
  change 1/(2*EulerAdmissible.pressure (compression s))=1/(8-s^2)
  rw [hp]
  congr 1
  ring

theorem compression_velocity (s : ℝ) : EulerAdmissible.fromVelocity (compression s)=![s,0,0] := by
  norm_num [compression,EulerAdmissible.fromVelocity,
    Matrix.cons_val_two,Matrix.cons_val_three,Matrix.vecHead,Matrix.vecTail]

theorem compression_face_energy (s t a : ℝ) :
    esFlux (compression s) (compression t) a 0 4 = ((s+t)/2)*
      (1/(2*EulerLogMean.logMean (1/(8-s^2)) (1/(8-t^2)))+
        1/(1/(8-s^2)+1/(8-t^2))+s*t/2) := by
  change ecFlux (compression s) (compression t) 0 4-a/2*(4-4)=_
  rw [sub_self,mul_zero,sub_zero]
  dsimp only [ecFlux]
  rw [compression_beta,compression_beta,compression_velocity,compression_velocity]
  norm_num [compression,parameterFlux,fluxWithMeans,average,speedSquared,EulerLogMean.diagonal,
    Matrix.cons_val_two,Matrix.cons_val_three,Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail,Fin.ext_iff]
  ring

theorem center_energy_increment (a : Fin 3 → ℝ) :
    increment states neighbor a center 4=1/(2*EulerLogMean.logMean (1/7) (1/8))+56/15 := by
  norm_num [increment,face,neighbor,cycle,center,states,Fin.sum_univ_succ,Equiv.prodCongr,
    Matrix.cons_val_two,Matrix.cons_val_three,Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail,Fin.ext_iff]
  rw [compression_face_energy,compression_face_energy]
  norm_num
  rw [EulerLogMean.symmetric (1/8) (1/7) (by norm_num) (by norm_num)]
  ring

theorem positive_step_leaves_region (a : Fin 3 → ℝ) (r : ℝ) (hr : 0 < r) :
    trial states neighbor a r center ∉ region := by
  have hl : 0 < EulerLogMean.logMean (1/7) (1/8) :=
    EulerLogMean.positive _ _ (by norm_num) (by norm_num)
  have hi : 0 < increment states neighbor a center 4 := by
    rw [center_energy_increment]
    positivity
  intro hnew
  have hE := hnew.2.2.1
  change 4+r*increment states neighbor a center 4 ≤ 4 at hE
  nlinarith [mul_pos hr hi]

theorem accepted_step_leaves_region (a : Fin 3 → ℝ) (ha : ∀ d, 0 < a d)
    (proposal : ℝ) (hproposal : 0 < proposal) :
    trial states neighbor a
      (acceptedRatio states neighbor a proposal initial_admissible ha hproposal) center ∉ region := by
  have hh := backtracked_step states neighbor a proposal initial_admissible ha hproposal
  exact positive_step_leaves_region a _ hh.1

end EulerRegionEscape


-- Periodic-grid variance control for the dissipation-to-error argument.
-- This is a spatial identity/estimate, not a continuum existence theorem.
noncomputable section
namespace EulerGridPoincare
open scoped BigOperators
abbrev Cell (n : ℕ) := Fin n × (Fin n × Fin n)

def scalarMean {I : Type*} [Fintype I] (f : I → ℝ) : ℝ := (∑ i, f i)/(Fintype.card I : ℝ)
def scalarVariance {I : Type*} [Fintype I] (f : I → ℝ) : ℝ := ∑ i, (f i-scalarMean f)^2

theorem pair_variance_identity {I : Type*} [Fintype I] [Nonempty I] (f : I → ℝ) :
    (∑ i, ∑ j, (f i-f j)^2)=2*(Fintype.card I : ℝ)*scalarVariance f := by
  have hn : (Fintype.card I : ℝ) ≠ 0 := by exact_mod_cast Fintype.card_ne_zero
  simp only [sub_sq,Finset.sum_add_distrib,Finset.sum_sub_distrib,
    Finset.sum_const,Finset.card_univ,nsmul_eq_mul,← Finset.mul_sum,← Finset.sum_mul,
    scalarVariance,scalarMean]
  field_simp
  ring

open Fin.NatCast in
theorem line_oscillation (n : ℕ) [NeZero n] (f : Fin n → ℝ) (i j : Fin n) :
    (f i-f j)^2 ≤ (n : ℝ)*∑ k : Fin n, (f (k+1)-f k)^2 := by
  have hh := EulerGridSobolev.oscillation (fun k : ℕ => f (Fin.ofNat n k)) n i.val j.val i.isLt j.isLt
  have he : (∑ k ∈ Finset.range n, (f (Fin.ofNat n (k+1))-f (Fin.ofNat n k))^2)=
      ∑ k : Fin n, (f (k+1)-f k)^2 := by
    rw [← Fin.sum_univ_eq_sum_range]
    simp only [Fin.ofNat_eq_cast,Nat.cast_add,Nat.cast_one,Fin.cast_val_eq_self]
  rw [he] at hh
  simpa only [Fin.ofNat_eq_cast,Fin.cast_val_eq_self] using hh

def lineX {n : ℕ} [NeZero n] (f : Cell n → ℝ) (j k : Fin n) : ℝ :=
  ∑ i : Fin n, (f (i+1,(j,k))-f (i,(j,k)))^2
def lineY {n : ℕ} [NeZero n] (f : Cell n → ℝ) (i k : Fin n) : ℝ :=
  ∑ j : Fin n, (f (i,(j+1,k))-f (i,(j,k)))^2
def lineZ {n : ℕ} [NeZero n] (f : Cell n → ℝ) (i j : Fin n) : ℝ :=
  ∑ k : Fin n, (f (i,(j,k+1))-f (i,(j,k)))^2
def scalarEdges {n : ℕ} [NeZero n] (f : Cell n → ℝ) : ℝ :=
  (∑ j, ∑ k, lineX f j k)+(∑ i, ∑ k, lineY f i k)+(∑ i, ∑ j, lineZ f i j)

theorem grid_pair_bound (n : ℕ) [NeZero n] (f : Cell n → ℝ) (x y : Cell n) :
    (f x-f y)^2 ≤ 3*(n : ℝ)*(lineX f x.2.1 x.2.2+lineY f y.1 x.2.2+lineZ f y.1 y.2.1) := by
  rcases x with ⟨i,j,k⟩
  rcases y with ⟨a,b,c⟩
  have hx := line_oscillation n (fun z => f (z,(j,k))) i a
  have hy := line_oscillation n (fun z => f (a,(z,k))) j b
  have hz := line_oscillation n (fun z => f (a,(b,z))) k c
  have hs := EulerPhysicalRegion.three_sum_bound (f (i,(j,k))-f (a,(j,k)))
    (f (a,(j,k))-f (a,(b,k))) (f (a,(b,k))-f (a,(b,c)))
  change (f (i,(j,k))-f (a,(j,k)))^2 ≤ (n : ℝ)*lineX f j k at hx
  change (f (a,(j,k))-f (a,(b,k)))^2 ≤ (n : ℝ)*lineY f a k at hy
  change (f (a,(b,k))-f (a,(b,c)))^2 ≤ (n : ℝ)*lineZ f a b at hz
  dsimp only
  nlinarith

theorem coordinate_pair_sum (n : ℕ) (X Y Z : Fin n → Fin n → ℝ) :
    (∑ x : Cell n, ∑ y : Cell n, (X x.2.1 x.2.2+Y y.1 x.2.2+Z y.1 y.2.1)) =
      (n : ℝ)^4*((∑ i, ∑ j, X i j)+(∑ i, ∑ j, Y i j)+(∑ i, ∑ j, Z i j)) := by
  have hy : (∑ k, ∑ a, Y a k)=∑ a, ∑ k, Y a k := Finset.sum_comm
  simp only [Fintype.sum_prod_type,Finset.sum_add_distrib,Finset.sum_const,
    Finset.card_univ,Fintype.card_prod,Fintype.card_fin,nsmul_eq_mul,← Finset.mul_sum,Cell,Nat.cast_mul]
  rw [hy]
  ring

theorem scalar_poincare (n : ℕ) [NeZero n] (f : Cell n → ℝ) :
    scalarVariance f ≤ (3/2 : ℝ)*(n : ℝ)^2*scalarEdges f := by
  have hh := Finset.sum_le_sum (fun x (_ : x ∈ Finset.univ) =>
    Finset.sum_le_sum (fun y (_ : y ∈ Finset.univ) => grid_pair_bound n f x y))
  simp only [← Finset.mul_sum,coordinate_pair_sum] at hh
  rw [pair_variance_identity f] at hh
  have hcard : (Fintype.card (Cell n) : ℝ)=(n : ℝ)^3 := by simp [Cell,pow_succ]; ring
  rw [hcard] at hh
  have hn : 0 < (n : ℝ) := by exact_mod_cast (NeZero.pos n)
  apply (mul_le_mul_iff_right₀ (pow_pos hn 3)).mp
  dsimp [scalarEdges] at *
  nlinarith only [hh]

def neighbors (n : ℕ) [NeZero n] : Fin 3 → Equiv.Perm (Cell n) :=
  ![Equiv.prodCongr (Equiv.addRight (1 : Fin n)) (Equiv.refl _),
    Equiv.prodCongr (Equiv.refl _) (Equiv.prodCongr (Equiv.addRight (1 : Fin n)) (Equiv.refl _)),
    Equiv.prodCongr (Equiv.refl _) (Equiv.prodCongr (Equiv.refl _) (Equiv.addRight (1 : Fin n)))]

theorem scalar_edges_as_cells (n : ℕ) [NeZero n] (f : Cell n → ℝ) :
    scalarEdges f=∑ d, ∑ x, (f (neighbors n d x)-f x)^2 := by
  have hx : (∑ j, ∑ k, ∑ i, (f (i+1,(j,k))-f (i,(j,k)))^2)=
      ∑ i, ∑ j, ∑ k, (f (i+1,(j,k))-f (i,(j,k)))^2 := by
    calc
      _ = ∑ j, ∑ i, ∑ k, (f (i+1,(j,k))-f (i,(j,k)))^2 :=
        Finset.sum_congr rfl (fun j _ => Finset.sum_comm)
      _ = _ := Finset.sum_comm
  have hy : (∑ i, ∑ k, ∑ j, (f (i,(j+1,k))-f (i,(j,k)))^2)=
      ∑ i, ∑ j, ∑ k, (f (i,(j+1,k))-f (i,(j,k)))^2 :=
    Finset.sum_congr rfl (fun i _ => Finset.sum_comm)
  simp only [scalarEdges,lineX,lineY,lineZ,hx,hy,Fin.sum_univ_succ,neighbors,
    Matrix.cons_val_zero,Equiv.prodCongr_apply,Fintype.sum_prod_type]
  simp [add_assoc]

def meanState {I : Type*} [Fintype I] (u : I → EulerEntropy.State) : EulerEntropy.State :=
  (1/(Fintype.card I : ℝ)) • ∑ i, u i

theorem mean_component {I : Type*} [Fintype I] (u : I → EulerEntropy.State) (j : Fin 5) :
    meanState u j=scalarMean (fun i => u i j) := by
  simp only [meanState,Pi.smul_apply,Finset.sum_apply,smul_eq_mul,scalarMean]
  ring

theorem vector_poincare (n : ℕ) [NeZero n] (u : Cell n → EulerEntropy.State) :
    (∑ i, EulerEnergyBounds.sizeSquared (u i-meanState u)) ≤
      (3/2 : ℝ)*(n : ℝ)^2*EulerFiniteVolumeEntropy.edgeEnergy u (neighbors n) := by
  have hj (j : Fin 5) := scalar_poincare n (fun i => u i j)
  have hh := Finset.sum_le_sum (fun j (_ : j ∈ Finset.univ) => hj j)
  simp only [scalarVariance,← mean_component,scalar_edges_as_cells] at hh
  rw [Finset.sum_comm] at hh
  simp only [← Finset.mul_sum] at hh
  have he : (∑ j : Fin 5, ∑ d : Fin 3, ∑ i : Cell n,
      (u (neighbors n d i) j-u i j)^2)=EulerFiniteVolumeEntropy.edgeEnergy u (neighbors n) := by
    rw [Finset.sum_comm]
    simp only [EulerFiniteVolumeEntropy.edgeEnergy,EulerVectorEstimates.size_as_sum,Pi.sub_apply]
    exact Finset.sum_congr rfl (fun d _ => Finset.sum_comm)
  rw [he] at hh
  simpa only [EulerVectorEstimates.size_as_sum,Pi.sub_apply] using hh

end EulerGridPoincare

-- Quantitative entropy loss of the actual periodic EC+LF update. The bridge
-- to continuous Euler accuracy and the trajectory bounds remain obligations.
noncomputable section
namespace EulerEntropyDecay
open EulerEntropy EulerEntropyCandidateStep EulerGridPoincare
open EulerPhysicalRegion EulerEntropyTaylor EulerEnergyBounds EulerVectorEstimates
open scoped BigOperators
abbrev State := Fin 5 → ℝ

theorem uniform_weights_sum {I : Type*} [Fintype I] [Nonempty I] :
    (∑ _i : I, 1/(Fintype.card I : ℝ))=1 := by
  have hn : (Fintype.card I : ℝ) ≠ 0 := by exact_mod_cast Fintype.card_ne_zero
  simp only [Finset.sum_const,Finset.card_univ,nsmul_eq_mul]
  field_simp

theorem mean_in_region {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (hu : ∀ i, u i ∈ region) : meanState u ∈ region := by
  have hh := region_convex.sum_mem
    (fun _i (_ : _i ∈ Finset.univ) => by positivity : ∀ i ∈ Finset.univ, (0 : ℝ) ≤ 1/(Fintype.card I : ℝ))
    (uniform_weights_sum (I := I)) (fun i _ => hu i)
  simpa only [← Finset.smul_sum,meanState] using hh

theorem sum_centered {I : Type*} [Fintype I] [Nonempty I] (u : I → State) :
    (∑ i, (u i-meanState u))=0 := by
  have hn : (Fintype.card I : ℝ) ≠ 0 := by exact_mod_cast Fintype.card_ne_zero
  funext j
  simp only [Finset.sum_apply,Pi.sub_apply,Finset.sum_sub_distrib,Finset.sum_const,
    Finset.card_univ,nsmul_eq_mul,mean_component,scalarMean,Pi.zero_apply]
  field_simp
  ring

theorem mean_conservation {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (r : ℝ) :
    meanState (trial u neighbor a r)=meanState u := by
  simp only [meanState,trial_conservation]

def entropyExcess {I : Type*} [Fintype I] (u : I → State) : ℝ :=
  totalEntropy u-(Fintype.card I : ℝ)*entropy (meanState u)

theorem entropy_excess_nonnegative {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) : 0 ≤ entropyExcess u := by
  have hn : (Fintype.card I : ℝ) ≠ 0 := by exact_mod_cast Fintype.card_ne_zero
  have hconv := EulerEntropyConvexity.entropy_convex_mixture
    (fun _i : I => 1/(Fintype.card I : ℝ)) u (fun _ => by positivity)
    (uniform_weights_sum (I := I)) hu
  simp only [← Finset.smul_sum,← Finset.mul_sum] at hconv
  have hh : (Fintype.card I : ℝ)*entropy (meanState u) ≤ totalEntropy u := by
    calc
      _ ≤ (Fintype.card I : ℝ)*((1/(Fintype.card I : ℝ))*totalEntropy u) :=
        mul_le_mul_of_nonneg_left hconv (Nat.cast_nonneg _)
      _ = _ := by field_simp
  exact sub_nonneg.mpr hh

theorem entropy_excess_upper {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (hu : ∀ i, u i ∈ region) :
    entropyExcess u ≤ 50000*∑ i, sizeSquared (u i-meanState u) := by
  have hm := mean_in_region u hu
  have hi (i : I) := entropy_taylor_upper (meanState u) (u i)
    (region_admissible _ hm) (region_admissible _ (hu i)) 100000
    (fun t ht => hessian_upper_bound _ _
      (EulerEntropyRegion.segment_in_region region region_convex _ _ hm (hu i) t ht))
  have hlin : (∑ i, dot (gradient (meanState u)) (u i-meanState u))=0 := by
    rw [← dot_sum_right,sum_centered]
    simp [dot]
  have hh := Finset.sum_le_sum (fun i (_ : i ∈ Finset.univ) => hi i)
  simp only [Finset.sum_add_distrib,Finset.sum_const,Finset.card_univ,nsmul_eq_mul,
    ← Finset.mul_sum,hlin,add_zero] at hh
  dsimp [entropyExcess,totalEntropy]
  linarith

theorem entropy_excess_poincare (n : ℕ) [NeZero n] (u : Cell n → State)
    (hu : ∀ i, u i ∈ region) :
    entropyExcess u ≤ 75000*(n : ℝ)^2*EulerFiniteVolumeEntropy.edgeEnergy u (neighbors n) := by
  have hh := entropy_excess_upper u hu
  have hp := mul_le_mul_of_nonneg_left (vector_poincare n u) (by norm_num : (0 : ℝ) ≤ 50000)
  linarith

theorem dissipation_controls_edges {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, u i ∈ region) (ha : ∀ d, 1/4 ≤ a d) :
    (1/100000 : ℝ)*EulerFiniteVolumeEntropy.edgeEnergy u neighbor ≤ dissipation u neighbor a := by
  have hi (d : Fin 3) (i : I) :
      (1/100000 : ℝ)*sizeSquared (u (neighbor d i)-u i) ≤
        (a d/2)*dot (gradient (u (neighbor d i))-gradient (u i)) (u (neighbor d i)-u i) := by
    have hmono := EulerFaceEntropy.gradient_strong_monotonicity (u i) (u (neighbor d i)) (1/12500)
      (region_admissible _ (hu i)) (region_admissible _ (hu _))
      (fun t ht => hessian_coercivity _ _
        (EulerEntropyRegion.segment_in_region region region_convex _ _ (hu i) (hu _) t ht))
    have hmult := mul_le_mul_of_nonneg_left hmono (by linarith [ha d] : 0 ≤ a d/2)
    have hcoeff := mul_le_mul_of_nonneg_right (ha d) (size_nonnegative (u (neighbor d i)-u i))
    nlinarith
  have hh := Finset.sum_le_sum (fun d (_ : d ∈ Finset.univ) =>
    Finset.sum_le_sum (fun i (_ : i ∈ Finset.univ) => hi d i))
  simpa only [EulerFiniteVolumeEntropy.edgeEnergy,dissipation,← Finset.mul_sum] using hh

theorem region_wave_speed_lower (u : State) (hu : u ∈ region) (d : Fin 3) :
    (1/4 : ℝ) ≤ EulerAdmissible.waveSpeed u d := by
  have hphys := region_admissible u hu
  have hQ : (1/8 : ℝ) ≤ 2*EulerAdmissible.pressure u/u 0 := by
    apply (le_div_iff₀ hphys.1).mpr
    linarith [hu.2.1,hu.2.2.2]
  have hQpos : 0 ≤ 2*EulerAdmissible.pressure u/u 0 := by positivity
  have hs := Real.sq_sqrt hQpos
  have hc : (1/4 : ℝ) ≤ Real.sqrt (2*EulerAdmissible.pressure u/u 0) := by
    nlinarith [Real.sqrt_nonneg (2*EulerAdmissible.pressure u/u 0)]
  dsimp [EulerAdmissible.waveSpeed]
  linarith [abs_nonneg (EulerAdmissible.fromVelocity u d)]

theorem computed_speed_lower {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (hu : ∀ i, u i ∈ region) (d : Fin 3) : (1/4 : ℝ) ≤ EulerAdmissible.globalSpeed u d := by
  obtain ⟨i⟩ := ‹Nonempty I›
  exact (region_wave_speed_lower (u i) (hu i) d).trans (EulerAdmissible.globalSpeed_bound u d i)

theorem accepted_step_decay (n : ℕ) [NeZero n] (u : Cell n → State)
    (a : Fin 3 → ℝ) (r : ℝ) (hu : ∀ i, u i ∈ region) (ha : ∀ d, 1/4 ≤ a d)
    (hr : 0 ≤ r) (haccept : Acceptable u (neighbors n) a r) :
    r*entropyExcess u ≤ 15000000000*(n : ℝ)^2*
      (entropyExcess u-entropyExcess (trial u (neighbors n) a r)) := by
  have hR := entropy_excess_poincare n u hu
  have hD := dissipation_controls_edges u (neighbors n) a hu ha
  have hmult := mul_le_mul_of_nonneg_left hD (by positivity : 0 ≤ 7500000000*(n : ℝ)^2)
  have hbudget : entropyExcess u ≤ 7500000000*(n : ℝ)^2*dissipation u (neighbors n) a := by
    nlinarith only [hR,hmult]
  have htime := mul_le_mul_of_nonneg_left hbudget hr
  have hdrop : (r/2)*dissipation u (neighbors n) a ≤
      entropyExcess u-entropyExcess (trial u (neighbors n) a r) := by
    simp only [entropyExcess,mean_conservation]
    linarith [haccept.2]
  have hdropmult := mul_le_mul_of_nonneg_left hdrop (by positivity : 0 ≤ 15000000000*(n : ℝ)^2)
  nlinarith only [htime,hdropmult]

theorem backtracked_step_decay (n : ℕ) [NeZero n] (u : Cell n → State)
    (a : Fin 3 → ℝ) (proposal : ℝ) (hu : ∀ i, u i ∈ region)
    (ha : ∀ d, 1/4 ≤ a d) (hproposal : 0 < proposal) :
    let hphys := fun i => region_admissible (u i) (hu i)
    let hapos := fun d => lt_of_lt_of_le (by norm_num : (0 : ℝ) < 1/4) (ha d)
    let r := acceptedRatio u (neighbors n) a proposal hphys hapos hproposal
    r*entropyExcess u ≤ 15000000000*(n : ℝ)^2*
      (entropyExcess u-entropyExcess (trial u (neighbors n) a r)) := by
  dsimp only
  have hh := backtracked_step u (neighbors n) a proposal
    (fun i => region_admissible (u i) (hu i))
    (fun d => lt_of_lt_of_le (by norm_num : (0 : ℝ) < 1/4) (ha d)) hproposal
  exact accepted_step_decay n u a _ hu ha hh.1.le hh.2.1

theorem scalar_trace_loss (R r : ℕ → ℝ) (m : ℕ) (C : ℝ)
    (hr : ∀ k < m, 0 ≤ r k) (hmono : ∀ k < m, R (k+1) ≤ R k)
    (hstep : ∀ k < m, r k*R k ≤ C*(R k-R (k+1))) :
    (∑ k ∈ Finset.range m, r k)*R m ≤ C*(R 0-R m) := by
  have hc : Antitone (fun k => R (min k m)) := by
    apply antitone_nat_of_succ_le
    intro k
    by_cases hk : k < m
    · simpa only [Nat.min_eq_left (by omega : k+1 ≤ m),Nat.min_eq_left (by omega : k ≤ m)] using hmono k hk
    · simp only [Nat.min_eq_right (by omega : m ≤ k+1),Nat.min_eq_right (by omega : m ≤ k),le_refl]
  have hpoint (k : ℕ) (hk : k ∈ Finset.range m) : r k*R m ≤ C*(R k-R (k+1)) := by
    have hkm := Finset.mem_range.mp hk
    have hR : R m ≤ R k := by
      simpa only [Nat.min_self,Nat.min_eq_left hkm.le] using hc hkm.le
    exact (mul_le_mul_of_nonneg_left hR (hr k hkm)).trans (hstep k hkm)
  have hh := Finset.sum_le_sum hpoint
  rw [← Finset.sum_mul,← Finset.mul_sum,Finset.sum_range_sub'] at hh
  exact hh

theorem trace_mean_conservation {I : Type*} [Fintype I] (u : ℕ → I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : ℕ → Fin 3 → ℝ) (r : ℕ → ℝ) (m : ℕ)
    (hupdate : ∀ k < m, u (k+1)=trial (u k) neighbor (a k) (r k)) :
    meanState (u m)=meanState (u 0) := by
  have hi (k : ℕ) (hk : k ≤ m) : meanState (u k)=meanState (u 0) := by
    induction k with
    | zero => rfl
    | succ k ih =>
      rw [hupdate k (by omega),mean_conservation]
      exact ih (by omega)
  exact hi m le_rfl

theorem actual_trace_entropy_loss (n : ℕ) [NeZero n] (u : ℕ → Cell n → State)
    (a : ℕ → Fin 3 → ℝ) (r : ℕ → ℝ) (m : ℕ)
    (hupdate : ∀ k < m, u (k+1)=trial (u k) (neighbors n) (a k) (r k))
    (hu : ∀ k < m, ∀ i, u k i ∈ region) (ha : ∀ k < m, ∀ d, 1/4 ≤ a k d)
    (hr : ∀ k < m, 0 ≤ r k) (haccept : ∀ k < m, Acceptable (u k) (neighbors n) (a k) (r k)) :
    (∑ k ∈ Finset.range m, r k)*entropyExcess (u m) ≤
      15000000000*(n : ℝ)^2*(totalEntropy (u 0)-totalEntropy (u m)) := by
  have hstep (k : ℕ) (hk : k < m) := accepted_step_decay n (u k) (a k) (r k)
    (hu k hk) (ha k hk) (hr k hk) (haccept k hk)
  have hmono (k : ℕ) (hk : k < m) : entropyExcess (u (k+1)) ≤ entropyExcess (u k) := by
    rw [hupdate k hk]
    have hD := dissipation_nonnegative (u k) (neighbors n) (a k)
      (fun i => region_admissible _ (hu k hk i)) (fun d => by linarith [ha k hk d])
    have htime := mul_nonneg (hr k hk) hD
    simp only [entropyExcess,mean_conservation]
    linarith [(haccept k hk).2]
  have hh := scalar_trace_loss (fun k => entropyExcess (u k)) r m (15000000000*(n : ℝ)^2)
    hr hmono (fun k hk => by dsimp only; rw [hupdate k hk]; exact hstep k hk)
  dsimp only at hh
  have hm := trace_mean_conservation u (neighbors n) a r m hupdate
  have he : entropyExcess (u 0)-entropyExcess (u m)=totalEntropy (u 0)-totalEntropy (u m) := by
    simp only [entropyExcess,hm]
    ring
  rwa [he] at hh

theorem physical_time_entropy_loss (n : ℕ) [NeZero n] (u : ℕ → Cell n → State)
    (a : ℕ → Fin 3 → ℝ) (r : ℕ → ℝ) (m : ℕ) (T : ℝ)
    (hupdate : ∀ k < m, u (k+1)=trial (u k) (neighbors n) (a k) (r k))
    (hu : ∀ k < m, ∀ i, u k i ∈ region) (ha : ∀ k < m, ∀ d, 1/4 ≤ a k d)
    (hr : ∀ k < m, 0 ≤ r k) (haccept : ∀ k < m, Acceptable (u k) (neighbors n) (a k) (r k))
    (hT : (2*Real.pi/(n : ℝ))*(∑ k ∈ Finset.range m, r k)=T) :
    T*entropyExcess (u m) ≤
      (30000000000*Real.pi*(n : ℝ))*(totalEntropy (u 0)-totalEntropy (u m)) := by
  have hn : (n : ℝ) ≠ 0 := by exact_mod_cast (NeZero.ne n)
  have hh := actual_trace_entropy_loss n u a r m hupdate hu ha hr haccept
  have hs := mul_le_mul_of_nonneg_left hh (by positivity : 0 ≤ 2*Real.pi/(n : ℝ))
  calc
    _ = (2*Real.pi/(n : ℝ))*((∑ k ∈ Finset.range m, r k)*entropyExcess (u m)) := by rw [← hT]; ring
    _ ≤ _ := hs
    _ = _ := by field_simp; ring

theorem computed_trace_entropy_loss (n : ℕ) [NeZero n] (u : ℕ → Cell n → State)
    (r : ℕ → ℝ) (m : ℕ) (T : ℝ)
    (hupdate : ∀ k < m, u (k+1)=trial (u k) (neighbors n) (EulerAdmissible.globalSpeed (u k)) (r k))
    (hu : ∀ k < m, ∀ i, u k i ∈ region) (hr : ∀ k < m, 0 ≤ r k)
    (haccept : ∀ k < m, Acceptable (u k) (neighbors n) (EulerAdmissible.globalSpeed (u k)) (r k))
    (hT : (2*Real.pi/(n : ℝ))*(∑ k ∈ Finset.range m, r k)=T) :
    T*entropyExcess (u m) ≤
      (30000000000*Real.pi*(n : ℝ))*(totalEntropy (u 0)-totalEntropy (u m)) := by
  exact physical_time_entropy_loss n u (fun k => EulerAdmissible.globalSpeed (u k)) r m T hupdate hu
    (fun k hk => computed_speed_lower (u k) (hu k hk)) hr haccept hT

end EulerEntropyDecay


-- A direct link between physical entropy and conserved-component L1 errors.
-- This does not supply an exact Euler solution or prove its integral balance.
noncomputable section
namespace EulerEntropyError
open EulerEntropy EulerPhysicalRegion
open scoped BigOperators
abbrev State := Fin 5 → ℝ

theorem box_log_bound (x : ℝ) (hlo : 1/4 ≤ x) (hhi : x ≤ 4) : |Real.log x| ≤ 3 := by
  have hx : 0 < x := by linarith
  have hlog := Real.log_le_sub_one_of_pos hx
  have hi := (EulerCoefficientBounds.reciprocal_bounds x hlo).2
  have hilog := Real.log_le_sub_one_of_pos (inv_pos.mpr hx)
  rw [Real.log_inv] at hilog
  rw [one_div] at hi
  exact abs_le.mpr ⟨by linarith,by linarith⟩

theorem gradient_component_bound (u : State) (hu : u ∈ region) (j : Fin 5) :
    |gradient u j| ≤ 32 := by
  have hphys := region_admissible u hu
  have hrpos := hphys.1
  have hppos := hphys.2
  have hr := ne_of_gt hphys.1
  have hp := ne_of_gt hphys.2
  have hlogr := abs_le.mp (box_log_bound (u 0) hu.1 hu.2.1)
  have hlogp := abs_le.mp (box_log_bound (EulerAdmissible.pressure u) hu.2.2.2 (pressure_upper u hu))
  let q := (u 1^2+u 2^2+u 3^2)/(2*u 0*EulerAdmissible.pressure u)
  have hq0 : 0 ≤ q := by dsimp [q]; positivity
  have he : q=(u 4-EulerAdmissible.pressure u)/EulerAdmissible.pressure u := by
    dsimp [q,EulerAdmissible.pressure]
    field_simp
    ring
  have hq15 : q ≤ 15 := by
    rw [he]
    apply (div_le_iff₀ hphys.2).mpr
    linarith [hu.2.2.1,hu.2.2.2]
  have hm (i : Fin 3) : |u ⟨i.val+1,by omega⟩/EulerAdmissible.pressure u| ≤ 24 := by
    have hh := EulerECFluxBounds.quotient_abs_bound (u ⟨i.val+1,by omega⟩) (EulerAdmissible.pressure u)
      (1/4) 6 (by norm_num) hu.2.2.2 (EulerECFluxBounds.momentum_abs_bound u hu i)
    norm_num at hh
    exact hh
  have hE : |u 0/EulerAdmissible.pressure u| ≤ 16 := by
    have hh := EulerECFluxBounds.quotient_abs_bound (u 0) (EulerAdmissible.pressure u)
      (1/4) 4 (by norm_num) hu.2.2.2 (by rw [abs_of_pos hphys.1]; exact hu.2.1)
    norm_num at hh
    exact hh
  fin_cases j
  · change |2-(Real.log (EulerAdmissible.pressure u)-2*Real.log (u 0))-q| ≤ 32
    exact abs_le.mpr ⟨by linarith,by linarith⟩
  · change |u 1/EulerAdmissible.pressure u| ≤ 32
    exact (hm 0).trans (by norm_num)
  · change |u 2/EulerAdmissible.pressure u| ≤ 32
    exact (hm 1).trans (by norm_num)
  · change |u 3/EulerAdmissible.pressure u| ≤ 32
    exact (hm 2).trans (by norm_num)
  · change |(-u 0)/EulerAdmissible.pressure u| ≤ 32
    rw [neg_div,abs_neg]
    exact hE.trans (by norm_num)

def componentL1 (k : State) : ℝ := ∑ j, |k j|

theorem dot_as_sum (u k : State) : dot u k=∑ j, u j*k j := by
  simp [dot,Fin.sum_univ_succ]
  ring

theorem gradient_pairing_bound (u k : State) (hu : u ∈ region) :
    |dot (gradient u) k| ≤ 32*componentL1 k := by
  rw [dot_as_sum]
  calc
    _ ≤ ∑ j, |gradient u j*k j| := Finset.abs_sum_le_sum_abs _ _
    _ ≤ ∑ j, 32*|k j| := Finset.sum_le_sum (fun j _ => by
      rw [abs_mul]
      exact mul_le_mul_of_nonneg_right (gradient_component_bound u hu j) (abs_nonneg _))
    _ = _ := by rw [← Finset.mul_sum]; rfl

theorem entropy_lipschitz (u v : State) (hu : u ∈ region) (hv : v ∈ region) :
    |entropy v-entropy u| ≤ 32*componentL1 (v-u) := by
  let f := fun t => entropy (EulerEntropyConvexity.segment u v t)
  let df := fun t => dot (gradient (EulerEntropyConvexity.segment u v t)) (v-u)
  have hseg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :=
    EulerEntropyRegion.segment_in_region region region_convex u v hu hv t ht
  have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t :=
    entropy_derivative (EulerEntropyConvexity.segment_derivative u v t)
      (ne_of_gt (region_admissible _ (hseg t ht)).1) (ne_of_gt (region_admissible _ (hseg t ht)).2)
  obtain ⟨t,ht,he⟩ := exists_hasDerivAt_eq_slope f df (by norm_num : (0 : ℝ) < 1)
    (fun t ht => (hd t ht).continuousAt.continuousWithinAt)
    (fun t ht => hd t ⟨ht.1.le,ht.2.le⟩)
  have hh := gradient_pairing_bound (EulerEntropyConvexity.segment u v t) (v-u) (hseg t ⟨ht.1.le,ht.2.le⟩)
  change |df t| ≤ 32*componentL1 (v-u) at hh
  simp [f,EulerEntropyConvexity.segment] at he
  rwa [he] at hh

open MeasureTheory

theorem integrated_entropy_error {X : Type*} [MeasurableSpace X] (mu : Measure X) (u v : X → State)
    (hu : ∀ x, u x ∈ region) (hv : ∀ x, v x ∈ region)
    (hEu : Integrable (fun x => entropy (u x)) mu) (hEv : Integrable (fun x => entropy (v x)) mu)
    (herr : ∀ j, Integrable (fun x => |v x j-u x j|) mu) :
    |(∫ x, entropy (v x) ∂mu)-(∫ x, entropy (u x) ∂mu)| ≤
      32*∑ j, ∫ x, |v x j-u x j| ∂mu := by
  have hi : Integrable (fun x => ∑ j : Fin 5, |v x j-u x j|) mu :=
    integrable_finset_sum Finset.univ (fun j _ => herr j)
  rw [← integral_sub hEv hEu]
  calc
    _ ≤ ∫ x, |entropy (v x)-entropy (u x)| ∂mu := abs_integral_le_integral_abs
    _ ≤ ∫ x, 32*(∑ j : Fin 5, |v x j-u x j|) ∂mu :=
      integral_mono (hEv.sub hEu).abs (hi.const_mul 32) (fun x => entropy_lipschitz (u x) (v x) (hu x) (hv x))
    _ = _ := by rw [integral_const_mul,integral_finset_sum Finset.univ (fun j _ => herr j)]

theorem component_accuracy_controls_entropy {X : Type*} [MeasurableSpace X] (mu : Measure X)
    (u v : X → State) (epsilon : ℝ) (hu : ∀ x, u x ∈ region) (hv : ∀ x, v x ∈ region)
    (hEu : Integrable (fun x => entropy (u x)) mu) (hEv : Integrable (fun x => entropy (v x)) mu)
    (herr : ∀ j, Integrable (fun x => |v x j-u x j|) mu)
    (haccuracy : ∀ j, (∫ x, |v x j-u x j| ∂mu) ≤ epsilon) :
    |(∫ x, entropy (v x) ∂mu)-(∫ x, entropy (u x) ∂mu)| ≤ 160*epsilon := by
  have hh := integrated_entropy_error mu u v hu hv hEu hEv herr
  have hs := Finset.sum_le_sum (fun j (_ : j ∈ Finset.univ) => haccuracy j)
  simp only [Finset.sum_const,Finset.card_univ,Fintype.card_fin,nsmul_eq_mul] at hs
  norm_num only [Nat.cast_ofNat] at hs
  linarith

def maxComponentError {X : Type*} [MeasurableSpace X] (mu : Measure X) (u v : X → State) : ℝ :=
  Finset.univ.sup' Finset.univ_nonempty (fun j : Fin 5 => ∫ x, |v x j-u x j| ∂mu)

theorem entropy_gap_error_lower_bound {X : Type*} [MeasurableSpace X] (mu : Measure X)
    (u v : X → State) (hu : ∀ x, u x ∈ region) (hv : ∀ x, v x ∈ region)
    (hEu : Integrable (fun x => entropy (u x)) mu) (hEv : Integrable (fun x => entropy (v x)) mu)
    (herr : ∀ j, Integrable (fun x => |v x j-u x j|) mu) :
    |(∫ x, entropy (v x) ∂mu)-(∫ x, entropy (u x) ∂mu)|/160 ≤ maxComponentError mu u v := by
  have hh := component_accuracy_controls_entropy mu u v (maxComponentError mu u v) hu hv hEu hEv herr
    (fun j => Finset.le_sup' (f := fun j : Fin 5 => ∫ x, |v x j-u x j| ∂mu) (Finset.mem_univ j))
  exact (div_le_iff₀ (by norm_num : (0 : ℝ) < 160)).mpr (by linarith)

end EulerEntropyError


-- Global entropy balance for an actual differentiable periodic Euler field.
-- Existence of such a field for the target family is a separate obligation.
noncomputable section
namespace EulerEntropyIntegral
open EulerEntropy EulerEntropyDynamics EulerPhysicalFluxBounds EulerVectorEstimates
open scoped BigOperators
abbrev State := Fin 5 → ℝ
abbrev Space := Fin 3 → ℝ
abbrev Point := Fin 4 → ℝ

theorem entropy_flux_pairing (u k : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    dot (gradient u) (fluxD u k d)=dot (gradient u) k*normalVelocity u d+
      entropy u*normalVelocityD u k d := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  fin_cases d
  all_goals dsimp [dot,gradient,fluxD,normalVelocity,normalVelocityD,normalShift,pressureD,entropy]
  all_goals field_simp
  all_goals dsimp [EulerAdmissible.pressure]
  all_goals field_simp
  all_goals ring

theorem entropy_flux_hasDerivAt {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hphys : EulerAdmissible.Admissible (u t)) (d : Fin 3) :
    HasDerivAt (fun s => entropyFlux (u s) d) (dot (gradient (u t)) (fluxD (u t) k d)) t := by
  have he := entropy_derivative hu (ne_of_gt hphys.1) (ne_of_gt hphys.2)
  have hv := normal_velocity_derivative hu (ne_of_gt hphys.1) d
  rw [entropy_flux_pairing (u t) k hphys d]
  exact he.mul hv

theorem pressure_differentiable (u : State) (hu : u 0 ≠ 0) :
    DifferentiableAt ℝ EulerAdmissible.pressure u := by
  have he (j : Fin 5) : DifferentiableAt ℝ (fun v : State => v j) u := by fun_prop
  have hnum := (((he 1).pow 2).add ((he 2).pow 2)).add ((he 3).pow 2)
  have hden := ((he 0).const_mul 2).inv (mul_ne_zero (by norm_num : (2 : ℝ) ≠ 0) hu)
  have hquot : DifferentiableAt ℝ (fun v : State => (v 1^2+v 2^2+v 3^2)/(2*v 0)) u := by
    simpa only [div_eq_mul_inv] using hnum.mul hden
  exact (he 4).sub hquot

theorem entropy_differentiable (u : State) (hu : EulerAdmissible.Admissible u) :
    DifferentiableAt ℝ entropy u := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  have hpr := pressure_differentiable u hr
  have he : DifferentiableAt ℝ (fun v : State => v 0) u := by fun_prop
  exact he.neg.mul ((hpr.log hp).sub ((he.log hr).const_mul 2))

theorem entropy_flux_differentiable (u : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    DifferentiableAt ℝ (fun v => entropyFlux v d) u := by
  have hr := ne_of_gt hu.1
  have he := entropy_differentiable u hu
  have hm : DifferentiableAt ℝ (fun v : State => v ⟨d.val+1,by omega⟩) u := by fun_prop
  have hrho : DifferentiableAt ℝ (fun v : State => v 0) u := by fun_prop
  simpa only [entropyFlux,div_eq_mul_inv] using he.mul (hm.mul (hrho.inv hr))

theorem physical_flux_differentiable (u : State) (hu : u 0 ≠ 0) (d : Fin 3) :
    DifferentiableAt ℝ (fun v => EulerAdmissible.eulerFlux v d) u := by
  have hp := pressure_differentiable u hu
  have he (j : Fin 5) : DifferentiableAt ℝ (fun v : State => v j) u := by fun_prop
  have hv : DifferentiableAt ℝ (fun v : State => v ⟨d.val+1,by omega⟩/v 0) u := by
    simpa only [div_eq_mul_inv] using (he ⟨d.val+1,by omega⟩).mul ((he 0).inv hu)
  have hif (j : Fin 3) : DifferentiableAt ℝ (fun v : State => if d=j then EulerAdmissible.pressure v else 0) u := by
    by_cases hd : d=j
    · simpa only [hd,if_true] using hp
    · simp only [hd,if_false]
      exact differentiableAt_const (0 : ℝ)
  apply differentiableAt_pi.mpr
  intro j
  fin_cases j
  · exact he ⟨d.val+1,by omega⟩
  · exact ((he 1).mul hv).add (hif 0)
  · exact ((he 2).mul hv).add (hif 1)
  · exact ((he 3).mul hv).add (hif 2)
  · exact ((he 4).add hp).mul hv

def unit (i : Fin 4) : Point := Pi.single i 1
def line (x v : Point) (s : ℝ) : Point := x+s • v

theorem line_zero (x v : Point) : line x v 0=x := by simp [line]

theorem line_hasDerivAt (x v : Point) : HasDerivAt (line x v) v 0 := by
  simpa only [zero_add,one_smul] using
    (hasDerivAt_const (0 : ℝ) x).add ((hasDerivAt_id (0 : ℝ)).smul_const v)

theorem field_line_derivative (U : Point → State) (x v : Point) (hU : DifferentiableAt ℝ U x) :
    HasDerivAt (fun s => U (line x v s)) ((fderiv ℝ U x) v) 0 := by
  exact hU.hasFDerivAt.comp_hasDerivAt_of_eq 0 (line_hasDerivAt x v) (line_zero x v).symm

def current (i : Fin 4) (u : State) : ℝ := Fin.cases (entropy u) (fun d => entropyFlux u d) i

theorem current_differentiable (i : Fin 4) (u : State) (hu : EulerAdmissible.Admissible u) :
    DifferentiableAt ℝ (current i) u := by
  refine Fin.cases ?_ (fun d => ?_) i
  · exact entropy_differentiable u hu
  · exact entropy_flux_differentiable u hu d

theorem entropy_directional (U : Point → State) (x v : Point)
    (hU : DifferentiableAt ℝ U x) (hu : EulerAdmissible.Admissible (U x)) :
    (fderiv ℝ (fun z => entropy (U z)) x) v=dot (gradient (U x)) ((fderiv ℝ U x) v) := by
  have hline := field_line_derivative U x v hU
  have hadm : EulerAdmissible.Admissible (U (line x v 0)) := by rwa [line_zero]
  have he := entropy_derivative hline (ne_of_gt hadm.1) (ne_of_gt hadm.2)
  have hf := ((entropy_differentiable (U x) hu).comp x hU).hasFDerivAt.comp_hasDerivAt_of_eq 0
    (line_hasDerivAt x v) (line_zero x v).symm
  have hh := hf.unique he
  simpa only [line_zero] using hh

theorem entropy_flux_directional (U : Point → State) (x v : Point)
    (hU : DifferentiableAt ℝ U x) (hu : EulerAdmissible.Admissible (U x)) (d : Fin 3) :
    (fderiv ℝ (fun z => entropyFlux (U z) d) x) v=
      dot (gradient (U x)) (fluxD (U x) ((fderiv ℝ U x) v) d) := by
  have hline := field_line_derivative U x v hU
  have hadm : EulerAdmissible.Admissible (U (line x v 0)) := by rwa [line_zero]
  have he := entropy_flux_hasDerivAt hline hadm d
  have hf := ((entropy_flux_differentiable (U x) hu d).comp x hU).hasFDerivAt.comp_hasDerivAt_of_eq 0
    (line_hasDerivAt x v) (line_zero x v).symm
  have hh := hf.unique he
  simpa only [line_zero] using hh

theorem physical_flux_directional (U : Point → State) (x v : Point)
    (hU : DifferentiableAt ℝ U x) (hu : EulerAdmissible.Admissible (U x)) (d : Fin 3) :
    (fderiv ℝ (fun z => EulerAdmissible.eulerFlux (U z) d) x) v=
      fluxD (U x) ((fderiv ℝ U x) v) d := by
  have hline := field_line_derivative U x v hU
  have hr : U (line x v 0) 0 ≠ 0 := by rw [line_zero]; exact ne_of_gt hu.1
  have he := flux_derivative hline hr d
  have hf := ((physical_flux_differentiable (U x) (ne_of_gt hu.1) d).comp x hU).hasFDerivAt.comp_hasDerivAt_of_eq 0
    (line_hasDerivAt x v) (line_zero x v).symm
  have hh := hf.unique he
  simpa only [line_zero] using hh

def eulerResidual (U : Point → State) (x : Point) : State :=
  (fderiv ℝ U x) (unit 0)+
    ∑ d : Fin 3, (fderiv ℝ (fun z => EulerAdmissible.eulerFlux (U z) d) x) (unit d.succ)

theorem entropy_divergence_zero (U : Point → State) (x : Point)
    (hU : DifferentiableAt ℝ U x) (hu : EulerAdmissible.Admissible (U x))
    (heuler : eulerResidual U x=0) :
    (∑ i : Fin 4, (fderiv ℝ (fun z => current i (U z)) x) (unit i))=0 := by
  have he := congrArg (dot (gradient (U x))) heuler
  simp only [eulerResidual,dot_add_right,dot_sum_right,physical_flux_directional U x _ hU hu] at he
  rw [Fin.sum_univ_succ]
  simp only [current,Fin.cases_zero,Fin.cases_succ,entropy_directional U x _ hU hu,
    entropy_flux_directional U x _ hU hu]
  simpa only [dot,Pi.zero_apply,mul_zero,add_zero] using he

open MeasureTheory

def lower : Point := fun _ => 0
def upper (T L : ℝ) : Point := Fin.cons T (fun _ : Fin 3 => L)
def box (T L : ℝ) : Set Point := Set.Icc lower (upper T L)
def cube (L : ℝ) : Set Space := Set.Icc (fun _ => 0) (fun _ => L)
def faceDomain (T L : ℝ) (i : Fin 4) : Set Space :=
  Set.Icc (lower ∘ i.succAbove) (upper T L ∘ i.succAbove)

theorem time_face_domain (T L : ℝ) : faceDomain T L 0=cube L := by rfl

theorem box_order (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L) : lower ≤ upper T L := by
  intro i
  refine Fin.cases ?_ (fun _ => ?_) i
  · exact hT
  · exact hL

theorem interior_box_subset (T L : ℝ) :
    (Set.pi Set.univ (fun i => Set.Ioo (lower i) (upper T L i))) ⊆ box T L := by
  intro x hx
  exact ⟨fun i => (hx i (Set.mem_univ i)).1.le,fun i => (hx i (Set.mem_univ i)).2.le⟩

theorem periodic_face_balance {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L)
    (f : Fin 4 → Point → E) (df : Fin 4 → Point → Point →L[ℝ] E)
    (hd : ∀ x ∈ box T L, ∀ i, HasFDerivAt (f i) (df i x) x)
    (hdiv : ∀ x ∈ box T L, (∑ i, df i x (unit i))=0)
    (hper : ∀ i : Fin 4, i ≠ 0 → ∀ y ∈ faceDomain T L i,
      f i (i.insertNth (upper T L i) y)=f i (i.insertNth (lower i) y)) :
    (∫ y in cube L, f 0 (Fin.cons T y))=(∫ y in cube L, f 0 (Fin.cons 0 y)) := by
  have hzero : (fun x => ∑ i, df i x (unit i)) =ᵐ[(volume : Measure Point).restrict (box T L)]
      (fun _ => (0 : E)) := by
    filter_upwards [ae_restrict_mem (measurableSet_Icc : MeasurableSet (box T L))] with x hx
    exact hdiv x hx
  have hi : IntegrableOn (fun x => ∑ i, df i x (unit i)) (box T L) :=
    (integrable_zero Point E (volume.restrict (box T L))).congr hzero.symm
  have hg := integral_divergence_of_hasFDerivAt_off_countable' lower (upper T L) (box_order T L hT hL)
    f df ∅ Set.countable_empty
    (fun i x hx => (hd x hx i).continuousAt.continuousWithinAt)
    (fun x hx i => hd x (interior_box_subset T L hx.1) i) hi
  have hz : (∫ x in box T L, ∑ i, df i x (unit i))=0 := by
    calc
      _ = ∫ _x : Point, (0 : E) ∂(volume.restrict (box T L)) := integral_congr_ae hzero
      _ = _ := by simp
  have hface (i : Fin 4) (hi : i ≠ 0) :
      ((∫ y in faceDomain T L i, f i (i.insertNth (upper T L i) y))-
        ∫ y in faceDomain T L i, f i (i.insertNth (lower i) y))=0 := by
    apply sub_eq_zero.mpr
    exact setIntegral_congr_fun measurableSet_Icc (hper i hi)
  have hsum : (∑ i : Fin 4,
      ((∫ y in faceDomain T L i, f i (i.insertNth (upper T L i) y))-
        ∫ y in faceDomain T L i, f i (i.insertNth (lower i) y))) =
      (∫ y in faceDomain T L 0, f 0 ((0 : Fin 4).insertNth (upper T L 0) y))-
        ∫ y in faceDomain T L 0, f 0 ((0 : Fin 4).insertNth (lower 0) y) := by
    exact Finset.sum_eq_single 0 (fun i _ hi => hface i hi)
      (fun hnot => False.elim (hnot (Finset.mem_univ 0)))
  change (∫ x in box T L, ∑ i, df i x (unit i))=
    ∑ i : Fin 4, ((∫ y in faceDomain T L i, f i (i.insertNth (upper T L i) y))-
      ∫ y in faceDomain T L i, f i (i.insertNth (lower i) y)) at hg
  rw [hz,hsum] at hg
  have hh : (0 : E)=(∫ y in cube L, f 0 (Fin.cons T y))-(∫ y in cube L, f 0 (Fin.cons 0 y)) := by
    simpa only [time_face_domain,upper,lower,Fin.cons_zero,Fin.insertNth_zero'] using hg
  exact sub_eq_zero.mp hh.symm

def PeriodicBoundary (U : Point → State) (T L : ℝ) : Prop :=
  ∀ i : Fin 4, i ≠ 0 → ∀ y ∈ faceDomain T L i,
    U (i.insertNth (upper T L i) y)=U (i.insertNth (lower i) y)

theorem periodic_entropy_conservation (U : Point → State) (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L) :
    (∫ y in cube L, entropy (U (Fin.cons T y)))=(∫ y in cube L, entropy (U (Fin.cons 0 y))) := by
  apply periodic_face_balance T L hT hL (fun i x => current i (U x))
    (fun i x => fderiv ℝ (fun z => current i (U z)) x)
  · intro x hx i
    exact ((current_differentiable i (U x) (hphys x hx)).comp x (hU x hx)).hasFDerivAt
  · intro x hx
    exact entropy_divergence_zero U x (hU x hx) (hphys x hx) (heuler x hx)
  · intro i hi y hy
    exact congrArg (current i) (hperiodic i hi y hy)

def conservedCurrent (i : Fin 4) (u : State) : State := Fin.cases u (fun d => EulerAdmissible.eulerFlux u d) i

theorem conserved_current_differentiable (i : Fin 4) (u : State) (hu : EulerAdmissible.Admissible u) :
    DifferentiableAt ℝ (conservedCurrent i) u := by
  refine Fin.cases ?_ (fun d => ?_) i
  · exact differentiableAt_id
  · exact physical_flux_differentiable u (ne_of_gt hu.1) d

theorem periodic_conserved_integral (U : Point → State) (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L) :
    (∫ y in cube L, U (Fin.cons T y))=(∫ y in cube L, U (Fin.cons 0 y)) := by
  apply periodic_face_balance T L hT hL (fun i x => conservedCurrent i (U x))
    (fun i x => fderiv ℝ (fun z => conservedCurrent i (U z)) x)
  · intro x hx i
    exact ((conserved_current_differentiable i (U x) (hphys x hx)).comp x (hU x hx)).hasFDerivAt
  · intro x hx
    simpa only [Fin.sum_univ_succ,conservedCurrent,Fin.cases_zero,Fin.cases_succ,eulerResidual] using heuler x hx
  · intro i hi y hy
    exact congrArg (conservedCurrent i) (hperiodic i hi y hy)

-- The error contract uses volume normalized by the physical cube's volume.
def cubeMeasure (L : ℝ) : Measure Space :=
  ENNReal.ofReal (1/L^3) • (volume.restrict (cube L))

theorem cube_volume (L : ℝ) (hL : 0 ≤ L) : volume (cube L)=ENNReal.ofReal (L^3) := by
  simp only [cube,Real.volume_Icc_pi,sub_zero,Finset.prod_const,Finset.card_univ,Fintype.card_fin]
  exact (ENNReal.ofReal_pow hL 3).symm

theorem cube_measure_univ (L : ℝ) (hL : 0 < L) : cubeMeasure L Set.univ=1 := by
  rw [cubeMeasure,Measure.smul_apply,Measure.restrict_apply_univ,cube_volume L hL.le]
  change ENNReal.ofReal (1/L^3)*ENNReal.ofReal (L^3)=1
  rw [← ENNReal.ofReal_mul (by positivity : 0 ≤ 1/L^3)]
  simp [ne_of_gt hL]

theorem cube_integral {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    (L : ℝ) (hL : 0 ≤ L) (f : Space → E) :
    (∫ y, f y ∂cubeMeasure L)=(1/L^3) • (∫ y in cube L, f y) := by
  rw [cubeMeasure,integral_smul_measure,ENNReal.toReal_ofReal (by positivity : 0 ≤ 1/L^3)]

theorem normalized_entropy_conservation (U : Point → State) (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L) :
    (∫ y, entropy (U (Fin.cons T y)) ∂cubeMeasure L)=
      (∫ y, entropy (U (Fin.cons 0 y)) ∂cubeMeasure L) := by
  rw [cube_integral L hL,cube_integral L hL,
    periodic_entropy_conservation U T L hT hL hU hphys heuler hperiodic]

theorem normalized_conserved_integral (U : Point → State) (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L) :
    (∫ y, U (Fin.cons T y) ∂cubeMeasure L)=(∫ y, U (Fin.cons 0 y) ∂cubeMeasure L) := by
  rw [cube_integral L hL,cube_integral L hL,
    periodic_conserved_integral U T L hT hL hU hphys heuler hperiodic]

open EulerPhysicalRegion EulerEntropyError

theorem integrated_entropy_error_ae {X : Type*} [MeasurableSpace X] (mu : Measure X) (u v : X → State)
    (hu : ∀ᵐ x ∂mu, u x ∈ region) (hv : ∀ᵐ x ∂mu, v x ∈ region)
    (hEu : Integrable (fun x => entropy (u x)) mu) (hEv : Integrable (fun x => entropy (v x)) mu)
    (herr : ∀ j, Integrable (fun x => |v x j-u x j|) mu) :
    |(∫ x, entropy (v x) ∂mu)-(∫ x, entropy (u x) ∂mu)| ≤
      32*∑ j, ∫ x, |v x j-u x j| ∂mu := by
  have hi : Integrable (fun x => ∑ j : Fin 5, |v x j-u x j|) mu :=
    integrable_finset_sum Finset.univ (fun j _ => herr j)
  have hpoint : (fun x => |entropy (v x)-entropy (u x)|) ≤ᵐ[mu]
      (fun x => 32*(∑ j : Fin 5, |v x j-u x j|)) := by
    filter_upwards [hu,hv] with x hux hvx
    exact entropy_lipschitz (u x) (v x) hux hvx
  rw [← integral_sub hEv hEu]
  calc
    _ ≤ ∫ x, |entropy (v x)-entropy (u x)| ∂mu := abs_integral_le_integral_abs
    _ ≤ ∫ x, 32*(∑ j : Fin 5, |v x j-u x j|) ∂mu :=
      integral_mono_ae (hEv.sub hEu).abs (hi.const_mul 32) hpoint
    _ = _ := by rw [integral_const_mul,integral_finset_sum Finset.univ (fun j _ => herr j)]

theorem entropy_gap_error_lower_bound_ae {X : Type*} [MeasurableSpace X] (mu : Measure X)
    (u v : X → State) (hu : ∀ᵐ x ∂mu, u x ∈ region) (hv : ∀ᵐ x ∂mu, v x ∈ region)
    (hEu : Integrable (fun x => entropy (u x)) mu) (hEv : Integrable (fun x => entropy (v x)) mu)
    (herr : ∀ j, Integrable (fun x => |v x j-u x j|) mu) :
    |(∫ x, entropy (v x) ∂mu)-(∫ x, entropy (u x) ∂mu)|/160 ≤ maxComponentError mu u v := by
  have hh := integrated_entropy_error_ae mu u v hu hv hEu hEv herr
  have hj (j : Fin 5) : (∫ x, |v x j-u x j| ∂mu) ≤ maxComponentError mu u v :=
    Finset.le_sup' (f := fun j : Fin 5 => ∫ x, |v x j-u x j| ∂mu) (Finset.mem_univ j)
  have hs := Finset.sum_le_sum (fun j (_ : j ∈ Finset.univ) => hj j)
  simp only [Finset.sum_const,Finset.card_univ,Fintype.card_fin,nsmul_eq_mul] at hs
  norm_num only [Nat.cast_ofNat] at hs
  apply (div_le_iff₀ (by norm_num : (0 : ℝ) < 160)).mpr
  linarith

theorem cube_ae_mem (L : ℝ) : ∀ᵐ y ∂cubeMeasure L, y ∈ cube L :=
  Measure.ae_smul_measure (ae_restrict_mem (measurableSet_Icc : MeasurableSet (cube L))) _

theorem cube_integrable {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    (L : ℝ) (f : Space → E) (hf : ContinuousOn f (cube L)) : Integrable f (cubeMeasure L) := by
  exact (hf.integrableOn_compact isCompact_Icc).smul_measure ENNReal.ofReal_ne_top

theorem entropy_continuousOn (L : ℝ) (u : Space → State)
    (hc : ContinuousOn u (cube L)) (hu : ∀ x ∈ cube L, u x ∈ region) :
    ContinuousOn (fun x => entropy (u x)) (cube L) := by
  intro x hx
  exact (entropy_differentiable (u x) (region_admissible _ (hu x hx))).continuousAt.comp_continuousWithinAt (hc x hx)

theorem normalized_error_lower_bound (L : ℝ) (u v : Space → State)
    (hcu : ContinuousOn u (cube L)) (hcv : ContinuousOn v (cube L))
    (hu : ∀ x ∈ cube L, u x ∈ region) (hv : ∀ x ∈ cube L, v x ∈ region) :
    |(∫ x, entropy (v x) ∂cubeMeasure L)-(∫ x, entropy (u x) ∂cubeMeasure L)|/160 ≤
      maxComponentError (cubeMeasure L) u v := by
  have huae : ∀ᵐ x ∂cubeMeasure L, u x ∈ region := (cube_ae_mem L).mono (fun x hx => hu x hx)
  have hvae : ∀ᵐ x ∂cubeMeasure L, v x ∈ region := (cube_ae_mem L).mono (fun x hx => hv x hx)
  apply entropy_gap_error_lower_bound_ae (cubeMeasure L) u v huae hvae
    (cube_integrable L _ (entropy_continuousOn L u hcu hu))
    (cube_integrable L _ (entropy_continuousOn L v hcv hv))
  intro j
  apply cube_integrable
  exact ((continuous_apply j).continuousOn.comp hcv (fun _ _ => Set.mem_univ _)).sub
    ((continuous_apply j).continuousOn.comp hcu (fun _ _ => Set.mem_univ _)) |>.abs

theorem slice_mem_box (T L t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) T) (y : Space) (hy : y ∈ cube L) :
    Fin.cons t y ∈ box T L := by
  constructor
  · intro i
    exact Fin.cases ht.1 (fun d => hy.1 d) i
  · intro i
    exact Fin.cases ht.2 (fun d => hy.2 d) i

theorem slice_continuousOn (U : Point → State) (T L t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) T)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x) :
    ContinuousOn (fun y => U (Fin.cons t y)) (cube L) := by
  intro y hy
  have hc : ContinuousAt (fun z : Space => Fin.cons t z : Space → Point) y := by
    apply continuousAt_pi.mpr
    intro i
    refine Fin.cases ?_ (fun d => ?_) i
    · exact continuousAt_const
    · exact (continuous_apply d).continuousAt
  exact ((hU _ (slice_mem_box T L t ht y hy)).continuousAt.comp hc).continuousWithinAt

-- This compares a continuous approximate field with a smooth Euler solution.
-- It neither constructs that solution nor asserts accuracy of a numerical method.
theorem physical_error_from_initial_entropy (U : Point → State) (V : Space → State)
    (T L : ℝ) (hT : 0 ≤ T) (hL : 0 < L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L)
    (hUT : ∀ y ∈ cube L, U (Fin.cons T y) ∈ region)
    (hVc : ContinuousOn V (cube L)) (hV : ∀ y ∈ cube L, V y ∈ region) :
    |(∫ y, entropy (V y) ∂cubeMeasure L)-
      (∫ y, entropy (U (Fin.cons 0 y)) ∂cubeMeasure L)|/160 ≤
      maxComponentError (cubeMeasure L) (fun y => U (Fin.cons T y)) V := by
  rw [← normalized_entropy_conservation U T L hT hL.le hU hphys heuler hperiodic]
  exact normalized_error_lower_bound L _ V
    (slice_continuousOn U T L T ⟨hT,le_rfl⟩ hU) hVc hUT hV

end EulerEntropyIntegral


-- Continuous periodic trilinear reconstruction of actual conserved grid states.
noncomputable section
namespace EulerHatReconstruction
open MeasureTheory EulerEntropyIntegral
open scoped BigOperators
abbrev State := Fin 5 → ℝ

def ramp (x : ℝ) : ℝ := max 0 (min 1 x)
def hat (x : ℝ) : ℝ := ramp (x+1)-ramp x

theorem ramp_zero (x : ℝ) (hx : x ≤ 0) : ramp x=0 := by
  simp [ramp,min_eq_right (by linarith : x ≤ 1),max_eq_left hx]

theorem ramp_one (x : ℝ) (hx : 1 ≤ x) : ramp x=1 := by
  simp [ramp,min_eq_left hx]

theorem ramp_middle (x : ℝ) (h0 : 0 ≤ x) (h1 : x ≤ 1) : ramp x=x := by
  simp [ramp,min_eq_right h1,max_eq_right h0]

theorem hat_nonnegative (x : ℝ) : 0 ≤ hat x := by
  apply sub_nonneg.mpr
  exact max_le_max le_rfl (min_le_min_left 1 (by linarith : x ≤ x+1))

theorem hat_continuous : Continuous hat := by unfold hat ramp; fun_prop

theorem hat_zero_left (x : ℝ) (hx : x ≤ -1) : hat x=0 := by
  rw [hat,ramp_zero (x+1) (by linarith),ramp_zero x (by linarith),sub_self]

theorem hat_zero_right (x : ℝ) (hx : 1 ≤ x) : hat x=0 := by
  rw [hat,ramp_one (x+1) (by linarith),ramp_one x hx,sub_self]

theorem hat_left (x : ℝ) (h0 : -1 ≤ x) (h1 : x ≤ 0) : hat x=x+1 := by
  rw [hat,ramp_middle (x+1) (by linarith) (by linarith),ramp_zero x h1,sub_zero]

theorem hat_right (x : ℝ) (h0 : 0 ≤ x) (h1 : x ≤ 1) : hat x=1-x := by
  rw [hat,ramp_one (x+1) (by linarith),ramp_middle x h0 h1]

theorem sum_hat (n : ℕ) (s : ℝ) :
    (∑ i : Fin n, hat (s-(i.val : ℝ)))=ramp (s+1)-ramp (s-(n : ℝ)+1) := by
  induction n with
  | zero => simp
  | succ n ih =>
    rw [Fin.sum_univ_castSucc]
    simp only [Fin.coe_castSucc,Fin.val_last,Nat.cast_add,Nat.cast_one]
    rw [ih]
    have he : s-((n : ℝ)+1)+1=s-(n : ℝ) := by ring
    rw [he]
    dsimp [hat]
    ring

def periodicHat (n : ℕ) (i : Fin n) (s : ℝ) : ℝ :=
  hat (s-(i.val : ℝ))+hat (s-(i.val : ℝ)+(n : ℝ))+hat (s-(i.val : ℝ)-(n : ℝ))

theorem periodic_hat_nonnegative (n : ℕ) (i : Fin n) (s : ℝ) : 0 ≤ periodicHat n i s :=
  add_nonneg (add_nonneg (hat_nonnegative _) (hat_nonnegative _)) (hat_nonnegative _)

theorem periodic_hat_continuous (n : ℕ) (i : Fin n) : Continuous (periodicHat n i) := by
  unfold periodicHat
  exact ((hat_continuous.comp (continuous_id.sub continuous_const)).add
    (hat_continuous.comp ((continuous_id.sub continuous_const).add continuous_const))).add
    (hat_continuous.comp ((continuous_id.sub continuous_const).sub continuous_const))

theorem periodic_hat_sum (n : ℕ) [NeZero n] (s : ℝ)
    (hs0 : -(1/2 : ℝ) ≤ s) (hs1 : s ≤ (n : ℝ)-1/2) :
    (∑ i : Fin n, periodicHat n i s)=1 := by
  have hn : 1 ≤ (n : ℝ) := by exact_mod_cast (NeZero.one_le : 1 ≤ n)
  have ep (i : Fin n) : s-(i.val : ℝ)+(n : ℝ)=(s+(n : ℝ))-(i.val : ℝ) := by ring
  have em (i : Fin n) : s-(i.val : ℝ)-(n : ℝ)=(s-(n : ℝ))-(i.val : ℝ) := by ring
  simp only [periodicHat,ep,em,Finset.sum_add_distrib,sum_hat]
  have e1 : s+(n : ℝ)-(n : ℝ)+1=s+1 := by ring
  have e2 : s-(n : ℝ)-(n : ℝ)+1=s-2*(n : ℝ)+1 := by ring
  rw [e1,e2,ramp_one (s+(n : ℝ)+1) (by linarith),
    ramp_zero (s-2*(n : ℝ)+1) (by linarith)]
  ring

theorem periodic_hat_boundary (n : ℕ) [NeZero n] (i : Fin n) :
    periodicHat n i ((n : ℝ)-1/2)=periodicHat n i (-(1/2 : ℝ)) := by
  have hn : 1 ≤ (n : ℝ) := by exact_mod_cast (NeZero.one_le : 1 ≤ n)
  have hi : (i.val : ℝ)+1 ≤ (n : ℝ) := by exact_mod_cast i.isLt
  have hi0 : 0 ≤ (i.val : ℝ) := Nat.cast_nonneg _
  have e1 : (n : ℝ)-1/2-(i.val : ℝ)= -(1/2 : ℝ)-(i.val : ℝ)+(n : ℝ) := by ring
  have e2 : (n : ℝ)-1/2-(i.val : ℝ)-(n : ℝ)= -(1/2 : ℝ)-(i.val : ℝ) := by ring
  unfold periodicHat
  rw [hat_zero_right ((n : ℝ)-1/2-(i.val : ℝ)+(n : ℝ)) (by linarith),
    hat_zero_left (-(1/2 : ℝ)-(i.val : ℝ)-(n : ℝ)) (by linarith),e2,e1]
  ring

def weight (n : ℕ) (L : ℝ) (i : Fin n) (x : ℝ) : ℝ :=
  periodicHat n i ((n : ℝ)*x/L-1/2)

theorem weight_nonnegative (n : ℕ) (L : ℝ) (i : Fin n) (x : ℝ) : 0 ≤ weight n L i x :=
  periodic_hat_nonnegative n i _

theorem weight_continuous (n : ℕ) (L : ℝ) (i : Fin n) : Continuous (weight n L i) := by
  exact (periodic_hat_continuous n i).comp (by fun_prop)

theorem weight_sum (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (x : ℝ) (hx : x ∈ Set.Icc (0 : ℝ) L) :
    (∑ i : Fin n, weight n L i x)=1 := by
  apply periodic_hat_sum
  · have hh : 0 ≤ (n : ℝ)*x/L := div_nonneg (mul_nonneg (Nat.cast_nonneg _) hx.1) hL.le
    linarith
  · have hh : (n : ℝ)*x/L ≤ (n : ℝ) := by
      apply (div_le_iff₀ hL).mpr
      exact mul_le_mul_of_nonneg_left hx.2 (Nat.cast_nonneg _)
    linarith

theorem weight_boundary (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (i : Fin n) :
    weight n L i L=weight n L i 0 := by
  simpa [weight,ne_of_gt hL] using periodic_hat_boundary n i

theorem hat_support (a b : ℝ) (ha : a ≤ -1) (hb : 1 ≤ b) :
    Function.support hat ⊆ Set.Ioc a b := by
  intro x hx
  have hl : -1 < x := lt_of_not_ge (fun h => hx (hat_zero_left x h))
  have hr : x < 1 := lt_of_not_ge (fun h => hx (hat_zero_right x h))
  exact ⟨ha.trans_lt hl,hr.le.trans hb⟩

theorem hat_unit_integral : (∫ x in (-1 : ℝ)..1, hat x)=1 := by
  have hl : (∫ x in (-1 : ℝ)..0, hat x)=1/2 := by
    calc
      _ = ∫ x in (-1 : ℝ)..0, x+1 := intervalIntegral.integral_congr (fun x hx => by
        rw [Set.uIcc_of_le (by norm_num : (-1 : ℝ) ≤ 0)] at hx
        exact hat_left x hx.1 hx.2)
      _ = _ := by
        rw [intervalIntegral.integral_add (f := fun x : ℝ => x) (g := fun _ => (1 : ℝ))
          (continuous_id.intervalIntegrable _ _) (continuous_const.intervalIntegrable _ _)]
        norm_num
  have hr : (∫ x in (0 : ℝ)..1, hat x)=1/2 := by
    calc
      _ = ∫ x in (0 : ℝ)..1, 1-x := intervalIntegral.integral_congr (fun x hx => by
        rw [Set.uIcc_of_le (by norm_num : (0 : ℝ) ≤ 1)] at hx
        exact hat_right x hx.1 hx.2)
      _ = _ := by
        rw [intervalIntegral.integral_sub (f := fun _ : ℝ => (1 : ℝ)) (g := fun x => x)
          (continuous_const.intervalIntegrable _ _) (continuous_id.intervalIntegrable _ _)]
        norm_num
  rw [← intervalIntegral.integral_add_adjacent_intervals
    (hat_continuous.intervalIntegrable (-1) 0) (hat_continuous.intervalIntegrable 0 1),hl,hr]
  norm_num

theorem hat_integral (a b : ℝ) (ha : a ≤ -1) (hb : 1 ≤ b) :
    (∫ x in a..b, hat x)=1 := by
  rw [intervalIntegral.integral_eq_integral_of_support_subset (hat_support a b ha hb),
    ← intervalIntegral.integral_eq_integral_of_support_subset
      (hat_support (-1) 1 le_rfl le_rfl)]
  exact hat_unit_integral

theorem periodic_hat_integral (n : ℕ) [NeZero n] (i : Fin n) :
    (∫ s in -(1/2 : ℝ)..(n : ℝ)-1/2, periodicHat n i s)=1 := by
  have hn : 1 ≤ (n : ℝ) := by exact_mod_cast (NeZero.one_le : 1 ≤ n)
  have hi : (i.val : ℝ)+1 ≤ (n : ℝ) := by exact_mod_cast i.isLt
  have hi0 : 0 ≤ (i.val : ℝ) := Nat.cast_nonneg _
  let a := -(1/2 : ℝ)-(i.val : ℝ)-(n : ℝ)
  let b := -(1/2 : ℝ)-(i.val : ℝ)
  let c := (n : ℝ)-1/2-(i.val : ℝ)
  let d := (n : ℝ)-1/2-(i.val : ℝ)+(n : ℝ)
  have hp : (∫ s in -(1/2 : ℝ)..(n : ℝ)-1/2, hat (s-(i.val : ℝ)+(n : ℝ)))=
      ∫ s in c..d, hat s := by
    calc
      _ = ∫ s in -(1/2 : ℝ)..(n : ℝ)-1/2, hat (s+((n : ℝ)-(i.val : ℝ))) :=
        intervalIntegral.integral_congr (fun s _ => congrArg hat (by ring))
      _ = _ := by
        rw [intervalIntegral.integral_comp_add_right]
        congr 1 <;> dsimp [c,d] <;> ring
  have hm : (∫ s in -(1/2 : ℝ)..(n : ℝ)-1/2, hat (s-(i.val : ℝ)-(n : ℝ)))=
      ∫ s in a..b, hat s := by
    calc
      _ = ∫ s in -(1/2 : ℝ)..(n : ℝ)-1/2, hat (s-((i.val : ℝ)+(n : ℝ))) :=
        intervalIntegral.integral_congr (fun s _ => congrArg hat (by ring))
      _ = _ := by
        rw [intervalIntegral.integral_comp_sub_right]
        congr 1 <;> dsimp [a,b] <;> ring
  have hc0 : Continuous (fun s => hat (s-(i.val : ℝ))) :=
    hat_continuous.comp (continuous_id.sub continuous_const)
  have hcp : Continuous (fun s => hat (s-(i.val : ℝ)+(n : ℝ))) :=
    hat_continuous.comp ((continuous_id.sub continuous_const).add continuous_const)
  have hcm : Continuous (fun s => hat (s-(i.val : ℝ)-(n : ℝ))) :=
    hat_continuous.comp ((continuous_id.sub continuous_const).sub continuous_const)
  simp only [periodicHat]
  rw [intervalIntegral.integral_add ((hc0.add hcp).intervalIntegrable _ _)
    (hcm.intervalIntegrable _ _),intervalIntegral.integral_add
    (hc0.intervalIntegrable _ _) (hcp.intervalIntegrable _ _),hp,hm,
    intervalIntegral.integral_comp_sub_right]
  change ((∫ s in b..c, hat s)+(∫ s in c..d, hat s))+(∫ s in a..b, hat s)=1
  rw [intervalIntegral.integral_add_adjacent_intervals
    (hat_continuous.intervalIntegrable b c) (hat_continuous.intervalIntegrable c d),add_comm,
    intervalIntegral.integral_add_adjacent_intervals
    (hat_continuous.intervalIntegrable a b) (hat_continuous.intervalIntegrable b d)]
  exact hat_integral a d (by dsimp [a]; linarith) (by dsimp [d]; linarith)

theorem weight_integral (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (i : Fin n) :
    (∫ x in Set.Icc (0 : ℝ) L, weight n L i x)=L/(n : ℝ) := by
  have hn : (n : ℝ) ≠ 0 := by exact_mod_cast NeZero.ne n
  rw [integral_Icc_eq_integral_Ioc,← intervalIntegral.integral_of_le hL.le]
  have he : weight n L i=(fun x => periodicHat n i (((n : ℝ)/L)*x-1/2)) := by
    funext x
    unfold weight
    congr 1
    ring
  rw [he,intervalIntegral.integral_comp_mul_sub _ (div_ne_zero hn (ne_of_gt hL))]
  simp only [mul_zero,zero_sub,div_mul_cancel₀ _ (ne_of_gt hL),periodic_hat_integral,
    smul_eq_mul,mul_one,inv_div]

abbrev Cell (n : ℕ) := EulerGridPoincare.Cell n
def coordinates {n : ℕ} (i : Cell n) : Fin 3 → Fin n := ![i.1,i.2.1,i.2.2]
def weight3 (n : ℕ) (L : ℝ) (i : Cell n) (x : Space) : ℝ :=
  weight n L i.1 (x 0)*weight n L i.2.1 (x 1)*weight n L i.2.2 (x 2)

theorem weight3_product (n : ℕ) (L : ℝ) (i : Cell n) (x : Space) :
    weight3 n L i x=∏ d : Fin 3, weight n L (coordinates i d) (x d) := by
  simp [weight3,coordinates,Fin.prod_univ_succ,mul_assoc]

theorem weight3_nonnegative (n : ℕ) (L : ℝ) (i : Cell n) (x : Space) : 0 ≤ weight3 n L i x :=
  mul_nonneg (mul_nonneg (weight_nonnegative _ _ _ _) (weight_nonnegative _ _ _ _))
    (weight_nonnegative _ _ _ _)

theorem weight3_continuous (n : ℕ) (L : ℝ) (i : Cell n) : Continuous (weight3 n L i) :=
  (((weight_continuous n L i.1).comp (continuous_apply 0)).mul
    ((weight_continuous n L i.2.1).comp (continuous_apply 1))).mul
    ((weight_continuous n L i.2.2).comp (continuous_apply 2))

theorem weight3_sum (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (x : Space) (hx : x ∈ cube L) :
    (∑ i : Cell n, weight3 n L i x)=1 := by
  have hs (d : Fin 3) := weight_sum n L hL (x d) ⟨hx.1 d,hx.2 d⟩
  simp only [Fintype.sum_prod_type,weight3,← Finset.mul_sum,hs,mul_one]

theorem cube_product_measure (L : ℝ) :
    (volume : Measure Space).restrict (cube L)=
      Measure.pi (fun _ : Fin 3 => (volume : Measure ℝ).restrict (Set.Icc (0 : ℝ) L)) := by
  rw [cube,← Set.pi_univ_Icc]
  exact Measure.restrict_pi_pi _ _

theorem weight3_integral (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (i : Cell n) :
    (∫ x, weight3 n L i x ∂cubeMeasure L)=1/(n : ℝ)^3 := by
  have he : (∫ x in cube L, weight3 n L i x)=(L/(n : ℝ))^3 := by
    simp_rw [weight3_product]
    rw [cube_product_measure,integral_fintype_prod_eq_prod]
    simp only [weight_integral n L hL,Finset.prod_const,Finset.card_univ,Fintype.card_fin]
  rw [cube_integral L hL.le,he,smul_eq_mul]
  have hn : (n : ℝ) ≠ 0 := by exact_mod_cast NeZero.ne n
  field_simp

def reconstruct (n : ℕ) (L : ℝ) (u : Cell n → State) (x : Space) : State :=
  ∑ i, weight3 n L i x • u i

theorem reconstruction_continuous (n : ℕ) (L : ℝ) (u : Cell n → State) :
    Continuous (reconstruct n L u) := by
  exact continuous_finset_sum _ (fun i _ => (weight3_continuous n L i).smul continuous_const)

theorem reconstruction_in_region (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (u : Cell n → State)
    (hu : ∀ i, u i ∈ EulerPhysicalRegion.region) (x : Space) (hx : x ∈ cube L) :
    reconstruct n L u x ∈ EulerPhysicalRegion.region := by
  exact EulerPhysicalRegion.region_convex.sum_mem
    (fun i _ => weight3_nonnegative n L i x) (weight3_sum n L hL x hx) (fun i _ => hu i)

theorem reconstruction_mean (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (u : Cell n → State) :
    (∫ x, reconstruct n L u x ∂cubeMeasure L)=EulerGridPoincare.meanState u := by
  have hi (i : Cell n) : Integrable (fun x => weight3 n L i x • u i) (cubeMeasure L) :=
    cube_integrable L _ ((weight3_continuous n L i).smul continuous_const).continuousOn
  change (∫ x, ∑ i, weight3 n L i x • u i ∂cubeMeasure L)=_
  rw [integral_finset_sum Finset.univ (fun i _ => hi i)]
  simp only [integral_smul_const,weight3_integral n L hL,← Finset.smul_sum,
    EulerGridPoincare.meanState,Fintype.card_prod,Fintype.card_fin,Nat.cast_mul]
  congr 1
  ring

theorem reconstruction_entropy (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (u : Cell n → State)
    (hu : ∀ i, u i ∈ EulerPhysicalRegion.region) :
    (∫ x, EulerEntropy.entropy (reconstruct n L u x) ∂cubeMeasure L) ≤
      (1/(n : ℝ)^3)*∑ i, EulerEntropy.entropy (u i) := by
  have hfield := reconstruction_in_region n L hL u hu
  have he : Integrable (fun x => EulerEntropy.entropy (reconstruct n L u x)) (cubeMeasure L) :=
    cube_integrable L _ (entropy_continuousOn L _ (reconstruction_continuous n L u).continuousOn hfield)
  have hi (i : Cell n) : Integrable (fun x => weight3 n L i x*EulerEntropy.entropy (u i)) (cubeMeasure L) :=
    cube_integrable L _ ((weight3_continuous n L i).mul continuous_const).continuousOn
  calc
    _ ≤ ∫ x, ∑ i, weight3 n L i x*EulerEntropy.entropy (u i) ∂cubeMeasure L := by
      apply integral_mono_ae he (integrable_finset_sum Finset.univ (fun i _ => hi i))
      filter_upwards [cube_ae_mem L] with x hx
      exact EulerEntropyConvexity.entropy_convex_mixture (fun i => weight3 n L i x) u
        (fun i => weight3_nonnegative n L i x) (weight3_sum n L hL x hx)
        (fun i => EulerPhysicalRegion.region_admissible _ (hu i))
    _ = _ := by
      rw [integral_finset_sum Finset.univ (fun i _ => hi i)]
      simp only [integral_mul_const,weight3_integral n L hL,← Finset.mul_sum]

theorem reconstruction_boundary (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L)
    (u : Cell n → State) (x : Space) (d : Fin 3) :
    reconstruct n L u (Function.update x d L)=reconstruct n L u (Function.update x d 0) := by
  apply Finset.sum_congr rfl
  intro i _
  congr 1
  rw [weight3_product,weight3_product]
  apply Finset.prod_congr rfl
  intro e _
  by_cases h : e=d
  · subst e
    simp only [Function.update_self]
    exact weight_boundary n L hL _
  · simp [h]

theorem periodic_hat_node (n : ℕ) [NeZero n] (i k : Fin n) :
    periodicHat n i (k.val : ℝ)=if i=k then 1 else 0 := by
  have hi : (i.val : ℝ)+1 ≤ (n : ℝ) := by exact_mod_cast i.isLt
  have hk : (k.val : ℝ)+1 ≤ (n : ℝ) := by exact_mod_cast k.isLt
  have hi0 : 0 ≤ (i.val : ℝ) := Nat.cast_nonneg _
  have hk0 : 0 ≤ (k.val : ℝ) := Nat.cast_nonneg _
  rw [periodicHat,hat_zero_right ((k.val : ℝ)-(i.val : ℝ)+(n : ℝ)) (by linarith),
    hat_zero_left ((k.val : ℝ)-(i.val : ℝ)-(n : ℝ)) (by linarith),add_zero,add_zero]
  by_cases h : i=k
  · subst i
    simp [hat,ramp]
  · rw [if_neg h]
    have hv : i.val ≠ k.val := fun he => h (Fin.ext he)
    rcases lt_or_gt_of_ne hv with hlt | hgt
    · have hh : (i.val : ℝ)+1 ≤ (k.val : ℝ) := by exact_mod_cast hlt
      exact hat_zero_right _ (by linarith)
    · have hh : (k.val : ℝ)+1 ≤ (i.val : ℝ) := by exact_mod_cast hgt
      exact hat_zero_left _ (by linarith)

theorem weight_node (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (i k : Fin n) :
    weight n L i (((k.val : ℝ)+1/2)*L/(n : ℝ))=if i=k then 1 else 0 := by
  have hn : (n : ℝ) ≠ 0 := by exact_mod_cast NeZero.ne n
  have he : (n : ℝ)*(((k.val : ℝ)+1/2)*L/(n : ℝ))/L-1/2=(k.val : ℝ) := by
    field_simp
    ring
  rw [weight,he,periodic_hat_node]

def node (n : ℕ) (L : ℝ) (i : Cell n) : Space :=
  fun d => (((coordinates i d).val : ℝ)+1/2)*L/(n : ℝ)

theorem weight3_node (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (i k : Cell n) :
    weight3 n L i (node n L k)=if i=k then 1 else 0 := by
  simp only [weight3,node,coordinates,Matrix.cons_val_zero,Matrix.cons_val_one,
    Matrix.cons_val_two,Matrix.vecHead,Matrix.vecTail,weight_node n L hL]
  by_cases h0 : i.1=k.1 <;> by_cases h1 : i.2.1=k.2.1 <;> by_cases h2 : i.2.2=k.2.2 <;>
    simp_all [Prod.ext_iff]

theorem reconstruction_nodes (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (u : Cell n → State) (i : Cell n) :
    reconstruct n L u (node n L i)=u i := by
  simp [reconstruct,weight3_node n L hL]

theorem reconstructed_physical_error_lower_bound (n : ℕ) [NeZero n] (u : Cell n → State)
    (hu : ∀ i, u i ∈ EulerPhysicalRegion.region) (U : Point → State)
    (T L : ℝ) (hT : 0 ≤ T) (hL : 0 < L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L)
    (hUT : ∀ y ∈ cube L, U (Fin.cons T y) ∈ EulerPhysicalRegion.region) :
    ((∫ y, EulerEntropy.entropy (U (Fin.cons 0 y)) ∂cubeMeasure L)-
      (1/(n : ℝ)^3)*∑ i, EulerEntropy.entropy (u i))/160 ≤
      EulerEntropyError.maxComponentError (cubeMeasure L) (fun y => U (Fin.cons T y))
        (reconstruct n L u) := by
  have he := physical_error_from_initial_entropy U (reconstruct n L u) T L hT hL
    hU hphys heuler hperiodic hUT (reconstruction_continuous n L u).continuousOn
    (reconstruction_in_region n L hL u hu)
  have hr := reconstruction_entropy n L hL u hu
  have ha := le_abs_self ((∫ y, EulerEntropy.entropy (U (Fin.cons 0 y)) ∂cubeMeasure L)-
    (∫ y, EulerEntropy.entropy (reconstruct n L u y) ∂cubeMeasure L))
  rw [abs_sub_comm] at ha
  linarith only [he,hr,ha]

end EulerHatReconstruction


-- Exact normalized spatial averages of the specified nonlinear initial family.
noncomputable section
namespace EulerInitialAverages
open MeasureTheory EulerEntropyIntegral EulerInitialRegion
open scoped BigOperators
abbrev State := Fin 5 → ℝ

def period : ℝ := 2*Real.pi
theorem period_positive : 0 < period := by unfold period; positivity

def lineAverage (f : ℝ → ℝ) : ℝ := (1/period)*(∫ x in (0 : ℝ)..period, f x)
def average (f : Space → ℝ) : ℝ := ∫ x, f x ∂cubeMeasure period
def tensor (f g h : ℝ → ℝ) (x : Space) : ℝ := f (x 0)*g (x 1)*h (x 2)

@[fun_prop]
theorem tensor_continuous (f g h : ℝ → ℝ) (hf : Continuous f) (hg : Continuous g) (hh : Continuous h) :
    Continuous (tensor f g h) :=
  ((hf.comp (continuous_apply 0)).mul (hg.comp (continuous_apply 1))).mul (hh.comp (continuous_apply 2))

theorem average_tensor (f g h : ℝ → ℝ) :
    average (tensor f g h)=lineAverage f*lineAverage g*lineAverage h := by
  have he : tensor f g h=(fun x : Space => ∏ d : Fin 3, (![f,g,h] d) (x d)) := by
    funext x
    simp [tensor,Fin.prod_univ_succ,mul_assoc]
  rw [average,cube_integral period period_positive.le,he,EulerHatReconstruction.cube_product_measure,
    integral_fintype_prod_eq_prod]
  simp only [Fin.prod_univ_succ,Matrix.cons_val_zero,Matrix.cons_val_succ,Fin.prod_univ_zero,
    mul_one,integral_Icc_eq_integral_Ioc,← intervalIntegral.integral_of_le period_positive.le,smul_eq_mul]
  dsimp [lineAverage]
  ring

theorem average_add (f g : Space → ℝ) (hf : Continuous f) (hg : Continuous g) :
    average (fun x => f x+g x)=average f+average g :=
  integral_add (cube_integrable period f hf.continuousOn) (cube_integrable period g hg.continuousOn)

theorem average_sub (f g : Space → ℝ) (hf : Continuous f) (hg : Continuous g) :
    average (fun x => f x-g x)=average f-average g :=
  integral_sub (cube_integrable period f hf.continuousOn) (cube_integrable period g hg.continuousOn)

theorem average_const_mul (a : ℝ) (f : Space → ℝ) :
    average (fun x => a*f x)=a*average f := integral_const_mul _ _

theorem average_mul_const (f : Space → ℝ) (a : ℝ) :
    average (fun x => f x*a)=average f*a := integral_mul_const _ _

theorem average_const (a : ℝ) : average (fun _ => a)=a := by
  simp [average,integral_const,measureReal_def,cube_measure_univ period period_positive]

theorem line_average_const (a : ℝ) : lineAverage (fun _ => a)=a := by
  dsimp [lineAverage]
  rw [intervalIntegral.integral_const]
  simp [ne_of_gt period_positive]

theorem line_average_sin : lineAverage Real.sin=0 := by
  simp [lineAverage,period,Real.cos_two_pi]

theorem line_average_cos : lineAverage Real.cos=0 := by
  simp [lineAverage,period,Real.sin_two_pi]

theorem line_average_cos_two : lineAverage (fun x => Real.cos (2*x))=0 := by
  unfold lineAverage
  rw [intervalIntegral.integral_comp_mul_left _ (by norm_num : (2 : ℝ) ≠ 0)]
  simp [period,Real.sin_two_mul]

theorem line_average_sin_sq : lineAverage (fun x => Real.sin x^2)=1/2 := by
  unfold lineAverage
  rw [integral_sin_sq]
  simp [period,Real.sin_two_pi,Real.cos_two_pi]
  field_simp

theorem line_average_cos_sq : lineAverage (fun x => Real.cos x^2)=1/2 := by
  unfold lineAverage
  rw [integral_cos_sq]
  simp [period,Real.sin_two_pi,Real.cos_two_pi]
  field_simp

theorem line_average_sin_cos : lineAverage (fun x => Real.sin x*Real.cos x)=0 := by
  unfold lineAverage
  rw [integral_sin_mul_cos₁]
  simp [period,Real.sin_two_pi]

theorem line_average_sin_cos_sq : lineAverage (fun x => Real.sin x*Real.cos x^2)=0 := by
  unfold lineAverage
  rw [integral_sin_mul_cos_sq]
  simp [period,Real.cos_two_pi]

theorem line_average_sin_cube : lineAverage (fun x => Real.sin x^3)=0 := by
  unfold lineAverage
  rw [integral_sin_pow_three]
  simp [period,Real.cos_two_pi]

def field (A delta : ℝ) (x : Space) : State := initialState A delta (x 0) (x 1) (x 2)

theorem field_continuous (A delta : ℝ) : Continuous (field A delta) := by
  apply continuous_pi
  intro j
  fin_cases j
  all_goals dsimp [field,initialState,density,pressure,velocity,EulerAdmissible.primitive,EulerAdmissible.kinetic]
  all_goals fun_prop

theorem average_density (A delta : ℝ) : average (fun x => field A delta x 0)=1 := by
  have he : (fun x => field A delta x 0)=
      (fun x => 1+delta*tensor Real.sin Real.sin Real.sin x) := by rfl
  rw [he]
  simp (disch := fun_prop) only [average_add,average_const_mul,average_const,average_tensor,
    line_average_sin,mul_zero,add_zero]

theorem average_pressure (A : ℝ) : average (fun x => pressure A (x 0) (x 1) (x 2))=1 := by
  have he : (fun x : Space => pressure A (x 0) (x 1) (x 2))=
      (fun x => 1+(A^2/16)*(
        tensor (fun s => Real.cos (2*s)) (fun _ => 1) (fun s => Real.cos (2*s)) x+
        2*tensor (fun s => Real.cos (2*s)) (fun _ => 1) (fun _ => 1) x+
        tensor (fun _ => 1) (fun s => Real.cos (2*s)) (fun s => Real.cos (2*s)) x+
        2*tensor (fun _ => 1) (fun s => Real.cos (2*s)) (fun _ => 1) x)) := by
    funext x
    dsimp [pressure,tensor]
    ring
  rw [he]
  simp (disch := fun_prop) only [average_add,average_const_mul,average_const,average_tensor,
    line_average_cos_two,line_average_const,mul_zero,zero_mul,add_zero]

theorem average_momentum_x (A delta : ℝ) : average (fun x => field A delta x 1)=0 := by
  have he : (fun x => field A delta x 1)=(fun x =>
      A*tensor Real.sin Real.cos Real.cos x+
      delta*A*tensor (fun s => Real.sin s^2) (fun s => Real.sin s*Real.cos s)
        (fun s => Real.sin s*Real.cos s) x) := by
    funext x
    dsimp [field,initialState,EulerAdmissible.primitive,density,velocity,tensor]
    ring
  rw [he]
  simp (disch := fun_prop) only [average_add,average_const_mul,average_tensor,
    line_average_sin,line_average_cos,line_average_sin_sq,line_average_sin_cos,
    mul_zero,add_zero]

theorem average_momentum_y (A delta : ℝ) : average (fun x => field A delta x 2)=0 := by
  have he : (fun x => field A delta x 2)=(fun x =>
      -A*tensor Real.cos Real.sin Real.cos x-
      delta*A*tensor (fun s => Real.sin s*Real.cos s) (fun s => Real.sin s^2)
        (fun s => Real.sin s*Real.cos s) x) := by
    funext x
    dsimp [field,initialState,EulerAdmissible.primitive,density,velocity,tensor]
    ring
  rw [he]
  simp (disch := fun_prop) only [average_sub,average_const_mul,average_tensor,
    line_average_sin,line_average_cos,line_average_sin_sq,line_average_sin_cos,
    mul_zero,zero_mul,sub_self]

theorem average_momentum_z (A delta : ℝ) : average (fun x => field A delta x 3)=0 := by
  have he : (fun x => field A delta x 3)=(fun _ => (0 : ℝ)) := by
    funext x
    simp [field,initialState,EulerAdmissible.primitive,velocity]
  rw [he,average_const]

theorem average_energy (A delta : ℝ) : average (fun x => field A delta x 4)=1+A^2/8 := by
  have he : (fun x => field A delta x 4)=(fun x =>
      pressure A (x 0) (x 1) (x 2)+
      (A^2/2)*tensor (fun s => Real.sin s^2) (fun s => Real.cos s^2) (fun s => Real.cos s^2) x+
      (A^2/2)*tensor (fun s => Real.cos s^2) (fun s => Real.sin s^2) (fun s => Real.cos s^2) x+
      (delta*A^2/2)*tensor (fun s => Real.sin s^3) (fun s => Real.sin s*Real.cos s^2)
        (fun s => Real.sin s*Real.cos s^2) x+
      (delta*A^2/2)*tensor (fun s => Real.sin s*Real.cos s^2) (fun s => Real.sin s^3)
        (fun s => Real.sin s*Real.cos s^2) x) := by
    funext x
    dsimp [field,initialState,EulerAdmissible.primitive,EulerAdmissible.kinetic,density,velocity,tensor]
    ring
  rw [he]
  have hp : Continuous (fun x : Space => pressure A (x 0) (x 1) (x 2)) := by
    unfold pressure
    fun_prop
  simp (disch := fun_prop) only [average_add,average_const_mul,average_tensor,average_pressure,
    line_average_sin_sq,line_average_cos_sq,line_average_sin_cube,line_average_sin_cos_sq,
    mul_zero,add_zero]
  ring

theorem average_density_pressure_error (A delta : ℝ) :
    average (fun x => density delta (x 0) (x 1) (x 2)*(pressure A (x 0) (x 1) (x 2)-1))=0 := by
  have he : (fun x : Space => density delta (x 0) (x 1) (x 2)*(pressure A (x 0) (x 1) (x 2)-1))=
      (fun x => (pressure A (x 0) (x 1) (x 2)-1)+(delta*A^2/16)*(
        tensor (fun s => Real.sin s*Real.cos (2*s)) Real.sin (fun s => Real.sin s*Real.cos (2*s)) x+
        2*tensor (fun s => Real.sin s*Real.cos (2*s)) Real.sin Real.sin x+
        tensor Real.sin (fun s => Real.sin s*Real.cos (2*s)) (fun s => Real.sin s*Real.cos (2*s)) x+
        2*tensor Real.sin (fun s => Real.sin s*Real.cos (2*s)) Real.sin x)) := by
    funext x
    dsimp [density,pressure,tensor]
    ring
  rw [he]
  have hp : Continuous (fun x : Space => pressure A (x 0) (x 1) (x 2)) := by unfold pressure; fun_prop
  simp (disch := fun_prop) only [average_add,average_sub,average_const_mul,average_const,
    average_tensor,average_pressure,line_average_sin,mul_zero,zero_mul,add_zero,sub_self]

def meanInitial (A : ℝ) : State := ![1,0,0,0,1+A^2/8]

theorem initial_integral_mean (A delta : ℝ) :
    (∫ x, field A delta x ∂cubeMeasure period)=meanInitial A := by
  funext j
  have hi := cube_integrable period (field A delta) (field_continuous A delta).continuousOn
  have hp := (ContinuousLinearMap.proj j : State →L[ℝ] ℝ).integral_comp_comm hi
  change average (fun x => field A delta x j)=(∫ x, field A delta x ∂cubeMeasure period) j at hp
  rw [← hp]
  fin_cases j
  · exact average_density A delta
  · exact average_momentum_x A delta
  · exact average_momentum_y A delta
  · exact average_momentum_z A delta
  · exact average_energy A delta

end EulerInitialAverages


-- A uniform positive exact initial entropy excess for the entire target family.
noncomputable section
namespace EulerInitialExcess
open MeasureTheory EulerEntropyIntegral EulerInitialAverages

theorem entropy_lower (u : EulerEntropy.State) (hu : EulerAdmissible.Admissible u) :
    -(u 0)*(EulerAdmissible.pressure u-1)+2*(u 0-1) ≤ EulerEntropy.entropy u := by
  have hp := mul_le_mul_of_nonneg_left (Real.log_le_sub_one_of_pos hu.2) hu.1.le
  have hr := mul_le_mul_of_nonneg_left (Real.one_sub_inv_le_log_of_pos hu.1) hu.1.le
  have hn : u 0 ≠ 0 := ne_of_gt hu.1
  simp only [mul_sub,mul_one,mul_inv_cancel₀ hn] at hr
  dsimp [EulerEntropy.entropy]
  nlinarith only [hp,hr]

theorem mean_entropy (A : ℝ) : EulerEntropy.entropy (meanInitial A)= -Real.log (1+A^2/8) := by
  simp [meanInitial,EulerEntropy.entropy,EulerAdmissible.pressure]

theorem initial_entropy_nonnegative (A delta : ℝ)
    (hA0 : 1/2 ≤ A) (hA1 : A ≤ 1) (hd0 : -1/20 ≤ delta) (hd1 : delta ≤ 1/20) :
    0 ≤ average (fun x => EulerEntropy.entropy (field A delta x)) := by
  have hk (x : Space) := EulerInitialRegion.initial_family_in_region A delta (x 0) (x 1) (x 2)
    hA0 hA1 hd0 hd1
  have hadm (x : Space) := EulerPhysicalRegion.region_admissible _ (hk x)
  have hc := entropy_continuousOn period (field A delta) (field_continuous A delta).continuousOn
    (fun x _ => hk x)
  have hi := cube_integrable period _ hc
  let lower := fun x : Space =>
    -EulerInitialRegion.density delta (x 0) (x 1) (x 2)*(EulerInitialRegion.pressure A (x 0) (x 1) (x 2)-1)+
      2*(EulerInitialRegion.density delta (x 0) (x 1) (x 2)-1)
  have hlc : Continuous lower := by unfold lower EulerInitialRegion.density EulerInitialRegion.pressure; fun_prop
  have hlow : average lower ≤ average (fun x => EulerEntropy.entropy (field A delta x)) := by
    apply integral_mono (cube_integrable period _ hlc.continuousOn) hi
    intro x
    have hh := entropy_lower (field A delta x) (hadm x)
    simpa only [field,EulerInitialRegion.initialState,EulerAdmissible.pressure_primitive] using hh
  have hlo : average lower=0 := by
    have he : lower=(fun x =>
        (-1)*(EulerInitialRegion.density delta (x 0) (x 1) (x 2)*(EulerInitialRegion.pressure A (x 0) (x 1) (x 2)-1))+
        2*(field A delta x 0-1)) := by
      funext x
      dsimp [lower,field,EulerInitialRegion.initialState,EulerAdmissible.primitive]
      ring
    rw [he]
    have hr : Continuous (fun x : Space => EulerInitialRegion.density delta (x 0) (x 1) (x 2)) := by
      unfold EulerInitialRegion.density
      fun_prop
    have hp : Continuous (fun x : Space => EulerInitialRegion.pressure A (x 0) (x 1) (x 2)) := by
      unfold EulerInitialRegion.pressure
      fun_prop
    have hf : Continuous (fun x => field A delta x 0) := (continuous_apply 0).comp (field_continuous A delta)
    simp (disch := fun_prop) only [average_add,average_const_mul,average_sub,average_const,
      average_density_pressure_error,average_density,sub_self,mul_zero,add_zero]
  rwa [hlo] at hlow

theorem log_mean_energy_lower (A : ℝ) (hA : 1/2 ≤ A) : (1 : ℝ)/33 ≤ Real.log (1+A^2/8) := by
  have hA2 : (1 : ℝ)/4 ≤ A^2 := by nlinarith [sq_nonneg (A-1/2)]
  have hpos : 0 < 1+A^2/8 := by positivity
  have hh := Real.one_sub_inv_le_log_of_pos hpos
  have hi : (1+A^2/8)⁻¹ ≤ 32/33 := by
    rw [← one_div]
    apply (div_le_iff₀ hpos).mpr
    nlinarith only [hA2]
  linarith

theorem uniform_initial_excess (A delta : ℝ)
    (hA0 : 1/2 ≤ A) (hA1 : A ≤ 1) (hd0 : -1/20 ≤ delta) (hd1 : delta ≤ 1/20) :
    (1 : ℝ)/33 ≤ average (fun x => EulerEntropy.entropy (field A delta x))-
      EulerEntropy.entropy (∫ x, field A delta x ∂cubeMeasure period) := by
  rw [initial_integral_mean,mean_entropy]
  linarith [initial_entropy_nonnegative A delta hA0 hA1 hd0 hd1,log_mean_energy_lower A hA0]

end EulerInitialExcess


-- Physical accuracy forces nonzero final grid excess for the actual family.
noncomputable section
namespace EulerExcessAccuracy
open MeasureTheory EulerEntropyIntegral EulerInitialAverages EulerInitialExcess
open EulerEntropy EulerPhysicalRegion EulerGridPoincare EulerEntropyError
open scoped BigOperators
abbrev State := Fin 5 → ℝ

theorem integral_component (L : ℝ) (u : Space → State) (hc : ContinuousOn u (cube L)) (j : Fin 5) :
    (∫ x, u x j ∂cubeMeasure L)=(∫ x, u x ∂cubeMeasure L) j := by
  exact (ContinuousLinearMap.proj j : State →L[ℝ] ℝ).integral_comp_comm (cube_integrable L u hc)

theorem mean_component_error (L : ℝ) (u v : Space → State)
    (hcu : ContinuousOn u (cube L)) (hcv : ContinuousOn v (cube L)) (j : Fin 5) :
    |(∫ x, v x ∂cubeMeasure L) j-(∫ x, u x ∂cubeMeasure L) j| ≤
      ∫ x, |v x j-u x j| ∂cubeMeasure L := by
  have hu : Integrable (fun x => u x j) (cubeMeasure L) :=
    cube_integrable L _ ((continuous_apply j).continuousOn.comp hcu (fun _ _ => Set.mem_univ _))
  have hv : Integrable (fun x => v x j) (cubeMeasure L) :=
    cube_integrable L _ ((continuous_apply j).continuousOn.comp hcv (fun _ _ => Set.mem_univ _))
  rw [← integral_component L v hcv j,← integral_component L u hcu j,← integral_sub hv hu]
  exact abs_integral_le_integral_abs

theorem mean_entropy_error (L : ℝ) (u v : Space → State)
    (hcu : ContinuousOn u (cube L)) (hcv : ContinuousOn v (cube L))
    (hu : (∫ x, u x ∂cubeMeasure L) ∈ region) (hv : (∫ x, v x ∂cubeMeasure L) ∈ region) :
    |entropy (∫ x, v x ∂cubeMeasure L)-entropy (∫ x, u x ∂cubeMeasure L)| ≤
      160*maxComponentError (cubeMeasure L) u v := by
  have he := entropy_lipschitz _ _ hu hv
  have hj (j : Fin 5) : |(∫ x, v x ∂cubeMeasure L) j-(∫ x, u x ∂cubeMeasure L) j| ≤
      maxComponentError (cubeMeasure L) u v :=
    (mean_component_error L u v hcu hcv j).trans
      (Finset.le_sup' (f := fun j : Fin 5 => ∫ x, |v x j-u x j| ∂cubeMeasure L) (Finset.mem_univ j))
  have hs := Finset.sum_le_sum (fun j (_ : j ∈ Finset.univ) => hj j)
  simp only [Finset.sum_const,Finset.card_univ,Fintype.card_fin,nsmul_eq_mul] at hs
  norm_num only [Nat.cast_ofNat] at hs
  change _ ≤ 32*(∑ j : Fin 5, |(∫ x, v x ∂cubeMeasure L) j-(∫ x, u x ∂cubeMeasure L) j|) at he
  linarith only [he,hs]

theorem reconstruction_excess_accuracy (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L)
    (u : Cell n → State) (hu : ∀ i, u i ∈ region) (U : Space → State)
    (hUc : ContinuousOn U (cube L)) (hU : ∀ x ∈ cube L, U x ∈ region)
    (hUm : (∫ x, U x ∂cubeMeasure L) ∈ region) :
    (∫ x, entropy (U x) ∂cubeMeasure L)-entropy (∫ x, U x ∂cubeMeasure L)-
      320*maxComponentError (cubeMeasure L) U (EulerHatReconstruction.reconstruct n L u) ≤
      (1/(n : ℝ)^3)*EulerEntropyDecay.entropyExcess u := by
  let V := EulerHatReconstruction.reconstruct n L u
  have hVc : ContinuousOn V (cube L) := (EulerHatReconstruction.reconstruction_continuous n L u).continuousOn
  have hV := EulerHatReconstruction.reconstruction_in_region n L hL u hu
  have he := normalized_error_lower_bound L U V hUc hVc hU hV
  have hvmean : (∫ x, V x ∂cubeMeasure L)=meanState u := EulerHatReconstruction.reconstruction_mean n L hL u
  have hVm : (∫ x, V x ∂cubeMeasure L) ∈ region := by
    rw [hvmean]
    exact EulerEntropyDecay.mean_in_region u hu
  have hm := mean_entropy_error L U V hUc hVc hUm hVm
  have hrec := EulerHatReconstruction.reconstruction_entropy n L hL u hu
  have hae := (abs_le.mp ((div_le_iff₀ (by norm_num : (0 : ℝ) < 160)).mp he)).1
  have ham := (abs_le.mp hm).2
  rw [hvmean] at ham
  have hn : (n : ℝ) ≠ 0 := by exact_mod_cast NeZero.ne n
  have hc : (Fintype.card (Cell n) : ℝ)=(n : ℝ)^3 := by simp [Cell,EulerGridPoincare.Cell,pow_succ]; ring
  have hex : (1/(n : ℝ)^3)*EulerEntropyDecay.entropyExcess u=
      (1/(n : ℝ)^3)*(∑ i, entropy (u i))-entropy (meanState u) := by
    rw [EulerEntropyDecay.entropyExcess,hc,EulerEntropyCandidateStep.totalEntropy]
    field_simp
  rw [hex]
  change _ ≤ (1/(n : ℝ)^3)*(∑ i, entropy (u i)) at hrec
  change _ ≤ _*maxComponentError (cubeMeasure L) U V at ham
  change _ ≤ _ at hae
  change _-320*maxComponentError (cubeMeasure L) U V ≤ _
  linarith only [hae,ham,hrec]

theorem mean_initial_in_region (A : ℝ) (hA0 : 1/2 ≤ A) (hA1 : A ≤ 1) : meanInitial A ∈ region := by
  have hA2 : A^2 ≤ 1 := (sq_le_one_iff_abs_le_one A).mpr (abs_le.mpr ⟨by linarith,hA1⟩)
  change (1/4 : ℝ) ≤ 1 ∧ (1 : ℝ) ≤ 4 ∧ 1+A^2/8 ≤ 4 ∧
    1/4 ≤ EulerAdmissible.pressure (meanInitial A)
  have hp : EulerAdmissible.pressure (meanInitial A)=1+A^2/8 := by
    change (1+A^2/8)-((0 : ℝ)^2+0^2+0^2)/(2*1)=1+A^2/8
    ring
  rw [hp]
  norm_num
  constructor <;> nlinarith [sq_nonneg A]

theorem family_final_excess_bound (n : ℕ) [NeZero n] (u : Cell n → State)
    (hu : ∀ i, u i ∈ region) (U : Point → State) (T A delta : ℝ)
    (hT : 0 ≤ T) (hA0 : 1/2 ≤ A) (hA1 : A ≤ 1) (hd0 : -1/20 ≤ delta) (hd1 : delta ≤ 1/20)
    (hU : ∀ x ∈ box T period, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T period, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T period, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T period)
    (hinit : ∀ y ∈ cube period, U (Fin.cons 0 y)=field A delta y)
    (hUT : ∀ y ∈ cube period, U (Fin.cons T y) ∈ region) :
    (1 : ℝ)/33-320*maxComponentError (cubeMeasure period) (fun y => U (Fin.cons T y))
      (EulerHatReconstruction.reconstruct n period u) ≤ (1/(n : ℝ)^3)*EulerEntropyDecay.entropyExcess u := by
  have hc := slice_continuousOn U T period T ⟨hT,le_rfl⟩ hU
  have hi : (fun y => U (Fin.cons 0 y)) =ᵐ[cubeMeasure period] field A delta :=
    (cube_ae_mem period).mono (fun y hy => hinit y hy)
  have hm := normalized_conserved_integral U T period hT period_positive.le hU hphys heuler hperiodic
  rw [integral_congr_ae hi,initial_integral_mean] at hm
  have he := normalized_entropy_conservation U T period hT period_positive.le hU hphys heuler hperiodic
  have hei : (fun y => entropy (U (Fin.cons 0 y))) =ᵐ[cubeMeasure period]
      (fun y => entropy (field A delta y)) := hi.mono (fun _ hy => congrArg entropy hy)
  rw [integral_congr_ae hei] at he
  have hmean : (∫ y, U (Fin.cons T y) ∂cubeMeasure period) ∈ region := by
    rw [hm]
    exact mean_initial_in_region A hA0 hA1
  have hh := reconstruction_excess_accuracy n period period_positive u hu _ hc hUT hmean
  rw [he,hm] at hh
  have h0 := uniform_initial_excess A delta hA0 hA1 hd0 hd1
  rw [initial_integral_mean] at h0
  change (1 : ℝ)/33 ≤ (∫ y, entropy (field A delta y) ∂cubeMeasure period)-entropy (meanInitial A) at h0
  linarith only [hh,h0]

end EulerExcessAccuracy
