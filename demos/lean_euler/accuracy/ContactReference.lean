import Mathlib.Data.Real.Basic
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Ring

noncomputable section
namespace ContactReference

structure State where
  rho : ℝ
  mx : ℝ
  my : ℝ
  mz : ℝ
  energy : ℝ

def kineticFactor (vx vy vz : ℝ) : ℝ := (vx^2+vy^2+vz^2)/2

def contact (rho p vx vy vz : ℝ) : State :=
  ⟨rho,rho*vx,rho*vy,rho*vz,p+rho*kineticFactor vx vy vz⟩

def pressure (u : State) : ℝ := u.energy-(u.mx^2+u.my^2+u.mz^2)/(2*u.rho)

theorem contact_pressure (rho p vx vy vz : ℝ) :
    pressure (contact rho p vx vy vz) = p := by
  simp only [pressure, contact, kineticFactor]
  field_simp; ring

theorem contact_velocity (rho p vx vy vz : ℝ) (nonzero : rho ≠ 0) :
    (contact rho p vx vy vz).mx/rho = vx ∧
    (contact rho p vx vy vz).my/rho = vy ∧
    (contact rho p vx vy vz).mz/rho = vz := by
  simp [contact, nonzero]

-- For constant p and v, every conservation-law residual is a fixed multiple
-- of the scalar transport residual. The arguments are the density derivatives;
-- identifying them with derivatives of a particular profile is a separate step.
def residual (rt rx ry rz p vx vy vz : ℝ) : State :=
  ⟨rt+vx*rx+vy*ry+vz*rz,
   vx*rt+vx^2*rx+vx*vy*ry+vx*vz*rz,
   vy*rt+vy*vx*rx+vy^2*ry+vy*vz*rz,
   vz*rt+vz*vx*rx+vz*vy*ry+vz^2*rz,
   kineticFactor vx vy vz*rt+
     kineticFactor vx vy vz*vx*rx+kineticFactor vx vy vz*vy*ry+
     kineticFactor vx vy vz*vz*rz+0*p⟩

theorem transported_contact_residual (rt rx ry rz p vx vy vz : ℝ)
    (transport : rt+vx*rx+vy*ry+vz*rz = 0) :
    residual rt rx ry rz p vx vy vz = ⟨0,0,0,0,0⟩ := by
  have hx := congrArg (fun z => vx*z) transport
  have hy := congrArg (fun z => vy*z) transport
  have hz := congrArg (fun z => vz*z) transport
  have he := congrArg (fun z => kineticFactor vx vy vz*z) transport
  dsimp at hx hy hz he
  simp only [residual, State.mk.injEq]
  refine ⟨transport, ?_, ?_, ?_, ?_⟩
  · simpa only [mul_add, mul_zero, pow_two, mul_assoc] using hx
  · simpa only [mul_add, mul_zero, pow_two, mul_assoc] using hy
  · simpa only [mul_add, mul_zero, pow_two, mul_assoc] using hz
  · simpa only [mul_add, mul_zero, zero_mul, add_zero, mul_assoc] using he

-- The parameters used by the experiment give a transparent exact derivative jet.
theorem sinusoidal_transport_jet (d : ℝ) :
    -(3/5:ℝ)*d + (1/2:ℝ)*d + (1/5:ℝ)*d + (-1/10:ℝ)*d = 0 := by ring

theorem density_controls_components (r s p vx vy vz : ℝ) :
    (contact r p vx vy vz).mx-(contact s p vx vy vz).mx = vx*(r-s) ∧
    (contact r p vx vy vz).my-(contact s p vx vy vz).my = vy*(r-s) ∧
    (contact r p vx vy vz).mz-(contact s p vx vy vz).mz = vz*(r-s) ∧
    (contact r p vx vy vz).energy-(contact s p vx vy vz).energy =
      kineticFactor vx vy vz*(r-s) := by
  simp only [contact]
  constructor
  · ring
  constructor
  · ring
  constructor <;> ring
end ContactReference
