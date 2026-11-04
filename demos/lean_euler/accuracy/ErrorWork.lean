import Mathlib.Algebra.Order.BigOperators.Group.Finset
import Mathlib.Algebra.BigOperators.Ring.Finset
import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Ring

noncomputable section
namespace ErrorWork
open scoped BigOperators

-- A scalar convex stencil, reusable for monotone transport subproblems.
def stencil {ι : Type} [Fintype ι] (w u : ι → ℝ) : ℝ := ∑ i, w i*u i

theorem stencil_nonexpansive {ι : Type} [Fintype ι] (w u v : ι → ℝ)
    (positive : ∀ i, 0 ≤ w i) (partition : ∑ i, w i = 1)
    (E : ℝ) (error : ∀ i, |u i-v i| ≤ E) :
    |stencil w u-stencil w v| ≤ E := by
  have identity : stencil w u-stencil w v = ∑ i, w i*(u i-v i) := by
    simp [stencil, mul_sub, Finset.sum_sub_distrib]
  rw [identity]
  calc
    |∑ i, w i*(u i-v i)| ≤ ∑ i, |w i*(u i-v i)| := Finset.abs_sum_le_sum_abs _ _
    _ = ∑ i, w i*|u i-v i| := by simp [abs_mul, abs_of_nonneg (positive _)]
    _ ≤ ∑ i, w i*E := Finset.sum_le_sum (fun i _ => mul_le_mul_of_nonneg_left (error i) (positive i))
    _ = E := by rw [← Finset.sum_mul, partition, one_mul]

-- If a nonexpansive scheme has a certified one-step defect at most delta,
-- the total error is no greater than initial error plus the sum of defects.
-- This does not discharge a nonlinear Euler stability or truncation hypothesis.
theorem accumulate_error (e : Nat → ℝ) (delta E0 : ℝ)
    (initial : e 0 ≤ E0) (oneStep : ∀ k, e (k+1) ≤ e k+delta) (steps : Nat) :
    e steps ≤ E0 + steps*delta := by
  induction steps with
  | zero => simpa using initial
  | succ k ih =>
    have h := oneStep k
    push_cast
    nlinarith

def cellStageWork (n stages : Nat) : Nat := n^3*stages

theorem first_order_budget (e : Nat → ℝ) (n m : Nat) (C K eps : ℝ)
    (hn : 0 < (n : ℝ)) (hC : 0 ≤ C)
    (initial : e 0 ≤ 0)
    (defect : ∀ j, e (j+1) ≤ e j + C/(n:ℝ)^2)
    (stepBound : (m:ℝ) ≤ K*n)
    (resolution : K*C/(n:ℝ) ≤ eps) : e m ≤ eps := by
  have accumulation := accumulate_error e (C/(n:ℝ)^2) 0 initial defect m
  have localNonnegative : 0 ≤ C/(n:ℝ)^2 := div_nonneg hC (sq_nonneg _)
  have scaled := mul_le_mul_of_nonneg_right stepBound localNonnegative
  have cancel : K*(n:ℝ)*(C/(n:ℝ)^2) = K*C/(n:ℝ) := by
    field_simp [ne_of_gt hn]
  rw [cancel] at scaled
  linarith

theorem total_work_bound (n m k : Nat) (steps : m ≤ k*n) :
    cellStageWork n m ≤ k*n^4 := by
  have h := Nat.mul_le_mul_left (n^3) steps
  simpa [cellStageWork, pow_succ, Nat.mul_assoc, Nat.mul_comm, Nat.mul_left_comm] using h

-- Error-based admission is distinct from resource minimization. This theorem
-- deliberately requires the caller's error certificate; measured errors alone
-- are not silently turned into a PDE proof.
theorem smallest_certified_grid_minimizes_work (n n0 k : Nat)
    (leastGrid : n0 ≤ n) : cellStageWork n0 (k*n0) ≤ cellStageWork n (k*n) := by
  have cells : n0^3 ≤ n^3 := Nat.pow_le_pow_left leastGrid 3
  have steps := Nat.mul_le_mul_left k leastGrid
  exact Nat.mul_le_mul cells steps
end ErrorWork
