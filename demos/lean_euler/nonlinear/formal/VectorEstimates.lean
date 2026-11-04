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
