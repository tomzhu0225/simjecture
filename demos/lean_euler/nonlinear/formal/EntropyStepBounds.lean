import Mathlib.Data.Nat.Log
import Mathlib.Algebra.Order.Floor.Semiring

-- A state-dependent quantitative bound for the same exact-real halving search.
-- Uniform trajectory and total-work-to-accuracy bounds are still required.
noncomputable section
namespace EulerEntropyStepBounds
open EulerEntropy EulerPressurePolynomial EulerEntropyCandidateStep
open scoped BigOperators
abbrev State := Fin 5 → ℝ

def localRate (u k : State) : ℝ :=
  |k 0|/u 0+(|firstCoefficient u k|+|secondCoefficient k|)/quadratic u

theorem local_rate_nonnegative (u k : State) (hu : EulerAdmissible.Admissible u) :
    0 ≤ localRate u k := by
  have hr := hu.1
  have hQ := quadratic_positive u hu
  dsimp [localRate]
  positivity

def maximumRate {I : Type*} [Fintype I] [Nonempty I] (u k : I → State) : ℝ :=
  Finset.univ.sup' Finset.univ_nonempty (fun i => localRate (u i) (k i))

theorem maximum_rate_bound {I : Type*} [Fintype I] [Nonempty I]
    (u k : I → State) (i : I) : localRate (u i) (k i) ≤ maximumRate u k :=
  Finset.le_sup' (f := fun i => localRate (u i) (k i)) (Finset.mem_univ i)

theorem maximum_rate_nonnegative {I : Type*} [Fintype I] [Nonempty I]
    (u k : I → State) (hu : ∀ i, EulerAdmissible.Admissible (u i)) : 0 ≤ maximumRate u k := by
  obtain ⟨i⟩ := ‹Nonempty I›
  exact (local_rate_nonnegative (u i) (k i) (hu i)).trans (maximum_rate_bound u k i)

def radius {I : Type*} [Fintype I] [Nonempty I] (u k : I → State) : ℝ :=
  1/(2*(1+maximumRate u k))

theorem radius_bounds {I : Type*} [Fintype I] [Nonempty I]
    (u k : I → State) (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    0 < radius u k ∧ radius u k ≤ 1/2 := by
  have hn := maximum_rate_nonnegative u k hu
  constructor
  · dsimp [radius]
    positivity
  · exact one_div_le_one_div_of_le (by norm_num) (by linarith)

theorem radius_times_rate {I : Type*} [Fintype I] [Nonempty I]
    (u k : I → State) (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    radius u k*maximumRate u k ≤ 1/2 := by
  have hn := maximum_rate_nonnegative u k hu
  dsimp [radius]
  calc
    _ = maximumRate u k/(2*(1+maximumRate u k)) := by ring
    _ ≤ _ := (div_le_iff₀ (by positivity : 0 < 2*(1+maximumRate u k))).mpr (by linarith)

theorem trial_path_bound {I : Type*} [Fintype I] [Nonempty I]
    (u k : I → State) (hu : ∀ i, EulerAdmissible.Admissible (u i))
    (s : ℝ) (hs : 0 ≤ s) (hsr : s ≤ radius u k) (i : I) :
    EulerAdmissible.Admissible (u i+s • k i) ∧
      EulerEntropyTaylor.conservativeHessian (u i+s • k i) (k i) ≤ curvatureBound (u i) (k i) := by
  have hlocal := maximum_rate_bound u k i
  have hr := (hu i).1
  have hQ := quadratic_positive (u i) (hu i)
  have hrate : s*localRate (u i) (k i) ≤ 1/2 := by
    calc
      _ ≤ s*maximumRate u k := mul_le_mul_of_nonneg_left hlocal hs
      _ ≤ radius u k*maximumRate u k :=
        mul_le_mul_of_nonneg_right hsr (maximum_rate_nonnegative u k hu)
      _ ≤ _ := radius_times_rate u k hu
  have hparts : s*|k i 0|/u i 0+
      s*(|firstCoefficient (u i) (k i)|+|secondCoefficient (k i)|)/quadratic (u i) ≤ 1/2 := by
    calc
      _ = s*localRate (u i) (k i) := by dsimp [localRate]; ring
      _ ≤ _ := hrate
  have hrsmall : s*|k i 0| ≤ u i 0/2 := by
    have hh : 0 ≤ s*(|firstCoefficient (u i) (k i)|+|secondCoefficient (k i)|)/quadratic (u i) := by positivity
    have hm : s*|k i 0|/u i 0 ≤ 1/2 := by linarith
    have hx := (div_le_iff₀ hr).mp hm
    linarith
  have hQsmall : s*(|firstCoefficient (u i) (k i)|+|secondCoefficient (k i)|) ≤ quadratic (u i)/2 := by
    have hh : 0 ≤ s*|k i 0|/u i 0 := by positivity
    have hm : s*(|firstCoefficient (u i) (k i)|+|secondCoefficient (k i)|)/quadratic (u i) ≤ 1/2 := by
      linarith
    have hx := (div_le_iff₀ hQ).mp hm
    linarith
  exact path_curvature_bound (u i) (k i) (hu i) s hs
    (hsr.trans ((radius_bounds u k hu).2.trans (by norm_num))) hrsmall hQsmall

theorem line_entropy_upper (u k : State) (r B : ℝ) (hr : 0 ≤ r)
    (hpath : ∀ s ∈ Set.Icc (0 : ℝ) r, EulerAdmissible.Admissible (u+s • k) ∧
      EulerEntropyTaylor.conservativeHessian (u+s • k) k ≤ B) :
    entropy (u+r • k) ≤ entropy u+r*dot (gradient u) k+r^2*B/2 := by
  let v := u+r • k
  let f := fun t => entropy (EulerEntropyConvexity.segment u v t)
  let df := fun t => dot (gradient (EulerEntropyConvexity.segment u v t)) (v-u)
  let ddf := fun t => EulerEntropyTaylor.conservativeHessian (EulerEntropyConvexity.segment u v t) (v-u)
  have he (t : ℝ) : EulerEntropyConvexity.segment u v t=u+(t*r) • k := by
    funext j
    dsimp [EulerEntropyConvexity.segment,v]
    ring
  have hs (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : t*r ∈ Set.Icc (0 : ℝ) r := by
    exact ⟨mul_nonneg ht.1 hr,by nlinarith [mul_le_mul_of_nonneg_right ht.2 hr]⟩
  have hadm (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
      EulerAdmissible.Admissible (EulerEntropyConvexity.segment u v t) := by
    rw [he]
    exact (hpath _ (hs t ht)).1
  have hf (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t :=
    entropy_derivative (EulerEntropyConvexity.segment_derivative u v t)
      (ne_of_gt (hadm t ht).1) (ne_of_gt (hadm t ht).2)
  have hdf (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt df (ddf t) t :=
    entropy_second_directional (EulerEntropyConvexity.segment_derivative u v t)
      (hadm t ht).1 (hadm t ht).2
  have hddf (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : ddf t ≤ r^2*B := by
    dsimp only [ddf]
    have hdiff : v-u=r • k := by dsimp [v]; exact add_sub_cancel_left u (r • k)
    rw [hdiff,hessian_smul _ _ r (hadm t ht),he]
    exact mul_le_mul_of_nonneg_left (hpath _ (hs t ht)).2 (sq_nonneg r)
  have hh := EulerEntropyTaylor.scalar_second_derivative_upper f df ddf (r^2*B) hf hdf hddf
  simpa [f,df,v,EulerEntropyConvexity.segment,EulerVectorEstimates.dot_smul_right] using hh

def curvatureTotal {I : Type*} [Fintype I] (u k : I → State) : ℝ :=
  ∑ i, curvatureBound (u i) (k i)

theorem curvature_total_nonnegative {I : Type*} [Fintype I] (u k : I → State)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) : 0 ≤ curvatureTotal u k :=
  Finset.sum_nonneg (fun i _ => curvature_bound_nonnegative (u i) (k i) (hu i))

theorem total_entropy_upper {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (r : ℝ) (hr : 0 ≤ r)
    (hradius : r ≤ radius u (increment u neighbor a)) :
    totalEntropy (trial u neighbor a r) ≤ totalEntropy u-r*dissipation u neighbor a+
      r^2*curvatureTotal u (increment u neighbor a)/2 := by
  have hi (i : I) : entropy (trial u neighbor a r i) ≤ entropy (u i)+
      r*dot (gradient (u i)) (increment u neighbor a i)+r^2*curvatureBound (u i) (increment u neighbor a i)/2 := by
    exact line_entropy_upper (u i) (increment u neighbor a i) r _ hr
      (fun s hs => trial_path_bound u (increment u neighbor a) hu s hs.1 (hs.2.trans hradius) i)
  have hh := Finset.sum_le_sum (fun i (_ : i ∈ Finset.univ) => hi i)
  simp only [Finset.sum_add_distrib,div_eq_mul_inv,← Finset.sum_mul,← Finset.mul_sum,
    entropy_residual_pairing u neighbor a hu] at hh
  exact hh.trans_eq (by dsimp [totalEntropy,curvatureTotal]; ring)

theorem quantitative_acceptance {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (r : ℝ) (hr : 0 ≤ r)
    (hradius : r ≤ radius u (increment u neighbor a))
    (hbudget : r*curvatureTotal u (increment u neighbor a) ≤ dissipation u neighbor a) :
    Acceptable u neighbor a r := by
  refine ⟨fun i => (trial_path_bound u (increment u neighbor a) hu r hr hradius i).1,?_⟩
  have hh := total_entropy_upper u neighbor a hu r hr hradius
  have hm := mul_le_mul_of_nonneg_left hbudget hr
  nlinarith

def stepCap {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) : ℝ :=
  min (radius u (increment u neighbor a))
    (dissipation u neighbor a/(curvatureTotal u (increment u neighbor a)+dissipation u neighbor a))

theorem step_cap_positive {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (hD : 0 < dissipation u neighbor a) :
    0 < stepCap u neighbor a := by
  have hB := curvature_total_nonnegative u (increment u neighbor a) hu
  exact lt_min (radius_bounds u (increment u neighbor a) hu).1 (div_pos hD (by linarith))

theorem below_cap_acceptable {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (hD : 0 < dissipation u neighbor a)
    (r : ℝ) (hr : 0 ≤ r) (hcap : r ≤ stepCap u neighbor a) : Acceptable u neighbor a r := by
  have hB := curvature_total_nonnegative u (increment u neighbor a) hu
  have hh := le_min_iff.mp hcap
  have hbudget := (le_div_iff₀ (by linarith :
    0 < curvatureTotal u (increment u neighbor a)+dissipation u neighbor a)).mp hh.2
  apply quantitative_acceptance u neighbor a hu r hr hh.1
  nlinarith [mul_nonneg hr hD.le]

def sufficientHalvings (proposal cap : ℝ) : ℕ := Nat.clog 2 (Nat.ceil (proposal/cap))

theorem sufficient_halvings_bound (proposal cap : ℝ) (hcap : 0 < cap) :
    proposal*(1/2 : ℝ)^sufficientHalvings proposal cap ≤ cap := by
  have hc : (Nat.ceil (proposal/cap) : ℝ) ≤ (2 : ℝ)^sufficientHalvings proposal cap := by
    exact_mod_cast Nat.le_pow_clog (by norm_num : 1 < (2 : ℕ)) (Nat.ceil (proposal/cap))
  have hh := (div_le_iff₀ hcap).mp ((Nat.le_ceil (proposal/cap)).trans hc)
  have hp : 0 < (2 : ℝ)^sufficientHalvings proposal cap := by positivity
  calc
    _ = proposal/((2 : ℝ)^sufficientHalvings proposal cap) := by rw [one_div_pow]; ring
    _ ≤ _ := (div_le_iff₀ hp).mpr (by nlinarith)

theorem positive_dissipation_retry_bound {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal)
    (hD : 0 < dissipation u neighbor a) :
    halvingIndex u neighbor a proposal hu ha hproposal ≤
      sufficientHalvings proposal (stepCap u neighbor a) := by
  classical
  apply Nat.find_min'
  exact below_cap_acceptable u neighbor a hu hD _
    (mul_nonneg hproposal.le (pow_nonneg (by norm_num) _))
    (sufficient_halvings_bound proposal _ (step_cap_positive u neighbor a hu hD))

def retryBound {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ) : ℕ :=
  if dissipation u neighbor a=0 then 0 else sufficientHalvings proposal (stepCap u neighbor a)

theorem quantitative_retry_bound {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal) :
    halvingIndex u neighbor a proposal hu ha hproposal ≤ retryBound u neighbor a proposal := by
  classical
  by_cases hD : dissipation u neighbor a=0
  · rw [retryBound,if_pos hD]
    apply Nat.find_min'
    rw [zero_dissipation_stationary u neighbor a hu ha hD,hD]
    simpa only [mul_zero,sub_zero,le_refl,and_true] using hu
  · rw [retryBound,if_neg hD]
    exact positive_dissipation_retry_bound u neighbor a proposal hu ha hproposal
      (lt_of_le_of_ne (dissipation_nonnegative u neighbor a hu (fun d => (ha d).le)) (Ne.symm hD))

theorem accepted_ratio_lower_bound {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal)
    (hD : 0 < dissipation u neighbor a) :
    min proposal (stepCap u neighbor a/2) ≤ acceptedRatio u neighbor a proposal hu ha hproposal := by
  cases he : halvingIndex u neighbor a proposal hu ha hproposal with
  | zero => simpa only [acceptedRatio,he,pow_zero,mul_one] using min_le_left proposal (stepCap u neighbor a/2)
  | succ m =>
    have hrejected := earlier_trials_rejected u neighbor a proposal hu ha hproposal m (by rw [he]; omega)
    have hprev : stepCap u neighbor a < proposal*(1/2 : ℝ)^m := by
      by_contra hnot
      exact hrejected (below_cap_acceptable u neighbor a hu hD _
        (mul_nonneg hproposal.le (pow_nonneg (by norm_num) _)) (le_of_not_gt hnot))
    have hmin := min_le_right proposal (stepCap u neighbor a/2)
    simp only [acceptedRatio,he,pow_succ]
    linarith

end EulerEntropyStepBounds
