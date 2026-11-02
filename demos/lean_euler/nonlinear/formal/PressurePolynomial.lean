-- Quantitative directional entropy bounds from the actual conserved state.
noncomputable section
namespace EulerPressurePolynomial
open EulerEntropy EulerEntropyTaylor EulerPhysicalRegion
abbrev State := Fin 5 → ℝ

def quadratic (u : State) : ℝ := 2*u 0*u 4-(u 1^2+u 2^2+u 3^2)
def firstCoefficient (u k : State) : ℝ :=
  2*k 0*u 4+2*u 0*k 4-2*(u 1*k 1+u 2*k 2+u 3*k 3)
def secondCoefficient (k : State) : ℝ := 2*k 0*k 4-(k 1^2+k 2^2+k 3^2)

theorem quadratic_pressure (u : State) (hr : u 0 ≠ 0) :
    quadratic u=2*u 0*EulerAdmissible.pressure u := by
  dsimp [quadratic,EulerAdmissible.pressure]
  field_simp

theorem quadratic_positive (u : State) (hu : EulerAdmissible.Admissible u) : 0 < quadratic u := by
  rw [quadratic_pressure u (ne_of_gt hu.1)]
  exact mul_pos (mul_pos (by norm_num) hu.1) hu.2

theorem admissible_of_quadratic (u : State) (hr : 0 < u 0) (hQ : 0 < quadratic u) :
    EulerAdmissible.Admissible u := by
  refine ⟨hr,?_⟩
  rw [quadratic_pressure u (ne_of_gt hr)] at hQ
  exact (mul_pos_iff_of_pos_left (mul_pos (by norm_num) hr)).mp hQ

theorem quadratic_path (u k : State) (s : ℝ) :
    quadratic (u+s • k)=quadratic u+s*firstCoefficient u k+s^2*secondCoefficient k := by
  dsimp [quadratic,firstCoefficient,secondCoefficient]
  ring

theorem first_coefficient_path (u k : State) (s : ℝ) :
    firstCoefficient (u+s • k) k=firstCoefficient u k+2*s*secondCoefficient k := by
  dsimp [firstCoefficient,secondCoefficient]
  ring

theorem first_coefficient_pressure (u k : State) (hr : u 0 ≠ 0) :
    firstCoefficient u k=2*u 0*pressureD u k+2*EulerAdmissible.pressure u*k 0 := by
  dsimp [firstCoefficient,pressureD,EulerAdmissible.pressure]
  field_simp
  ring

theorem hessian_polynomial (u k : State) (hu : EulerAdmissible.Admissible u) :
    conservativeHessian u k=3*k 0^2/u 0-2*k 0*firstCoefficient u k/quadratic u-
      2*u 0*secondCoefficient k/quadratic u+u 0*(firstCoefficient u k/quadratic u)^2 := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  rw [conservative_hessian_squares u k hu,quadratic_pressure u hr,first_coefficient_pressure u k hr]
  dsimp [thermalShift,shiftedMomentumSquared,secondCoefficient,pressureD]
  field_simp
  ring

theorem hessian_smul (u k : State) (s : ℝ) (hu : EulerAdmissible.Admissible u) :
    conservativeHessian u (s • k)=s^2*conservativeHessian u k := by
  rw [hessian_polynomial u (s • k) hu,hessian_polynomial u k hu]
  dsimp [firstCoefficient,secondCoefficient]
  ring

def firstBound (u k : State) : ℝ := |firstCoefficient u k|+2*|secondCoefficient k|
def curvatureBound (u k : State) : ℝ :=
  6*k 0^2/u 0+4*|k 0| *firstBound u k/quadratic u+
    6*u 0*|secondCoefficient k|/quadratic u+6*u 0*(firstBound u k/quadratic u)^2

theorem first_bound_nonnegative (u k : State) : 0 ≤ firstBound u k := by
  dsimp [firstBound]
  positivity

theorem curvature_bound_nonnegative (u k : State) (hu : EulerAdmissible.Admissible u) :
    0 ≤ curvatureBound u k := by
  have hr := hu.1
  have hQ := quadratic_positive u hu
  have hf := first_bound_nonnegative u k
  dsimp [curvatureBound]
  positivity

theorem path_density_bounds (u k : State) (s : ℝ) (hs : 0 ≤ s)
    (hsmall : s*|k 0| ≤ u 0/2) :
    u 0/2 ≤ (u+s • k) 0 ∧ (u+s • k) 0 ≤ 3*u 0/2 := by
  have hlow := mul_le_mul_of_nonneg_left (neg_abs_le (k 0)) hs
  have hupp := mul_le_mul_of_nonneg_left (le_abs_self (k 0)) hs
  change u 0/2 ≤ u 0+s*k 0 ∧ u 0+s*k 0 ≤ 3*u 0/2
  constructor <;> linarith

theorem path_quadratic_bound (u k : State) (s : ℝ) (hs : 0 ≤ s) (hs1 : s ≤ 1)
    (hsmall : s*(|firstCoefficient u k|+|secondCoefficient k|) ≤ quadratic u/2) :
    quadratic u/2 ≤ quadratic (u+s • k) := by
  have h1 := mul_le_mul_of_nonneg_left (neg_abs_le (firstCoefficient u k)) hs
  have h2 := mul_le_mul_of_nonneg_left (neg_abs_le (secondCoefficient k)) (sq_nonneg s)
  have hsq : s^2 ≤ s := by nlinarith
  have hm := mul_le_mul_of_nonneg_right hsq (abs_nonneg (secondCoefficient k))
  rw [quadratic_path]
  nlinarith

theorem path_first_bound (u k : State) (s : ℝ) (hs : 0 ≤ s) (hs1 : s ≤ 1) :
    |firstCoefficient (u+s • k) k| ≤ firstBound u k := by
  rw [first_coefficient_path]
  have hh := abs_add_le (firstCoefficient u k) (2*s*secondCoefficient k)
  rw [abs_mul,abs_mul,abs_of_nonneg (by norm_num : (0 : ℝ) ≤ 2),abs_of_nonneg hs] at hh
  have hm := mul_le_mul_of_nonneg_right hs1 (abs_nonneg (secondCoefficient k))
  dsimp [firstBound]
  nlinarith

theorem reciprocal_half_bound (a b : ℝ) (ha : 0 < a) (hab : a/2 ≤ b) : 1/b ≤ 2/a := by
  calc
    _ ≤ 1/(a/2) := one_div_le_one_div_of_le (by positivity) hab
    _ = _ := by ring

theorem scalar_curvature_upper (R Q x y kr c f W : ℝ)
    (hR : 0 < R) (hQ : 0 < Q) (hx : R/2 ≤ x) (hxup : x ≤ 3*R/2)
    (hy : Q/2 ≤ y) (hf : |f| ≤ W) :
    3*kr^2/x-2*kr*f/y-2*x*c/y+x*(f/y)^2 ≤
      6*kr^2/R+4*|kr| *W/Q+6*R*|c|/Q+6*R*(W/Q)^2 := by
  have hxpos : 0 < x := lt_of_lt_of_le (by positivity) hx
  have hypos : 0 < y := lt_of_lt_of_le (by positivity) hy
  have hW : 0 ≤ W := (abs_nonneg f).trans hf
  have hxi := reciprocal_half_bound R x hR hx
  have hyi := reciprocal_half_bound Q y hQ hy
  have h0 : 3*kr^2/x ≤ 6*kr^2/R := by
    calc
      _ = (3*kr^2)*(1/x) := by ring
      _ ≤ (3*kr^2)*(2/R) := mul_le_mul_of_nonneg_left hxi (by positivity)
      _ = _ := by ring
  have hab : -(kr*f) ≤ |kr| *W := by
    calc
      _ ≤ |kr*f| := neg_le_abs _
      _ = |kr| *|f| := abs_mul _ _
      _ ≤ _ := mul_le_mul_of_nonneg_left hf (abs_nonneg kr)
  have h1 : -(2*kr*f/y) ≤ 4*|kr| *W/Q := by
    calc
      _ = (2/y)*(-(kr*f)) := by ring
      _ ≤ (2/y)*(|kr| *W) := mul_le_mul_of_nonneg_left hab (by positivity)
      _ = (2*|kr| *W)*(1/y) := by ring
      _ ≤ (2*|kr| *W)*(2/Q) := mul_le_mul_of_nonneg_left hyi (by positivity)
      _ = _ := by ring
  have h2 : -(2*x*c/y) ≤ 6*R*|c|/Q := by
    calc
      _ = (2*x/y)*(-c) := by ring
      _ ≤ (2*x/y)*|c| := mul_le_mul_of_nonneg_left (neg_le_abs c) (by positivity)
      _ = (2*|c| *(1/y))*x := by ring
      _ ≤ (2*|c| *(1/y))*(3*R/2) := mul_le_mul_of_nonneg_left hxup (by positivity)
      _ = (3*R*|c|)*(1/y) := by ring
      _ ≤ (3*R*|c|)*(2/Q) := mul_le_mul_of_nonneg_left hyi (by positivity)
      _ = _ := by ring
  have hratio : |f/y| ≤ 2*W/Q := by
    calc
      _ = |f| *(1/y) := by rw [abs_div,abs_of_pos hypos]; ring
      _ ≤ W*(1/y) := mul_le_mul_of_nonneg_right hf (by positivity)
      _ ≤ W*(2/Q) := mul_le_mul_of_nonneg_left hyi hW
      _ = _ := by ring
  have hsquare : (f/y)^2 ≤ (2*W/Q)^2 := by
    have hh := mul_self_le_mul_self (abs_nonneg (f/y)) hratio
    nlinarith [sq_abs (f/y)]
  have h3 : x*(f/y)^2 ≤ 6*R*(W/Q)^2 := by
    calc
      _ ≤ (3*R/2)*(f/y)^2 := mul_le_mul_of_nonneg_right hxup (sq_nonneg _)
      _ ≤ (3*R/2)*(2*W/Q)^2 := mul_le_mul_of_nonneg_left hsquare (by positivity)
      _ = _ := by ring
  linarith

theorem path_curvature_bound (u k : State) (hu : EulerAdmissible.Admissible u)
    (s : ℝ) (hs : 0 ≤ s) (hs1 : s ≤ 1)
    (hrsmall : s*|k 0| ≤ u 0/2)
    (hQsmall : s*(|firstCoefficient u k|+|secondCoefficient k|) ≤ quadratic u/2) :
    EulerAdmissible.Admissible (u+s • k) ∧
      conservativeHessian (u+s • k) k ≤ curvatureBound u k := by
  have hr := path_density_bounds u k s hs hrsmall
  have hQ := path_quadratic_bound u k s hs hs1 hQsmall
  have hQpos := quadratic_positive u hu
  have hnew := admissible_of_quadratic (u+s • k)
    (lt_of_lt_of_le (by linarith [hu.1]) hr.1) (lt_of_lt_of_le (by positivity) hQ)
  refine ⟨hnew,?_⟩
  rw [hessian_polynomial _ _ hnew]
  exact scalar_curvature_upper (u 0) (quadratic u) ((u+s • k) 0) (quadratic (u+s • k))
    (k 0) (secondCoefficient k) (firstCoefficient (u+s • k) k) (firstBound u k)
    hu.1 hQpos hr.1 hr.2 hQ (path_first_bound u k s hs hs1)

end EulerPressurePolynomial
