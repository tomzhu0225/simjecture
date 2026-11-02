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
