import Mathlib.MeasureTheory.Integral.Bochner.Basic

-- A direct link between physical entropy and conserved-component L1 errors.
-- This does not supply an exact Euler solution or prove its integral balance.
noncomputable section
namespace EulerEntropyError
open EulerEntropy EulerPhysicalRegion
open scoped BigOperators
abbrev State := Fin 5 → ℝ

theorem box_log_bound (x : ℝ) (hlo : 1/4 ≤ x) (hhi : x ≤ 4) : |Real.log x| ≤ 3 := by
  have hx : 0 < x := by linarith
  have hlog := Real.log_le_sub_one_of_pos hx
  have hi := (EulerCoefficientBounds.reciprocal_bounds x hlo).2
  have hilog := Real.log_le_sub_one_of_pos (inv_pos.mpr hx)
  rw [Real.log_inv] at hilog
  rw [one_div] at hi
  exact abs_le.mpr ⟨by linarith,by linarith⟩

theorem gradient_component_bound (u : State) (hu : u ∈ region) (j : Fin 5) :
    |gradient u j| ≤ 32 := by
  have hphys := region_admissible u hu
  have hrpos := hphys.1
  have hppos := hphys.2
  have hr := ne_of_gt hphys.1
  have hp := ne_of_gt hphys.2
  have hlogr := abs_le.mp (box_log_bound (u 0) hu.1 hu.2.1)
  have hlogp := abs_le.mp (box_log_bound (EulerAdmissible.pressure u) hu.2.2.2 (pressure_upper u hu))
  let q := (u 1^2+u 2^2+u 3^2)/(2*u 0*EulerAdmissible.pressure u)
  have hq0 : 0 ≤ q := by dsimp [q]; positivity
  have he : q=(u 4-EulerAdmissible.pressure u)/EulerAdmissible.pressure u := by
    dsimp [q,EulerAdmissible.pressure]
    field_simp
    ring
  have hq15 : q ≤ 15 := by
    rw [he]
    apply (div_le_iff₀ hphys.2).mpr
    linarith [hu.2.2.1,hu.2.2.2]
  have hm (i : Fin 3) : |u ⟨i.val+1,by omega⟩/EulerAdmissible.pressure u| ≤ 24 := by
    have hh := EulerECFluxBounds.quotient_abs_bound (u ⟨i.val+1,by omega⟩) (EulerAdmissible.pressure u)
      (1/4) 6 (by norm_num) hu.2.2.2 (EulerECFluxBounds.momentum_abs_bound u hu i)
    norm_num at hh
    exact hh
  have hE : |u 0/EulerAdmissible.pressure u| ≤ 16 := by
    have hh := EulerECFluxBounds.quotient_abs_bound (u 0) (EulerAdmissible.pressure u)
      (1/4) 4 (by norm_num) hu.2.2.2 (by rw [abs_of_pos hphys.1]; exact hu.2.1)
    norm_num at hh
    exact hh
  fin_cases j
  · change |2-(Real.log (EulerAdmissible.pressure u)-2*Real.log (u 0))-q| ≤ 32
    exact abs_le.mpr ⟨by linarith,by linarith⟩
  · change |u 1/EulerAdmissible.pressure u| ≤ 32
    exact (hm 0).trans (by norm_num)
  · change |u 2/EulerAdmissible.pressure u| ≤ 32
    exact (hm 1).trans (by norm_num)
  · change |u 3/EulerAdmissible.pressure u| ≤ 32
    exact (hm 2).trans (by norm_num)
  · change |(-u 0)/EulerAdmissible.pressure u| ≤ 32
    rw [neg_div,abs_neg]
    exact hE.trans (by norm_num)

def componentL1 (k : State) : ℝ := ∑ j, |k j|

theorem dot_as_sum (u k : State) : dot u k=∑ j, u j*k j := by
  simp [dot,Fin.sum_univ_succ]
  ring

theorem gradient_pairing_bound (u k : State) (hu : u ∈ region) :
    |dot (gradient u) k| ≤ 32*componentL1 k := by
  rw [dot_as_sum]
  calc
    _ ≤ ∑ j, |gradient u j*k j| := Finset.abs_sum_le_sum_abs _ _
    _ ≤ ∑ j, 32*|k j| := Finset.sum_le_sum (fun j _ => by
      rw [abs_mul]
      exact mul_le_mul_of_nonneg_right (gradient_component_bound u hu j) (abs_nonneg _))
    _ = _ := by rw [← Finset.mul_sum]; rfl

theorem entropy_lipschitz (u v : State) (hu : u ∈ region) (hv : v ∈ region) :
    |entropy v-entropy u| ≤ 32*componentL1 (v-u) := by
  let f := fun t => entropy (EulerEntropyConvexity.segment u v t)
  let df := fun t => dot (gradient (EulerEntropyConvexity.segment u v t)) (v-u)
  have hseg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :=
    EulerEntropyRegion.segment_in_region region region_convex u v hu hv t ht
  have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t :=
    entropy_derivative (EulerEntropyConvexity.segment_derivative u v t)
      (ne_of_gt (region_admissible _ (hseg t ht)).1) (ne_of_gt (region_admissible _ (hseg t ht)).2)
  obtain ⟨t,ht,he⟩ := exists_hasDerivAt_eq_slope f df (by norm_num : (0 : ℝ) < 1)
    (fun t ht => (hd t ht).continuousAt.continuousWithinAt)
    (fun t ht => hd t ⟨ht.1.le,ht.2.le⟩)
  have hh := gradient_pairing_bound (EulerEntropyConvexity.segment u v t) (v-u) (hseg t ⟨ht.1.le,ht.2.le⟩)
  change |df t| ≤ 32*componentL1 (v-u) at hh
  simp [f,EulerEntropyConvexity.segment] at he
  rwa [he] at hh

open MeasureTheory

theorem integrated_entropy_error {X : Type*} [MeasurableSpace X] (mu : Measure X) (u v : X → State)
    (hu : ∀ x, u x ∈ region) (hv : ∀ x, v x ∈ region)
    (hEu : Integrable (fun x => entropy (u x)) mu) (hEv : Integrable (fun x => entropy (v x)) mu)
    (herr : ∀ j, Integrable (fun x => |v x j-u x j|) mu) :
    |(∫ x, entropy (v x) ∂mu)-(∫ x, entropy (u x) ∂mu)| ≤
      32*∑ j, ∫ x, |v x j-u x j| ∂mu := by
  have hi : Integrable (fun x => ∑ j : Fin 5, |v x j-u x j|) mu :=
    integrable_finset_sum Finset.univ (fun j _ => herr j)
  rw [← integral_sub hEv hEu]
  calc
    _ ≤ ∫ x, |entropy (v x)-entropy (u x)| ∂mu := abs_integral_le_integral_abs
    _ ≤ ∫ x, 32*(∑ j : Fin 5, |v x j-u x j|) ∂mu :=
      integral_mono (hEv.sub hEu).abs (hi.const_mul 32) (fun x => entropy_lipschitz (u x) (v x) (hu x) (hv x))
    _ = _ := by rw [integral_const_mul,integral_finset_sum Finset.univ (fun j _ => herr j)]

theorem component_accuracy_controls_entropy {X : Type*} [MeasurableSpace X] (mu : Measure X)
    (u v : X → State) (epsilon : ℝ) (hu : ∀ x, u x ∈ region) (hv : ∀ x, v x ∈ region)
    (hEu : Integrable (fun x => entropy (u x)) mu) (hEv : Integrable (fun x => entropy (v x)) mu)
    (herr : ∀ j, Integrable (fun x => |v x j-u x j|) mu)
    (haccuracy : ∀ j, (∫ x, |v x j-u x j| ∂mu) ≤ epsilon) :
    |(∫ x, entropy (v x) ∂mu)-(∫ x, entropy (u x) ∂mu)| ≤ 160*epsilon := by
  have hh := integrated_entropy_error mu u v hu hv hEu hEv herr
  have hs := Finset.sum_le_sum (fun j (_ : j ∈ Finset.univ) => haccuracy j)
  simp only [Finset.sum_const,Finset.card_univ,Fintype.card_fin,nsmul_eq_mul] at hs
  norm_num only [Nat.cast_ofNat] at hs
  linarith

def maxComponentError {X : Type*} [MeasurableSpace X] (mu : Measure X) (u v : X → State) : ℝ :=
  Finset.univ.sup' Finset.univ_nonempty (fun j : Fin 5 => ∫ x, |v x j-u x j| ∂mu)

theorem entropy_gap_error_lower_bound {X : Type*} [MeasurableSpace X] (mu : Measure X)
    (u v : X → State) (hu : ∀ x, u x ∈ region) (hv : ∀ x, v x ∈ region)
    (hEu : Integrable (fun x => entropy (u x)) mu) (hEv : Integrable (fun x => entropy (v x)) mu)
    (herr : ∀ j, Integrable (fun x => |v x j-u x j|) mu) :
    |(∫ x, entropy (v x) ∂mu)-(∫ x, entropy (u x) ∂mu)|/160 ≤ maxComponentError mu u v := by
  have hh := component_accuracy_controls_entropy mu u v (maxComponentError mu u v) hu hv hEu hEv herr
    (fun j => Finset.le_sup' (f := fun j : Fin 5 => ∫ x, |v x j-u x j| ∂mu) (Finset.mem_univ j))
  exact (div_le_iff₀ (by norm_num : (0 : ℝ) < 160)).mpr (by linarith)

end EulerEntropyError
