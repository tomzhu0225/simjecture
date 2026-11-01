import Mathlib.Data.Real.Sqrt
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Tactic.Ring

noncomputable section
namespace EulerCache
open scoped BigOperators
abbrev State := Fin 5 → ℝ
abbrev Axis := Fin 3

def momentumIndex (a : Axis) : Fin 5 := ⟨a.val+1, by omega⟩
def pressure (u : State) : ℝ :=
  u 4 - ((u 1)^2 + (u 2)^2 + (u 3)^2) / (2*u 0)
def sound (u : State) : ℝ := Real.sqrt (2*pressure u/u 0)
def admissible (u : State) : Prop := 0 < u 0 ∧ 0 < pressure u

structure Thermo where
  p : ℝ
  c : ℝ

def thermal (u : State) : Thermo := ⟨pressure u, sound u⟩
def velocity (u : State) (a : Axis) : ℝ := u (momentumIndex a) / u 0

-- Independent expression for the five physical flux components, gamma = 2.
def physical (u : State) (a : Axis) (k : Fin 5) : ℝ :=
  u k * velocity u a +
    (if k = momentumIndex a then pressure u else 0) +
    (if k = 4 then pressure u * velocity u a else 0)
def spectral (u : State) (a : Axis) : ℝ := |velocity u a| + sound u

-- Candidate receives a previously computed thermodynamic record.
def cachedPhysical (u : State) (t : Thermo) (a : Axis) (k : Fin 5) : ℝ :=
  (u k * velocity u a + (if k = momentumIndex a then t.p else 0)) +
    (if k = 4 then t.p * velocity u a else 0)
def cachedSpectral (u : State) (t : Thermo) (a : Axis) : ℝ :=
  |velocity u a| + t.c

def face (l r : State) (a : Axis) (k : Fin 5) : ℝ :=
  (physical l a k + physical r a k -
    max (spectral l a) (spectral r a) * (r k-l k)) / 2
def cachedFace (l r : State) (tl tr : Thermo) (a : Axis) (k : Fin 5) : ℝ :=
  (cachedPhysical l tl a k + cachedPhysical r tr a k -
    max (cachedSpectral l tl a) (cachedSpectral r tr a) * (r k-l k)) / 2

theorem physical_equivalence (u : State) (a : Axis) :
    cachedPhysical u (thermal u) a = physical u a := by
  rfl

theorem face_equivalence (l r : State) (a : Axis) :
    cachedFace l r (thermal l) (thermal r) a = face l r a := by
  rfl

-- next[a] is the periodic successor in direction a; next[a].symm is
-- the predecessor. All directional face fluxes use the same old state.
def referenceStep {ι : Type} (U : ι → State) (next : Axis → Equiv.Perm ι)
    (ratio : Axis → ℝ) (i : ι) (k : Fin 5) : ℝ :=
  ((U i k - ratio 0 * (face (U i) (U (next 0 i)) 0 k -
      face (U ((next 0).symm i)) (U i) 0 k)) -
    ratio 1 * (face (U i) (U (next 1 i)) 1 k -
      face (U ((next 1).symm i)) (U i) 1 k)) -
    ratio 2 * (face (U i) (U (next 2 i)) 2 k -
      face (U ((next 2).symm i)) (U i) 2 k)

def cachedStep {ι : Type} (U : ι → State) (cache : ι → Thermo)
    (next : Axis → Equiv.Perm ι) (ratio : Axis → ℝ) (i : ι) (k : Fin 5) : ℝ :=
  ((U i k - ratio 0 * (cachedFace (U i) (U (next 0 i)) (cache i) (cache (next 0 i)) 0 k -
      cachedFace (U ((next 0).symm i)) (U i) (cache ((next 0).symm i)) (cache i) 0 k)) -
    ratio 1 * (cachedFace (U i) (U (next 1 i)) (cache i) (cache (next 1 i)) 1 k -
      cachedFace (U ((next 1).symm i)) (U i) (cache ((next 1).symm i)) (cache i) 1 k)) -
    ratio 2 * (cachedFace (U i) (U (next 2 i)) (cache i) (cache (next 2 i)) 2 k -
      cachedFace (U ((next 2).symm i)) (U i) (cache ((next 2).symm i)) (cache i) 2 k)

theorem step_equivalence {ι : Type} (U : ι → State) (cache : ι → Thermo)
    (next : Axis → Equiv.Perm ι) (ratio : Axis → ℝ)
    (fresh : ∀ i, cache i = thermal (U i)) :
    cachedStep U cache next ratio = referenceStep U next ratio := by
  funext i k
  simp only [cachedStep, referenceStep, fresh, face_equivalence]

-- On physical inputs, equivalence holds for all components and any step size.
-- This statement does not assert that either updated state stays admissible.
theorem admissible_step_equivalence {ι : Type} (U : ι → State)
    (next : Axis → Equiv.Perm ι) (ratio : Axis → ℝ) :
    (∀ i, admissible (U i)) →
    cachedStep U (fun i => thermal (U i)) next ratio = referenceStep U next ratio := by
  intro _
  exact step_equivalence U _ next ratio (fun _ => rfl)

-- A generic shared-face divergence form, independently summable.
def sharedStep {ι : Type} (U : ι → State) (F : Axis → ι → State)
    (next : Axis → Equiv.Perm ι) (ratio : Axis → ℝ) (i : ι) (k : Fin 5) : ℝ :=
  U i k - ∑ a : Axis, ratio a * (F a i k-F a ((next a).symm i) k)

theorem reference_is_shared {ι : Type} (U : ι → State)
    (next : Axis → Equiv.Perm ι) (ratio : Axis → ℝ) :
    referenceStep U next ratio =
      sharedStep U (fun a i => face (U i) (U (next a i)) a) next ratio := by
  funext i k
  simp [referenceStep, sharedStep, Fin.sum_univ_succ]
  ring

theorem shared_conservation {ι : Type} [Fintype ι] (U : ι → State)
    (F : Axis → ι → State) (next : Axis → Equiv.Perm ι) (ratio : Axis → ℝ)
    (k : Fin 5) : ∑ i, sharedStep U F next ratio i k = ∑ i, U i k := by
  simp only [sharedStep, Finset.sum_sub_distrib]
  rw [Finset.sum_comm]
  have h : ∀ a : Axis, ∑ i, ratio a * (F a i k-F a ((next a).symm i) k) = 0 := by
    intro a
    rw [← Finset.mul_sum, Finset.sum_sub_distrib]
    have reindex := Equiv.sum_comp (next a).symm (fun j => F a j k)
    rw [reindex]
    simp
  simp only [h, Finset.sum_const_zero, sub_zero]

theorem cached_conservation {ι : Type} [Fintype ι] (U : ι → State)
    (next : Axis → Equiv.Perm ι) (ratio : Axis → ℝ) (k : Fin 5) :
    ∑ i, cachedStep U (fun j => thermal (U j)) next ratio i k = ∑ i, U i k := by
  rw [step_equivalence U _ next ratio (fun _ => rfl), reference_is_shared]
  exact shared_conservation U _ next ratio k

theorem face_consistency (u : State) (a : Axis) : face u u a = physical u a := by
  funext k
  simp [face]

-- Applying the fresh cache construction at every step gives equal iterates.
theorem trajectory_equivalence {ι : Type} (next : Axis → Equiv.Perm ι)
    (ratio : Axis → ℝ) (U : ι → State) (steps : Nat) :
    (fun V => cachedStep V (fun i => thermal (V i)) next ratio)^[steps] U =
      (fun V => referenceStep V next ratio)^[steps] U := by
  have eq : (fun V => cachedStep V (fun i => thermal (V i)) next ratio) =
      (fun V => referenceStep V next ratio) := by
    funext V
    exact step_equivalence V _ next ratio (fun _ => rfl)
  rw [eq]
end EulerCache
