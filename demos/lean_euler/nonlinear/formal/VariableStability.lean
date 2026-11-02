-- Assemble after VariableEnergy.lean and CoefficientBounds.lean. This concerns
-- the variable-coefficient principal update, not the complete nonlinear map.
noncomputable section
namespace EulerVariableStability
open EulerPrimitiveEnergy EulerDiscreteEnergy EulerEnergyBounds
open EulerVariableEnergy EulerCoefficientBounds
open scoped BigOperators

theorem split_contribution_formula (q p v a ratio sign : ℝ) (hq : 0 < q) (hp : 0 < p)
    (d : Fin 3) (x : State) :
    metric q p x (splitAction q p v a ratio sign d x) =
      (ratio/2)*((a+sign*v)*metric q p x x+sign*(2*x 4*x ⟨d.val+1,by omega⟩)) := by
  simp only [splitAction,metric_smul_right,metric_add_right,
    principal_metric_identity q p v hq hp d x x]
  ring

theorem split_contribution_variation (q p q' p' v v' a ratio sign B : ℝ)
    (hq : 1/4 ≤ q) (hp : 1/4 ≤ p) (hq' : 1/4 ≤ q') (hp' : 1/4 ≤ p')
    (hr : 0 ≤ ratio) (hs : sign^2=1) (hB : |a+sign*v'| ≤ B) (d : Fin 3) (x : State) :
    |metric q' p' x (splitAction q' p' v' a ratio sign d x)-
      metric q p x (splitAction q p v a ratio sign d x)| ≤
      (ratio/2)*(256*B*(|q'-q|+|p'-p|)+32*|v'-v|)*sizeSquared x := by
  have hsign : |sign| = 1 := by nlinarith [sq_abs sign,abs_nonneg sign]
  have he : |(a+sign*v')-(a+sign*v)| = |v'-v| := by
    rw [show (a+sign*v')-(a+sign*v)=sign*(v'-v) by ring,abs_mul,hsign,one_mul]
  have heq : metric q' p' x (splitAction q' p' v' a ratio sign d x)-
      metric q p x (splitAction q p v a ratio sign d x) =
      (ratio/2)*((a+sign*v')*metric q' p' x x-(a+sign*v)*metric q p x x) := by
    rw [split_contribution_formula q' p' v' a ratio sign (by linarith) (by linarith),
      split_contribution_formula q p v a ratio sign (by linarith) (by linarith)]
    ring
  have hb := weighted_metric_variation q p q' p' (a+sign*v) (a+sign*v') B hq hp hq' hp' hB x
  rw [he] at hb
  rw [heq,abs_mul,abs_of_nonneg (by positivity : 0 ≤ ratio/2)]
  calc
    _ ≤ (ratio/2)*((256*B*(|q'-q|+|p'-p|)+32*|v'-v|)*sizeSquared x) :=
      mul_le_mul_of_nonneg_left hb (by positivity)
    _ = _ := by ring

theorem split_gradient_bound (q p q' p' v v' a ratio sign B h K D : ℝ)
    (hq : 1/4 ≤ q) (hp : 1/4 ≤ p) (hq' : 1/4 ≤ q') (hp' : 1/4 ≤ p')
    (hr : 0 ≤ ratio) (hs : sign^2=1) (hB : |a+sign*v'| ≤ B)
    (hh : 0 ≤ h) (hK : 0 ≤ K) (hD : 0 ≤ D)
    (hqp : |q'-q|+|p'-p| ≤ h*K) (hv : |v'-v| ≤ h*D) (d : Fin 3) (x : State) :
    |metric q' p' x (splitAction q' p' v' a ratio sign d x)-
      metric q p x (splitAction q p v a ratio sign d x)| ≤
      ratio*h*(256*B*K+32*D)*sizeSquared x := by
  have hBn : 0 ≤ B := (abs_nonneg _).trans hB
  have hsn : 0 ≤ sizeSquared x := by dsimp [sizeSquared]; positivity
  calc
    _ ≤ (ratio/2)*(256*B*(|q'-q|+|p'-p|)+32*|v'-v|)*sizeSquared x :=
      split_contribution_variation q p q' p' v v' a ratio sign B hq hp hq' hp' hr hs hB d x
    _ ≤ (ratio/2)*(256*B*(h*K)+32*(h*D))*sizeSquared x :=
      mul_le_mul_of_nonneg_right (mul_le_mul_of_nonneg_left
        (add_le_add (mul_le_mul_of_nonneg_left hqp (by positivity))
          (mul_le_mul_of_nonneg_left hv (by norm_num))) (by positivity)) hsn
    _ ≤ ratio*h*(256*B*K+32*D)*sizeSquared x := by
      have hn : 0 ≤ ratio*h*(256*B*K+32*D)*sizeSquared x := by positivity
      nlinarith

theorem variable_principal_energy_growth {I : Type*} [Fintype I]
    (q p : I → ℝ) (ratio : ℝ) (v : I → Fin 3 → ℝ) (a : Fin 3 → ℝ)
    (hq : ∀ i, 1/4 ≤ q i) (hp : ∀ i, 1/4 ≤ p i)
    (hq4 : ∀ i, q i ≤ 4) (hp4 : ∀ i, p i ≤ 4)
    (hr : 0 ≤ ratio) (ha : ∀ i d, |v i d|+Real.sqrt (2*p i*q i) ≤ a d)
    (hcf : ratio*(a 0+a 1+a 2) ≤ 1)
    (shift : Fin 7 → Equiv.Perm I) (hcenter : shift 0 = Equiv.refl I)
    (B h K D : ℝ) (hBn : 0 ≤ B) (hh : 0 ≤ h) (hK : 0 ≤ K) (hD : 0 ≤ D)
    (hB : ∀ i d, |a d|+|v i d| ≤ B)
    (hqp : ∀ i j, |q ((shift j).symm i)-q i|+|p ((shift j).symm i)-p i| ≤ h*K)
    (hv : ∀ i j d, |v ((shift j).symm i) d-v i d| ≤ h*D) (u : I → State) :
    (∑ i, metric (q i) (p i) (variableUpdate q p ratio v a shift u i)
      (variableUpdate q p ratio v a shift u i)) ≤
      (1+756*ratio*h*(256*B*K+32*D))*(∑ i, metric (q i) (p i) (u i) (u i)) := by
  have hqpos (i : I) : 0 < q i := by linarith [hq i]
  have hppos (i : I) : 0 < p i := by linarith [hp i]
  have hsn (i : I) : 0 ≤ sizeSquared (u i) := by dsimp [sizeSquared]; positivity
  have hsplit (i : I) (j : Fin 7) (d : Fin 3) (sign : ℝ) (hs : sign^2=1) :
      |metric (q ((shift j).symm i)) (p ((shift j).symm i)) (u i)
        (splitAction (q ((shift j).symm i)) (p ((shift j).symm i))
          (v ((shift j).symm i) d) (a d) ratio sign d (u i))-
      metric (q i) (p i) (u i) (splitAction (q i) (p i) (v i d) (a d) ratio sign d (u i))| ≤
        ratio*h*(256*B*K+32*D)*sizeSquared (u i) := by
    apply split_gradient_bound _ _ _ _ _ _ _ _ _ _ _ _ _
      (hq i) (hp i) (hq _) (hp _) hr hs _ hh hK hD (hqp i j) (hv i j d) d (u i)
    have hsign : |sign| = 1 := by nlinarith [sq_abs sign,abs_nonneg sign]
    calc
      _ ≤ |a d|+|sign*v ((shift j).symm i) d| := abs_add_le _ _
      _ = |a d|+|v ((shift j).symm i) d| := by rw [abs_mul,hsign,one_mul]
      _ ≤ B := hB _ d
  have hlocal (i : I) (j : Fin 7) :
      |localContribution q p ratio v a ((shift j).symm i) j (u i)-
        localContribution q p ratio v a i j (u i)| ≤
      ratio*h*(256*B*K+32*D)*sizeSquared (u i) := by
    fin_cases j
    · change |localContribution q p ratio v a ((shift 0).symm i) 0 (u i)-
        localContribution q p ratio v a i 0 (u i)| ≤ _
      rw [hcenter]
      change |localContribution q p ratio v a i 0 (u i)-localContribution q p ratio v a i 0 (u i)| ≤ _
      rw [sub_self,abs_zero]
      exact mul_nonneg (by positivity) (hsn i)
    · exact hsplit i 1 0 (-1) (by norm_num)
    · exact hsplit i 2 0 1 (by norm_num)
    · exact hsplit i 3 1 (-1) (by norm_num)
    · exact hsplit i 4 1 1 (by norm_num)
    · exact hsplit i 5 2 (-1) (by norm_num)
    · exact hsplit i 6 2 1 (by norm_num)
  have hsum (i : I) :
      (∑ j, (localContribution q p ratio v a ((shift j).symm i) j (u i)-
        localContribution q p ratio v a i j (u i))) ≤
      7*(ratio*h*(256*B*K+32*D)*sizeSquared (u i)) := by
    have hb := Finset.sum_le_sum (fun (j : Fin 7) (_ : j ∈ Finset.univ) =>
      (le_abs_self _).trans (hlocal i j))
    simpa only [Finset.sum_const,Finset.card_univ,Fintype.card_fin,nsmul_eq_mul,Nat.cast_ofNat] using hb
  have hdef : variationDefect q p ratio v a shift u ≤
      (756*ratio*h*(256*B*K+32*D))*(∑ i, metric (q i) (p i) (u i) (u i)) := by
    calc
      _ ≤ ∑ i, 7*(ratio*h*(256*B*K+32*D)*sizeSquared (u i)) :=
        Finset.sum_le_sum (fun i _ => hsum i)
      _ ≤ ∑ i, 7*(ratio*h*(256*B*K+32*D)*(108*metric (q i) (p i) (u i) (u i))) :=
        Finset.sum_le_sum (fun i _ => mul_le_mul_of_nonneg_left
          (mul_le_mul_of_nonneg_left (box_coercivity (q i) (p i) (hq i) (hq4 i) (hp i) (hp4 i) (u i))
            (by positivity)) (by norm_num))
      _ = _ := by simp only [← Finset.mul_sum]; ring
  have henergy := variable_principal_energy_defect q p ratio v a hqpos hppos hr ha hcf shift u
  calc
    _ ≤ (∑ i, metric (q i) (p i) (u i) (u i))+variationDefect q p ratio v a shift u := henergy
    _ ≤ (∑ i, metric (q i) (p i) (u i) (u i))+
        (756*ratio*h*(256*B*K+32*D))*(∑ i, metric (q i) (p i) (u i) (u i)) :=
      add_le_add_left hdef _
    _ = _ := by ring

def witnessQ : Fin 2 → ℝ := ![1,2]
def entropyError (c : ℝ) : State := fun k => if k=0 then c else 0
def witnessError (i : Fin 2) : State := entropyError (if i=0 then 1 else 4)
def witnessShift (j : Fin 7) : Equiv.Perm (Fin 2) :=
  if j=0 then Equiv.refl _ else Equiv.swap 0 1

theorem principal_entropy (q p c : ℝ) (d : Fin 3) :
    principal q p 0 d (entropyError c) = 0 := by
  funext j
  fin_cases d <;> fin_cases j <;> norm_num [principal,entropyError,Fin.ext_iff]

theorem split_entropy (q p a ratio sign c : ℝ) (d : Fin 3) :
    splitAction q p 0 a ratio sign d (entropyError c) = (ratio*a/2) • entropyError c := by
  simp only [splitAction,principal_entropy,smul_zero,add_zero,smul_smul]
  congr 1
  ring

theorem metric_entropy (q p c : ℝ) :
    metric q p (entropyError c) (entropyError c) = (c/q)^2 := by
  norm_num [metric,entropyError,show (1 : Fin 5) ≠ 0 by decide,
    show (2 : Fin 5) ≠ 0 by decide,show (3 : Fin 5) ≠ 0 by decide,
    show (4 : Fin 5) ≠ 0 by decide]
  ring

theorem witness_update (i : Fin 2) :
    variableUpdate witnessQ (fun _ => 1) (1/12) (fun _ _ => 0) (fun _ => 2)
      witnessShift witnessError i = entropyError (5/2) := by
  funext j
  fin_cases i <;> fin_cases j <;>
    norm_num [variableUpdate,witnessError,witnessShift,actions,split_entropy,
      entropyError,Fin.sum_univ_succ,Equiv.swap_apply_def]

-- With positive coefficients and CFL=1/2, the varying local metric need not
-- contract. This is an error-field witness, not an alternative flow family.
theorem varying_metric_energy_increase :
    (∀ i : Fin 2, 0 < witnessQ i ∧ Real.sqrt (2*witnessQ i) ≤ 2) ∧
    (1/12 : ℝ)*(2+2+2) ≤ 1 ∧
    (∑ i, metric (witnessQ i) 1 (witnessError i) (witnessError i)) = 5 ∧
    (∑ i, metric (witnessQ i) 1
      (variableUpdate witnessQ (fun _ => 1) (1/12) (fun _ _ => 0) (fun _ => 2)
        witnessShift witnessError i)
      (variableUpdate witnessQ (fun _ => 1) (1/12) (fun _ _ => 0) (fun _ => 2)
        witnessShift witnessError i)) = 125/16 ∧ (5 : ℝ) < 125/16 := by
  constructor
  · intro i
    fin_cases i <;> norm_num [witnessQ,Real.sqrt_le_iff]
  · simp only [witness_update]
    norm_num [Fin.sum_univ_succ,witnessQ,witnessError,metric_entropy]

end EulerVariableStability
