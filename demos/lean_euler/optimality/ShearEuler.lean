import Mathlib.Analysis.Calculus.ContDiff.Operations
import Mathlib.Analysis.Calculus.Deriv.Add
import Mathlib.Analysis.Calculus.Deriv.Pow
import Mathlib.Analysis.Calculus.Deriv.Prod
import Mathlib.Analysis.Calculus.Deriv.Mul
import Mathlib.Analysis.Calculus.Deriv.Comp
import Mathlib.Analysis.Calculus.FDeriv.Prod
import Mathlib.Data.Fin.VecNotation
import Mathlib.Tactic.FinCases
import Mathlib.Tactic.Ring
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.LinearCombination
import Mathlib.Tactic.FunProp

noncomputable section
namespace ShearEuler
abbrev Space := Fin 3 → ℝ
abbrev State := Fin 5 → ℝ

def flow (t : ℝ) (a : Space) : Space := ![a 0+t*a 1, a 1+t*a 2, a 2+t]
def invFlow (t : ℝ) (x : Space) : Space :=
  ![x 0-t*x 1+t^2*x 2-t^3, x 1-t*x 2+t^2, x 2-t]
def velocity (t : ℝ) (x : Space) : Space := ![x 1-t*x 2+t^2, x 2-t, 1]
def invTime (t : ℝ) (x : Space) : Space := ![-x 1+2*t*x 2-3*t^2, -x 2+2*t, -1]
def invColumn (t : ℝ) (d : Fin 3) : Space :=
  match d with
  | 0 => ![1,0,0]
  | 1 => ![-t,1,0]
  | 2 => ![t^2,-t,1]

theorem inverse_flow (t : ℝ) (a : Space) : invFlow t (flow t a) = a := by
  funext i
  fin_cases i <;> simp [flow, invFlow] <;> ring

theorem flow_inverse (t : ℝ) (x : Space) : flow t (invFlow t x) = x := by
  funext i
  fin_cases i <;> simp [flow, invFlow] <;> ring

theorem material_velocity (t : ℝ) (a : Space) : velocity t (flow t a) = ![a 1,a 2,1] := by
  funext i
  fin_cases i <;> simp [flow,velocity]
  ring

theorem flow_derivative (t : ℝ) (a : Space) :
    HasDerivAt (fun s => flow s a) ![a 1,a 2,1] t := by
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · simpa [flow] using ((hasDerivAt_id t).mul_const (a 1)).const_add (a 0)
  · simpa [flow] using ((hasDerivAt_id t).mul_const (a 2)).const_add (a 1)
  · simpa [flow] using (hasDerivAt_id t).const_add (a 2)

theorem inverse_time_derivative (t : ℝ) (x : Space) :
    HasDerivAt (fun s => invFlow s x) (invTime t x) t := by
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · have h := (((hasDerivAt_const t (x 0)).sub ((hasDerivAt_id t).mul_const (x 1))).add
      (((hasDerivAt_id t).pow 2).mul_const (x 2))).sub ((hasDerivAt_id t).pow 3)
    convert h using 1; simp [invTime]
  · have h := ((hasDerivAt_const t (x 1)).sub ((hasDerivAt_id t).mul_const (x 2))).add
      ((hasDerivAt_id t).pow 2)
    convert h using 1; simp [invTime]
  · simpa [invFlow,invTime] using (hasDerivAt_const t (x 2)).sub (hasDerivAt_id t)

theorem inverse_coordinate_affine (t : ℝ) (x : Space) (d : Fin 3) (s : ℝ) :
    invFlow t (Function.update x d s) = invFlow t x + (s-x d) • invColumn t d := by
  funext k
  fin_cases d <;> fin_cases k <;> simp [invFlow,invColumn] <;> ring

theorem inverse_coordinate_derivative (t : ℝ) (x : Space) (d : Fin 3) :
    HasDerivAt (fun s => invFlow t (Function.update x d s)) (invColumn t d) (x d) := by
  have eq : (fun s => invFlow t (Function.update x d s)) =
      (fun s => invFlow t x + (s-x d) • invColumn t d) := by
    funext s
    exact inverse_coordinate_affine t x d s
  rw [eq]
  simpa using (((hasDerivAt_id (x d)).sub_const (x d)).smul_const
    (invColumn t d)).const_add (invFlow t x)

theorem inverse_transport_identity (t : ℝ) (x : Space) :
    invTime t x + (velocity t x 0) • invColumn t 0 +
      (velocity t x 1) • invColumn t 1 + (velocity t x 2) • invColumn t 2 = 0 := by
  funext k
  fin_cases k <;> simp [invTime,velocity,invColumn] <;> ring

def density (rho0 : Space → ℝ) (t : ℝ) (x : Space) : ℝ := rho0 (invFlow t x)

-- The derivative is taken by the actual multivariate chain rule, not supplied
-- as an unproved stability/consistency premise.
theorem density_derivatives (rho0 : Space → ℝ) (t : ℝ) (x : Space)
    (smooth : DifferentiableAt ℝ rho0 (invFlow t x)) :
    HasDerivAt (fun s => density rho0 s x)
      ((fderiv ℝ rho0 (invFlow t x)) (invTime t x)) t ∧
    (∀ d : Fin 3, HasDerivAt (fun s => density rho0 t (Function.update x d s))
      ((fderiv ℝ rho0 (invFlow t x)) (invColumn t d)) (x d)) := by
  constructor
  · exact smooth.hasFDerivAt.comp_hasDerivAt t (inverse_time_derivative t x)
  · intro d
    have hs : HasFDerivAt rho0 (fderiv ℝ rho0 (invFlow t x)) (invFlow t (Function.update x d (x d))) := by
      simpa using smooth.hasFDerivAt
    have h := hs.comp_hasDerivAt (x d) (inverse_coordinate_derivative t x d)
    simpa [density] using h

theorem density_transport (rho0 : Space → ℝ) (t : ℝ) (x : Space)
    (smooth : DifferentiableAt ℝ rho0 (invFlow t x)) :
    deriv (fun s => density rho0 s x) t +
      velocity t x 0 * deriv (fun s => density rho0 t (Function.update x 0 s)) (x 0) +
      velocity t x 1 * deriv (fun s => density rho0 t (Function.update x 1 s)) (x 1) +
      velocity t x 2 * deriv (fun s => density rho0 t (Function.update x 2 s)) (x 2) = 0 := by
  obtain ⟨ht,hx⟩ := density_derivatives rho0 t x smooth
  rw [ht.deriv,(hx 0).deriv,(hx 1).deriv,(hx 2).deriv]
  have h := congrArg (fderiv ℝ rho0 (invFlow t x)) (inverse_transport_identity t x)
  simpa only [map_add,map_smul,smul_eq_mul,map_zero] using h

def velTime (t : ℝ) (x : Space) : Space := ![-x 2+2*t,-1,0]
def velColumn (t : ℝ) (d : Fin 3) : Space :=
  match d with
  | 0 => ![0,0,0]
  | 1 => ![1,0,0]
  | 2 => ![-t,1,0]

theorem velocity_time_derivative (t : ℝ) (x : Space) :
    HasDerivAt (fun s => velocity s x) (velTime t x) t := by
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · have h := ((hasDerivAt_const t (x 1)).sub ((hasDerivAt_id t).mul_const (x 2))).add
      ((hasDerivAt_id t).pow 2)
    convert h using 1; simp [velTime]
  · simpa [velocity,velTime] using (hasDerivAt_const t (x 2)).sub (hasDerivAt_id t)
  · exact hasDerivAt_const t 1

theorem velocity_coordinate_affine (t : ℝ) (x : Space) (d : Fin 3) (s : ℝ) :
    velocity t (Function.update x d s) = velocity t x + (s-x d) • velColumn t d := by
  funext k
  fin_cases d <;> fin_cases k <;> simp [velocity,velColumn] <;> ring

theorem velocity_coordinate_derivative (t : ℝ) (x : Space) (d : Fin 3) :
    HasDerivAt (fun s => velocity t (Function.update x d s)) (velColumn t d) (x d) := by
  have eq : (fun s => velocity t (Function.update x d s)) =
      (fun s => velocity t x + (s-x d) • velColumn t d) := by
    funext s
    exact velocity_coordinate_affine t x d s
  rw [eq]
  simpa using (((hasDerivAt_id (x d)).sub_const (x d)).smul_const
    (velColumn t d)).const_add (velocity t x)

def kinetic (v : Space) : ℝ := (v 0^2+v 1^2+v 2^2)/2
def kineticD (v dv : Space) : ℝ := v 0*dv 0+v 1*dv 1+v 2*dv 2

def conserved (r : ℝ) (v : Space) : State := ![r,r*v 0,r*v 1,r*v 2,1+r*kinetic v]
def conservedD (r : ℝ) (v : Space) (dr : ℝ) (dv : Space) : State :=
  ![dr,dr*v 0+r*dv 0,dr*v 1+r*dv 1,dr*v 2+r*dv 2,dr*kinetic v+r*kineticD v dv]
def flux (r : ℝ) (v : Space) (d : Fin 3) : State :=
  ![r*v d, r*v 0*v d+(if d=0 then 1 else 0),
    r*v 1*v d+(if d=1 then 1 else 0),r*v 2*v d+(if d=2 then 1 else 0),
    (2+r*kinetic v)*v d]
def fluxD (r : ℝ) (v : Space) (dr : ℝ) (dv : Space) (d : Fin 3) : State :=
  ![dr*v d+r*dv d,
    (dr*v 0+r*dv 0)*v d+r*v 0*dv d,
    (dr*v 1+r*dv 1)*v d+r*v 1*dv d,
    (dr*v 2+r*dv 2)*v d+r*v 2*dv d,
    (dr*kinetic v+r*kineticD v dv)*v d+(2+r*kinetic v)*dv d]

theorem kinetic_derivative {r : ℝ} {v : ℝ → Space} {dv : Space}
    (hv : HasDerivAt v dv r) :
    HasDerivAt (fun s => kinetic (v s)) (kineticD (v r) dv) r := by
  have h := (((((hasDerivAt_pi.mp hv) 0).pow 2).add
    (((hasDerivAt_pi.mp hv) 1).pow 2)).add (((hasDerivAt_pi.mp hv) 2).pow 2)).mul_const (1/2 : ℝ)
  convert h using 1 <;> simp [kinetic,kineticD,div_eq_mul_inv]; ring

theorem conserved_derivative {s : ℝ} {r : ℝ → ℝ} {v : ℝ → Space} {dr : ℝ} {dv : Space}
    (hr : HasDerivAt r dr s) (hv : HasDerivAt v dv s) :
    HasDerivAt (fun z => conserved (r z) (v z)) (conservedD (r s) (v s) dr dv) s := by
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · exact hr
  · simpa [conserved,conservedD,add_comm] using hr.mul ((hasDerivAt_pi.mp hv) 0)
  · simpa [conserved,conservedD,add_comm] using hr.mul ((hasDerivAt_pi.mp hv) 1)
  · simpa [conserved,conservedD,add_comm] using hr.mul ((hasDerivAt_pi.mp hv) 2)
  · simpa [conserved,conservedD,add_comm] using (hr.mul (kinetic_derivative hv)).const_add 1

theorem flux_derivative {s : ℝ} {r : ℝ → ℝ} {v : ℝ → Space} {dr : ℝ} {dv : Space}
    (hr : HasDerivAt r dr s) (hv : HasDerivAt v dv s) (d : Fin 3) :
    HasDerivAt (fun z => flux (r z) (v z) d) (fluxD (r s) (v s) dr dv d) s := by
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · simpa [flux,fluxD,add_comm] using hr.mul ((hasDerivAt_pi.mp hv) d)
  · simpa [flux,fluxD,add_comm] using ((hr.mul ((hasDerivAt_pi.mp hv) 0)).mul
      ((hasDerivAt_pi.mp hv) d)).add_const (if d=0 then 1 else 0)
  · simpa [flux,fluxD,add_comm] using ((hr.mul ((hasDerivAt_pi.mp hv) 1)).mul
      ((hasDerivAt_pi.mp hv) d)).add_const (if d=1 then 1 else 0)
  · simpa [flux,fluxD,add_comm] using ((hr.mul ((hasDerivAt_pi.mp hv) 2)).mul
      ((hasDerivAt_pi.mp hv) d)).add_const (if d=2 then 1 else 0)
  · simpa [flux,fluxD,add_comm] using ((hr.mul (kinetic_derivative hv)).const_add 2).mul
      ((hasDerivAt_pi.mp hv) d)

def solution (rho0 : Space → ℝ) (t : ℝ) (x : Space) : State :=
  conserved (density rho0 t x) (velocity t x)
def solutionFlux (rho0 : Space → ℝ) (t : ℝ) (x : Space) (d : Fin 3) : State :=
  flux (density rho0 t x) (velocity t x) d

theorem residual_algebra (t : ℝ) (x : Space) (r rt r0 r1 r2 : ℝ)
    (transport : rt + velocity t x 0*r0 + velocity t x 1*r1 + velocity t x 2*r2 = 0) :
    conservedD r (velocity t x) rt (velTime t x) +
      fluxD r (velocity t x) r0 (velColumn t 0) 0 +
      fluxD r (velocity t x) r1 (velColumn t 1) 1 +
      fluxD r (velocity t x) r2 (velColumn t 2) 2 = 0 := by
  funext i
  simp [velocity] at transport
  fin_cases i <;> simp [conservedD,fluxD,velocity,velTime,velColumn,kinetic,kineticD]
  · simpa [mul_comm] using transport
  · linear_combination (x 1-t*x 2+t^2)*transport
  · linear_combination (x 2-t)*transport
  · simpa [mul_comm] using transport
  · linear_combination (((x 1-t*x 2+t^2)^2+(x 2-t)^2+1)/2)*transport

theorem full_euler_equations (rho0 : Space → ℝ) (t : ℝ) (x : Space)
    (smooth : DifferentiableAt ℝ rho0 (invFlow t x)) :
    deriv (fun s => solution rho0 s x) t +
      deriv (fun s => solutionFlux rho0 t (Function.update x 0 s) 0) (x 0) +
      deriv (fun s => solutionFlux rho0 t (Function.update x 1 s) 1) (x 1) +
      deriv (fun s => solutionFlux rho0 t (Function.update x 2 s) 2) (x 2) = 0 := by
  obtain ⟨hr,hx⟩ := density_derivatives rho0 t x smooth
  have ht := (conserved_derivative hr (velocity_time_derivative t x)).deriv
  have hd (d : Fin 3) := (flux_derivative (hx d) (velocity_coordinate_derivative t x d) d).deriv
  simp only [Function.update_eq_self] at hd
  change deriv (fun s => conserved (density rho0 s x) (velocity s x)) t + _ + _ + _ = 0
  rw [ht]
  change conservedD _ _ _ _ +
    deriv (fun s => flux (density rho0 t (Function.update x 0 s)) (velocity t (Function.update x 0 s)) 0) (x 0) +
    deriv (fun s => flux (density rho0 t (Function.update x 1 s)) (velocity t (Function.update x 1 s)) 1) (x 1) +
    deriv (fun s => flux (density rho0 t (Function.update x 2 s)) (velocity t (Function.update x 2 s)) 2) (x 2) = 0
  rw [hd 0,hd 1,hd 2]
  apply residual_algebra
  have transport := density_transport rho0 t x smooth
  rwa [hr.deriv,(hx 0).deriv,(hx 1).deriv,(hx 2).deriv] at transport

theorem initial_state (rho0 : Space → ℝ) (x : Space) :
    solution rho0 0 x = conserved (rho0 x) ![x 1,x 2,1] := by
  have inv : invFlow 0 x = x := by
    funext i
    fin_cases i <;> simp [invFlow]
  simp [solution,density,inv,velocity]

theorem boundary_moves_with_fluid (t : ℝ) (a : Space) :
    deriv (fun s => flow s a) t = velocity t (flow t a) := by
  rw [(flow_derivative t a).deriv,material_velocity]

-- Canonical gamma=2 ideal-gas pressure and conservative Euler flux.
def pressure (u : State) : ℝ := u 4-(u 1^2+u 2^2+u 3^2)/(2*u 0)
def eulerFlux (u : State) (d : Fin 3) : State :=
  let vd := u ⟨d.val+1,by omega⟩/u 0
  ![u ⟨d.val+1,by omega⟩,u 1*vd+(if d=0 then pressure u else 0),
    u 2*vd+(if d=1 then pressure u else 0),
    u 3*vd+(if d=2 then pressure u else 0),(u 4+pressure u)*vd]

theorem pressure_of_conserved (r : ℝ) (v : Space) :
    pressure (conserved r v) = 1 := by
  simp [pressure,conserved,kinetic]
  field_simp
  ring

theorem canonical_flux (r : ℝ) (v : Space) (positive : 0 < r) (d : Fin 3) :
    eulerFlux (conserved r v) d = flux r v d := by
  have hp := pressure_of_conserved r v
  have hn : r ≠ 0 := ne_of_gt positive
  simp only [eulerFlux,hp]
  funext i
  fin_cases d <;> fin_cases i <;> simp [conserved,flux,hn,add_comm] <;> (left; ring)

theorem physical_euler_equations (rho0 : Space → ℝ) (t : ℝ) (x : Space)
    (smooth : DifferentiableAt ℝ rho0 (invFlow t x))
    (positive : ∀ a, 0 < rho0 a) :
    deriv (fun s => solution rho0 s x) t +
      deriv (fun s => eulerFlux (solution rho0 t (Function.update x 0 s)) 0) (x 0) +
      deriv (fun s => eulerFlux (solution rho0 t (Function.update x 1 s)) 1) (x 1) +
      deriv (fun s => eulerFlux (solution rho0 t (Function.update x 2 s)) 2) (x 2) = 0 := by
  have eq (y : Space) (d : Fin 3) : eulerFlux (solution rho0 t y) d = solutionFlux rho0 t y d :=
    canonical_flux _ _ (positive _) d
  simp_rw [eq]
  exact full_euler_equations rho0 t x smooth

theorem solution_is_C1 (rho0 : Space → ℝ) (smooth : ContDiff ℝ 1 rho0) :
    ContDiff ℝ 1 (fun tx : ℝ × Space => solution rho0 tx.1 tx.2) := by
  have hi : ContDiff ℝ 1 (fun tx : ℝ × Space => invFlow tx.1 tx.2) := by
    apply contDiff_pi.mpr
    intro d
    fin_cases d <;> dsimp [invFlow] <;> fun_prop
  have hr : ContDiff ℝ 1 (fun tx : ℝ × Space => density rho0 tx.1 tx.2) := smooth.comp hi
  have hv : ContDiff ℝ 1 (fun tx : ℝ × Space => velocity tx.1 tx.2) := by
    apply contDiff_pi.mpr
    intro d
    fin_cases d <;> dsimp [velocity] <;> fun_prop
  have hv0 := contDiff_pi.mp hv 0
  have hv1 := contDiff_pi.mp hv 1
  have hv2 := contDiff_pi.mp hv 2
  apply contDiff_pi.mpr
  intro i
  fin_cases i <;> dsimp [solution,conserved,kinetic] <;> fun_prop
end ShearEuler
