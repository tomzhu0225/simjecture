import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Data.Real.Basic
import Mathlib.Tactic.Ring

namespace FiniteVolume
open scoped BigOperators

-- A periodic predecessor is a permutation of the finite cells. Uniform volume
-- and dt/dx factors are incorporated into each shared outgoing face flux.
def update {ι : Type*} (U F : ι → ℝ) (prev : Equiv.Perm ι) (i : ι) : ℝ :=
  U i - (F i - F (prev i))

theorem conservation {ι : Type*} [Fintype ι] (U F : ι → ℝ)
    (prev : Equiv.Perm ι) :
    ∑ i, update U F prev i = ∑ i, U i := by
  simp only [update, Finset.sum_sub_distrib]
  rw [Equiv.sum_comp prev]
  ring

-- Applies to a Cartesian product grid and each of the five Euler components.
-- Each axis uses one shared flux per face and a periodic neighbor permutation.
def update3D {ι : Type*} (U Fx Fy Fz : ι → ℝ)
    (px py pz : Equiv.Perm ι) (i : ι) : ℝ :=
  update (update (update U Fx px) Fy py) Fz pz i

theorem conservation3D {ι : Type*} [Fintype ι] (U Fx Fy Fz : ι → ℝ)
    (px py pz : Equiv.Perm ι) :
    ∑ i, update3D U Fx Fy Fz px py pz i = ∑ i, U i := by
  simp only [update3D, conservation]

theorem constant_state {ι : Type*} (u f : ℝ) (prev : Equiv.Perm ι) (i : ι) :
    update (fun _ => u) (fun _ => f) prev i = u := by
  simp [update]
end FiniteVolume
