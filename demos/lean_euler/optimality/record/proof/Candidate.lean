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
import Mathlib.Analysis.Normed.Group.Constructions
import Mathlib.Analysis.Normed.Field.Basic
import Mathlib.Data.Real.Archimedean
import Mathlib.Data.Fintype.Pi
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Positivity
import Mathlib.Analysis.Calculus.BumpFunction.InnerProduct
import Mathlib.Analysis.Calculus.ContDiff.RCLike
import Mathlib.Data.Finset.Card


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


noncomputable section
namespace Grid
abbrev Space := Fin 3 → ℝ
abbrev Cell (n : ℕ) := Fin 3 → Fin n

def center (n : ℕ) (i : Cell n) : Space := fun d => ((i d:ℕ)+1/2 : ℝ)/n

def locate1 (n : ℕ) (hn : 0 < n) (x : ℝ) : Fin n :=
  ⟨min ⌊(n:ℝ)*x⌋₊ (n-1), lt_of_le_of_lt (min_le_right _ _) (by omega)⟩
def locate (n : ℕ) (hn : 0 < n) (x : Space) : Cell n := fun d => locate1 n hn (x d)

theorem locate1_bounds (n : ℕ) (hn : 0 < n) (x : ℝ) (hx0 : 0 ≤ x) (hx1 : x ≤ 1) :
    (locate1 n hn x:ℕ) ≤ (n:ℝ)*x ∧ (n:ℝ)*x ≤ (locate1 n hn x:ℕ)+1 := by
  have hnR : (0:ℝ) < n := by exact_mod_cast hn
  have hx : 0 ≤ (n:ℝ)*x := mul_nonneg hnR.le hx0
  have hlo := Nat.floor_le hx
  have hhi := (Nat.lt_floor_add_one ((n:ℝ)*x)).le
  dsimp [locate1]
  by_cases h : ⌊(n:ℝ)*x⌋₊ ≤ n-1
  · simpa [min_eq_left h] using And.intro hlo hhi
  · have hm : min ⌊(n:ℝ)*x⌋₊ (n-1) = n-1 := min_eq_right (by omega)
    rw [hm]
    have hnsub : ((n-1:ℕ):ℝ) = (n:ℝ)-1 := by rw [Nat.cast_sub (by omega)]; norm_num
    rw [hnsub]
    constructor
    · have hh : (n:ℝ)-1 ≤ (⌊(n:ℝ)*x⌋₊:ℝ) := by
        rw [← hnsub]
        exact_mod_cast (show n-1 ≤ ⌊(n:ℝ)*x⌋₊ by omega)
      linarith
    · nlinarith

theorem center_error_coordinate (n : ℕ) (hn : 0 < n) (x : ℝ)
    (hx0 : 0 ≤ x) (hx1 : x ≤ 1) :
    |x-(((locate1 n hn x:ℕ):ℝ)+1/2)/(n:ℝ)| ≤ 1/(2*(n:ℝ)) := by
  obtain ⟨hl,hu⟩ := locate1_bounds n hn x hx0 hx1
  have hp : (0:ℝ) < n := by exact_mod_cast hn
  apply (abs_le).mpr
  have hA : (n:ℝ)*((((locate1 n hn x:ℕ):ℝ)+1/2)/(n:ℝ)) = ((locate1 n hn x:ℕ):ℝ)+1/2 :=
    mul_div_cancel₀ _ (ne_of_gt hp)
  have hB : (n:ℝ)*(1/(2*(n:ℝ))) = 1/2 := by field_simp
  constructor <;> nlinarith

theorem center_covers_cube (n : ℕ) (hn : 0 < n) (x : Space)
    (hx : ∀ d, 0 ≤ x d ∧ x d ≤ 1) :
    ‖x-center n (locate n hn x)‖ ≤ 1/(2*(n:ℝ)) := by
  apply (pi_norm_le_iff_of_nonneg (by positivity)).mpr
  intro d
  simpa [center,locate,Real.norm_eq_abs] using center_error_coordinate n hn (x d) (hx d).1 (hx d).2

theorem center_in_cube (n : ℕ) (hn : 0 < n) (i : Cell n) :
    ∀ d, 0 ≤ center n i d ∧ center n i d ≤ 1 := by
  intro d
  have hp : (0:ℝ) < n := by exact_mod_cast hn
  have hi : ((i d:ℕ):ℝ) < n := by exact_mod_cast (i d).isLt
  have h0 : (0:ℝ) ≤ (i d:ℕ) := Nat.cast_nonneg _
  dsimp [center]
  constructor
  · positivity
  · apply (div_le_iff₀ hp).mpr
    have hj : ((i d:ℕ):ℝ)+1 ≤ n := by exact_mod_cast (Nat.succ_le_of_lt (i d).isLt)
    linarith

theorem number_of_cells (n : ℕ) : Fintype.card (Cell n) = n^3 := by simp [Cell]

theorem centers_separated (n : ℕ) (hn : 0 < n) (i j : Cell n) (hne : i ≠ j) :
    1/(n:ℝ) ≤ ‖center n i-center n j‖ := by
  have hp : (0:ℝ) < n := by exact_mod_cast hn
  obtain ⟨d,hd⟩ : ∃ d, i d ≠ j d := Function.ne_iff.mp hne
  have hv : (i d:ℕ) ≠ (j d:ℕ) := by exact fun h => hd (Fin.ext h)
  have hdif : (1:ℝ) ≤ |((i d:ℕ):ℝ)-((j d:ℕ):ℝ)| := by
    rcases lt_or_gt_of_ne hv with h | h
    · have hh : ((i d:ℕ):ℝ)+1 ≤ (j d:ℕ) := by exact_mod_cast (Nat.succ_le_of_lt h)
      rw [abs_of_nonpos (by linarith)]
      linarith
    · have hh : ((j d:ℕ):ℝ)+1 ≤ (i d:ℕ) := by exact_mod_cast (Nat.succ_le_of_lt h)
      rw [abs_of_nonneg (by linarith)]
      linarith
  have heq : center n i d-center n j d = (((i d:ℕ):ℝ)-((j d:ℕ):ℝ))/(n:ℝ) := by
    dsimp [center]
    ring
  calc
    1/(n:ℝ) ≤ |center n i d-center n j d| := by
      rw [heq,abs_div,abs_of_pos hp]
      exact div_le_div_of_nonneg_right hdif hp.le
    _ ≤ ‖center n i-center n j‖ := by
      simpa only [Real.norm_eq_abs,Pi.sub_apply] using norm_le_pi_norm (center n i-center n j) d

def cells (n : ℕ) : List (Cell n) :=
  (List.finRange n).flatMap (fun i => (List.finRange n).flatMap (fun j =>
    (List.finRange n).map (fun k => ![i,j,k])))

theorem mem_cells (n : ℕ) (i : Cell n) : i ∈ cells n := by
  have heq : ![i 0,i 1,i 2] = i := by
    funext d
    fin_cases d <;> rfl
  simp only [cells,List.mem_flatMap,List.mem_finRange,true_and,List.mem_map]
  exact ⟨i 0,i 1,i 2,heq⟩

theorem cells_length (n : ℕ) : (cells n).length = n^3 := by
  simp [cells,List.length_flatMap]
  ring
end Grid


noncomputable section
open scoped Topology ContDiff
namespace Recovery
abbrev Space := Fin 3 → ℝ

def InCube (x : Space) : Prop := ∀ d, 0 ≤ x d ∧ x d ≤ 1

def Admissible (L : ℝ) (f : Space → ℝ) : Prop :=
  ContDiff ℝ 1 f ∧ (∀ x, 1 ≤ f x ∧ f x ≤ 2) ∧
    (∀ x y, |f x-f y| ≤ L*‖x-y‖)

-- This supplies the hard inputs constructively from the library's proved
-- existence theorem. The Lipschitz constant is fixed before grid refinement.
theorem exists_base_bump : ∃ (b : Space → ℝ) (K : ℝ),
    1 ≤ K ∧ ContDiff ℝ 1 b ∧ (∀ x, 0 ≤ b x ∧ b x ≤ 1) ∧ b 0 = 1 ∧
    (∀ x, 1/2 ≤ ‖x‖ → b x = 0) ∧
    (∀ x y, |b x-b y| ≤ K*‖x-y‖) := by
  let base : ContDiffBump (0 : ℝ) :=
    { rIn := 1/4, rOut := 1/2, rIn_pos := by norm_num, rIn_lt_rOut := by norm_num }
  let b : Space → ℝ := fun x => base (x 0)*base (x 1)*base (x 2)
  have hb : ∀ x, 0 ≤ b x ∧ b x ≤ 1 := by
    intro x
    have h01 : base (x 0)*base (x 1) ≤ 1 := by
      simpa using mul_le_mul (base.le_one (x := x 0)) (base.le_one (x := x 1)) base.nonneg (by norm_num : (0:ℝ) ≤ 1)
    have h012 : b x ≤ 1 := by
      simpa [b] using mul_le_mul h01 (base.le_one (x := x 2)) base.nonneg (by norm_num : (0:ℝ) ≤ 1)
    exact ⟨mul_nonneg (mul_nonneg base.nonneg base.nonneg) base.nonneg,h012⟩
  have hd : ContDiff ℝ 1 b := by
    have hbase : ContDiff ℝ 1 base := base.contDiff
    dsimp [b]
    fun_prop
  have hz : ∀ x, 1/2 ≤ ‖x‖ → b x = 0 := by
    intro x hx
    have hnot : ¬ ∀ d : Fin 3, ‖x d‖ < 1/2 := by
      intro h
      have hh := (pi_norm_lt_iff (by norm_num : (0:ℝ) < 1/2)).mpr h
      linarith
    obtain ⟨d,hd⟩ := not_forall.mp hnot
    have hzero : base (x d) = 0 := by
      apply base.zero_of_le_dist
      simpa [base,dist_zero_right] using le_of_not_gt hd
    fin_cases d
    · have hh : base (x 0) = 0 := hzero
      simp [b,hh]
    · have hh : base (x 1) = 0 := hzero
      simp [b,hh]
    · have hh : base (x 2) = 0 := hzero
      simp [b,hh]
  have hs : Function.support b ⊆ Metric.closedBall 0 (1/2) := by
    intro x hx
    have hh : ‖x‖ < 1/2 := lt_of_not_ge (fun h => hx (hz x h))
    simpa only [Metric.mem_closedBall,dist_zero_right] using hh.le
  have hc : HasCompactSupport b :=
    (isCompact_closedBall (0 : Space) (1/2)).of_isClosed_subset isClosed_closure (closure_minimal hs Metric.isClosed_closedBall)
  obtain ⟨K, hK⟩ := ContDiff.lipschitzWith_of_hasCompactSupport hc hd (by simp)
  refine ⟨b, max (K:ℝ) 1, le_max_right _ _, hd, hb, ?_, hz, ?_⟩
  · have hbase : base 0 = 1 := base.one_of_mem_closedBall (by simp [base])
    simp [b,hbase]
  · intro x y
    calc
      |b x-b y| ≤ (K:ℝ)*‖x-y‖ := by simpa only [Real.norm_eq_abs] using hK.norm_sub_le x y
      _ ≤ max (K:ℝ) 1*‖x-y‖ := mul_le_mul_of_nonneg_right (le_max_left _ _) (norm_nonneg _)

-- A decision tree permits adaptive real-valued queries and arbitrary outputs.
-- Every path terminates; no input formula or hidden density oracle is in a leaf.
inductive QueryTree (Output : Type) where
  | done : Output → QueryTree Output
  | ask : Space → (ℝ → QueryTree Output) → QueryTree Output

def QueryTree.run {O : Type} (a : QueryTree O) (f : Space → ℝ) : O :=
  match a with
  | .done o => o
  | .ask q next => (next (f q)).run f

def QueryTree.queries {O : Type} (a : QueryTree O) (f : Space → ℝ) : List Space :=
  match a with
  | .done _ => []
  | .ask q next => q :: (next (f q)).queries f

theorem adaptive_indistinguishability {O : Type} (a : QueryTree O) (f g : Space → ℝ)
    (same : ∀ q ∈ a.queries f, g q = f q) : a.run g = a.run f := by
  induction a with
  | done o => rfl
  | ask q next ih =>
    have hq : g q = f q := same q (by simp [QueryTree.queries])
    simp only [QueryTree.run,hq]
    apply ih (f q)
    intro p hp
    exact same p (by simp [QueryTree.queries,hp])

def QueryTree.map {O P : Type} (a : QueryTree O) (f : O → P) : QueryTree P :=
  match a with
  | .done o => .done (f o)
  | .ask q next => .ask q (fun y => (next y).map f)

theorem QueryTree.run_map {O P : Type} (a : QueryTree O) (g : O → P) (f : Space → ℝ) :
    (a.map g).run f = g (a.run f) := by
  induction a with
  | done o => rfl
  | ask q next ih => exact ih (f q)

theorem QueryTree.queries_map {O P : Type} (a : QueryTree O) (g : O → P) (f : Space → ℝ) :
    (a.map g).queries f = a.queries f := by
  induction a with
  | done o => rfl
  | ask q next ih => simp [QueryTree.map,QueryTree.queries,ih]

def tabulate {I : Type} [DecidableEq I] (qs : List I) (loc : I → Space) : QueryTree (I → ℝ) :=
  match qs with
  | [] => .done (fun _ => 0)
  | i::rest => .ask (loc i) (fun y => (tabulate rest loc).map (fun data => Function.update data i y))

theorem tabulate_queries {I : Type} [DecidableEq I] (qs : List I) (loc : I → Space) (f : Space → ℝ) :
    (tabulate qs loc).queries f = qs.map loc := by
  induction qs with
  | nil => rfl
  | cons i rest ih => simp [tabulate,QueryTree.queries,QueryTree.queries_map,ih]

theorem tabulate_values {I : Type} [DecidableEq I] (qs : List I) (loc : I → Space) (f : Space → ℝ) :
    ∀ i ∈ qs, (tabulate qs loc).run f i = f (loc i) := by
  induction qs with
  | nil => simp
  | cons j rest ih =>
    intro i hi
    simp only [tabulate,QueryTree.run,QueryTree.run_map]
    by_cases hij : i=j
    · subst i
      simp
    · rw [Function.update_of_ne hij]
      apply ih i
      simpa [hij] using hi

def perturb (b : Space → ℝ) (a n : ℝ) (c : Space) (x : Space) : ℝ :=
  3/2+a*b (n • (x-c))

theorem perturb_admissible (b : Space → ℝ) (K L a n : ℝ) (c : Space)
    (hb : ContDiff ℝ 1 b) (hbounds : ∀ x, 0 ≤ b x ∧ b x ≤ 1)
    (hlip : ∀ x y, |b x-b y| ≤ K*‖x-y‖)
    (hn : 0 ≤ n) (ha : |a| ≤ 1/2) (hcost : |a| *K*n ≤ L) :
    Admissible L (perturb b a n c) := by
  refine ⟨?_,?_,?_⟩
  · unfold perturb
    fun_prop
  · intro x
    have hab : |a*b (n • (x-c))| ≤ 1/2 := by
      rw [abs_mul,abs_of_nonneg (hbounds _).1]
      calc
        |a| *b (n • (x-c)) ≤ |a| *1 := mul_le_mul_of_nonneg_left (hbounds _).2 (abs_nonneg _)
        _ ≤ 1/2 := by simpa using ha
    have hh := abs_le.mp hab
    dsimp [perturb]
    constructor <;> linarith
  · intro x y
    have heq : perturb b a n c x-perturb b a n c y = a*(b (n • (x-c))-b (n • (y-c))) := by
      dsimp [perturb]
      ring
    rw [heq,abs_mul]
    have hnorm : ‖n • (x-c)-n • (y-c)‖ = n*‖x-y‖ := by
      rw [← smul_sub,sub_sub_sub_cancel_right,norm_smul,Real.norm_eq_abs,abs_of_nonneg hn]
    calc
      |a| *|b (n • (x-c))-b (n • (y-c))| ≤ |a| *(K*‖n • (x-c)-n • (y-c)‖) :=
        mul_le_mul_of_nonneg_left (hlip _ _) (abs_nonneg _)
      _ = (|a| *K*n)*‖x-y‖ := by rw [hnorm]; ring
      _ ≤ L*‖x-y‖ := mul_le_mul_of_nonneg_right hcost (norm_nonneg _)
end Recovery


noncomputable section
namespace Optimality
open Recovery Grid

-- The lower bound applies to arbitrary adaptive sampling, not a prespecified
-- finite set of candidate solvers.
theorem at_most_one_cell (b : Recovery.Space → ℝ)
    (hz : ∀ x, 1/2 ≤ ‖x‖ → b x = 0)
    (n : ℕ) (hn : 0 < n) (q : Recovery.Space) (i j : Grid.Cell n)
    (hi : b ((n:ℝ) • (q-Grid.center n i)) ≠ 0)
    (hj : b ((n:ℝ) • (q-Grid.center n j)) ≠ 0) : i = j := by
  have hp : (0:ℝ) < n := by exact_mod_cast hn
  have normi : ‖(n:ℝ) • (q-Grid.center n i)‖ < 1/2 := lt_of_not_ge (fun h => hi (hz _ h))
  have normj : ‖(n:ℝ) • (q-Grid.center n j)‖ < 1/2 := lt_of_not_ge (fun h => hj (hz _ h))
  rw [norm_smul,Real.norm_eq_abs,abs_of_pos hp] at normi normj
  by_contra hne
  have sep := Grid.centers_separated n hn i j hne
  have tri := norm_sub_le_norm_sub_add_norm_sub (Grid.center n i) q (Grid.center n j)
  rw [norm_sub_rev (Grid.center n i) q] at tri
  have hscale : (n:ℝ)*(1/(n:ℝ)) = 1 := by field_simp
  nlinarith

theorem exists_unqueried_cell (b : Recovery.Space → ℝ)
    (hz : ∀ x, 1/2 ≤ ‖x‖ → b x = 0)
    (n : ℕ) (hn : 0 < n) (queries : List Recovery.Space)
    (small : queries.length < n^3) :
    ∃ i : Grid.Cell n, ∀ q ∈ queries, b ((n:ℝ) • (q-Grid.center n i)) = 0 := by
  classical
  let fallback : Grid.Cell n := fun _ => ⟨0,hn⟩
  let select (q : Recovery.Space) : Grid.Cell n :=
    if h : ∃ i : Grid.Cell n, b ((n:ℝ) • (q-Grid.center n i)) ≠ 0 then h.choose else fallback
  let observed : Finset (Grid.Cell n) := queries.toFinset.image select
  have hc : observed.card < (Finset.univ : Finset (Grid.Cell n)).card := by
    calc
      observed.card ≤ queries.toFinset.card := Finset.card_image_le
      _ ≤ queries.length := List.toFinset_card_le queries
      _ < n^3 := small
      _ = (Finset.univ : Finset (Grid.Cell n)).card := by simp
  obtain ⟨i,_,hi⟩ := Finset.exists_mem_notMem_of_card_lt_card hc
  refine ⟨i,?_⟩
  intro q hq
  by_contra hneq
  have hex : ∃ j : Grid.Cell n, b ((n:ℝ) • (q-Grid.center n j)) ≠ 0 := ⟨i,hneq⟩
  have hselect : b ((n:ℝ) • (q-Grid.center n (select q))) ≠ 0 := by
    dsimp [select]
    rw [dif_pos hex]
    exact hex.choose_spec
  have heq : select q = i := at_most_one_cell b hz n hn q _ i hselect hneq
  apply hi
  exact Finset.mem_image.mpr ⟨q,List.mem_toFinset.mpr hq,heq⟩

-- A density-recovery specification is necessary for every full-state Euler
-- approximation because density is its first conserved component.
def AccurateDensity (L eps : ℝ) (a : Recovery.QueryTree (Recovery.Space → ℝ)) : Prop :=
  ∀ f, Recovery.Admissible L f → ∀ x, Recovery.InCube x → |a.run f x-f x| ≤ eps

theorem adaptive_query_lower_bound (b : Recovery.Space → ℝ) (K L eps : ℝ)
    (hb : ContDiff ℝ 1 b) (hbounds : ∀ x, 0 ≤ b x ∧ b x ≤ 1) (h0 : b 0 = 1)
    (hz : ∀ x, 1/2 ≤ ‖x‖ → b x = 0)
    (hlip : ∀ x y, |b x-b y| ≤ K*‖x-y‖)
    (heps : 0 < eps) (hepsmax : eps ≤ 1/4)
    (n : ℕ) (hn : 0 < n) (hbudget : 2*eps*K*(n:ℝ) ≤ L)
    (a : Recovery.QueryTree (Recovery.Space → ℝ)) (correct : AccurateDensity L eps a) :
    n^3 ≤ (a.queries (fun _ => 3/2)).length := by
  by_contra hnq
  obtain ⟨i,hi⟩ := exists_unqueried_cell b hz n hn (a.queries (fun _ => 3/2)) (by omega)
  let fplus := Recovery.perturb b (2*eps) n (Grid.center n i)
  let fminus := Recovery.perturb b (-2*eps) n (Grid.center n i)
  have hplus : Recovery.Admissible L fplus := by
    apply Recovery.perturb_admissible b K L (2*eps) n (Grid.center n i) hb hbounds hlip
    · positivity
    · rw [abs_of_pos (by positivity)]
      linarith
    · simpa [abs_of_pos (by positivity : 0 < 2*eps)] using hbudget
  have hminus : Recovery.Admissible L fminus := by
    apply Recovery.perturb_admissible b K L (-2*eps) n (Grid.center n i) hb hbounds hlip
    · positivity
    · rw [abs_of_neg (by linarith)]
      linarith
    · rw [abs_of_neg (by linarith)]
      convert hbudget using 1; ring
  have ep : a.run fplus = a.run (fun _ => 3/2) := by
    apply Recovery.adaptive_indistinguishability
    intro q hq
    simp [fplus,Recovery.perturb,hi q hq]
  have em : a.run fminus = a.run (fun _ => 3/2) := by
    apply Recovery.adaptive_indistinguishability
    intro q hq
    simp [fminus,Recovery.perturb,hi q hq]
  have hp := correct fplus hplus (Grid.center n i) (Grid.center_in_cube n hn i)
  have hm := correct fminus hminus (Grid.center n i) (Grid.center_in_cube n hn i)
  rw [ep] at hp
  rw [em] at hm
  simp [fplus,fminus,Recovery.perturb,h0] at hp hm
  have hp' := abs_le.mp hp
  have hm' := abs_le.mp hm
  linarith

-- The reconstructed velocity is exact. Density approximation propagates to
-- all five conserved components with a uniform factor at most 3/2.
theorem conserved_error (r s : ℝ) (a : Recovery.Space) (ha : Recovery.InCube a) :
    ‖ShearEuler.conserved r ![a 1,a 2,1]-ShearEuler.conserved s ![a 1,a 2,1]‖ ≤
      (3/2)*|r-s| := by
  have h1 := ha 1
  have h2 := ha 2
  have hr := abs_nonneg (r-s)
  have hk0 : 0 ≤ (a 1^2+a 2^2+1)/2 := by positivity
  have hk1 : (a 1^2+a 2^2+1)/2 ≤ 3/2 := by nlinarith [sq_nonneg (a 1-1),sq_nonneg (a 2-1)]
  apply (pi_norm_le_iff_of_nonneg (by positivity)).mpr
  intro i
  fin_cases i <;> simp [ShearEuler.conserved,ShearEuler.kinetic,Real.norm_eq_abs]
  · nlinarith
  · rw [← sub_mul,abs_mul,abs_of_nonneg h1.1]
    nlinarith
  · rw [← sub_mul,abs_mul,abs_of_nonneg h2.1]
    nlinarith
  · nlinarith
  · rw [← sub_mul,abs_mul,abs_of_nonneg hk0]
    nlinarith

def samples (f : Recovery.Space → ℝ) (n : ℕ) : Grid.Cell n → ℝ := fun i => f (Grid.center n i)
def reconstruct (n : ℕ) (hn : 0 < n) (data : Grid.Cell n → ℝ) (t : ℝ) (x : Recovery.Space) : ShearEuler.State :=
  ShearEuler.conserved (data (Grid.locate n hn (ShearEuler.invFlow t x))) (ShearEuler.velocity t x)

theorem uniform_full_state_error (f : Recovery.Space → ℝ) (L : ℝ) (hL : 0 ≤ L)
    (hf : Recovery.Admissible L f) (n : ℕ) (hn : 0 < n) (t : ℝ) (a : Recovery.Space)
    (ha : Recovery.InCube a) :
    ‖reconstruct n hn (samples f n) t (ShearEuler.flow t a)-
      ShearEuler.solution f t (ShearEuler.flow t a)‖ ≤ 3*L/(4*(n:ℝ)) := by
  have hc := Grid.center_covers_cube n hn a ha
  have hd := hf.2.2 (Grid.center n (Grid.locate n hn a)) a
  rw [norm_sub_rev] at hd
  have hd' : |f (Grid.center n (Grid.locate n hn a))-f a| ≤ L/(2*(n:ℝ)) := by
    calc
      _ ≤ L*‖a-Grid.center n (Grid.locate n hn a)‖ := hd
      _ ≤ L*(1/(2*(n:ℝ))) := mul_le_mul_of_nonneg_left hc hL
      _ = L/(2*(n:ℝ)) := by ring
  simp only [reconstruct,samples,ShearEuler.solution,ShearEuler.density,
    ShearEuler.inverse_flow,ShearEuler.material_velocity]
  calc
    _ ≤ (3/2)*|f (Grid.center n (Grid.locate n hn a))-f a| := conserved_error _ _ a ha
    _ ≤ (3/2)*(L/(2*(n:ℝ))) := mul_le_mul_of_nonneg_left hd' (by norm_num)
    _ = 3*L/(4*(n:ℝ)) := by ring

-- The density lower bound above is unconditional once the fixed bump supplied
-- by Mathlib has been instantiated.
theorem exists_lower_bound_constant : ∃ K : ℝ, 1 ≤ K ∧
    ∀ (L eps : ℝ) (n : ℕ), 0 < eps → eps ≤ 1/4 → 0 < n → 2*eps*K*(n:ℝ) ≤ L →
    ∀ a : Recovery.QueryTree (Recovery.Space → ℝ), AccurateDensity L eps a →
      n^3 ≤ (a.queries (fun _ => 3/2)).length := by
  obtain ⟨b,K,hK,hb,hbounds,h0,hz,hlip⟩ := Recovery.exists_base_bump
  refine ⟨K,hK,?_⟩
  intro L eps n he hmax hn hbudget a hcorrect
  exact adaptive_query_lower_bound b K L eps hb hbounds h0 hz hlip he hmax n hn hbudget a hcorrect

def resolution (L eps : ℝ) : ℕ := ⌈3*L/(4*eps)⌉₊

theorem resolution_positive (L eps : ℝ) (hL : 0 < L) (he : 0 < eps) : 0 < resolution L eps := by
  apply Nat.one_le_ceil_iff.mpr
  positivity

theorem accuracy_at_tolerance (f : Recovery.Space → ℝ) (L eps : ℝ)
    (hL : 0 < L) (he : 0 < eps) (hf : Recovery.Admissible L f)
    (t : ℝ) (a : Recovery.Space) (ha : Recovery.InCube a) :
    ‖reconstruct (resolution L eps) (resolution_positive L eps hL he)
      (samples f (resolution L eps)) t (ShearEuler.flow t a)-
      ShearEuler.solution f t (ShearEuler.flow t a)‖ ≤ eps := by
  apply (uniform_full_state_error f L hL.le hf _ (resolution_positive L eps hL he) t a ha).trans
  have hceil := Nat.le_ceil (3*L/(4*eps))
  have hn : (0:ℝ) < resolution L eps := by exact_mod_cast resolution_positive L eps hL he
  apply (div_le_iff₀ (by positivity : (0:ℝ) < 4*(resolution L eps:ℝ))).mpr
  have hh := (div_le_iff₀ (by positivity : (0:ℝ) < 4*eps)).mp hceil
  change 3*L ≤ eps*(4*(⌈3*L/(4*eps)⌉₊:ℝ))
  nlinarith

theorem resolution_work_upper (L eps : ℝ) (hL : 0 < L) (he : 0 < eps) (heL : eps ≤ L) :
    ((resolution L eps)^3 : ℝ) ≤ (2*L/eps)^3 := by
  have hc := (Nat.ceil_lt_add_one (by positivity : (0:ℝ) ≤ 3*L/(4*eps))).le
  have hn : (resolution L eps:ℝ) ≤ 2*L/eps := by
    dsimp [resolution]
    apply hc.trans
    apply (le_div_iff₀ he).mpr
    have hcancel : (3*L/(4*eps))*eps = 3*L/4 := by field_simp
    nlinarith
  exact pow_le_pow_left₀ (by positivity) hn 3

theorem optimal_query_scaling : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps : ℝ, 1 ≤ L → 0 < eps → eps ≤ 1/(4*K) →
    ∀ a : Recovery.QueryTree (Recovery.Space → ℝ), AccurateDensity L eps a →
      (L/(4*K*eps))^3 ≤ ((a.queries (fun _ => 3/2)).length:ℝ) := by
  obtain ⟨K,hK,lower⟩ := exists_lower_bound_constant
  refine ⟨K,hK,?_⟩
  intro L eps hL he hsmall a hcorrect
  have hKp : 0 < K := by linarith
  have hLp : 0 < L := by linarith
  have hprod : 4*K*eps ≤ 1 := by
    have hh := (le_div_iff₀ (by positivity : 0 < 4*K)).mp hsmall
    nlinarith
  have hem : eps ≤ 1/4 := by nlinarith
  let x : ℝ := L/(2*K*eps)
  have hx2 : 2 ≤ x := by
    apply (le_div_iff₀ (by positivity : 0 < 2*K*eps)).mpr
    nlinarith
  let n := ⌊x⌋₊
  have hn : 0 < n := by
    have hh : 1 ≤ n := (Nat.one_le_floor_iff x).mpr (by linarith)
    omega
  have hfloor : (n:ℝ) ≤ x := Nat.floor_le (by linarith)
  have hfloor2 : x < (n:ℝ)+1 := Nat.lt_floor_add_one x
  have hnlarge : L/(4*K*eps) ≤ (n:ℝ) := by
    have heq : L/(4*K*eps) = x/2 := by dsimp [x]; ring
    rw [heq]
    linarith
  have hbudget : 2*eps*K*(n:ℝ) ≤ L := by
    have hh := (le_div_iff₀ (by positivity : 0 < 2*K*eps)).mp hfloor
    nlinarith
  have hqueries := lower L eps n he hem hn hbudget a hcorrect
  have hqueriesR : (n:ℝ)^3 ≤ ((a.queries (fun _ => 3/2)).length:ℝ) := by exact_mod_cast hqueries
  exact (pow_le_pow_left₀ (by positivity) hnlarge 3).trans hqueriesR

def samplingAlgorithm (n : ℕ) : Recovery.QueryTree (Grid.Cell n → ℝ) :=
  Recovery.tabulate (Grid.cells n) (Grid.center n)

theorem sampling_values (n : ℕ) (f : Recovery.Space → ℝ) :
    (samplingAlgorithm n).run f = samples f n := by
  funext i
  exact Recovery.tabulate_values (Grid.cells n) (Grid.center n) f i (Grid.mem_cells n i)

theorem sampling_queries (n : ℕ) (f : Recovery.Space → ℝ) :
    ((samplingAlgorithm n).queries f).length = n^3 := by
  simp [samplingAlgorithm,Recovery.tabulate_queries,Grid.cells_length]

def eulerAlgorithm (n : ℕ) (hn : 0 < n) (t : ℝ) : Recovery.QueryTree (Recovery.Space → ShearEuler.State) :=
  (samplingAlgorithm n).map (fun data => reconstruct n hn data t)

def AccurateEuler (t L eps : ℝ) (a : Recovery.QueryTree (Recovery.Space → ShearEuler.State)) : Prop :=
  ∀ f, Recovery.Admissible L f → ∀ x, Recovery.InCube x →
    ‖a.run f (ShearEuler.flow t x)-ShearEuler.solution f t (ShearEuler.flow t x)‖ ≤ eps

theorem euler_algorithm_accurate (L eps t : ℝ) (hL : 0 < L) (he : 0 < eps) :
    AccurateEuler t L eps (eulerAlgorithm (resolution L eps) (resolution_positive L eps hL he) t) := by
  intro f hf x hx
  simp only [eulerAlgorithm,Recovery.QueryTree.run_map,sampling_values]
  exact accuracy_at_tolerance f L eps hL he hf t x hx

theorem euler_algorithm_queries (n : ℕ) (hn : 0 < n) (t : ℝ) (f : Recovery.Space → ℝ) :
    ((eulerAlgorithm n hn t).queries f).length = n^3 := by
  simp only [eulerAlgorithm,Recovery.QueryTree.queries_map,sampling_queries]

def densityReduction (t : ℝ) (a : Recovery.QueryTree (Recovery.Space → ShearEuler.State)) :
    Recovery.QueryTree (Recovery.Space → ℝ) :=
  a.map (fun output x => output (ShearEuler.flow t x) 0)

theorem euler_implies_density (t L eps : ℝ) (a : Recovery.QueryTree (Recovery.Space → ShearEuler.State))
    (hcorrect : AccurateEuler t L eps a) : AccurateDensity L eps (densityReduction t a) := by
  intro f hf x hx
  have h := hcorrect f hf x hx
  have hcoord := norm_le_pi_norm (a.run f (ShearEuler.flow t x)-ShearEuler.solution f t (ShearEuler.flow t x)) 0
  have hh := hcoord.trans h
  simpa [densityReduction,Recovery.QueryTree.run_map,ShearEuler.solution,ShearEuler.conserved,
    ShearEuler.density,ShearEuler.inverse_flow,Real.norm_eq_abs] using hh

theorem optimal_euler_query_scaling : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps t : ℝ, 1 ≤ L → 0 < eps → eps ≤ 1/(4*K) →
    ∀ a : Recovery.QueryTree (Recovery.Space → ShearEuler.State), AccurateEuler t L eps a →
      (L/(4*K*eps))^3 ≤ ((a.queries (fun _ => 3/2)).length:ℝ) := by
  obtain ⟨K,hK,lower⟩ := optimal_query_scaling
  refine ⟨K,hK,?_⟩
  intro L eps t hL he hsmall a hcorrect
  have h := lower L eps hL he hsmall (densityReduction t a) (euler_implies_density t L eps a hcorrect)
  simpa only [densityReduction,Recovery.QueryTree.queries_map] using h
end Optimality

-- This file is assembled after Optimality.lean. Costs use a unit-cost RAM:
-- scalar cast/add/divide, oracle query, array write, loop test/increment each
-- cost one. Real constants are literals; arrays have constant-time indexing.
-- Ceiling and index arithmetic are also unit-cost scalar instructions.
-- These are abstract operation counts, not floating-point or elapsed time.
noncomputable section
namespace Work
open Recovery Grid Optimality

structure Metered (A : Type) where
  value : A
  work : ℕ

def literal (r : ℝ) : Metered ℝ := ⟨r,0⟩
def cast (i : ℕ) : Metered ℝ := ⟨i,1⟩
def add (a b : Metered ℝ) : Metered ℝ := ⟨a.value+b.value,a.work+b.work+1⟩
def divide (a b : Metered ℝ) : Metered ℝ := ⟨a.value/b.value,a.work+b.work+1⟩
def coordinate (n i : ℕ) : Metered ℝ := divide (add (cast i) (literal (1/2))) (literal n)
def centerProgram (n : ℕ) (i : Grid.Cell n) : Metered Grid.Space :=
  ⟨fun d => (coordinate n (i d)).value,
    (coordinate n (i 0)).work+(coordinate n (i 1)).work+(coordinate n (i 2)).work⟩
def sampleProgram (f : Recovery.Space → ℝ) (n : ℕ) (i : Grid.Cell n) : Metered ℝ :=
  let c := centerProgram n i
  ⟨f c.value,c.work+1+1⟩ -- one oracle query and one destination-array write

theorem center_program_correct (n : ℕ) (i : Grid.Cell n) :
    (centerProgram n i).value = Grid.center n i := rfl

theorem sample_program_correct (f : Recovery.Space → ℝ) (n : ℕ) (i : Grid.Cell n) :
    (sampleProgram f n i).value = f (Grid.center n i) ∧ (sampleProgram f n i).work = 11 := by
  exact ⟨rfl,rfl⟩

-- RAM arrays are represented semantically as finite functions; update writes
-- one cell. This does not assert a cost bound for persistent function closures.
def fill (f : Recovery.Space → ℝ) (n : ℕ) (cells : List (Grid.Cell n)) : Metered (Grid.Cell n → ℝ) :=
  match cells with
  | [] => ⟨fun _ => 0,2⟩ -- loop initialization and final condition test
  | i::rest =>
    let head := sampleProgram f n i
    let tail := fill f n rest
    ⟨Function.update tail.value i head.value,head.work+tail.work+2⟩

-- Every iteration adds its body, increment and condition test.
def loopWork (n body : ℕ) : ℕ :=
  match n with
  | 0 => 2
  | k+1 => loopWork k body+body+2

theorem loop_work (n body : ℕ) : loopWork n body = 2+n*(body+2) := by
  induction n with
  | zero => simp [loopWork]
  | succ n ih => simp [loopWork,ih]; ring

theorem fill_work (f : Recovery.Space → ℝ) (n : ℕ) (cells : List (Grid.Cell n)) :
    (fill f n cells).work = loopWork cells.length 11 := by
  induction cells with
  | nil => rfl
  | cons i rest ih =>
    simp [fill,sampleProgram,centerProgram,coordinate,divide,add,cast,literal,ih,loop_work]
    omega

theorem fill_values (f : Recovery.Space → ℝ) (n : ℕ) (cells : List (Grid.Cell n)) :
    ∀ i ∈ cells, (fill f n cells).value i = f (Grid.center n i) := by
  induction cells with
  | nil => simp
  | cons j rest ih =>
    intro i hi
    by_cases hij : i=j
    · subst i
      simp only [fill,Function.update_self]
      exact (sample_program_correct f n j).1
    · simp only [fill,Function.update_of_ne hij]
      exact ih i (by simpa [hij] using hi)

-- First enumerate the triples in three nested counted loops, writing three
-- index words per cell. Then fill the density array. This intentionally simple
-- implementation pays for all enumeration and storage rather than assuming
-- grid construction is free. The final three words retain n, T, and the table.
def enumerationWork (n : ℕ) : ℕ := loopWork n (loopWork n (loopWork n 3))
def solverProgram (f : Recovery.Space → ℝ) (n : ℕ) : Metered (Grid.Cell n → ℝ) :=
  let table := fill f n (Grid.cells n)
  ⟨table.value,enumerationWork n+n^3+1+table.work+3⟩

theorem solver_program_values (f : Recovery.Space → ℝ) (n : ℕ) :
    (solverProgram f n).value = Optimality.samples f n := by
  funext i
  exact fill_values f n (Grid.cells n) i (Grid.mem_cells n i)

theorem solver_program_matches_query_algorithm (f : Recovery.Space → ℝ) (n : ℕ) :
    (solverProgram f n).value = (Optimality.samplingAlgorithm n).run f := by
  rw [solver_program_values,Optimality.sampling_values]

theorem solver_work_exact (f : Recovery.Space → ℝ) (n : ℕ) :
    (solverProgram f n).work = 19*n^3+4*n^2+4*n+8 := by
  simp [solverProgram,enumerationWork,fill_work,loop_work,Grid.cells_length]
  ring

theorem solver_work_linear (f : Recovery.Space → ℝ) (n : ℕ) (hn : 0 < n) :
    (solverProgram f n).work ≤ 35*n^3 := by
  rw [solver_work_exact]
  have hn1 : 1 ≤ n := hn
  have hn2 : n ≤ n^2 := by nlinarith
  have hn3 : n^2 ≤ n^3 := by nlinarith
  nlinarith

-- Three scalar operations and one ceiling choose n from L and epsilon.
def toleranceProgram (f : Recovery.Space → ℝ) (L eps : ℝ) : Metered (Grid.Cell (Optimality.resolution L eps) → ℝ) :=
  let p := solverProgram f (Optimality.resolution L eps)
  ⟨p.value,4+p.work⟩

theorem tolerance_work_linear (f : Recovery.Space → ℝ) (L eps : ℝ)
    (hL : 0 < L) (he : 0 < eps) :
    (toleranceProgram f L eps).work ≤ 39*(Optimality.resolution L eps)^3 := by
  have h := solver_work_linear f _ (Optimality.resolution_positive L eps hL he)
  have hn := Optimality.resolution_positive L eps hL he
  have hp : 1 ≤ (Optimality.resolution L eps)^3 := one_le_pow₀ hn
  dsimp [toleranceProgram]
  omega

-- A query is a unit-cost instruction. Any additional scalar/memory work is
-- nonnegative. This lower bound therefore covers all such charged algorithms.
def chargedWork {O : Type} (a : Recovery.QueryTree O) (f : Recovery.Space → ℝ) (additional : ℕ) : ℕ :=
  (a.queries f).length+additional

theorem total_work_upper (f : Recovery.Space → ℝ) (L eps : ℝ)
    (hL : 0 < L) (he : 0 < eps) (heL : eps ≤ L) :
    ((toleranceProgram f L eps).work:ℝ) ≤ 312*(L/eps)^3 := by
  have hwork := tolerance_work_linear f L eps hL he
  have hw : ((toleranceProgram f L eps).work:ℝ) ≤
      39*((Optimality.resolution L eps:ℝ)^3) := by exact_mod_cast hwork
  have hn := Optimality.resolution_work_upper L eps hL he heL
  calc
    _ ≤ 39*((Optimality.resolution L eps:ℝ)^3) := hw
    _ ≤ 39*(2*L/eps)^3 := mul_le_mul_of_nonneg_left hn (by norm_num)
    _ = 312*(L/eps)^3 := by ring

theorem total_work_lower : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps t : ℝ, 1 ≤ L → 0 < eps → eps ≤ 1/(4*K) →
    ∀ a : Recovery.QueryTree (Recovery.Space → ShearEuler.State), Optimality.AccurateEuler t L eps a →
    ∀ additional : ℕ,
      (L/(4*K*eps))^3 ≤ (chargedWork a (fun _ => 3/2) additional:ℝ) := by
  obtain ⟨K,hK,lower⟩ := Optimality.optimal_euler_query_scaling
  refine ⟨K,hK,?_⟩
  intro L eps t hL he hsmall a hcorrect additional
  apply (lower L eps t hL he hsmall a hcorrect).trans
  simp only [chargedWork,Nat.cast_add]
  exact le_add_of_nonneg_right (Nat.cast_nonneg _)
end Work

-- Assembled after the component proofs. This theorem ties the physical
-- solution, finite-query algorithm, uniform accuracy and work bounds together.
noncomputable section
namespace Certificate

theorem admissible_is_classical_euler (L : ℝ) (rho0 : Recovery.Space → ℝ)
    (hf : Recovery.Admissible L rho0) :
    ContDiff ℝ 1 (fun tx : ℝ × ShearEuler.Space => ShearEuler.solution rho0 tx.1 tx.2) ∧
    (∀ t x, deriv (fun s => ShearEuler.solution rho0 s x) t +
      deriv (fun s => ShearEuler.eulerFlux (ShearEuler.solution rho0 t (Function.update x 0 s)) 0) (x 0) +
      deriv (fun s => ShearEuler.eulerFlux (ShearEuler.solution rho0 t (Function.update x 1 s)) 1) (x 1) +
      deriv (fun s => ShearEuler.eulerFlux (ShearEuler.solution rho0 t (Function.update x 2 s)) 2) (x 2) = 0) ∧
    (∀ x, ShearEuler.solution rho0 0 x = ShearEuler.conserved (rho0 x) ![x 1,x 2,1]) ∧
    (∀ t x, deriv (fun s => ShearEuler.flow s x) t = ShearEuler.velocity t (ShearEuler.flow t x)) := by
  refine ⟨ShearEuler.solution_is_C1 rho0 hf.1,?_,ShearEuler.initial_state rho0,ShearEuler.boundary_moves_with_fluid⟩
  intro t x
  apply ShearEuler.physical_euler_equations
  · exact hf.1.differentiable (by norm_num) _
  · intro a
    have h := (hf.2.1 a).1
    linarith

theorem family_nonempty (L : ℝ) (hL : 0 ≤ L) : Recovery.Admissible L (fun _ => 3/2) := by
  refine ⟨contDiff_const,?_,?_⟩
  · intro x
    norm_num
  · intro x y
    simp only [sub_self,abs_zero]
    exact mul_nonneg hL (norm_nonneg _)

-- Minimax-order optimality, with one fixed positive lower-bound constant.
-- Both upper and lower orders are (L/epsilon)^3. No best-constant claim.
theorem certified_work_optimality : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps t : ℝ, ∀ hL : 1 ≤ L, ∀ he : 0 < eps, eps ≤ 1/(4*K) →
    let n := Optimality.resolution L eps
    let hn := Optimality.resolution_positive L eps (lt_of_lt_of_le (by norm_num) hL) he
    Optimality.AccurateEuler t L eps (Optimality.eulerAlgorithm n hn t) ∧
    (∀ f : Recovery.Space → ℝ,
      (Work.toleranceProgram f L eps).value = (Optimality.samplingAlgorithm n).run f ∧
      ((Work.toleranceProgram f L eps).work:ℝ) ≤ 312*(L/eps)^3 ∧
      ((Optimality.eulerAlgorithm n hn t).queries f).length = n^3) ∧
    (∀ competitor : Recovery.QueryTree (Recovery.Space → ShearEuler.State),
      Optimality.AccurateEuler t L eps competitor → ∀ additional : ℕ,
      (L/(4*K*eps))^3 ≤ (Work.chargedWork competitor (fun _ => 3/2) additional:ℝ)) := by
  obtain ⟨K,hK,lower⟩ := Work.total_work_lower
  refine ⟨K,hK,?_⟩
  intro L eps t hL he hsmall
  have hLp : 0 < L := by linarith
  have hKp : 0 < K := by linarith
  have heL : eps ≤ L := by
    have hh := (le_div_iff₀ (by positivity : 0 < 4*K)).mp hsmall
    nlinarith
  refine ⟨Optimality.euler_algorithm_accurate L eps t hLp he,?_,?_⟩
  · intro f
    exact ⟨Work.solver_program_matches_query_algorithm f _,Work.total_work_upper f L eps hLp he heL,
      Optimality.euler_algorithm_queries _ _ t f⟩
  · intro competitor hcorrect additional
    exact lower L eps t hL he hsmall competitor hcorrect additional
end Certificate

-- A general deterministic adaptive oracle machine. Unbounded internal state
-- and infinite paths are allowed; only valid inputs must terminate.
noncomputable section
namespace Machines
open Recovery Grid Optimality

inductive Action (S O : Type) where
  | done : O → Action S O
  | ask : Recovery.Space → (ℝ → S) → Action S O

structure Machine (S O : Type) where
  step : S → Action S O

inductive Executes {S O : Type} (m : Machine S O) (f : Recovery.Space → ℝ) : S → List Recovery.Space → O → Prop where
  | done {s o} : m.step s = .done o → Executes m f s [] o
  | ask {s q next qs o} : m.step s = .ask q next →
      Executes m f (next (f q)) qs o → Executes m f s (q::qs) o

theorem same_answers {S O : Type} (m : Machine S O) (f g : Recovery.Space → ℝ)
    {s : S} {qs : List Recovery.Space} {o : O} (h : Executes m f s qs o)
    (same : ∀ q ∈ qs, g q=f q) : Executes m g s qs o := by
  induction h with
  | done h => exact Executes.done h
  | @ask s q next qs o h tail ih =>
    apply Executes.ask h
    have hq := same q (by simp)
    rw [hq]
    apply ih
    intro x hx
    exact same x (by simp [hx])

def Correct {S : Type} (m : Machine S (Recovery.Space → ShearEuler.State)) (s : S)
    (t L eps : ℝ) : Prop :=
  (∀ f, Recovery.Admissible L f → ∃ qs o, Executes m f s qs o) ∧
  (∀ f, Recovery.Admissible L f → ∀ qs o, Executes m f s qs o → ∀ x, Recovery.InCube x →
    ‖o (ShearEuler.flow t x)-ShearEuler.solution f t (ShearEuler.flow t x)‖ ≤ eps)

def ofTree {O : Type} : Machine (Recovery.QueryTree O) O where
  step a := match a with
    | .done o => .done o
    | .ask q next => .ask q next

theorem tree_executes {O : Type} (a : Recovery.QueryTree O) (f : Recovery.Space → ℝ) :
    Executes ofTree f a (a.queries f) (a.run f) := by
  induction a with
  | done o => exact Executes.done rfl
  | ask q next ih => exact Executes.ask rfl (ih (f q))

theorem tree_execution_output {O : Type} (a : Recovery.QueryTree O) (f : Recovery.Space → ℝ)
    (qs : List Recovery.Space) (o : O) (h : Executes ofTree f a qs o) : o = a.run f := by
  induction h with
  | @done s o hs =>
    cases s with
    | done value => simpa [ofTree,QueryTree.run,Action.done.injEq] using hs.symm
    | ask q next => simp [ofTree] at hs
  | @ask s q next qs o hs ht ih =>
    cases s with
    | done value => simp [ofTree] at hs
    | ask p follow =>
      have hh : p=q ∧ follow=next := by simpa [ofTree,Action.ask.injEq] using hs
      rcases hh with ⟨rfl,rfl⟩
      exact ih

theorem tree_correct (a : Recovery.QueryTree (Recovery.Space → ShearEuler.State)) (t L eps : ℝ)
    (h : Optimality.AccurateEuler t L eps a) : Correct ofTree a t L eps := by
  constructor
  · intro f hf
    exact ⟨a.queries f,a.run f,tree_executes a f⟩
  · intro f hf qs o he x hx
    rw [tree_execution_output a f qs o he]
    exact h f hf x hx

theorem density_component_error (f : Recovery.Space → ℝ) (o : Recovery.Space → ShearEuler.State)
    (t eps : ℝ) (x : Recovery.Space)
    (h : ‖o (ShearEuler.flow t x)-ShearEuler.solution f t (ShearEuler.flow t x)‖ ≤ eps) :
    |o (ShearEuler.flow t x) 0-f x| ≤ eps := by
  have hc := (norm_le_pi_norm (o (ShearEuler.flow t x)-ShearEuler.solution f t (ShearEuler.flow t x)) 0).trans h
  simpa [ShearEuler.solution,ShearEuler.conserved,ShearEuler.density,ShearEuler.inverse_flow,Real.norm_eq_abs] using hc

theorem machine_query_lower {S : Type} (m : Machine S (Recovery.Space → ShearEuler.State)) (s : S)
    (t L eps K : ℝ) (b : Recovery.Space → ℝ)
    (hb : ContDiff ℝ 1 b) (hbounds : ∀ x, 0 ≤ b x ∧ b x ≤ 1) (h0 : b 0 = 1)
    (hz : ∀ x, 1/2 ≤ ‖x‖ → b x = 0) (hlip : ∀ x y, |b x-b y| ≤ K*‖x-y‖)
    (heps : 0 < eps) (hepsmax : eps ≤ 1/4) (n : ℕ) (hn : 0 < n)
    (hbudget : 2*eps*K*(n:ℝ) ≤ L) (correct : Correct m s t L eps)
    (qs : List Recovery.Space) (o : Recovery.Space → ShearEuler.State)
    (run : Executes m (fun _ => 3/2) s qs o) : n^3 ≤ qs.length := by
  by_contra small
  obtain ⟨i,hi⟩ := Optimality.exists_unqueried_cell b hz n hn qs (by omega)
  let fplus := Recovery.perturb b (2*eps) n (Grid.center n i)
  let fminus := Recovery.perturb b (-2*eps) n (Grid.center n i)
  have hplus : Recovery.Admissible L fplus := by
    apply Recovery.perturb_admissible b K L (2*eps) n (Grid.center n i) hb hbounds hlip
    · positivity
    · rw [abs_of_pos (by positivity)]
      linarith
    · simpa [abs_of_pos (by positivity : 0 < 2*eps)] using hbudget
  have hminus : Recovery.Admissible L fminus := by
    apply Recovery.perturb_admissible b K L (-2*eps) n (Grid.center n i) hb hbounds hlip
    · positivity
    · rw [abs_of_neg (by linarith)]
      linarith
    · rw [abs_of_neg (by linarith)]
      convert hbudget using 1; ring
  have ep : Executes m fplus s qs o := by
    apply same_answers m (fun _ => 3/2) fplus run
    intro q hq
    simp [fplus,Recovery.perturb,hi q hq]
  have em : Executes m fminus s qs o := by
    apply same_answers m (fun _ => 3/2) fminus run
    intro q hq
    simp [fminus,Recovery.perturb,hi q hq]
  have hp := density_component_error fplus o t eps _
    (correct.2 fplus hplus qs o ep _ (Grid.center_in_cube n hn i))
  have hm := density_component_error fminus o t eps _
    (correct.2 fminus hminus qs o em _ (Grid.center_in_cube n hn i))
  simp [fplus,fminus,Recovery.perturb,h0] at hp hm
  have hp' := abs_le.mp hp
  have hm' := abs_le.mp hm
  linarith

theorem general_machine_work_lower : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps t : ℝ, 1 ≤ L → 0 < eps → eps ≤ 1/(4*K) →
    ∀ (S : Type) (m : Machine S (Recovery.Space → ShearEuler.State)) (s : S), Correct m s t L eps →
    ∀ qs o, Executes m (fun _ => 3/2) s qs o → ∀ additional : ℕ,
      (L/(4*K*eps))^3 ≤ ((qs.length+additional):ℝ) := by
  obtain ⟨b,K,hK,hb,hbounds,h0,hz,hlip⟩ := Recovery.exists_base_bump
  refine ⟨K,hK,?_⟩
  intro L eps t hL he hsmall S m s hcorrect qs o hrun additional
  have hKp : 0 < K := by linarith
  have hprod : 4*K*eps ≤ 1 := by
    have hh := (le_div_iff₀ (by positivity : 0 < 4*K)).mp hsmall
    nlinarith
  have hem : eps ≤ 1/4 := by nlinarith
  let x : ℝ := L/(2*K*eps)
  have hx2 : 2 ≤ x := by
    apply (le_div_iff₀ (by positivity : 0 < 2*K*eps)).mpr
    nlinarith
  let n := ⌊x⌋₊
  have hn : 0 < n := by
    have hh : 1 ≤ n := (Nat.one_le_floor_iff x).mpr (by linarith)
    omega
  have hfloor : (n:ℝ) ≤ x := Nat.floor_le (by linarith)
  have hfloor2 : x < (n:ℝ)+1 := Nat.lt_floor_add_one x
  have hnlarge : L/(4*K*eps) ≤ (n:ℝ) := by
    have heq : L/(4*K*eps) = x/2 := by dsimp [x]; ring
    rw [heq]
    linarith
  have hbudget : 2*eps*K*(n:ℝ) ≤ L := by
    have hh := (le_div_iff₀ (by positivity : 0 < 2*K*eps)).mp hfloor
    nlinarith
  have hqueries := machine_query_lower m s t L eps K b hb hbounds h0 hz hlip he hem n hn hbudget hcorrect qs o hrun
  have hqueriesR : (n:ℝ)^3 ≤ (qs.length:ℝ) := by exact_mod_cast hqueries
  calc
    _ ≤ (n:ℝ)^3 := pow_le_pow_left₀ (by positivity) hnlarge 3
    _ ≤ (qs.length:ℝ) := hqueriesR
    _ ≤ ((qs.length+additional):ℝ) := by exact_mod_cast Nat.le_add_right qs.length additional

theorem certified_general_optimality : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps t : ℝ, ∀ hL : 1 ≤ L, ∀ he : 0 < eps, eps ≤ 1/(4*K) →
    let n := Optimality.resolution L eps
    let hn := Optimality.resolution_positive L eps (lt_of_lt_of_le (by norm_num) hL) he
    Correct ofTree (Optimality.eulerAlgorithm n hn t) t L eps ∧
    (∀ f : Recovery.Space → ℝ, ((Work.toleranceProgram f L eps).work:ℝ) ≤ 312*(L/eps)^3) ∧
    (∀ (S : Type) (m : Machine S (Recovery.Space → ShearEuler.State)) (s : S), Correct m s t L eps →
      ∃ qs o, Executes m (fun _ => 3/2) s qs o ∧
        ∀ additional : ℕ, (L/(4*K*eps))^3 ≤ ((qs.length+additional):ℝ)) := by
  obtain ⟨K,hK,lower⟩ := general_machine_work_lower
  refine ⟨K,hK,?_⟩
  intro L eps t hL he hsmall
  have hLp : 0 < L := by linarith
  have hKp : 0 < K := by linarith
  have heL : eps ≤ L := by
    have hh := (le_div_iff₀ (by positivity : 0 < 4*K)).mp hsmall
    nlinarith
  refine ⟨tree_correct _ t L eps (Optimality.euler_algorithm_accurate L eps t hLp he),?_,?_⟩
  · intro f
    exact Work.total_work_upper f L eps hLp he heL
  · intro S m s hcorrect
    obtain ⟨qs,o,hrun⟩ := hcorrect.1 (fun _ => 3/2) (Certificate.family_nonempty L hLp.le)
    exact ⟨qs,o,hrun,fun additional => lower L eps t hL he hsmall S m s hcorrect qs o hrun additional⟩
end Machines
