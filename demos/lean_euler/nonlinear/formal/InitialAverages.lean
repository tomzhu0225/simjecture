import Mathlib.Analysis.SpecialFunctions.Integrals.Basic
import Mathlib.MeasureTheory.Integral.Pi

-- Exact normalized spatial averages of the specified nonlinear initial family.
noncomputable section
namespace EulerInitialAverages
open MeasureTheory EulerEntropyIntegral EulerInitialRegion
open scoped BigOperators
abbrev State := Fin 5 → ℝ

def period : ℝ := 2*Real.pi
theorem period_positive : 0 < period := by unfold period; positivity

def lineAverage (f : ℝ → ℝ) : ℝ := (1/period)*(∫ x in (0 : ℝ)..period, f x)
def average (f : Space → ℝ) : ℝ := ∫ x, f x ∂cubeMeasure period
def tensor (f g h : ℝ → ℝ) (x : Space) : ℝ := f (x 0)*g (x 1)*h (x 2)

@[fun_prop]
theorem tensor_continuous (f g h : ℝ → ℝ) (hf : Continuous f) (hg : Continuous g) (hh : Continuous h) :
    Continuous (tensor f g h) :=
  ((hf.comp (continuous_apply 0)).mul (hg.comp (continuous_apply 1))).mul (hh.comp (continuous_apply 2))

theorem average_tensor (f g h : ℝ → ℝ) :
    average (tensor f g h)=lineAverage f*lineAverage g*lineAverage h := by
  have he : tensor f g h=(fun x : Space => ∏ d : Fin 3, (![f,g,h] d) (x d)) := by
    funext x
    simp [tensor,Fin.prod_univ_succ,mul_assoc]
  rw [average,cube_integral period period_positive.le,he,EulerHatReconstruction.cube_product_measure,
    integral_fintype_prod_eq_prod]
  simp only [Fin.prod_univ_succ,Matrix.cons_val_zero,Matrix.cons_val_succ,Fin.prod_univ_zero,
    mul_one,integral_Icc_eq_integral_Ioc,← intervalIntegral.integral_of_le period_positive.le,smul_eq_mul]
  dsimp [lineAverage]
  ring

theorem average_add (f g : Space → ℝ) (hf : Continuous f) (hg : Continuous g) :
    average (fun x => f x+g x)=average f+average g :=
  integral_add (cube_integrable period f hf.continuousOn) (cube_integrable period g hg.continuousOn)

theorem average_sub (f g : Space → ℝ) (hf : Continuous f) (hg : Continuous g) :
    average (fun x => f x-g x)=average f-average g :=
  integral_sub (cube_integrable period f hf.continuousOn) (cube_integrable period g hg.continuousOn)

theorem average_const_mul (a : ℝ) (f : Space → ℝ) :
    average (fun x => a*f x)=a*average f := integral_const_mul _ _

theorem average_mul_const (f : Space → ℝ) (a : ℝ) :
    average (fun x => f x*a)=average f*a := integral_mul_const _ _

theorem average_const (a : ℝ) : average (fun _ => a)=a := by
  simp [average,integral_const,measureReal_def,cube_measure_univ period period_positive]

theorem line_average_const (a : ℝ) : lineAverage (fun _ => a)=a := by
  dsimp [lineAverage]
  rw [intervalIntegral.integral_const]
  simp [ne_of_gt period_positive]

theorem line_average_sin : lineAverage Real.sin=0 := by
  simp [lineAverage,period,Real.cos_two_pi]

theorem line_average_cos : lineAverage Real.cos=0 := by
  simp [lineAverage,period,Real.sin_two_pi]

theorem line_average_cos_two : lineAverage (fun x => Real.cos (2*x))=0 := by
  unfold lineAverage
  rw [intervalIntegral.integral_comp_mul_left _ (by norm_num : (2 : ℝ) ≠ 0)]
  simp [period,Real.sin_two_mul]

theorem line_average_sin_sq : lineAverage (fun x => Real.sin x^2)=1/2 := by
  unfold lineAverage
  rw [integral_sin_sq]
  simp [period,Real.sin_two_pi,Real.cos_two_pi]
  field_simp

theorem line_average_cos_sq : lineAverage (fun x => Real.cos x^2)=1/2 := by
  unfold lineAverage
  rw [integral_cos_sq]
  simp [period,Real.sin_two_pi,Real.cos_two_pi]
  field_simp

theorem line_average_sin_cos : lineAverage (fun x => Real.sin x*Real.cos x)=0 := by
  unfold lineAverage
  rw [integral_sin_mul_cos₁]
  simp [period,Real.sin_two_pi]

theorem line_average_sin_cos_sq : lineAverage (fun x => Real.sin x*Real.cos x^2)=0 := by
  unfold lineAverage
  rw [integral_sin_mul_cos_sq]
  simp [period,Real.cos_two_pi]

theorem line_average_sin_cube : lineAverage (fun x => Real.sin x^3)=0 := by
  unfold lineAverage
  rw [integral_sin_pow_three]
  simp [period,Real.cos_two_pi]

def field (A delta : ℝ) (x : Space) : State := initialState A delta (x 0) (x 1) (x 2)

theorem field_continuous (A delta : ℝ) : Continuous (field A delta) := by
  apply continuous_pi
  intro j
  fin_cases j
  all_goals dsimp [field,initialState,density,pressure,velocity,EulerAdmissible.primitive,EulerAdmissible.kinetic]
  all_goals fun_prop

theorem average_density (A delta : ℝ) : average (fun x => field A delta x 0)=1 := by
  have he : (fun x => field A delta x 0)=
      (fun x => 1+delta*tensor Real.sin Real.sin Real.sin x) := by rfl
  rw [he]
  simp (disch := fun_prop) only [average_add,average_const_mul,average_const,average_tensor,
    line_average_sin,mul_zero,add_zero]

theorem average_pressure (A : ℝ) : average (fun x => pressure A (x 0) (x 1) (x 2))=1 := by
  have he : (fun x : Space => pressure A (x 0) (x 1) (x 2))=
      (fun x => 1+(A^2/16)*(
        tensor (fun s => Real.cos (2*s)) (fun _ => 1) (fun s => Real.cos (2*s)) x+
        2*tensor (fun s => Real.cos (2*s)) (fun _ => 1) (fun _ => 1) x+
        tensor (fun _ => 1) (fun s => Real.cos (2*s)) (fun s => Real.cos (2*s)) x+
        2*tensor (fun _ => 1) (fun s => Real.cos (2*s)) (fun _ => 1) x)) := by
    funext x
    dsimp [pressure,tensor]
    ring
  rw [he]
  simp (disch := fun_prop) only [average_add,average_const_mul,average_const,average_tensor,
    line_average_cos_two,line_average_const,mul_zero,zero_mul,add_zero]

theorem average_momentum_x (A delta : ℝ) : average (fun x => field A delta x 1)=0 := by
  have he : (fun x => field A delta x 1)=(fun x =>
      A*tensor Real.sin Real.cos Real.cos x+
      delta*A*tensor (fun s => Real.sin s^2) (fun s => Real.sin s*Real.cos s)
        (fun s => Real.sin s*Real.cos s) x) := by
    funext x
    dsimp [field,initialState,EulerAdmissible.primitive,density,velocity,tensor]
    ring
  rw [he]
  simp (disch := fun_prop) only [average_add,average_const_mul,average_tensor,
    line_average_sin,line_average_cos,line_average_sin_sq,line_average_sin_cos,
    mul_zero,add_zero]

theorem average_momentum_y (A delta : ℝ) : average (fun x => field A delta x 2)=0 := by
  have he : (fun x => field A delta x 2)=(fun x =>
      -A*tensor Real.cos Real.sin Real.cos x-
      delta*A*tensor (fun s => Real.sin s*Real.cos s) (fun s => Real.sin s^2)
        (fun s => Real.sin s*Real.cos s) x) := by
    funext x
    dsimp [field,initialState,EulerAdmissible.primitive,density,velocity,tensor]
    ring
  rw [he]
  simp (disch := fun_prop) only [average_sub,average_const_mul,average_tensor,
    line_average_sin,line_average_cos,line_average_sin_sq,line_average_sin_cos,
    mul_zero,zero_mul,sub_self]

theorem average_momentum_z (A delta : ℝ) : average (fun x => field A delta x 3)=0 := by
  have he : (fun x => field A delta x 3)=(fun _ => (0 : ℝ)) := by
    funext x
    simp [field,initialState,EulerAdmissible.primitive,velocity]
  rw [he,average_const]

theorem average_energy (A delta : ℝ) : average (fun x => field A delta x 4)=1+A^2/8 := by
  have he : (fun x => field A delta x 4)=(fun x =>
      pressure A (x 0) (x 1) (x 2)+
      (A^2/2)*tensor (fun s => Real.sin s^2) (fun s => Real.cos s^2) (fun s => Real.cos s^2) x+
      (A^2/2)*tensor (fun s => Real.cos s^2) (fun s => Real.sin s^2) (fun s => Real.cos s^2) x+
      (delta*A^2/2)*tensor (fun s => Real.sin s^3) (fun s => Real.sin s*Real.cos s^2)
        (fun s => Real.sin s*Real.cos s^2) x+
      (delta*A^2/2)*tensor (fun s => Real.sin s*Real.cos s^2) (fun s => Real.sin s^3)
        (fun s => Real.sin s*Real.cos s^2) x) := by
    funext x
    dsimp [field,initialState,EulerAdmissible.primitive,EulerAdmissible.kinetic,density,velocity,tensor]
    ring
  rw [he]
  have hp : Continuous (fun x : Space => pressure A (x 0) (x 1) (x 2)) := by
    unfold pressure
    fun_prop
  simp (disch := fun_prop) only [average_add,average_const_mul,average_tensor,average_pressure,
    line_average_sin_sq,line_average_cos_sq,line_average_sin_cube,line_average_sin_cos_sq,
    mul_zero,add_zero]
  ring

theorem average_density_pressure_error (A delta : ℝ) :
    average (fun x => density delta (x 0) (x 1) (x 2)*(pressure A (x 0) (x 1) (x 2)-1))=0 := by
  have he : (fun x : Space => density delta (x 0) (x 1) (x 2)*(pressure A (x 0) (x 1) (x 2)-1))=
      (fun x => (pressure A (x 0) (x 1) (x 2)-1)+(delta*A^2/16)*(
        tensor (fun s => Real.sin s*Real.cos (2*s)) Real.sin (fun s => Real.sin s*Real.cos (2*s)) x+
        2*tensor (fun s => Real.sin s*Real.cos (2*s)) Real.sin Real.sin x+
        tensor Real.sin (fun s => Real.sin s*Real.cos (2*s)) (fun s => Real.sin s*Real.cos (2*s)) x+
        2*tensor Real.sin (fun s => Real.sin s*Real.cos (2*s)) Real.sin x)) := by
    funext x
    dsimp [density,pressure,tensor]
    ring
  rw [he]
  have hp : Continuous (fun x : Space => pressure A (x 0) (x 1) (x 2)) := by unfold pressure; fun_prop
  simp (disch := fun_prop) only [average_add,average_sub,average_const_mul,average_const,
    average_tensor,average_pressure,line_average_sin,mul_zero,zero_mul,add_zero,sub_self]

def meanInitial (A : ℝ) : State := ![1,0,0,0,1+A^2/8]

theorem initial_integral_mean (A delta : ℝ) :
    (∫ x, field A delta x ∂cubeMeasure period)=meanInitial A := by
  funext j
  have hi := cube_integrable period (field A delta) (field_continuous A delta).continuousOn
  have hp := (ContinuousLinearMap.proj j : State →L[ℝ] ℝ).integral_comp_comm hi
  change average (fun x => field A delta x j)=(∫ x, field A delta x ∂cubeMeasure period) j at hp
  rw [← hp]
  fin_cases j
  · exact average_density A delta
  · exact average_momentum_x A delta
  · exact average_momentum_y A delta
  · exact average_momentum_z A delta
  · exact average_energy A delta

end EulerInitialAverages
