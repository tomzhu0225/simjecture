import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Tactic.LinearCombination

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
