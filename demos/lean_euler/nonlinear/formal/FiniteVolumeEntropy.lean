-- Algebra and quadratic estimates for the actual nonlinear Rusanov update.
-- Spatial entropy residuals and Hessian bounds are still required to obtain
-- a quantitative finite-step dissipation theorem.
noncomputable section
namespace EulerFiniteVolumeEntropy
open EulerEntropy EulerEnergyBounds EulerVectorEstimates
open scoped BigOperators

def gridFace {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (d : Fin 3) (i : I) : State :=
  EulerAdmissible.faceFlux (u i) (u (neighbor d i)) (a d) d

def gridIncrement {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (i : I) : State :=
  -(∑ d, (gridFace u neighbor a d i-gridFace u neighbor a d ((neighbor d).symm i)))

def gridUpdate {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (ratio : ℝ) (i : I) : State :=
  EulerAdmissible.update (u i) (fun d => u (neighbor d i))
    (fun d => u ((neighbor d).symm i)) ratio a

theorem update_increment {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (ratio : ℝ) (i : I) :
    gridUpdate u neighbor a ratio i=u i+ratio • gridIncrement u neighbor a i := by
  funext j
  simp [gridUpdate,EulerAdmissible.update,gridIncrement,gridFace,Fin.sum_univ_succ]
  ring

theorem periodic_pairing {I : Type*} [Fintype I] (neighbor : Equiv.Perm I) (g flux : I → State) :
    (∑ i, dot (g i) (flux i-flux (neighbor.symm i))) =
      -(∑ i, dot (g (neighbor i)-g i) (flux i)) := by
  have heq : (∑ i, dot (g i) (flux (neighbor.symm i))) =
      ∑ i, dot (g (neighbor i)) (flux i) := by
    have h := Equiv.sum_comp neighbor (fun i => dot (g i) (flux (neighbor.symm i)))
    simpa only [Equiv.symm_apply_apply] using h.symm
  simp only [dot_sub_right,dot_sub_left,Finset.sum_sub_distrib,heq]
  ring

theorem increment_pairing {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (g : I → State) :
    (∑ i, dot (g i) (gridIncrement u neighbor a i)) =
      ∑ d, ∑ i, dot (g (neighbor d i)-g i) (gridFace u neighbor a d i) := by
  simp only [gridIncrement,dot_neg_right,dot_sum_right,Finset.sum_neg_distrib]
  rw [Finset.sum_comm]
  simp only [periodic_pairing,Finset.sum_neg_distrib,neg_neg]

theorem update_pairing {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio : ℝ) (g : I → State) :
    (∑ i, dot (g i) (gridUpdate u neighbor a ratio i-u i)) =
      ratio*(∑ d, ∑ i, dot (g (neighbor d i)-g i) (gridFace u neighbor a d i)) := by
  simp only [update_increment,add_sub_cancel_left,dot_smul_right,← Finset.mul_sum,increment_pairing]

def edgeAction (u v : State) (a sign : ℝ) (d : Fin 3) : State :=
  a • (v-u)+sign • (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux u d)

theorem edge_action_bound (u v : State) (a sign A L : ℝ) (d : Fin 3)
    (ha : a^2 ≤ A^2) (hs : sign^2=1)
    (hF : sizeSquared (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux u d) ≤
      L^2*sizeSquared (v-u)) :
    sizeSquared (edgeAction u v a sign d) ≤ 2*(A^2+L^2)*sizeSquared (v-u) := by
  have hh := size_add_bound (a • (v-u))
    (sign • (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux u d))
  simp only [size_smul,hs,one_mul] at hh
  have hmult := mul_le_mul_of_nonneg_right ha (size_nonnegative (v-u))
  dsimp [edgeAction]
  nlinarith

def neighborState {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (i : I) : Fin 6 → State :=
  ![u (neighbor 0 i),u ((neighbor 0).symm i),u (neighbor 1 i),u ((neighbor 1).symm i),
    u (neighbor 2 i),u ((neighbor 2).symm i)]

def contributions {I : Type*} (u : I → State) (neighbor : Fin 3 → Equiv.Perm I)
    (a : Fin 3 → ℝ) (i : I) : Fin 6 → State :=
  ![edgeAction (u i) (u (neighbor 0 i)) (a 0) (-1) 0,
    edgeAction (u i) (u ((neighbor 0).symm i)) (a 0) 1 0,
    edgeAction (u i) (u (neighbor 1 i)) (a 1) (-1) 1,
    edgeAction (u i) (u ((neighbor 1).symm i)) (a 1) 1 1,
    edgeAction (u i) (u (neighbor 2 i)) (a 2) (-1) 2,
    edgeAction (u i) (u ((neighbor 2).symm i)) (a 2) 1 2]

theorem increment_six_neighbors {I : Type*} (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (i : I) :
    gridIncrement u neighbor a i=(1/2 : ℝ) • ∑ j, contributions u neighbor a i j := by
  funext k
  simp [gridIncrement,gridFace,contributions,edgeAction,EulerAdmissible.faceFlux,Fin.sum_univ_succ]
  ring

theorem point_increment_bound {I : Type*} (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (A L : ℝ)
    (ha : ∀ d, (a d)^2 ≤ A^2)
    (hF : ∀ i j d, sizeSquared (EulerAdmissible.eulerFlux (neighborState u neighbor i j) d-
      EulerAdmissible.eulerFlux (u i) d) ≤ L^2*sizeSquared (neighborState u neighbor i j-u i))
    (i : I) : sizeSquared (gridIncrement u neighbor a i) ≤
      3*(A^2+L^2)*(∑ j, sizeSquared (neighborState u neighbor i j-u i)) := by
  have hc (j : Fin 6) : sizeSquared (contributions u neighbor a i j) ≤
      2*(A^2+L^2)*sizeSquared (neighborState u neighbor i j-u i) := by
    fin_cases j
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 0) (by norm_num) (hF i 0 0)
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 0) (by norm_num) (hF i 1 0)
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 1) (by norm_num) (hF i 2 1)
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 1) (by norm_num) (hF i 3 1)
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 2) (by norm_num) (hF i 4 2)
    · exact edge_action_bound _ _ _ _ _ _ _ (ha 2) (by norm_num) (hF i 5 2)
  have hs := Finset.sum_le_sum (fun j (_ : j ∈ Finset.univ) => hc j)
  rw [← Finset.mul_sum] at hs
  have hb := size_sum_bound (contributions u neighbor a i)
  norm_num only [Fintype.card_fin,Nat.cast_ofNat] at hb
  rw [increment_six_neighbors,size_smul]
  nlinarith

def edgeEnergy {I : Type*} [Fintype I] (u : I → State) (neighbor : Fin 3 → Equiv.Perm I) : ℝ :=
  ∑ d, ∑ i, sizeSquared (u (neighbor d i)-u i)

theorem neighbor_energy_sum {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) :
    (∑ i, ∑ j, sizeSquared (neighborState u neighbor i j-u i)) = 2*edgeEnergy u neighbor := by
  have heq (d : Fin 3) : (∑ i, sizeSquared (u ((neighbor d).symm i)-u i)) =
      ∑ i, sizeSquared (u (neighbor d i)-u i) := by
    have hh := Equiv.sum_comp (neighbor d) (fun i => sizeSquared (u ((neighbor d).symm i)-u i))
    simpa only [Equiv.symm_apply_apply,size_sub_comm] using hh.symm
  simp [neighborState,Fin.sum_univ_succ,Finset.sum_add_distrib,heq,edgeEnergy]
  ring

theorem total_increment_bound {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (A L : ℝ)
    (ha : ∀ d, (a d)^2 ≤ A^2)
    (hF : ∀ i j d, sizeSquared (EulerAdmissible.eulerFlux (neighborState u neighbor i j) d-
      EulerAdmissible.eulerFlux (u i) d) ≤ L^2*sizeSquared (neighborState u neighbor i j-u i)) :
    (∑ i, sizeSquared (gridIncrement u neighbor a i)) ≤
      6*(A^2+L^2)*edgeEnergy u neighbor := by
  calc
    _ ≤ ∑ i, 3*(A^2+L^2)*(∑ j, sizeSquared (neighborState u neighbor i j-u i)) :=
      Finset.sum_le_sum (fun i _ => point_increment_bound u neighbor a A L ha hF i)
    _ = _ := by rw [← Finset.mul_sum,neighbor_energy_sum]; ring

theorem edge_energy_nonnegative {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) : 0 ≤ edgeEnergy u neighbor :=
  Finset.sum_nonneg (fun _ _ => Finset.sum_nonneg (fun _ _ => size_nonnegative _))

theorem face_entropy_sum_bound {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (C : ℝ)
    (hface : ∀ d i, dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)-
      (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩) ≤
        -C*sizeSquared (u (neighbor d i)-u i)) :
    (∑ d, ∑ i, dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)) ≤
      -C*edgeEnergy u neighbor := by
  have hp (d : Fin 3) : (∑ i, (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩))=0 := by
    rw [Finset.sum_sub_distrib]
    have hh := Equiv.sum_comp (neighbor d) (fun i => u i ⟨d.val+1,by omega⟩)
    rw [hh,sub_self]
  have hd (d : Fin 3) :
      (∑ i, dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)) ≤
        -C*(∑ i, sizeSquared (u (neighbor d i)-u i)) := by
    calc
      _ ≤ ∑ i, ((u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩)-
          C*sizeSquared (u (neighbor d i)-u i)) :=
        Finset.sum_le_sum (fun i _ => by linarith [hface d i])
      _ = _ := by rw [Finset.sum_sub_distrib,hp,← Finset.mul_sum]; ring
  calc
    _ ≤ ∑ d, -C*(∑ i, sizeSquared (u (neighbor d i)-u i)) := Finset.sum_le_sum (fun d _ => hd d)
    _ = _ := by rw [← Finset.mul_sum]; rfl

theorem entropy_step_bound {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio A L M C : ℝ)
    (hr : 0 ≤ ratio) (hM : 0 ≤ M)
    (hu : ∀ i, EulerAdmissible.Admissible (u i))
    (hv : ∀ i, EulerAdmissible.Admissible (gridUpdate u neighbor a ratio i))
    (ha : ∀ d, (a d)^2 ≤ A^2)
    (hF : ∀ i j d, sizeSquared (EulerAdmissible.eulerFlux (neighborState u neighbor i j) d-
      EulerAdmissible.eulerFlux (u i) d) ≤ L^2*sizeSquared (neighborState u neighbor i j-u i))
    (hH : ∀ i t, t ∈ Set.Icc (0 : ℝ) 1 →
      EulerEntropyTaylor.conservativeHessian
        (EulerEntropyConvexity.segment (u i) (gridUpdate u neighbor a ratio i) t)
        (gridUpdate u neighbor a ratio i-u i) ≤ M*sizeSquared (gridUpdate u neighbor a ratio i-u i))
    (hface : ∀ d i, dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)-
      (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩) ≤
        -C*sizeSquared (u (neighbor d i)-u i)) :
    (∑ i, entropy (gridUpdate u neighbor a ratio i)) ≤ (∑ i, entropy (u i))-
      ratio*C*edgeEnergy u neighbor+3*M*ratio^2*(A^2+L^2)*edgeEnergy u neighbor := by
  have hlinear : (∑ i, dot (gradient (u i)) (gridUpdate u neighbor a ratio i-u i)) ≤
      -ratio*C*edgeEnergy u neighbor := by
    rw [update_pairing]
    have hh := mul_le_mul_of_nonneg_left (face_entropy_sum_bound u neighbor a C hface) hr
    convert hh using 1
    ring
  have hquad : (∑ i, sizeSquared (gridUpdate u neighbor a ratio i-u i)) ≤
      ratio^2*(6*(A^2+L^2)*edgeEnergy u neighbor) := by
    simp only [update_increment,add_sub_cancel_left,size_smul,← Finset.mul_sum]
    exact mul_le_mul_of_nonneg_left (total_increment_bound u neighbor a A L ha hF) (sq_nonneg ratio)
  have ht (i : I) := EulerEntropyTaylor.entropy_taylor_upper (u i) (gridUpdate u neighbor a ratio i)
    (hu i) (hv i) M (hH i)
  have hs := Finset.sum_le_sum (fun i (_ : i ∈ Finset.univ) => ht i)
  simp only [Finset.sum_add_distrib,← Finset.mul_sum] at hs
  have hquadratic := mul_le_mul_of_nonneg_left hquad (by positivity : 0 ≤ M/2)
  nlinarith

theorem entropy_step_dissipation {I : Type*} [Fintype I] (u : I → State)
    (neighbor : Fin 3 → Equiv.Perm I) (a : Fin 3 → ℝ) (ratio A L M C : ℝ)
    (hr : 0 ≤ ratio) (hM : 0 ≤ M)
    (hu : ∀ i, EulerAdmissible.Admissible (u i))
    (hv : ∀ i, EulerAdmissible.Admissible (gridUpdate u neighbor a ratio i))
    (ha : ∀ d, (a d)^2 ≤ A^2)
    (hF : ∀ i j d, sizeSquared (EulerAdmissible.eulerFlux (neighborState u neighbor i j) d-
      EulerAdmissible.eulerFlux (u i) d) ≤ L^2*sizeSquared (neighborState u neighbor i j-u i))
    (hH : ∀ i t, t ∈ Set.Icc (0 : ℝ) 1 →
      EulerEntropyTaylor.conservativeHessian
        (EulerEntropyConvexity.segment (u i) (gridUpdate u neighbor a ratio i) t)
        (gridUpdate u neighbor a ratio i-u i) ≤ M*sizeSquared (gridUpdate u neighbor a ratio i-u i))
    (hface : ∀ d i, dot (gradient (u (neighbor d i))-gradient (u i)) (gridFace u neighbor a d i)-
      (u (neighbor d i) ⟨d.val+1,by omega⟩-u i ⟨d.val+1,by omega⟩) ≤
        -C*sizeSquared (u (neighbor d i)-u i))
    (hstep : 3*M*ratio*(A^2+L^2) ≤ C/2) :
    (∑ i, entropy (gridUpdate u neighbor a ratio i)) ≤ (∑ i, entropy (u i))-
      (ratio*C/2)*edgeEnergy u neighbor := by
  have hb := entropy_step_bound u neighbor a ratio A L M C hr hM hu hv ha hF hH hface
  have hs := mul_le_mul_of_nonneg_right hstep (mul_nonneg hr (edge_energy_nonnegative u neighbor))
  nlinarith

end EulerFiniteVolumeEntropy
