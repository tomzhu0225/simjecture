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
