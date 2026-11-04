import Mathlib.Algebra.Group.Fin.Basic

-- Periodic-grid variance control for the dissipation-to-error argument.
-- This is a spatial identity/estimate, not a continuum existence theorem.
noncomputable section
namespace EulerGridPoincare
open scoped BigOperators
abbrev Cell (n : ℕ) := Fin n × (Fin n × Fin n)

def scalarMean {I : Type*} [Fintype I] (f : I → ℝ) : ℝ := (∑ i, f i)/(Fintype.card I : ℝ)
def scalarVariance {I : Type*} [Fintype I] (f : I → ℝ) : ℝ := ∑ i, (f i-scalarMean f)^2

theorem pair_variance_identity {I : Type*} [Fintype I] [Nonempty I] (f : I → ℝ) :
    (∑ i, ∑ j, (f i-f j)^2)=2*(Fintype.card I : ℝ)*scalarVariance f := by
  have hn : (Fintype.card I : ℝ) ≠ 0 := by exact_mod_cast Fintype.card_ne_zero
  simp only [sub_sq,Finset.sum_add_distrib,Finset.sum_sub_distrib,
    Finset.sum_const,Finset.card_univ,nsmul_eq_mul,← Finset.mul_sum,← Finset.sum_mul,
    scalarVariance,scalarMean]
  field_simp
  ring

open Fin.NatCast in
theorem line_oscillation (n : ℕ) [NeZero n] (f : Fin n → ℝ) (i j : Fin n) :
    (f i-f j)^2 ≤ (n : ℝ)*∑ k : Fin n, (f (k+1)-f k)^2 := by
  have hh := EulerGridSobolev.oscillation (fun k : ℕ => f (Fin.ofNat n k)) n i.val j.val i.isLt j.isLt
  have he : (∑ k ∈ Finset.range n, (f (Fin.ofNat n (k+1))-f (Fin.ofNat n k))^2)=
      ∑ k : Fin n, (f (k+1)-f k)^2 := by
    rw [← Fin.sum_univ_eq_sum_range]
    simp only [Fin.ofNat_eq_cast,Nat.cast_add,Nat.cast_one,Fin.cast_val_eq_self]
  rw [he] at hh
  simpa only [Fin.ofNat_eq_cast,Fin.cast_val_eq_self] using hh

def lineX {n : ℕ} [NeZero n] (f : Cell n → ℝ) (j k : Fin n) : ℝ :=
  ∑ i : Fin n, (f (i+1,(j,k))-f (i,(j,k)))^2
def lineY {n : ℕ} [NeZero n] (f : Cell n → ℝ) (i k : Fin n) : ℝ :=
  ∑ j : Fin n, (f (i,(j+1,k))-f (i,(j,k)))^2
def lineZ {n : ℕ} [NeZero n] (f : Cell n → ℝ) (i j : Fin n) : ℝ :=
  ∑ k : Fin n, (f (i,(j,k+1))-f (i,(j,k)))^2
def scalarEdges {n : ℕ} [NeZero n] (f : Cell n → ℝ) : ℝ :=
  (∑ j, ∑ k, lineX f j k)+(∑ i, ∑ k, lineY f i k)+(∑ i, ∑ j, lineZ f i j)

theorem grid_pair_bound (n : ℕ) [NeZero n] (f : Cell n → ℝ) (x y : Cell n) :
    (f x-f y)^2 ≤ 3*(n : ℝ)*(lineX f x.2.1 x.2.2+lineY f y.1 x.2.2+lineZ f y.1 y.2.1) := by
  rcases x with ⟨i,j,k⟩
  rcases y with ⟨a,b,c⟩
  have hx := line_oscillation n (fun z => f (z,(j,k))) i a
  have hy := line_oscillation n (fun z => f (a,(z,k))) j b
  have hz := line_oscillation n (fun z => f (a,(b,z))) k c
  have hs := EulerPhysicalRegion.three_sum_bound (f (i,(j,k))-f (a,(j,k)))
    (f (a,(j,k))-f (a,(b,k))) (f (a,(b,k))-f (a,(b,c)))
  change (f (i,(j,k))-f (a,(j,k)))^2 ≤ (n : ℝ)*lineX f j k at hx
  change (f (a,(j,k))-f (a,(b,k)))^2 ≤ (n : ℝ)*lineY f a k at hy
  change (f (a,(b,k))-f (a,(b,c)))^2 ≤ (n : ℝ)*lineZ f a b at hz
  dsimp only
  nlinarith

theorem coordinate_pair_sum (n : ℕ) (X Y Z : Fin n → Fin n → ℝ) :
    (∑ x : Cell n, ∑ y : Cell n, (X x.2.1 x.2.2+Y y.1 x.2.2+Z y.1 y.2.1)) =
      (n : ℝ)^4*((∑ i, ∑ j, X i j)+(∑ i, ∑ j, Y i j)+(∑ i, ∑ j, Z i j)) := by
  have hy : (∑ k, ∑ a, Y a k)=∑ a, ∑ k, Y a k := Finset.sum_comm
  simp only [Fintype.sum_prod_type,Finset.sum_add_distrib,Finset.sum_const,
    Finset.card_univ,Fintype.card_prod,Fintype.card_fin,nsmul_eq_mul,← Finset.mul_sum,Cell,Nat.cast_mul]
  rw [hy]
  ring

theorem scalar_poincare (n : ℕ) [NeZero n] (f : Cell n → ℝ) :
    scalarVariance f ≤ (3/2 : ℝ)*(n : ℝ)^2*scalarEdges f := by
  have hh := Finset.sum_le_sum (fun x (_ : x ∈ Finset.univ) =>
    Finset.sum_le_sum (fun y (_ : y ∈ Finset.univ) => grid_pair_bound n f x y))
  simp only [← Finset.mul_sum,coordinate_pair_sum] at hh
  rw [pair_variance_identity f] at hh
  have hcard : (Fintype.card (Cell n) : ℝ)=(n : ℝ)^3 := by simp [Cell,pow_succ]; ring
  rw [hcard] at hh
  have hn : 0 < (n : ℝ) := by exact_mod_cast (NeZero.pos n)
  apply (mul_le_mul_iff_right₀ (pow_pos hn 3)).mp
  dsimp [scalarEdges] at *
  nlinarith only [hh]

def neighbors (n : ℕ) [NeZero n] : Fin 3 → Equiv.Perm (Cell n) :=
  ![Equiv.prodCongr (Equiv.addRight (1 : Fin n)) (Equiv.refl _),
    Equiv.prodCongr (Equiv.refl _) (Equiv.prodCongr (Equiv.addRight (1 : Fin n)) (Equiv.refl _)),
    Equiv.prodCongr (Equiv.refl _) (Equiv.prodCongr (Equiv.refl _) (Equiv.addRight (1 : Fin n)))]

theorem scalar_edges_as_cells (n : ℕ) [NeZero n] (f : Cell n → ℝ) :
    scalarEdges f=∑ d, ∑ x, (f (neighbors n d x)-f x)^2 := by
  have hx : (∑ j, ∑ k, ∑ i, (f (i+1,(j,k))-f (i,(j,k)))^2)=
      ∑ i, ∑ j, ∑ k, (f (i+1,(j,k))-f (i,(j,k)))^2 := by
    calc
      _ = ∑ j, ∑ i, ∑ k, (f (i+1,(j,k))-f (i,(j,k)))^2 :=
        Finset.sum_congr rfl (fun j _ => Finset.sum_comm)
      _ = _ := Finset.sum_comm
  have hy : (∑ i, ∑ k, ∑ j, (f (i,(j+1,k))-f (i,(j,k)))^2)=
      ∑ i, ∑ j, ∑ k, (f (i,(j+1,k))-f (i,(j,k)))^2 :=
    Finset.sum_congr rfl (fun i _ => Finset.sum_comm)
  simp only [scalarEdges,lineX,lineY,lineZ,hx,hy,Fin.sum_univ_succ,neighbors,
    Matrix.cons_val_zero,Equiv.prodCongr_apply,Fintype.sum_prod_type]
  simp [add_assoc]

def meanState {I : Type*} [Fintype I] (u : I → EulerEntropy.State) : EulerEntropy.State :=
  (1/(Fintype.card I : ℝ)) • ∑ i, u i

theorem mean_component {I : Type*} [Fintype I] (u : I → EulerEntropy.State) (j : Fin 5) :
    meanState u j=scalarMean (fun i => u i j) := by
  simp only [meanState,Pi.smul_apply,Finset.sum_apply,smul_eq_mul,scalarMean]
  ring

theorem vector_poincare (n : ℕ) [NeZero n] (u : Cell n → EulerEntropy.State) :
    (∑ i, EulerEnergyBounds.sizeSquared (u i-meanState u)) ≤
      (3/2 : ℝ)*(n : ℝ)^2*EulerFiniteVolumeEntropy.edgeEnergy u (neighbors n) := by
  have hj (j : Fin 5) := scalar_poincare n (fun i => u i j)
  have hh := Finset.sum_le_sum (fun j (_ : j ∈ Finset.univ) => hj j)
  simp only [scalarVariance,← mean_component,scalar_edges_as_cells] at hh
  rw [Finset.sum_comm] at hh
  simp only [← Finset.mul_sum] at hh
  have he : (∑ j : Fin 5, ∑ d : Fin 3, ∑ i : Cell n,
      (u (neighbors n d i) j-u i j)^2)=EulerFiniteVolumeEntropy.edgeEnergy u (neighbors n) := by
    rw [Finset.sum_comm]
    simp only [EulerFiniteVolumeEntropy.edgeEnergy,EulerVectorEstimates.size_as_sum,Pi.sub_apply]
    exact Finset.sum_congr rfl (fun d _ => Finset.sum_comm)
  rw [he] at hh
  simpa only [EulerVectorEstimates.size_as_sum,Pi.sub_apply] using hh

end EulerGridPoincare
