-- Quantitative entropy loss of the actual periodic EC+LF update. The bridge
-- to continuous Euler accuracy and the trajectory bounds remain obligations.
noncomputable section
namespace EulerEntropyDecay
open EulerEntropy EulerEntropyCandidateStep EulerGridPoincare
open EulerPhysicalRegion EulerEntropyTaylor EulerEnergyBounds EulerVectorEstimates
open scoped BigOperators
abbrev State := Fin 5 → ℝ

theorem uniform_weights_sum {I : Type*} [Fintype I] [Nonempty I] :
    (∑ _i : I, 1/(Fintype.card I : ℝ))=1 := by
  have hn : (Fintype.card I : ℝ) ≠ 0 := by exact_mod_cast Fintype.card_ne_zero
  simp only [Finset.sum_const,Finset.card_univ,nsmul_eq_mul]
  field_simp

theorem mean_in_region {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (hu : ∀ i, u i ∈ region) : meanState u ∈ region := by
  have hh := region_convex.sum_mem
    (fun _i (_ : _i ∈ Finset.univ) => by positivity : ∀ i ∈ Finset.univ, (0 : ℝ) ≤ 1/(Fintype.card I : ℝ))
    (uniform_weights_sum (I := I)) (fun i _ => hu i)
  simpa only [← Finset.smul_sum,meanState] using hh

theorem sum_centered {I : Type*} [Fintype I] [Nonempty I] (u : I → State) :
    (∑ i, (u i-meanState u))=0 := by
  have hn : (Fintype.card I : ℝ) ≠ 0 := by exact_mod_cast Fintype.card_ne_zero
  funext j
  simp only [Finset.sum_apply,Pi.sub_apply,Finset.sum_sub_distrib,Finset.sum_const,
    Finset.card_univ,nsmul_eq_mul,mean_component,scalarMean,Pi.zero_apply]
  field_simp
  ring

theorem mean_conservation {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (r : ℝ) :
    meanState (trial u neighbor a r)=meanState u := by
  simp only [meanState,trial_conservation]

def entropyExcess {I : Type*} [Fintype I] (u : I → State) : ℝ :=
  totalEntropy u-(Fintype.card I : ℝ)*entropy (meanState u)

theorem entropy_excess_nonnegative {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) : 0 ≤ entropyExcess u := by
  have hn : (Fintype.card I : ℝ) ≠ 0 := by exact_mod_cast Fintype.card_ne_zero
  have hconv := EulerEntropyConvexity.entropy_convex_mixture
    (fun _i : I => 1/(Fintype.card I : ℝ)) u (fun _ => by positivity)
    (uniform_weights_sum (I := I)) hu
  simp only [← Finset.smul_sum,← Finset.mul_sum] at hconv
  have hh : (Fintype.card I : ℝ)*entropy (meanState u) ≤ totalEntropy u := by
    calc
      _ ≤ (Fintype.card I : ℝ)*((1/(Fintype.card I : ℝ))*totalEntropy u) :=
        mul_le_mul_of_nonneg_left hconv (Nat.cast_nonneg _)
      _ = _ := by field_simp
  exact sub_nonneg.mpr hh

theorem entropy_excess_upper {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (hu : ∀ i, u i ∈ region) :
    entropyExcess u ≤ 50000*∑ i, sizeSquared (u i-meanState u) := by
  have hm := mean_in_region u hu
  have hi (i : I) := entropy_taylor_upper (meanState u) (u i)
    (region_admissible _ hm) (region_admissible _ (hu i)) 100000
    (fun t ht => hessian_upper_bound _ _
      (EulerEntropyRegion.segment_in_region region region_convex _ _ hm (hu i) t ht))
  have hlin : (∑ i, dot (gradient (meanState u)) (u i-meanState u))=0 := by
    rw [← dot_sum_right,sum_centered]
    simp [dot]
  have hh := Finset.sum_le_sum (fun i (_ : i ∈ Finset.univ) => hi i)
  simp only [Finset.sum_add_distrib,Finset.sum_const,Finset.card_univ,nsmul_eq_mul,
    ← Finset.mul_sum,hlin,add_zero] at hh
  dsimp [entropyExcess,totalEntropy]
  linarith

theorem entropy_excess_poincare (n : ℕ) [NeZero n] (u : Cell n → State)
    (hu : ∀ i, u i ∈ region) :
    entropyExcess u ≤ 75000*(n : ℝ)^2*EulerFiniteVolumeEntropy.edgeEnergy u (neighbors n) := by
  have hh := entropy_excess_upper u hu
  have hp := mul_le_mul_of_nonneg_left (vector_poincare n u) (by norm_num : (0 : ℝ) ≤ 50000)
  linarith

theorem dissipation_controls_edges {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, u i ∈ region) (ha : ∀ d, 1/4 ≤ a d) :
    (1/100000 : ℝ)*EulerFiniteVolumeEntropy.edgeEnergy u neighbor ≤ dissipation u neighbor a := by
  have hi (d : Fin 3) (i : I) :
      (1/100000 : ℝ)*sizeSquared (u (neighbor d i)-u i) ≤
        (a d/2)*dot (gradient (u (neighbor d i))-gradient (u i)) (u (neighbor d i)-u i) := by
    have hmono := EulerFaceEntropy.gradient_strong_monotonicity (u i) (u (neighbor d i)) (1/12500)
      (region_admissible _ (hu i)) (region_admissible _ (hu _))
      (fun t ht => hessian_coercivity _ _
        (EulerEntropyRegion.segment_in_region region region_convex _ _ (hu i) (hu _) t ht))
    have hmult := mul_le_mul_of_nonneg_left hmono (by linarith [ha d] : 0 ≤ a d/2)
    have hcoeff := mul_le_mul_of_nonneg_right (ha d) (size_nonnegative (u (neighbor d i)-u i))
    nlinarith
  have hh := Finset.sum_le_sum (fun d (_ : d ∈ Finset.univ) =>
    Finset.sum_le_sum (fun i (_ : i ∈ Finset.univ) => hi d i))
  simpa only [EulerFiniteVolumeEntropy.edgeEnergy,dissipation,← Finset.mul_sum] using hh

theorem region_wave_speed_lower (u : State) (hu : u ∈ region) (d : Fin 3) :
    (1/4 : ℝ) ≤ EulerAdmissible.waveSpeed u d := by
  have hphys := region_admissible u hu
  have hQ : (1/8 : ℝ) ≤ 2*EulerAdmissible.pressure u/u 0 := by
    apply (le_div_iff₀ hphys.1).mpr
    linarith [hu.2.1,hu.2.2.2]
  have hQpos : 0 ≤ 2*EulerAdmissible.pressure u/u 0 := by positivity
  have hs := Real.sq_sqrt hQpos
  have hc : (1/4 : ℝ) ≤ Real.sqrt (2*EulerAdmissible.pressure u/u 0) := by
    nlinarith [Real.sqrt_nonneg (2*EulerAdmissible.pressure u/u 0)]
  dsimp [EulerAdmissible.waveSpeed]
  linarith [abs_nonneg (EulerAdmissible.fromVelocity u d)]

theorem computed_speed_lower {I : Type*} [Fintype I] [Nonempty I] (u : I → State)
    (hu : ∀ i, u i ∈ region) (d : Fin 3) : (1/4 : ℝ) ≤ EulerAdmissible.globalSpeed u d := by
  obtain ⟨i⟩ := ‹Nonempty I›
  exact (region_wave_speed_lower (u i) (hu i) d).trans (EulerAdmissible.globalSpeed_bound u d i)

theorem accepted_step_decay (n : ℕ) [NeZero n] (u : Cell n → State)
    (a : Fin 3 → ℝ) (r : ℝ) (hu : ∀ i, u i ∈ region) (ha : ∀ d, 1/4 ≤ a d)
    (hr : 0 ≤ r) (haccept : Acceptable u (neighbors n) a r) :
    r*entropyExcess u ≤ 15000000000*(n : ℝ)^2*
      (entropyExcess u-entropyExcess (trial u (neighbors n) a r)) := by
  have hR := entropy_excess_poincare n u hu
  have hD := dissipation_controls_edges u (neighbors n) a hu ha
  have hmult := mul_le_mul_of_nonneg_left hD (by positivity : 0 ≤ 7500000000*(n : ℝ)^2)
  have hbudget : entropyExcess u ≤ 7500000000*(n : ℝ)^2*dissipation u (neighbors n) a := by
    nlinarith only [hR,hmult]
  have htime := mul_le_mul_of_nonneg_left hbudget hr
  have hdrop : (r/2)*dissipation u (neighbors n) a ≤
      entropyExcess u-entropyExcess (trial u (neighbors n) a r) := by
    simp only [entropyExcess,mean_conservation]
    linarith [haccept.2]
  have hdropmult := mul_le_mul_of_nonneg_left hdrop (by positivity : 0 ≤ 15000000000*(n : ℝ)^2)
  nlinarith only [htime,hdropmult]

theorem backtracked_step_decay (n : ℕ) [NeZero n] (u : Cell n → State)
    (a : Fin 3 → ℝ) (proposal : ℝ) (hu : ∀ i, u i ∈ region)
    (ha : ∀ d, 1/4 ≤ a d) (hproposal : 0 < proposal) :
    let hphys := fun i => region_admissible (u i) (hu i)
    let hapos := fun d => lt_of_lt_of_le (by norm_num : (0 : ℝ) < 1/4) (ha d)
    let r := acceptedRatio u (neighbors n) a proposal hphys hapos hproposal
    r*entropyExcess u ≤ 15000000000*(n : ℝ)^2*
      (entropyExcess u-entropyExcess (trial u (neighbors n) a r)) := by
  dsimp only
  have hh := backtracked_step u (neighbors n) a proposal
    (fun i => region_admissible (u i) (hu i))
    (fun d => lt_of_lt_of_le (by norm_num : (0 : ℝ) < 1/4) (ha d)) hproposal
  exact accepted_step_decay n u a _ hu ha hh.1.le hh.2.1

theorem scalar_trace_loss (R r : ℕ → ℝ) (m : ℕ) (C : ℝ)
    (hr : ∀ k < m, 0 ≤ r k) (hmono : ∀ k < m, R (k+1) ≤ R k)
    (hstep : ∀ k < m, r k*R k ≤ C*(R k-R (k+1))) :
    (∑ k ∈ Finset.range m, r k)*R m ≤ C*(R 0-R m) := by
  have hc : Antitone (fun k => R (min k m)) := by
    apply antitone_nat_of_succ_le
    intro k
    by_cases hk : k < m
    · simpa only [Nat.min_eq_left (by omega : k+1 ≤ m),Nat.min_eq_left (by omega : k ≤ m)] using hmono k hk
    · simp only [Nat.min_eq_right (by omega : m ≤ k+1),Nat.min_eq_right (by omega : m ≤ k),le_refl]
  have hpoint (k : ℕ) (hk : k ∈ Finset.range m) : r k*R m ≤ C*(R k-R (k+1)) := by
    have hkm := Finset.mem_range.mp hk
    have hR : R m ≤ R k := by
      simpa only [Nat.min_self,Nat.min_eq_left hkm.le] using hc hkm.le
    exact (mul_le_mul_of_nonneg_left hR (hr k hkm)).trans (hstep k hkm)
  have hh := Finset.sum_le_sum hpoint
  rw [← Finset.sum_mul,← Finset.mul_sum,Finset.sum_range_sub'] at hh
  exact hh

theorem trace_mean_conservation {I : Type*} [Fintype I] (u : ℕ → I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : ℕ → Fin 3 → ℝ) (r : ℕ → ℝ) (m : ℕ)
    (hupdate : ∀ k < m, u (k+1)=trial (u k) neighbor (a k) (r k)) :
    meanState (u m)=meanState (u 0) := by
  have hi (k : ℕ) (hk : k ≤ m) : meanState (u k)=meanState (u 0) := by
    induction k with
    | zero => rfl
    | succ k ih =>
      rw [hupdate k (by omega),mean_conservation]
      exact ih (by omega)
  exact hi m le_rfl

theorem actual_trace_entropy_loss (n : ℕ) [NeZero n] (u : ℕ → Cell n → State)
    (a : ℕ → Fin 3 → ℝ) (r : ℕ → ℝ) (m : ℕ)
    (hupdate : ∀ k < m, u (k+1)=trial (u k) (neighbors n) (a k) (r k))
    (hu : ∀ k < m, ∀ i, u k i ∈ region) (ha : ∀ k < m, ∀ d, 1/4 ≤ a k d)
    (hr : ∀ k < m, 0 ≤ r k) (haccept : ∀ k < m, Acceptable (u k) (neighbors n) (a k) (r k)) :
    (∑ k ∈ Finset.range m, r k)*entropyExcess (u m) ≤
      15000000000*(n : ℝ)^2*(totalEntropy (u 0)-totalEntropy (u m)) := by
  have hstep (k : ℕ) (hk : k < m) := accepted_step_decay n (u k) (a k) (r k)
    (hu k hk) (ha k hk) (hr k hk) (haccept k hk)
  have hmono (k : ℕ) (hk : k < m) : entropyExcess (u (k+1)) ≤ entropyExcess (u k) := by
    rw [hupdate k hk]
    have hD := dissipation_nonnegative (u k) (neighbors n) (a k)
      (fun i => region_admissible _ (hu k hk i)) (fun d => by linarith [ha k hk d])
    have htime := mul_nonneg (hr k hk) hD
    simp only [entropyExcess,mean_conservation]
    linarith [(haccept k hk).2]
  have hh := scalar_trace_loss (fun k => entropyExcess (u k)) r m (15000000000*(n : ℝ)^2)
    hr hmono (fun k hk => by dsimp only; rw [hupdate k hk]; exact hstep k hk)
  dsimp only at hh
  have hm := trace_mean_conservation u (neighbors n) a r m hupdate
  have he : entropyExcess (u 0)-entropyExcess (u m)=totalEntropy (u 0)-totalEntropy (u m) := by
    simp only [entropyExcess,hm]
    ring
  rwa [he] at hh

theorem physical_time_entropy_loss (n : ℕ) [NeZero n] (u : ℕ → Cell n → State)
    (a : ℕ → Fin 3 → ℝ) (r : ℕ → ℝ) (m : ℕ) (T : ℝ)
    (hupdate : ∀ k < m, u (k+1)=trial (u k) (neighbors n) (a k) (r k))
    (hu : ∀ k < m, ∀ i, u k i ∈ region) (ha : ∀ k < m, ∀ d, 1/4 ≤ a k d)
    (hr : ∀ k < m, 0 ≤ r k) (haccept : ∀ k < m, Acceptable (u k) (neighbors n) (a k) (r k))
    (hT : (2*Real.pi/(n : ℝ))*(∑ k ∈ Finset.range m, r k)=T) :
    T*entropyExcess (u m) ≤
      (30000000000*Real.pi*(n : ℝ))*(totalEntropy (u 0)-totalEntropy (u m)) := by
  have hn : (n : ℝ) ≠ 0 := by exact_mod_cast (NeZero.ne n)
  have hh := actual_trace_entropy_loss n u a r m hupdate hu ha hr haccept
  have hs := mul_le_mul_of_nonneg_left hh (by positivity : 0 ≤ 2*Real.pi/(n : ℝ))
  calc
    _ = (2*Real.pi/(n : ℝ))*((∑ k ∈ Finset.range m, r k)*entropyExcess (u m)) := by rw [← hT]; ring
    _ ≤ _ := hs
    _ = _ := by field_simp; ring

theorem computed_trace_entropy_loss (n : ℕ) [NeZero n] (u : ℕ → Cell n → State)
    (r : ℕ → ℝ) (m : ℕ) (T : ℝ)
    (hupdate : ∀ k < m, u (k+1)=trial (u k) (neighbors n) (EulerAdmissible.globalSpeed (u k)) (r k))
    (hu : ∀ k < m, ∀ i, u k i ∈ region) (hr : ∀ k < m, 0 ≤ r k)
    (haccept : ∀ k < m, Acceptable (u k) (neighbors n) (EulerAdmissible.globalSpeed (u k)) (r k))
    (hT : (2*Real.pi/(n : ℝ))*(∑ k ∈ Finset.range m, r k)=T) :
    T*entropyExcess (u m) ≤
      (30000000000*Real.pi*(n : ℝ))*(totalEntropy (u 0)-totalEntropy (u m)) := by
  exact physical_time_entropy_loss n u (fun k => EulerAdmissible.globalSpeed (u k)) r m T hupdate hu
    (fun k hk => computed_speed_lower (u k) (hu k hk)) hr haccept hT

end EulerEntropyDecay
