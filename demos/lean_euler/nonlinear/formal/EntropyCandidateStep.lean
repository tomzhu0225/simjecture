-- Periodic identities for the alternative EC+LF method. The trial parameter
-- scales a residual computed from the same old state throughout a line search.
noncomputable section
namespace EulerEntropyCandidateStep
open EulerEntropy EulerEntropyConservativeFlux EulerVectorEstimates
open scoped BigOperators Topology
abbrev State := Fin 5 → ℝ

def face {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (d : Fin 3) (i : I) : State := esFlux (u i) (u (neighbor d i)) (a d) d

def increment {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (i : I) : State :=
  -(∑ d, (face u neighbor a d i-face u neighbor a d ((neighbor d).symm i)))

def trial {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (ratio : ℝ) (i : I) : State := u i+ratio • increment u neighbor a i

def totalEntropy {I : Type*} [Fintype I] (u : I → State) : ℝ := ∑ i, entropy (u i)

def dissipation {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) : ℝ :=
  ∑ d, ∑ i, (a d/2)*dot (gradient (u (neighbor d i))-gradient (u i)) (u (neighbor d i)-u i)

theorem increment_sum_zero {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) : ∑ i, increment u neighbor a i=0 := by
  have hd (d : Fin 3) : (∑ i, (face u neighbor a d i-face u neighbor a d ((neighbor d).symm i)))=0 := by
    rw [Finset.sum_sub_distrib]
    have hh := Equiv.sum_comp (neighbor d).symm (face u neighbor a d)
    rw [hh,sub_self]
  simp only [increment,Finset.sum_neg_distrib]
  rw [Finset.sum_comm]
  simp only [hd,Finset.sum_const_zero,neg_zero]

theorem trial_conservation {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio : ℝ) :
    ∑ i, trial u neighbor a ratio i=∑ i, u i := by
  simp only [trial,Finset.sum_add_distrib,← Finset.smul_sum,increment_sum_zero,smul_zero,add_zero]

theorem trial_zero {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) : trial u neighbor a 0=u := by
  funext i
  simp [trial]

theorem entropy_residual_pairing {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    (∑ i, dot (gradient (u i)) (increment u neighbor a i)) = -dissipation u neighbor a := by
  have hface (d : Fin 3) (i : I) : dot (gradient (u (neighbor d i))-gradient (u i)) (face u neighbor a d i) =
      (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩)-
      (a d/2)*dot (gradient (u (neighbor d i))-gradient (u i)) (u (neighbor d i)-u i) := by
    have hh := dissipative_entropy_identity (u i) (u (neighbor d i)) (hu i) (hu _) (a d) d
    change dot _ (esFlux (u i) (u (neighbor d i)) (a d) d)=_
    linarith
  have hp (d : Fin 3) : (∑ i, (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩))=0 := by
    rw [Finset.sum_sub_distrib]
    have hh := Equiv.sum_comp (neighbor d) (fun i => u i ⟨d.val+1,by omega⟩)
    rw [hh,sub_self]
  simp only [increment,dot_neg_right,dot_sum_right,Finset.sum_neg_distrib]
  rw [Finset.sum_comm]
  simp only [EulerFiniteVolumeEntropy.periodic_pairing,neg_neg,
    hface,Finset.sum_sub_distrib,hp,zero_sub,dissipation]

theorem dissipation_nonnegative {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 ≤ a d) :
    0 ≤ dissipation u neighbor a := by
  apply Finset.sum_nonneg
  intro d _
  apply Finset.sum_nonneg
  intro i _
  have hh := face_entropy_stable (u i) (u (neighbor d i)) (hu i) (hu _) (a d) (ha d) d
  rw [dissipative_entropy_identity (u i) (u (neighbor d i)) (hu i) (hu _) (a d) d] at hh
  linarith

theorem gradient_strict_monotonicity (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v) (hne : u ≠ v) :
    0 < dot (gradient v-gradient u) (v-u) := by
  let f := fun t => dot (gradient (EulerEntropyConvexity.segment u v t)) (v-u)
  let df := fun t => EulerEntropyTaylor.conservativeHessian (EulerEntropyConvexity.segment u v t) (v-u)
  have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t := by
    have hs := EulerEntropyConvexity.segment_admissible u v hu hv t ht
    exact entropy_second_directional (EulerEntropyConvexity.segment_derivative u v t) hs.1 hs.2
  obtain ⟨c,hc,he⟩ := exists_hasDerivAt_eq_slope f df (by norm_num : (0 : ℝ) < 1)
    (fun t ht => (hd t ht).continuousAt.continuousWithinAt)
    (fun t ht => hd t ⟨ht.1.le,ht.2.le⟩)
  have hs := EulerEntropyConvexity.segment_admissible u v hu hv c ⟨hc.1.le,hc.2.le⟩
  have hk : primitiveD (EulerEntropyConvexity.segment u v c) (v-u) ≠ 0 := by
    intro hz
    have hh := jacobian_primitiveD (EulerEntropyConvexity.segment u v c) (v-u) (ne_of_gt hs.1)
    rw [hz,EulerConservativePrimitive.jacobian_zero] at hh
    exact hne (sub_eq_zero.mp hh.symm).symm
  have hp := hessian_positive (toPrimitive (EulerEntropyConvexity.segment u v c))
    (primitiveD (EulerEntropyConvexity.segment u v c) (v-u))
    (by dsimp [toPrimitive]; exact one_div_pos.mpr hs.1) hs.2 hk
  have hh : 0 < f 1-f 0 := by
    change 0 < df c at hp
    rw [he] at hp
    simpa only [sub_zero,div_one] using hp
  simpa [f,EulerEntropyConvexity.segment,dot_sub_left] using hh

theorem zero_dissipation_neighbors {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d)
    (hD : dissipation u neighbor a=0) : ∀ d i, u (neighbor d i)=u i := by
  have hn (d : Fin 3) (i : I) :
      0 ≤ (a d/2)*dot (gradient (u (neighbor d i))-gradient (u i)) (u (neighbor d i)-u i) := by
    have hh := face_entropy_stable (u i) (u (neighbor d i)) (hu i) (hu _) (a d) (ha d).le d
    rw [dissipative_entropy_identity (u i) (u (neighbor d i)) (hu i) (hu _) (a d) d] at hh
    linarith
  have hd := (Finset.sum_eq_zero_iff_of_nonneg (fun d (_ : d ∈ Finset.univ) =>
    Finset.sum_nonneg (fun i _ => hn d i))).mp hD
  intro d i
  have hi := (Finset.sum_eq_zero_iff_of_nonneg (fun j (_ : j ∈ Finset.univ) => hn d j)).mp
    (hd d (Finset.mem_univ d)) i (Finset.mem_univ i)
  by_contra hne
  have hs := gradient_strict_monotonicity (u i) (u (neighbor d i)) (hu i) (hu _) (Ne.symm hne)
  have hp := mul_pos (div_pos (ha d) (by norm_num : (0 : ℝ) < 2)) hs
  linarith

theorem zero_dissipation_stationary {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d)
    (hD : dissipation u neighbor a=0) (ratio : ℝ) : trial u neighbor a ratio=u := by
  have hn := zero_dissipation_neighbors u neighbor a hu ha hD
  have hf (d : Fin 3) (i : I) : face u neighbor a d i=EulerAdmissible.eulerFlux (u i) d := by
    rw [face,hn d i,dissipative_flux_consistency (u i) (hu i) (a d) d]
  funext i
  have hz (d : Fin 3) : face u neighbor a d i-face u neighbor a d ((neighbor d).symm i)=0 := by
    rw [hf,hf,← hn d ((neighbor d).symm i)]
    simp
  simp only [trial,increment,hz,Finset.sum_const_zero,neg_zero,smul_zero,add_zero]

theorem trial_derivative {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (i : I) :
    HasDerivAt (fun r => trial u neighbor a r i) (increment u neighbor a i) 0 := by
  have hh := (hasDerivAt_const (0 : ℝ) (u i)).add
    ((hasDerivAt_id (0 : ℝ)).smul_const (increment u neighbor a i))
  simpa only [zero_add,one_smul] using hh

theorem total_entropy_trial_derivative {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    HasDerivAt (fun r => totalEntropy (trial u neighbor a r)) (-dissipation u neighbor a) 0 := by
  have hd (i : I) := entropy_derivative (trial_derivative u neighbor a i)
    (by rw [trial_zero]; exact ne_of_gt (hu i).1)
    (by rw [trial_zero]; exact ne_of_gt (hu i).2)
  have hh := HasDerivAt.fun_sum (fun i (_ : i ∈ Finset.univ) => hd i)
  simp only [trial_zero] at hh
  rwa [entropy_residual_pairing u neighbor a hu] at hh

theorem trial_eventually_admissible {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    ∀ᶠ r in 𝓝 (0 : ℝ), ∀ i, EulerAdmissible.Admissible (trial u neighbor a r i) := by
  apply Filter.eventually_all.mpr
  intro i
  have hd := trial_derivative u neighbor a i
  have hr : ∀ᶠ r in 𝓝 (0 : ℝ), 0 < trial u neighbor a r i 0 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hd) 0).continuousAt (by rw [trial_zero]; exact (hu i).1)
  have hp := (pressure_derivative hd (by rw [trial_zero]; exact ne_of_gt (hu i).1)).continuousAt
  have hpp : ∀ᶠ r in 𝓝 (0 : ℝ), 0 < EulerAdmissible.pressure (trial u neighbor a r i) :=
    continuousAt_const.eventually_lt hp (by rw [trial_zero]; exact (hu i).2)
  exact hr.and hpp

-- A positive dissipation rate guarantees acceptable sufficiently small real
-- trial steps. This does not give a uniform timestep or a floating-point cap.
theorem positive_dissipation_small_step {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (hD : 0 < dissipation u neighbor a) :
    ∃ delta : ℝ, 0 < delta ∧ ∀ r, 0 < r → r < delta →
      (∀ i, EulerAdmissible.Admissible (trial u neighbor a r i)) ∧
      totalEntropy (trial u neighbor a r) ≤ totalEntropy u-(r/2)*dissipation u neighbor a := by
  have hd := total_entropy_trial_derivative u neighbor a hu
  have hs := hd.tendsto_slope_zero_right
  have hlimit : -dissipation u neighbor a < -dissipation u neighbor a/2 := by linarith
  have hev := hs.eventually (Iio_mem_nhds hlimit)
  have he : ∀ᶠ r in 𝓝[>] (0 : ℝ),
      totalEntropy (trial u neighbor a r) ≤ totalEntropy u-(r/2)*dissipation u neighbor a := by
    filter_upwards [hev,self_mem_nhdsWithin] with r hr hrpos
    have hq : (totalEntropy (trial u neighbor a r)-totalEntropy u)/r < -dissipation u neighbor a/2 := by
      simpa only [zero_add,trial_zero,smul_eq_mul,div_eq_mul_inv,mul_comm] using hr
    have hh := (div_lt_iff₀ hrpos).mp hq
    linarith
  have hp : ∀ᶠ r in 𝓝[>] (0 : ℝ), ∀ i, EulerAdmissible.Admissible (trial u neighbor a r i) :=
    (trial_eventually_admissible u neighbor a hu).filter_mono nhdsWithin_le_nhds
  obtain ⟨delta,hdelta,hall⟩ := mem_nhdsGT_iff_exists_Ioo_subset.mp (hp.and he)
  exact ⟨delta,hdelta,fun r hr hrd => hall ⟨hr,hrd⟩⟩

-- Exact-real halving terminates at each admissible finite-grid state with
-- positive diffusion coefficients. There is no uniform retry or time bound.
theorem exists_acceptable_halving {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal) :
    ∃ n : ℕ, (∀ i, EulerAdmissible.Admissible (trial u neighbor a (proposal*(1/2)^n) i)) ∧
      totalEntropy (trial u neighbor a (proposal*(1/2)^n)) ≤
        totalEntropy u-(proposal*(1/2)^n/2)*dissipation u neighbor a := by
  have hnonneg := dissipation_nonnegative u neighbor a hu (fun d => (ha d).le)
  rcases eq_or_lt_of_le hnonneg with hz | hp
  · refine ⟨0,?_⟩
    rw [zero_dissipation_stationary u neighbor a hu ha hz.symm,← hz]
    simpa only [mul_zero,sub_zero,le_refl,and_true] using hu
  · obtain ⟨delta,hdelta,hall⟩ := positive_dissipation_small_step u neighbor a hu hp
    obtain ⟨n,hn⟩ := exists_pow_lt_of_lt_one (div_pos hdelta hproposal) (by norm_num : (1/2 : ℝ) < 1)
    have hr : proposal*(1/2 : ℝ)^n < delta := by
      have hh := (lt_div_iff₀ hproposal).mp hn
      simpa only [mul_comm] using hh
    exact ⟨n,hall _ (mul_pos hproposal (pow_pos (by norm_num) n)) hr⟩

-- A mathematical real-arithmetic model of choosing the first accepted trial.
-- This is not a verified floating-point implementation or a uniform cost bound.
def Acceptable {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio : ℝ) : Prop :=
  (∀ i, EulerAdmissible.Admissible (trial u neighbor a ratio i)) ∧
    totalEntropy (trial u neighbor a ratio) ≤ totalEntropy u-(ratio/2)*dissipation u neighbor a

def halvingIndex {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal) : ℕ := by
  classical
  exact Nat.find (exists_acceptable_halving u neighbor a proposal hu ha hproposal)

def acceptedRatio {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal) : ℝ :=
  proposal*(1/2)^halvingIndex u neighbor a proposal hu ha hproposal

theorem backtracked_step {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal) :
    let ratio := acceptedRatio u neighbor a proposal hu ha hproposal
    0 < ratio ∧ Acceptable u neighbor a ratio ∧
      (∑ i, trial u neighbor a ratio i)=∑ i, u i := by
  classical
  dsimp only
  refine ⟨mul_pos hproposal (pow_pos (by norm_num) _),?_,trial_conservation u neighbor a _⟩
  exact Nat.find_spec (exists_acceptable_halving u neighbor a proposal hu ha hproposal)

theorem earlier_trials_rejected {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (proposal : ℝ)
    (hu : ∀ i, EulerAdmissible.Admissible (u i)) (ha : ∀ d, 0 < a d) (hproposal : 0 < proposal)
    (k : ℕ) (hk : k < halvingIndex u neighbor a proposal hu ha hproposal) :
    ¬ Acceptable u neighbor a (proposal*(1/2)^k) := by
  classical
  exact Nat.find_min (exists_acceptable_halving u neighbor a proposal hu ha hproposal) hk

end EulerEntropyCandidateStep
