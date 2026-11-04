import Mathlib.MeasureTheory.Integral.DivergenceTheorem

-- Global entropy balance for an actual differentiable periodic Euler field.
-- Existence of such a field for the target family is a separate obligation.
noncomputable section
namespace EulerEntropyIntegral
open EulerEntropy EulerEntropyDynamics EulerPhysicalFluxBounds EulerVectorEstimates
open scoped BigOperators
abbrev State := Fin 5 → ℝ
abbrev Space := Fin 3 → ℝ
abbrev Point := Fin 4 → ℝ

theorem entropy_flux_pairing (u k : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    dot (gradient u) (fluxD u k d)=dot (gradient u) k*normalVelocity u d+
      entropy u*normalVelocityD u k d := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  fin_cases d
  all_goals dsimp [dot,gradient,fluxD,normalVelocity,normalVelocityD,normalShift,pressureD,entropy]
  all_goals field_simp
  all_goals dsimp [EulerAdmissible.pressure]
  all_goals field_simp
  all_goals ring

theorem entropy_flux_hasDerivAt {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hphys : EulerAdmissible.Admissible (u t)) (d : Fin 3) :
    HasDerivAt (fun s => entropyFlux (u s) d) (dot (gradient (u t)) (fluxD (u t) k d)) t := by
  have he := entropy_derivative hu (ne_of_gt hphys.1) (ne_of_gt hphys.2)
  have hv := normal_velocity_derivative hu (ne_of_gt hphys.1) d
  rw [entropy_flux_pairing (u t) k hphys d]
  exact he.mul hv

theorem pressure_differentiable (u : State) (hu : u 0 ≠ 0) :
    DifferentiableAt ℝ EulerAdmissible.pressure u := by
  have he (j : Fin 5) : DifferentiableAt ℝ (fun v : State => v j) u := by fun_prop
  have hnum := (((he 1).pow 2).add ((he 2).pow 2)).add ((he 3).pow 2)
  have hden := ((he 0).const_mul 2).inv (mul_ne_zero (by norm_num : (2 : ℝ) ≠ 0) hu)
  have hquot : DifferentiableAt ℝ (fun v : State => (v 1^2+v 2^2+v 3^2)/(2*v 0)) u := by
    simpa only [div_eq_mul_inv] using hnum.mul hden
  exact (he 4).sub hquot

theorem entropy_differentiable (u : State) (hu : EulerAdmissible.Admissible u) :
    DifferentiableAt ℝ entropy u := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  have hpr := pressure_differentiable u hr
  have he : DifferentiableAt ℝ (fun v : State => v 0) u := by fun_prop
  exact he.neg.mul ((hpr.log hp).sub ((he.log hr).const_mul 2))

theorem entropy_flux_differentiable (u : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    DifferentiableAt ℝ (fun v => entropyFlux v d) u := by
  have hr := ne_of_gt hu.1
  have he := entropy_differentiable u hu
  have hm : DifferentiableAt ℝ (fun v : State => v ⟨d.val+1,by omega⟩) u := by fun_prop
  have hrho : DifferentiableAt ℝ (fun v : State => v 0) u := by fun_prop
  simpa only [entropyFlux,div_eq_mul_inv] using he.mul (hm.mul (hrho.inv hr))

theorem physical_flux_differentiable (u : State) (hu : u 0 ≠ 0) (d : Fin 3) :
    DifferentiableAt ℝ (fun v => EulerAdmissible.eulerFlux v d) u := by
  have hp := pressure_differentiable u hu
  have he (j : Fin 5) : DifferentiableAt ℝ (fun v : State => v j) u := by fun_prop
  have hv : DifferentiableAt ℝ (fun v : State => v ⟨d.val+1,by omega⟩/v 0) u := by
    simpa only [div_eq_mul_inv] using (he ⟨d.val+1,by omega⟩).mul ((he 0).inv hu)
  have hif (j : Fin 3) : DifferentiableAt ℝ (fun v : State => if d=j then EulerAdmissible.pressure v else 0) u := by
    by_cases hd : d=j
    · simpa only [hd,if_true] using hp
    · simp only [hd,if_false]
      exact differentiableAt_const (0 : ℝ)
  apply differentiableAt_pi.mpr
  intro j
  fin_cases j
  · exact he ⟨d.val+1,by omega⟩
  · exact ((he 1).mul hv).add (hif 0)
  · exact ((he 2).mul hv).add (hif 1)
  · exact ((he 3).mul hv).add (hif 2)
  · exact ((he 4).add hp).mul hv

def unit (i : Fin 4) : Point := Pi.single i 1
def line (x v : Point) (s : ℝ) : Point := x+s • v

theorem line_zero (x v : Point) : line x v 0=x := by simp [line]

theorem line_hasDerivAt (x v : Point) : HasDerivAt (line x v) v 0 := by
  simpa only [zero_add,one_smul] using
    (hasDerivAt_const (0 : ℝ) x).add ((hasDerivAt_id (0 : ℝ)).smul_const v)

theorem field_line_derivative (U : Point → State) (x v : Point) (hU : DifferentiableAt ℝ U x) :
    HasDerivAt (fun s => U (line x v s)) ((fderiv ℝ U x) v) 0 := by
  exact hU.hasFDerivAt.comp_hasDerivAt_of_eq 0 (line_hasDerivAt x v) (line_zero x v).symm

def current (i : Fin 4) (u : State) : ℝ := Fin.cases (entropy u) (fun d => entropyFlux u d) i

theorem current_differentiable (i : Fin 4) (u : State) (hu : EulerAdmissible.Admissible u) :
    DifferentiableAt ℝ (current i) u := by
  refine Fin.cases ?_ (fun d => ?_) i
  · exact entropy_differentiable u hu
  · exact entropy_flux_differentiable u hu d

theorem entropy_directional (U : Point → State) (x v : Point)
    (hU : DifferentiableAt ℝ U x) (hu : EulerAdmissible.Admissible (U x)) :
    (fderiv ℝ (fun z => entropy (U z)) x) v=dot (gradient (U x)) ((fderiv ℝ U x) v) := by
  have hline := field_line_derivative U x v hU
  have hadm : EulerAdmissible.Admissible (U (line x v 0)) := by rwa [line_zero]
  have he := entropy_derivative hline (ne_of_gt hadm.1) (ne_of_gt hadm.2)
  have hf := ((entropy_differentiable (U x) hu).comp x hU).hasFDerivAt.comp_hasDerivAt_of_eq 0
    (line_hasDerivAt x v) (line_zero x v).symm
  have hh := hf.unique he
  simpa only [line_zero] using hh

theorem entropy_flux_directional (U : Point → State) (x v : Point)
    (hU : DifferentiableAt ℝ U x) (hu : EulerAdmissible.Admissible (U x)) (d : Fin 3) :
    (fderiv ℝ (fun z => entropyFlux (U z) d) x) v=
      dot (gradient (U x)) (fluxD (U x) ((fderiv ℝ U x) v) d) := by
  have hline := field_line_derivative U x v hU
  have hadm : EulerAdmissible.Admissible (U (line x v 0)) := by rwa [line_zero]
  have he := entropy_flux_hasDerivAt hline hadm d
  have hf := ((entropy_flux_differentiable (U x) hu d).comp x hU).hasFDerivAt.comp_hasDerivAt_of_eq 0
    (line_hasDerivAt x v) (line_zero x v).symm
  have hh := hf.unique he
  simpa only [line_zero] using hh

theorem physical_flux_directional (U : Point → State) (x v : Point)
    (hU : DifferentiableAt ℝ U x) (hu : EulerAdmissible.Admissible (U x)) (d : Fin 3) :
    (fderiv ℝ (fun z => EulerAdmissible.eulerFlux (U z) d) x) v=
      fluxD (U x) ((fderiv ℝ U x) v) d := by
  have hline := field_line_derivative U x v hU
  have hr : U (line x v 0) 0 ≠ 0 := by rw [line_zero]; exact ne_of_gt hu.1
  have he := flux_derivative hline hr d
  have hf := ((physical_flux_differentiable (U x) (ne_of_gt hu.1) d).comp x hU).hasFDerivAt.comp_hasDerivAt_of_eq 0
    (line_hasDerivAt x v) (line_zero x v).symm
  have hh := hf.unique he
  simpa only [line_zero] using hh

def eulerResidual (U : Point → State) (x : Point) : State :=
  (fderiv ℝ U x) (unit 0)+
    ∑ d : Fin 3, (fderiv ℝ (fun z => EulerAdmissible.eulerFlux (U z) d) x) (unit d.succ)

theorem entropy_divergence_zero (U : Point → State) (x : Point)
    (hU : DifferentiableAt ℝ U x) (hu : EulerAdmissible.Admissible (U x))
    (heuler : eulerResidual U x=0) :
    (∑ i : Fin 4, (fderiv ℝ (fun z => current i (U z)) x) (unit i))=0 := by
  have he := congrArg (dot (gradient (U x))) heuler
  simp only [eulerResidual,dot_add_right,dot_sum_right,physical_flux_directional U x _ hU hu] at he
  rw [Fin.sum_univ_succ]
  simp only [current,Fin.cases_zero,Fin.cases_succ,entropy_directional U x _ hU hu,
    entropy_flux_directional U x _ hU hu]
  simpa only [dot,Pi.zero_apply,mul_zero,add_zero] using he

open MeasureTheory

def lower : Point := fun _ => 0
def upper (T L : ℝ) : Point := Fin.cons T (fun _ : Fin 3 => L)
def box (T L : ℝ) : Set Point := Set.Icc lower (upper T L)
def cube (L : ℝ) : Set Space := Set.Icc (fun _ => 0) (fun _ => L)
def faceDomain (T L : ℝ) (i : Fin 4) : Set Space :=
  Set.Icc (lower ∘ i.succAbove) (upper T L ∘ i.succAbove)

theorem time_face_domain (T L : ℝ) : faceDomain T L 0=cube L := by rfl

theorem box_order (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L) : lower ≤ upper T L := by
  intro i
  refine Fin.cases ?_ (fun _ => ?_) i
  · exact hT
  · exact hL

theorem interior_box_subset (T L : ℝ) :
    (Set.pi Set.univ (fun i => Set.Ioo (lower i) (upper T L i))) ⊆ box T L := by
  intro x hx
  exact ⟨fun i => (hx i (Set.mem_univ i)).1.le,fun i => (hx i (Set.mem_univ i)).2.le⟩

theorem periodic_face_balance {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L)
    (f : Fin 4 → Point → E) (df : Fin 4 → Point → Point →L[ℝ] E)
    (hd : ∀ x ∈ box T L, ∀ i, HasFDerivAt (f i) (df i x) x)
    (hdiv : ∀ x ∈ box T L, (∑ i, df i x (unit i))=0)
    (hper : ∀ i : Fin 4, i ≠ 0 → ∀ y ∈ faceDomain T L i,
      f i (i.insertNth (upper T L i) y)=f i (i.insertNth (lower i) y)) :
    (∫ y in cube L, f 0 (Fin.cons T y))=(∫ y in cube L, f 0 (Fin.cons 0 y)) := by
  have hzero : (fun x => ∑ i, df i x (unit i)) =ᵐ[(volume : Measure Point).restrict (box T L)]
      (fun _ => (0 : E)) := by
    filter_upwards [ae_restrict_mem (measurableSet_Icc : MeasurableSet (box T L))] with x hx
    exact hdiv x hx
  have hi : IntegrableOn (fun x => ∑ i, df i x (unit i)) (box T L) :=
    (integrable_zero Point E (volume.restrict (box T L))).congr hzero.symm
  have hg := integral_divergence_of_hasFDerivAt_off_countable' lower (upper T L) (box_order T L hT hL)
    f df ∅ Set.countable_empty
    (fun i x hx => (hd x hx i).continuousAt.continuousWithinAt)
    (fun x hx i => hd x (interior_box_subset T L hx.1) i) hi
  have hz : (∫ x in box T L, ∑ i, df i x (unit i))=0 := by
    calc
      _ = ∫ _x : Point, (0 : E) ∂(volume.restrict (box T L)) := integral_congr_ae hzero
      _ = _ := by simp
  have hface (i : Fin 4) (hi : i ≠ 0) :
      ((∫ y in faceDomain T L i, f i (i.insertNth (upper T L i) y))-
        ∫ y in faceDomain T L i, f i (i.insertNth (lower i) y))=0 := by
    apply sub_eq_zero.mpr
    exact setIntegral_congr_fun measurableSet_Icc (hper i hi)
  have hsum : (∑ i : Fin 4,
      ((∫ y in faceDomain T L i, f i (i.insertNth (upper T L i) y))-
        ∫ y in faceDomain T L i, f i (i.insertNth (lower i) y))) =
      (∫ y in faceDomain T L 0, f 0 ((0 : Fin 4).insertNth (upper T L 0) y))-
        ∫ y in faceDomain T L 0, f 0 ((0 : Fin 4).insertNth (lower 0) y) := by
    exact Finset.sum_eq_single 0 (fun i _ hi => hface i hi)
      (fun hnot => False.elim (hnot (Finset.mem_univ 0)))
  change (∫ x in box T L, ∑ i, df i x (unit i))=
    ∑ i : Fin 4, ((∫ y in faceDomain T L i, f i (i.insertNth (upper T L i) y))-
      ∫ y in faceDomain T L i, f i (i.insertNth (lower i) y)) at hg
  rw [hz,hsum] at hg
  have hh : (0 : E)=(∫ y in cube L, f 0 (Fin.cons T y))-(∫ y in cube L, f 0 (Fin.cons 0 y)) := by
    simpa only [time_face_domain,upper,lower,Fin.cons_zero,Fin.insertNth_zero'] using hg
  exact sub_eq_zero.mp hh.symm

def PeriodicBoundary (U : Point → State) (T L : ℝ) : Prop :=
  ∀ i : Fin 4, i ≠ 0 → ∀ y ∈ faceDomain T L i,
    U (i.insertNth (upper T L i) y)=U (i.insertNth (lower i) y)

theorem periodic_entropy_conservation (U : Point → State) (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L) :
    (∫ y in cube L, entropy (U (Fin.cons T y)))=(∫ y in cube L, entropy (U (Fin.cons 0 y))) := by
  apply periodic_face_balance T L hT hL (fun i x => current i (U x))
    (fun i x => fderiv ℝ (fun z => current i (U z)) x)
  · intro x hx i
    exact ((current_differentiable i (U x) (hphys x hx)).comp x (hU x hx)).hasFDerivAt
  · intro x hx
    exact entropy_divergence_zero U x (hU x hx) (hphys x hx) (heuler x hx)
  · intro i hi y hy
    exact congrArg (current i) (hperiodic i hi y hy)

def conservedCurrent (i : Fin 4) (u : State) : State := Fin.cases u (fun d => EulerAdmissible.eulerFlux u d) i

theorem conserved_current_differentiable (i : Fin 4) (u : State) (hu : EulerAdmissible.Admissible u) :
    DifferentiableAt ℝ (conservedCurrent i) u := by
  refine Fin.cases ?_ (fun d => ?_) i
  · exact differentiableAt_id
  · exact physical_flux_differentiable u (ne_of_gt hu.1) d

theorem periodic_conserved_integral (U : Point → State) (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L) :
    (∫ y in cube L, U (Fin.cons T y))=(∫ y in cube L, U (Fin.cons 0 y)) := by
  apply periodic_face_balance T L hT hL (fun i x => conservedCurrent i (U x))
    (fun i x => fderiv ℝ (fun z => conservedCurrent i (U z)) x)
  · intro x hx i
    exact ((conserved_current_differentiable i (U x) (hphys x hx)).comp x (hU x hx)).hasFDerivAt
  · intro x hx
    simpa only [Fin.sum_univ_succ,conservedCurrent,Fin.cases_zero,Fin.cases_succ,eulerResidual] using heuler x hx
  · intro i hi y hy
    exact congrArg (conservedCurrent i) (hperiodic i hi y hy)

-- The error contract uses volume normalized by the physical cube's volume.
def cubeMeasure (L : ℝ) : Measure Space :=
  ENNReal.ofReal (1/L^3) • (volume.restrict (cube L))

theorem cube_volume (L : ℝ) (hL : 0 ≤ L) : volume (cube L)=ENNReal.ofReal (L^3) := by
  simp only [cube,Real.volume_Icc_pi,sub_zero,Finset.prod_const,Finset.card_univ,Fintype.card_fin]
  exact (ENNReal.ofReal_pow hL 3).symm

theorem cube_measure_univ (L : ℝ) (hL : 0 < L) : cubeMeasure L Set.univ=1 := by
  rw [cubeMeasure,Measure.smul_apply,Measure.restrict_apply_univ,cube_volume L hL.le]
  change ENNReal.ofReal (1/L^3)*ENNReal.ofReal (L^3)=1
  rw [← ENNReal.ofReal_mul (by positivity : 0 ≤ 1/L^3)]
  simp [ne_of_gt hL]

theorem cube_integral {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    (L : ℝ) (hL : 0 ≤ L) (f : Space → E) :
    (∫ y, f y ∂cubeMeasure L)=(1/L^3) • (∫ y in cube L, f y) := by
  rw [cubeMeasure,integral_smul_measure,ENNReal.toReal_ofReal (by positivity : 0 ≤ 1/L^3)]

theorem normalized_entropy_conservation (U : Point → State) (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L) :
    (∫ y, entropy (U (Fin.cons T y)) ∂cubeMeasure L)=
      (∫ y, entropy (U (Fin.cons 0 y)) ∂cubeMeasure L) := by
  rw [cube_integral L hL,cube_integral L hL,
    periodic_entropy_conservation U T L hT hL hU hphys heuler hperiodic]

theorem normalized_conserved_integral (U : Point → State) (T L : ℝ) (hT : 0 ≤ T) (hL : 0 ≤ L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L) :
    (∫ y, U (Fin.cons T y) ∂cubeMeasure L)=(∫ y, U (Fin.cons 0 y) ∂cubeMeasure L) := by
  rw [cube_integral L hL,cube_integral L hL,
    periodic_conserved_integral U T L hT hL hU hphys heuler hperiodic]

open EulerPhysicalRegion EulerEntropyError

theorem integrated_entropy_error_ae {X : Type*} [MeasurableSpace X] (mu : Measure X) (u v : X → State)
    (hu : ∀ᵐ x ∂mu, u x ∈ region) (hv : ∀ᵐ x ∂mu, v x ∈ region)
    (hEu : Integrable (fun x => entropy (u x)) mu) (hEv : Integrable (fun x => entropy (v x)) mu)
    (herr : ∀ j, Integrable (fun x => |v x j-u x j|) mu) :
    |(∫ x, entropy (v x) ∂mu)-(∫ x, entropy (u x) ∂mu)| ≤
      32*∑ j, ∫ x, |v x j-u x j| ∂mu := by
  have hi : Integrable (fun x => ∑ j : Fin 5, |v x j-u x j|) mu :=
    integrable_finset_sum Finset.univ (fun j _ => herr j)
  have hpoint : (fun x => |entropy (v x)-entropy (u x)|) ≤ᵐ[mu]
      (fun x => 32*(∑ j : Fin 5, |v x j-u x j|)) := by
    filter_upwards [hu,hv] with x hux hvx
    exact entropy_lipschitz (u x) (v x) hux hvx
  rw [← integral_sub hEv hEu]
  calc
    _ ≤ ∫ x, |entropy (v x)-entropy (u x)| ∂mu := abs_integral_le_integral_abs
    _ ≤ ∫ x, 32*(∑ j : Fin 5, |v x j-u x j|) ∂mu :=
      integral_mono_ae (hEv.sub hEu).abs (hi.const_mul 32) hpoint
    _ = _ := by rw [integral_const_mul,integral_finset_sum Finset.univ (fun j _ => herr j)]

theorem entropy_gap_error_lower_bound_ae {X : Type*} [MeasurableSpace X] (mu : Measure X)
    (u v : X → State) (hu : ∀ᵐ x ∂mu, u x ∈ region) (hv : ∀ᵐ x ∂mu, v x ∈ region)
    (hEu : Integrable (fun x => entropy (u x)) mu) (hEv : Integrable (fun x => entropy (v x)) mu)
    (herr : ∀ j, Integrable (fun x => |v x j-u x j|) mu) :
    |(∫ x, entropy (v x) ∂mu)-(∫ x, entropy (u x) ∂mu)|/160 ≤ maxComponentError mu u v := by
  have hh := integrated_entropy_error_ae mu u v hu hv hEu hEv herr
  have hj (j : Fin 5) : (∫ x, |v x j-u x j| ∂mu) ≤ maxComponentError mu u v :=
    Finset.le_sup' (f := fun j : Fin 5 => ∫ x, |v x j-u x j| ∂mu) (Finset.mem_univ j)
  have hs := Finset.sum_le_sum (fun j (_ : j ∈ Finset.univ) => hj j)
  simp only [Finset.sum_const,Finset.card_univ,Fintype.card_fin,nsmul_eq_mul] at hs
  norm_num only [Nat.cast_ofNat] at hs
  apply (div_le_iff₀ (by norm_num : (0 : ℝ) < 160)).mpr
  linarith

theorem cube_ae_mem (L : ℝ) : ∀ᵐ y ∂cubeMeasure L, y ∈ cube L :=
  Measure.ae_smul_measure (ae_restrict_mem (measurableSet_Icc : MeasurableSet (cube L))) _

theorem cube_integrable {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E] [CompleteSpace E]
    (L : ℝ) (f : Space → E) (hf : ContinuousOn f (cube L)) : Integrable f (cubeMeasure L) := by
  exact (hf.integrableOn_compact isCompact_Icc).smul_measure ENNReal.ofReal_ne_top

theorem entropy_continuousOn (L : ℝ) (u : Space → State)
    (hc : ContinuousOn u (cube L)) (hu : ∀ x ∈ cube L, u x ∈ region) :
    ContinuousOn (fun x => entropy (u x)) (cube L) := by
  intro x hx
  exact (entropy_differentiable (u x) (region_admissible _ (hu x hx))).continuousAt.comp_continuousWithinAt (hc x hx)

theorem normalized_error_lower_bound (L : ℝ) (u v : Space → State)
    (hcu : ContinuousOn u (cube L)) (hcv : ContinuousOn v (cube L))
    (hu : ∀ x ∈ cube L, u x ∈ region) (hv : ∀ x ∈ cube L, v x ∈ region) :
    |(∫ x, entropy (v x) ∂cubeMeasure L)-(∫ x, entropy (u x) ∂cubeMeasure L)|/160 ≤
      maxComponentError (cubeMeasure L) u v := by
  have huae : ∀ᵐ x ∂cubeMeasure L, u x ∈ region := (cube_ae_mem L).mono (fun x hx => hu x hx)
  have hvae : ∀ᵐ x ∂cubeMeasure L, v x ∈ region := (cube_ae_mem L).mono (fun x hx => hv x hx)
  apply entropy_gap_error_lower_bound_ae (cubeMeasure L) u v huae hvae
    (cube_integrable L _ (entropy_continuousOn L u hcu hu))
    (cube_integrable L _ (entropy_continuousOn L v hcv hv))
  intro j
  apply cube_integrable
  exact ((continuous_apply j).continuousOn.comp hcv (fun _ _ => Set.mem_univ _)).sub
    ((continuous_apply j).continuousOn.comp hcu (fun _ _ => Set.mem_univ _)) |>.abs

theorem slice_mem_box (T L t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) T) (y : Space) (hy : y ∈ cube L) :
    Fin.cons t y ∈ box T L := by
  constructor
  · intro i
    exact Fin.cases ht.1 (fun d => hy.1 d) i
  · intro i
    exact Fin.cases ht.2 (fun d => hy.2 d) i

theorem slice_continuousOn (U : Point → State) (T L t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) T)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x) :
    ContinuousOn (fun y => U (Fin.cons t y)) (cube L) := by
  intro y hy
  have hc : ContinuousAt (fun z : Space => Fin.cons t z : Space → Point) y := by
    apply continuousAt_pi.mpr
    intro i
    refine Fin.cases ?_ (fun d => ?_) i
    · exact continuousAt_const
    · exact (continuous_apply d).continuousAt
  exact ((hU _ (slice_mem_box T L t ht y hy)).continuousAt.comp hc).continuousWithinAt

-- This compares a continuous approximate field with a smooth Euler solution.
-- It neither constructs that solution nor asserts accuracy of a numerical method.
theorem physical_error_from_initial_entropy (U : Point → State) (V : Space → State)
    (T L : ℝ) (hT : 0 ≤ T) (hL : 0 < L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L)
    (hUT : ∀ y ∈ cube L, U (Fin.cons T y) ∈ region)
    (hVc : ContinuousOn V (cube L)) (hV : ∀ y ∈ cube L, V y ∈ region) :
    |(∫ y, entropy (V y) ∂cubeMeasure L)-
      (∫ y, entropy (U (Fin.cons 0 y)) ∂cubeMeasure L)|/160 ≤
      maxComponentError (cubeMeasure L) (fun y => U (Fin.cons T y)) V := by
  rw [← normalized_entropy_conservation U T L hT hL.le hU hphys heuler hperiodic]
  exact normalized_error_lower_bound L _ V
    (slice_continuousOn U T L T ⟨hT,le_rfl⟩ hU) hVc hUT hV

end EulerEntropyIntegral
