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
