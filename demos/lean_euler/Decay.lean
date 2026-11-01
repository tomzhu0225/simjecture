import Mathlib.Data.Real.Basic
import Mathlib.Tactic.NormNum

namespace Decay
-- Forward Euler for y' = -y; separate from the compressible Euler PDE.
def step (y h : ℝ) : ℝ := (1 - h) * y

theorem nonnegative (y h : ℝ) (hy : 0 ≤ y) (hh : h ≤ 1) :
    0 ≤ step y h := by
  exact mul_nonneg (sub_nonneg.mpr hh) hy

theorem counterexample : step 1 2 < 0 := by
  norm_num [step]
end Decay
