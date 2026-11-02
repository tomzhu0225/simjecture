-- Exact-real logarithmic mean, including its equal-argument branch.
noncomputable section
namespace EulerLogMean

def logMean (a b : ℝ) : ℝ := if a=b then a else (b-a)/(Real.log b-Real.log a)

theorem diagonal (a : ℝ) : logMean a a=a := by simp [logMean]

theorem log_difference_ne (a b : ℝ) (ha : 0 < a) (hb : 0 < b) (hab : a ≠ b) :
    Real.log b-Real.log a ≠ 0 := by
  intro h
  have he := Real.log_injOn_pos hb ha (sub_eq_zero.mp h)
  exact hab he.symm

theorem jump_identity (a b : ℝ) (ha : 0 < a) (hb : 0 < b) :
    logMean a b*(Real.log b-Real.log a)=b-a := by
  by_cases hab : a=b
  · subst b
    simp
  · rw [logMean,if_neg hab]
    exact div_mul_cancel₀ (b-a) (log_difference_ne a b ha hb hab)

theorem symmetric (a b : ℝ) (ha : 0 < a) (hb : 0 < b) : logMean a b=logMean b a := by
  by_cases hab : a=b
  · subst b
    rfl
  · rw [logMean,logMean,if_neg hab,if_neg (Ne.symm hab)]
    apply (div_eq_div_iff (log_difference_ne a b ha hb hab)
      (log_difference_ne b a hb ha (Ne.symm hab))).mpr
    ring

theorem ordered_mean_value (a b : ℝ) (ha : 0 < a) (hab : a < b) :
    ∃ c, a < c ∧ c < b ∧ logMean a b=c := by
  have hb : 0 < b := ha.trans hab
  have hd (t : ℝ) (ht : t ∈ Set.Icc a b) : HasDerivAt Real.log (1/t) t := by
    simpa only [one_div] using Real.hasDerivAt_log (ne_of_gt (lt_of_lt_of_le ha ht.1))
  obtain ⟨c,hc,he⟩ := exists_hasDerivAt_eq_slope Real.log (fun t => 1/t) hab
    (fun t ht => (hd t ht).continuousAt.continuousWithinAt)
    (fun t ht => hd t ⟨ht.1.le,ht.2.le⟩)
  refine ⟨c,hc.1,hc.2,?_⟩
  have hc0 : c ≠ 0 := ne_of_gt (ha.trans hc.1)
  have hba0 : b-a ≠ 0 := sub_ne_zero.mpr (ne_of_gt hab)
  have hx := (div_eq_div_iff hc0 hba0).mp he
  rw [logMean,if_neg (ne_of_lt hab)]
  apply (div_eq_iff (log_difference_ne a b ha hb (ne_of_lt hab))).mpr
  nlinarith

theorem between (a b : ℝ) (ha : 0 < a) (hb : 0 < b) :
    min a b ≤ logMean a b ∧ logMean a b ≤ max a b := by
  rcases lt_trichotomy a b with hab | hab | hab
  · obtain ⟨c,hca,hcb,he⟩ := ordered_mean_value a b ha hab
    rw [he,min_eq_left hab.le,max_eq_right hab.le]
    exact ⟨hca.le,hcb.le⟩
  · subst b
    simp [diagonal]
  · obtain ⟨c,hcb,hca,he⟩ := ordered_mean_value b a hb hab
    rw [symmetric a b ha hb,he,min_eq_right hab.le,max_eq_left hab.le]
    exact ⟨hcb.le,hca.le⟩

theorem positive (a b : ℝ) (ha : 0 < a) (hb : 0 < b) : 0 < logMean a b :=
  (lt_min ha hb).trans_le (between a b ha hb).1

end EulerLogMean
