import Mathlib.Algebra.BigOperators.Intervals
import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Data.Real.Basic
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.Ring

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
