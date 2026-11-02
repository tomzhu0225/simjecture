-- Assemble after DiscreteEnergy.lean and EnergyBounds.lean. The first inequality
-- displays the exact coefficient-variation defect rather than hiding it in an
-- assumed stability constant. Uniform control of that defect is still needed.
noncomputable section
namespace EulerVariableEnergy
open EulerPrimitiveEnergy EulerDiscreteEnergy
open scoped BigOperators

def localContribution {I : Type*} (q p : I → ℝ) (ratio : ℝ)
    (v : I → Fin 3 → ℝ) (a : Fin 3 → ℝ) (i : I) (j : Fin 7) (x : State) : ℝ :=
  metric (q i) (p i) x (actions (q i) (p i) ratio (v i) a j x)

def variableUpdate {I : Type*} (q p : I → ℝ) (ratio : ℝ)
    (v : I → Fin 3 → ℝ) (a : Fin 3 → ℝ)
    (shift : Fin 7 → Equiv.Perm I) (u : I → State) (i : I) : State :=
  ∑ j, actions (q i) (p i) ratio (v i) a j (u (shift j i))

def variationDefect {I : Type*} [Fintype I] (q p : I → ℝ) (ratio : ℝ)
    (v : I → Fin 3 → ℝ) (a : Fin 3 → ℝ)
    (shift : Fin 7 → Equiv.Perm I) (u : I → State) : ℝ :=
  ∑ i, ∑ j, (localContribution q p ratio v a ((shift j).symm i) j (u i)-
    localContribution q p ratio v a i j (u i))

theorem variable_principal_energy_defect {I : Type*} [Fintype I]
    (q p : I → ℝ) (ratio : ℝ) (v : I → Fin 3 → ℝ) (a : Fin 3 → ℝ)
    (hq : ∀ i, 0 < q i) (hp : ∀ i, 0 < p i) (hr : 0 ≤ ratio)
    (ha : ∀ i d, |v i d|+Real.sqrt (2*p i*q i) ≤ a d)
    (hcf : ratio*(a 0+a 1+a 2) ≤ 1)
    (shift : Fin 7 → Equiv.Perm I) (u : I → State) :
    (∑ i, metric (q i) (p i) (variableUpdate q p ratio v a shift u i)
      (variableUpdate q p ratio v a shift u i)) ≤
      (∑ i, metric (q i) (p i) (u i) (u i))+variationDefect q p ratio v a shift u := by
  have hpoint (i : I) := energy_jensen (q i) (p i) (actions (q i) (p i) ratio (v i) a)
    (actions_sub (q i) (p i) ratio (v i) a)
    (actions_symmetric (q i) (p i) ratio (v i) a (hq i) (hp i))
    (actions_nonnegative (q i) (p i) ratio (v i) a (hq i) (hp i) hr (ha i) hcf)
    (actions_partition (q i) (p i) ratio (v i) a) (fun j => u (shift j i))
  have hs (j : Fin 7) :
      (∑ i, localContribution q p ratio v a i j (u (shift j i))) =
      ∑ i, localContribution q p ratio v a ((shift j).symm i) j (u i) := by
    have h := Equiv.sum_comp (shift j)
      (fun i => localContribution q p ratio v a ((shift j).symm i) j (u i))
    simpa only [Equiv.symm_apply_apply] using h
  have hpresent (i : I) : ∑ j, localContribution q p ratio v a i j (u i) =
      metric (q i) (p i) (u i) (u i) := by
    simp only [localContribution,← metric_sum_right,actions_partition]
  calc
    _ ≤ ∑ i, ∑ j, localContribution q p ratio v a i j (u (shift j i)) :=
      Finset.sum_le_sum (fun i _ => hpoint i)
    _ = (∑ i, metric (q i) (p i) (u i) (u i))+variationDefect q p ratio v a shift u := by
      rw [Finset.sum_comm]
      simp_rw [hs]
      rw [Finset.sum_comm]
      simp only [variationDefect,Finset.sum_sub_distrib,hpresent]
      ring

-- The acoustic pressure-velocity cross term is constant in the symmetrized
-- flux. Its spatial coefficient variation cancels exactly.
theorem principal_form_variation (q p q' p' v v' : ℝ)
    (hq : 0 < q) (hp : 0 < p) (hq' : 0 < q') (hp' : 0 < p')
    (d : Fin 3) (x y : State) :
    metric q' p' x (principal q' p' v' d y)-metric q p x (principal q p v d y) =
      v'*metric q' p' x y-v*metric q p x y := by
  rw [principal_metric_identity q' p' v' hq' hp' d x y,
    principal_metric_identity q p v hq hp d x y]
  ring
end EulerVariableEnergy
