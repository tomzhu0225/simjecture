-- Actual Rusanov face entropy residual from proved entropy calculus. The
-- quantitative Hessian and flux bounds on the state segment are explicit.
noncomputable section
namespace EulerFaceEntropy
open EulerEntropy EulerEntropyTaylor EulerEntropyConvexity EulerEntropyGeometry
open EulerVectorEstimates EulerEnergyBounds
abbrev State := Fin 5 → ℝ

def meanFlux (u v : State) (d : Fin 3) : State :=
  (1/2 : ℝ) • (EulerAdmissible.eulerFlux u d+EulerAdmissible.eulerFlux v d)

theorem flux_midpoint_bound (u v w : State) (d : Fin 3) (L : ℝ)
    (h0 : sizeSquared (EulerAdmissible.eulerFlux w d-EulerAdmissible.eulerFlux u d) ≤
      L^2*sizeSquared (v-u))
    (h1 : sizeSquared (EulerAdmissible.eulerFlux w d-EulerAdmissible.eulerFlux v d) ≤
      L^2*sizeSquared (v-u)) :
    sizeSquared (meanFlux u v d-EulerAdmissible.eulerFlux w d) ≤ L^2*sizeSquared (v-u) := by
  have he : meanFlux u v d-EulerAdmissible.eulerFlux w d = (1/2 : ℝ) •
      ((EulerAdmissible.eulerFlux u d-EulerAdmissible.eulerFlux w d)+
        (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux w d)) := by
    funext j
    dsimp [meanFlux]
    ring
  rw [he,size_smul]
  have hh := size_add_bound (EulerAdmissible.eulerFlux u d-EulerAdmissible.eulerFlux w d)
    (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux w d)
  rw [size_sub_comm (EulerAdmissible.eulerFlux u d) _,size_sub_comm (EulerAdmissible.eulerFlux v d) _] at hh
  nlinarith

theorem residual_derivative (u v : State) (d : Fin 3) (t : ℝ)
    (ht : EulerAdmissible.Admissible (EulerEntropyConvexity.segment u v t)) :
    HasDerivAt (fun s => dot (gradient (EulerEntropyConvexity.segment u v s)) (meanFlux u v d)-
      (EulerEntropyConvexity.segment u v s) ⟨d.val+1,by omega⟩)
      (hessianPair (EulerEntropyConvexity.segment u v t) (v-u)
        (meanFlux u v d-EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d)) t := by
  have hcurve := segment_derivative u v t
  have hh := (gradient_pair_derivative hcurve ht (meanFlux u v d)).sub
    ((hasDerivAt_pi.mp hcurve) ⟨d.val+1,by omega⟩)
  simpa only [hessian_pair_sub_right,hessian_flux_compatibility _ _ ht d] using hh

theorem central_entropy_residual (u v : State) (d : Fin 3) (M L : ℝ)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v) (hM : 0 ≤ M)
    (hH : ∀ t ∈ Set.Icc (0 : ℝ) 1, ∀ k,
      conservativeHessian (EulerEntropyConvexity.segment u v t) k ≤ M*sizeSquared k)
    (hF : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      sizeSquared (EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d-
        EulerAdmissible.eulerFlux u d) ≤ L^2*sizeSquared (v-u) ∧
      sizeSquared (EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d-
        EulerAdmissible.eulerFlux v d) ≤ L^2*sizeSquared (v-u)) :
    dot (gradient v-gradient u) (meanFlux u v d)-(v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) ≤
      (M/2)*(1+L^2)*sizeSquared (v-u) := by
  let f := fun t => dot (gradient (EulerEntropyConvexity.segment u v t)) (meanFlux u v d)-
    (EulerEntropyConvexity.segment u v t) ⟨d.val+1,by omega⟩
  let df := fun t => hessianPair (EulerEntropyConvexity.segment u v t) (v-u)
    (meanFlux u v d-EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d)
  have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t :=
    residual_derivative u v d t (segment_admissible u v hu hv t ht)
  have hb (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
      df t ≤ (M/2)*(1+L^2)*sizeSquared (v-u) := by
    have hh := hessian_young_bound (EulerEntropyConvexity.segment u v t) (v-u)
      (meanFlux u v d-EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d)
      (segment_admissible u v hu hv t ht) M
      (hH t ht _) (hH t ht _)
    have hflux := flux_midpoint_bound u v (EulerEntropyConvexity.segment u v t) d L
      (hF t ht).1 (hF t ht).2
    have hmult := mul_le_mul_of_nonneg_left hflux (by positivity : 0 ≤ M/2)
    dsimp [df]
    nlinarith
  have hs := scalar_first_derivative_upper f df ((M/2)*(1+L^2)*sizeSquared (v-u)) hd hb
  simp [f,EulerEntropyConvexity.segment] at hs
  rw [dot_sub_left]
  linarith

theorem gradient_strong_monotonicity (u v : State) (lambda : ℝ)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v)
    (hH : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      lambda*sizeSquared (v-u) ≤ conservativeHessian (EulerEntropyConvexity.segment u v t) (v-u)) :
    lambda*sizeSquared (v-u) ≤ dot (gradient v-gradient u) (v-u) := by
  let f := fun t => dot (gradient (EulerEntropyConvexity.segment u v t)) (v-u)
  let df := fun t => conservativeHessian (EulerEntropyConvexity.segment u v t) (v-u)
  have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t := by
    have h := segment_admissible u v hu hv t ht
    exact entropy_second_directional (segment_derivative u v t) h.1 h.2
  have hs := scalar_first_derivative_lower f df (lambda*sizeSquared (v-u)) hd hH
  simpa [f,EulerEntropyConvexity.segment,dot_sub_left] using hs

theorem rusanov_face_entropy_bound (u v : State) (d : Fin 3) (a M L lambda : ℝ)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v)
    (ha : 0 ≤ a) (hM : 0 ≤ M)
    (hHupper : ∀ t ∈ Set.Icc (0 : ℝ) 1, ∀ k,
      conservativeHessian (EulerEntropyConvexity.segment u v t) k ≤ M*sizeSquared k)
    (hHlower : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      lambda*sizeSquared (v-u) ≤ conservativeHessian (EulerEntropyConvexity.segment u v t) (v-u))
    (hF : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      sizeSquared (EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d-
        EulerAdmissible.eulerFlux u d) ≤ L^2*sizeSquared (v-u) ∧
      sizeSquared (EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d-
        EulerAdmissible.eulerFlux v d) ≤ L^2*sizeSquared (v-u))
    (hvisc : M*(1+L^2) ≤ a*lambda/2) :
    dot (gradient v-gradient u) (EulerAdmissible.faceFlux u v a d)-
      (v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) ≤
      -(a*lambda/4)*sizeSquared (v-u) := by
  have hcentral := central_entropy_residual u v d M L hu hv hM hHupper hF
  have hmono := gradient_strong_monotonicity u v lambda hu hv hHlower
  have hmult := mul_le_mul_of_nonneg_left hmono (by positivity : 0 ≤ a/2)
  have hmargin := mul_le_mul_of_nonneg_right hvisc (size_nonnegative (v-u))
  have he : dot (gradient v-gradient u) (EulerAdmissible.faceFlux u v a d) =
      dot (gradient v-gradient u) (meanFlux u v d)-(a/2)*dot (gradient v-gradient u) (v-u) := by
    simp only [EulerAdmissible.faceFlux,meanFlux,dot_smul_right,dot_sub_right,dot_add_right]
    ring
  rw [he]
  nlinarith

end EulerFaceEntropy
