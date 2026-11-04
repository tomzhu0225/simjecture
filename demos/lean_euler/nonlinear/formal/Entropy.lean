import Mathlib.Analysis.SpecialFunctions.Log.Deriv

-- Actual derivatives of the gamma=2 convex mathematical entropy. These local
-- identities do not establish entropy dissipation of a finite-volume step.
noncomputable section
namespace EulerEntropy
open EulerConservativePrimitive
open scoped Topology
abbrev State := Fin 5 → ℝ

def dot (x y : State) : ℝ := x 0*y 0+x 1*y 1+x 2*y 2+x 3*y 3+x 4*y 4

def entropy (u : State) : ℝ :=
  -u 0*(Real.log (EulerAdmissible.pressure u)-2*Real.log (u 0))

def pressureD (u k : State) : ℝ :=
  k 4-(u 1*k 1+u 2*k 2+u 3*k 3)/u 0+
    (u 1^2+u 2^2+u 3^2)*k 0/(2*(u 0)^2)

def gradient (u : State) : State :=
  let p := EulerAdmissible.pressure u
  ![2-(Real.log p-2*Real.log (u 0))-(u 1^2+u 2^2+u 3^2)/(2*u 0*p),
    u 1/p,u 2/p,u 3/p,-u 0/p]

theorem entropy_log_ratio (u : State) (hu : EulerAdmissible.Admissible u) :
    entropy u = -u 0*Real.log (EulerAdmissible.pressure u/(u 0)^2) := by
  rw [Real.log_div (ne_of_gt hu.2) (pow_ne_zero 2 (ne_of_gt hu.1)),Real.log_pow]
  rfl

theorem pressure_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : u t 0 ≠ 0) :
    HasDerivAt (fun s => EulerAdmissible.pressure (u s)) (pressureD (u t) k) t := by
  have hnum := ((((hasDerivAt_pi.mp hu) 1).pow 2).add
    (((hasDerivAt_pi.mp hu) 2).pow 2)).add (((hasDerivAt_pi.mp hu) 3).pow 2)
  have hh := ((hasDerivAt_pi.mp hu) 4).sub
    (hnum.div (((hasDerivAt_pi.mp hu) 0).const_mul 2) (mul_ne_zero (by norm_num) hr))
  convert hh using 1
  dsimp [pressureD]
  field_simp
  ring

theorem entropy_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : u t 0 ≠ 0) (hp : EulerAdmissible.pressure (u t) ≠ 0) :
    HasDerivAt (fun s => entropy (u s)) (dot (gradient (u t)) k) t := by
  have hh := (((hasDerivAt_pi.mp hu) 0).mul
    (((pressure_derivative hu hr).log hp).sub ((((hasDerivAt_pi.mp hu) 0).log hr).const_mul 2))).neg
  convert hh using 1
  · funext s
    dsimp [entropy]
    ring
  · dsimp [dot,gradient,pressureD]
    field_simp
    ring

def logState (w : State) : ℝ := Real.log (w 4)+2*Real.log (w 0)
def primitiveEntropy (w : State) : ℝ := -logState w/w 0
def entropyVariables (w : State) : State :=
  ![2-logState w-kinetic w/(w 0*w 4),
    w 1/(w 0*w 4),w 2/(w 0*w 4),w 3/(w 0*w 4),-1/(w 0*w 4)]

def variablesD (w h : State) : State :=
  let R := w 0*w 4
  let dR := h 0*w 4+w 0*h 4
  ![-(h 4/w 4+2*h 0/w 0)-(kineticD w h*R-kinetic w*dR)/R^2,
    (h 1*R-w 1*dR)/R^2,(h 2*R-w 2*dR)/R^2,(h 3*R-w 3*dR)/R^2,dR/R^2]

theorem pressure_conserved (w : State) : EulerAdmissible.pressure (conserved w) = w 4 := by
  rw [conserved_as_primitive,EulerAdmissible.pressure_primitive]

theorem entropy_conserved (w : State) : entropy (conserved w) = primitiveEntropy w := by
  simp only [entropy,pressure_conserved]
  dsimp [conserved,primitiveEntropy,logState]
  rw [one_div,Real.log_inv]
  ring

theorem gradient_conserved (w : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0) :
    gradient (conserved w) = entropyVariables w := by
  simp only [gradient,pressure_conserved]
  funext i
  fin_cases i
  all_goals dsimp [conserved,entropyVariables,kinetic,logState]
  all_goals try simp only [one_div,Real.log_inv]
  all_goals field_simp
  all_goals ring

theorem variables_derivative {w : ℝ → State} {h : State} {t : ℝ}
    (hw : HasDerivAt w h t) (hq : w t 0 ≠ 0) (hp : w t 4 ≠ 0) :
    HasDerivAt (fun s => entropyVariables (w s)) (variablesD (w t) h) t := by
  have hR := ((hasDerivAt_pi.mp hw) 0).mul ((hasDerivAt_pi.mp hw) 4)
  have hRn : w t 0*w t 4 ≠ 0 := mul_ne_zero hq hp
  have hlog := (((hasDerivAt_pi.mp hw) 4).log hp).add
    ((((hasDerivAt_pi.mp hw) 0).log hq).const_mul 2)
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · have hh := ((hasDerivAt_const t (2 : ℝ)).sub hlog).sub ((kinetic_derivative hw).div hR hRn)
    convert hh using 1
    dsimp [variablesD]
    ring
  · exact ((hasDerivAt_pi.mp hw) 1).div hR hRn
  · exact ((hasDerivAt_pi.mp hw) 2).div hR hRn
  · exact ((hasDerivAt_pi.mp hw) 3).div hR hRn
  · have hh := (hR.inv hRn).neg
    convert hh using 1
    · funext s
      dsimp [entropyVariables]
      ring
    · dsimp [variablesD]
      ring

def hessianForm (w h : State) : ℝ :=
  h 4^2/(2*(w 4)^2*w 0)+(h 1^2+h 2^2+h 3^2)/(w 4*(w 0)^2)+
    (2/w 0)*(h 0/w 0+h 4/(2*w 4))^2

theorem hessian_pullback (w h : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0) :
    dot (variablesD w h) (jacobian w h) = hessianForm w h := by
  dsimp [dot,variablesD,jacobian,kinetic,kineticD,hessianForm]
  field_simp
  ring

theorem hessian_nonnegative (w h : State) (hq : 0 < w 0) (hp : 0 < w 4) :
    0 ≤ hessianForm w h := by
  dsimp [hessianForm]
  positivity

theorem metric_le_entropy_factor (w h : State) (hq : 0 < w 0) (hp : 0 < w 4) :
    EulerPrimitiveEnergy.metric (w 0) (w 4) h h ≤
      (w 0*w 4+w 0/2+1)*hessianForm w h := by
  let A := h 4^2/(2*(w 4)^2*w 0)+(h 1^2+h 2^2+h 3^2)/(w 4*(w 0)^2)
  let B := (2/w 0)*(h 0/w 0+h 4/(2*w 4))^2
  have hA : 0 ≤ A := by dsimp [A]; positivity
  have hB : 0 ≤ B := by dsimp [B]; positivity
  have hq0 := ne_of_gt hq
  have hp0 := ne_of_gt hp
  calc
    _ = (w 0*w 4)*A+(w 0/2)*B := by
      dsimp [A,B,EulerPrimitiveEnergy.metric]
      field_simp
    _ ≤ (w 0*w 4+w 0/2+1)*A+(w 0*w 4+w 0/2+1)*B :=
      add_le_add (mul_le_mul_of_nonneg_right (by nlinarith) hA)
        (mul_le_mul_of_nonneg_right (by nlinarith) hB)
    _ = _ := by dsimp [A,B,hessianForm]; ring

theorem hessian_positive (w h : State) (hq : 0 < w 0) (hp : 0 < w 4) (hh : h ≠ 0) :
    0 < hessianForm w h := by
  have hg := EulerPrimitiveEnergy.metric_positive (w 0) (w 4) hq hp h hh
  have hb := metric_le_entropy_factor w h hq hp
  have hcoef : 0 ≤ w 0*w 4+w 0/2+1 := by positivity
  by_contra hnot
  have hn := mul_nonpos_of_nonneg_of_nonpos hcoef (le_of_not_gt hnot)
  linarith

theorem gradient_conserved_derivative {w : ℝ → State} {h : State} {t : ℝ}
    (hw : HasDerivAt w h t) (hq : 0 < w t 0) (hp : 0 < w t 4) :
    HasDerivAt (fun s => gradient (conserved (w s))) (variablesD (w t) h) t := by
  have hqp : ∀ᶠ s in 𝓝 t, 0 < w s 0 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hw) 0).continuousAt hq
  have hpp : ∀ᶠ s in 𝓝 t, 0 < w s 4 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hw) 4).continuousAt hp
  have heq : (fun s => gradient (conserved (w s))) =ᶠ[𝓝 t]
      (fun s => entropyVariables (w s)) := (hqp.and hpp).mono
    (fun s hs => gradient_conserved (w s) (ne_of_gt hs.1) (ne_of_gt hs.2))
  exact (variables_derivative hw (ne_of_gt hq) (ne_of_gt hp)).congr_of_eventuallyEq heq

theorem dot_derivative {f : ℝ → State} {h : State} {t : ℝ}
    (hf : HasDerivAt f h t) (k : State) :
    HasDerivAt (fun s => dot (f s) k) (dot h k) t := by
  exact ((((((hasDerivAt_pi.mp hf) 0).mul_const (k 0)).add
    (((hasDerivAt_pi.mp hf) 1).mul_const (k 1))).add
    (((hasDerivAt_pi.mp hf) 2).mul_const (k 2))).add
    (((hasDerivAt_pi.mp hf) 3).mul_const (k 3))).add
    (((hasDerivAt_pi.mp hf) 4).mul_const (k 4))

-- This differentiates the actual conservative entropy gradient and evaluates
-- it against the conservative tangent. It is not a definition of a Hessian.
theorem conservative_hessian_derivative {w : ℝ → State} {h : State} {t : ℝ}
    (hw : HasDerivAt w h t) (hq : 0 < w t 0) (hp : 0 < w t 4) :
    HasDerivAt (fun s => dot (gradient (conserved (w s))) (jacobian (w t) h))
      (hessianForm (w t) h) t := by
  have hh := dot_derivative (gradient_conserved_derivative hw hq hp) (jacobian (w t) h)
  rwa [hessian_pullback (w t) h (ne_of_gt hq) (ne_of_gt hp)] at hh

def toPrimitive (u : State) : State :=
  ![1/u 0,u 1/u 0,u 2/u 0,u 3/u 0,EulerAdmissible.pressure u]

def primitiveD (u k : State) : State :=
  ![-k 0/(u 0)^2,(k 1*u 0-u 1*k 0)/(u 0)^2,
    (k 2*u 0-u 2*k 0)/(u 0)^2,(k 3*u 0-u 3*k 0)/(u 0)^2,pressureD u k]

theorem primitive_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : u t 0 ≠ 0) :
    HasDerivAt (fun s => toPrimitive (u s)) (primitiveD (u t) k) t := by
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · simpa only [toPrimitive,primitiveD,one_div,Pi.inv_apply] using
      ((hasDerivAt_pi.mp hu) 0).inv hr
  · exact ((hasDerivAt_pi.mp hu) 1).div ((hasDerivAt_pi.mp hu) 0) hr
  · exact ((hasDerivAt_pi.mp hu) 2).div ((hasDerivAt_pi.mp hu) 0) hr
  · exact ((hasDerivAt_pi.mp hu) 3).div ((hasDerivAt_pi.mp hu) 0) hr
  · exact pressure_derivative hu hr

theorem conserved_toPrimitive (u : State) (hr : u 0 ≠ 0) : conserved (toPrimitive u) = u := by
  funext i
  fin_cases i <;> dsimp [conserved,toPrimitive,kinetic,EulerAdmissible.pressure]
  all_goals field_simp
  all_goals ring

theorem jacobian_primitiveD (u k : State) (hr : u 0 ≠ 0) :
    jacobian (toPrimitive u) (primitiveD u k) = k := by
  funext i
  fin_cases i <;> dsimp [jacobian,toPrimitive,primitiveD,pressureD,kinetic,kineticD]
  all_goals field_simp
  all_goals ring

theorem gradient_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : 0 < u t 0) (hp : 0 < EulerAdmissible.pressure (u t)) :
    HasDerivAt (fun s => gradient (u s))
      (variablesD (toPrimitive (u t)) (primitiveD (u t) k)) t := by
  have hq : 0 < toPrimitive (u t) 0 := by dsimp [toPrimitive]; positivity
  have hh := gradient_conserved_derivative (primitive_derivative hu (ne_of_gt hr)) hq hp
  have hpos : ∀ᶠ s in 𝓝 t, 0 < u s 0 :=
    continuousAt_const.eventually_lt ((hasDerivAt_pi.mp hu) 0).continuousAt hr
  have heq : (fun s => gradient (u s)) =ᶠ[𝓝 t]
      (fun s => gradient (conserved (toPrimitive (u s)))) := hpos.mono
    (fun s hs => congrArg gradient (conserved_toPrimitive (u s) (ne_of_gt hs)).symm)
  exact hh.congr_of_eventuallyEq heq

theorem entropy_second_directional {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : 0 < u t 0) (hp : 0 < EulerAdmissible.pressure (u t)) :
    HasDerivAt (fun s => dot (gradient (u s)) k)
      (hessianForm (toPrimitive (u t)) (primitiveD (u t) k)) t := by
  have hh := dot_derivative (gradient_derivative hu hr hp) k
  have he : dot (variablesD (toPrimitive (u t)) (primitiveD (u t) k)) k =
      hessianForm (toPrimitive (u t)) (primitiveD (u t) k) := by
    calc
      _ = dot (variablesD (toPrimitive (u t)) (primitiveD (u t) k))
          (jacobian (toPrimitive (u t)) (primitiveD (u t) k)) := by
        rw [jacobian_primitiveD (u t) k (ne_of_gt hr)]
      _ = _ := hessian_pullback _ _ (by dsimp [toPrimitive]; positivity) (ne_of_gt hp)
  rwa [he] at hh

def entropyDifferential (w h : State) : ℝ :=
  (logState w-2)*h 0/(w 0)^2-h 4/(w 0*w 4)

theorem entropy_jacobian_pairing (w h : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0) :
    dot (entropyVariables w) (jacobian w h) = entropyDifferential w h := by
  dsimp [dot,entropyVariables,jacobian,entropyDifferential,kinetic,kineticD]
  field_simp
  ring

theorem primitive_entropy_derivative {w : ℝ → State} {h : State} {t : ℝ}
    (hw : HasDerivAt w h t) (hq : w t 0 ≠ 0) (hp : w t 4 ≠ 0) :
    HasDerivAt (fun s => primitiveEntropy (w s)) (entropyDifferential (w t) h) t := by
  have hr : conserved (w t) 0 ≠ 0 := by dsimp [conserved]; positivity
  have hpr : EulerAdmissible.pressure (conserved (w t)) ≠ 0 := by rwa [pressure_conserved]
  have hh := entropy_derivative (conserved_derivative hw hq) hr hpr
  simpa only [entropy_conserved,gradient_conserved (w t) hq hp,
    entropy_jacobian_pairing (w t) h hq hp] using hh

theorem principal_entropy_compatibility (w h : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0)
    (d : Fin 3) :
    entropyDifferential w
      (EulerPrimitiveEnergy.principal (w 0) (w 4) (w ⟨d.val+1,by omega⟩) d h) =
    w ⟨d.val+1,by omega⟩*entropyDifferential w h+
      primitiveEntropy w*h ⟨d.val+1,by omega⟩ := by
  fin_cases d <;> dsimp [entropyDifferential,EulerPrimitiveEnergy.principal,primitiveEntropy] <;>
    field_simp <;> ring

theorem primitive_entropy_potential (w : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0)
    (d : Fin 3) : dot (entropyVariables w) (primitiveFlux w d)-
      primitiveEntropy w*w ⟨d.val+1,by omega⟩ = w ⟨d.val+1,by omega⟩/w 0 := by
  fin_cases d <;> dsimp [dot,entropyVariables,primitiveFlux,primitiveEntropy,kinetic] <;>
    field_simp <;> ring

end EulerEntropy
