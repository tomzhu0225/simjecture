import Mathlib.MeasureTheory.Integral.Pi
import Mathlib.Analysis.SpecialFunctions.Integrals.Basic

-- Continuous periodic trilinear reconstruction of actual conserved grid states.
noncomputable section
namespace EulerHatReconstruction
open MeasureTheory EulerEntropyIntegral
open scoped BigOperators
abbrev State := Fin 5 → ℝ

def ramp (x : ℝ) : ℝ := max 0 (min 1 x)
def hat (x : ℝ) : ℝ := ramp (x+1)-ramp x

theorem ramp_zero (x : ℝ) (hx : x ≤ 0) : ramp x=0 := by
  simp [ramp,min_eq_right (by linarith : x ≤ 1),max_eq_left hx]

theorem ramp_one (x : ℝ) (hx : 1 ≤ x) : ramp x=1 := by
  simp [ramp,min_eq_left hx]

theorem ramp_middle (x : ℝ) (h0 : 0 ≤ x) (h1 : x ≤ 1) : ramp x=x := by
  simp [ramp,min_eq_right h1,max_eq_right h0]

theorem hat_nonnegative (x : ℝ) : 0 ≤ hat x := by
  apply sub_nonneg.mpr
  exact max_le_max le_rfl (min_le_min_left 1 (by linarith : x ≤ x+1))

theorem hat_continuous : Continuous hat := by unfold hat ramp; fun_prop

theorem hat_zero_left (x : ℝ) (hx : x ≤ -1) : hat x=0 := by
  rw [hat,ramp_zero (x+1) (by linarith),ramp_zero x (by linarith),sub_self]

theorem hat_zero_right (x : ℝ) (hx : 1 ≤ x) : hat x=0 := by
  rw [hat,ramp_one (x+1) (by linarith),ramp_one x hx,sub_self]

theorem hat_left (x : ℝ) (h0 : -1 ≤ x) (h1 : x ≤ 0) : hat x=x+1 := by
  rw [hat,ramp_middle (x+1) (by linarith) (by linarith),ramp_zero x h1,sub_zero]

theorem hat_right (x : ℝ) (h0 : 0 ≤ x) (h1 : x ≤ 1) : hat x=1-x := by
  rw [hat,ramp_one (x+1) (by linarith),ramp_middle x h0 h1]

theorem sum_hat (n : ℕ) (s : ℝ) :
    (∑ i : Fin n, hat (s-(i.val : ℝ)))=ramp (s+1)-ramp (s-(n : ℝ)+1) := by
  induction n with
  | zero => simp
  | succ n ih =>
    rw [Fin.sum_univ_castSucc]
    simp only [Fin.coe_castSucc,Fin.val_last,Nat.cast_add,Nat.cast_one]
    rw [ih]
    have he : s-((n : ℝ)+1)+1=s-(n : ℝ) := by ring
    rw [he]
    dsimp [hat]
    ring

def periodicHat (n : ℕ) (i : Fin n) (s : ℝ) : ℝ :=
  hat (s-(i.val : ℝ))+hat (s-(i.val : ℝ)+(n : ℝ))+hat (s-(i.val : ℝ)-(n : ℝ))

theorem periodic_hat_nonnegative (n : ℕ) (i : Fin n) (s : ℝ) : 0 ≤ periodicHat n i s :=
  add_nonneg (add_nonneg (hat_nonnegative _) (hat_nonnegative _)) (hat_nonnegative _)

theorem periodic_hat_continuous (n : ℕ) (i : Fin n) : Continuous (periodicHat n i) := by
  unfold periodicHat
  exact ((hat_continuous.comp (continuous_id.sub continuous_const)).add
    (hat_continuous.comp ((continuous_id.sub continuous_const).add continuous_const))).add
    (hat_continuous.comp ((continuous_id.sub continuous_const).sub continuous_const))

theorem periodic_hat_sum (n : ℕ) [NeZero n] (s : ℝ)
    (hs0 : -(1/2 : ℝ) ≤ s) (hs1 : s ≤ (n : ℝ)-1/2) :
    (∑ i : Fin n, periodicHat n i s)=1 := by
  have hn : 1 ≤ (n : ℝ) := by exact_mod_cast (NeZero.one_le : 1 ≤ n)
  have ep (i : Fin n) : s-(i.val : ℝ)+(n : ℝ)=(s+(n : ℝ))-(i.val : ℝ) := by ring
  have em (i : Fin n) : s-(i.val : ℝ)-(n : ℝ)=(s-(n : ℝ))-(i.val : ℝ) := by ring
  simp only [periodicHat,ep,em,Finset.sum_add_distrib,sum_hat]
  have e1 : s+(n : ℝ)-(n : ℝ)+1=s+1 := by ring
  have e2 : s-(n : ℝ)-(n : ℝ)+1=s-2*(n : ℝ)+1 := by ring
  rw [e1,e2,ramp_one (s+(n : ℝ)+1) (by linarith),
    ramp_zero (s-2*(n : ℝ)+1) (by linarith)]
  ring

theorem periodic_hat_boundary (n : ℕ) [NeZero n] (i : Fin n) :
    periodicHat n i ((n : ℝ)-1/2)=periodicHat n i (-(1/2 : ℝ)) := by
  have hn : 1 ≤ (n : ℝ) := by exact_mod_cast (NeZero.one_le : 1 ≤ n)
  have hi : (i.val : ℝ)+1 ≤ (n : ℝ) := by exact_mod_cast i.isLt
  have hi0 : 0 ≤ (i.val : ℝ) := Nat.cast_nonneg _
  have e1 : (n : ℝ)-1/2-(i.val : ℝ)= -(1/2 : ℝ)-(i.val : ℝ)+(n : ℝ) := by ring
  have e2 : (n : ℝ)-1/2-(i.val : ℝ)-(n : ℝ)= -(1/2 : ℝ)-(i.val : ℝ) := by ring
  unfold periodicHat
  rw [hat_zero_right ((n : ℝ)-1/2-(i.val : ℝ)+(n : ℝ)) (by linarith),
    hat_zero_left (-(1/2 : ℝ)-(i.val : ℝ)-(n : ℝ)) (by linarith),e2,e1]
  ring

def weight (n : ℕ) (L : ℝ) (i : Fin n) (x : ℝ) : ℝ :=
  periodicHat n i ((n : ℝ)*x/L-1/2)

theorem weight_nonnegative (n : ℕ) (L : ℝ) (i : Fin n) (x : ℝ) : 0 ≤ weight n L i x :=
  periodic_hat_nonnegative n i _

theorem weight_continuous (n : ℕ) (L : ℝ) (i : Fin n) : Continuous (weight n L i) := by
  exact (periodic_hat_continuous n i).comp (by fun_prop)

theorem weight_sum (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (x : ℝ) (hx : x ∈ Set.Icc (0 : ℝ) L) :
    (∑ i : Fin n, weight n L i x)=1 := by
  apply periodic_hat_sum
  · have hh : 0 ≤ (n : ℝ)*x/L := div_nonneg (mul_nonneg (Nat.cast_nonneg _) hx.1) hL.le
    linarith
  · have hh : (n : ℝ)*x/L ≤ (n : ℝ) := by
      apply (div_le_iff₀ hL).mpr
      exact mul_le_mul_of_nonneg_left hx.2 (Nat.cast_nonneg _)
    linarith

theorem weight_boundary (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (i : Fin n) :
    weight n L i L=weight n L i 0 := by
  simpa [weight,ne_of_gt hL] using periodic_hat_boundary n i

theorem hat_support (a b : ℝ) (ha : a ≤ -1) (hb : 1 ≤ b) :
    Function.support hat ⊆ Set.Ioc a b := by
  intro x hx
  have hl : -1 < x := lt_of_not_ge (fun h => hx (hat_zero_left x h))
  have hr : x < 1 := lt_of_not_ge (fun h => hx (hat_zero_right x h))
  exact ⟨ha.trans_lt hl,hr.le.trans hb⟩

theorem hat_unit_integral : (∫ x in (-1 : ℝ)..1, hat x)=1 := by
  have hl : (∫ x in (-1 : ℝ)..0, hat x)=1/2 := by
    calc
      _ = ∫ x in (-1 : ℝ)..0, x+1 := intervalIntegral.integral_congr (fun x hx => by
        rw [Set.uIcc_of_le (by norm_num : (-1 : ℝ) ≤ 0)] at hx
        exact hat_left x hx.1 hx.2)
      _ = _ := by
        rw [intervalIntegral.integral_add (f := fun x : ℝ => x) (g := fun _ => (1 : ℝ))
          (continuous_id.intervalIntegrable _ _) (continuous_const.intervalIntegrable _ _)]
        norm_num
  have hr : (∫ x in (0 : ℝ)..1, hat x)=1/2 := by
    calc
      _ = ∫ x in (0 : ℝ)..1, 1-x := intervalIntegral.integral_congr (fun x hx => by
        rw [Set.uIcc_of_le (by norm_num : (0 : ℝ) ≤ 1)] at hx
        exact hat_right x hx.1 hx.2)
      _ = _ := by
        rw [intervalIntegral.integral_sub (f := fun _ : ℝ => (1 : ℝ)) (g := fun x => x)
          (continuous_const.intervalIntegrable _ _) (continuous_id.intervalIntegrable _ _)]
        norm_num
  rw [← intervalIntegral.integral_add_adjacent_intervals
    (hat_continuous.intervalIntegrable (-1) 0) (hat_continuous.intervalIntegrable 0 1),hl,hr]
  norm_num

theorem hat_integral (a b : ℝ) (ha : a ≤ -1) (hb : 1 ≤ b) :
    (∫ x in a..b, hat x)=1 := by
  rw [intervalIntegral.integral_eq_integral_of_support_subset (hat_support a b ha hb),
    ← intervalIntegral.integral_eq_integral_of_support_subset
      (hat_support (-1) 1 le_rfl le_rfl)]
  exact hat_unit_integral

theorem periodic_hat_integral (n : ℕ) [NeZero n] (i : Fin n) :
    (∫ s in -(1/2 : ℝ)..(n : ℝ)-1/2, periodicHat n i s)=1 := by
  have hn : 1 ≤ (n : ℝ) := by exact_mod_cast (NeZero.one_le : 1 ≤ n)
  have hi : (i.val : ℝ)+1 ≤ (n : ℝ) := by exact_mod_cast i.isLt
  have hi0 : 0 ≤ (i.val : ℝ) := Nat.cast_nonneg _
  let a := -(1/2 : ℝ)-(i.val : ℝ)-(n : ℝ)
  let b := -(1/2 : ℝ)-(i.val : ℝ)
  let c := (n : ℝ)-1/2-(i.val : ℝ)
  let d := (n : ℝ)-1/2-(i.val : ℝ)+(n : ℝ)
  have hp : (∫ s in -(1/2 : ℝ)..(n : ℝ)-1/2, hat (s-(i.val : ℝ)+(n : ℝ)))=
      ∫ s in c..d, hat s := by
    calc
      _ = ∫ s in -(1/2 : ℝ)..(n : ℝ)-1/2, hat (s+((n : ℝ)-(i.val : ℝ))) :=
        intervalIntegral.integral_congr (fun s _ => congrArg hat (by ring))
      _ = _ := by
        rw [intervalIntegral.integral_comp_add_right]
        congr 1 <;> dsimp [c,d] <;> ring
  have hm : (∫ s in -(1/2 : ℝ)..(n : ℝ)-1/2, hat (s-(i.val : ℝ)-(n : ℝ)))=
      ∫ s in a..b, hat s := by
    calc
      _ = ∫ s in -(1/2 : ℝ)..(n : ℝ)-1/2, hat (s-((i.val : ℝ)+(n : ℝ))) :=
        intervalIntegral.integral_congr (fun s _ => congrArg hat (by ring))
      _ = _ := by
        rw [intervalIntegral.integral_comp_sub_right]
        congr 1 <;> dsimp [a,b] <;> ring
  have hc0 : Continuous (fun s => hat (s-(i.val : ℝ))) :=
    hat_continuous.comp (continuous_id.sub continuous_const)
  have hcp : Continuous (fun s => hat (s-(i.val : ℝ)+(n : ℝ))) :=
    hat_continuous.comp ((continuous_id.sub continuous_const).add continuous_const)
  have hcm : Continuous (fun s => hat (s-(i.val : ℝ)-(n : ℝ))) :=
    hat_continuous.comp ((continuous_id.sub continuous_const).sub continuous_const)
  simp only [periodicHat]
  rw [intervalIntegral.integral_add ((hc0.add hcp).intervalIntegrable _ _)
    (hcm.intervalIntegrable _ _),intervalIntegral.integral_add
    (hc0.intervalIntegrable _ _) (hcp.intervalIntegrable _ _),hp,hm,
    intervalIntegral.integral_comp_sub_right]
  change ((∫ s in b..c, hat s)+(∫ s in c..d, hat s))+(∫ s in a..b, hat s)=1
  rw [intervalIntegral.integral_add_adjacent_intervals
    (hat_continuous.intervalIntegrable b c) (hat_continuous.intervalIntegrable c d),add_comm,
    intervalIntegral.integral_add_adjacent_intervals
    (hat_continuous.intervalIntegrable a b) (hat_continuous.intervalIntegrable b d)]
  exact hat_integral a d (by dsimp [a]; linarith) (by dsimp [d]; linarith)

theorem weight_integral (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (i : Fin n) :
    (∫ x in Set.Icc (0 : ℝ) L, weight n L i x)=L/(n : ℝ) := by
  have hn : (n : ℝ) ≠ 0 := by exact_mod_cast NeZero.ne n
  rw [integral_Icc_eq_integral_Ioc,← intervalIntegral.integral_of_le hL.le]
  have he : weight n L i=(fun x => periodicHat n i (((n : ℝ)/L)*x-1/2)) := by
    funext x
    unfold weight
    congr 1
    ring
  rw [he,intervalIntegral.integral_comp_mul_sub _ (div_ne_zero hn (ne_of_gt hL))]
  simp only [mul_zero,zero_sub,div_mul_cancel₀ _ (ne_of_gt hL),periodic_hat_integral,
    smul_eq_mul,mul_one,inv_div]

abbrev Cell (n : ℕ) := EulerGridPoincare.Cell n
def coordinates {n : ℕ} (i : Cell n) : Fin 3 → Fin n := ![i.1,i.2.1,i.2.2]
def weight3 (n : ℕ) (L : ℝ) (i : Cell n) (x : Space) : ℝ :=
  weight n L i.1 (x 0)*weight n L i.2.1 (x 1)*weight n L i.2.2 (x 2)

theorem weight3_product (n : ℕ) (L : ℝ) (i : Cell n) (x : Space) :
    weight3 n L i x=∏ d : Fin 3, weight n L (coordinates i d) (x d) := by
  simp [weight3,coordinates,Fin.prod_univ_succ,mul_assoc]

theorem weight3_nonnegative (n : ℕ) (L : ℝ) (i : Cell n) (x : Space) : 0 ≤ weight3 n L i x :=
  mul_nonneg (mul_nonneg (weight_nonnegative _ _ _ _) (weight_nonnegative _ _ _ _))
    (weight_nonnegative _ _ _ _)

theorem weight3_continuous (n : ℕ) (L : ℝ) (i : Cell n) : Continuous (weight3 n L i) :=
  (((weight_continuous n L i.1).comp (continuous_apply 0)).mul
    ((weight_continuous n L i.2.1).comp (continuous_apply 1))).mul
    ((weight_continuous n L i.2.2).comp (continuous_apply 2))

theorem weight3_sum (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (x : Space) (hx : x ∈ cube L) :
    (∑ i : Cell n, weight3 n L i x)=1 := by
  have hs (d : Fin 3) := weight_sum n L hL (x d) ⟨hx.1 d,hx.2 d⟩
  simp only [Fintype.sum_prod_type,weight3,← Finset.mul_sum,hs,mul_one]

theorem cube_product_measure (L : ℝ) :
    (volume : Measure Space).restrict (cube L)=
      Measure.pi (fun _ : Fin 3 => (volume : Measure ℝ).restrict (Set.Icc (0 : ℝ) L)) := by
  rw [cube,← Set.pi_univ_Icc]
  exact Measure.restrict_pi_pi _ _

theorem weight3_integral (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (i : Cell n) :
    (∫ x, weight3 n L i x ∂cubeMeasure L)=1/(n : ℝ)^3 := by
  have he : (∫ x in cube L, weight3 n L i x)=(L/(n : ℝ))^3 := by
    simp_rw [weight3_product]
    rw [cube_product_measure,integral_fintype_prod_eq_prod]
    simp only [weight_integral n L hL,Finset.prod_const,Finset.card_univ,Fintype.card_fin]
  rw [cube_integral L hL.le,he,smul_eq_mul]
  have hn : (n : ℝ) ≠ 0 := by exact_mod_cast NeZero.ne n
  field_simp

def reconstruct (n : ℕ) (L : ℝ) (u : Cell n → State) (x : Space) : State :=
  ∑ i, weight3 n L i x • u i

theorem reconstruction_continuous (n : ℕ) (L : ℝ) (u : Cell n → State) :
    Continuous (reconstruct n L u) := by
  exact continuous_finset_sum _ (fun i _ => (weight3_continuous n L i).smul continuous_const)

theorem reconstruction_in_region (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (u : Cell n → State)
    (hu : ∀ i, u i ∈ EulerPhysicalRegion.region) (x : Space) (hx : x ∈ cube L) :
    reconstruct n L u x ∈ EulerPhysicalRegion.region := by
  exact EulerPhysicalRegion.region_convex.sum_mem
    (fun i _ => weight3_nonnegative n L i x) (weight3_sum n L hL x hx) (fun i _ => hu i)

theorem reconstruction_mean (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (u : Cell n → State) :
    (∫ x, reconstruct n L u x ∂cubeMeasure L)=EulerGridPoincare.meanState u := by
  have hi (i : Cell n) : Integrable (fun x => weight3 n L i x • u i) (cubeMeasure L) :=
    cube_integrable L _ ((weight3_continuous n L i).smul continuous_const).continuousOn
  change (∫ x, ∑ i, weight3 n L i x • u i ∂cubeMeasure L)=_
  rw [integral_finset_sum Finset.univ (fun i _ => hi i)]
  simp only [integral_smul_const,weight3_integral n L hL,← Finset.smul_sum,
    EulerGridPoincare.meanState,Fintype.card_prod,Fintype.card_fin,Nat.cast_mul]
  congr 1
  ring

theorem reconstruction_entropy (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (u : Cell n → State)
    (hu : ∀ i, u i ∈ EulerPhysicalRegion.region) :
    (∫ x, EulerEntropy.entropy (reconstruct n L u x) ∂cubeMeasure L) ≤
      (1/(n : ℝ)^3)*∑ i, EulerEntropy.entropy (u i) := by
  have hfield := reconstruction_in_region n L hL u hu
  have he : Integrable (fun x => EulerEntropy.entropy (reconstruct n L u x)) (cubeMeasure L) :=
    cube_integrable L _ (entropy_continuousOn L _ (reconstruction_continuous n L u).continuousOn hfield)
  have hi (i : Cell n) : Integrable (fun x => weight3 n L i x*EulerEntropy.entropy (u i)) (cubeMeasure L) :=
    cube_integrable L _ ((weight3_continuous n L i).mul continuous_const).continuousOn
  calc
    _ ≤ ∫ x, ∑ i, weight3 n L i x*EulerEntropy.entropy (u i) ∂cubeMeasure L := by
      apply integral_mono_ae he (integrable_finset_sum Finset.univ (fun i _ => hi i))
      filter_upwards [cube_ae_mem L] with x hx
      exact EulerEntropyConvexity.entropy_convex_mixture (fun i => weight3 n L i x) u
        (fun i => weight3_nonnegative n L i x) (weight3_sum n L hL x hx)
        (fun i => EulerPhysicalRegion.region_admissible _ (hu i))
    _ = _ := by
      rw [integral_finset_sum Finset.univ (fun i _ => hi i)]
      simp only [integral_mul_const,weight3_integral n L hL,← Finset.mul_sum]

theorem reconstruction_boundary (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L)
    (u : Cell n → State) (x : Space) (d : Fin 3) :
    reconstruct n L u (Function.update x d L)=reconstruct n L u (Function.update x d 0) := by
  apply Finset.sum_congr rfl
  intro i _
  congr 1
  rw [weight3_product,weight3_product]
  apply Finset.prod_congr rfl
  intro e _
  by_cases h : e=d
  · subst e
    simp only [Function.update_self]
    exact weight_boundary n L hL _
  · simp [h]

theorem periodic_hat_node (n : ℕ) [NeZero n] (i k : Fin n) :
    periodicHat n i (k.val : ℝ)=if i=k then 1 else 0 := by
  have hi : (i.val : ℝ)+1 ≤ (n : ℝ) := by exact_mod_cast i.isLt
  have hk : (k.val : ℝ)+1 ≤ (n : ℝ) := by exact_mod_cast k.isLt
  have hi0 : 0 ≤ (i.val : ℝ) := Nat.cast_nonneg _
  have hk0 : 0 ≤ (k.val : ℝ) := Nat.cast_nonneg _
  rw [periodicHat,hat_zero_right ((k.val : ℝ)-(i.val : ℝ)+(n : ℝ)) (by linarith),
    hat_zero_left ((k.val : ℝ)-(i.val : ℝ)-(n : ℝ)) (by linarith),add_zero,add_zero]
  by_cases h : i=k
  · subst i
    simp [hat,ramp]
  · rw [if_neg h]
    have hv : i.val ≠ k.val := fun he => h (Fin.ext he)
    rcases lt_or_gt_of_ne hv with hlt | hgt
    · have hh : (i.val : ℝ)+1 ≤ (k.val : ℝ) := by exact_mod_cast hlt
      exact hat_zero_right _ (by linarith)
    · have hh : (k.val : ℝ)+1 ≤ (i.val : ℝ) := by exact_mod_cast hgt
      exact hat_zero_left _ (by linarith)

theorem weight_node (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (i k : Fin n) :
    weight n L i (((k.val : ℝ)+1/2)*L/(n : ℝ))=if i=k then 1 else 0 := by
  have hn : (n : ℝ) ≠ 0 := by exact_mod_cast NeZero.ne n
  have he : (n : ℝ)*(((k.val : ℝ)+1/2)*L/(n : ℝ))/L-1/2=(k.val : ℝ) := by
    field_simp
    ring
  rw [weight,he,periodic_hat_node]

def node (n : ℕ) (L : ℝ) (i : Cell n) : Space :=
  fun d => (((coordinates i d).val : ℝ)+1/2)*L/(n : ℝ)

theorem weight3_node (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (i k : Cell n) :
    weight3 n L i (node n L k)=if i=k then 1 else 0 := by
  simp only [weight3,node,coordinates,Matrix.cons_val_zero,Matrix.cons_val_one,
    Matrix.cons_val_two,Matrix.vecHead,Matrix.vecTail,weight_node n L hL]
  by_cases h0 : i.1=k.1 <;> by_cases h1 : i.2.1=k.2.1 <;> by_cases h2 : i.2.2=k.2.2 <;>
    simp_all [Prod.ext_iff]

theorem reconstruction_nodes (n : ℕ) [NeZero n] (L : ℝ) (hL : 0 < L) (u : Cell n → State) (i : Cell n) :
    reconstruct n L u (node n L i)=u i := by
  simp [reconstruct,weight3_node n L hL]

theorem reconstructed_physical_error_lower_bound (n : ℕ) [NeZero n] (u : Cell n → State)
    (hu : ∀ i, u i ∈ EulerPhysicalRegion.region) (U : Point → State)
    (T L : ℝ) (hT : 0 ≤ T) (hL : 0 < L)
    (hU : ∀ x ∈ box T L, DifferentiableAt ℝ U x)
    (hphys : ∀ x ∈ box T L, EulerAdmissible.Admissible (U x))
    (heuler : ∀ x ∈ box T L, eulerResidual U x=0) (hperiodic : PeriodicBoundary U T L)
    (hUT : ∀ y ∈ cube L, U (Fin.cons T y) ∈ EulerPhysicalRegion.region) :
    ((∫ y, EulerEntropy.entropy (U (Fin.cons 0 y)) ∂cubeMeasure L)-
      (1/(n : ℝ)^3)*∑ i, EulerEntropy.entropy (u i))/160 ≤
      EulerEntropyError.maxComponentError (cubeMeasure L) (fun y => U (Fin.cons T y))
        (reconstruct n L u) := by
  have he := physical_error_from_initial_entropy U (reconstruct n L u) T L hT hL
    hU hphys heuler hperiodic hUT (reconstruction_continuous n L u).continuousOn
    (reconstruction_in_region n L hL u hu)
  have hr := reconstruction_entropy n L hL u hu
  have ha := le_abs_self ((∫ y, EulerEntropy.entropy (U (Fin.cons 0 y)) ∂cubeMeasure L)-
    (∫ y, EulerEntropy.entropy (reconstruct n L u y) ∂cubeMeasure L))
  rw [abs_sub_comm] at ha
  linarith only [he,hr,ha]

end EulerHatReconstruction
