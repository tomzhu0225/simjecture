import Mathlib.Analysis.SpecialFunctions.ExpDeriv
import Mathlib.Algebra.Order.BigOperators.Ring.Finset
import Mathlib.Tactic.FunProp
import Mathlib.Analysis.Calculus.ContDiff.Operations
import Mathlib.Analysis.Calculus.ContDiff.Basic
import Mathlib.Analysis.Calculus.FDeriv.CompCLM
import Mathlib.Tactic.Module
import Mathlib.Tactic.GCongr
import Mathlib.Tactic.LinearCombination
import Mathlib.Tactic.FinCases
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith
import Mathlib.Analysis.Calculus.MeanValue
import Mathlib.MeasureTheory.Integral.DominatedConvergence
import Mathlib.MeasureTheory.Integral.Bochner.Set
import Mathlib.Analysis.Calculus.Deriv.Inv
import Mathlib.Analysis.Calculus.Deriv.Pow
import Mathlib.MeasureTheory.Integral.Pi
import Mathlib.Data.Fin.VecNotation
import Mathlib.Tactic.Positivity
import Mathlib.MeasureTheory.Integral.IntervalIntegral.FundThmCalculus
import Mathlib.Analysis.Calculus.Deriv.Mul
import Mathlib.Analysis.SpecialFunctions.Trigonometric.Basic
import Mathlib.Tactic.NormNum

noncomputable section
open MeasureTheory Set
open scoped Interval BigOperators
namespace EulerPeriodicAcoustic

-- The endpoint conditions are the only periodicity used by this integration step.
structure PeriodicPair (a L : ℝ) (p v dp dv : ℝ → ℝ) : Prop where
  continuous_p : ContinuousOn p (uIcc a (a+L))
  continuous_v : ContinuousOn v (uIcc a (a+L))
  derivative_p : ∀ x ∈ Ioo (min a (a+L)) (max a (a+L)), HasDerivAt p (dp x) x
  derivative_v : ∀ x ∈ Ioo (min a (a+L)) (max a (a+L)), HasDerivAt v (dv x) x
  integrable_dp : IntervalIntegrable dp volume a (a+L)
  integrable_dv : IntervalIntegrable dv volume a (a+L)
  seam_p : p (a+L) = p a
  seam_v : v (a+L) = v a

def acousticProduct (p v dp dv : ℝ → ℝ) (x : ℝ) : ℝ :=
  dp x * v x + p x * dv x

theorem periodic_product_integral_zero (a L : ℝ) (p v dp dv : ℝ → ℝ)
    (h : PeriodicPair a L p v dp dv) :
    (∫ x in a..(a+L), acousticProduct p v dp dv x) = 0 := by
  have hint : IntervalIntegrable (fun x => dp x * v x + p x * dv x)
      volume a (a+L) :=
    (h.integrable_dp.mul_continuousOn h.continuous_v).add
      (h.integrable_dv.continuousOn_mul h.continuous_p)
  have hi := intervalIntegral.integral_eq_sub_of_hasDeriv_right
    (h.continuous_p.mul h.continuous_v)
    (fun x hx => ((h.derivative_p x hx).mul (h.derivative_v x hx)).hasDerivWithinAt)
    hint
  change (∫ x in a..(a+L), dp x * v x + p x * dv x) = 0
  rw [hi, h.seam_p, h.seam_v, sub_self]

theorem normalized_periodic_integral_zero (a L : ℝ) (_hL : 0 < L)
    (p v dp dv : ℝ → ℝ) (h : PeriodicPair a L p v dp dv) :
    L⁻¹ * (∫ x in a..(a+L), acousticProduct p v dp dv x) = 0 := by
  rw [periodic_product_integral_zero a L p v dp dv h, mul_zero]

theorem physical_two_pi_integral_zero (p v dp dv : ℝ → ℝ)
    (h : PeriodicPair 0 (2*Real.pi) p v dp dv) :
    (2*Real.pi)⁻¹ * (∫ x in (0 : ℝ)..(2*Real.pi), acousticProduct p v dp dv x) = 0 := by
  have hL : 0 < 2*Real.pi := mul_pos (by norm_num) Real.pi_pos
  simpa using normalized_periodic_integral_zero 0 (2*Real.pi) hL p v dp dv h

theorem three_channel_integral_zero (a L : ℝ) (_hL : 0 < L)
    (p v dp dv : Fin 3 → ℝ → ℝ)
    (h : ∀ d, PeriodicPair a L (p d) (v d) (dp d) (dv d)) :
    L⁻¹ * (∑ d : Fin 3, ∫ x in a..(a+L),
      acousticProduct (p d) (v d) (dp d) (dv d) x) = 0 := by
  have hz : (∑ d : Fin 3, ∫ x in a..(a+L),
      acousticProduct (p d) (v d) (dp d) (dv d) x) = 0 := by
    apply Finset.sum_eq_zero
    intro d _hd
    exact periodic_product_integral_zero a L (p d) (v d) (dp d) (dv d) (h d)
  rw [hz, mul_zero]

-- The order is the acoustic coordinate first, then the two transverse coordinates.
-- Coordinate permutations and product-measure identification are separate steps.
theorem transverse_iterated_integral_zero (a L : ℝ) (_hL : 0 < L)
    (p v dp dv : ℝ → ℝ → ℝ → ℝ)
    (h : ∀ y z, PeriodicPair a L (p y z) (v y z) (dp y z) (dv y z)) :
    L⁻¹ * (L⁻¹ * (L⁻¹ *
      (∫ z in a..(a+L), ∫ y in a..(a+L), ∫ x in a..(a+L),
        acousticProduct (p y z) (v y z) (dp y z) (dv y z) x))) = 0 := by
  have hz : ∀ y z, (∫ x in a..(a+L),
      acousticProduct (p y z) (v y z) (dp y z) (dv y z) x) = 0 := by
    intro y z
    exact periodic_product_integral_zero a L (p y z) (v y z) (dp y z) (dv y z) (h y z)
  simp_rw [hz]
  simp

lemma nonperiodic_linear_integral (L : ℝ) (hL : 0 < L) :
    L⁻¹ * (∫ x in (0 : ℝ)..L,
      acousticProduct (fun t => t) (fun _ => 1) (fun _ => 1) (fun _ => 0) x) = 1 := by
  simp only [acousticProduct, mul_one, mul_zero, add_zero]
  simp [ne_of_gt hL]

-- Real differentiable functions with a nonzero boundary term invalidate the zero claim.
theorem nonperiodic_control (L : ℝ) (hL : 0 < L) :
    (∀ x : ℝ, HasDerivAt (fun t : ℝ => t) 1 x ∧
      HasDerivAt (fun _ : ℝ => (1 : ℝ)) 0 x) ∧
    ((fun t : ℝ => t) L ≠ (fun t : ℝ => t) 0) ∧
    (L⁻¹ * (∫ x in (0 : ℝ)..L,
      acousticProduct (fun t => t) (fun _ => 1) (fun _ => 1) (fun _ => 0) x) ≠ 0) := by
  refine ⟨?_, ne_of_gt hL, ?_⟩
  · intro x
    exact ⟨hasDerivAt_id x, hasDerivAt_const x 1⟩
  · rw [nonperiodic_linear_integral L hL]
    norm_num

end EulerPeriodicAcoustic

namespace EulerCellMoments
open MeasureTheory
open scoped BigOperators
abbrev Space := Fin 3 → ℝ
def box (a : Space) (h : ℝ) : Set Space := Set.Icc a (fun d => a d+h)
def boxMeasure (a : Space) (h : ℝ) : Measure Space :=
  ENNReal.ofReal (1/h^3) • (volume.restrict (box a h))
def boxAverage (a : Space) (h : ℝ) (f : Space → ℝ) : ℝ :=
  ∫ x, f x ∂boxMeasure a h
def tensor (f g k : ℝ → ℝ) (x : Space) : ℝ := f (x 0)*g (x 1)*k (x 2)

theorem box_product_measure (a : Space) (h : ℝ) :
    (volume : Measure Space).restrict (box a h)=
      Measure.pi (fun d => (volume : Measure ℝ).restrict (Set.Icc (a d) (a d+h))) := by
  rw [box,← Set.pi_univ_Icc]
  exact Measure.restrict_pi_pi _ _

theorem box_integral (a : Space) (h : ℝ) (hh : 0 ≤ h) (f : Space → ℝ) :
    boxAverage a h f=(1/h^3)*(∫ x in box a h, f x) := by
  rw [boxAverage,boxMeasure,integral_smul_measure,
      ENNReal.toReal_ofReal (by positivity : 0 ≤ 1/h^3),smul_eq_mul]

theorem box_measure_univ (a : Space) (h : ℝ) (hh : 0 < h) :
    boxMeasure a h Set.univ=1 := by
  have hv : (volume : Measure Space) (box a h)=ENNReal.ofReal (h^3) := by
    simp only [box,Real.volume_Icc_pi,add_sub_cancel_left,
      Finset.prod_const,Finset.card_univ,Fintype.card_fin]
    exact (ENNReal.ofReal_pow hh.le 3).symm
  rw [boxMeasure,Measure.smul_apply,Measure.restrict_apply_univ,hv]
  change ENNReal.ofReal (1/h^3)*ENNReal.ofReal (h^3)=1
  rw [← ENNReal.ofReal_mul (by positivity : 0 ≤ 1/h^3)]
  simp [ne_of_gt hh]


end EulerCellMoments

namespace EulerPeriodicBox
open MeasureTheory Set
open scoped Interval BigOperators
abbrev Space := Fin 3 → ℝ
abbrev Transverse := Fin 2 → ℝ

def cube (L : ℝ) : Set Space := EulerCellMoments.box (fun _ => 0) L
def cubeMeasure (L : ℝ) : Measure Space := EulerCellMoments.boxMeasure (fun _ => 0) L
def cubeAverage (L : ℝ) (f : Space → ℝ) : ℝ := ∫ x, f x ∂cubeMeasure L
def lineMeasure (L : ℝ) : Measure ℝ := volume.restrict (Icc 0 L)
def transverseMeasure (L : ℝ) : Measure Transverse :=
  Measure.pi (fun _ => lineMeasure L)
instance line_sigmaFinite (L : ℝ) : SigmaFinite (lineMeasure L) := by
  unfold lineMeasure
  infer_instance

instance transverse_sigmaFinite (L : ℝ) : SigmaFinite (transverseMeasure L) := by
  unfold transverseMeasure
  infer_instance

def productTerm (p v dp dv : Space → ℝ) (x : Space) : ℝ :=
  dp x * v x + p x * dv x

theorem cube_product_measure (L : ℝ) :
    (volume : Measure Space).restrict (cube L) =
      Measure.pi (fun _ : Fin 3 => lineMeasure L) := by
  simpa [cube,lineMeasure] using EulerCellMoments.box_product_measure (fun _ => 0) L

theorem transverse_product_measure (L : ℝ) :
    transverseMeasure L = (volume : Measure Transverse).restrict
      (Icc (fun _ => 0) (fun _ => L)) := by
  rw [transverseMeasure,lineMeasure,← Measure.restrict_pi_pi,Set.pi_univ_Icc]
  rfl

lemma line_integral_eq_interval (L : ℝ) (hL : 0 ≤ L) (f : ℝ → ℝ) :
    (∫ x, f x ∂lineMeasure L) = ∫ x in (0 : ℝ)..L, f x := by
  rw [lineMeasure,integral_Icc_eq_integral_Ioc,intervalIntegral.integral_of_le hL]

theorem cube_integral_sliced (L : ℝ) (hL : 0 ≤ L) (d : Fin 3)
    (f : Space → ℝ) (hf : Integrable f ((volume : Measure Space).restrict (cube L))) :
    (∫ x in cube L, f x) =
      ∫ y, (∫ t in (0 : ℝ)..L, f (d.insertNth t y)) ∂transverseMeasure L := by
  let e := MeasurableEquiv.piFinSuccAbove (fun _ : Fin 3 => ℝ) d
  have hmp : MeasurePreserving e.symm
      ((lineMeasure L).prod (transverseMeasure L))
      (Measure.pi (fun _ : Fin 3 => lineMeasure L)) :=
    (measurePreserving_piFinSuccAbove (fun _ : Fin 3 => lineMeasure L) d).symm
  have hi : Integrable f (Measure.pi (fun _ : Fin 3 => lineMeasure L)) := by
    rw [← cube_product_measure]
    exact hf
  have hcomp : Integrable (f ∘ e.symm)
      ((lineMeasure L).prod (transverseMeasure L)) :=
    (hmp.integrable_comp_emb e.symm.measurableEmbedding).2 hi
  calc
    (∫ x in cube L, f x) = ∫ x, f x ∂Measure.pi (fun _ : Fin 3 => lineMeasure L) := by
      rw [cube_product_measure]
    _ = ∫ z, f (e.symm z) ∂((lineMeasure L).prod (transverseMeasure L)) :=
      (hmp.integral_comp' f).symm
    _ = ∫ y, ∫ t, f (e.symm (t,y)) ∂lineMeasure L ∂transverseMeasure L :=
      integral_prod_symm _ hcomp
    _ = ∫ y, (∫ t in (0 : ℝ)..L, f (d.insertNth t y)) ∂transverseMeasure L := by
      apply integral_congr_ae
      exact Filter.Eventually.of_forall fun y => by
        simpa only [e,MeasurableEquiv.piFinSuccAbove_symm_apply,Fin.insertNthEquiv,
          Equiv.coe_fn_mk] using line_integral_eq_interval L hL (fun t => f (d.insertNth t y))

theorem normalized_cube_sliced (L : ℝ) (hL : 0 ≤ L) (d : Fin 3)
    (f : Space → ℝ) (hf : Integrable f ((volume : Measure Space).restrict (cube L))) :
    cubeAverage L f = (1/L^3) *
      (∫ y, (∫ t in (0 : ℝ)..L, f (d.insertNth t y)) ∂transverseMeasure L) := by
  change EulerCellMoments.boxAverage (fun _ => 0) L f = _
  rw [EulerCellMoments.box_integral _ _ hL]
  exact congrArg (fun r : ℝ => (1/L^3)*r) (cube_integral_sliced L hL d f hf)

theorem cube_integral_coordinate_permutation (L : ℝ) (hL : 0 ≤ L)
    (e : Fin 3 ≃ Fin 3) (f : Space → ℝ) :
    cubeAverage L (fun x => f (MeasurableEquiv.piCongrLeft (fun _ : Fin 3 => ℝ) e x)) =
      cubeAverage L f := by
  change EulerCellMoments.boxAverage (fun _ => 0) L _ =
    EulerCellMoments.boxAverage (fun _ => 0) L f
  rw [EulerCellMoments.box_integral _ _ hL,EulerCellMoments.box_integral _ _ hL]
  change (1/L^3)*(∫ x in cube L,
    f (MeasurableEquiv.piCongrLeft (fun _ : Fin 3 => ℝ) e x)) =
      (1/L^3)*(∫ x in cube L, f x)
  rw [cube_product_measure]
  exact congrArg (fun r : ℝ => (1/L^3)*r)
    ((measurePreserving_piCongrLeft (fun _ : Fin 3 => lineMeasure L) e).integral_comp' f)

theorem cube_acoustic_zero (L : ℝ) (hL : 0 < L) (d : Fin 3)
    (p v dp dv : Space → ℝ)
    (hint : Integrable (productTerm p v dp dv)
      ((volume : Measure Space).restrict (cube L)))
    (hpair : ∀ y : Transverse, EulerPeriodicAcoustic.PeriodicPair 0 L
      (fun t => p (d.insertNth t y)) (fun t => v (d.insertNth t y))
      (fun t => dp (d.insertNth t y)) (fun t => dv (d.insertNth t y))) :
    cubeAverage L (productTerm p v dp dv) = 0 := by
  rw [normalized_cube_sliced L hL.le d _ hint]
  have hz : ∀ y : Transverse,
      (∫ t in (0 : ℝ)..L, productTerm p v dp dv (d.insertNth t y)) = 0 := by
    intro y
    simpa only [zero_add,productTerm,EulerPeriodicAcoustic.acousticProduct] using
      EulerPeriodicAcoustic.periodic_product_integral_zero 0 L
        (fun t => p (d.insertNth t y)) (fun t => v (d.insertNth t y))
        (fun t => dp (d.insertNth t y)) (fun t => dv (d.insertNth t y)) (hpair y)
  simp_rw [hz]
  simp

theorem cube_acoustic_sum_zero (L : ℝ) (hL : 0 < L)
    (p v dp dv : Fin 3 → Space → ℝ)
    (hint : ∀ d, Integrable (productTerm (p d) (v d) (dp d) (dv d))
      ((volume : Measure Space).restrict (cube L)))
    (hpair : ∀ d y, EulerPeriodicAcoustic.PeriodicPair 0 L
      (fun t => p d (d.insertNth t y)) (fun t => v d (d.insertNth t y))
      (fun t => dp d (d.insertNth t y)) (fun t => dv d (d.insertNth t y))) :
    cubeAverage L (fun x => ∑ d : Fin 3, productTerm (p d) (v d) (dp d) (dv d) x) = 0 := by
  have hi : ∀ d, Integrable (productTerm (p d) (v d) (dp d) (dv d)) (cubeMeasure L) := by
    intro d
    exact (hint d).smul_measure ENNReal.ofReal_ne_top
  change (∫ x, ∑ d : Fin 3, productTerm (p d) (v d) (dp d) (dv d) x ∂cubeMeasure L) = 0
  rw [integral_finset_sum _ (fun d _ => hi d)]
  apply Finset.sum_eq_zero
  intro d _hd
  exact cube_acoustic_zero L hL d (p d) (v d) (dp d) (dv d) (hint d) (hpair d)

theorem physical_cube_acoustic_zero (d : Fin 3) (p v dp dv : Space → ℝ)
    (hint : Integrable (productTerm p v dp dv)
      ((volume : Measure Space).restrict (cube (2*Real.pi))))
    (hpair : ∀ y : Transverse, EulerPeriodicAcoustic.PeriodicPair 0 (2*Real.pi)
      (fun t => p (d.insertNth t y)) (fun t => v (d.insertNth t y))
      (fun t => dp (d.insertNth t y)) (fun t => dv (d.insertNth t y))) :
    cubeAverage (2*Real.pi) (productTerm p v dp dv) = 0 :=
  cube_acoustic_zero (2*Real.pi) (mul_pos (by norm_num) Real.pi_pos) d p v dp dv hint hpair

theorem nonperiodic_cube_control (L : ℝ) (hL : 0 < L) (d : Fin 3) :
    cubeAverage L (productTerm (fun x => x d) (fun _ => 1) (fun _ => 1) (fun _ => 0)) = 1 := by
  change EulerCellMoments.boxAverage (fun _ => 0) L _ = 1
  simp [EulerCellMoments.boxAverage,productTerm,integral_const,measureReal_def,
    EulerCellMoments.box_measure_univ (fun _ => 0) L hL]

end EulerPeriodicBox

/-
Adapted from Mathlib Analysis.Calculus.ParametricIntegral, Patrick Massot (2021),
Apache 2.0. Pinned source retained in METRIC_PARAMETRIC_REFERENCE files.
Only complete codomain spaces are used; all mathematical proofs are rechecked.
-/
namespace EulerMetricInterchange
open TopologicalSpace MeasureTheory Filter Metric

open scoped Topology Filter

variable {α : Type*} [MeasurableSpace α] {μ : Measure α} {𝕜 : Type*} [RCLike 𝕜] {E : Type*}
  [NormedAddCommGroup E] [NormedSpace ℝ E] [NormedSpace 𝕜 E] {H : Type*}
  [NormedAddCommGroup H] [NormedSpace 𝕜 H]

variable {F : H → α → E} {x₀ : H} {bound : α → ℝ} {ε : ℝ}

/-- Differentiation under integral of `x ↦ ∫ F x a` at a given point `x₀`, assuming `F x₀` is
integrable, `‖F x a - F x₀ a‖ ≤ bound a * ‖x - x₀‖` for `x` in a ball around `x₀` for ae `a` with
integrable Lipschitz bound `bound` (with a ball radius independent of `a`), and `F x` is
ae-measurable for `x` in the same ball. See `hasFDerivAt_integral_of_dominated_loc_of_lip` for a
slightly less general but usually more useful version. -/
theorem hasFDerivAt_integral_of_dominated_loc_of_lip' [CompleteSpace E] {F' : α → H →L[𝕜] E} (ε_pos : 0 < ε)
    (hF_meas : ∀ x ∈ ball x₀ ε, AEStronglyMeasurable (F x) μ) (hF_int : Integrable (F x₀) μ)
    (hF'_meas : AEStronglyMeasurable F' μ)
    (h_lipsch : ∀ᵐ a ∂μ, ∀ x ∈ ball x₀ ε, ‖F x a - F x₀ a‖ ≤ bound a * ‖x - x₀‖)
    (bound_integrable : Integrable (bound : α → ℝ) μ)
    (h_diff : ∀ᵐ a ∂μ, HasFDerivAt (F · a) (F' a) x₀) :
    Integrable F' μ ∧ HasFDerivAt (fun x ↦ ∫ a, F x a ∂μ) (∫ a, F' a ∂μ) x₀ := by
  have x₀_in : x₀ ∈ ball x₀ ε := mem_ball_self ε_pos
  have nneg : ∀ x, 0 ≤ ‖x - x₀‖⁻¹ := fun x ↦ inv_nonneg.mpr (norm_nonneg _)
  set b : α → ℝ := fun a ↦ |bound a|
  have b_int : Integrable b μ := bound_integrable.norm
  have b_nonneg : ∀ a, 0 ≤ b a := fun a ↦ abs_nonneg _
  replace h_lipsch : ∀ᵐ a ∂μ, ∀ x ∈ ball x₀ ε, ‖F x a - F x₀ a‖ ≤ b a * ‖x - x₀‖ :=
    h_lipsch.mono fun a ha x hx ↦
      (ha x hx).trans <| mul_le_mul_of_nonneg_right (le_abs_self _) (norm_nonneg _)
  have hF_int' : ∀ x ∈ ball x₀ ε, Integrable (F x) μ := fun x x_in ↦ by
    have : ∀ᵐ a ∂μ, ‖F x₀ a - F x a‖ ≤ ε * b a := by
      simp only [norm_sub_rev (F x₀ _)]
      refine h_lipsch.mono fun a ha ↦ (ha x x_in).trans ?_
      rw [mul_comm ε]
      rw [mem_ball, dist_eq_norm] at x_in
      exact mul_le_mul_of_nonneg_left x_in.le (b_nonneg _)
    exact integrable_of_norm_sub_le (hF_meas x x_in) hF_int
      (bound_integrable.norm.const_mul ε) this
  have hF'_int : Integrable F' μ :=
    have : ∀ᵐ a ∂μ, ‖F' a‖ ≤ b a := by
      apply (h_diff.and h_lipsch).mono
      rintro a ⟨ha_diff, ha_lip⟩
      exact ha_diff.le_of_lip' (b_nonneg a) (mem_of_superset (ball_mem_nhds _ ε_pos) <| ha_lip)
    b_int.mono' hF'_meas this
  refine ⟨hF'_int, ?_⟩
  have h_ball : ball x₀ ε ∈ 𝓝 x₀ := ball_mem_nhds x₀ ε_pos
  have : ∀ᶠ x in 𝓝 x₀, ‖x - x₀‖⁻¹ * ‖((∫ a, F x a ∂μ) - ∫ a, F x₀ a ∂μ) - (∫ a, F' a ∂μ) (x - x₀)‖ =
      ‖∫ a, ‖x - x₀‖⁻¹ • (F x a - F x₀ a - F' a (x - x₀)) ∂μ‖ := by
    apply mem_of_superset (ball_mem_nhds _ ε_pos)
    intro x x_in; simp only
    rw [Set.mem_setOf_eq, ← norm_smul_of_nonneg (nneg _), integral_smul, integral_sub, integral_sub,
      ← ContinuousLinearMap.integral_apply hF'_int]
    exacts [hF_int' x x_in, hF_int, (hF_int' x x_in).sub hF_int,
      hF'_int.apply_continuousLinearMap _]
  rw [hasFDerivAt_iff_tendsto, tendsto_congr' this, ← tendsto_zero_iff_norm_tendsto_zero, ←
    show (∫ a : α, ‖x₀ - x₀‖⁻¹ • (F x₀ a - F x₀ a - (F' a) (x₀ - x₀)) ∂μ) = 0 by simp]
  apply tendsto_integral_filter_of_dominated_convergence
  · filter_upwards [h_ball] with _ x_in
    apply AEStronglyMeasurable.const_smul
    exact ((hF_meas _ x_in).sub (hF_meas _ x₀_in)).sub (hF'_meas.apply_continuousLinearMap _)
  · refine mem_of_superset h_ball fun x hx ↦ ?_
    apply (h_diff.and h_lipsch).mono
    on_goal 1 => rintro a ⟨-, ha_bound⟩
    show ‖‖x - x₀‖⁻¹ • (F x a - F x₀ a - F' a (x - x₀))‖ ≤ b a + ‖F' a‖
    replace ha_bound : ‖F x a - F x₀ a‖ ≤ b a * ‖x - x₀‖ := ha_bound x hx
    calc
      ‖‖x - x₀‖⁻¹ • (F x a - F x₀ a - F' a (x - x₀))‖ =
          ‖‖x - x₀‖⁻¹ • (F x a - F x₀ a) - ‖x - x₀‖⁻¹ • F' a (x - x₀)‖ := by rw [smul_sub]
      _ ≤ ‖‖x - x₀‖⁻¹ • (F x a - F x₀ a)‖ + ‖‖x - x₀‖⁻¹ • F' a (x - x₀)‖ := norm_sub_le _ _
      _ = ‖x - x₀‖⁻¹ * ‖F x a - F x₀ a‖ + ‖x - x₀‖⁻¹ * ‖F' a (x - x₀)‖ := by
        rw [norm_smul_of_nonneg, norm_smul_of_nonneg] <;> exact nneg _
      _ ≤ ‖x - x₀‖⁻¹ * (b a * ‖x - x₀‖) + ‖x - x₀‖⁻¹ * (‖F' a‖ * ‖x - x₀‖) := by
        gcongr; exact (F' a).le_opNorm _
      _ ≤ b a + ‖F' a‖ := ?_
    simp only [← div_eq_inv_mul]
    apply_rules [add_le_add, div_le_of_le_mul₀] <;> first | rfl | positivity
  · exact b_int.add hF'_int.norm
  · apply h_diff.mono
    intro a ha
    suffices Tendsto (fun x ↦ ‖x - x₀‖⁻¹ • (F x a - F x₀ a - F' a (x - x₀))) (𝓝 x₀) (𝓝 0) by simpa
    rw [tendsto_zero_iff_norm_tendsto_zero]
    have : (fun x ↦ ‖x - x₀‖⁻¹ * ‖F x a - F x₀ a - F' a (x - x₀)‖) = fun x ↦
        ‖‖x - x₀‖⁻¹ • (F x a - F x₀ a - F' a (x - x₀))‖ := by
      ext x
      rw [norm_smul_of_nonneg (nneg _)]
    rwa [hasFDerivAt_iff_tendsto, this] at ha

/-- Differentiation under integral of `x ↦ ∫ F x a` at a given point `x₀`, assuming
`F x₀` is integrable, `x ↦ F x a` is locally Lipschitz on a ball around `x₀` for ae `a`
(with a ball radius independent of `a`) with integrable Lipschitz bound, and `F x` is ae-measurable
for `x` in a possibly smaller neighborhood of `x₀`. -/
theorem hasFDerivAt_integral_of_dominated_loc_of_lip [CompleteSpace E] {F' : α → H →L[𝕜] E}
    (ε_pos : 0 < ε) (hF_meas : ∀ᶠ x in 𝓝 x₀, AEStronglyMeasurable (F x) μ)
    (hF_int : Integrable (F x₀) μ) (hF'_meas : AEStronglyMeasurable F' μ)
    (h_lip : ∀ᵐ a ∂μ, LipschitzOnWith (Real.nnabs <| bound a) (F · a) (ball x₀ ε))
    (bound_integrable : Integrable (bound : α → ℝ) μ)
    (h_diff : ∀ᵐ a ∂μ, HasFDerivAt (F · a) (F' a) x₀) :
    Integrable F' μ ∧ HasFDerivAt (fun x ↦ ∫ a, F x a ∂μ) (∫ a, F' a ∂μ) x₀ := by
  obtain ⟨δ, δ_pos, hδ⟩ : ∃ δ > 0, ∀ x ∈ ball x₀ δ, AEStronglyMeasurable (F x) μ ∧ x ∈ ball x₀ ε :=
    eventually_nhds_iff_ball.mp (hF_meas.and (ball_mem_nhds x₀ ε_pos))
  choose hδ_meas hδε using hδ
  replace h_lip : ∀ᵐ a : α ∂μ, ∀ x ∈ ball x₀ δ, ‖F x a - F x₀ a‖ ≤ |bound a| * ‖x - x₀‖ :=
    h_lip.mono fun a lip x hx ↦ lip.norm_sub_le (hδε x hx) (mem_ball_self ε_pos)
  replace bound_integrable := bound_integrable.norm
  apply hasFDerivAt_integral_of_dominated_loc_of_lip' δ_pos <;> assumption

theorem hasFDerivAt_integral_of_dominated_of_fderiv_le [CompleteSpace E] {F' : H → α → H →L[𝕜] E} (ε_pos : 0 < ε)
    (hF_meas : ∀ᶠ x in 𝓝 x₀, AEStronglyMeasurable (F x) μ) (hF_int : Integrable (F x₀) μ)
    (hF'_meas : AEStronglyMeasurable (F' x₀) μ)
    (h_bound : ∀ᵐ a ∂μ, ∀ x ∈ ball x₀ ε, ‖F' x a‖ ≤ bound a)
    (bound_integrable : Integrable (bound : α → ℝ) μ)
    (h_diff : ∀ᵐ a ∂μ, ∀ x ∈ ball x₀ ε, HasFDerivAt (F · a) (F' x a) x) :
    HasFDerivAt (fun x ↦ ∫ a, F x a ∂μ) (∫ a, F' x₀ a ∂μ) x₀ := by
  letI : NormedSpace ℝ H := NormedSpace.restrictScalars ℝ 𝕜 H
  have x₀_in : x₀ ∈ ball x₀ ε := mem_ball_self ε_pos
  have diff_x₀ : ∀ᵐ a ∂μ, HasFDerivAt (F · a) (F' x₀ a) x₀ :=
    h_diff.mono fun a ha ↦ ha x₀ x₀_in
  have : ∀ᵐ a ∂μ, LipschitzOnWith (Real.nnabs (bound a)) (F · a) (ball x₀ ε) := by
    apply (h_diff.and h_bound).mono
    rintro a ⟨ha_deriv, ha_bound⟩
    refine (convex_ball _ _).lipschitzOnWith_of_nnnorm_hasFDerivWithin_le
      (fun x x_in ↦ (ha_deriv x x_in).hasFDerivWithinAt) fun x x_in ↦ ?_
    rw [← NNReal.coe_le_coe, coe_nnnorm, Real.coe_nnabs]
    exact (ha_bound x x_in).trans (le_abs_self _)
  exact (hasFDerivAt_integral_of_dominated_loc_of_lip ε_pos hF_meas hF_int hF'_meas this
    bound_integrable diff_x₀).2

section

variable {F : 𝕜 → α → E} {x₀ : 𝕜}

/-- Derivative under integral of `x ↦ ∫ F x a` at a given point `x₀ : 𝕜`, `𝕜 = ℝ` or `𝕜 = ℂ`,
assuming `F x₀` is integrable, `x ↦ F x a` is locally Lipschitz on a ball around `x₀` for ae `a`
(with ball radius independent of `a`) with integrable Lipschitz bound, and `F x` is
ae-measurable for `x` in a possibly smaller neighborhood of `x₀`. -/
theorem hasDerivAt_integral_of_dominated_loc_of_lip [CompleteSpace E] {F' : α → E} (ε_pos : 0 < ε)
    (hF_meas : ∀ᶠ x in 𝓝 x₀, AEStronglyMeasurable (F x) μ) (hF_int : Integrable (F x₀) μ)
    (hF'_meas : AEStronglyMeasurable F' μ)
    (h_lipsch : ∀ᵐ a ∂μ, LipschitzOnWith (Real.nnabs <| bound a) (F · a) (ball x₀ ε))
    (bound_integrable : Integrable (bound : α → ℝ) μ)
    (h_diff : ∀ᵐ a ∂μ, HasDerivAt (F · a) (F' a) x₀) :
    Integrable F' μ ∧ HasDerivAt (fun x ↦ ∫ a, F x a ∂μ) (∫ a, F' a ∂μ) x₀ := by
  set L : E →L[𝕜] 𝕜 →L[𝕜] E := ContinuousLinearMap.smulRightL 𝕜 𝕜 E 1
  replace h_diff : ∀ᵐ a ∂μ, HasFDerivAt (F · a) (L (F' a)) x₀ :=
    h_diff.mono fun x hx ↦ hx.hasFDerivAt
  have hm : AEStronglyMeasurable (L ∘ F') μ := L.continuous.comp_aestronglyMeasurable hF'_meas
  obtain ⟨hF'_int, key⟩ := hasFDerivAt_integral_of_dominated_loc_of_lip
    ε_pos hF_meas hF_int hm h_lipsch bound_integrable h_diff
  replace hF'_int : Integrable F' μ := by
    rw [← integrable_norm_iff hm] at hF'_int
    simpa only [L, (· ∘ ·), integrable_norm_iff, hF'_meas, one_mul, norm_one,
      ContinuousLinearMap.comp_apply, ContinuousLinearMap.coe_restrict_scalarsL',
      ContinuousLinearMap.norm_restrictScalars, ContinuousLinearMap.norm_smulRightL_apply] using
      hF'_int
  refine ⟨hF'_int, ?_⟩
  simp_rw [hasDerivAt_iff_hasFDerivAt] at h_diff ⊢
  simpa only [(· ∘ ·), ContinuousLinearMap.integral_comp_comm _ hF'_int] using key

/-- Derivative under integral of `x ↦ ∫ F x a` at a given point `x₀ : ℝ`, assuming
`F x₀` is integrable, `x ↦ F x a` is differentiable on an interval around `x₀` for ae `a`
(with interval radius independent of `a`) with derivative uniformly bounded by an integrable
function, and `F x` is ae-measurable for `x` in a possibly smaller neighborhood of `x₀`. -/
theorem hasDerivAt_integral_of_dominated_loc_of_deriv_le [CompleteSpace E] (ε_pos : 0 < ε)
    (hF_meas : ∀ᶠ x in 𝓝 x₀, AEStronglyMeasurable (F x) μ) (hF_int : Integrable (F x₀) μ)
    {F' : 𝕜 → α → E} (hF'_meas : AEStronglyMeasurable (F' x₀) μ)
    (h_bound : ∀ᵐ a ∂μ, ∀ x ∈ ball x₀ ε, ‖F' x a‖ ≤ bound a) (bound_integrable : Integrable bound μ)
    (h_diff : ∀ᵐ a ∂μ, ∀ x ∈ ball x₀ ε, HasDerivAt (F · a) (F' x a) x) :
    Integrable (F' x₀) μ ∧ HasDerivAt (fun n ↦ ∫ a, F n a ∂μ) (∫ a, F' x₀ a ∂μ) x₀ := by
  have x₀_in : x₀ ∈ ball x₀ ε := mem_ball_self ε_pos
  have diff_x₀ : ∀ᵐ a ∂μ, HasDerivAt (F · a) (F' x₀ a) x₀ :=
    h_diff.mono fun a ha ↦ ha x₀ x₀_in
  have : ∀ᵐ a ∂μ, LipschitzOnWith (Real.nnabs (bound a)) (fun x : 𝕜 ↦ F x a) (ball x₀ ε) := by
    apply (h_diff.and h_bound).mono
    rintro a ⟨ha_deriv, ha_bound⟩
    refine (convex_ball _ _).lipschitzOnWith_of_nnnorm_hasDerivWithin_le
      (fun x x_in ↦ (ha_deriv x x_in).hasDerivWithinAt) fun x x_in ↦ ?_
    rw [← NNReal.coe_le_coe, coe_nnnorm, Real.coe_nnabs]
    exact (ha_bound x x_in).trans (le_abs_self _)
  exact
    hasDerivAt_integral_of_dominated_loc_of_lip ε_pos hF_meas hF_int hF'_meas this bound_integrable
      diff_x₀

end

end EulerMetricInterchange

namespace EulerMetricEnergy
open MeasureTheory Filter Metric
open scoped Topology BigOperators
abbrev Space := EulerPeriodicBox.Space
structure Fields where
  q : ℝ → Space → ℝ
  p : ℝ → Space → ℝ
  a : ℝ → Space → ℝ
  b : Fin 3 → ℝ → Space → ℝ
  c : ℝ → Space → ℝ

def density (f : Fields) (t : ℝ) (x : Space) : ℝ :=
  (f.a t x / f.q t x + f.c t x / (2*f.p t x))^2 +
  (∑ i : Fin 3, (f.b i t x)^2) / f.q t x + (f.c t x)^2 / (2*f.p t x)

def rate (f ft : Fields) (t : ℝ) (x : Space) : ℝ :=
  2*(f.a t x/f.q t x+f.c t x/(2*f.p t x))*
    ((ft.a t x*f.q t x-f.a t x*ft.q t x)/(f.q t x)^2+
     (ft.c t x*(2*f.p t x)-f.c t x*(2*ft.p t x))/(2*f.p t x)^2) +
  ((∑ i : Fin 3, 2*f.b i t x*ft.b i t x)*f.q t x-
    (∑ i : Fin 3, (f.b i t x)^2)*ft.q t x)/(f.q t x)^2 +
  (2*f.c t x*ft.c t x*(2*f.p t x)-(f.c t x)^2*(2*ft.p t x))/(2*f.p t x)^2

structure JetPair (f ft : Fields) (t : ℝ) (x : Space) : Prop where
  q_pos : 0 < f.q t x
  p_pos : 0 < f.p t x
  q_deriv : HasDerivAt (fun s => f.q s x) (ft.q t x) t
  p_deriv : HasDerivAt (fun s => f.p s x) (ft.p t x) t
  a_deriv : HasDerivAt (fun s => f.a s x) (ft.a t x) t
  b_deriv : ∀ i, HasDerivAt (fun s => f.b i s x) (ft.b i t x) t
  c_deriv : HasDerivAt (fun s => f.c s x) (ft.c t x) t

theorem density_hasDeriv (f ft : Fields) (t : ℝ) (x : Space) (h : JetPair f ft t x) :
    HasDerivAt (fun s => density f s x) (rate f ft t x) t := by
  have h2p := h.p_deriv.const_mul 2
  have h2pn : 2*f.p t x ≠ 0 := ne_of_gt (mul_pos (by norm_num) h.p_pos)
  have hq := h.a_deriv.div h.q_deriv (ne_of_gt h.q_pos)
  have hc := h.c_deriv.div h2p h2pn
  have hs : HasDerivAt (fun s => ∑ i : Fin 3, (f.b i s x)^2)
      (∑ i : Fin 3, 2*f.b i t x*ft.b i t x) t := by
    simpa using
      (HasDerivAt.fun_sum (u := Finset.univ) (fun i _ => (h.b_deriv i).pow 2))
  have hx := (hq.add hc).pow 2
  have hb := hs.div h.q_deriv (ne_of_gt h.q_pos)
  have hz := (h.c_deriv.pow 2).div h2p h2pn
  simpa [density,rate] using (hx.add hb).add hz

theorem cube_energy_hasDeriv (L t0 eps : ℝ) (heps : 0 < eps) (f ft : Fields)
    (bound : Space → ℝ)
    (hm : ∀ᶠ t in 𝓝 t0, AEStronglyMeasurable (density f t) (EulerPeriodicBox.cubeMeasure L))
    (hi : Integrable (density f t0) (EulerPeriodicBox.cubeMeasure L))
    (hmr : AEStronglyMeasurable (rate f ft t0) (EulerPeriodicBox.cubeMeasure L))
    (hb : ∀ᵐ x ∂EulerPeriodicBox.cubeMeasure L, ∀ t ∈ ball t0 eps, ‖rate f ft t x‖ ≤ bound x)
    (hib : Integrable bound (EulerPeriodicBox.cubeMeasure L))
    (hj : ∀ᵐ x ∂EulerPeriodicBox.cubeMeasure L, ∀ t ∈ ball t0 eps, JetPair f ft t x) :
    Integrable (rate f ft t0) (EulerPeriodicBox.cubeMeasure L) ∧
      HasDerivAt (fun t => EulerPeriodicBox.cubeAverage L (density f t))
        (EulerPeriodicBox.cubeAverage L (rate f ft t0)) t0 := by
  exact EulerMetricInterchange.hasDerivAt_integral_of_dominated_loc_of_deriv_le heps hm hi hmr hb hib
    (hj.mono fun x hx t ht => density_hasDeriv f ft t x (hx t ht))

theorem physical_energy_hasDeriv (t0 eps : ℝ) (heps : 0 < eps) (f ft : Fields)
    (bound : Space → ℝ)
    (hm : ∀ᶠ t in 𝓝 t0, AEStronglyMeasurable (density f t) (EulerPeriodicBox.cubeMeasure (2*Real.pi)))
    (hi : Integrable (density f t0) (EulerPeriodicBox.cubeMeasure (2*Real.pi)))
    (hmr : AEStronglyMeasurable (rate f ft t0) (EulerPeriodicBox.cubeMeasure (2*Real.pi)))
    (hb : ∀ᵐ x ∂EulerPeriodicBox.cubeMeasure (2*Real.pi), ∀ t ∈ ball t0 eps, ‖rate f ft t x‖ ≤ bound x)
    (hib : Integrable bound (EulerPeriodicBox.cubeMeasure (2*Real.pi)))
    (hj : ∀ᵐ x ∂EulerPeriodicBox.cubeMeasure (2*Real.pi), ∀ t ∈ ball t0 eps, JetPair f ft t x) :
    HasDerivAt (fun t => EulerPeriodicBox.cubeAverage (2*Real.pi) (density f t))
      (EulerPeriodicBox.cubeAverage (2*Real.pi) (rate f ft t0)) t0 :=
  (cube_energy_hasDeriv (2*Real.pi) t0 eps heps f ft bound hm hi hmr hb hib hj).2

theorem finite_weighted_energy_hasDeriv {J : Type*} [Fintype J]
    (L t0 eps : ℝ) (heps : 0 < eps) (f ft : J → Fields) (alpha : J → ℝ)
    (bound : J → Space → ℝ)
    (hm : ∀ j, ∀ᶠ t in 𝓝 t0, AEStronglyMeasurable (density (f j) t) (EulerPeriodicBox.cubeMeasure L))
    (hi : ∀ j, Integrable (density (f j) t0) (EulerPeriodicBox.cubeMeasure L))
    (hmr : ∀ j, AEStronglyMeasurable (rate (f j) (ft j) t0) (EulerPeriodicBox.cubeMeasure L))
    (hb : ∀ j, ∀ᵐ x ∂EulerPeriodicBox.cubeMeasure L, ∀ t ∈ ball t0 eps,
      ‖rate (f j) (ft j) t x‖ ≤ bound j x)
    (hib : ∀ j, Integrable (bound j) (EulerPeriodicBox.cubeMeasure L))
    (hj : ∀ j, ∀ᵐ x ∂EulerPeriodicBox.cubeMeasure L, ∀ t ∈ ball t0 eps, JetPair (f j) (ft j) t x) :
    HasDerivAt (fun t => ∑ j, alpha j * EulerPeriodicBox.cubeAverage L (density (f j) t))
      (∑ j, alpha j * EulerPeriodicBox.cubeAverage L (rate (f j) (ft j) t0)) t0 := by
  exact HasDerivAt.fun_sum (fun j _ =>
    ((cube_energy_hasDeriv L t0 eps heps (f j) (ft j) (bound j)
      (hm j) (hi j) (hmr j) (hb j) (hib j) (hj j)).2.const_mul (alpha j)))

theorem finite_energy_as_integral {J : Type*} [Fintype J] (L t : ℝ)
    (f : J → Fields) (alpha : J → ℝ)
    (hi : ∀ j, Integrable (density (f j) t) (EulerPeriodicBox.cubeMeasure L)) :
    (∑ j, alpha j * EulerPeriodicBox.cubeAverage L (density (f j) t)) =
      EulerPeriodicBox.cubeAverage L (fun x => ∑ j, alpha j * density (f j) t x) := by
  unfold EulerPeriodicBox.cubeAverage
  rw [integral_finset_sum _ (fun j _ => (hi j).const_mul (alpha j))]
  simp only [integral_const_mul]

def control : Fields where
  q := fun t _ => 1+t
  p := fun _ _ => 1
  a := fun _ _ => 1
  b := fun _ _ _ => 0
  c := fun _ _ => 0

theorem control_energy (L : ℝ) (hL : 0 < L) (t : ℝ) :
    EulerPeriodicBox.cubeAverage L (density control t) = (1/(1+t))^2 := by
  change EulerCellMoments.boxAverage (fun _ => 0) L _ = _
  simp [EulerCellMoments.boxAverage,density,control,integral_const,measureReal_def,
    EulerCellMoments.box_measure_univ (fun _ => 0) L hL]

theorem changing_metric_control (L : ℝ) (hL : 0 < L) :
    HasDerivAt (fun t => EulerPeriodicBox.cubeAverage L (density control t)) (-2) 0 := by
  have hq : HasDerivAt (fun t : ℝ => 1+t) 1 0 := by
    simpa only [zero_add] using (hasDerivAt_id (0:ℝ)).const_add 1
  have hd := ((hasDerivAt_const (0:ℝ) (1:ℝ)).div hq (by norm_num)).pow 2
  have he : (fun t => EulerPeriodicBox.cubeAverage L (density control t)) =
      (fun t : ℝ => (1/(1+t))^2) := funext (control_energy L hL)
  rw [he]
  convert hd using 1
  norm_num

end EulerMetricEnergy

namespace EulerTransport
open MeasureTheory Set
open scoped BigOperators Interval
abbrev Space := EulerPeriodicBox.Space
abbrev Transverse := EulerPeriodicBox.Transverse
open EulerPeriodicBox

theorem coordinate_transport (L : ℝ) (hL : 0 < L) (d : Fin 3)
    (G v dG dv : Space → ℝ)
    (hadv : Integrable (fun x => v x*dG x) ((volume : Measure Space).restrict (cube L)))
    (hdiv : Integrable (fun x => dv x*G x) ((volume : Measure Space).restrict (cube L)))
    (hp : ∀ y : Transverse, EulerPeriodicAcoustic.PeriodicPair 0 L
      (fun t => v (d.insertNth t y)) (fun t => G (d.insertNth t y))
      (fun t => dv (d.insertNth t y)) (fun t => dG (d.insertNth t y))) :
    cubeAverage L (fun x => v x*dG x) = -cubeAverage L (fun x => dv x*G x) := by
  have hz := cube_acoustic_zero L hL d v G dv dG (hdiv.add hadv) hp
  have ha : Integrable (fun x => v x*dG x) (cubeMeasure L) :=
    hadv.smul_measure ENNReal.ofReal_ne_top
  have hd : Integrable (fun x => dv x*G x) (cubeMeasure L) :=
    hdiv.smul_measure ENNReal.ofReal_ne_top
  change (∫ x, dv x*G x+v x*dG x ∂cubeMeasure L) = 0 at hz
  rw [integral_add hd ha] at hz
  change (∫ x, v x*dG x ∂cubeMeasure L) = -(∫ x, dv x*G x ∂cubeMeasure L)
  linarith

theorem transport_sum (L : ℝ) (hL : 0 < L)
    (G : Space → ℝ) (v dG dv : Fin 3 → Space → ℝ)
    (hadv : ∀ d, Integrable (fun x => v d x*dG d x) ((volume : Measure Space).restrict (cube L)))
    (hdiv : ∀ d, Integrable (fun x => dv d x*G x) ((volume : Measure Space).restrict (cube L)))
    (hp : ∀ d y, EulerPeriodicAcoustic.PeriodicPair 0 L
      (fun t => v d (d.insertNth t y)) (fun t => G (d.insertNth t y))
      (fun t => dv d (d.insertNth t y)) (fun t => dG d (d.insertNth t y))) :
    cubeAverage L (fun x => ∑ d, v d x*dG d x) =
      -cubeAverage L (fun x => (∑ d, dv d x)*G x) := by
  have ha : ∀ d, Integrable (fun x => v d x*dG d x) (cubeMeasure L) :=
    fun d => (hadv d).smul_measure ENNReal.ofReal_ne_top
  have hd : ∀ d, Integrable (fun x => dv d x*G x) (cubeMeasure L) :=
    fun d => (hdiv d).smul_measure ENNReal.ofReal_ne_top
  simp_rw [Finset.sum_mul]
  change (∫ x, ∑ d, v d x*dG d x ∂cubeMeasure L) =
    -(∫ x, ∑ d, dv d x*G x ∂cubeMeasure L)
  rw [integral_finset_sum _ (fun d _ => ha d),integral_finset_sum _ (fun d _ => hd d),
    ← Finset.sum_neg_distrib]
  apply Finset.sum_congr rfl
  intro d _hd
  exact coordinate_transport L hL d G (v d) (dG d) (dv d) (hadv d) (hdiv d) (hp d)

structure TestState where
  a : ℝ
  b : Fin 3 → ℝ
  c : ℝ

def metric (q p : ℝ) (W V : TestState) : ℝ :=
  (W.a/q+W.c/(2*p))*(V.a/q+V.c/(2*p))+
    (∑ i, W.b i*V.b i)/q+W.c*V.c/(2*p)
def potential (q p : ℝ) (W : TestState) : ℝ :=
  -(W.a/q+W.c/(2*p))^2+3*W.c^2/(2*p)+3*W.c*(W.a/q+W.c/(2*p))/p

def fixedFields (q p : ℝ) (W : TestState) : EulerMetricEnergy.Fields where
  q := fun _ _ => q
  p := fun _ _ => p
  a := fun _ _ => W.a
  b := fun i _ _ => W.b i
  c := fun _ _ => W.c

def materialFields (q p theta : ℝ) (V : TestState) : EulerMetricEnergy.Fields where
  q := fun _ _ => q*theta
  p := fun _ _ => -2*p*theta
  a := fun _ _ => V.a
  b := fun i _ _ => V.b i
  c := fun _ _ => V.c

theorem material_rate_identity (q p theta : ℝ) (hq : q ≠ 0) (hp : p ≠ 0)
    (W V : TestState) :
    EulerMetricEnergy.rate (fixedFields q p W) (materialFields q p theta V) 0 (fun _ => 0) =
      theta*(potential q p W-metric q p W W)+2*metric q p W V := by
  simp only [EulerMetricEnergy.rate,fixedFields,materialFields,potential,metric]
  simp [Fin.sum_univ_succ]
  field_simp [hq,hp]
  ring

def acoustic (q p : ℝ) (j : Fin 3) (V : TestState) : TestState where
  a := -q*V.b j
  b := fun i => if i=j then q*V.c else 0
  c := 2*p*V.b j

theorem acoustic_pairing (q p : ℝ) (hq : q ≠ 0) (hp : p ≠ 0)
    (j : Fin 3) (W V : TestState) :
    metric q p W (acoustic q p j V) = W.c*V.b j+W.b j*V.c := by
  simp only [metric,acoustic,mul_ite,mul_zero,Finset.sum_ite_eq',Finset.mem_univ,if_true]
  field_simp [hq,hp]
  ring

def G (t : ℝ) : ℝ := t^2-2*t^3+t^4
def V (t : ℝ) : ℝ := 2*t-6*t^2+4*t^3
def DV (t : ℝ) : ℝ := 2-12*t+12*t^2
lemma continuous_G : Continuous G :=
  ((continuous_id.pow 2).sub ((continuous_const : Continuous (fun _ : ℝ => (2:ℝ))).mul
    (continuous_id.pow 3))).add (continuous_id.pow 4)
lemma continuous_V : Continuous V :=
  (((continuous_const : Continuous (fun _ : ℝ => (2:ℝ))).mul continuous_id).sub
    ((continuous_const : Continuous (fun _ : ℝ => (6:ℝ))).mul (continuous_id.pow 2))).add
    ((continuous_const : Continuous (fun _ : ℝ => (4:ℝ))).mul (continuous_id.pow 3))
lemma continuous_DV : Continuous DV :=
  ((continuous_const : Continuous (fun _ : ℝ => (2:ℝ))).sub
    ((continuous_const : Continuous (fun _ : ℝ => (12:ℝ))).mul continuous_id)).add
    ((continuous_const : Continuous (fun _ : ℝ => (12:ℝ))).mul (continuous_id.pow 2))
lemma deriv_G (x : ℝ) : HasDerivAt G (V x) x := by
  have h := (((hasDerivAt_id x).pow 2).sub (((hasDerivAt_id x).pow 3).const_mul 2)).add
    ((hasDerivAt_id x).pow 4)
  change HasDerivAt (fun t : ℝ => t^2-2*t^3+t^4) (V x) x
  convert h using 1
  dsimp [V]
  ring
lemma deriv_V (x : ℝ) : HasDerivAt V (DV x) x := by
  have h := (((hasDerivAt_id x).const_mul 2).sub (((hasDerivAt_id x).pow 2).const_mul 6)).add
    (((hasDerivAt_id x).pow 3).const_mul 4)
  change HasDerivAt (fun t : ℝ => 2*t-6*t^2+4*t^3) (DV x) x
  convert h using 1
  dsimp [DV]
  ring

theorem polynomial_pair : EulerPeriodicAcoustic.PeriodicPair 0 1 V G DV V := by
  refine ⟨continuous_V.continuousOn,continuous_G.continuousOn,
    (fun x _ => deriv_V x),(fun x _ => deriv_G x),
    continuous_DV.intervalIntegrable _ _,continuous_V.intervalIntegrable _ _,?_,?_⟩ <;>
    norm_num [V,G]

def primitive (t : ℝ) : ℝ := (4/3:ℝ)*t^3-6*t^4+(52/5:ℝ)*t^5-8*t^6+(16/7:ℝ)*t^7
lemma primitive_deriv (x : ℝ) : HasDerivAt primitive ((V x)^2) x := by
  have h := (((((hasDerivAt_id x).pow 3).const_mul (4/3:ℝ)).sub
    (((hasDerivAt_id x).pow 4).const_mul 6)).add
    (((hasDerivAt_id x).pow 5).const_mul (52/5:ℝ))).sub
    (((hasDerivAt_id x).pow 6).const_mul 8)
  have hh := h.add (((hasDerivAt_id x).pow 7).const_mul (16/7:ℝ))
  change HasDerivAt (fun t : ℝ => (4/3:ℝ)*t^3-6*t^4+(52/5:ℝ)*t^5-8*t^6+(16/7:ℝ)*t^7) ((V x)^2) x
  convert hh using 1
  dsimp [V]
  ring
lemma continuous_primitive : Continuous primitive := by
  exact (((((continuous_const : Continuous (fun _ : ℝ => (4/3:ℝ))).mul (continuous_id.pow 3)).sub
    ((continuous_const : Continuous (fun _ : ℝ => (6:ℝ))).mul (continuous_id.pow 4))).add
    ((continuous_const : Continuous (fun _ : ℝ => (52/5:ℝ))).mul (continuous_id.pow 5))).sub
    ((continuous_const : Continuous (fun _ : ℝ => (8:ℝ))).mul (continuous_id.pow 6))).add
    ((continuous_const : Continuous (fun _ : ℝ => (16/7:ℝ))).mul (continuous_id.pow 7))

theorem polynomial_transport_integral : (∫ t in (0:ℝ)..1, (V t)^2) = 2/105 := by
  have h := intervalIntegral.integral_eq_sub_of_hasDeriv_right
    (a := (0:ℝ)) (b := 1) continuous_primitive.continuousOn
    (fun x _ => (primitive_deriv x).hasDerivWithinAt)
    ((continuous_V.pow 2).intervalIntegrable 0 1)
  rw [h]
  norm_num [primitive]

lemma unit_coordinate_average (d : Fin 3) :
    cubeAverage 1 (fun x => (V (x d))^2) = 2/105 := by
  have hc : Continuous (fun x : Space => (V (x d))^2) :=
    (continuous_V.comp (continuous_apply d)).pow 2
  have hi : Integrable (fun x : Space => (V (x d))^2)
      ((volume : Measure Space).restrict (cube 1)) :=
    hc.continuousOn.integrableOn_compact isCompact_Icc
  rw [normalized_cube_sliced 1 (by norm_num) d _ hi]
  have hline : ∀ y : Transverse, (∫ t in (0:ℝ)..1, (V ((d.insertNth t y : Space) d))^2) = 2/105 := by
    intro y
    simpa using polynomial_transport_integral
  simp_rw [hline]
  rw [transverse_product_measure]
  norm_num [integral_const,measureReal_def,Measure.restrict_apply_univ,Real.volume_Icc_pi]

theorem periodic_divergence_control (d : Fin 3) :
    cubeAverage 1 (fun x => V (x d)*V (x d)) = 2/105 ∧
    cubeAverage 1 (fun x => DV (x d)*G (x d)) = -(2/105) := by
  have ha : Integrable (fun x : Space => V (x d)*V (x d))
      ((volume : Measure Space).restrict (cube 1)) :=
    ((continuous_V.comp (continuous_apply d)).mul (continuous_V.comp (continuous_apply d))).continuousOn.integrableOn_compact isCompact_Icc
  have hd : Integrable (fun x : Space => DV (x d)*G (x d))
      ((volume : Measure Space).restrict (cube 1)) :=
    ((continuous_DV.comp (continuous_apply d)).mul (continuous_G.comp (continuous_apply d))).continuousOn.integrableOn_compact isCompact_Icc
  have hp : ∀ y : Transverse, EulerPeriodicAcoustic.PeriodicPair 0 1
      (fun t => V ((d.insertNth t y : Space) d)) (fun t => G ((d.insertNth t y : Space) d))
      (fun t => DV ((d.insertNth t y : Space) d)) (fun t => V ((d.insertNth t y : Space) d)) := by
    intro y
    simpa using polynomial_pair
  have ht := coordinate_transport 1 (by norm_num) d (fun x => G (x d))
    (fun x => V (x d)) (fun x => V (x d)) (fun x => DV (x d)) ha hd hp
  have hv : cubeAverage 1 (fun x => V (x d)*V (x d)) = 2/105 := by
    simpa only [pow_two] using unit_coordinate_average d
  exact ⟨hv,by linarith⟩

theorem nonperiodic_boundary_control (L : ℝ) (hL : 0 < L) (d : Fin 3) :
    cubeAverage L (fun x : Space => (1:ℝ)*(1:ℝ)+(x d)*(0:ℝ)) = 1 := by
  simpa only [productTerm] using nonperiodic_cube_control L hL d

end EulerTransport

namespace EulerBalance
open MeasureTheory Set Filter Metric
open scoped BigOperators Topology
open EulerPeriodicBox EulerTransport EulerMetricEnergy
abbrev Space := EulerPeriodicBox.Space
abbrev Transverse := EulerPeriodicBox.Transverse
abbrev State := EulerTransport.TestState

def state (f : Fields) (t : ℝ) (x : Space) : State :=
  ⟨f.a t x,fun i => f.b i t x,f.c t x⟩
def derivativeFields (Q P : ℝ) (V : State) : Fields where
  q := fun _ _ => Q
  p := fun _ _ => P
  a := fun _ _ => V.a
  b := fun i _ _ => V.b i
  c := fun _ _ => V.c

def pointRate (q p : ℝ) (W : State) (Q P : ℝ) (V : State) : ℝ :=
  rate (fixedFields q p W) (derivativeFields Q P V) 0 (fun _ => 0)

theorem rate_representation (f ft : Fields) (t : ℝ) (x : Space) :
    rate f ft t x = pointRate (f.q t x) (f.p t x) (state f t x)
      (ft.q t x) (ft.p t x) (state ft t x) := rfl

lemma density_representation (f : Fields) (t : ℝ) (x : Space) :
    density f t x = metric (f.q t x) (f.p t x) (state f t x) (state f t x) := by
  simp only [density,metric,state,pow_two]

def slice (f : Fields) (t : ℝ) (d : Fin 3) (y : Transverse) : Fields where
  q := fun s _ => f.q t (d.insertNth s y)
  p := fun s _ => f.p t (d.insertNth s y)
  a := fun s _ => f.a t (d.insertNth s y)
  b := fun i s _ => f.b i t (d.insertNth s y)
  c := fun s _ => f.c t (d.insertNth s y)

theorem coordinate_density_derivative (f fx : Fields) (t : ℝ) (d : Fin 3)
    (y : Transverse) (s : ℝ)
    (hj : JetPair (slice f t d y) (slice fx t d y) s (fun _ => 0)) :
    HasDerivAt (fun z => density f t (d.insertNth z y))
      (rate f fx t (d.insertNth s y)) s := by
  simpa only [density,rate,slice] using
    density_hasDeriv (slice f t d y) (slice fx t d y) s (fun _ => 0) hj

theorem pointwise_material_balance (q p qt pt theta : ℝ) (hq : q ≠ 0) (hp : p ≠ 0)
    (W Wt F : State) (v qx px : Fin 3 → ℝ) (Wx : Fin 3 → State)
    (hqe : qt + (∑ j, v j*qx j) = q*theta)
    (hpe : pt + (∑ j, v j*px j) = -2*p*theta)
    (ha : Wt.a + (∑ j, v j*(Wx j).a) + (∑ j, -q*(Wx j).b j) = F.a)
    (hb : ∀ i, Wt.b i + (∑ j, v j*(Wx j).b i) +
      (∑ j, if i=j then q*(Wx j).c else 0) = F.b i)
    (hc : Wt.c + (∑ j, v j*(Wx j).c) + (∑ j, 2*p*(Wx j).b j) = F.c) :
    pointRate q p W qt pt Wt + (∑ j, v j*pointRate q p W (qx j) (px j) (Wx j)) =
      theta*(potential q p W-metric q p W W)+2*metric q p W F -
        2*(∑ j, ((Wx j).c*W.b j+W.c*(Wx j).b j)) := by
  have hqt : qt = q*theta-(∑ j, v j*qx j) := by linarith
  have hpt : pt = -2*p*theta-(∑ j, v j*px j) := by linarith
  have hat : Wt.a = F.a-(∑ j, v j*(Wx j).a)-(∑ j, -q*(Wx j).b j) := by linarith
  have hbt : ∀ i, Wt.b i = F.b i-(∑ j, v j*(Wx j).b i)-
      (∑ j, if i=j then q*(Wx j).c else 0) := by
    intro i
    linarith [hb i]
  have hct : Wt.c = F.c-(∑ j, v j*(Wx j).c)-(∑ j, 2*p*(Wx j).b j) := by linarith
  simp only [pointRate,rate,fixedFields,derivativeFields]
  rw [hqt,hpt,hat,hct]
  simp_rw [hbt]
  simp [Fin.sum_univ_succ,metric,potential]
  field_simp [hq,hp]
  ring

structure TimePremises (L t0 eps : ℝ) (f ft : Fields) (bound : Space → ℝ) : Prop where
  eps_pos : 0 < eps
  measurable : ∀ᶠ t in 𝓝 t0, AEStronglyMeasurable (density f t) (cubeMeasure L)
  integrable : Integrable (density f t0) (cubeMeasure L)
  rate_measurable : AEStronglyMeasurable (rate f ft t0) (cubeMeasure L)
  dominated : ∀ᵐ x ∂cubeMeasure L, ∀ t ∈ ball t0 eps, ‖rate f ft t x‖ ≤ bound x
  bound_integrable : Integrable bound (cubeMeasure L)
  actual_jets : ∀ᵐ x ∂cubeMeasure L, ∀ t ∈ ball t0 eps, JetPair f ft t x

structure SpatialPremises (L t : ℝ) (f : Fields) (fx : Fin 3 → Fields)
    (v dv : Fin 3 → Space → ℝ) : Prop where
  actual_jets : ∀ (d : Fin 3) (y : Transverse) (s : ℝ), s ∈ Ioo 0 L →
    JetPair (slice f t d y) (slice (fx d) t d y) s (fun _ => 0)
  v_continuous : ∀ (d : Fin 3) (y : Transverse), ContinuousOn (fun s => v d (d.insertNth s y)) (uIcc 0 L)
  density_continuous : ∀ (d : Fin 3) (y : Transverse), ContinuousOn (fun s => density f t (d.insertNth s y)) (uIcc 0 L)
  v_deriv : ∀ (d : Fin 3) (y : Transverse) (s : ℝ), s ∈ Ioo 0 L →
    HasDerivAt (fun z => v d (d.insertNth z y)) (dv d (d.insertNth s y)) s
  dv_integrable : ∀ (d : Fin 3) (y : Transverse), IntervalIntegrable (fun s => dv d (d.insertNth s y)) volume 0 L
  density_rate_integrable : ∀ (d : Fin 3) (y : Transverse), IntervalIntegrable
    (fun s => rate f (fx d) t (d.insertNth s y)) volume 0 L
  v_seam : ∀ (d : Fin 3) (y : Transverse), v d (d.insertNth 0 y) = v d (d.insertNth L y)
  density_seam : ∀ (d : Fin 3) (y : Transverse), density f t (d.insertNth 0 y) = density f t (d.insertNth L y)
  c_continuous : ∀ (d : Fin 3) (y : Transverse), ContinuousOn (fun s => f.c t (d.insertNth s y)) (uIcc 0 L)
  b_continuous : ∀ (d : Fin 3) (y : Transverse), ContinuousOn (fun s => f.b d t (d.insertNth s y)) (uIcc 0 L)
  dc_integrable : ∀ (d : Fin 3) (y : Transverse), IntervalIntegrable (fun s => (fx d).c t (d.insertNth s y)) volume 0 L
  db_integrable : ∀ (d : Fin 3) (y : Transverse), IntervalIntegrable (fun s => (fx d).b d t (d.insertNth s y)) volume 0 L
  c_seam : ∀ (d : Fin 3) (y : Transverse), f.c t (d.insertNth 0 y) = f.c t (d.insertNth L y)
  b_seam : ∀ (d : Fin 3) (y : Transverse), f.b d t (d.insertNth 0 y) = f.b d t (d.insertNth L y)
  adv_integrable : ∀ d, Integrable (fun x => v d x*rate f (fx d) t x)
    ((volume : Measure Space).restrict (cube L))
  div_integrable : ∀ d, Integrable (fun x => dv d x*density f t x)
    ((volume : Measure Space).restrict (cube L))
  acoustic_left_integrable : ∀ d, Integrable (fun x => (fx d).c t x*f.b d t x)
    ((volume : Measure Space).restrict (cube L))
  acoustic_right_integrable : ∀ d, Integrable (fun x => f.c t x*(fx d).b d t x)
    ((volume : Measure Space).restrict (cube L))

def theta (dv : Fin 3 → Space → ℝ) (x : Space) : ℝ := ∑ d, dv d x

def forcingDensity (f : Fields) (t : ℝ) (dv : Fin 3 → Space → ℝ) (F : Space → State)
    (x : Space) : ℝ := theta dv x*potential (f.q t x) (f.p t x) (state f t x)+
    2*metric (f.q t x) (f.p t x) (state f t x) (F x)

def adv (f : Fields) (fx : Fin 3 → Fields) (t : ℝ) (v : Fin 3 → Space → ℝ) (x : Space) : ℝ :=
  ∑ d, v d x*rate f (fx d) t x

def acousticSum (f : Fields) (fx : Fin 3 → Fields) (t : ℝ) (x : Space) : ℝ :=
  ∑ d, ((fx d).c t x*f.b d t x+f.c t x*(fx d).b d t x)

structure EulerPremises (t : ℝ) (f ft : Fields) (fx : Fin 3 → Fields)
    (v dv : Fin 3 → Space → ℝ) (F : Space → State) : Prop where
  q_pos : ∀ x, 0 < f.q t x
  p_pos : ∀ x, 0 < f.p t x
  q_equation : ∀ x, ft.q t x+(∑ d, v d x*(fx d).q t x) = f.q t x*theta dv x
  p_equation : ∀ x, ft.p t x+(∑ d, v d x*(fx d).p t x) = -2*f.p t x*theta dv x
  a_equation : ∀ x, ft.a t x+(∑ d, v d x*(fx d).a t x)+
    (∑ d, -f.q t x*(fx d).b d t x) = (F x).a
  b_equation : ∀ x i, ft.b i t x+(∑ d, v d x*(fx d).b i t x)+
    (∑ d, if i=d then f.q t x*(fx d).c t x else 0) = (F x).b i
  c_equation : ∀ x, ft.c t x+(∑ d, v d x*(fx d).c t x)+
    (∑ d, 2*f.p t x*(fx d).b d t x) = (F x).c

lemma forcing_pointwise (t : ℝ) (f ft : Fields) (fx : Fin 3 → Fields)
    (v dv : Fin 3 → Space → ℝ) (F : Space → State) (h : EulerPremises t f ft fx v dv F)
    (x : Space) :
    forcingDensity f t dv F x = rate f ft t x+adv f fx t v x+
      theta dv x*density f t x+2*acousticSum f fx t x := by
  have he := pointwise_material_balance (f.q t x) (f.p t x) (ft.q t x) (ft.p t x)
    (theta dv x) (ne_of_gt (h.q_pos x)) (ne_of_gt (h.p_pos x))
    (state f t x) (state ft t x) (F x) (fun d => v d x)
    (fun d => (fx d).q t x) (fun d => (fx d).p t x) (fun d => state (fx d) t x)
    (h.q_equation x) (h.p_equation x) (h.a_equation x) (h.b_equation x) (h.c_equation x)
  rw [rate_representation f ft t x]
  simp only [adv,rate_representation,acousticSum,state,forcingDensity] at he ⊢
  simp only [density_representation,state] at *
  linarith

lemma transport_premises (L t : ℝ) (hL : 0 < L) (f : Fields) (fx : Fin 3 → Fields)
    (v dv : Fin 3 → Space → ℝ) (h : SpatialPremises L t f fx v dv) (d : Fin 3) (y : Transverse) :
    EulerPeriodicAcoustic.PeriodicPair 0 L
      (fun s => v d (d.insertNth s y)) (fun s => density f t (d.insertNth s y))
      (fun s => dv d (d.insertNth s y)) (fun s => rate f (fx d) t (d.insertNth s y)) := by
  refine ⟨?_,?_,?_,?_,?_,?_,?_,?_⟩
  · simpa only [zero_add] using h.v_continuous d y
  · simpa only [zero_add] using h.density_continuous d y
  · intro s hs
    exact h.v_deriv d y s
      (by simpa only [zero_add,min_eq_left hL.le,max_eq_right hL.le] using hs)
  · intro s hs
    exact coordinate_density_derivative f (fx d) t d y s
      (h.actual_jets d y s
        (by simpa only [zero_add,min_eq_left hL.le,max_eq_right hL.le] using hs))
  · simpa only [zero_add] using h.dv_integrable d y
  · simpa only [zero_add] using h.density_rate_integrable d y
  · simpa only [zero_add] using (h.v_seam d y).symm
  · simpa only [zero_add] using (h.density_seam d y).symm

lemma acoustic_premises (L t : ℝ) (hL : 0 < L) (f : Fields) (fx : Fin 3 → Fields)
    (v dv : Fin 3 → Space → ℝ) (h : SpatialPremises L t f fx v dv) (d : Fin 3) (y : Transverse) :
    EulerPeriodicAcoustic.PeriodicPair 0 L
      (fun s => f.c t (d.insertNth s y)) (fun s => f.b d t (d.insertNth s y))
      (fun s => (fx d).c t (d.insertNth s y)) (fun s => (fx d).b d t (d.insertNth s y)) := by
  refine ⟨?_,?_,?_,?_,?_,?_,?_,?_⟩
  · simpa only [zero_add] using h.c_continuous d y
  · simpa only [zero_add] using h.b_continuous d y
  · intro s hs
    exact (h.actual_jets d y s
      (by simpa only [zero_add,min_eq_left hL.le,max_eq_right hL.le] using hs)).c_deriv
  · intro s hs
    exact (h.actual_jets d y s
      (by simpa only [zero_add,min_eq_left hL.le,max_eq_right hL.le] using hs)).b_deriv d
  · simpa only [zero_add] using h.dc_integrable d y
  · simpa only [zero_add] using h.db_integrable d y
  · simpa only [zero_add] using (h.c_seam d y).symm
  · simpa only [zero_add] using (h.b_seam d y).symm

theorem normalized_energy_balance (L t0 eps : ℝ) (hL : 0 < L)
    (f ft : Fields) (fx : Fin 3 → Fields) (bound : Space → ℝ)
    (v dv : Fin 3 → Space → ℝ) (F : Space → State)
    (ht : TimePremises L t0 eps f ft bound)
    (hs : SpatialPremises L t0 f fx v dv)
    (he : EulerPremises t0 f ft fx v dv F) :
    Integrable (forcingDensity f t0 dv F) (cubeMeasure L) ∧
      HasDerivAt (fun t => cubeAverage L (density f t))
        (cubeAverage L (forcingDensity f t0 dv F)) t0 := by
  obtain ⟨hri,hrd⟩ := cube_energy_hasDeriv L t0 eps ht.eps_pos f ft bound
    ht.measurable ht.integrable ht.rate_measurable ht.dominated ht.bound_integrable ht.actual_jets
  have ha : Integrable (adv f fx t0 v) (cubeMeasure L) := by
    exact integrable_finset_sum _ (fun d _ => (hs.adv_integrable d).smul_measure ENNReal.ofReal_ne_top)
  have hd : Integrable (fun x => theta dv x*density f t0 x) (cubeMeasure L) := by
    simp_rw [theta,Finset.sum_mul]
    exact integrable_finset_sum _ (fun d _ => (hs.div_integrable d).smul_measure ENNReal.ofReal_ne_top)
  have hac : Integrable (acousticSum f fx t0) (cubeMeasure L) := by
    exact integrable_finset_sum _ (fun d _ =>
      ((hs.acoustic_left_integrable d).add (hs.acoustic_right_integrable d)).smul_measure ENNReal.ofReal_ne_top)
  have htzero := transport_sum L hL (density f t0) v (fun d => rate f (fx d) t0) dv
    hs.adv_integrable hs.div_integrable (transport_premises L t0 hL f fx v dv hs)
  have hczero : cubeAverage L (acousticSum f fx t0) = 0 := by
    exact cube_acoustic_sum_zero L hL (fun _ => f.c t0) (fun d => f.b d t0)
      (fun d => (fx d).c t0) (fun d => (fx d).b d t0)
      (fun d => (hs.acoustic_left_integrable d).add (hs.acoustic_right_integrable d))
      (acoustic_premises L t0 hL f fx v dv hs)
  have heq : forcingDensity f t0 dv F = fun x => rate f ft t0 x+adv f fx t0 v x+
      theta dv x*density f t0 x+2*acousticSum f fx t0 x := by
    funext x
    exact forcing_pointwise t0 f ft fx v dv F he x
  have hfi : Integrable (forcingDensity f t0 dv F) (cubeMeasure L) := by
    rw [heq]
    exact ((hri.add ha).add hd).add (hac.const_mul 2)
  refine ⟨hfi,?_⟩
  have hvalue : cubeAverage L (forcingDensity f t0 dv F) = cubeAverage L (rate f ft t0) := by
    rw [heq]
    unfold cubeAverage
    have h1 : (∫ x, rate f ft t0 x+adv f fx t0 v x ∂cubeMeasure L) =
        (∫ x, rate f ft t0 x ∂cubeMeasure L)+(∫ x, adv f fx t0 v x ∂cubeMeasure L) :=
      integral_add hri ha
    have h2 : (∫ x, rate f ft t0 x+adv f fx t0 v x+theta dv x*density f t0 x ∂cubeMeasure L) =
        (∫ x, rate f ft t0 x+adv f fx t0 v x ∂cubeMeasure L)+
        (∫ x, theta dv x*density f t0 x ∂cubeMeasure L) :=
      integral_add (hri.add ha) hd
    have h3 : (∫ x, rate f ft t0 x+adv f fx t0 v x+theta dv x*density f t0 x+
        2*acousticSum f fx t0 x ∂cubeMeasure L) =
        (∫ x, rate f ft t0 x+adv f fx t0 v x+theta dv x*density f t0 x ∂cubeMeasure L)+
        (∫ x, 2*acousticSum f fx t0 x ∂cubeMeasure L) :=
      integral_add ((hri.add ha).add hd) (hac.const_mul 2)
    rw [h3,h2,h1,integral_const_mul]
    change (cubeAverage L (rate f ft t0)+cubeAverage L (adv f fx t0 v))+
      cubeAverage L (fun x => theta dv x*density f t0 x)+
      2*cubeAverage L (acousticSum f fx t0) = cubeAverage L (rate f ft t0)
    change cubeAverage L (adv f fx t0 v) = -cubeAverage L (fun x => theta dv x*density f t0 x) at htzero
    rw [htzero,hczero]
    ring
  rw [hvalue]
  exact hrd

theorem physical_energy_balance (t0 eps : ℝ)
    (f ft : Fields) (fx : Fin 3 → Fields) (bound : Space → ℝ)
    (v dv : Fin 3 → Space → ℝ) (F : Space → State)
    (ht : TimePremises (2*Real.pi) t0 eps f ft bound)
    (hs : SpatialPremises (2*Real.pi) t0 f fx v dv)
    (he : EulerPremises t0 f ft fx v dv F) :
    HasDerivAt (fun t => cubeAverage (2*Real.pi) (density f t))
      (cubeAverage (2*Real.pi) (forcingDensity f t0 dv F)) t0 :=
  (normalized_energy_balance (2*Real.pi) t0 eps (mul_pos (by norm_num) Real.pi_pos)
    f ft fx bound v dv F ht hs he).2

end EulerBalance
/-
Copyright (c) 2021 Sébastien Gouëzel. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Sébastien Gouëzel
The real-valued second-derivative symmetry proofs below are retained from the
pinned Mathlib source. Analytic and general-field sections are not included.
-/
open Asymptotics Set Filter
open scoped Topology ContDiff
section Real

variable {E F : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E] [NormedAddCommGroup F]
  [NormedSpace ℝ F] {s : Set E} (s_conv : Convex ℝ s) {f : E → F} {f' : E → E →L[ℝ] F}
  {f'' : E →L[ℝ] E →L[ℝ] F} (hf : ∀ x ∈ interior s, HasFDerivAt f (f' x) x) {x : E} (xs : x ∈ s)
  (hx : HasFDerivWithinAt f' f'' (interior s) x)

section
include s_conv hf xs hx

/-- Assume that `f` is differentiable inside a convex set `s`, and that its derivative `f'` is
differentiable at a point `x`. Then, given two vectors `v` and `w` pointing inside `s`, one can
Taylor-expand to order two the function `f` on the segment `[x + h v, x + h (v + w)]`, giving a
bilinear estimate for `f (x + hv + hw) - f (x + hv)` in terms of `f' w` and of `f'' ⬝ w`, up to
`o(h^2)`.

This is a technical statement used to show that the second derivative is symmetric. -/
theorem Convex.taylor_approx_two_segment {v w : E} (hv : x + v ∈ interior s)
    (hw : x + v + w ∈ interior s) :
    (fun h : ℝ => f (x + h • v + h • w)
        - f (x + h • v) - h • f' x w - h ^ 2 • f'' v w - (h ^ 2 / 2) • f'' w w) =o[𝓝[>] 0]
      fun h => h ^ 2 := by
  -- it suffices to check that the expression is bounded by `ε * ((‖v‖ + ‖w‖) * ‖w‖) * h^2` for
  -- small enough `h`, for any positive `ε`.
  refine IsLittleO.trans_isBigO
    (isLittleO_iff.2 fun ε εpos => ?_) (isBigO_const_mul_self ((‖v‖ + ‖w‖) * ‖w‖) _ _)
  -- consider a ball of radius `δ` around `x` in which the Taylor approximation for `f''` is
  -- good up to `δ`.
  rw [HasFDerivWithinAt, hasFDerivAtFilter_iff_isLittleO, isLittleO_iff] at hx
  rcases Metric.mem_nhdsWithin_iff.1 (hx εpos) with ⟨δ, δpos, sδ⟩
  have E1 : ∀ᶠ h in 𝓝[>] (0 : ℝ), h * (‖v‖ + ‖w‖) < δ := by
    have : Filter.Tendsto (fun h => h * (‖v‖ + ‖w‖)) (𝓝[>] (0 : ℝ)) (𝓝 (0 * (‖v‖ + ‖w‖))) :=
      (continuous_id.mul continuous_const).continuousWithinAt
    apply (tendsto_order.1 this).2 δ
    simpa only [zero_mul] using δpos
  have E2 : ∀ᶠ h in 𝓝[>] (0 : ℝ), (h : ℝ) < 1 :=
    mem_nhdsWithin_of_mem_nhds <| Iio_mem_nhds zero_lt_one
  filter_upwards [E1, E2, self_mem_nhdsWithin] with h hδ h_lt_1 hpos
  -- we consider `h` small enough that all points under consideration belong to this ball,
  -- and also with `0 < h < 1`.
  replace hpos : 0 < h := hpos
  have xt_mem : ∀ t ∈ Icc (0 : ℝ) 1, x + h • v + (t * h) • w ∈ interior s := by
    intro t ht
    have : x + h • v ∈ interior s := s_conv.add_smul_mem_interior xs hv ⟨hpos, h_lt_1.le⟩
    rw [← smul_smul]
    apply s_conv.interior.add_smul_mem this _ ht
    rw [add_assoc] at hw
    convert s_conv.add_smul_mem_interior xs hw ⟨hpos, h_lt_1.le⟩ using 1
    module
  -- define a function `g` on `[0,1]` (identified with `[v, v + w]`) such that `g 1 - g 0` is the
  -- quantity to be estimated. We will check that its derivative is given by an explicit
  -- expression `g'`, that we can bound. Then the desired bound for `g 1 - g 0` follows from the
  -- mean value inequality.
  let g t :=
    f (x + h • v + (t * h) • w) - (t * h) • f' x w - (t * h ^ 2) • f'' v w -
      ((t * h) ^ 2 / 2) • f'' w w
  set g' := fun t =>
    f' (x + h • v + (t * h) • w) (h • w) - h • f' x w - h ^ 2 • f'' v w - (t * h ^ 2) • f'' w w
    with hg'
  -- check that `g'` is the derivative of `g`, by a straightforward computation
  have g_deriv : ∀ t ∈ Icc (0 : ℝ) 1, HasDerivWithinAt g (g' t) (Icc 0 1) t := by
    intro t ht
    apply_rules [HasDerivWithinAt.sub, HasDerivWithinAt.add]
    · refine (hf _ ?_).comp_hasDerivWithinAt _ ?_
      · exact xt_mem t ht
      apply_rules [HasDerivAt.hasDerivWithinAt, HasDerivAt.const_add, HasDerivAt.smul_const,
        hasDerivAt_mul_const]
    · apply_rules [HasDerivAt.hasDerivWithinAt, HasDerivAt.smul_const, hasDerivAt_mul_const]
    · apply_rules [HasDerivAt.hasDerivWithinAt, HasDerivAt.smul_const, hasDerivAt_mul_const]
    · suffices H : HasDerivWithinAt (fun u => ((u * h) ^ 2 / 2) • f'' w w)
          ((((2 : ℕ) : ℝ) * (t * h) ^ (2 - 1) * (1 * h) / 2) • f'' w w) (Icc 0 1) t by
        convert H using 2
        ring
      apply_rules [HasDerivAt.hasDerivWithinAt, HasDerivAt.smul_const, hasDerivAt_id',
        HasDerivAt.pow, HasDerivAt.mul_const]
  -- check that `g'` is uniformly bounded, with a suitable bound `ε * ((‖v‖ + ‖w‖) * ‖w‖) * h^2`.
  have g'_bound : ∀ t ∈ Ico (0 : ℝ) 1, ‖g' t‖ ≤ ε * ((‖v‖ + ‖w‖) * ‖w‖) * h ^ 2 := by
    intro t ht
    have I : ‖h • v + (t * h) • w‖ ≤ h * (‖v‖ + ‖w‖) :=
      calc
        ‖h • v + (t * h) • w‖ ≤ ‖h • v‖ + ‖(t * h) • w‖ := norm_add_le _ _
        _ = h * ‖v‖ + t * (h * ‖w‖) := by
          simp only [norm_smul, Real.norm_eq_abs, hpos.le, abs_of_nonneg, abs_mul, ht.left,
            mul_assoc]
        _ ≤ h * ‖v‖ + 1 * (h * ‖w‖) := by gcongr; exact ht.2.le
        _ = h * (‖v‖ + ‖w‖) := by ring
    calc
      ‖g' t‖ = ‖(f' (x + h • v + (t * h) • w) - f' x - f'' (h • v + (t * h) • w)) (h • w)‖ := by
        rw [hg']
        congrm ‖?_‖
        simp only [ContinuousLinearMap.sub_apply, ContinuousLinearMap.add_apply,
          ContinuousLinearMap.smul_apply, map_add, map_smul]
        module
      _ ≤ ‖f' (x + h • v + (t * h) • w) - f' x - f'' (h • v + (t * h) • w)‖ * ‖h • w‖ :=
        (ContinuousLinearMap.le_opNorm _ _)
      _ ≤ ε * ‖h • v + (t * h) • w‖ * ‖h • w‖ := by
        gcongr
        have H : x + h • v + (t * h) • w ∈ Metric.ball x δ ∩ interior s := by
          refine ⟨?_, xt_mem t ⟨ht.1, ht.2.le⟩⟩
          rw [add_assoc, add_mem_ball_iff_norm]
          exact I.trans_lt hδ
        simpa only [mem_setOf_eq, add_assoc x, add_sub_cancel_left] using sδ H
      _ ≤ ε * (‖h • v‖ + ‖h • w‖) * ‖h • w‖ := by
        gcongr
        apply (norm_add_le _ _).trans
        gcongr
        simp only [norm_smul, Real.norm_eq_abs, abs_mul, abs_of_nonneg, ht.1, hpos.le, mul_assoc]
        exact mul_le_of_le_one_left (by positivity) ht.2.le
      _ = ε * ((‖v‖ + ‖w‖) * ‖w‖) * h ^ 2 := by
        simp only [norm_smul, Real.norm_eq_abs, abs_of_nonneg, hpos.le]; ring
  -- conclude using the mean value inequality
  have I : ‖g 1 - g 0‖ ≤ ε * ((‖v‖ + ‖w‖) * ‖w‖) * h ^ 2 := by
    simpa only [mul_one, sub_zero] using
      norm_image_sub_le_of_norm_deriv_le_segment' g_deriv g'_bound 1 (right_mem_Icc.2 zero_le_one)
  convert I using 1
  · congr 1
    simp only [g, add_zero, one_mul, zero_div, zero_mul, sub_zero,
      zero_smul, Ne, not_false_iff, zero_pow, reduceCtorEq]
    abel
  · simp (discharger := positivity) only [Real.norm_eq_abs, abs_of_nonneg]
    ring

/-- One can get `f'' v w` as the limit of `h ^ (-2)` times the alternate sum of the values of `f`
along the vertices of a quadrilateral with sides `h v` and `h w` based at `x`.
In a setting where `f` is not guaranteed to be continuous at `f`, we can still
get this if we use a quadrilateral based at `h v + h w`. -/
theorem Convex.isLittleO_alternate_sum_square {v w : E} (h4v : x + (4 : ℝ) • v ∈ interior s)
    (h4w : x + (4 : ℝ) • w ∈ interior s) :
    (fun h : ℝ => f (x + h • (2 • v + 2 • w)) + f (x + h • (v + w))
        - f (x + h • (2 • v + w)) - f (x + h • (v + 2 • w)) - h ^ 2 • f'' v w) =o[𝓝[>] 0]
      fun h => h ^ 2 := by
  have A : (1 : ℝ) / 2 ∈ Ioc (0 : ℝ) 1 := ⟨by simp, by norm_num⟩
  have B : (1 : ℝ) / 2 ∈ Icc (0 : ℝ) 1 := ⟨by simp, by norm_num⟩
  have h2v2w : x + (2 : ℝ) • v + (2 : ℝ) • w ∈ interior s := by
    convert s_conv.interior.add_smul_sub_mem h4v h4w B using 1
    module
  have h2vww : x + (2 • v + w) + w ∈ interior s := by
    convert h2v2w using 1
    module
  have h2v : x + (2 : ℝ) • v ∈ interior s := by
    convert s_conv.add_smul_sub_mem_interior xs h4v A using 1
    module
  have h2w : x + (2 : ℝ) • w ∈ interior s := by
    convert s_conv.add_smul_sub_mem_interior xs h4w A using 1
    module
  have hvw : x + (v + w) ∈ interior s := by
    convert s_conv.add_smul_sub_mem_interior xs h2v2w A using 1
    module
  have h2vw : x + (2 • v + w) ∈ interior s := by
    convert s_conv.interior.add_smul_sub_mem h2v h2v2w B using 1
    module
  have hvww : x + (v + w) + w ∈ interior s := by
    convert s_conv.interior.add_smul_sub_mem h2w h2v2w B using 1
    module
  have TA1 := s_conv.taylor_approx_two_segment hf xs hx h2vw h2vww
  have TA2 := s_conv.taylor_approx_two_segment hf xs hx hvw hvww
  convert TA1.sub TA2 using 1
  ext h
  simp only [two_smul, smul_add, ← add_assoc, ContinuousLinearMap.map_add,
    ContinuousLinearMap.add_apply]
  abel

/-- Assume that `f` is differentiable inside a convex set `s`, and that its derivative `f'` is
differentiable at a point `x`. Then, given two vectors `v` and `w` pointing inside `s`, one
has `f'' v w = f'' w v`. Superseded by `Convex.second_derivative_within_at_symmetric`, which
removes the assumption that `v` and `w` point inside `s`. -/
theorem Convex.second_derivative_within_at_symmetric_of_mem_interior {v w : E}
    (h4v : x + (4 : ℝ) • v ∈ interior s) (h4w : x + (4 : ℝ) • w ∈ interior s) :
    f'' w v = f'' v w := by
  have A : (fun h : ℝ => h ^ 2 • (f'' w v - f'' v w)) =o[𝓝[>] 0] fun h => h ^ 2 := by
    convert (s_conv.isLittleO_alternate_sum_square hf xs hx h4v h4w).sub
      (s_conv.isLittleO_alternate_sum_square hf xs hx h4w h4v) using 1
    ext h
    simp only [add_comm, smul_add, smul_sub]
    abel
  have B : (fun _ : ℝ => f'' w v - f'' v w) =o[𝓝[>] 0] fun _ => (1 : ℝ) := by
    have : (fun h : ℝ => 1 / h ^ 2) =O[𝓝[>] 0] fun h => 1 / h ^ 2 := isBigO_refl _ _
    have C := this.smul_isLittleO A
    apply C.congr' _ _
    · filter_upwards [self_mem_nhdsWithin]
      intro h (hpos : 0 < h)
      match_scalars <;> field_simp
    · filter_upwards [self_mem_nhdsWithin] with h (hpos : 0 < h)
      simp [field]
  simpa only [sub_eq_zero] using isLittleO_const_const_iff.1 B

end

/-- If a function is differentiable inside a convex set with nonempty interior, and has a second
derivative at a point of this convex set, then this second derivative is symmetric. -/
theorem Convex.second_derivative_within_at_symmetric {s : Set E} (s_conv : Convex ℝ s)
    (hne : (interior s).Nonempty) {f : E → F} {f' : E → E →L[ℝ] F} {f'' : E →L[ℝ] E →L[ℝ] F}
    (hf : ∀ x ∈ interior s, HasFDerivAt f (f' x) x) {x : E} (xs : x ∈ s)
    (hx : HasFDerivWithinAt f' f'' (interior s) x) (v w : E) : f'' v w = f'' w v := by
  /- we work around a point `x + 4 z` in the interior of `s`. For any vector `m`,
    then `x + 4 (z + t m)` also belongs to the interior of `s` for small enough `t`. This means that
    we will be able to apply `second_derivative_within_at_symmetric_of_mem_interior` to show
    that `f''` is symmetric, after cancelling all the contributions due to `z`. -/
  rcases hne with ⟨y, hy⟩
  obtain ⟨z, hz⟩ : ∃ z, z = ((1 : ℝ) / 4) • (y - x) := ⟨((1 : ℝ) / 4) • (y - x), rfl⟩
  have A : ∀ m : E, Filter.Tendsto (fun t : ℝ => x + (4 : ℝ) • (z + t • m)) (𝓝 0) (𝓝 y) := by
    intro m
    have : x + (4 : ℝ) • (z + (0 : ℝ) • m) = y := by simp [hz]
    rw [← this]
    refine tendsto_const_nhds.add <| tendsto_const_nhds.smul <| tendsto_const_nhds.add ?_
    exact continuousAt_id.smul continuousAt_const
  have B : ∀ m : E, ∀ᶠ t in 𝓝[>] (0 : ℝ), x + (4 : ℝ) • (z + t • m) ∈ interior s := by
    intro m
    apply nhdsWithin_le_nhds
    apply A m
    rw [mem_interior_iff_mem_nhds] at hy
    exact interior_mem_nhds.2 hy
  -- we choose `t m > 0` such that `x + 4 (z + (t m) m)` belongs to the interior of `s`, for any
  -- vector `m`.
  choose t ts tpos using fun m => ((B m).and self_mem_nhdsWithin).exists
  -- applying `second_derivative_within_at_symmetric_of_mem_interior` to the vectors `z`
  -- and `z + (t m) m`, we deduce that `f'' m z = f'' z m` for all `m`.
  have C : ∀ m : E, f'' m z = f'' z m := by
    intro m
    have : f'' (z + t m • m) (z + t 0 • (0 : E)) = f'' (z + t 0 • (0 : E)) (z + t m • m) :=
      s_conv.second_derivative_within_at_symmetric_of_mem_interior hf xs hx (ts 0) (ts m)
    simp only [ContinuousLinearMap.map_add, ContinuousLinearMap.map_smul, add_right_inj,
      ContinuousLinearMap.add_apply, Pi.smul_apply, ContinuousLinearMap.coe_smul', add_zero,
      smul_zero] at this
    exact smul_right_injective F (tpos m).ne' this
  -- applying `second_derivative_within_at_symmetric_of_mem_interior` to the vectors `z + (t v) v`
  -- and `z + (t w) w`, we deduce that `f'' v w = f'' w v`. Cross terms involving `z` can be
  -- eliminated thanks to the fact proved above that `f'' m z = f'' z m`.
  have : f'' (z + t v • v) (z + t w • w) = f'' (z + t w • w) (z + t v • v) :=
    s_conv.second_derivative_within_at_symmetric_of_mem_interior hf xs hx (ts w) (ts v)
  simp only [ContinuousLinearMap.map_add, ContinuousLinearMap.map_smul, smul_smul,
    ContinuousLinearMap.add_apply, Pi.smul_apply, ContinuousLinearMap.coe_smul', C] at this
  have : (t v * t w) • (f'' v) w = (t v * t w) • (f'' w) v := by
    linear_combination (norm := module) this
  apply smul_right_injective F _ this
  simp [(tpos v).ne', (tpos w).ne']

/-- If a function is differentiable around `x`, and has two derivatives at `x`, then the second
derivative is symmetric. Version over `ℝ`. See `second_derivative_symmetric_of_eventually` for a
version over `ℝ` or `ℂ`. -/
theorem second_derivative_symmetric_of_eventually_of_real {f : E → F} {f' : E → E →L[ℝ] F}
    {f'' : E →L[ℝ] E →L[ℝ] F} (hf : ∀ᶠ y in 𝓝 x, HasFDerivAt f (f' y) y) (hx : HasFDerivAt f' f'' x)
    (v w : E) : f'' v w = f'' w v := by
  rcases Metric.mem_nhds_iff.1 hf with ⟨ε, εpos, hε⟩
  have A : (interior (Metric.ball x ε)).Nonempty := by
    rwa [Metric.isOpen_ball.interior_eq, Metric.nonempty_ball]
  exact
    Convex.second_derivative_within_at_symmetric (convex_ball x ε) A
      (fun y hy => hε (interior_subset hy)) (Metric.mem_ball_self εpos) hx.hasFDerivWithinAt v w

end Real

namespace EulerOrdered
open MeasureTheory Set Filter
open scoped BigOperators Topology ContDiff
abbrev Space := EulerPeriodicBox.Space
abbrev Joint := ℝ × Space
abbrev Vector := Fin 5 → Joint → ℝ
abbrev Matrix := Fin 3 → Fin 5 → Fin 5 → Joint → ℝ

def D (u : Joint → ℝ) (e : Joint) (z : Joint) : ℝ := fderiv ℝ u z e

def et : Joint := (1,fun _ => 0)
def ex (j : Fin 3) : Joint := (0,Pi.single j 1)
def bi (j : Fin 3) : Fin 5 := j.castSucc.succ

lemma derivative_differentiable {u : Joint → ℝ} {z : Joint}
    (h : ContDiffAt ℝ 2 u z) : DifferentiableAt ℝ (fderiv ℝ u) z :=
  (h.fderiv_right (m := 1) (by norm_num)).differentiableAt (by norm_num)

lemma D_differentiable {u : Joint → ℝ} {z : Joint} (h : ContDiffAt ℝ 2 u z) (e : Joint) :
    DifferentiableAt ℝ (D u e) z :=
  (derivative_differentiable h).clm_apply (differentiableAt_const e)

lemma second_directional {u : Joint → ℝ} {z : Joint} (h : ContDiffAt ℝ 2 u z) (e k : Joint) :
    D (D u e) k z = fderiv ℝ (fderiv ℝ u) z k e := by
  have hd := (derivative_differentiable h).hasFDerivAt.clm_apply (hasFDerivAt_const e z)
  change (fderiv ℝ (fun y => fderiv ℝ u y e) z) k = _
  rw [hd.fderiv]
  simp

theorem mixed_directional_commute {u : Joint → ℝ} {z : Joint}
    (h : ContDiffAt ℝ 2 u z) (e k : Joint) : D (D u e) k z = D (D u k) e z := by
  rw [second_directional h e k,second_directional h k e]
  exact second_derivative_symmetric_of_eventually_of_real
    ((h.eventually (by norm_num)).mono fun y hy => (hy.differentiableAt (by norm_num)).hasFDerivAt)
    (derivative_differentiable h).hasFDerivAt k e

theorem directional_line_hasDeriv {u : Joint → ℝ} {z : Joint}
    (h : DifferentiableAt ℝ u z) (e : Joint) :
    HasDerivAt (fun s : ℝ => u (z+s • e)) (D u e z) 0 := by
  have hc : HasDerivAt (fun s : ℝ => z+s • e) e 0 := by
    simpa using ((hasDerivAt_id (0:ℝ)).smul_const e).const_add z
  have hu : HasFDerivAt u (fderiv ℝ u z) (z+(0:ℝ) • e) := by
    simpa only [zero_smul,add_zero] using h.hasFDerivAt
  simpa only [zero_smul,add_zero] using hu.comp_hasDerivAt 0 hc

lemma D_add {f g : Joint → ℝ} {z : Joint} (hf : DifferentiableAt ℝ f z)
    (hg : DifferentiableAt ℝ g z) (e : Joint) :
    D (fun y => f y+g y) e z = D f e z+D g e z := by
  simp only [D,fderiv_fun_add hf hg,ContinuousLinearMap.add_apply]

lemma D_mul {f g : Joint → ℝ} {z : Joint} (hf : DifferentiableAt ℝ f z)
    (hg : DifferentiableAt ℝ g z) (e : Joint) :
    D (fun y => f y*g y) e z = D f e z*g z+f z*D g e z := by
  simp only [D,fderiv_fun_mul hf hg,ContinuousLinearMap.add_apply,
    ContinuousLinearMap.smul_apply,smul_eq_mul]
  ring

lemma D_const_mul {f : Joint → ℝ} {z : Joint} (hf : DifferentiableAt ℝ f z)
    (c : ℝ) (e : Joint) : D (fun y => c*f y) e z = c*D f e z := by
  rw [D_mul (differentiableAt_const c) hf]
  simp [D]

lemma D_sum {I : Type*} [Fintype I] (f : I → Joint → ℝ) {z : Joint}
    (hf : ∀ i, DifferentiableAt ℝ (f i) z) (e : Joint) :
    D (fun y => ∑ i, f i y) e z = ∑ i, D (f i) e z := by
  classical
  simp only [D,fderiv_fun_sum (fun i _ => hf i),ContinuousLinearMap.sum_apply]

def coefficient (q p v : ℝ) (j : Fin 3) (i m : Fin 5) : ℝ :=
  (if i=m then 1 else 0)*v+
  ((if i=0 ∧ m=bi j then -1 else 0)+(if i=bi j ∧ m=4 then 1 else 0))*q+
  (if i=4 ∧ m=bi j then 2 else 0)*p

def coefficients (q p : Joint → ℝ) (v : Fin 3 → Joint → ℝ) : Matrix :=
  fun j i m z => coefficient (q z) (p z) (v j z) j i m

lemma coefficient_differentiable {q p v : Joint → ℝ} {z : Joint}
    (hq : DifferentiableAt ℝ q z) (hp : DifferentiableAt ℝ p z) (hv : DifferentiableAt ℝ v z)
    (j : Fin 3) (i m : Fin 5) :
    DifferentiableAt ℝ (fun y => coefficient (q y) (p y) (v y) j i m) z :=
  (((differentiableAt_const (if i=m then (1:ℝ) else 0)).mul hv).add
    ((differentiableAt_const ((if i=0 ∧ m=bi j then (-1:ℝ) else 0)+
      (if i=bi j ∧ m=4 then (1:ℝ) else 0))).mul hq)).add
    ((differentiableAt_const (if i=4 ∧ m=bi j then (2:ℝ) else 0)).mul hp)

theorem coefficient_derivative {q p v : Joint → ℝ} {z : Joint}
    (hq : DifferentiableAt ℝ q z) (hp : DifferentiableAt ℝ p z) (hv : DifferentiableAt ℝ v z)
    (j : Fin 3) (i m : Fin 5) (e : Joint) :
    D (fun y => coefficient (q y) (p y) (v y) j i m) e z =
      coefficient (D q e z) (D p e z) (D v e z) j i m := by
  unfold coefficient
  let cv : ℝ := if i=m then 1 else 0
  let cq : ℝ := (if i=0 ∧ m=bi j then -1 else 0)+(if i=bi j ∧ m=4 then 1 else 0)
  let cp : ℝ := if i=4 ∧ m=bi j then 2 else 0
  change D (fun y => cv*v y+cq*q y+cp*p y) e z =
    cv*D v e z+cq*D q e z+cp*D p e z
  have hv' : DifferentiableAt ℝ (fun y => cv*v y) z :=
    (differentiableAt_const cv).mul hv
  have hq' : DifferentiableAt ℝ (fun y => cq*q y) z :=
    (differentiableAt_const cq).mul hq
  have hp' : DifferentiableAt ℝ (fun y => cp*p y) z :=
    (differentiableAt_const cp).mul hp
  have hs : DifferentiableAt ℝ (fun y => cv*v y+cq*q y) z := hv'.add hq'
  rw [D_add (f := fun y => cv*v y+cq*q y) (g := fun y => cp*p y) hs hp' e,
    D_add (f := fun y => cv*v y) (g := fun y => cq*q y) hv' hq' e,
    D_const_mul hv,D_const_mul hq,D_const_mul hp]

lemma row_a (q p v : ℝ) (j : Fin 3) (Z : Fin 5 → ℝ) :
    (∑ m, coefficient q p v j 0 m*Z m) = v*Z 0+(-q)*Z (bi j) := by
  fin_cases j <;> simp [coefficient,bi,Fin.sum_univ_succ]

lemma row_b (q p v : ℝ) (j i : Fin 3) (Z : Fin 5 → ℝ) :
    (∑ m, coefficient q p v j (bi i) m*Z m) =
      v*Z (bi i)+(if i=j then q*Z 4 else 0) := by
  fin_cases j <;> fin_cases i <;> simp [coefficient,bi,Fin.sum_univ_succ]

lemma row_c (q p v : ℝ) (j : Fin 3) (Z : Fin 5 → ℝ) :
    (∑ m, coefficient q p v j 4 m*Z m) = v*Z 4+2*p*Z (bi j) := by
  fin_cases j <;> simp [coefficient,bi,Fin.sum_univ_succ] <;> ring

def pack (W : EulerTransport.TestState) (i : Fin 5) : ℝ :=
  if i=0 then W.a else if i=1 then W.b 0 else if i=2 then W.b 1 else if i=3 then W.b 2 else W.c

theorem coefficient_acoustic_map (q p v : ℝ) (j : Fin 3) (W : EulerTransport.TestState) :
    (∑ m, coefficient q p v j 0 m*pack W m) = v*W.a+(EulerTransport.acoustic q p j W).a ∧
    (∀ i, (∑ m, coefficient q p v j (bi i) m*pack W m) =
      v*W.b i+(EulerTransport.acoustic q p j W).b i) ∧
    (∑ m, coefficient q p v j 4 m*pack W m) = v*W.c+(EulerTransport.acoustic q p j W).c := by
  refine ⟨?_,?_,?_⟩
  · rw [row_a]
    fin_cases j <;> simp [pack,bi,EulerTransport.acoustic]
  · intro i
    rw [row_b]
    fin_cases j <;> fin_cases i <;> simp [pack,bi,EulerTransport.acoustic]
  · rw [row_c]
    fin_cases j <;> simp [pack,bi,EulerTransport.acoustic]

def residual (A : Matrix) (U : Vector) (i : Fin 5) (z : Joint) : ℝ :=
  D (U i) et z+∑ j, ∑ m, A j i m z*D (U m) (ex j) z

def matrixForcing (A : Matrix) (U F : Vector) (e : Joint) (i : Fin 5) (z : Joint) : ℝ :=
  D (F i) e z-∑ j, ∑ m, D (A j i m) e z*D (U m) (ex j) z

theorem differentiated_equation (A : Matrix) (U F : Vector) (z : Joint) (e : Joint)
    (hu : ∀ i, ContDiffAt ℝ 2 (U i) z)
    (ha : ∀ j i m, DifferentiableAt ℝ (A j i m) z)
    (heq : ∀ i, residual A U i =ᶠ[𝓝 z] F i) (i : Fin 5) :
    residual A (fun m => D (U m) e) i z = matrixForcing A U F e i z := by
  have hp : ∀ j m, DifferentiableAt ℝ (fun y => A j i m y*D (U m) (ex j) y) z :=
    fun j m => (ha j i m).mul (D_differentiable (hu m) (ex j))
  have hr : ∀ j, DifferentiableAt ℝ (fun y => ∑ m, A j i m y*D (U m) (ex j) y) z :=
    fun j => DifferentiableAt.fun_sum (fun m _ => hp j m)
  have hsum : DifferentiableAt ℝ (fun y => ∑ j, ∑ m, A j i m y*D (U m) (ex j) y) z :=
    DifferentiableAt.fun_sum (fun j _ => hr j)
  have hd : D (residual A U i) e z = D (D (U i) et) e z+
      ∑ j, ∑ m, (D (A j i m) e z*D (U m) (ex j) z+
        A j i m z*D (D (U m) (ex j)) e z) := by
    unfold residual
    rw [D_add (D_differentiable (hu i) et) hsum,D_sum _ hr]
    congr 1
    apply Finset.sum_congr rfl
    intro j _
    rw [D_sum _ (hp j)]
    apply Finset.sum_congr rfl
    intro m _
    exact D_mul (ha j i m) (D_differentiable (hu m) (ex j)) e
  have heqd : D (residual A U i) e z = D (F i) e z :=
    congrArg (fun c : Joint →L[ℝ] ℝ => c e) (heq i).fderiv_eq
  rw [heqd,mixed_directional_commute (hu i) et e] at hd
  have hc : ∀ j m, D (D (U m) (ex j)) e z = D (D (U m) e) (ex j) z :=
    fun j m => mixed_directional_commute (hu m) (ex j) e
  simp_rw [hc,Finset.sum_add_distrib] at hd
  unfold residual matrixForcing
  linarith

def commutatorForcing (q p : Joint → ℝ) (v : Fin 3 → Joint → ℝ)
    (U F : Vector) (e : Joint) (i : Fin 5) (z : Joint) : ℝ :=
  D (F i) e z-∑ j, ∑ m,
    coefficient (D q e z) (D p e z) (D (v j) e z) j i m*D (U m) (ex j) z

theorem euler_first_equation (q p : Joint → ℝ) (v : Fin 3 → Joint → ℝ)
    (U F : Vector) (z : Joint) (k : Fin 3)
    (hu : ∀ i, ContDiffAt ℝ 2 (U i) z)
    (hq : DifferentiableAt ℝ q z) (hp : DifferentiableAt ℝ p z)
    (hv : ∀ j, DifferentiableAt ℝ (v j) z)
    (heq : ∀ i, residual (coefficients q p v) U i =ᶠ[𝓝 z] F i) (i : Fin 5) :
    residual (coefficients q p v) (fun m => D (U m) (ex k)) i z =
      commutatorForcing q p v U F (ex k) i z := by
  have h := differentiated_equation (coefficients q p v) U F z (ex k) hu
    (fun j i m => coefficient_differentiable hq hp (hv j) j i m) heq i
  unfold matrixForcing coefficients at h
  simp_rw [coefficient_derivative hq hp (hv _) _ _ _] at h
  exact h

theorem primitive_first_equation (U : Vector) (z : Joint) (k : Fin 3)
    (hu : ∀ i, ContDiffAt ℝ 2 (U i) z)
    (heq : ∀ i, residual (coefficients (U 0) (U 4) (fun j => U (bi j))) U i =ᶠ[𝓝 z] (fun _ => 0))
    (i : Fin 5) :
    residual (coefficients (U 0) (U 4) (fun j => U (bi j))) (fun m => D (U m) (ex k)) i z =
      commutatorForcing (U 0) (U 4) (fun j => U (bi j)) U (fun _ _ => 0) (ex k) i z :=
  euler_first_equation (U 0) (U 4) (fun j => U (bi j)) U (fun _ _ => 0) z k hu
    ((hu 0).differentiableAt (by norm_num)) ((hu 4).differentiableAt (by norm_num))
    (fun j => (hu (bi j)).differentiableAt (by norm_num)) heq i

-- The background coefficients stay q,p; the test-field components come from U.
def fields (q p : Joint → ℝ) (U : Vector) : EulerMetricEnergy.Fields where
  q := fun t x => q (t,x)
  p := fun t x => p (t,x)
  a := fun t x => U 0 (t,x)
  b := fun j t x => U (bi j) (t,x)
  c := fun t x => U 4 (t,x)
def timeFields (q p : Joint → ℝ) (U : Vector) : EulerMetricEnergy.Fields :=
  fields (D q et) (D p et) (fun i => D (U i) et)
def spaceFields (q p : Joint → ℝ) (U : Vector) (j : Fin 3) : EulerMetricEnergy.Fields :=
  fields (D q (ex j)) (D p (ex j)) (fun i => D (U i) (ex j))
def velocity (v : Fin 3 → Joint → ℝ) (t : ℝ) : Fin 3 → Space → ℝ := fun j x => v j (t,x)
def diagonal (v : Fin 3 → Joint → ℝ) (t : ℝ) : Fin 3 → Space → ℝ := fun j x => D (v j) (ex j) (t,x)
def stateOf (F : Vector) (t : ℝ) (x : Space) : EulerTransport.TestState :=
  ⟨F 0 (t,x),fun j => F (bi j) (t,x),F 4 (t,x)⟩

lemma equations_to_balance (q p : Joint → ℝ) (v : Fin 3 → Joint → ℝ) (U F : Vector) (t : ℝ)
    (hq : ∀ x, 0 < q (t,x)) (hp : ∀ x, 0 < p (t,x))
    (hqe : ∀ x, D q et (t,x)+(∑ j, v j (t,x)*D q (ex j) (t,x)) =
      q (t,x)*EulerBalance.theta (diagonal v t) x)
    (hpe : ∀ x, D p et (t,x)+(∑ j, v j (t,x)*D p (ex j) (t,x)) =
      -2*p (t,x)*EulerBalance.theta (diagonal v t) x)
    (heq : ∀ x i, residual (coefficients q p v) U i (t,x) = F i (t,x)) :
    EulerBalance.EulerPremises t (fields q p U) (timeFields q p U) (spaceFields q p U)
      (velocity v t) (diagonal v t) (stateOf F t) := by
  refine ⟨hq,hp,hqe,hpe,?_,?_,?_⟩
  · intro x
    have h := heq x 0
    simp only [residual,coefficients] at h
    simp_rw [row_a,Finset.sum_add_distrib] at h
    simpa only [timeFields,spaceFields,fields,velocity,stateOf,add_assoc] using h
  · intro x i
    have h := heq x (bi i)
    simp only [residual,coefficients] at h
    simp_rw [row_b,Finset.sum_add_distrib] at h
    simpa only [timeFields,spaceFields,fields,velocity,stateOf,add_assoc] using h
  · intro x
    have h := heq x 4
    simp only [residual,coefficients] at h
    simp_rw [row_c,Finset.sum_add_distrib] at h
    simpa only [timeFields,spaceFields,fields,velocity,stateOf,add_assoc] using h

theorem first_derivative_energy_balance (L t eps : ℝ) (hL : 0 < L)
    (q p : Joint → ℝ) (v : Fin 3 → Joint → ℝ) (U F : Vector) (k : Fin 3)
    (bound : Space → ℝ)
    (hu : ∀ x i, ContDiffAt ℝ 2 (U i) (t,x))
    (hq1 : ∀ x, DifferentiableAt ℝ q (t,x)) (hp1 : ∀ x, DifferentiableAt ℝ p (t,x))
    (hv1 : ∀ x j, DifferentiableAt ℝ (v j) (t,x))
    (heq : ∀ x i, residual (coefficients q p v) U i =ᶠ[𝓝 (t,x)] F i)
    (hq : ∀ x, 0 < q (t,x)) (hp : ∀ x, 0 < p (t,x))
    (hqe : ∀ x, D q et (t,x)+(∑ j, v j (t,x)*D q (ex j) (t,x)) =
      q (t,x)*EulerBalance.theta (diagonal v t) x)
    (hpe : ∀ x, D p et (t,x)+(∑ j, v j (t,x)*D p (ex j) (t,x)) =
      -2*p (t,x)*EulerBalance.theta (diagonal v t) x)
    (ht : EulerBalance.TimePremises L t eps
      (fields q p (fun i => D (U i) (ex k)))
      (timeFields q p (fun i => D (U i) (ex k))) bound)
    (hs : EulerBalance.SpatialPremises L t
      (fields q p (fun i => D (U i) (ex k)))
      (spaceFields q p (fun i => D (U i) (ex k))) (velocity v t) (diagonal v t)) :
    HasDerivAt (fun s => EulerPeriodicBox.cubeAverage L
      (EulerMetricEnergy.density (fields q p (fun i => D (U i) (ex k))) s))
      (EulerPeriodicBox.cubeAverage L (EulerBalance.forcingDensity
        (fields q p (fun i => D (U i) (ex k))) t (diagonal v t)
        (stateOf (commutatorForcing q p v U F (ex k)) t))) t := by
  have hder : ∀ x i, residual (coefficients q p v) (fun m => D (U m) (ex k)) i (t,x) =
      commutatorForcing q p v U F (ex k) i (t,x) :=
    fun x i => euler_first_equation q p v U F (t,x) k (hu x) (hq1 x) (hp1 x) (hv1 x) (heq x) i
  exact (EulerBalance.normalized_energy_balance L t eps hL _ _ _ bound _ _ _ ht hs
    (equations_to_balance q p v (fun i => D (U i) (ex k))
      (commutatorForcing q p v U F (ex k)) t hq hp hqe hpe hder)).2

-- Independent scalar-coordinate polynomial components challenge the commutator sign.
def controlFa (s : ℝ) : ℝ := 2*s^2-4*s*(s+1)
def controlFb (s : ℝ) : ℝ := 4*s^2+6*s*(s+1)
def controlFc (s : ℝ) : ℝ := 6*s^2+8*s*(s+2)

theorem nonconstant_commutator_control :
    HasDerivAt controlFa (-8) 1 ∧ HasDerivAt controlFb 26 1 ∧ HasDerivAt controlFc 44 1 ∧
    (1*2-1*4 = (-2:ℝ)) ∧ (1*4+1*6 = (10:ℝ)) ∧ (1*6+2*1*4 = (14:ℝ)) ∧
    ((-8:ℝ)-(-2) = -6) ∧ ((26:ℝ)-10 = 16) ∧ ((44:ℝ)-14 = 30) ∧
    ((-6:ℝ) ≠ -8 ∧ (-6:ℝ) ≠ -10) ∧ ((16:ℝ) ≠ 26 ∧ (16:ℝ) ≠ 36) ∧
    ((30:ℝ) ≠ 44 ∧ (30:ℝ) ≠ 58) := by
  have hid := hasDerivAt_id (1:ℝ)
  have ha := ((hid.pow 2).const_mul 2).sub (((hid.const_mul 4).mul (hid.add_const 1)))
  have hb := ((hid.pow 2).const_mul 4).add (((hid.const_mul 6).mul (hid.add_const 1)))
  have hc := ((hid.pow 2).const_mul 6).add (((hid.const_mul 8).mul (hid.add_const 2)))
  refine ⟨?_,?_,?_,?_⟩
  · change HasDerivAt (fun s : ℝ => 2*s^2-4*s*(s+1)) (-8) 1
    convert ha using 1
    norm_num
  · change HasDerivAt (fun s : ℝ => 4*s^2+6*s*(s+1)) (26) 1
    convert hb using 1
    norm_num
  · change HasDerivAt (fun s : ℝ => 6*s^2+8*s*(s+2)) (44) 1
    convert hc using 1
    norm_num
  · norm_num

end EulerOrdered

namespace EulerErrorField
open EulerOrdered
open scoped Topology

def difference (U V : Vector) : Vector := fun i z => U i z-V i z
def stateMatrix (U : Vector) : Matrix := coefficients (U 0) (U 4) (fun j => U (bi j))
def candidateResidual (V : Vector) : Vector := EulerOrdered.residual (stateMatrix V) V

def differenceForcing (U V : Vector) : Vector := fun i z =>
  ∑ j, ∑ m, stateMatrix (difference U V) j i m z*D (V m) (ex j) z

def errorForcing (U V : Vector) : Vector := fun i z =>
  -candidateResidual V i z-differenceForcing U V i z

lemma D_sub {f g : Joint → ℝ} {z : Joint}
    (hf : DifferentiableAt ℝ f z) (hg : DifferentiableAt ℝ g z) (e : Joint) :
    D (fun y => f y-g y) e z = D f e z-D g e z := by
  have h : HasFDerivAt (fun y => f y-g y) (fderiv ℝ f z-fderiv ℝ g z) z :=
    hf.hasFDerivAt.sub hg.hasFDerivAt
  unfold D
  rw [h.fderiv]
  rfl

theorem coefficient_sub (q p v Q P w : ℝ) (j : Fin 3) (i m : Fin 5) :
    coefficient (q-Q) (p-P) (v-w) j i m =
      coefficient q p v j i m-coefficient Q P w j i m := by
  unfold coefficient
  ring

theorem stateMatrix_difference (U V : Vector) (j : Fin 3) (i m : Fin 5) (z : Joint) :
    stateMatrix (difference U V) j i m z = stateMatrix U j i m z-stateMatrix V j i m z :=
  coefficient_sub _ _ _ _ _ _ j i m

lemma residual_sub (A : Matrix) (U V : Vector) (z : Joint)
    (hu : ∀ i, DifferentiableAt ℝ (U i) z) (hv : ∀ i, DifferentiableAt ℝ (V i) z)
    (i : Fin 5) :
    EulerOrdered.residual A (difference U V) i z = EulerOrdered.residual A U i z-EulerOrdered.residual A V i z := by
  unfold EulerOrdered.residual difference
  simp_rw [D_sub (hu _) (hv _),mul_sub,Finset.sum_sub_distrib]
  ring

lemma residual_change (A B : Matrix) (V : Vector) (i : Fin 5) (z : Joint) :
    EulerOrdered.residual A V i z = EulerOrdered.residual B V i z+
      ∑ j, ∑ m, (A j i m z-B j i m z)*D (V m) (ex j) z := by
  unfold EulerOrdered.residual
  simp_rw [sub_mul,Finset.sum_sub_distrib]
  ring

theorem error_residual_identity (U V : Vector) (z : Joint)
    (hu : ∀ i, DifferentiableAt ℝ (U i) z) (hv : ∀ i, DifferentiableAt ℝ (V i) z)
    (i : Fin 5) :
    EulerOrdered.residual (stateMatrix U) (difference U V) i z =
      candidateResidual U i z+errorForcing U V i z := by
  rw [residual_sub _ U V z hu hv i,residual_change (stateMatrix U) (stateMatrix V) V i z]
  unfold errorForcing differenceForcing candidateResidual
  simp_rw [stateMatrix_difference]
  ring

theorem actual_error_equation (U V : Vector) (z : Joint)
    (hu : ∀ i, DifferentiableAt ℝ (U i) z) (hv : ∀ i, DifferentiableAt ℝ (V i) z)
    (heq : ∀ i, candidateResidual U i z = 0) (i : Fin 5) :
    EulerOrdered.residual (stateMatrix U) (difference U V) i z = errorForcing U V i z := by
  rw [error_residual_identity U V z hu hv i,heq i,zero_add]

theorem error_neighborhood_equation (U V : Vector) (z : Joint)
    (hu : ∀ i, ContDiffAt ℝ 2 (U i) z) (hv : ∀ i, ContDiffAt ℝ 2 (V i) z)
    (heq : ∀ i, candidateResidual U i =ᶠ[𝓝 z] (fun _ => 0)) (i : Fin 5) :
    EulerOrdered.residual (stateMatrix U) (difference U V) i =ᶠ[𝓝 z] errorForcing U V i := by
  have hu' : ∀ᶠ y in 𝓝 z, ∀ m, DifferentiableAt ℝ (U m) y :=
    Filter.eventually_all.mpr fun m =>
      ((hu m).eventually (by norm_num)).mono fun y hy => hy.differentiableAt (by norm_num)
  have hv' : ∀ᶠ y in 𝓝 z, ∀ m, DifferentiableAt ℝ (V m) y :=
    Filter.eventually_all.mpr fun m =>
      ((hv m).eventually (by norm_num)).mono fun y hy => hy.differentiableAt (by norm_num)
  filter_upwards [hu',hv',heq i] with y huy hvy hey
  rw [error_residual_identity U V y huy hvy i,hey,zero_add]

def principalCommutator (U V : Vector) (e : Joint) : Vector := fun i z =>
  ∑ j, ∑ m, D (stateMatrix U j i m) e z*D (difference U V m) (ex j) z

def firstForcing (U V : Vector) (e : Joint) : Vector := fun i z =>
  D (errorForcing U V i) e z-principalCommutator U V e i z

theorem actual_first_error_equation (U V : Vector) (z : Joint) (k : Fin 3)
    (hu : ∀ i, ContDiffAt ℝ 2 (U i) z) (hv : ∀ i, ContDiffAt ℝ 2 (V i) z)
    (heq : ∀ i, candidateResidual U i =ᶠ[𝓝 z] (fun _ => 0)) (i : Fin 5) :
    EulerOrdered.residual (stateMatrix U) (fun m => D (difference U V m) (ex k)) i z =
      firstForcing U V (ex k) i z := by
  have hw : ∀ m, ContDiffAt ℝ 2 (difference U V m) z := fun m => (hu m).sub (hv m)
  exact differentiated_equation (stateMatrix U) (difference U V) (errorForcing U V) z (ex k)
    hw (fun j i m => coefficient_differentiable
      ((hu 0).differentiableAt (by norm_num)) ((hu 4).differentiableAt (by norm_num))
      ((hu (bi j)).differentiableAt (by norm_num)) j i m)
    (error_neighborhood_equation U V z hu hv heq) i

lemma stateMatrix_differentiable (U : Vector) (z : Joint)
    (hu : ∀ i, DifferentiableAt ℝ (U i) z) (j : Fin 3) (i m : Fin 5) :
    DifferentiableAt ℝ (stateMatrix U j i m) z :=
  coefficient_differentiable (hu 0) (hu 4) (hu (bi j)) j i m

lemma candidateResidual_differentiable (V : Vector) (z : Joint)
    (hv : ∀ i, ContDiffAt ℝ 2 (V i) z) (i : Fin 5) :
    DifferentiableAt ℝ (candidateResidual V i) z := by
  have hp : ∀ j m, DifferentiableAt ℝ
      (fun y => stateMatrix V j i m y*D (V m) (ex j) y) z := fun j m =>
    (stateMatrix_differentiable V z (fun m => (hv m).differentiableAt (by norm_num)) j i m).mul
      (D_differentiable (hv m) (ex j))
  exact (D_differentiable (hv i) et).add
    (DifferentiableAt.fun_sum fun j _ => DifferentiableAt.fun_sum fun m _ => hp j m)

def differentiatedDifference (U V : Vector) (e : Joint) : Vector := fun i z =>
  ∑ j, ∑ m, (D (stateMatrix (difference U V) j i m) e z*D (V m) (ex j) z+
    stateMatrix (difference U V) j i m z*D (D (V m) (ex j)) e z)

theorem differenceForcing_derivative (U V : Vector) (z : Joint) (e : Joint)
    (hu : ∀ i, DifferentiableAt ℝ (U i) z) (hv : ∀ i, ContDiffAt ℝ 2 (V i) z)
    (i : Fin 5) :
    D (differenceForcing U V i) e z = differentiatedDifference U V e i z := by
  have hw : ∀ m, DifferentiableAt ℝ (difference U V m) z :=
    fun m => (hu m).sub ((hv m).differentiableAt (by norm_num))
  have hp : ∀ j m, DifferentiableAt ℝ
      (fun y => stateMatrix (difference U V) j i m y*D (V m) (ex j) y) z :=
    fun j m => (stateMatrix_differentiable _ z hw j i m).mul
      (D_differentiable (hv m) (ex j))
  unfold differenceForcing differentiatedDifference
  rw [D_sum _ (fun j => DifferentiableAt.fun_sum fun m _ => hp j m)]
  apply Finset.sum_congr rfl
  intro j _
  rw [D_sum _ (hp j)]
  apply Finset.sum_congr rfl
  intro m _
  exact D_mul (stateMatrix_differentiable _ z hw j i m)
    (D_differentiable (hv m) (ex j)) e

theorem expanded_first_forcing (U V : Vector) (z : Joint) (e : Joint)
    (hu : ∀ i, DifferentiableAt ℝ (U i) z) (hv : ∀ i, ContDiffAt ℝ 2 (V i) z)
    (i : Fin 5) :
    firstForcing U V e i z = -D (candidateResidual V i) e z-
      differentiatedDifference U V e i z-principalCommutator U V e i z := by
  have hw : ∀ m, DifferentiableAt ℝ (difference U V m) z :=
    fun m => (hu m).sub ((hv m).differentiableAt (by norm_num))
  have hp : ∀ j m, DifferentiableAt ℝ
      (fun y => stateMatrix (difference U V) j i m y*D (V m) (ex j) y) z :=
    fun j m => (stateMatrix_differentiable _ z hw j i m).mul
      (D_differentiable (hv m) (ex j))
  have hd : DifferentiableAt ℝ (differenceForcing U V i) z :=
    DifferentiableAt.fun_sum fun j _ => DifferentiableAt.fun_sum fun m _ => hp j m
  unfold firstForcing errorForcing
  rw [D_sub (f := fun y => -candidateResidual V i y) (g := differenceForcing U V i)
    (candidateResidual_differentiable V z hv i).neg hd e]
  have hn : D (fun y => -candidateResidual V i y) e z = -D (candidateResidual V i) e z := by
    have h : HasFDerivAt (fun y => -candidateResidual V i y)
        (-fderiv ℝ (candidateResidual V i) z) z :=
      (candidateResidual_differentiable V z hv i).hasFDerivAt.neg
    unfold D
    rw [h.fderiv]
    rfl
  rw [hn,differenceForcing_derivative U V z e hu hv i]

theorem actual_first_error_expanded (U V : Vector) (z : Joint) (k : Fin 3)
    (hu : ∀ i, ContDiffAt ℝ 2 (U i) z) (hv : ∀ i, ContDiffAt ℝ 2 (V i) z)
    (heq : ∀ i, candidateResidual U i =ᶠ[𝓝 z] (fun _ => 0)) (i : Fin 5) :
    EulerOrdered.residual (stateMatrix U) (fun m => D (difference U V m) (ex k)) i z =
      -D (candidateResidual V i) (ex k) z-differentiatedDifference U V (ex k) i z-
        principalCommutator U V (ex k) i z := by
  rw [actual_first_error_equation U V z k hu hv heq i,
    expanded_first_forcing U V z (ex k) (fun m => (hu m).differentiableAt (by norm_num)) hv i]

-- These are diagnostic polynomial fields; their true-state EulerOrdered.residual is retained, not set to zero.
def coord (z : Joint) : ℝ := z.2 0
def lift (f : ℝ → ℝ) : Joint → ℝ := fun z => f (coord z)
lemma coord_hasFDeriv (z : Joint) : HasFDerivAt coord
    ((ContinuousLinearMap.proj (0:Fin 3)).comp (ContinuousLinearMap.snd ℝ ℝ Space)) z :=
  (hasFDerivAt_apply (𝕜 := ℝ) (0:Fin 3) z.2).comp z hasFDerivAt_snd

lemma D_lift {f : ℝ → ℝ} {f' : ℝ} (z : Joint) (e : Joint)
    (hf : HasDerivAt f f' (coord z)) : D (lift f) e z = f'*e.2 0 := by
  have h : HasFDerivAt (lift f)
      ((ContinuousLinearMap.smulRight (1 : ℝ →L[ℝ] ℝ) f').comp
        ((ContinuousLinearMap.proj (0:Fin 3)).comp (ContinuousLinearMap.snd ℝ ℝ Space))) z :=
    hf.hasFDerivAt.comp z (coord_hasFDeriv z)
  unfold D
  rw [h.fderiv]
  simp
  exact mul_comm _ _

def polyU (i : Fin 5) (s : ℝ) : ℝ :=
  ![s+2,2*s,3*s,4*s,3*s+4] i
def polyV (i : Fin 5) (s : ℝ) : ℝ :=
  ![s^2+1,s^2,2*s^2,3*s^2,2*s^2+2] i
def controlU : Vector := fun i => lift (polyU i)
def controlV : Vector := fun i => lift (polyV i)
def controlPoint : Joint := (0,fun _ => 1)

lemma polyU_deriv (i : Fin 5) (s : ℝ) :
    HasDerivAt (polyU i) (![1,2,3,4,3] i) s := by
  fin_cases i
  · change HasDerivAt (fun t : ℝ => t+2) 1 s
    exact (hasDerivAt_id s).add_const 2
  · change HasDerivAt (fun t : ℝ => 2*t) 2 s
    simpa only [id,mul_one] using (hasDerivAt_id s).const_mul 2
  · change HasDerivAt (fun t : ℝ => 3*t) 3 s
    simpa only [id,mul_one] using (hasDerivAt_id s).const_mul 3
  · change HasDerivAt (fun t : ℝ => 4*t) 4 s
    simpa only [id,mul_one] using (hasDerivAt_id s).const_mul 4
  · change HasDerivAt (fun t : ℝ => 3*t+4) 3 s
    simpa only [id,mul_one] using ((hasDerivAt_id s).const_mul 3).add_const 4

lemma polyV_deriv (i : Fin 5) (s : ℝ) :
    HasDerivAt (polyV i) (![2*s,2*s,4*s,6*s,4*s] i) s := by
  have h : HasDerivAt (fun t : ℝ => t^2) (2*s) s := by
    convert (hasDerivAt_id s).pow 2 using 1
    norm_num [id]
  fin_cases i
  · change HasDerivAt (fun t : ℝ => t^2+1) (2*s) s
    exact h.add_const 1
  · change HasDerivAt (fun t : ℝ => t^2) (2*s) s
    exact h
  · change HasDerivAt (fun t : ℝ => 2*t^2) (4*s) s
    convert h.const_mul 2 using 1
    ring
  · change HasDerivAt (fun t : ℝ => 3*t^2) (6*s) s
    convert h.const_mul 3 using 1
    ring
  · change HasDerivAt (fun t : ℝ => 2*t^2+2) (4*s) s
    convert (h.const_mul 2).add_const 2 using 1
    ring

lemma D_controlU (i : Fin 5) (z : Joint) (e : Joint) :
    D (controlU i) e z = (![1,2,3,4,3] i)*e.2 0 := D_lift z e (polyU_deriv i _)
lemma D_controlV (i : Fin 5) (z : Joint) (e : Joint) :
    D (controlV i) e z = (![2*coord z,2*coord z,4*coord z,6*coord z,4*coord z] i)*e.2 0 :=
  D_lift z e (polyV_deriv i _)

lemma controlU_differentiable (i : Fin 5) (z : Joint) : DifferentiableAt ℝ (controlU i) z :=
  ((polyU_deriv i _).hasFDerivAt.comp z (coord_hasFDeriv z)).differentiableAt
lemma controlV_differentiable (i : Fin 5) (z : Joint) : DifferentiableAt ℝ (controlV i) z :=
  ((polyV_deriv i _).hasFDerivAt.comp z (coord_hasFDeriv z)).differentiableAt

lemma row_one (q p v : ℝ) (j : Fin 3) (Z : Fin 5 → ℝ) :
    (∑ m, coefficient q p v j 1 m*Z m) =
      v*Z 1+(if (0:Fin 3)=j then q*Z 4 else 0) :=
  row_b q p v j 0 Z

lemma sum_three (f : Fin 3 → ℝ) : (∑ j, f j) = f 0+f 1+f 2 := by
  simp [Fin.sum_univ_succ,add_assoc]

lemma vec_five_last (a b c d e : ℝ) : (![a,b,c,d,e] (4:Fin 5)) = e := rfl
lemma vec_four_cast_two (a b c d : ℝ) :
    (![a,b,c,d] (Fin.castSucc (2:Fin 3))) = c := rfl
lemma single_two_zero :
    (Pi.single (2 : Fin 3) (1 : ℝ) : Fin 3 → ℝ) (0 : Fin 3) = (0 : ℝ) := rfl
lemma zero_ne_two : (0:Fin 3) ≠ 2 := by decide

lemma control_residual_formula : candidateResidual controlV 1 = lift (fun s => 6*s^3+4*s) := by
  funext z
  unfold candidateResidual EulerOrdered.residual stateMatrix coefficients
  simp_rw [row_one,D_controlV]
  rw [sum_three]
  norm_num [controlV,lift,polyV,bi,et,ex,vec_five_last,vec_four_cast_two,single_two_zero,zero_ne_two]
  ring

lemma control_difference_formula : differenceForcing controlU controlV 1 =
    lift (fun s => 8*s^2+4*s-6*s^3) := by
  funext z
  unfold differenceForcing stateMatrix coefficients
  simp_rw [row_one,D_controlV]
  rw [sum_three]
  norm_num [difference,controlU,controlV,lift,polyU,polyV,bi,ex,
    vec_five_last,vec_four_cast_two,single_two_zero,zero_ne_two]
  ring

-- Full definitions determine every charged quantity; no independent jet values are supplied.
theorem full_definition_control :
    candidateResidual controlV 1 controlPoint = 10 ∧
    differenceForcing controlU controlV 1 controlPoint = 6 ∧
    errorForcing controlU controlV 1 controlPoint = -16 ∧
    EulerOrdered.residual (stateMatrix controlU) (difference controlU controlV) 1 controlPoint = -3 ∧
    candidateResidual controlU 1 controlPoint = 13 ∧
    D (candidateResidual controlV 1) (ex 0) controlPoint = 22 ∧
    D (differenceForcing controlU controlV 1) (ex 0) controlPoint = 2 ∧
    principalCommutator controlU controlV (ex 0) 1 controlPoint = -1 ∧
    firstForcing controlU controlV (ex 0) 1 controlPoint = -23 ∧
    ((-23:ℝ) ≠ -1 ∧ (-23:ℝ) ≠ -21 ∧ (-23:ℝ) ≠ -24 ∧
      (-23:ℝ) ≠ 21 ∧ (-23:ℝ) ≠ -19 ∧ (-23:ℝ) ≠ -25) := by
  have hr : D (candidateResidual controlV 1) (ex 0) controlPoint = 22 := by
    rw [control_residual_formula]
    have h := (((hasDerivAt_id (1:ℝ)).pow 3).const_mul 6).add
      ((hasDerivAt_id (1:ℝ)).const_mul 4)
    have hd := D_lift controlPoint (ex 0) h
    norm_num [coord,controlPoint,ex] at hd
    exact hd
  have hd : D (differenceForcing controlU controlV 1) (ex 0) controlPoint = 2 := by
    rw [control_difference_formula]
    have h := ((((hasDerivAt_id (1:ℝ)).pow 2).const_mul 8).add
      ((hasDerivAt_id (1:ℝ)).const_mul 4)).sub (((hasDerivAt_id (1:ℝ)).pow 3).const_mul 6)
    have he := D_lift controlPoint (ex 0) h
    norm_num [coord,controlPoint,ex] at he
    exact he
  have hp : principalCommutator controlU controlV (ex 0) 1 controlPoint = -1 := by
    unfold principalCommutator stateMatrix coefficients
    simp_rw [coefficient_derivative (controlU_differentiable 0 _)
      (controlU_differentiable 4 _) (controlU_differentiable _ _)]
    unfold difference
    simp_rw [D_sub (controlU_differentiable _ _) (controlV_differentiable _ _)]
    simp_rw [row_one,D_controlU,D_controlV]
    rw [sum_three]
    norm_num [bi,ex,controlPoint,coord,vec_five_last,vec_four_cast_two,single_two_zero,zero_ne_two]
  have hf : firstForcing controlU controlV (ex 0) 1 controlPoint = -23 := by
    unfold firstForcing errorForcing
    have he : (fun y => -candidateResidual controlV 1 y-differenceForcing controlU controlV 1 y) =
        lift (fun s => -(6*s^3+4*s)-(8*s^2+4*s-6*s^3)) := by
      rw [control_residual_formula,control_difference_formula]
      rfl
    rw [he,hp]
    have h := (((((hasDerivAt_id (1:ℝ)).pow 3).const_mul 6).add
      ((hasDerivAt_id (1:ℝ)).const_mul 4)).neg).sub
      (((((hasDerivAt_id (1:ℝ)).pow 2).const_mul 8).add
        ((hasDerivAt_id (1:ℝ)).const_mul 4)).sub (((hasDerivAt_id (1:ℝ)).pow 3).const_mul 6))
    have ht : HasDerivAt (fun s : ℝ => -(6*s^3+4*s)-(8*s^2+4*s-6*s^3)) (-24) 1 := by
      convert h using 1
      norm_num
    have he' : D (lift (fun s : ℝ => -(6*s^3+4*s)-(8*s^2+4*s-6*s^3)))
        (ex 0) controlPoint = -24 := by
      simpa only [ex,Pi.single_eq_same,mul_one] using D_lift controlPoint (ex 0) ht
    rw [he']
    norm_num
  refine ⟨?_,?_,?_,?_,?_,hr,hd,hp,hf,?_⟩
  · rw [control_residual_formula]
    norm_num [lift,coord,controlPoint]
  · rw [control_difference_formula]
    norm_num [lift,coord,controlPoint]
  · unfold errorForcing
    rw [control_residual_formula,control_difference_formula]
    norm_num [lift,coord,controlPoint]
  · rw [residual_sub _ _ _ _ (fun i => controlU_differentiable i _)
      (fun i => controlV_differentiable i _) 1]
    unfold EulerOrdered.residual stateMatrix coefficients
    simp_rw [row_one,D_controlU,D_controlV]
    rw [sum_three,sum_three]
    norm_num [controlU,controlV,lift,polyU,polyV,coord,controlPoint,bi,et,ex,
      vec_five_last,vec_four_cast_two,single_two_zero,zero_ne_two]
  · unfold candidateResidual EulerOrdered.residual stateMatrix coefficients
    simp_rw [row_one,D_controlU]
    rw [sum_three]
    norm_num [controlU,lift,polyU,coord,controlPoint,bi,et,ex,
      vec_five_last,vec_four_cast_two,single_two_zero,zero_ne_two]
  · norm_num

end EulerErrorField

namespace EulerErrorIntegral
open MeasureTheory Set Filter
open scoped BigOperators Topology
open EulerOrdered EulerErrorField

-- These are the actual true-state velocity and its actual diagonal derivatives.
def trueVelocity (U : Vector) : Fin 3 → Joint → ℝ := fun j => U (bi j)
def errorFields (U V : Vector) : EulerMetricEnergy.Fields :=
  fields (U 0) (U 4) (difference U V)
def firstError (U V : Vector) (k : Fin 3) : Vector :=
  fun i => D (difference U V i) (ex k)
def firstFields (U V : Vector) (k : Fin 3) : EulerMetricEnergy.Fields :=
  fields (U 0) (U 4) (firstError U V k)
def expandedForcing (U V : Vector) (k : Fin 3) : Vector := fun i z =>
  -D (candidateResidual V i) (ex k) z-differentiatedDifference U V (ex k) i z-
    principalCommutator U V (ex k) i z

theorem expanded_forcing_terms (U V : Vector) (k : Fin 3) (i : Fin 5) (z : Joint) :
    expandedForcing U V k i z = -D (candidateResidual V i) (ex k) z-
      (∑ j, ∑ m, (D (stateMatrix (difference U V) j i m) (ex k) z*D (V m) (ex j) z+
        stateMatrix (difference U V) j i m z*D (D (V m) (ex j)) (ex k) z))-
      (∑ j, ∑ m, D (stateMatrix U j i m) (ex k) z*D (difference U V m) (ex j) z) := rfl

theorem true_material_equations (U : Vector) (t : ℝ)
    (heq : ∀ x i, candidateResidual U i (t,x) = 0) :
    (∀ x, D (U 0) et (t,x)+(∑ j, trueVelocity U j (t,x)*D (U 0) (ex j) (t,x)) =
      U 0 (t,x)*EulerBalance.theta (diagonal (trueVelocity U) t) x) ∧
    (∀ x, D (U 4) et (t,x)+(∑ j, trueVelocity U j (t,x)*D (U 4) (ex j) (t,x)) =
      -2*U 4 (t,x)*EulerBalance.theta (diagonal (trueVelocity U) t) x) := by
  constructor
  · intro x
    have h := heq x 0
    simp only [candidateResidual,stateMatrix,EulerOrdered.residual,coefficients] at h
    simp_rw [row_a,Finset.sum_add_distrib] at h
    have hq : (∑ j, -U 0 (t,x)*D (U (bi j)) (ex j) (t,x)) =
        -U 0 (t,x)*EulerBalance.theta (diagonal (trueVelocity U) t) x := by
      rw [← Finset.mul_sum]
      rfl
    rw [hq] at h
    change D (U 0) et (t,x)+(∑ j, U (bi j) (t,x)*D (U 0) (ex j) (t,x)) =
      U 0 (t,x)*EulerBalance.theta (diagonal (trueVelocity U) t) x
    linarith
  · intro x
    have h := heq x 4
    simp only [candidateResidual,stateMatrix,EulerOrdered.residual,coefficients] at h
    simp_rw [row_c,Finset.sum_add_distrib] at h
    have hp : (∑ j, 2*U 4 (t,x)*D (U (bi j)) (ex j) (t,x)) =
        2*U 4 (t,x)*EulerBalance.theta (diagonal (trueVelocity U) t) x := by
      rw [← Finset.mul_sum]
      rfl
    rw [hp] at h
    change D (U 4) et (t,x)+(∑ j, U (bi j) (t,x)*D (U 4) (ex j) (t,x)) =
      -2*U 4 (t,x)*EulerBalance.theta (diagonal (trueVelocity U) t) x
    linarith

theorem error_euler_premises (U V : Vector) (t : ℝ)
    (hu : ∀ x i, DifferentiableAt ℝ (U i) (t,x))
    (hv : ∀ x i, DifferentiableAt ℝ (V i) (t,x))
    (heq : ∀ x i, candidateResidual U i (t,x) = 0)
    (hq : ∀ x, 0 < U 0 (t,x)) (hp : ∀ x, 0 < U 4 (t,x)) :
    EulerBalance.EulerPremises t (errorFields U V)
      (timeFields (U 0) (U 4) (difference U V))
      (spaceFields (U 0) (U 4) (difference U V))
      (velocity (trueVelocity U) t) (diagonal (trueVelocity U) t) (stateOf (errorForcing U V) t) := by
  have hm := true_material_equations U t heq
  exact equations_to_balance (U 0) (U 4) (trueVelocity U) (difference U V)
    (errorForcing U V) t hq hp hm.1 hm.2
    (fun x i => actual_error_equation U V (t,x) (hu x) (hv x) (heq x) i)

theorem first_error_euler_premises (U V : Vector) (t : ℝ) (k : Fin 3)
    (hu : ∀ x i, ContDiffAt ℝ 2 (U i) (t,x))
    (hv : ∀ x i, ContDiffAt ℝ 2 (V i) (t,x))
    (heq : ∀ x i, candidateResidual U i =ᶠ[𝓝 (t,x)] (fun _ => 0))
    (hq : ∀ x, 0 < U 0 (t,x)) (hp : ∀ x, 0 < U 4 (t,x)) :
    EulerBalance.EulerPremises t (firstFields U V k)
      (timeFields (U 0) (U 4) (firstError U V k))
      (spaceFields (U 0) (U 4) (firstError U V k))
      (velocity (trueVelocity U) t) (diagonal (trueVelocity U) t) (stateOf (expandedForcing U V k) t) := by
  have hm := true_material_equations U t (fun x i => (heq x i).eq_of_nhds)
  exact equations_to_balance (U 0) (U 4) (trueVelocity U) (firstError U V k)
    (expandedForcing U V k) t hq hp hm.1 hm.2
    (fun x i => actual_first_error_expanded U V (t,x) k (hu x) (hv x) (heq x) i)

-- Every analytic integral premise is fresh for this actual error, with U as metric state.
theorem error_energy_balance (L t eps : ℝ) (hL : 0 < L) (U V : Vector) (bound : Space → ℝ)
    (hu : ∀ x i, DifferentiableAt ℝ (U i) (t,x))
    (hv : ∀ x i, DifferentiableAt ℝ (V i) (t,x))
    (heq : ∀ x i, candidateResidual U i (t,x) = 0)
    (hq : ∀ x, 0 < U 0 (t,x)) (hp : ∀ x, 0 < U 4 (t,x))
    (ht : EulerBalance.TimePremises L t eps (errorFields U V)
      (timeFields (U 0) (U 4) (difference U V)) bound)
    (hs : EulerBalance.SpatialPremises L t (errorFields U V)
      (spaceFields (U 0) (U 4) (difference U V))
      (velocity (trueVelocity U) t) (diagonal (trueVelocity U) t)) :
    Integrable (EulerBalance.forcingDensity (errorFields U V) t
      (diagonal (trueVelocity U) t) (stateOf (errorForcing U V) t)) (EulerPeriodicBox.cubeMeasure L) ∧
    HasDerivAt (fun s => EulerPeriodicBox.cubeAverage L (EulerMetricEnergy.density (errorFields U V) s))
      (EulerPeriodicBox.cubeAverage L (EulerBalance.forcingDensity (errorFields U V) t
        (diagonal (trueVelocity U) t) (stateOf (errorForcing U V) t))) t :=
  EulerBalance.normalized_energy_balance L t eps hL _ _ _ bound _ _ _ ht hs
    (error_euler_premises U V t hu hv heq hq hp)

-- Rank-one domination, actual time/slice jets, integrability and seams are separate inputs.
theorem first_error_energy_balance (L t eps : ℝ) (hL : 0 < L) (U V : Vector) (k : Fin 3)
    (bound : Space → ℝ)
    (hu : ∀ x i, ContDiffAt ℝ 2 (U i) (t,x))
    (hv : ∀ x i, ContDiffAt ℝ 2 (V i) (t,x))
    (heq : ∀ x i, candidateResidual U i =ᶠ[𝓝 (t,x)] (fun _ => 0))
    (hq : ∀ x, 0 < U 0 (t,x)) (hp : ∀ x, 0 < U 4 (t,x))
    (ht : EulerBalance.TimePremises L t eps (firstFields U V k)
      (timeFields (U 0) (U 4) (firstError U V k)) bound)
    (hs : EulerBalance.SpatialPremises L t (firstFields U V k)
      (spaceFields (U 0) (U 4) (firstError U V k))
      (velocity (trueVelocity U) t) (diagonal (trueVelocity U) t)) :
    Integrable (EulerBalance.forcingDensity (firstFields U V k) t
      (diagonal (trueVelocity U) t) (stateOf (expandedForcing U V k) t)) (EulerPeriodicBox.cubeMeasure L) ∧
    HasDerivAt (fun s => EulerPeriodicBox.cubeAverage L (EulerMetricEnergy.density (firstFields U V k) s))
      (EulerPeriodicBox.cubeAverage L (EulerBalance.forcingDensity (firstFields U V k) t
        (diagonal (trueVelocity U) t) (stateOf (expandedForcing U V k) t))) t :=
  EulerBalance.normalized_energy_balance L t eps hL _ _ _ bound _ _ _ ht hs
    (first_error_euler_premises U V t k hu hv heq hq hp)

theorem physical_error_energy_balance (t eps : ℝ) (U V : Vector) (bound : Space → ℝ)
    (hu : ∀ x i, DifferentiableAt ℝ (U i) (t,x))
    (hv : ∀ x i, DifferentiableAt ℝ (V i) (t,x))
    (heq : ∀ x i, candidateResidual U i (t,x) = 0)
    (hq : ∀ x, 0 < U 0 (t,x)) (hp : ∀ x, 0 < U 4 (t,x))
    (ht : EulerBalance.TimePremises (2*Real.pi) t eps (errorFields U V)
      (timeFields (U 0) (U 4) (difference U V)) bound)
    (hs : EulerBalance.SpatialPremises (2*Real.pi) t (errorFields U V)
      (spaceFields (U 0) (U 4) (difference U V))
      (velocity (trueVelocity U) t) (diagonal (trueVelocity U) t)) :
    HasDerivAt (fun s => EulerPeriodicBox.cubeAverage (2*Real.pi)
      (EulerMetricEnergy.density (errorFields U V) s))
      (EulerPeriodicBox.cubeAverage (2*Real.pi) (EulerBalance.forcingDensity (errorFields U V) t
        (diagonal (trueVelocity U) t) (stateOf (errorForcing U V) t))) t :=
  (error_energy_balance (2*Real.pi) t eps (mul_pos (by norm_num) Real.pi_pos)
    U V bound hu hv heq hq hp ht hs).2

theorem physical_first_error_energy_balance (t eps : ℝ) (U V : Vector) (k : Fin 3)
    (bound : Space → ℝ)
    (hu : ∀ x i, ContDiffAt ℝ 2 (U i) (t,x))
    (hv : ∀ x i, ContDiffAt ℝ 2 (V i) (t,x))
    (heq : ∀ x i, candidateResidual U i =ᶠ[𝓝 (t,x)] (fun _ => 0))
    (hq : ∀ x, 0 < U 0 (t,x)) (hp : ∀ x, 0 < U 4 (t,x))
    (ht : EulerBalance.TimePremises (2*Real.pi) t eps (firstFields U V k)
      (timeFields (U 0) (U 4) (firstError U V k)) bound)
    (hs : EulerBalance.SpatialPremises (2*Real.pi) t (firstFields U V k)
      (spaceFields (U 0) (U 4) (firstError U V k))
      (velocity (trueVelocity U) t) (diagonal (trueVelocity U) t)) :
    HasDerivAt (fun s => EulerPeriodicBox.cubeAverage (2*Real.pi)
      (EulerMetricEnergy.density (firstFields U V k) s))
      (EulerPeriodicBox.cubeAverage (2*Real.pi) (EulerBalance.forcingDensity (firstFields U V k) t
        (diagonal (trueVelocity U) t) (stateOf (expandedForcing U V k) t))) t :=
  (first_error_energy_balance (2*Real.pi) t eps (mul_pos (by norm_num) Real.pi_pos)
    U V k bound hu hv heq hq hp ht hs).2

end EulerErrorIntegral

namespace EulerRegularPremises
open MeasureTheory Set Filter Metric
open scoped BigOperators Topology ContDiff
open EulerOrdered EulerErrorField EulerErrorIntegral

-- A sufficient extension setting: global smoothness/periodicity, local-in-time positive margins.
def Periodic (L : ℝ) (f : Joint → ℝ) : Prop :=
  ∀ (d : Fin 3) (z : Joint), f (z+L • ex d) = f z
def jets (q p : Joint → ℝ) (W : Vector) (e : Joint) : EulerMetricEnergy.Fields :=
  fields (D q e) (D p e) (fun i => D (W i) e)

lemma D_continuous {f : Joint → ℝ} (h : ContDiff ℝ 1 f) (e : Joint) : Continuous (D f e) :=
  (h.fderiv_right (m := 0) (by norm_num)).continuous.clm_apply continuous_const

lemma D_contDiff {f : Joint → ℝ} (h : ContDiff ℝ 2 f) (e : Joint) : ContDiff ℝ 1 (D f e) :=
  (h.fderiv_right (m := 1) (by norm_num)).clm_apply contDiff_const

theorem periodic_derivative (L : ℝ) (f : Joint → ℝ) (hf : Differentiable ℝ f)
    (hper : Periodic L f) (e : Joint) : Periodic L (D f e) := by
  intro d z
  have hc : HasFDerivAt (fun y : Joint => f (y+L • ex d))
      (fderiv ℝ f (z+L • ex d)) z := by
    simpa only [ContinuousLinearMap.comp_id] using
      (hf (z+L • ex d)).hasFDerivAt.comp z ((hasFDerivAt_id z).add_const (L • ex d))
  have he : (fun y : Joint => f (y+L • ex d)) = f := funext (hper d)
  rw [he] at hc
  exact congrArg (fun c : Joint →L[ℝ] ℝ => c e) hc.fderiv.symm

lemma periodic_sub (L : ℝ) (f g : Joint → ℝ) (hf : Periodic L f) (hg : Periodic L g) :
    Periodic L (fun z => f z-g z) := by
  intro d z
  change f (z+L • ex d)-g (z+L • ex d) = f z-g z
  rw [hf d z,hg d z]

lemma insert_affine (d : Fin 3) (y : EulerPeriodicBox.Transverse) (s : ℝ) :
    (d.insertNth s y : Space) = d.insertNth 0 y+s • (Pi.single d (1:ℝ) : Space) := by
  apply funext
  refine (Fin.forall_iff_succAbove (P := fun j =>
    (d.insertNth s y : Space) j = (d.insertNth 0 y+s • (Pi.single d (1:ℝ) : Space) : Space) j) d).mpr ⟨?_,?_⟩
  · simp
  · intro j
    simp [Fin.succAbove_ne]

lemma joint_line (t : ℝ) (d : Fin 3) (y : EulerPeriodicBox.Transverse) (s : ℝ) :
    (t,d.insertNth s y) = (t,d.insertNth 0 y)+s • ex d := by
  apply Prod.ext
  · simp [ex]
  · exact insert_affine d y s

lemma line_continuous (t : ℝ) (d : Fin 3) (y : EulerPeriodicBox.Transverse) :
    Continuous (fun s : ℝ => ((t,d.insertNth s y) : Joint)) := by
  have h : Continuous (fun s : ℝ => (t,d.insertNth 0 y)+s • ex d) :=
    continuous_const.add (continuous_id.smul continuous_const)
  convert h using 1
  funext s
  exact joint_line t d y s

lemma time_deriv {f : Joint → ℝ} (hf : Differentiable ℝ f) (t : ℝ) (x : Space) :
    HasDerivAt (fun s => f (s,x)) (D f et (t,x)) t := by
  have hc : HasDerivAt (fun s : ℝ => (s,x)) et t := by
    simpa [et] using (hasDerivAt_id t).prodMk (hasDerivAt_const t x)
  exact (hf (t,x)).hasFDerivAt.comp_hasDerivAt t hc

lemma slice_deriv {f : Joint → ℝ} (hf : Differentiable ℝ f) (t : ℝ)
    (d : Fin 3) (y : EulerPeriodicBox.Transverse) (s : ℝ) :
    HasDerivAt (fun a => f (t,d.insertNth a y)) (D f (ex d) (t,d.insertNth s y)) s := by
  have hc : HasDerivAt (fun a : ℝ => (t,d.insertNth a y)) (ex d) s := by
    have he : (fun a : ℝ => (t,d.insertNth a y)) =
        fun a => (t,d.insertNth 0 y)+a • ex d := funext (joint_line t d y)
    rw [he]
    simpa using ((hasDerivAt_id s).smul_const (ex d)).const_add (t,d.insertNth 0 y)
  exact (hf _).hasFDerivAt.comp_hasDerivAt s hc

theorem all_slice_seam (L : ℝ) (f : Joint → ℝ) (hper : Periodic L f)
    (t : ℝ) (d : Fin 3) (y : EulerPeriodicBox.Transverse) :
    f (t,d.insertNth 0 y) = f (t,d.insertNth L y) := by
  rw [joint_line t d y L]
  exact (hper d (t,d.insertNth 0 y)).symm

lemma density_continuousAt (q p : Joint → ℝ) (W : Vector)
    (hq : Continuous q) (hp : Continuous p) (hw : ∀ i, Continuous (W i))
    (z : Joint) (hqn : q z ≠ 0) (hpn : p z ≠ 0) :
    ContinuousAt (fun y : Joint => EulerMetricEnergy.density (fields q p W) y.1 y.2) z := by
  simp only [EulerMetricEnergy.density,fields,Prod.eta]
  fun_prop (disch := aesop)

lemma rate_continuousAt (q p : Joint → ℝ) (W : Vector) (e : Joint)
    (hq : ContDiff ℝ 1 q) (hp : ContDiff ℝ 1 p) (hw : ∀ i, ContDiff ℝ 1 (W i))
    (z : Joint) (hqn : q z ≠ 0) (hpn : p z ≠ 0) :
    ContinuousAt (fun y : Joint => EulerMetricEnergy.rate (fields q p W) (jets q p W e) y.1 y.2) z := by
  have cq := hq.continuous
  have cp := hp.continuous
  have cw : ∀ i, Continuous (W i) := fun i => (hw i).continuous
  have dq := D_continuous hq e
  have dp := D_continuous hp e
  have dw : ∀ i, Continuous (D (W i) e) := fun i => D_continuous (hw i) e
  simp only [EulerMetricEnergy.rate,fields,jets,Prod.eta]
  fun_prop (disch := aesop)

lemma density_continuous_slice (q p : Joint → ℝ) (W : Vector)
    (hq : Continuous q) (hp : Continuous p) (hw : ∀ i, Continuous (W i)) (t : ℝ)
    (hqn : ∀ x, q (t,x) ≠ 0) (hpn : ∀ x, p (t,x) ≠ 0) :
    Continuous (EulerMetricEnergy.density (fields q p W) t) := by
  apply continuous_iff_continuousAt.mpr
  intro x
  exact (density_continuousAt q p W hq hp hw (t,x) (hqn x) (hpn x)).comp
    (continuous_const.prodMk continuous_id).continuousAt

lemma rate_continuous_slice (q p : Joint → ℝ) (W : Vector) (e : Joint)
    (hq : ContDiff ℝ 1 q) (hp : ContDiff ℝ 1 p) (hw : ∀ i, ContDiff ℝ 1 (W i)) (t : ℝ)
    (hqn : ∀ x, q (t,x) ≠ 0) (hpn : ∀ x, p (t,x) ≠ 0) :
    Continuous (EulerMetricEnergy.rate (fields q p W) (jets q p W e) t) := by
  apply continuous_iff_continuousAt.mpr
  intro x
  exact (rate_continuousAt q p W e hq hp hw (t,x) (hqn x) (hpn x)).comp
    (continuous_const.prodMk continuous_id).continuousAt

lemma cube_integrable (L : ℝ) (f : Space → ℝ) (hf : Continuous f) :
    Integrable f (EulerPeriodicBox.cubeMeasure L) :=
  (hf.continuousOn.integrableOn_compact isCompact_Icc).smul_measure ENNReal.ofReal_ne_top

theorem common_time_premises (L t r : ℝ) (hr : 0 < r) (q p : Joint → ℝ) (W : Vector)
    (hq : ContDiff ℝ 1 q) (hp : ContDiff ℝ 1 p) (hw : ∀ i, ContDiff ℝ 1 (W i))
    (hqp : ∀ s ∈ Icc (t-r) (t+r), ∀ x, 0 < q (s,x))
    (hpp : ∀ s ∈ Icc (t-r) (t+r), ∀ x, 0 < p (s,x)) :
    ∃ B : ℝ, EulerBalance.TimePremises L t r (fields q p W) (timeFields q p W) (fun _ => B) := by
  let K : Set Joint := Icc (t-r) (t+r) ×ˢ EulerPeriodicBox.cube L
  have hK : IsCompact K := isCompact_Icc.prod isCompact_Icc
  have hc : ContinuousOn (fun z : Joint => ‖EulerMetricEnergy.rate
      (fields q p W) (jets q p W et) z.1 z.2‖) K := by
    intro z hz
    exact ((rate_continuousAt q p W et hq hp hw z
      (ne_of_gt (hqp z.1 hz.1 z.2)) (ne_of_gt (hpp z.1 hz.1 z.2))).norm).continuousWithinAt
  obtain ⟨B,hB⟩ := hK.bddAbove_image hc
  have ht : t ∈ Icc (t-r) (t+r) := ⟨by linarith,by linarith⟩
  have hball : ∀ s ∈ ball t r, s ∈ Icc (t-r) (t+r) := by
    intro s hs
    rw [mem_ball,Real.dist_eq,abs_lt] at hs
    constructor <;> linarith
  have hd : ∀ s ∈ Icc (t-r) (t+r), Continuous (EulerMetricEnergy.density (fields q p W) s) :=
    fun s hs => density_continuous_slice q p W hq.continuous hp.continuous
      (fun i => (hw i).continuous) s (fun x => ne_of_gt (hqp s hs x)) (fun x => ne_of_gt (hpp s hs x))
  have hrate := rate_continuous_slice q p W et hq hp hw t
    (fun x => ne_of_gt (hqp t ht x)) (fun x => ne_of_gt (hpp t ht x))
  refine ⟨B,⟨hr,?_,cube_integrable L _ (hd t ht),hrate.aestronglyMeasurable,?_,
    cube_integrable L _ continuous_const,?_⟩⟩
  · filter_upwards [Metric.ball_mem_nhds t hr] with s hs
    exact (hd s (hball s hs)).aestronglyMeasurable
  · have hae : ∀ᵐ x ∂EulerPeriodicBox.cubeMeasure L, x ∈ EulerPeriodicBox.cube L :=
      Measure.ae_smul_measure (ae_restrict_mem measurableSet_Icc) _
    filter_upwards [hae] with x hx
    intro s hs
    exact hB ⟨(s,x),⟨hball s hs,hx⟩,rfl⟩
  · exact Filter.Eventually.of_forall fun x s hs =>
      ⟨hqp s (hball s hs) x,hpp s (hball s hs) x,
        time_deriv (hq.differentiable (by norm_num)) s x,
        time_deriv (hp.differentiable (by norm_num)) s x,
        time_deriv ((hw 0).differentiable (by norm_num)) s x,
        fun i => time_deriv ((hw (bi i)).differentiable (by norm_num)) s x,
        time_deriv ((hw 4).differentiable (by norm_num)) s x⟩

theorem all_spatial_premises (L t : ℝ) (q p : Joint → ℝ) (W : Vector)
    (v : Fin 3 → Joint → ℝ)
    (hq : ContDiff ℝ 1 q) (hp : ContDiff ℝ 1 p) (hw : ∀ i, ContDiff ℝ 1 (W i))
    (hv : ∀ i, ContDiff ℝ 1 (v i))
    (hqp : ∀ x, 0 < q (t,x)) (hpp : ∀ x, 0 < p (t,x))
    (pq : Periodic L q) (pp : Periodic L p) (pw : ∀ i, Periodic L (W i))
    (pv : ∀ i, Periodic L (v i)) :
    EulerBalance.SpatialPremises L t (fields q p W) (spaceFields q p W)
      (velocity v t) (diagonal v t) := by
  have hd := density_continuous_slice q p W hq.continuous hp.continuous
    (fun i => (hw i).continuous) t (fun x => ne_of_gt (hqp x)) (fun x => ne_of_gt (hpp x))
  have hr : ∀ d, Continuous (EulerMetricEnergy.rate (fields q p W) (spaceFields q p W d) t) :=
    fun d => rate_continuous_slice q p W (ex d) hq hp hw t
      (fun x => ne_of_gt (hqp x)) (fun x => ne_of_gt (hpp x))
  have cv : ∀ d, Continuous (velocity v t d) := fun d =>
    (hv d).continuous.comp (continuous_const.prodMk continuous_id)
  have cdv : ∀ d, Continuous (diagonal v t d) := fun d =>
    (D_continuous (hv d) (ex d)).comp (continuous_const.prodMk continuous_id)
  have cw : ∀ i, Continuous (fun x : Space => W i (t,x)) := fun i =>
    (hw i).continuous.comp (continuous_const.prodMk continuous_id)
  have cdw : ∀ d i, Continuous (fun x : Space => D (W i) (ex d) (t,x)) := fun d i =>
    (D_continuous (hw i) (ex d)).comp (continuous_const.prodMk continuous_id)
  refine ⟨?_,?_,?_,?_,?_,?_,?_,?_,?_,?_,?_,?_,?_,?_,?_,?_,?_,?_⟩
  · intro d y s _
    exact ⟨hqp _,hpp _,slice_deriv (hq.differentiable (by norm_num)) t d y s,
      slice_deriv (hp.differentiable (by norm_num)) t d y s,
      slice_deriv ((hw 0).differentiable (by norm_num)) t d y s,
      fun i => slice_deriv ((hw (bi i)).differentiable (by norm_num)) t d y s,
      slice_deriv ((hw 4).differentiable (by norm_num)) t d y s⟩
  · intro d y
    exact ((hv d).continuous.comp (line_continuous t d y)).continuousOn
  · intro d y
    exact (hd.comp (continuous_snd.comp (line_continuous t d y))).continuousOn
  · intro d y s _
    exact slice_deriv ((hv d).differentiable (by norm_num)) t d y s
  · intro d y
    exact ((D_continuous (hv d) (ex d)).comp (line_continuous t d y)).intervalIntegrable 0 L
  · intro d y
    exact ((hr d).comp (continuous_snd.comp (line_continuous t d y))).intervalIntegrable 0 L
  · intro d y
    exact all_slice_seam L _ (pv d) t d y
  · intro d y
    have hb : (∑ i : Fin 3, (W (bi i) (t,d.insertNth 0 y))^2) =
        ∑ i : Fin 3, (W (bi i) (t,d.insertNth L y))^2 := by
      apply Finset.sum_congr rfl
      intro i _
      rw [all_slice_seam L (W (bi i)) (pw (bi i)) t d y]
    simp only [EulerMetricEnergy.density,fields]
    rw [all_slice_seam L q pq t d y,all_slice_seam L p pp t d y,
      all_slice_seam L (W 0) (pw 0) t d y,all_slice_seam L (W 4) (pw 4) t d y,hb]
  · intro d y
    exact ((hw 4).continuous.comp (line_continuous t d y)).continuousOn
  · intro d y
    exact ((hw (bi d)).continuous.comp (line_continuous t d y)).continuousOn
  · intro d y
    exact ((D_continuous (hw 4) (ex d)).comp (line_continuous t d y)).intervalIntegrable 0 L
  · intro d y
    exact ((D_continuous (hw (bi d)) (ex d)).comp (line_continuous t d y)).intervalIntegrable 0 L
  · intro d y
    exact all_slice_seam L _ (pw 4) t d y
  · intro d y
    exact all_slice_seam L _ (pw (bi d)) t d y
  · intro d
    exact ((cv d).mul (hr d)).continuousOn.integrableOn_compact isCompact_Icc
  · intro d
    exact ((cdv d).mul hd).continuousOn.integrableOn_compact isCompact_Icc
  · intro d
    exact ((cdw d 4).mul (cw (bi d))).continuousOn.integrableOn_compact isCompact_Icc
  · intro d
    exact ((cw 4).mul (cdw d (bi d))).continuousOn.integrableOn_compact isCompact_Icc

-- These wrappers derive separate analytic premises, not an energy estimate or an Euler solution.
theorem error_regular_premises (L t r qmin pmin : ℝ) (hr : 0 < r)
    (hqm : 0 < qmin) (hpm : 0 < pmin) (U V : Vector)
    (hu : ∀ i, ContDiff ℝ 2 (U i)) (hv : ∀ i, ContDiff ℝ 2 (V i))
    (hqp : ∀ s ∈ Icc (t-r) (t+r), ∀ x, qmin ≤ U 0 (s,x))
    (hpp : ∀ s ∈ Icc (t-r) (t+r), ∀ x, pmin ≤ U 4 (s,x))
    (pu : ∀ i, Periodic L (U i)) (pv : ∀ i, Periodic L (V i)) :
    ∃ B : ℝ, EulerBalance.TimePremises L t r (errorFields U V)
      (timeFields (U 0) (U 4) (difference U V)) (fun _ => B) ∧
      EulerBalance.SpatialPremises L t (errorFields U V)
        (spaceFields (U 0) (U 4) (difference U V))
        (velocity (trueVelocity U) t) (diagonal (trueVelocity U) t) := by
  have hq : ContDiff ℝ 1 (U 0) := (hu 0).of_le (by norm_num)
  have hp : ContDiff ℝ 1 (U 4) := (hu 4).of_le (by norm_num)
  have hw : ∀ i, ContDiff ℝ 1 (difference U V i) :=
    fun i => ((hu i).sub (hv i)).of_le (by norm_num)
  have hqs : ∀ s ∈ Icc (t-r) (t+r), ∀ x, 0 < U 0 (s,x) :=
    fun s hs x => lt_of_lt_of_le hqm (hqp s hs x)
  have hps : ∀ s ∈ Icc (t-r) (t+r), ∀ x, 0 < U 4 (s,x) :=
    fun s hs x => lt_of_lt_of_le hpm (hpp s hs x)
  obtain ⟨B,hB⟩ := common_time_premises L t r hr (U 0) (U 4) (difference U V) hq hp hw hqs hps
  have ht : t ∈ Icc (t-r) (t+r) := ⟨by linarith,by linarith⟩
  exact ⟨B,hB,all_spatial_premises L t (U 0) (U 4) (difference U V) (trueVelocity U)
    hq hp hw (fun i => (hu (bi i)).of_le (by norm_num)) (hqs t ht) (hps t ht)
    (pu 0) (pu 4) (fun i => periodic_sub L _ _ (pu i) (pv i)) (fun i => pu (bi i))⟩

theorem first_error_regular_premises (L t r qmin pmin : ℝ) (hr : 0 < r)
    (hqm : 0 < qmin) (hpm : 0 < pmin) (U V : Vector) (k : Fin 3)
    (hu : ∀ i, ContDiff ℝ 2 (U i)) (hv : ∀ i, ContDiff ℝ 2 (V i))
    (hqp : ∀ s ∈ Icc (t-r) (t+r), ∀ x, qmin ≤ U 0 (s,x))
    (hpp : ∀ s ∈ Icc (t-r) (t+r), ∀ x, pmin ≤ U 4 (s,x))
    (pu : ∀ i, Periodic L (U i)) (pv : ∀ i, Periodic L (V i)) :
    ∃ B : ℝ, EulerBalance.TimePremises L t r (firstFields U V k)
      (timeFields (U 0) (U 4) (firstError U V k)) (fun _ => B) ∧
      EulerBalance.SpatialPremises L t (firstFields U V k)
        (spaceFields (U 0) (U 4) (firstError U V k))
        (velocity (trueVelocity U) t) (diagonal (trueVelocity U) t) := by
  have hq : ContDiff ℝ 1 (U 0) := (hu 0).of_le (by norm_num)
  have hp : ContDiff ℝ 1 (U 4) := (hu 4).of_le (by norm_num)
  have hw2 : ∀ i, ContDiff ℝ 2 (difference U V i) := fun i => (hu i).sub (hv i)
  have hw : ∀ i, ContDiff ℝ 1 (firstError U V k i) := fun i => D_contDiff (hw2 i) (ex k)
  have hqs : ∀ s ∈ Icc (t-r) (t+r), ∀ x, 0 < U 0 (s,x) :=
    fun s hs x => lt_of_lt_of_le hqm (hqp s hs x)
  have hps : ∀ s ∈ Icc (t-r) (t+r), ∀ x, 0 < U 4 (s,x) :=
    fun s hs x => lt_of_lt_of_le hpm (hpp s hs x)
  have pw : ∀ i, Periodic L (firstError U V k i) := fun i =>
    periodic_derivative L _ ((hw2 i).differentiable (by norm_num))
      (periodic_sub L _ _ (pu i) (pv i)) (ex k)
  obtain ⟨B,hB⟩ := common_time_premises L t r hr (U 0) (U 4) (firstError U V k) hq hp hw hqs hps
  have ht : t ∈ Icc (t-r) (t+r) := ⟨by linarith,by linarith⟩
  exact ⟨B,hB,all_spatial_premises L t (U 0) (U 4) (firstError U V k) (trueVelocity U)
    hq hp hw (fun i => (hu (bi i)).of_le (by norm_num)) (hqs t ht) (hps t ht)
    (pu 0) (pu 4) pw (fun i => pu (bi i))⟩

end EulerRegularPremises

namespace EulerTimeEnergy
open MeasureTheory Set
open scoped BigOperators Topology Interval
open EulerOrdered EulerErrorField EulerErrorIntegral EulerRegularPremises
abbrev Vec := Fin 5 → ℝ
abbrev Mat := Fin 5 → Fin 5 → ℝ
def S (w : Vec) : ℝ := ∑ i, (w i)^2
def Q (g : Mat) (w f : Vec) : ℝ := ∑ i, ∑ m, g i m*w i*f m
def ts (w : Vec) : EulerTransport.TestState := ⟨w 0,fun j => w (bi j),w 4⟩
def gm (q p : ℝ) : Mat :=
  ![![q⁻¹^2,0,0,0,q⁻¹*(2*p)⁻¹],
    ![0,q⁻¹,0,0,0],![0,0,q⁻¹,0,0],![0,0,0,q⁻¹,0],
    ![q⁻¹*(2*p)⁻¹,0,0,0,(2*p)⁻¹^2+(2*p)⁻¹] ]
def pm (q p : ℝ) : Mat :=
  ![![-q⁻¹^2,0,0,0,2*q⁻¹*(2*p)⁻¹],
    ![0,0,0,0,0],![0,0,0,0,0],![0,0,0,0,0],
    ![2*q⁻¹*(2*p)⁻¹,0,0,0,5*(2*p)⁻¹^2+3*(2*p)⁻¹] ]

lemma five_last {α : Type*} (a b c d e : α) : (![a,b,c,d,e] (4:Fin 5)) = e := rfl

theorem metric_matrix (q p : ℝ) (w f : Vec) :
    EulerTransport.metric q p (ts w) (ts f) = Q (gm q p) w f := by
  simp [EulerTransport.metric,ts,Q,gm,bi,Fin.sum_univ_succ,div_eq_mul_inv]
  ring

theorem potential_matrix (q p : ℝ) (w : Vec) :
    EulerTransport.potential q p (ts w) = Q (pm q p) w w := by
  simp [EulerTransport.potential,ts,Q,pm,bi,Fin.sum_univ_succ,div_eq_mul_inv,mul_inv_rev]
  ring

lemma sum_sq {n : ℕ} (f : Fin n → ℝ) : (∑ i, f i)^2 ≤ n*∑ i, (f i)^2 := by
  simpa using Finset.sum_mul_sq_le_sq_mul_sq Finset.univ (fun _ : Fin n => (1:ℝ)) f

lemma pair_bound (g : Mat) (w f : Vec) (G : ℝ) (hG : 0 ≤ G)
    (hg : ∀ i m, |g i m| ≤ G) :
    2*|Q g w f| ≤ 5*G*(S w+S f) := by
  have ht : ∀ i m, 2*|g i m*w i*f m| ≤ G*((w i)^2+(f m)^2) := by
    intro i m
    rw [abs_mul,abs_mul]
    have ha := mul_le_mul_of_nonneg_right (hg i m) (mul_nonneg (abs_nonneg (w i)) (abs_nonneg (f m)))
    have hb := sq_nonneg (|w i|-|f m|)
    rw [sub_sq,sq_abs,sq_abs] at hb
    have hc := mul_nonneg hG hb
    nlinarith
  have hsum : 2*|Q g w f| ≤ ∑ i, ∑ m, G*((w i)^2+(f m)^2) := by
    calc
      2*|Q g w f| ≤ 2*∑ i, |∑ m, g i m*w i*f m| :=
        mul_le_mul_of_nonneg_left (Finset.abs_sum_le_sum_abs _ _) (by norm_num)
      _ ≤ 2*∑ i, ∑ m, |g i m*w i*f m| := by
        gcongr with i
        exact Finset.abs_sum_le_sum_abs _ _
      _ = ∑ i, ∑ m, 2*|g i m*w i*f m| := by simp_rw [Finset.mul_sum]
      _ ≤ _ := Finset.sum_le_sum fun i _ => Finset.sum_le_sum fun m _ => ht i m
  have he : (∑ i : Fin 5, ∑ m : Fin 5, G*((w i)^2+(f m)^2)) = 5*G*(S w+S f) := by
    simp only [mul_add,Finset.sum_add_distrib,Finset.sum_const,Finset.card_univ,
      Fintype.card_fin,nsmul_eq_mul,S]
    simp_rw [← Finset.mul_sum]
    ring
  rwa [he] at hsum

lemma quadratic_bound (g : Mat) (w : Vec) (G : ℝ) (hG : 0 ≤ G)
    (hg : ∀ i m, |g i m| ≤ G) : |Q g w w| ≤ 5*G*S w := by
  have h := pair_bound g w w G hG hg
  linarith

-- Entry and coercivity bounds are explicit quantitative algebraic hypotheses.
structure Envelope (U V : Vector) (z : Joint) (K G P A M H R : ℝ) : Prop where
  K_nonneg : 0 ≤ K
  G_nonneg : 0 ≤ G
  P_nonneg : 0 ≤ P
  H_nonneg : 0 ≤ H
  metric_entries : ∀ i m, |gm (U 0 z) (U 4 z) i m| ≤ G
  potential_entries : ∀ i m, |pm (U 0 z) (U 4 z) i m| ≤ P
  coercivity : ∀ w : Vec, S w ≤ K*Q (gm (U 0 z) (U 4 z)) w w
  coefficient_difference : ∀ j i m,
    (stateMatrix (difference U V) j i m z)^2 ≤ A^2*S (fun i => difference U V i z)
  candidate_gradient : ∀ j m, (D (V m) (ex j) z)^2 ≤ M^2
  divergence : |EulerBalance.theta (diagonal (trueVelocity U) z.1) z.2| ≤ H
  residual : S (fun i => candidateResidual V i z) ≤ R

def growth (K G P A M H : ℝ) : ℝ :=
  (5*H*P+5*G*(1+2250*A^2*M^2))*K

theorem difference_forcing_bound (U V : Vector) (z : Joint) (A M : ℝ)
    (ha : ∀ j i m, (stateMatrix (difference U V) j i m z)^2 ≤
      A^2*S (fun i => difference U V i z))
    (hm : ∀ j m, (D (V m) (ex j) z)^2 ≤ M^2) :
    S (fun i => differenceForcing U V i z) ≤
      1125*A^2*M^2*S (fun i => difference U V i z) := by
  let w : Vec := fun i => difference U V i z
  have hs : 0 ≤ S w := Finset.sum_nonneg fun i _ => sq_nonneg _
  have ht : ∀ j i m, (stateMatrix (difference U V) j i m z*D (V m) (ex j) z)^2 ≤ A^2*M^2*S w := by
    intro j i m
    rw [mul_pow]
    calc
      _ ≤ (A^2*S w)*M^2 := mul_le_mul (ha j i m) (hm j m) (sq_nonneg _) (mul_nonneg (sq_nonneg _) hs)
      _ = _ := by ring
  have hi : ∀ i, (differenceForcing U V i z)^2 ≤ 225*A^2*M^2*S w := by
    intro i
    have inner : ∀ j, (∑ m, stateMatrix (difference U V) j i m z*D (V m) (ex j) z)^2 ≤ 25*A^2*M^2*S w := by
      intro j
      have h := (sum_sq (fun m => stateMatrix (difference U V) j i m z*D (V m) (ex j) z)).trans
        (mul_le_mul_of_nonneg_left (Finset.sum_le_sum fun m _ => ht j i m) (by norm_num : (0:ℝ) ≤ 5))
      simp only [Finset.sum_const,Finset.card_univ,Fintype.card_fin,nsmul_eq_mul] at h
      convert h using 1; ring
    have h := (sum_sq (fun j => ∑ m, stateMatrix (difference U V) j i m z*D (V m) (ex j) z)).trans
      (mul_le_mul_of_nonneg_left (Finset.sum_le_sum fun j _ => inner j) (by norm_num : (0:ℝ) ≤ 3))
    simp only [Finset.sum_const,Finset.card_univ,Fintype.card_fin,nsmul_eq_mul] at h
    change (differenceForcing U V i z)^2 ≤ _ at h
    convert h using 1; ring
  have h := Finset.sum_le_sum (s := Finset.univ) fun i _ => hi i
  simp only [Finset.sum_const,Finset.card_univ,Fintype.card_fin,nsmul_eq_mul] at h
  change S (fun i => differenceForcing U V i z) ≤ 5*(225*A^2*M^2*S w) at h
  dsimp [w] at h
  convert h using 1; ring

theorem forcing_pointwise_bound (U V : Vector) (z : Joint) (K G P A M H R : ℝ)
    (h : Envelope U V z K G P A M H R) :
    EulerBalance.forcingDensity (errorFields U V) z.1 (diagonal (trueVelocity U) z.1)
      (stateOf (errorForcing U V) z.1) z.2 ≤
      growth K G P A M H*EulerMetricEnergy.density (errorFields U V) z.1 z.2+10*G*R := by
  let w : Vec := fun i => difference U V i z
  let f : Vec := fun i => errorForcing U V i z
  have hd : EulerMetricEnergy.density (errorFields U V) z.1 z.2 =
      Q (gm (U 0 z) (U 4 z)) w w := by
    rw [EulerBalance.density_representation]
    exact metric_matrix _ _ w w
  have hc := h.coercivity w
  have hp := quadratic_bound (pm (U 0 z) (U 4 z)) w P h.P_nonneg h.potential_entries
  have hg := pair_bound (gm (U 0 z) (U 4 z)) w f G h.G_nonneg h.metric_entries
  have hf : S f ≤ 2*R+2250*A^2*M^2*S w := by
    have ht : ∀ i, (errorForcing U V i z)^2 ≤
        2*(candidateResidual V i z)^2+2*(differenceForcing U V i z)^2 := by
      intro i
      dsimp [errorForcing]
      nlinarith [sq_nonneg (candidateResidual V i z-differenceForcing U V i z)]
    have hsum := Finset.sum_le_sum (s := Finset.univ) fun i _ => ht i
    simp only [Finset.sum_add_distrib,← Finset.mul_sum] at hsum
    have hdf := difference_forcing_bound U V z A M h.coefficient_difference h.candidate_gradient
    change S f ≤ 2*S (fun i => candidateResidual V i z)+2*S (fun i => differenceForcing U V i z) at hsum
    change S (fun i => differenceForcing U V i z) ≤ 1125*A^2*M^2*S w at hdf
    nlinarith [h.residual]
  have hK := h.K_nonneg
  have hG := h.G_nonneg
  have hP := h.P_nonneg
  have hH := h.H_nonneg
  have htheta := h.divergence
  have hab : |EulerBalance.theta (diagonal (trueVelocity U) z.1) z.2*
      Q (pm (U 0 z) (U 4 z)) w w| ≤ H*(5*P*S w) := by
    rw [abs_mul]
    exact mul_le_mul htheta hp (abs_nonneg _) h.H_nonneg
  have hfg := mul_le_mul_of_nonneg_left hf (mul_nonneg (by norm_num : (0:ℝ) ≤ 5) h.G_nonneg)
  have hcg := mul_le_mul_of_nonneg_left hc (by positivity : 0 ≤ 5*H*P+5*G*(1+2250*A^2*M^2))
  rw [hd]
  change EulerBalance.theta (diagonal (trueVelocity U) z.1) z.2*
    EulerTransport.potential (U 0 z) (U 4 z) (ts w)+
    2*EulerTransport.metric (U 0 z) (U 4 z) (ts w) (ts f) ≤ _
  rw [potential_matrix,metric_matrix]
  have hpa := le_abs_self (EulerBalance.theta (diagonal (trueVelocity U) z.1) z.2*Q (pm (U 0 z) (U 4 z)) w w)
  have hga := le_abs_self (Q (gm (U 0 z) (U 4 z)) w f)
  dsimp [growth]
  nlinarith

def energy (L : ℝ) (U V : Vector) (t : ℝ) : ℝ :=
  EulerPeriodicBox.cubeAverage L (EulerMetricEnergy.density (errorFields U V) t)
def production (L : ℝ) (U V : Vector) (t : ℝ) : ℝ :=
  EulerPeriodicBox.cubeAverage L (EulerBalance.forcingDensity (errorFields U V) t
    (diagonal (trueVelocity U) t) (stateOf (errorForcing U V) t))

-- No differential or integrated energy inequality is an input.
theorem regular_energy_derivative (L t r qmin pmin : ℝ) (hL : 0 < L) (hr : 0 < r)
    (hqm : 0 < qmin) (hpm : 0 < pmin) (U V : Vector)
    (hu : ∀ i, ContDiff ℝ 2 (U i)) (hv : ∀ i, ContDiff ℝ 2 (V i))
    (hqp : ∀ s ∈ Icc (t-r) (t+r), ∀ x, qmin ≤ U 0 (s,x))
    (hpp : ∀ s ∈ Icc (t-r) (t+r), ∀ x, pmin ≤ U 4 (s,x))
    (pu : ∀ i, Periodic L (U i)) (pv : ∀ i, Periodic L (V i))
    (heq : ∀ x i, candidateResidual U i (t,x) = 0) :
    HasDerivAt (energy L U V) (production L U V t) t := by
  obtain ⟨B,ht,hs⟩ := error_regular_premises L t r qmin pmin hr hqm hpm U V hu hv hqp hpp pu pv
  have ht0 : t ∈ Icc (t-r) (t+r) := ⟨by linarith,by linarith⟩
  exact (error_energy_balance L t r hL U V (fun _ => B)
    (fun x i => ((hu i).differentiable (by norm_num)) (t,x))
    (fun x i => ((hv i).differentiable (by norm_num)) (t,x)) heq
    (fun x => lt_of_lt_of_le hqm (hqp t ht0 x))
    (fun x => lt_of_lt_of_le hpm (hpp t ht0 x)) ht hs).2

-- A generic FTC composition retaining separate time integrability premises.
theorem integrated_comparison (a b C D : ℝ) (hab : a ≤ b) (E F : ℝ → ℝ)
    (hd : ∀ t ∈ Icc a b, HasDerivAt E (F t) t)
    (hb : ∀ t ∈ Icc a b, F t ≤ C*E t+D)
    (hf : IntervalIntegrable F volume a b)
    (hi : IntervalIntegrable (fun t => C*E t+D) volume a b) :
    E b ≤ E a+∫ t in a..b, C*E t+D := by
  have hft := intervalIntegral.integral_eq_sub_of_hasDerivAt
    (by simpa only [uIcc_of_le hab] using hd) hf
  have hm := intervalIntegral.integral_mono_on hab hf hi hb
  linarith

lemma average_const (L d : ℝ) (hL : 0 < L) :
    EulerPeriodicBox.cubeAverage L (fun _ => d) = d := by
  simp [EulerPeriodicBox.cubeAverage,EulerPeriodicBox.cubeMeasure,integral_const,
    measureReal_def,EulerCellMoments.box_measure_univ (fun _ => 0) L hL]

theorem regular_production_bound (L t r qmin pmin : ℝ) (hL : 0 < L) (hr : 0 < r)
    (hqm : 0 < qmin) (hpm : 0 < pmin) (U V : Vector)
    (hu : ∀ i, ContDiff ℝ 2 (U i)) (hv : ∀ i, ContDiff ℝ 2 (V i))
    (hqp : ∀ s ∈ Icc (t-r) (t+r), ∀ x, qmin ≤ U 0 (s,x))
    (hpp : ∀ s ∈ Icc (t-r) (t+r), ∀ x, pmin ≤ U 4 (s,x))
    (pu : ∀ i, Periodic L (U i)) (pv : ∀ i, Periodic L (V i))
    (heq : ∀ x i, candidateResidual U i (t,x) = 0)
    (K G P A M H R : ℝ) (hen : ∀ x, Envelope U V (t,x) K G P A M H R) :
    production L U V t ≤ growth K G P A M H*energy L U V t+10*G*R := by
  obtain ⟨B,ht,hs⟩ := error_regular_premises L t r qmin pmin hr hqm hpm U V hu hv hqp hpp pu pv
  have ht0 : t ∈ Icc (t-r) (t+r) := ⟨by linarith,by linarith⟩
  have hq : ∀ x, 0 < U 0 (t,x) := fun x => lt_of_lt_of_le hqm (hqp t ht0 x)
  have hp : ∀ x, 0 < U 4 (t,x) := fun x => lt_of_lt_of_le hpm (hpp t ht0 x)
  have hbal := error_energy_balance L t r hL U V (fun _ => B)
    (fun x i => ((hu i).differentiable (by norm_num)) (t,x))
    (fun x i => ((hv i).differentiable (by norm_num)) (t,x)) heq hq hp ht hs
  have hc := density_continuous_slice (U 0) (U 4) (difference U V)
    (hu 0).continuous (hu 4).continuous (fun i => ((hu i).sub (hv i)).continuous)
    t (fun x => ne_of_gt (hq x)) (fun x => ne_of_gt (hp x))
  have hi := cube_integrable L _ hc
  have hconst := cube_integrable L (fun _ => 10*G*R) continuous_const
  have hmaj := (hi.const_mul (growth K G P A M H)).add hconst
  have hm := integral_mono_ae hbal.1 hmaj
    (Filter.Eventually.of_forall fun x => forcing_pointwise_bound U V (t,x) K G P A M H R (hen x))
  change production L U V t ≤
    (∫ x, growth K G P A M H*EulerMetricEnergy.density (errorFields U V) t x
      +10*G*R ∂EulerPeriodicBox.cubeMeasure L) at hm
  have hsplit : (∫ x, growth K G P A M H*
      EulerMetricEnergy.density (errorFields U V) t x+10*G*R
        ∂EulerPeriodicBox.cubeMeasure L) =
      (∫ x, growth K G P A M H*EulerMetricEnergy.density (errorFields U V) t x
        ∂EulerPeriodicBox.cubeMeasure L)+
      (∫ x, (10*G*R:ℝ) ∂EulerPeriodicBox.cubeMeasure L) :=
    integral_add (hi.const_mul (growth K G P A M H)) hconst
  rw [hsplit,integral_const_mul] at hm
  change production L U V t ≤ growth K G P A M H*energy L U V t+
    EulerPeriodicBox.cubeAverage L (fun _ => 10*G*R) at hm
  rwa [average_const L _ hL] at hm

-- These input fields are regularity, Euler and explicit coefficient hypotheses,
-- plus two separately retained time-integrability premises; no balance is assumed.
structure Slab (L a b r qmin pmin K G P A M H R : ℝ) (U V : Vector) : Prop where
  length_pos : 0 < L
  ordered : a ≤ b
  radius_pos : 0 < r
  qmin_pos : 0 < qmin
  pmin_pos : 0 < pmin
  true_C2 : ∀ i, ContDiff ℝ 2 (U i)
  candidate_C2 : ∀ i, ContDiff ℝ 2 (V i)
  q_margin : ∀ s ∈ Icc (a-r) (b+r), ∀ x, qmin ≤ U 0 (s,x)
  p_margin : ∀ s ∈ Icc (a-r) (b+r), ∀ x, pmin ≤ U 4 (s,x)
  true_periodic : ∀ i, Periodic L (U i)
  candidate_periodic : ∀ i, Periodic L (V i)
  original_Euler : ∀ t ∈ Icc a b, ∀ x i, candidateResidual U i (t,x) = 0
  coefficients : ∀ t ∈ Icc a b, ∀ x, Envelope U V (t,x) K G P A M H R
  time_production_integrable : IntervalIntegrable (production L U V) volume a b
  time_majorant_integrable : IntervalIntegrable
    (fun t => growth K G P A M H*energy L U V t+10*G*R) volume a b

theorem integrated_error_energy (L a b r qmin pmin K G P A M H R : ℝ) (U V : Vector)
    (h : Slab L a b r qmin pmin K G P A M H R U V) :
    energy L U V b ≤ energy L U V a+
      ∫ t in a..b, growth K G P A M H*energy L U V t+10*G*R := by
  have hq : ∀ t ∈ Icc a b, ∀ s ∈ Icc (t-r) (t+r), ∀ x, qmin ≤ U 0 (s,x) := by
    intro t ht s hs x
    exact h.q_margin s ⟨by linarith [ht.1,hs.1],by linarith [ht.2,hs.2]⟩ x
  have hp : ∀ t ∈ Icc a b, ∀ s ∈ Icc (t-r) (t+r), ∀ x, pmin ≤ U 4 (s,x) := by
    intro t ht s hs x
    exact h.p_margin s ⟨by linarith [ht.1,hs.1],by linarith [ht.2,hs.2]⟩ x
  apply integrated_comparison a b _ _ h.ordered (energy L U V) (production L U V)
  · intro t ht
    exact regular_energy_derivative L t r qmin pmin h.length_pos h.radius_pos h.qmin_pos h.pmin_pos
      U V h.true_C2 h.candidate_C2 (hq t ht) (hp t ht) h.true_periodic h.candidate_periodic
      (h.original_Euler t ht)
  · intro t ht
    exact regular_production_bound L t r qmin pmin h.length_pos h.radius_pos h.qmin_pos h.pmin_pos
      U V h.true_C2 h.candidate_C2 (hq t ht) (hp t ht) h.true_periodic h.candidate_periodic
      (h.original_Euler t ht) K G P A M H R (h.coefficients t ht)
  · exact h.time_production_integrable
  · exact h.time_majorant_integrable

theorem physical_integrated_error_energy (a b r qmin pmin K G P A M H R : ℝ) (U V : Vector)
    (h : Slab (2*Real.pi) a b r qmin pmin K G P A M H R U V) :
    energy (2*Real.pi) U V b ≤ energy (2*Real.pi) U V a+
      ∫ t in a..b, growth K G P A M H*energy (2*Real.pi) U V t+10*G*R :=
  integrated_error_energy _ _ _ _ _ _ _ _ _ _ _ _ _ U V h

theorem metric_coefficient_control :
    EulerTransport.metric 1 1 (ts ![1,0,0,0,1]) (ts ![0,0,0,0,1]) = 5/4 ∧
    EulerTransport.potential 1 1 (ts ![1,0,0,0,1]) = 15/4 := by
  norm_num [EulerTransport.metric,EulerTransport.potential,ts,bi,Fin.sum_univ_succ,five_last]

end EulerTimeEnergy

namespace EulerTimeContinuity
open MeasureTheory Set Filter
open scoped BigOperators Topology Interval
open EulerOrdered EulerErrorField EulerErrorIntegral EulerRegularPremises EulerTimeEnergy

-- The previous two time-integrability fields are absent.
structure RegularSlab (L a b r qmin pmin K G P A M H R : ℝ) (U V : Vector) : Prop where
  length_pos : 0 < L
  ordered : a ≤ b
  radius_pos : 0 < r
  qmin_pos : 0 < qmin
  pmin_pos : 0 < pmin
  true_C2 : ∀ i, ContDiff ℝ 2 (U i)
  candidate_C2 : ∀ i, ContDiff ℝ 2 (V i)
  q_margin : ∀ s ∈ Icc (a-r) (b+r), ∀ x, qmin ≤ U 0 (s,x)
  p_margin : ∀ s ∈ Icc (a-r) (b+r), ∀ x, pmin ≤ U 4 (s,x)
  true_periodic : ∀ i, Periodic L (U i)
  candidate_periodic : ∀ i, Periodic L (V i)
  original_Euler : ∀ t ∈ Icc a b, ∀ x i, candidateResidual U i (t,x) = 0
  coefficients : ∀ t ∈ Icc a b, ∀ x, Envelope U V (t,x) K G P A M H R

-- Joint continuity on a compact cylinder supplies the common dominating constant.
theorem cube_average_continuousOn (L a b : ℝ) (F : Joint → ℝ)
    (hc : ∀ z ∈ Icc a b ×ˢ EulerPeriodicBox.cube L, ContinuousAt F z)
    (hsl : ∀ t ∈ Icc a b, Continuous (fun x => F (t,x))) :
    ContinuousOn (fun t => EulerPeriodicBox.cubeAverage L (fun x => F (t,x))) (Icc a b) := by
  have hK : IsCompact (Icc a b ×ˢ EulerPeriodicBox.cube L) := isCompact_Icc.prod isCompact_Icc
  have hnorm : ContinuousOn (fun z => ‖F z‖) (Icc a b ×ˢ EulerPeriodicBox.cube L) :=
    fun z hz => (hc z hz).norm.continuousWithinAt
  obtain ⟨B,hB⟩ := hK.bddAbove_image hnorm
  have hae : ∀ᵐ x ∂EulerPeriodicBox.cubeMeasure L, x ∈ EulerPeriodicBox.cube L :=
    Measure.ae_smul_measure (ae_restrict_mem measurableSet_Icc) _
  intro t ht
  have hn : ∀ᶠ s in 𝓝[Icc a b] t, s ∈ Icc a b := self_mem_nhdsWithin
  exact tendsto_integral_filter_of_dominated_convergence (fun _ => B)
    (hn.mono fun s hs => (hsl s hs).aestronglyMeasurable)
    (hn.mono fun s hs => hae.mono fun x hx => hB ⟨(s,x),⟨hs,hx⟩,rfl⟩)
    (cube_integrable L _ continuous_const)
    (hae.mono fun x hx => by
      have hline : ContinuousAt (fun s : ℝ => ((s,x) : Joint)) t :=
        (continuous_id.prodMk continuous_const).continuousAt
      have hpoint : ContinuousAt (fun s : ℝ => F (s,x)) t := ContinuousAt.comp (g := F) (f := fun s : ℝ => ((s,x) : Joint)) (hc (t,x) ⟨ht,hx⟩) hline
      exact hpoint.continuousWithinAt)

variable {L a b r qmin pmin K G P A M H R : ℝ} {U V : Vector}

lemma slice_q (h : RegularSlab L a b r qmin pmin K G P A M H R U V)
    (t : ℝ) (ht : t ∈ Icc a b) :
    ∀ s ∈ Icc (t-r) (t+r), ∀ x, qmin ≤ U 0 (s,x) := by
  intro s hs x
  exact h.q_margin s ⟨by linarith [ht.1,hs.1],by linarith [ht.2,hs.2]⟩ x

lemma slice_p (h : RegularSlab L a b r qmin pmin K G P A M H R U V)
    (t : ℝ) (ht : t ∈ Icc a b) :
    ∀ s ∈ Icc (t-r) (t+r), ∀ x, pmin ≤ U 4 (s,x) := by
  intro s hs x
  exact h.p_margin s ⟨by linarith [ht.1,hs.1],by linarith [ht.2,hs.2]⟩ x

lemma q_pos (h : RegularSlab L a b r qmin pmin K G P A M H R U V)
    (t : ℝ) (ht : t ∈ Icc a b) (x : Space) : 0 < U 0 (t,x) :=
  lt_of_lt_of_le h.qmin_pos (h.q_margin t
    ⟨by linarith [ht.1,h.radius_pos],by linarith [ht.2,h.radius_pos]⟩ x)

lemma p_pos (h : RegularSlab L a b r qmin pmin K G P A M H R U V)
    (t : ℝ) (ht : t ∈ Icc a b) (x : Space) : 0 < U 4 (t,x) :=
  lt_of_lt_of_le h.pmin_pos (h.p_margin t
    ⟨by linarith [ht.1,h.radius_pos],by linarith [ht.2,h.radius_pos]⟩ x)

theorem energy_continuousOn (h : RegularSlab L a b r qmin pmin K G P A M H R U V) :
    ContinuousOn (energy L U V) (Icc a b) := by
  intro t ht
  exact (regular_energy_derivative L t r qmin pmin h.length_pos h.radius_pos h.qmin_pos
    h.pmin_pos U V h.true_C2 h.candidate_C2 (slice_q h t ht) (slice_p h t ht)
    h.true_periodic h.candidate_periodic (h.original_Euler t ht)).continuousAt.continuousWithinAt

-- Uniqueness identifies the actual production with the actual time-rate integral.
theorem production_eq_rate (h : RegularSlab L a b r qmin pmin K G P A M H R U V)
    (t : ℝ) (ht : t ∈ Icc a b) :
    production L U V t = EulerPeriodicBox.cubeAverage L
      (EulerMetricEnergy.rate (errorFields U V) (timeFields (U 0) (U 4) (difference U V)) t) := by
  obtain ⟨B,hT,_⟩ := error_regular_premises L t r qmin pmin h.radius_pos h.qmin_pos h.pmin_pos
    U V h.true_C2 h.candidate_C2 (slice_q h t ht) (slice_p h t ht)
    h.true_periodic h.candidate_periodic
  have hd := regular_energy_derivative L t r qmin pmin h.length_pos h.radius_pos h.qmin_pos
    h.pmin_pos U V h.true_C2 h.candidate_C2 (slice_q h t ht) (slice_p h t ht)
    h.true_periodic h.candidate_periodic (h.original_Euler t ht)
  have hr := (EulerMetricEnergy.cube_energy_hasDeriv L t r hT.eps_pos
    (errorFields U V) (timeFields (U 0) (U 4) (difference U V)) (fun _ => B)
    hT.measurable hT.integrable hT.rate_measurable hT.dominated hT.bound_integrable hT.actual_jets).2
  exact hd.unique hr

theorem production_continuousOn (h : RegularSlab L a b r qmin pmin K G P A M H R U V) :
    ContinuousOn (production L U V) (Icc a b) := by
  have hu : ∀ i, ContDiff ℝ 1 (U i) := fun i => (h.true_C2 i).of_le (by norm_num)
  have hw : ∀ i, ContDiff ℝ 1 (difference U V i) :=
    fun i => ((h.true_C2 i).sub (h.candidate_C2 i)).of_le (by norm_num)
  have hc := cube_average_continuousOn L a b
    (fun z => EulerMetricEnergy.rate (errorFields U V)
      (timeFields (U 0) (U 4) (difference U V)) z.1 z.2)
    (fun z hz => rate_continuousAt (U 0) (U 4) (difference U V) et (hu 0) (hu 4) hw z
      (ne_of_gt (q_pos h z.1 hz.1 z.2)) (ne_of_gt (p_pos h z.1 hz.1 z.2)))
    (fun t ht => rate_continuous_slice (U 0) (U 4) (difference U V) et (hu 0) (hu 4) hw t
      (fun x => ne_of_gt (q_pos h t ht x)) (fun x => ne_of_gt (p_pos h t ht x)))
  exact hc.congr fun t ht => production_eq_rate h t ht

theorem time_integrability (h : RegularSlab L a b r qmin pmin K G P A M H R U V) :
    IntervalIntegrable (production L U V) volume a b ∧
      IntervalIntegrable (fun t => growth K G P A M H*energy L U V t+10*G*R) volume a b := by
  constructor
  · exact (production_continuousOn h).intervalIntegrable_of_Icc h.ordered
  · exact ((continuousOn_const.mul (energy_continuousOn h)).add continuousOn_const).intervalIntegrable_of_Icc h.ordered

theorem regular_to_slab (h : RegularSlab L a b r qmin pmin K G P A M H R U V) :
    Slab L a b r qmin pmin K G P A M H R U V := by
  have hi := time_integrability h
  exact ⟨h.length_pos,h.ordered,h.radius_pos,h.qmin_pos,h.pmin_pos,h.true_C2,h.candidate_C2,
    h.q_margin,h.p_margin,h.true_periodic,h.candidate_periodic,h.original_Euler,h.coefficients,hi.1,hi.2⟩

theorem integrated_error_energy (h : RegularSlab L a b r qmin pmin K G P A M H R U V) :
    energy L U V b ≤ energy L U V a+
      ∫ t in a..b, growth K G P A M H*energy L U V t+10*G*R :=
  EulerTimeEnergy.integrated_error_energy L a b r qmin pmin K G P A M H R U V (regular_to_slab h)

theorem physical_integrated_error_energy
    (h : RegularSlab (2*Real.pi) a b r qmin pmin K G P A M H R U V) :
    energy (2*Real.pi) U V b ≤ energy (2*Real.pi) U V a+
      ∫ t in a..b, growth K G P A M H*energy (2*Real.pi) U V t+10*G*R :=
  integrated_error_energy h

end EulerTimeContinuity

namespace EulerGronwall
open MeasureTheory Set
open scoped BigOperators Topology Interval
open EulerOrdered EulerErrorField EulerErrorIntegral EulerRegularPremises EulerTimeEnergy
open EulerTimeContinuity

-- A division-free sufficient bound, valid also when C = 0.
theorem scalar_bound (a b C D : ℝ) (hab : a ≤ b) (hC : 0 ≤ C) (hD : 0 ≤ D)
    (E F : ℝ → ℝ) (hd : ∀ t ∈ Icc a b, HasDerivAt E (F t) t)
    (hb : ∀ t ∈ Icc a b, F t ≤ C*E t+D) :
    E b ≤ Real.exp (C*(b-a))*(E a+D*(b-a)) := by
  let w : ℝ → ℝ := fun t => Real.exp (-C*(t-a))*E t
  let wrate : ℝ → ℝ := fun t =>
    Real.exp (-C*(t-a))*(-C)*E t+Real.exp (-C*(t-a))*F t
  have hw : ∀ t ∈ Icc a b, HasDerivAt w (wrate t) t := by
    intro t ht
    have he : HasDerivAt (fun s : ℝ => Real.exp (-C*(s-a)))
        (Real.exp (-C*(t-a))*(-C)) t := by
      simpa using (((hasDerivAt_id t).sub_const a).const_mul (-C)).exp
    exact he.mul (hd t ht)
  have hbound : ∀ t ∈ Icc a b, wrate t ≤ D := by
    intro t ht
    have hep : 0 ≤ Real.exp (-C*(t-a)) := (Real.exp_pos _).le
    have hel : Real.exp (-C*(t-a)) ≤ 1 := Real.exp_le_one_iff.mpr
      (mul_nonpos_of_nonpos_of_nonneg (neg_nonpos.mpr hC) (sub_nonneg.mpr ht.1))
    calc
      wrate t = Real.exp (-C*(t-a))*(F t-C*E t) := by dsimp [wrate]; ring
      _ ≤ Real.exp (-C*(t-a))*D := mul_le_mul_of_nonneg_left (by linarith [hb t ht]) hep
      _ ≤ 1*D := mul_le_mul_of_nonneg_right hel hD
      _ = D := one_mul D
  have hfence := image_le_of_deriv_right_le_deriv_boundary
    (f := w) (f' := wrate) (a := a) (b := b)
    (fun t ht => (hw t ht).continuousAt.continuousWithinAt)
    (fun t ht => (hw t ⟨ht.1,ht.2.le⟩).hasDerivWithinAt)
    (B := fun t => E a+D*(t-a)) (B' := fun _ => D)
    (by simp [w])
    (continuous_const.add (continuous_const.mul (continuous_id.sub continuous_const))).continuousOn
    (fun t _ => by
      simpa using ((((hasDerivAt_id t).sub_const a).const_mul D).const_add (E a)).hasDerivWithinAt)
    (fun t ht => hbound t ⟨ht.1,ht.2.le⟩)
  have hend := hfence ⟨hab,le_rfl⟩
  have hm := mul_le_mul_of_nonneg_left hend (Real.exp_pos (C*(b-a))).le
  have he : Real.exp (C*(b-a))*Real.exp (-C*(b-a)) = 1 := by
    rw [← Real.exp_add]
    simp
  calc
    E b = Real.exp (C*(b-a))*(Real.exp (-C*(b-a))*E b) := by
      rw [← mul_assoc,he,one_mul]
    _ ≤ Real.exp (C*(b-a))*(E a+D*(b-a)) := hm

variable {L a b r qmin pmin K G P A M H R : ℝ} {U V : Vector}

theorem coefficient_nonneg (h : RegularSlab L a b r qmin pmin K G P A M H R U V) :
    0 ≤ growth K G P A M H ∧ 0 ≤ 10*G*R := by
  have hen := h.coefficients a ⟨le_rfl,h.ordered⟩ (0:Space)
  have hK := hen.K_nonneg
  have hG := hen.G_nonneg
  have hP := hen.P_nonneg
  have hH := hen.H_nonneg
  have hR : 0 ≤ R :=
    (Finset.sum_nonneg (fun i _ => sq_nonneg (candidateResidual V i (a,(0:Space))))).trans hen.residual
  constructor
  · dsimp [growth]
    positivity
  · positivity

theorem gronwall_energy (h : RegularSlab L a b r qmin pmin K G P A M H R U V) :
    energy L U V b ≤ Real.exp (growth K G P A M H*(b-a))*
      (energy L U V a+10*G*R*(b-a)) := by
  obtain ⟨hC,hD⟩ := coefficient_nonneg h
  apply scalar_bound a b _ _ h.ordered hC hD (energy L U V) (production L U V)
  · intro t ht
    exact regular_energy_derivative L t r qmin pmin h.length_pos h.radius_pos h.qmin_pos h.pmin_pos
      U V h.true_C2 h.candidate_C2 (slice_q h t ht) (slice_p h t ht)
      h.true_periodic h.candidate_periodic (h.original_Euler t ht)
  · intro t ht
    exact regular_production_bound L t r qmin pmin h.length_pos h.radius_pos h.qmin_pos h.pmin_pos
      U V h.true_C2 h.candidate_C2 (slice_q h t ht) (slice_p h t ht)
      h.true_periodic h.candidate_periodic (h.original_Euler t ht) K G P A M H R (h.coefficients t ht)

theorem physical_gronwall_energy
    (h : RegularSlab (2*Real.pi) a b r qmin pmin K G P A M H R U V) :
    energy (2*Real.pi) U V b ≤ Real.exp (growth K G P A M H*(b-a))*
      (energy (2*Real.pi) U V a+10*G*R*(b-a)) := gronwall_energy h

theorem zero_growth_energy (h : RegularSlab L a b r qmin pmin K G P A M H R U V)
    (hc : growth K G P A M H = 0) :
    energy L U V b ≤ energy L U V a+10*G*R*(b-a) := by
  simpa only [hc,zero_mul,Real.exp_zero,one_mul] using gronwall_energy h

theorem zero_residual_energy (h : RegularSlab L a b r qmin pmin K G P A M H R U V)
    (hr : R = 0) :
    energy L U V b ≤ Real.exp (growth K G P A M H*(b-a))*energy L U V a := by
  simpa only [hr,mul_zero,zero_mul,add_zero] using gronwall_energy h

-- Exact scalar formula control; not a full-premise Euler trajectory.
theorem zero_growth_control :
    Real.exp (0*((1/4:ℝ)-0))*((2:ℝ)+3*((1/4:ℝ)-0)) = 11/4 ∧
      (2+3*(1/4:ℝ)) > 2 := by norm_num

end EulerGronwall
