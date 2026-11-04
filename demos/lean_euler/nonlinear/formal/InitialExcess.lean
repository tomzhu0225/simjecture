import Mathlib.Analysis.SpecialFunctions.Log.Basic

-- A uniform positive exact initial entropy excess for the entire target family.
noncomputable section
namespace EulerInitialExcess
open MeasureTheory EulerEntropyIntegral EulerInitialAverages

theorem entropy_lower (u : EulerEntropy.State) (hu : EulerAdmissible.Admissible u) :
    -(u 0)*(EulerAdmissible.pressure u-1)+2*(u 0-1) ≤ EulerEntropy.entropy u := by
  have hp := mul_le_mul_of_nonneg_left (Real.log_le_sub_one_of_pos hu.2) hu.1.le
  have hr := mul_le_mul_of_nonneg_left (Real.one_sub_inv_le_log_of_pos hu.1) hu.1.le
  have hn : u 0 ≠ 0 := ne_of_gt hu.1
  simp only [mul_sub,mul_one,mul_inv_cancel₀ hn] at hr
  dsimp [EulerEntropy.entropy]
  nlinarith only [hp,hr]

theorem mean_entropy (A : ℝ) : EulerEntropy.entropy (meanInitial A)= -Real.log (1+A^2/8) := by
  simp [meanInitial,EulerEntropy.entropy,EulerAdmissible.pressure]

theorem initial_entropy_nonnegative (A delta : ℝ)
    (hA0 : 1/2 ≤ A) (hA1 : A ≤ 1) (hd0 : -1/20 ≤ delta) (hd1 : delta ≤ 1/20) :
    0 ≤ average (fun x => EulerEntropy.entropy (field A delta x)) := by
  have hk (x : Space) := EulerInitialRegion.initial_family_in_region A delta (x 0) (x 1) (x 2)
    hA0 hA1 hd0 hd1
  have hadm (x : Space) := EulerPhysicalRegion.region_admissible _ (hk x)
  have hc := entropy_continuousOn period (field A delta) (field_continuous A delta).continuousOn
    (fun x _ => hk x)
  have hi := cube_integrable period _ hc
  let lower := fun x : Space =>
    -EulerInitialRegion.density delta (x 0) (x 1) (x 2)*(EulerInitialRegion.pressure A (x 0) (x 1) (x 2)-1)+
      2*(EulerInitialRegion.density delta (x 0) (x 1) (x 2)-1)
  have hlc : Continuous lower := by unfold lower EulerInitialRegion.density EulerInitialRegion.pressure; fun_prop
  have hlow : average lower ≤ average (fun x => EulerEntropy.entropy (field A delta x)) := by
    apply integral_mono (cube_integrable period _ hlc.continuousOn) hi
    intro x
    have hh := entropy_lower (field A delta x) (hadm x)
    simpa only [field,EulerInitialRegion.initialState,EulerAdmissible.pressure_primitive] using hh
  have hlo : average lower=0 := by
    have he : lower=(fun x =>
        (-1)*(EulerInitialRegion.density delta (x 0) (x 1) (x 2)*(EulerInitialRegion.pressure A (x 0) (x 1) (x 2)-1))+
        2*(field A delta x 0-1)) := by
      funext x
      dsimp [lower,field,EulerInitialRegion.initialState,EulerAdmissible.primitive]
      ring
    rw [he]
    have hr : Continuous (fun x : Space => EulerInitialRegion.density delta (x 0) (x 1) (x 2)) := by
      unfold EulerInitialRegion.density
      fun_prop
    have hp : Continuous (fun x : Space => EulerInitialRegion.pressure A (x 0) (x 1) (x 2)) := by
      unfold EulerInitialRegion.pressure
      fun_prop
    have hf : Continuous (fun x => field A delta x 0) := (continuous_apply 0).comp (field_continuous A delta)
    simp (disch := fun_prop) only [average_add,average_const_mul,average_sub,average_const,
      average_density_pressure_error,average_density,sub_self,mul_zero,add_zero]
  rwa [hlo] at hlow

theorem log_mean_energy_lower (A : ℝ) (hA : 1/2 ≤ A) : (1 : ℝ)/33 ≤ Real.log (1+A^2/8) := by
  have hA2 : (1 : ℝ)/4 ≤ A^2 := by nlinarith [sq_nonneg (A-1/2)]
  have hpos : 0 < 1+A^2/8 := by positivity
  have hh := Real.one_sub_inv_le_log_of_pos hpos
  have hi : (1+A^2/8)⁻¹ ≤ 32/33 := by
    rw [← one_div]
    apply (div_le_iff₀ hpos).mpr
    nlinarith only [hA2]
  linarith

theorem uniform_initial_excess (A delta : ℝ)
    (hA0 : 1/2 ≤ A) (hA1 : A ≤ 1) (hd0 : -1/20 ≤ delta) (hd1 : delta ≤ 1/20) :
    (1 : ℝ)/33 ≤ average (fun x => EulerEntropy.entropy (field A delta x))-
      EulerEntropy.entropy (∫ x, field A delta x ∂cubeMeasure period) := by
  rw [initial_integral_mean,mean_entropy]
  linarith [initial_entropy_nonnegative A delta hA0 hA1 hd0 hd1,log_mean_energy_lower A hA0]

end EulerInitialExcess
