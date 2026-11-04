import Mathlib.MeasureTheory.Integral.Bochner.ContinuousLinearMap

-- Physical accuracy forces nonzero final grid excess for the actual family.
noncomputable section
namespace EulerExcessAccuracy
open MeasureTheory EulerEntropyIntegral EulerInitialAverages EulerInitialExcess
open EulerEntropy EulerPhysicalRegion EulerGridPoincare EulerEntropyError
open scoped BigOperators
abbrev State := Fin 5 → ℝ

theorem integral_component (L : ℝ) (u : Space → State) (hc : ContinuousOn u (cube L)) (j : Fin 5) :
    (∫ x, u x j ∂cubeMeasure L)=(∫ x, u x ∂cubeMeasure L) j := by
  exact (ContinuousLinearMap.proj j : State →L[ℝ] ℝ).integral_comp_comm (cube_integrable L u hc)

theorem mean_component_error (L : ℝ) (u v : Space → State)
    (hcu : ContinuousOn u (cube L)) (hcv : ContinuousOn v (cube L)) (j : Fin 5) :
    |(∫ x, v x ∂cubeMeasure L) j-(∫ x, u x ∂cubeMeasure L) j| ≤
      ∫ x, |v x j-u x j| ∂cubeMeasure L := by
  have hu : Integrable (fun x => u x j) (cubeMeasure L) :=
    cube_integrable L _ ((continuous_apply j).continuousOn.comp hcu (fun _ _ => Set.mem_univ _))
  have hv : Integrable (fun x => v x j) (cubeMeasure L) :=
    cube_integrable L _ ((continuous_apply j).continuousOn.comp hcv (fun _ _ => Set.mem_univ _))
  rw [← integral_component L v hcv j,← integral_component L u hcu j,← integral_sub hv hu]
  exact abs_integral_le_integral_abs

theorem mean_entropy_error (L : ℝ) (u v : Space → State)
    (hcu : ContinuousOn u (cube L)) (hcv : ContinuousOn v (cube L))
    (hu : (∫ x, u x ∂cubeMeasure L) ∈ region) (hv : (∫ x, v x ∂cubeMeasure L) ∈ region) :
    |entropy (∫ x, v x ∂cubeMeasure L)-entropy (∫ x, u x ∂cubeMeasure L)| ≤
      160*maxComponentError (cubeMeasure L) u v := by
  have he := entropy_lipschitz _ _ hu hv
  have hj (j : Fin 5) : |(∫ x, v x ∂cubeMeasure L) j-(∫ x, u x ∂cubeMeasure L) j| ≤
      maxComponentError (cubeMeasure L) u v :=
    (mean_component_error L u v hcu hcv j).trans
      (Finset.le_sup' (f := fun j : Fin 5 => ∫ x, |v x j-u x j| ∂cubeMeasure L) (Finset.mem_univ j))
  have hs := Finset.sum_le_sum (fun j (_ : j ∈ Finset.univ) => hj j)
  simp only [Finset.sum_const,Finset.card_univ,Fintype.card_fin,nsmul_eq_mul] at hs
  norm_num only [Nat.cast_ofNat] at hs
  change _ ≤ 32*(∑ j : Fin 5, |(∫ x, v x ∂cubeMeasure L) j-(∫ x, u x ∂cubeMeasure L) j|) at he
  linarith only [he,hs]

theorem reconstruction_excess_accuracy (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L)
    (u : Cell n → State) (hu : ∀ i, u i ∈ region) (U : Space → State)
    (hUc : ContinuousOn U (cube L)) (hU : ∀ x ∈ cube L, U x ∈ region)
    (hUm : (∫ x, U x ∂cubeMeasure L) ∈ region) :
    (∫ x, entropy (U x) ∂cubeMeasure L)-entropy (∫ x, U x ∂cubeMeasure L)-
      320*maxComponentError (cubeMeasure L) U (EulerHatReconstruction.reconstruct n L u) ≤
      (1/(n : ℝ)^3)*EulerEntropyDecay.entropyExcess u := by
  let V := EulerHatReconstruction.reconstruct n L u
  have hVc : ContinuousOn V (cube L) := (EulerHatReconstruction.reconstruction_continuous n L u).continuousOn
  have hV := EulerHatReconstruction.reconstruction_in_region n L hL u hu
  have he := normalized_error_lower_bound L U V hUc hVc hU hV
  have hvmean : (∫ x, V x ∂cubeMeasure L)=meanState u := EulerHatReconstruction.reconstruction_mean n L hL u
  have hVm : (∫ x, V x ∂cubeMeasure L) ∈ region := by
    rw [hvmean]
    exact EulerEntropyDecay.mean_in_region u hu
  have hm := mean_entropy_error L U V hUc hVc hUm hVm
  have hrec := EulerHatReconstruction.reconstruction_entropy n L hL u hu
  have hae := (abs_le.mp ((div_le_iff₀ (by norm_num : (0 : ℝ) < 160)).mp he)).1
  have ham := (abs_le.mp hm).2
  rw [hvmean] at ham
  have hn : (n : ℝ) ≠ 0 := by exact_mod_cast NeZero.ne n
  have hc : (Fintype.card (Cell n) : ℝ)=(n : ℝ)^3 := by simp [Cell,EulerGridPoincare.Cell,pow_succ]; ring
  have hex : (1/(n : ℝ)^3)*EulerEntropyDecay.entropyExcess u=
      (1/(n : ℝ)^3)*(∑ i, entropy (u i))-entropy (meanState u) := by
    rw [EulerEntropyDecay.entropyExcess,hc,EulerEntropyCandidateStep.totalEntropy]
    field_simp
  rw [hex]
  change _ ≤ (1/(n : ℝ)^3)*(∑ i, entropy (u i)) at hrec
  change _ ≤ _*maxComponentError (cubeMeasure L) U V at ham
  change _ ≤ _ at hae
  change _-320*maxComponentError (cubeMeasure L) U V ≤ _
  linarith only [hae,ham,hrec]

theorem mean_initial_in_region (A : ℝ) (hA0 : 1/2 ≤ A) (hA1 : A ≤ 1) : meanInitial A ∈ region := by
  have hA2 : A^2 ≤ 1 := (sq_le_one_iff_abs_le_one A).mpr (abs_le.mpr ⟨by linarith,hA1⟩)
  change (1/4 : ℝ) ≤ 1 ∧ (1 : ℝ) ≤ 4 ∧ 1+A^2/8 ≤ 4 ∧
    1/4 ≤ EulerAdmissible.pressure (meanInitial A)
  have hp : EulerAdmissible.pressure (meanInitial A)=1+A^2/8 := by
    change (1+A^2/8)-((0 : ℝ)^2+0^2+0^2)/(2*1)=1+A^2/8
    ring
  rw [hp]
  norm_num
  constructor <;> nlinarith [sq_nonneg A]

theorem family_final_excess_bound (n : ℕ) [NeZero n] (u : Cell n → State)
    (hu : ∀ i, u i ∈ region) (U : Point → State) (T A delta : ℝ)
    (hT : 0 ≤ T) (hA0 : 1/2 ≤ A) (hA1 : A ≤ 1) (hd0 : -1/20 ≤ delta) (hd1 : delta ≤ 1/20)
    (hU : ∀ x ∈ box T period, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T period, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T period, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T period)
    (hinit : ∀ y ∈ cube period, U (Fin.cons 0 y)=field A delta y)
    (hUT : ∀ y ∈ cube period, U (Fin.cons T y) ∈ region) :
    (1 : ℝ)/33-320*maxComponentError (cubeMeasure period) (fun y => U (Fin.cons T y))
      (EulerHatReconstruction.reconstruct n period u) ≤ (1/(n : ℝ)^3)*EulerEntropyDecay.entropyExcess u := by
  have hc := slice_continuousOn U T period T ⟨hT,le_rfl⟩ hU
  have hi : (fun y => U (Fin.cons 0 y)) =ᵐ[cubeMeasure period] field A delta :=
    (cube_ae_mem period).mono (fun y hy => hinit y hy)
  have hm := normalized_conserved_integral U T period hT period_positive.le hU hphys heuler hperiodic
  rw [integral_congr_ae hi,initial_integral_mean] at hm
  have he := normalized_entropy_conservation U T period hT period_positive.le hU hphys heuler hperiodic
  have hei : (fun y => entropy (U (Fin.cons 0 y))) =ᵐ[cubeMeasure period]
      (fun y => entropy (field A delta y)) := hi.mono (fun _ hy => congrArg entropy hy)
  rw [integral_congr_ae hei] at he
  have hmean : (∫ y, U (Fin.cons T y) ∂cubeMeasure period) ∈ region := by
    rw [hm]
    exact mean_initial_in_region A hA0 hA1
  have hh := reconstruction_excess_accuracy n period period_positive u hu _ hc hUT hmean
  rw [he,hm] at hh
  have h0 := uniform_initial_excess A delta hA0 hA1 hd0 hd1
  rw [initial_integral_mean] at h0
  change (1 : ℝ)/33 ≤ (∫ y, entropy (field A delta y) ∂cubeMeasure period)-entropy (meanInitial A) at h0
  linarith only [hh,h0]

end EulerExcessAccuracy
