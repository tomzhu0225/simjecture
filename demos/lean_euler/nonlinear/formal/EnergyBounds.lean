-- Assemble after PrimitiveEnergy.lean. These are explicit uniform norm bounds
-- on a declared positive state box, not a proof that the solution stays there.
noncomputable section
namespace EulerEnergyBounds
open EulerPrimitiveEnergy

def sizeSquared (h : State) : ℝ := h 0^2+h 1^2+h 2^2+h 3^2+h 4^2

theorem metric_components (q p : ℝ) (hq : 0 < q) (hp : 0 < p) (h : State) :
    h 4^2/(2*p) ≤ metric q p h h ∧
    (h 1^2+h 2^2+h 3^2)/q ≤ metric q p h h ∧
    (h 0/q+h 4/(2*p))^2 ≤ metric q p h h := by
  have hA : 0 ≤ h 4^2/(2*p) := by positivity
  have hB : 0 ≤ (h 1^2+h 2^2+h 3^2)/q := by positivity
  have hC := sq_nonneg (h 0/q+h 4/(2*p))
  rw [metric_squares]
  exact ⟨by linarith,by linarith,by linarith⟩

theorem pressure_coercivity (q p : ℝ) (hq : 0 < q) (hp : 0 < p) (h : State) :
    h 4^2 ≤ 2*p*metric q p h h := by
  have h := (div_le_iff₀ (by positivity : 0 < 2*p)).mp (metric_components q p hq hp h).1
  nlinarith

theorem velocity_coercivity (q p : ℝ) (hq : 0 < q) (hp : 0 < p) (h : State) :
    h 1^2+h 2^2+h 3^2 ≤ q*metric q p h h := by
  have h := (div_le_iff₀ hq).mp (metric_components q p hq hp h).2.1
  nlinarith

theorem box_coercivity (q p : ℝ) (hq0 : 1/4 ≤ q) (hq1 : q ≤ 4)
    (hp0 : 1/4 ≤ p) (hp1 : p ≤ 4) (h : State) :
    sizeSquared h ≤ 108*metric q p h h := by
  have hq : 0 < q := by linarith
  have hp : 0 < p := by linarith
  have he := metric_nonnegative q p hq hp h
  obtain ⟨ha,hb,hc⟩ := metric_components q p hq hp h
  have hpressure : h 4^2 ≤ 8*metric q p h h := by
    have hh := pressure_coercivity q p hq hp h
    have hh2 := mul_le_mul_of_nonneg_right hp1 he
    nlinarith
  have hvel : h 1^2+h 2^2+h 3^2 ≤ 4*metric q p h h := by
    exact (velocity_coercivity q p hq hp h).trans (mul_le_mul_of_nonneg_right hq1 he)
  have hsmallpressure : (h 4/(2*p))^2 ≤ 2*metric q p h h := by
    calc
      _ = (h 4^2/(2*p))/(2*p) := by ring
      _ ≤ metric q p h h/(2*p) := div_le_div_of_nonneg_right ha (by positivity)
      _ ≤ 2*metric q p h h := by
        apply (div_le_iff₀ (by positivity : 0 < 2*p)).mpr
        nlinarith
  have hscaled : (h 0/q)^2 ≤ 6*metric q p h h := by
    nlinarith [sq_nonneg ((h 0/q+h 4/(2*p))+(h 4/(2*p)))]
  have hq2 : q^2 ≤ 16 := by nlinarith
  have h0 : h 0^2 ≤ 96*metric q p h h := by
    calc
      _ = q^2*(h 0/q)^2 := by field_simp
      _ ≤ q^2*(6*metric q p h h) := mul_le_mul_of_nonneg_left hscaled (sq_nonneg q)
      _ ≤ 16*(6*metric q p h h) := mul_le_mul_of_nonneg_right hq2 (by positivity)
      _ = 96*metric q p h h := by ring
  dsimp [sizeSquared]
  linarith

theorem box_upper_bound (q p : ℝ) (hq0 : 1/4 ≤ q) (hp0 : 1/4 ≤ p) (h : State) :
    metric q p h h ≤ 32*sizeSquared h := by
  have hq : 0 < q := by linarith
  have hp : 0 < p := by linarith
  have hqi : 1/q ≤ 4 := (div_le_iff₀ hq).mpr (by linarith)
  have hpi : 1/(2*p) ≤ 2 := (div_le_iff₀ (by positivity : 0 < 2*p)).mpr (by linarith)
  have hqin : 0 ≤ 1/q := by positivity
  have hpin : 0 ≤ 1/(2*p) := by positivity
  have hqisq : (1/q)^2 ≤ 16 := by nlinarith
  have hpisq : (1/(2*p))^2 ≤ 4 := by nlinarith
  have hqterm : (h 0/q)^2 ≤ 16*(h 0)^2 := by
    calc
      _ = (1/q)^2*(h 0)^2 := by ring
      _ ≤ 16*(h 0)^2 := mul_le_mul_of_nonneg_right hqisq (sq_nonneg _)
  have hpterm : (h 4/(2*p))^2 ≤ 4*(h 4)^2 := by
    calc
      _ = (1/(2*p))^2*(h 4)^2 := by ring
      _ ≤ 4*(h 4)^2 := mul_le_mul_of_nonneg_right hpisq (sq_nonneg _)
  have ha : h 4^2/(2*p) ≤ 2*(h 4)^2 := by
    simpa [div_eq_mul_inv,mul_comm] using
      mul_le_mul_of_nonneg_right hpi (sq_nonneg (h 4))
  have hb : (h 1^2+h 2^2+h 3^2)/q ≤ 4*(h 1^2+h 2^2+h 3^2) := by
    simpa [div_eq_mul_inv,mul_comm] using
      mul_le_mul_of_nonneg_right hqi (by positivity : 0 ≤ h 1^2+h 2^2+h 3^2)
  rw [metric_squares]
  dsimp [sizeSquared]
  nlinarith [sq_nonneg (h 0/q-h 4/(2*p)),sq_nonneg (h 1),sq_nonneg (h 2),sq_nonneg (h 3),sq_nonneg (h 4)]
end EulerEnergyBounds
