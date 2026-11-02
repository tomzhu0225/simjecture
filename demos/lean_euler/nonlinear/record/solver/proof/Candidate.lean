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
