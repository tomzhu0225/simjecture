-- Assemble after Entropy.lean. Local consequences of differentiable Euler
-- balance; existence and periodic space-time integration remain separate work.
noncomputable section
namespace EulerEntropyDynamics
open EulerEntropy EulerConservativePrimitive
open scoped Topology
abbrev State := Fin 5 → ℝ

def entropyFlux (u : State) (d : Fin 3) : ℝ :=
  entropy u*(u ⟨d.val+1,by omega⟩/u 0)

theorem entropy_flux_conserved (w : State) (hq : w 0 ≠ 0) (d : Fin 3) :
    entropyFlux (conserved w) d = primitiveEntropy w*w ⟨d.val+1,by omega⟩ := by
  rw [entropyFlux,entropy_conserved]
  congr 1
  fin_cases d <;> dsimp [conserved] <;> field_simp

theorem canonical_entropy_potential (u : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    dot (gradient u) (EulerAdmissible.eulerFlux u d)-entropyFlux u d = u ⟨d.val+1,by omega⟩ := by
  let w := toPrimitive u
  have hq : 0 < w 0 := by dsimp [w,toPrimitive]; exact one_div_pos.mpr hu.1
  have hp : w 4 ≠ 0 := ne_of_gt hu.2
  have hh : dot (gradient (conserved w)) (EulerAdmissible.eulerFlux (conserved w) d)-
      entropyFlux (conserved w) d = (conserved w) ⟨d.val+1,by omega⟩ := by
    rw [gradient_conserved w (ne_of_gt hq) hp,canonical_flux w hq d,
      entropy_flux_conserved w (ne_of_gt hq) d]
    have hr : (conserved w) ⟨d.val+1,by omega⟩ = w ⟨d.val+1,by omega⟩/w 0 := by
      fin_cases d <;> rfl
    rw [hr]
    exact primitive_entropy_potential w (ne_of_gt hq) hp d
  simpa only [w,conserved_toPrimitive u (ne_of_gt hu.1)] using hh

theorem entropy_flux_derivative {w : ℝ → State} {h : State} {t : ℝ}
    (hw : HasDerivAt w h t) (hq : 0 < w t 0) (hp : w t 4 ≠ 0) (d : Fin 3) :
    HasDerivAt (fun s => entropyFlux (conserved (w s)) d)
      (entropyDifferential (w t) (EulerPrimitiveEnergy.principal (w t 0) (w t 4)
        (w t ⟨d.val+1,by omega⟩) d h)) t := by
  have hh := (primitive_entropy_derivative hw (ne_of_gt hq) hp).mul
    ((hasDerivAt_pi.mp hw) ⟨d.val+1,by omega⟩)
  have hpos : ∀ᶠ s in 𝓝 t, 0 < w s 0 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hw) 0).continuousAt hq
  have heq : (fun s => entropyFlux (conserved (w s)) d) =ᶠ[𝓝 t]
      (fun s => primitiveEntropy (w s)*w s ⟨d.val+1,by omega⟩) := hpos.mono
    (fun s hs => entropy_flux_conserved (w s) (ne_of_gt hs) d)
  have hder := hh.congr_of_eventuallyEq heq
  convert hder using 1
  rw [principal_entropy_compatibility (w t) h (ne_of_gt hq) hp d]
  ring

theorem entropyDifferential_add (w x y : State) :
    entropyDifferential w (x+y) = entropyDifferential w x+entropyDifferential w y := by
  dsimp [entropyDifferential]
  ring

theorem entropyDifferential_zero (w : State) : entropyDifferential w 0=0 := by
  simp [entropyDifferential]

theorem smooth_entropy_balance (w ht : State) (hx : Fin 3 → State)
    (timeCurve : ℝ → State) (spaceCurve : Fin 3 → ℝ → State)
    (hq : 0 < w 0) (hp : 0 < w 4) (hvt : timeCurve 0=w) (hvx : ∀ d, spaceCurve d 0=w)
    (hdt : HasDerivAt timeCurve ht 0) (hdx : ∀ d, HasDerivAt (spaceCurve d) (hx d) 0)
    (heuler : deriv (fun t => conserved (timeCurve t)) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 0 t)) 0) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 1 t)) 1) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 2 t)) 2) 0=0) :
    deriv (fun t => entropy (conserved (timeCurve t))) 0+
      deriv (fun t => entropyFlux (conserved (spaceCurve 0 t)) 0) 0+
      deriv (fun t => entropyFlux (conserved (spaceCurve 1 t)) 1) 0+
      deriv (fun t => entropyFlux (conserved (spaceCurve 2 t)) 2) 0=0 := by
  have hprim := (euler_residual_equivalence w ht hx timeCurve spaceCurve hq hvt hvx hdt hdx).mp heuler
  have htime := (primitive_entropy_derivative hdt (by rw [hvt]; exact ne_of_gt hq)
    (by rw [hvt]; exact ne_of_gt hp)).deriv
  have hspace (d : Fin 3) := (entropy_flux_derivative (hdx d)
    (by rw [hvx]; exact hq) (by rw [hvx]; exact ne_of_gt hp) d).deriv
  simp only [entropy_conserved]
  rw [htime,hspace 0,hspace 1,hspace 2]
  simp only [hvt,hvx]
  rw [← entropyDifferential_add,← entropyDifferential_add,← entropyDifferential_add]
  change entropyDifferential w (ht+
    EulerPrimitiveEnergy.principal (w 0) (w 4) (w 1) 0 (hx 0)+
    EulerPrimitiveEnergy.principal (w 0) (w 4) (w 2) 1 (hx 1)+
    EulerPrimitiveEnergy.principal (w 0) (w 4) (w 3) 2 (hx 2))=0
  rw [hprim,entropyDifferential_zero]

end EulerEntropyDynamics
