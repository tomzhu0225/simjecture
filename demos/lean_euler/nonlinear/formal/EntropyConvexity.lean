import Mathlib.Analysis.Convex.Deriv
import Mathlib.Analysis.Convex.Jensen

-- Assemble after Entropy.lean. Convexity is derived from actual directional
-- derivatives of the conserved-variable entropy, not assumed as a solver property.
noncomputable section
namespace EulerEntropyConvexity
open EulerEntropy
open scoped BigOperators

def stateDomain : Set State := {u | EulerAdmissible.Admissible u}

theorem domain_convex : Convex ℝ stateDomain := by
  intro x hx y hy a b ha hb hab
  have ha1 : a ≤ 1 := by linarith
  have h := EulerAdmissible.convex_admissible x y hx hy a ha ha1
  have hbeq : 1-a=b := by linarith
  simpa only [hbeq] using h

def segment (x y : State) (t : ℝ) : State := x+t • (y-x)

theorem segment_mix (x y : State) (t : ℝ) : segment x y t = (1-t) • x+t • y := by
  funext i
  simp only [segment,Pi.add_apply,Pi.smul_apply,Pi.sub_apply,smul_eq_mul]
  ring

theorem segment_admissible (x y : State) (hx : x ∈ stateDomain) (hy : y ∈ stateDomain)
    (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : EulerAdmissible.Admissible (segment x y t) := by
  rw [segment_mix]
  exact domain_convex hx hy (sub_nonneg.mpr ht.2) ht.1 (by ring)

theorem segment_derivative (x y : State) (t : ℝ) : HasDerivAt (segment x y) (y-x) t := by
  have hh := (hasDerivAt_const t x).add ((hasDerivAt_id t).smul_const (y-x))
  simpa only [zero_add,one_smul] using hh

theorem entropy_convex_on_segment (x y : State) (hx : x ∈ stateDomain) (hy : y ∈ stateDomain) :
    ConvexOn ℝ (Set.Icc (0 : ℝ) 1) (fun t => entropy (segment x y t)) := by
  let df := fun t => dot (gradient (segment x y t)) (y-x)
  let ddf := fun t => hessianForm (toPrimitive (segment x y t)) (primitiveD (segment x y t) (y-x))
  have hder (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :
      HasDerivAt (fun s => entropy (segment x y s)) (df t) t := by
    obtain ⟨hr,hp⟩ := segment_admissible x y hx hy t ht
    exact entropy_derivative (segment_derivative x y t) (ne_of_gt hr) (ne_of_gt hp)
  have hder2 (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt df (ddf t) t := by
    obtain ⟨hr,hp⟩ := segment_admissible x y hx hy t ht
    exact entropy_second_directional (segment_derivative x y t) hr hp
  apply convexOn_of_hasDerivWithinAt2_nonneg (convex_Icc (0 : ℝ) 1)
    (fun t ht => (hder t ht).continuousAt.continuousWithinAt)
    (fun t ht => (hder t (interior_subset ht)).hasDerivWithinAt)
    (fun t ht => (hder2 t (interior_subset ht)).hasDerivWithinAt)
  intro t ht
  obtain ⟨hr,hp⟩ := segment_admissible x y hx hy t (interior_subset ht)
  exact hessian_nonnegative _ _ (by dsimp [toPrimitive]; positivity) hp

theorem entropy_convex : ConvexOn ℝ stateDomain entropy := by
  refine ⟨domain_convex,?_⟩
  intro x hx y hy a b ha hb hab
  have hc := entropy_convex_on_segment x y hx hy
  have hi0 : (0 : ℝ) ∈ Set.Icc (0 : ℝ) 1 := by norm_num
  have hi1 : (1 : ℝ) ∈ Set.Icc (0 : ℝ) 1 := by norm_num
  have hm := hc.2 hi0 hi1 ha hb hab
  have h0 : segment x y 0=x := by simp [segment]
  have h1 : segment x y 1=y := by simp [segment]
  have he : segment x y (a • (0 : ℝ)+b • (1 : ℝ)) = a • x+b • y := by
    rw [segment_mix]
    have hb1 : 1-b=a := by linarith
    simp only [smul_eq_mul,mul_zero,mul_one,zero_add,hb1]
  simpa only [he,h0,h1] using hm

theorem entropy_convex_mixture {I : Type*} [Fintype I] (a : I → ℝ) (u : I → State)
    (ha : ∀ i, 0 ≤ a i) (hs : ∑ i, a i=1) (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    entropy (∑ i, a i • u i) ≤ ∑ i, a i*entropy (u i) := by
  simpa only [smul_eq_mul] using entropy_convex.map_sum_le (fun i _ => ha i) hs (fun i _ => hu i)

-- A finite averaging map with unit row and column sums cannot restore convex
-- entropy lost by evolution. Continuous output integration is a separate bridge.
theorem averaging_entropy_bound {I : Type*} [Fintype I] (weights : I → I → ℝ) (u : I → State)
    (hw : ∀ i j, 0 ≤ weights i j) (hrow : ∀ i, ∑ j, weights i j=1)
    (hcol : ∀ j, ∑ i, weights i j=1) (hu : ∀ i, EulerAdmissible.Admissible (u i)) :
    (∑ i, entropy (∑ j, weights i j • u j)) ≤ ∑ i, entropy (u i) := by
  calc
    _ ≤ ∑ i, ∑ j, weights i j*entropy (u j) :=
      Finset.sum_le_sum (fun i _ => entropy_convex_mixture (weights i) u (hw i) (hrow i) hu)
    _ = _ := by
      rw [Finset.sum_comm]
      simp only [← Finset.sum_mul,hcol,one_mul]

end EulerEntropyConvexity
