-- Assemble after EntropyConvexity.lean. The finite-step remainder is derived
-- from the actual entropy Hessian along the segment between the two states.
noncomputable section
namespace EulerEntropyTaylor
open EulerEntropy EulerEntropyConvexity EulerEnergyBounds

theorem scalar_first_derivative_lower (f df : ℝ → ℝ) (C : ℝ)
    (hf : ∀ t ∈ Set.Icc (0 : ℝ) 1, HasDerivAt f (df t) t)
    (hdf : ∀ t ∈ Set.Icc (0 : ℝ) 1, C ≤ df t) : C ≤ f 1-f 0 := by
  let g := fun t => f t-C*t
  have hg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt g (df t-C) t := by
    convert (hf t ht).sub ((hasDerivAt_id t).const_mul C) using 1
    ring
  have hm := monotoneOn_of_hasDerivWithinAt_nonneg (convex_Icc (0 : ℝ) 1)
    (fun t ht => (hg t ht).continuousAt.continuousWithinAt)
    (fun t ht => (hg t (interior_subset ht)).hasDerivWithinAt)
    (fun t ht => sub_nonneg.mpr (hdf t (interior_subset ht)))
  have hh := hm (by norm_num : (0 : ℝ) ∈ Set.Icc (0 : ℝ) 1)
    (by norm_num : (1 : ℝ) ∈ Set.Icc (0 : ℝ) 1) (by norm_num : (0 : ℝ) ≤ 1)
  simp only [g,mul_zero,mul_one,sub_zero] at hh
  linarith

theorem scalar_first_derivative_upper (f df : ℝ → ℝ) (C : ℝ)
    (hf : ∀ t ∈ Set.Icc (0 : ℝ) 1, HasDerivAt f (df t) t)
    (hdf : ∀ t ∈ Set.Icc (0 : ℝ) 1, df t ≤ C) : f 1-f 0 ≤ C := by
  have hh := scalar_first_derivative_lower (fun t => -f t) (fun t => -df t) (-C)
    (fun t ht => (hf t ht).neg) (fun t ht => neg_le_neg (hdf t ht))
  linarith

theorem scalar_second_derivative_upper (f df ddf : ℝ → ℝ) (C : ℝ)
    (hf : ∀ t ∈ Set.Icc (0 : ℝ) 1, HasDerivAt f (df t) t)
    (hdf : ∀ t ∈ Set.Icc (0 : ℝ) 1, HasDerivAt df (ddf t) t)
    (hddf : ∀ t ∈ Set.Icc (0 : ℝ) 1, ddf t ≤ C) :
    f 1 ≤ f 0+df 0+C/2 := by
  let g := fun t => f t-(C/2)*t^2
  let dg := fun t => df t-C*t
  have hg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt g (dg t) t := by
    convert (hf t ht).sub (((hasDerivAt_id t).pow 2).const_mul (C/2)) using 1
    dsimp [dg]
    ring
  have hdg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt dg (ddf t-C) t := by
    convert (hdf t ht).sub ((hasDerivAt_id t).const_mul C) using 1
    ring
  have hc : ConcaveOn ℝ (Set.Icc (0 : ℝ) 1) g :=
    concaveOn_of_hasDerivWithinAt2_nonpos (convex_Icc (0 : ℝ) 1)
      (fun t ht => (hg t ht).continuousAt.continuousWithinAt)
      (fun t ht => (hg t (interior_subset ht)).hasDerivWithinAt)
      (fun t ht => (hdg t (interior_subset ht)).hasDerivWithinAt)
      (fun t ht => sub_nonpos.mpr (hddf t (interior_subset ht)))
  have hi0 : (0 : ℝ) ∈ Set.Icc (0 : ℝ) 1 := by norm_num
  have hi1 : (1 : ℝ) ∈ Set.Icc (0 : ℝ) 1 := by norm_num
  have hb := hc.slope_le_of_hasDerivAt hi0 hi1 (by norm_num) (hg 0 hi0)
  simp only [slope_def_field,g,dg,zero_pow (by norm_num : (2 : ℕ) ≠ 0),
    one_pow,mul_zero,mul_one,sub_zero,div_one] at hb
  linarith

def conservativeHessian (u k : State) : ℝ := hessianForm (toPrimitive u) (primitiveD u k)

theorem entropy_taylor_upper (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v) (M : ℝ)
    (hH : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      conservativeHessian (segment u v t) (v-u) ≤ M*sizeSquared (v-u)) :
    entropy v ≤ entropy u+dot (gradient u) (v-u)+(M/2)*sizeSquared (v-u) := by
  let f := fun t => entropy (segment u v t)
  let df := fun t => dot (gradient (segment u v t)) (v-u)
  let ddf := fun t => conservativeHessian (segment u v t) (v-u)
  have hf (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t := by
    obtain ⟨hr,hp⟩ := segment_admissible u v hu hv t ht
    exact entropy_derivative (segment_derivative u v t) (ne_of_gt hr) (ne_of_gt hp)
  have hdf (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt df (ddf t) t := by
    obtain ⟨hr,hp⟩ := segment_admissible u v hu hv t ht
    exact entropy_second_directional (segment_derivative u v t) hr hp
  have hb := scalar_second_derivative_upper f df ddf (M*sizeSquared (v-u)) hf hdf hH
  simp [f,df,EulerEntropyConvexity.segment] at hb
  nlinarith

end EulerEntropyTaylor
