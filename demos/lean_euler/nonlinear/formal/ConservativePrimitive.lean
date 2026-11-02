import Mathlib.Analysis.Calculus.Deriv.Add
import Mathlib.Analysis.Calculus.Deriv.Prod
import Mathlib.Analysis.Calculus.Deriv.Pow
import Mathlib.Analysis.Calculus.Deriv.Inv

-- Assemble after Admissible.lean and PrimitiveEnergy.lean.
noncomputable section
namespace EulerConservativePrimitive
open scoped Topology
abbrev State := Fin 5 → ℝ

def kinetic (w : State) : ℝ := (w 1^2+w 2^2+w 3^2)/2
def kineticD (w h : State) : ℝ := w 1*h 1+w 2*h 2+w 3*h 3

def conserved (w : State) : State :=
  ![1/w 0,w 1/w 0,w 2/w 0,w 3/w 0,w 4+kinetic w/w 0]

def jacobian (w h : State) : State :=
  ![-h 0/(w 0)^2,(h 1*w 0-w 1*h 0)/(w 0)^2,
    (h 2*w 0-w 2*h 0)/(w 0)^2,(h 3*w 0-w 3*h 0)/(w 0)^2,
    h 4+(kineticD w h*w 0-kinetic w*h 0)/(w 0)^2]

theorem kinetic_derivative {w : ℝ → State} {h : State} {s : ℝ}
    (hw : HasDerivAt w h s) : HasDerivAt (fun t => kinetic (w t)) (kineticD (w s) h) s := by
  have hk := (((((hasDerivAt_pi.mp hw) 1).pow 2).add
    (((hasDerivAt_pi.mp hw) 2).pow 2)).add (((hasDerivAt_pi.mp hw) 3).pow 2)).div_const 2
  convert hk using 1; simp [kineticD]; ring

theorem conserved_derivative {w : ℝ → State} {h : State} {s : ℝ}
    (hw : HasDerivAt w h s) (hq : w s 0 ≠ 0) :
    HasDerivAt (fun t => conserved (w t)) (jacobian (w s) h) s := by
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · have hi := ((hasDerivAt_pi.mp hw) 0).inv hq
    simpa only [conserved,jacobian,one_div,Pi.inv_apply] using hi
  · exact ((hasDerivAt_pi.mp hw) 1).div ((hasDerivAt_pi.mp hw) 0) hq
  · exact ((hasDerivAt_pi.mp hw) 2).div ((hasDerivAt_pi.mp hw) 0) hq
  · exact ((hasDerivAt_pi.mp hw) 3).div ((hasDerivAt_pi.mp hw) 0) hq
  · exact ((hasDerivAt_pi.mp hw) 4).add ((kinetic_derivative hw).div ((hasDerivAt_pi.mp hw) 0) hq)

theorem jacobian_add (w x y : State) : jacobian w (x+y) = jacobian w x+jacobian w y := by
  funext i
  fin_cases i <;> simp [jacobian,kineticD] <;> ring

theorem jacobian_zero (w : State) : jacobian w 0=0 := by
  funext i
  fin_cases i <;> simp [jacobian,kineticD]

theorem jacobian_injective (w : State) (hq : w 0 ≠ 0) : Function.Injective (jacobian w) := by
  intro x y h
  have hh (i : Fin 5) := congrFun h i
  have h0 : x 0=y 0 := by
    have hi := hh 0
    dsimp [jacobian] at hi
    have heq := (div_left_inj' (pow_ne_zero 2 hq)).mp hi
    linarith
  have h1 : x 1=y 1 := by
    have hi := hh 1
    dsimp [jacobian] at hi
    have heq := (div_left_inj' (pow_ne_zero 2 hq)).mp hi
    rw [h0] at heq
    exact (mul_right_cancel₀ hq) (by linarith [heq])
  have h2 : x 2=y 2 := by
    have hi := hh 2
    dsimp [jacobian] at hi
    have heq := (div_left_inj' (pow_ne_zero 2 hq)).mp hi
    rw [h0] at heq
    exact (mul_right_cancel₀ hq) (by linarith [heq])
  have h3 : x 3=y 3 := by
    have hi := hh 3
    dsimp [jacobian] at hi
    have heq := (div_left_inj' (pow_ne_zero 2 hq)).mp hi
    rw [h0] at heq
    exact (mul_right_cancel₀ hq) (by linarith [heq])
  have h4 : x 4=y 4 := by
    have hi := hh 4
    simpa [jacobian,kineticD,h0,h1,h2,h3] using hi
  funext i
  fin_cases i <;> simp [h0,h1,h2,h3,h4]

def primitiveFlux (w : State) (d : Fin 3) : State :=
  let vd := w ⟨d.val+1,by omega⟩
  ![vd/w 0,w 1*vd/w 0+(if d=0 then w 4 else 0),
    w 2*vd/w 0+(if d=1 then w 4 else 0),
    w 3*vd/w 0+(if d=2 then w 4 else 0),(2*w 4+kinetic w/w 0)*vd]

def primitiveFluxD (w h : State) (d : Fin 3) : State :=
  let vd := w ⟨d.val+1,by omega⟩
  let hd := h ⟨d.val+1,by omega⟩
  ![(hd*w 0-vd*h 0)/(w 0)^2,
    ((h 1*vd+w 1*hd)*w 0-w 1*vd*h 0)/(w 0)^2+(if d=0 then h 4 else 0),
    ((h 2*vd+w 2*hd)*w 0-w 2*vd*h 0)/(w 0)^2+(if d=1 then h 4 else 0),
    ((h 3*vd+w 3*hd)*w 0-w 3*vd*h 0)/(w 0)^2+(if d=2 then h 4 else 0),
    (2*h 4+(kineticD w h*w 0-kinetic w*h 0)/(w 0)^2)*vd+(2*w 4+kinetic w/w 0)*hd]

theorem flux_derivative {w : ℝ → State} {h : State} {s : ℝ}
    (hw : HasDerivAt w h s) (hq : w s 0 ≠ 0) (d : Fin 3) :
    HasDerivAt (fun t => primitiveFlux (w t) d) (primitiveFluxD (w s) h d) s := by
  let k : Fin 5 := ⟨d.val+1,by omega⟩
  have hd := hasDerivAt_pi.mp hw k
  have h0 := hasDerivAt_pi.mp hw 0
  have h4 := hasDerivAt_pi.mp hw 4
  have hc (j : Fin 3) : HasDerivAt (fun t => if d=j then w t 4 else 0)
      (if d=j then h 4 else 0) s := by
    by_cases heq : d=j
    · simpa only [heq,if_true] using h4
    · simpa only [heq,if_false] using hasDerivAt_const s (0 : ℝ)
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · exact hd.div h0 hq
  · exact (((hasDerivAt_pi.mp hw 1).mul hd).div h0 hq).add (hc 0)
  · exact (((hasDerivAt_pi.mp hw 2).mul hd).div h0 hq).add (hc 1)
  · exact (((hasDerivAt_pi.mp hw 3).mul hd).div h0 hq).add (hc 2)
  · have he := ((h4.const_mul 2).add ((kinetic_derivative hw).div h0 hq)).mul hd
    exact he

theorem principal_flux_identity (w h : State) (hq : w 0 ≠ 0) (d : Fin 3) :
    primitiveFluxD w h d = jacobian w
      (EulerPrimitiveEnergy.principal (w 0) (w 4) (w ⟨d.val+1,by omega⟩) d h) := by
  funext i
  fin_cases d <;> fin_cases i <;>
    simp [primitiveFluxD,jacobian,EulerPrimitiveEnergy.principal,kinetic,kineticD] <;> field_simp <;> ring

theorem conserved_as_primitive (w : State) :
    conserved w = EulerAdmissible.primitive (1/w 0) (w 4) ![w 1,w 2,w 3] := by
  funext i
  fin_cases i <;> simp [conserved,EulerAdmissible.primitive,kinetic,EulerAdmissible.kinetic] <;> ring

theorem canonical_flux (w : State) (hq : 0 < w 0) (d : Fin 3) :
    EulerAdmissible.eulerFlux (conserved w) d = primitiveFlux w d := by
  have hr : 0 < 1/w 0 := by positivity
  rw [conserved_as_primitive,EulerAdmissible.flux_primitive _ _ _ hr d]
  funext i
  fin_cases d <;> fin_cases i <;> dsimp [primitiveFlux,EulerAdmissible.primitiveFlux,kinetic,EulerAdmissible.kinetic] <;> ring

theorem canonical_flux_derivative {w : ℝ → State} {h : State} {s : ℝ}
    (hw : HasDerivAt w h s) (hq : 0 < w s 0) (d : Fin 3) :
    HasDerivAt (fun t => EulerAdmissible.eulerFlux (conserved (w t)) d)
      (jacobian (w s) (EulerPrimitiveEnergy.principal (w s 0) (w s 4)
        (w s ⟨d.val+1,by omega⟩) d h)) s := by
  have hpos : ∀ᶠ t in 𝓝 s, 0 < w t 0 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hw) 0).continuousAt hq
  have heq : (fun t => EulerAdmissible.eulerFlux (conserved (w t)) d) =ᶠ[𝓝 s]
      (fun t => primitiveFlux (w t) d) := hpos.mono (fun t ht => canonical_flux (w t) ht d)
  have hder := (flux_derivative hw (ne_of_gt hq) d).congr_of_eventuallyEq heq
  rwa [principal_flux_identity (w s) h (ne_of_gt hq) d] at hder

-- The derivative curves pass through one common physical point. No solution
-- existence or numerical stability is inferred from this equivalence.
theorem euler_residual_equivalence (w ht : State) (hx : Fin 3 → State)
    (timeCurve : ℝ → State) (spaceCurve : Fin 3 → ℝ → State)
    (hqt : 0 < w 0) (hvt : timeCurve 0=w) (hvx : ∀ d, spaceCurve d 0=w)
    (hdt : HasDerivAt timeCurve ht 0) (hdx : ∀ d, HasDerivAt (spaceCurve d) (hx d) 0) :
    (deriv (fun t => conserved (timeCurve t)) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 0 t)) 0) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 1 t)) 1) 0+
      deriv (fun t => EulerAdmissible.eulerFlux (conserved (spaceCurve 2 t)) 2) 0=0) ↔
    ht+EulerPrimitiveEnergy.principal (w 0) (w 4) (w 1) 0 (hx 0)+
      EulerPrimitiveEnergy.principal (w 0) (w 4) (w 2) 1 (hx 1)+
      EulerPrimitiveEnergy.principal (w 0) (w 4) (w 3) 2 (hx 2)=0 := by
  have htime := (conserved_derivative hdt (by rw [hvt]; exact ne_of_gt hqt)).deriv
  have hspace (d : Fin 3) := (canonical_flux_derivative (hdx d) (by rw [hvx]; exact hqt) d).deriv
  rw [htime,hspace 0,hspace 1,hspace 2]
  simp only [hvt,hvx]
  rw [← jacobian_add,← jacobian_add,← jacobian_add]
  constructor
  · intro h
    apply jacobian_injective w (ne_of_gt hqt)
    simpa only [jacobian_zero] using h
  · intro h
    exact (congrArg (jacobian w) h).trans (jacobian_zero w)
end EulerConservativePrimitive
