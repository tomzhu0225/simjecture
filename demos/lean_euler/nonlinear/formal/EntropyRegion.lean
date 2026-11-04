-- Conditional finite-step theorem for the actual nonlinear method. The region
-- is defined by actual entropy-Hessian and physical-flux bounds; proving the
-- full trajectory stays in such a region remains an explicit obligation.
noncomputable section
namespace EulerEntropyRegion
open EulerEntropy EulerEntropyTaylor EulerEntropyGeometry EulerFaceEntropy
open EulerFiniteVolumeEntropy EulerVectorEstimates EulerEnergyBounds
open scoped BigOperators
abbrev State := Fin 5 → ℝ

structure RegionBounds (K : Set State) (M lambda L : ℝ) : Prop where
  convex : Convex ℝ K
  admissible : ∀ u ∈ K, EulerAdmissible.Admissible u
  hessian_upper : ∀ u ∈ K, ∀ k, conservativeHessian u k ≤ M*sizeSquared k
  hessian_lower : ∀ u ∈ K, ∀ k, lambda*sizeSquared k ≤ conservativeHessian u k
  flux_bound : ∀ u ∈ K, ∀ v ∈ K, ∀ d,
    sizeSquared (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux u d) ≤ L^2*sizeSquared (v-u)

theorem segment_in_region (K : Set State) (hc : Convex ℝ K) (u v : State)
    (hu : u ∈ K) (hv : v ∈ K) (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
    EulerEntropyConvexity.segment u v t ∈ K := by
  rw [EulerEntropyConvexity.segment_mix]
  exact hc hu hv (sub_nonneg.mpr ht.2) ht.1 (by ring)

theorem segment_distance_bounds (u v : State) (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
    sizeSquared (EulerEntropyConvexity.segment u v t-u) ≤ sizeSquared (v-u) ∧
    sizeSquared (EulerEntropyConvexity.segment u v t-v) ≤ sizeSquared (v-u) := by
  have hS := size_nonnegative (v-u)
  have ht2 : t^2 ≤ 1 := by nlinarith [ht.1,ht.2]
  have htm2 : (t-1)^2 ≤ 1 := by nlinarith [ht.1,ht.2]
  have he0 : EulerEntropyConvexity.segment u v t-u=t • (v-u) := by
    simp [EulerEntropyConvexity.segment]
  have he1 : EulerEntropyConvexity.segment u v t-v=(t-1) • (v-u) := by
    funext j
    dsimp [EulerEntropyConvexity.segment]
    ring
  rw [he0,he1,size_smul,size_smul]
  constructor
  · simpa only [one_mul] using mul_le_mul_of_nonneg_right ht2 hS
  · simpa only [one_mul] using mul_le_mul_of_nonneg_right htm2 hS

theorem region_face_entropy (K : Set State) (M lambda L a : ℝ)
    (hK : RegionBounds K M lambda L) (u v : State) (hu : u ∈ K) (hv : v ∈ K)
    (d : Fin 3) (ha : 0 ≤ a) (hM : 0 ≤ M) (hvisc : M*(1+L^2) ≤ a*lambda/2) :
    dot (gradient v-gradient u) (EulerAdmissible.faceFlux u v a d)-
      (v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) ≤ -(a*lambda/4)*sizeSquared (v-u) := by
  have hseg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) := segment_in_region K hK.convex u v hu hv t ht
  apply rusanov_face_entropy_bound u v d a M L lambda (hK.admissible u hu) (hK.admissible v hv)
    ha hM (fun t ht k => hK.hessian_upper _ (hseg t ht) k)
    (fun t ht => hK.hessian_lower _ (hseg t ht) _) _ hvisc
  intro t ht
  obtain ⟨h0,h1⟩ := segment_distance_bounds u v t ht
  constructor
  · exact (hK.flux_bound u hu _ (hseg t ht) d).trans (mul_le_mul_of_nonneg_left h0 (sq_nonneg L))
  · exact (hK.flux_bound v hv _ (hseg t ht) d).trans (mul_le_mul_of_nonneg_left h1 (sq_nonneg L))

theorem nonlinear_step_entropy_from_region {I : Type*} [Fintype I]
    (K : Set State) (M lambda L : ℝ) (hK : RegionBounds K M lambda L)
    (u : I → State) (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio amin A : ℝ)
    (hu : ∀ i, u i ∈ K) (hv : ∀ i, gridUpdate u neighbor a ratio i ∈ K)
    (hr : 0 ≤ ratio) (hM : 0 ≤ M) (hlambda : 0 ≤ lambda) (hamin : 0 ≤ amin)
    (ha : ∀ d, amin ≤ a d) (haA : ∀ d, (a d)^2 ≤ A^2)
    (hvisc : M*(1+L^2) ≤ amin*lambda/2)
    (hstep : 3*M*ratio*(A^2+L^2) ≤ amin*lambda/8) :
    (∑ i, entropy (gridUpdate u neighbor a ratio i)) ≤ (∑ i, entropy (u i))-
      (ratio*amin*lambda/8)*edgeEnergy u neighbor := by
  have hneighbor (i : I) (j : Fin 6) : neighborState u neighbor i j ∈ K := by
    fin_cases j
    all_goals exact hu _
  have hface (d : Fin 3) (i : I) :
      dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)-
      (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩) ≤
        -(amin*lambda/4)*sizeSquared (u (neighbor d i)-u i) := by
    have hb := region_face_entropy K M lambda L (a d) hK (u i) (u (neighbor d i)) (hu i) (hu _)
      d (hamin.trans (ha d)) hM
      (hvisc.trans (by nlinarith [mul_le_mul_of_nonneg_right (ha d) hlambda]))
    have hm := mul_le_mul_of_nonneg_right (ha d) hlambda
    have hs := mul_le_mul_of_nonneg_right hm (size_nonnegative (u (neighbor d i)-u i))
    exact hb.trans (by nlinarith)
  have hH (i : I) (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :=
    hK.hessian_upper _ (segment_in_region K hK.convex _ _ (hu i) (hv i) t ht)
      (gridUpdate u neighbor a ratio i-u i)
  have hb := entropy_step_dissipation u neighbor a ratio A L M (amin*lambda/4) hr hM
    (fun i => hK.admissible _ (hu i)) (fun i => hK.admissible _ (hv i)) haA
    (fun i j d => hK.flux_bound _ (hu i) _ (hneighbor i j) d) hH hface
    (by
      convert hstep using 1
      ring)
  convert hb using 1
  ring

end EulerEntropyRegion
