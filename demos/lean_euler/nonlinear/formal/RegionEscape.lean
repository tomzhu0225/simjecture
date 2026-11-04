-- Negative control for a proposed global region-invariance shortcut. These
-- compression states are not the Taylor-Green research family.
noncomputable section
namespace EulerRegionEscape
open EulerEntropyConservativeFlux EulerEntropyCandidateStep EulerPhysicalRegion
abbrev State := Fin 5 → ℝ
abbrev Cell := Fin 3 × (Fin 3 × Fin 3)

def cycle : Equiv.Perm (Fin 3) where
  toFun := ![1,2,0]
  invFun := ![2,0,1]
  left_inv := by intro i; fin_cases i <;> rfl
  right_inv := by intro i; fin_cases i <;> rfl

def neighbor : Fin 3 → Equiv.Perm Cell :=
  ![Equiv.prodCongr cycle (Equiv.refl _),
    Equiv.prodCongr (Equiv.refl _) (Equiv.prodCongr cycle (Equiv.refl _)),
    Equiv.prodCongr (Equiv.refl _) (Equiv.prodCongr (Equiv.refl _) cycle)]

def compression (s : ℝ) : State := ![1,s,0,0,4]
def states (i : Cell) : State := compression ((![1,0,-1] : Fin 3 → ℝ) i.1)
def center : Cell := (1,(0,0))

theorem initial_in_region : ∀ i, states i ∈ region := by
  rintro ⟨i,j⟩
  fin_cases i <;> norm_num [states,compression,region,EulerAdmissible.pressure,
    Matrix.cons_val_two,Matrix.cons_val_three,Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail]

theorem initial_admissible : ∀ i, EulerAdmissible.Admissible (states i) :=
  fun i => region_admissible (states i) (initial_in_region i)

theorem compression_beta (s : ℝ) : beta (compression s)=1/(8-s^2) := by
  have hp : EulerAdmissible.pressure (compression s)=4-s^2/2 := by
    norm_num [compression,EulerAdmissible.pressure,
      Matrix.cons_val_two,Matrix.cons_val_three,Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail]
  change 1/(2*EulerAdmissible.pressure (compression s))=1/(8-s^2)
  rw [hp]
  congr 1
  ring

theorem compression_velocity (s : ℝ) : EulerAdmissible.fromVelocity (compression s)=![s,0,0] := by
  norm_num [compression,EulerAdmissible.fromVelocity,
    Matrix.cons_val_two,Matrix.cons_val_three,Matrix.vecHead,Matrix.vecTail]

theorem compression_face_energy (s t a : ℝ) :
    esFlux (compression s) (compression t) a 0 4 = ((s+t)/2)*
      (1/(2*EulerLogMean.logMean (1/(8-s^2)) (1/(8-t^2)))+
        1/(1/(8-s^2)+1/(8-t^2))+s*t/2) := by
  change ecFlux (compression s) (compression t) 0 4-a/2*(4-4)=_
  rw [sub_self,mul_zero,sub_zero]
  dsimp only [ecFlux]
  rw [compression_beta,compression_beta,compression_velocity,compression_velocity]
  norm_num [compression,parameterFlux,fluxWithMeans,average,speedSquared,EulerLogMean.diagonal,
    Matrix.cons_val_two,Matrix.cons_val_three,Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail,Fin.ext_iff]
  ring

theorem center_energy_increment (a : Fin 3 → ℝ) :
    increment states neighbor a center 4=1/(2*EulerLogMean.logMean (1/7) (1/8))+56/15 := by
  norm_num [increment,face,neighbor,cycle,center,states,Fin.sum_univ_succ,Equiv.prodCongr,
    Matrix.cons_val_two,Matrix.cons_val_three,Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail,Fin.ext_iff]
  rw [compression_face_energy,compression_face_energy]
  norm_num
  rw [EulerLogMean.symmetric (1/8) (1/7) (by norm_num) (by norm_num)]
  ring

theorem positive_step_leaves_region (a : Fin 3 → ℝ) (r : ℝ) (hr : 0 < r) :
    trial states neighbor a r center ∉ region := by
  have hl : 0 < EulerLogMean.logMean (1/7) (1/8) :=
    EulerLogMean.positive _ _ (by norm_num) (by norm_num)
  have hi : 0 < increment states neighbor a center 4 := by
    rw [center_energy_increment]
    positivity
  intro hnew
  have hE := hnew.2.2.1
  change 4+r*increment states neighbor a center 4 ≤ 4 at hE
  nlinarith [mul_pos hr hi]

theorem accepted_step_leaves_region (a : Fin 3 → ℝ) (ha : ∀ d, 0 < a d)
    (proposal : ℝ) (hproposal : 0 < proposal) :
    trial states neighbor a
      (acceptedRatio states neighbor a proposal initial_admissible ha hproposal) center ∉ region := by
  have hh := backtracked_step states neighbor a proposal initial_admissible ha hproposal
  exact positive_step_leaves_region a _ hh.1

end EulerRegionEscape
