import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic

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
