-- Gamma=2, three-dimensional version of the logarithmic-mean flux of
-- Chandrashekar (2013), not a claim of a new numerical-flux invention.
noncomputable section
namespace EulerEntropyConservativeFlux
open EulerEntropy EulerLogMean
open EulerVectorEstimates EulerEnergyBounds
abbrev State := Fin 5 → ℝ
abbrev Vec := Fin 3 → ℝ

def average (a b : ℝ) : ℝ := (a+b)/2
def speedSquared (v : Vec) : ℝ := v 0^2+v 1^2+v 2^2
def parameterState (r beta : ℝ) (v : Vec) : State := EulerAdmissible.primitive r (r/(2*beta)) v
def parameterGradient (r beta : ℝ) (v : Vec) : State :=
  ![2+Real.log 2+Real.log r+Real.log beta-beta*speedSquared v,
    2*beta*v 0,2*beta*v 1,2*beta*v 2,-2*beta]

theorem canonical_parameter_gradient (r beta : ℝ) (v : Vec) (hr : 0 < r) (hb : 0 < beta) :
    gradient (parameterState r beta v)=parameterGradient r beta v := by
  have hr0 := ne_of_gt hr
  have hb0 := ne_of_gt hb
  have hlog : Real.log (r/(2*beta))=Real.log r-Real.log 2-Real.log beta := by
    rw [Real.log_div hr0 (mul_ne_zero (by norm_num) hb0),Real.log_mul (by norm_num) hb0]
    ring
  simp only [parameterState,gradient,EulerAdmissible.pressure_primitive]
  funext i
  fin_cases i
  all_goals dsimp [EulerAdmissible.primitive,EulerAdmissible.kinetic,parameterGradient,speedSquared]
  all_goals try rw [hlog]
  all_goals field_simp
  all_goals ring

def fluxWithMeans (rL rR bL bR lr lb : ℝ) (vL vR : Vec) (d : Fin 3) : State :=
  let vd := average (vL d) (vR d)
  let vx := average (vL 0) (vR 0)
  let vy := average (vL 1) (vR 1)
  let vz := average (vL 2) (vR 2)
  let mass := lr*vd
  let p := average rL rR/(2*average bL bR)
  let mx := mass*vx+(if d=0 then p else 0)
  let my := mass*vy+(if d=1 then p else 0)
  let mz := mass*vz+(if d=2 then p else 0)
  ![mass,mx,my,mz,
    mass*(1/(2*lb)-average (speedSquared vL) (speedSquared vR)/2)+vx*mx+vy*my+vz*mz]

def parameterFlux (rL rR bL bR : ℝ) (vL vR : Vec) (d : Fin 3) : State :=
  fluxWithMeans rL rR bL bR (logMean rL rR) (logMean bL bR) vL vR d

theorem entropy_residual_identity (rL rR bL bR lr lb : ℝ) (vL vR : Vec) (d : Fin 3)
    (hbs : bL+bR ≠ 0) (hlb : lb ≠ 0) :
    dot (parameterGradient rR bR vR-parameterGradient rL bL vL)
      (fluxWithMeans rL rR bL bR lr lb vL vR d)-(rR*vR d-rL*vL d) =
      average (vL d) (vR d)*(lr*(Real.log rR-Real.log rL)-(rR-rL))+
      (lr*average (vL d) (vR d)/lb)*(lb*(Real.log bR-Real.log bL)-(bR-bL)) := by
  fin_cases d
  all_goals dsimp [dot,parameterGradient,fluxWithMeans,average,speedSquared]
  all_goals field_simp
  all_goals ring

theorem parameter_entropy_conservation (rL rR bL bR : ℝ) (vL vR : Vec) (d : Fin 3)
    (hrL : 0 < rL) (hrR : 0 < rR) (hbL : 0 < bL) (hbR : 0 < bR) :
    dot (gradient (parameterState rR bR vR)-gradient (parameterState rL bL vL))
      (parameterFlux rL rR bL bR vL vR d)=rR*vR d-rL*vL d := by
  rw [canonical_parameter_gradient rR bR vR hrR hbR,canonical_parameter_gradient rL bL vL hrL hbL]
  have hh := entropy_residual_identity rL rR bL bR (logMean rL rR) (logMean bL bR) vL vR d
    (ne_of_gt (add_pos hbL hbR)) (ne_of_gt (positive bL bR hbL hbR))
  rw [jump_identity rL rR hrL hrR,jump_identity bL bR hbL hbR,sub_self,sub_self,mul_zero,mul_zero,add_zero] at hh
  exact sub_eq_zero.mp hh

theorem parameter_flux_consistency (r beta : ℝ) (v : Vec) (d : Fin 3)
    (hr : 0 < r) (hb : 0 < beta) :
    parameterFlux r r beta beta v v d=EulerAdmissible.eulerFlux (parameterState r beta v) d := by
  rw [parameterState,EulerAdmissible.flux_primitive r (r/(2*beta)) v hr d]
  have hb0 := ne_of_gt hb
  simp only [parameterFlux,diagonal]
  funext i
  fin_cases d <;> fin_cases i <;>
    dsimp [fluxWithMeans,average,speedSquared,EulerAdmissible.primitiveFlux,EulerAdmissible.kinetic]
  all_goals field_simp
  all_goals ring

def beta (u : State) : ℝ := u 0/(2*EulerAdmissible.pressure u)
def ecFlux (u v : State) (d : Fin 3) : State :=
  parameterFlux (u 0) (v 0) (beta u) (beta v)
    (EulerAdmissible.fromVelocity u) (EulerAdmissible.fromVelocity v) d
def esFlux (u v : State) (a : ℝ) (d : Fin 3) : State := ecFlux u v d-(a/2) • (v-u)

theorem beta_positive (u : State) (hu : EulerAdmissible.Admissible u) : 0 < beta u := by
  exact div_pos hu.1 (mul_pos (by norm_num) hu.2)

theorem parameter_reconstruct (u : State) (hu : EulerAdmissible.Admissible u) :
    parameterState (u 0) (beta u) (EulerAdmissible.fromVelocity u)=u := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  have he : u 0/(2*beta u)=EulerAdmissible.pressure u := by
    dsimp [beta]
    field_simp
  rw [parameterState,he,EulerAdmissible.primitive_reconstruct u hu.1]

theorem momentum_reconstruct (u : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    u 0*EulerAdmissible.fromVelocity u d=u ⟨d.val+1,by omega⟩ := by
  have hr := ne_of_gt hu.1
  fin_cases d <;> dsimp [EulerAdmissible.fromVelocity] <;> field_simp

theorem canonical_entropy_conservation (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v) (d : Fin 3) :
    dot (gradient v-gradient u) (ecFlux u v d)=v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩ := by
  have hh := parameter_entropy_conservation (u 0) (v 0) (beta u) (beta v)
    (EulerAdmissible.fromVelocity u) (EulerAdmissible.fromVelocity v) d hu.1 hv.1
    (beta_positive u hu) (beta_positive v hv)
  rw [parameter_reconstruct u hu,parameter_reconstruct v hv,
    momentum_reconstruct u hu d,momentum_reconstruct v hv d] at hh
  exact hh

theorem canonical_flux_consistency (u : State) (hu : EulerAdmissible.Admissible u) (d : Fin 3) :
    ecFlux u u d=EulerAdmissible.eulerFlux u d := by
  have hh := parameter_flux_consistency (u 0) (beta u) (EulerAdmissible.fromVelocity u) d hu.1 (beta_positive u hu)
  rwa [parameter_reconstruct u hu] at hh

theorem dissipative_flux_consistency (u : State) (hu : EulerAdmissible.Admissible u)
    (a : ℝ) (d : Fin 3) : esFlux u u a d=EulerAdmissible.eulerFlux u d := by
  simp only [esFlux,sub_self,smul_zero,sub_zero,canonical_flux_consistency u hu d]

theorem dissipative_entropy_identity (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v) (a : ℝ) (d : Fin 3) :
    dot (gradient v-gradient u) (esFlux u v a d)-
      (v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) =
      -(a/2)*dot (gradient v-gradient u) (v-u) := by
  rw [esFlux,dot_sub_right,dot_smul_right,canonical_entropy_conservation u v hu hv d]
  ring

theorem dissipative_face_bound (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v)
    (a lambda : ℝ) (ha : 0 ≤ a) (d : Fin 3)
    (hH : ∀ t ∈ Set.Icc (0 : ℝ) 1,
      lambda*sizeSquared (v-u) ≤ EulerEntropyTaylor.conservativeHessian
        (EulerEntropyConvexity.segment u v t) (v-u)) :
    dot (gradient v-gradient u) (esFlux u v a d)-
      (v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) ≤ -(a*lambda/2)*sizeSquared (v-u) := by
  rw [dissipative_entropy_identity u v hu hv a d]
  have hh := mul_le_mul_of_nonneg_left (EulerFaceEntropy.gradient_strong_monotonicity u v lambda hu hv hH)
    (by positivity : 0 ≤ a/2)
  nlinarith

theorem face_entropy_stable (u v : State)
    (hu : EulerAdmissible.Admissible u) (hv : EulerAdmissible.Admissible v)
    (a : ℝ) (ha : 0 ≤ a) (d : Fin 3) :
    dot (gradient v-gradient u) (esFlux u v a d)-
      (v ⟨d.val+1,by omega⟩-u ⟨d.val+1,by omega⟩) ≤ 0 := by
  have hH (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
      (0 : ℝ)*sizeSquared (v-u) ≤ EulerEntropyTaylor.conservativeHessian
        (EulerEntropyConvexity.segment u v t) (v-u) := by
    have hs := EulerEntropyConvexity.segment_admissible u v hu hv t ht
    have hh := hessian_nonnegative (toPrimitive (EulerEntropyConvexity.segment u v t))
      (primitiveD (EulerEntropyConvexity.segment u v t) (v-u))
      (by dsimp [toPrimitive]; exact one_div_pos.mpr hs.1) hs.2
    simpa only [zero_mul] using hh
  have hh := dissipative_face_bound u v hu hv a 0 ha d hH
  simpa only [mul_zero,zero_div,neg_zero,zero_mul] using hh

end EulerEntropyConservativeFlux
