import Mathlib.Tactic.NormNum

namespace EulerWitness
-- Conservative variables (rho, momentum, total energy), gamma = 2.
structure State where
  rho : ℚ
  mom : ℚ
  energy : ℚ

def pressure (u : State) : ℚ := u.energy - u.mom^2 / (2*u.rho)
def physical (u : State) : State :=
  ⟨u.mom, u.mom^2/u.rho + pressure u, (u.energy+pressure u)*u.mom/u.rho⟩

-- Rusanov a = 1: each initial state below has v = 0 and sound-speed squared = 1.
def face (l r : State) : State :=
  ⟨((physical l).rho + (physical r).rho - (r.rho-l.rho))/2,
   ((physical l).mom + (physical r).mom - (r.mom-l.mom))/2,
   ((physical l).energy + (physical r).energy - (r.energy-l.energy))/2⟩

def low : State := ⟨1, 0, 1/2⟩
def high : State := ⟨2, 0, 1⟩
def admissible (u : State) : Prop := 0 < u.rho ∧ 0 < pressure u

theorem initial_admissible :
    admissible low ∧ admissible high ∧
    2 * pressure low / low.rho = 1 ∧ 2 * pressure high / high.rho = 1 := by
  norm_num [admissible, low, high, pressure]

-- Cell 2 in the periodic list [low, low, high], dt/dx = 4.
def updatedDensity : ℚ := high.rho - 4*((face high low).rho-(face low high).rho)

theorem negative_density : updatedDensity = -2 ∧ updatedDensity < 0 := by
  norm_num [updatedDensity, high, low, face, physical]
end EulerWitness
