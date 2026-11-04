-- Actual conservative entropy Hessian as a bilinear form, with its physical
-- flux compatibility. Uniform Hessian constants are explicit hypotheses below.
noncomputable section
namespace EulerEntropyGeometry
open EulerEntropy EulerEntropyTaylor EulerVectorEstimates EulerEnergyBounds
open EulerConservativePrimitive
abbrev State := Fin 5 → ℝ

def hessianVector (u k : State) : State := variablesD (toPrimitive u) (primitiveD u k)
def hessianPair (u k z : State) : ℝ := dot (hessianVector u k) z

def primitivePair (w h k : State) : ℝ :=
  h 4*k 4/(2*(w 4)^2*w 0)+(h 1*k 1+h 2*k 2+h 3*k 3)/(w 4*(w 0)^2)+
    (2/w 0)*(h 0/w 0+h 4/(2*w 4))*(k 0/w 0+k 4/(2*w 4))

theorem hessian_pullback_bilinear (w h k : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0) :
    dot (variablesD w h) (jacobian w k)=primitivePair w h k := by
  dsimp [dot,variablesD,jacobian,kinetic,kineticD,primitivePair]
  field_simp
  ring

theorem hessian_pair_primitive (u k z : State) (hu : EulerAdmissible.Admissible u) :
    hessianPair u k z=primitivePair (toPrimitive u) (primitiveD u k) (primitiveD u z) := by
  have hh := hessian_pullback_bilinear (toPrimitive u) (primitiveD u k) (primitiveD u z)
    (by dsimp [toPrimitive]; exact ne_of_gt (one_div_pos.mpr hu.1)) (ne_of_gt hu.2)
  rw [jacobian_primitiveD u z (ne_of_gt hu.1)] at hh
  exact hh

theorem hessian_pair_self (u k : State) (hu : EulerAdmissible.Admissible u) :
    hessianPair u k k=conservativeHessian u k := by
  rw [hessian_pair_primitive u k k hu]
  dsimp [primitivePair,conservativeHessian,hessianForm]
  ring

theorem hessian_pair_symmetric (u k z : State) (hu : EulerAdmissible.Admissible u) :
    hessianPair u k z=hessianPair u z k := by
  rw [hessian_pair_primitive u k z hu,hessian_pair_primitive u z k hu]
  dsimp [primitivePair]
  ring

theorem primitiveD_sub (u k z : State) : primitiveD u (k-z)=primitiveD u k-primitiveD u z := by
  funext i
  fin_cases i <;> dsimp [primitiveD,pressureD] <;> ring

theorem variablesD_sub (w k z : State) : variablesD w (k-z)=variablesD w k-variablesD w z := by
  funext i
  fin_cases i <;> dsimp [variablesD,kineticD] <;> ring

theorem hessian_pair_sub_left (u x y z : State) :
    hessianPair u (x-y) z=hessianPair u x z-hessianPair u y z := by
  simp only [hessianPair,hessianVector,primitiveD_sub,variablesD_sub,dot_sub_left]

theorem hessian_pair_sub_right (u x y z : State) :
    hessianPair u x (y-z)=hessianPair u x y-hessianPair u x z := by
  simp only [hessianPair,dot_sub_right]

theorem hessian_young_bound (u k z : State) (hu : EulerAdmissible.Admissible u) (M : ℝ)
    (hk : conservativeHessian u k ≤ M*sizeSquared k)
    (hz : conservativeHessian u z ≤ M*sizeSquared z) :
    hessianPair u k z ≤ (M/2)*(sizeSquared k+sizeSquared z) := by
  have hn : 0 ≤ hessianPair u (k-z) (k-z) := by
    rw [hessian_pair_self u _ hu]
    exact hessian_nonnegative _ _ (by dsimp [toPrimitive]; exact one_div_pos.mpr hu.1) hu.2
  rw [hessian_pair_sub_left,hessian_pair_sub_right,hessian_pair_sub_right,
    hessian_pair_symmetric u z k hu,hessian_pair_self u k hu,hessian_pair_self u z hu] at hn
  linarith

theorem primitive_hessian_flux (w h : State) (hq : w 0 ≠ 0) (hp : w 4 ≠ 0) (d : Fin 3) :
    dot (variablesD w h) (primitiveFlux w d)=(jacobian w h) ⟨d.val+1,by omega⟩ := by
  fin_cases d <;> dsimp [dot,variablesD,primitiveFlux,jacobian,kinetic,kineticD] <;>
    field_simp <;> ring

theorem hessian_flux_compatibility (u k : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    hessianPair u k (EulerAdmissible.eulerFlux u d)=k ⟨d.val+1,by omega⟩ := by
  have hq : 0 < toPrimitive u 0 := by dsimp [toPrimitive]; exact one_div_pos.mpr hu.1
  have hc := canonical_flux (toPrimitive u) hq d
  rw [conserved_toPrimitive u (ne_of_gt hu.1)] at hc
  dsimp [hessianPair,hessianVector]
  rw [hc,primitive_hessian_flux _ _ (ne_of_gt hq) (ne_of_gt hu.2) d,
    jacobian_primitiveD u k (ne_of_gt hu.1)]

theorem gradient_pair_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hder : HasDerivAt u k t) (hu : EulerAdmissible.Admissible (u t)) (z : State) :
    HasDerivAt (fun s => dot (gradient (u s)) z) (hessianPair (u t) k z) t :=
  dot_derivative (gradient_derivative hder hu.1 hu.2) z

end EulerEntropyGeometry
