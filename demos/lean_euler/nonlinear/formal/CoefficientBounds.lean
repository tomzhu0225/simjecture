-- Assemble after EnergyBounds.lean. Quantitative coefficient bounds on an
-- explicit positive state region; remaining in that region is a separate task.
noncomputable section
namespace EulerCoefficientBounds
open EulerPrimitiveEnergy EulerEnergyBounds

theorem reciprocal_bounds (x : ℝ) (hx : 1/4 ≤ x) : 0 ≤ 1/x ∧ 1/x ≤ 4 := by
  have hp : 0 < x := by linarith
  exact ⟨by positivity,(div_le_iff₀ hp).mpr (by linarith)⟩

theorem reciprocal_variation (x y : ℝ) (hx : 1/4 ≤ x) (hy : 1/4 ≤ y) :
    |1/x-1/y| ≤ 16*|x-y| := by
  have hxp : 0 < x := by linarith
  have hyp : 0 < y := by linarith
  have heq : 1/x-1/y = (y-x)/(x*y) := by field_simp
  have hprod : 1/16 ≤ x*y := by
    calc
      _ = (1/4 : ℝ)*(1/4) := by norm_num
      _ ≤ x*y := mul_le_mul hx hy (by norm_num) hxp.le
  rw [heq,abs_div,abs_of_pos (mul_pos hxp hyp),abs_sub_comm]
  apply (div_le_iff₀ (mul_pos hxp hyp)).mpr
  nlinarith [mul_le_mul_of_nonneg_right hprod (abs_nonneg (x-y))]

theorem metric_coefficients (q p : ℝ) (x : State) :
    metric q p x x = (1/(2*p)+(1/(2*p))^2)*x 4^2+
      (1/q)*(x 1^2+x 2^2+x 3^2)+(1/q)^2*x 0^2+
      ((1/q)*(1/(2*p)))*(2*x 0*x 4) := by
  dsimp [metric]
  ring

theorem quadratic_coefficient_bound (A B C D : ℝ) (x : State) :
    |A*x 4^2+B*(x 1^2+x 2^2+x 3^2)+C*x 0^2+D*(2*x 0*x 4)| ≤
      (|A|+|B|+|C|+|D|)*sizeSquared x := by
  have hv : 0 ≤ x 1^2+x 2^2+x 3^2 := by positivity
  have h0 : x 0^2 ≤ sizeSquared x := by
    dsimp [sizeSquared]; nlinarith [sq_nonneg (x 1),sq_nonneg (x 2),sq_nonneg (x 3),sq_nonneg (x 4)]
  have h4 : x 4^2 ≤ sizeSquared x := by
    dsimp [sizeSquared]; nlinarith [sq_nonneg (x 0),sq_nonneg (x 1),sq_nonneg (x 2),sq_nonneg (x 3)]
  have hvb : x 1^2+x 2^2+x 3^2 ≤ sizeSquared x := by
    dsimp [sizeSquared]; nlinarith [sq_nonneg (x 0),sq_nonneg (x 4)]
  have hc : |2*x 0*x 4| ≤ sizeSquared x := by
    apply abs_le.mpr
    dsimp [sizeSquared]
    constructor <;> nlinarith [sq_nonneg (x 0-x 4),sq_nonneg (x 0+x 4),
      sq_nonneg (x 1),sq_nonneg (x 2),sq_nonneg (x 3)]
  calc
    _ ≤ |A*x 4^2+B*(x 1^2+x 2^2+x 3^2)+C*x 0^2|+|D*(2*x 0*x 4)| := abs_add_le _ _
    _ ≤ (|A*x 4^2+B*(x 1^2+x 2^2+x 3^2)|+|C*x 0^2|)+|D*(2*x 0*x 4)| :=
      add_le_add_right (abs_add_le _ _) _
    _ ≤ ((|A*x 4^2|+|B*(x 1^2+x 2^2+x 3^2)|)+|C*x 0^2|)+|D*(2*x 0*x 4)| :=
      add_le_add_right (add_le_add_right (abs_add_le _ _) _) _
    _ = |A| *x 4^2+|B| *(x 1^2+x 2^2+x 3^2)+|C| *x 0^2+|D| *|2*x 0*x 4| := by
      rw [abs_mul,abs_mul,abs_mul,abs_mul,abs_sq,abs_sq,abs_of_nonneg hv]
    _ ≤ |A| *sizeSquared x+|B| *sizeSquared x+|C| *sizeSquared x+|D| *sizeSquared x :=
      add_le_add (add_le_add (add_le_add
        (mul_le_mul_of_nonneg_left h4 (abs_nonneg _))
        (mul_le_mul_of_nonneg_left hvb (abs_nonneg _)))
        (mul_le_mul_of_nonneg_left h0 (abs_nonneg _)))
        (mul_le_mul_of_nonneg_left hc (abs_nonneg _))
    _ = _ := by ring

theorem reciprocal_coefficient_variation (r s r' s' R S : ℝ)
    (hr : 0 ≤ r) (hr' : 0 ≤ r') (hr4 : r ≤ 4) (hr4' : r' ≤ 4)
    (hs : 0 ≤ s) (hs' : 0 ≤ s') (hs2 : s ≤ 2) (hs2' : s' ≤ 2)
    (hR : |r'-r| ≤ R) (hS : |s'-s| ≤ S) :
    |(s'+s'^2)-(s+s^2)|+|r'-r|+|r'^2-r^2|+|r'*s'-r*s| ≤ 11*R+9*S := by
  have hRn : 0 ≤ R := (abs_nonneg _).trans hR
  have hSn : 0 ≤ S := (abs_nonneg _).trans hS
  have hsquares : |s'^2-s^2| ≤ 4*S := by
    calc
      _ = |s'-s| *(s'+s) := by rw [sq_sub_sq,abs_mul,abs_of_nonneg (add_nonneg hs' hs),mul_comm]
      _ ≤ S*(s'+s) := mul_le_mul_of_nonneg_right hS (add_nonneg hs' hs)
      _ ≤ S*4 := mul_le_mul_of_nonneg_left (by linarith) hSn
      _ = _ := by ring
  have hfirst : |(s'+s'^2)-(s+s^2)| ≤ 5*S := by
    calc
      _ = |(s'-s)+(s'^2-s^2)| := by congr 1; ring
      _ ≤ |s'-s|+|s'^2-s^2| := abs_add_le _ _
      _ ≤ S+4*S := add_le_add hS hsquares
      _ = _ := by ring
  have hrsquares : |r'^2-r^2| ≤ 8*R := by
    calc
      _ = |r'-r| *(r'+r) := by rw [sq_sub_sq,abs_mul,abs_of_nonneg (add_nonneg hr' hr),mul_comm]
      _ ≤ R*(r'+r) := mul_le_mul_of_nonneg_right hR (add_nonneg hr' hr)
      _ ≤ R*8 := mul_le_mul_of_nonneg_left (by linarith) hRn
      _ = _ := by ring
  have hcross : |r'*s'-r*s| ≤ 2*R+4*S := by
    calc
      _ = |(r'-r)*s'+r*(s'-s)| := by congr 1; ring
      _ ≤ |(r'-r)*s'|+|r*(s'-s)| := abs_add_le _ _
      _ = |r'-r| *s'+r*|s'-s| := by rw [abs_mul,abs_mul,abs_of_nonneg hs',abs_of_nonneg hr]
      _ ≤ R*s'+r*S := add_le_add (mul_le_mul_of_nonneg_right hR hs')
        (mul_le_mul_of_nonneg_left hS hr)
      _ ≤ R*2+4*S := add_le_add (mul_le_mul_of_nonneg_left hs2' hRn)
        (mul_le_mul_of_nonneg_right hr4 hSn)
      _ = _ := by ring
  linarith

theorem metric_variation (q p q' p' : ℝ)
    (hq : 1/4 ≤ q) (hp : 1/4 ≤ p) (hq' : 1/4 ≤ q') (hp' : 1/4 ≤ p')
    (x : State) : |metric q' p' x x-metric q p x x| ≤
      256*(|q'-q|+|p'-p|)*sizeSquared x := by
  obtain ⟨hr,hr4⟩ := reciprocal_bounds q hq
  obtain ⟨hr',hr4'⟩ := reciprocal_bounds q' hq'
  obtain ⟨ht,ht4⟩ := reciprocal_bounds p hp
  obtain ⟨ht',ht4'⟩ := reciprocal_bounds p' hp'
  have hs : 0 ≤ 1/(2*p) := by positivity
  have hs' : 0 ≤ 1/(2*p') := by positivity
  have hs2 : 1/(2*p) ≤ 2 := by
    have he : 1/(2*p) = (1/p)/2 := by ring
    linarith
  have hs2' : 1/(2*p') ≤ 2 := by
    have he : 1/(2*p') = (1/p')/2 := by ring
    linarith
  have hR := reciprocal_variation q' q hq' hq
  have hS : |1/(2*p')-1/(2*p)| ≤ 8*|p'-p| := by
    have h := reciprocal_variation p' p hp' hp
    have he : 1/(2*p')-1/(2*p) = (1/p'-1/p)/2 := by ring
    rw [he,abs_div,abs_of_pos (by norm_num : (0 : ℝ)<2)]
    linarith
  have hcoeff := reciprocal_coefficient_variation (1/q) (1/(2*p)) (1/q') (1/(2*p'))
    (16*|q'-q|) (8*|p'-p|) hr hr' hr4 hr4' hs hs' hs2 hs2' hR hS
  have hbound := quadratic_coefficient_bound
    ((1/(2*p')+(1/(2*p'))^2)-(1/(2*p)+(1/(2*p))^2))
    (1/q'-1/q) ((1/q')^2-(1/q)^2) ((1/q')*(1/(2*p'))-(1/q)*(1/(2*p))) x
  have he : metric q' p' x x-metric q p x x =
      ((1/(2*p')+(1/(2*p'))^2)-(1/(2*p)+(1/(2*p))^2))*x 4^2+
      (1/q'-1/q)*(x 1^2+x 2^2+x 3^2)+((1/q')^2-(1/q)^2)*x 0^2+
      ((1/q')*(1/(2*p'))-(1/q)*(1/(2*p)))*(2*x 0*x 4) := by
    rw [metric_coefficients,metric_coefficients]; ring
  rw [he]
  have hsn : 0 ≤ sizeSquared x := by dsimp [sizeSquared]; positivity
  refine hbound.trans (mul_le_mul_of_nonneg_right ?_ hsn)
  nlinarith [abs_nonneg (q'-q),abs_nonneg (p'-p)]

theorem relative_metric_variation (q p q' p' : ℝ)
    (hq : 1/4 ≤ q) (hp : 1/4 ≤ p) (hq4 : q ≤ 4) (hp4 : p ≤ 4)
    (hq' : 1/4 ≤ q') (hp' : 1/4 ≤ p') (x : State) :
    |metric q' p' x x-metric q p x x| ≤
      27648*(|q'-q|+|p'-p|)*metric q p x x := by
  calc
    _ ≤ 256*(|q'-q|+|p'-p|)*sizeSquared x := metric_variation q p q' p' hq hp hq' hp' x
    _ ≤ 256*(|q'-q|+|p'-p|)*(108*metric q p x x) :=
      mul_le_mul_of_nonneg_left (box_coercivity q p hq hq4 hp hp4 x) (by positivity)
    _ = _ := by ring

theorem weighted_metric_variation (q p q' p' v v' B : ℝ)
    (hq : 1/4 ≤ q) (hp : 1/4 ≤ p) (hq' : 1/4 ≤ q') (hp' : 1/4 ≤ p')
    (hB : |v'| ≤ B) (x : State) :
    |v'*metric q' p' x x-v*metric q p x x| ≤
      (256*B*(|q'-q|+|p'-p|)+32*|v'-v|)*sizeSquared x := by
  have hg := metric_nonnegative q p (by linarith) (by linarith) x
  have hgn := box_upper_bound q p hq hp x
  have hsn : 0 ≤ sizeSquared x := by dsimp [sizeSquared]; positivity
  calc
    _ = |v'*(metric q' p' x x-metric q p x x)+(v'-v)*metric q p x x| := by congr 1; ring
    _ ≤ |v'*(metric q' p' x x-metric q p x x)|+|(v'-v)*metric q p x x| := abs_add_le _ _
    _ = |v'| *|metric q' p' x x-metric q p x x|+|v'-v| *metric q p x x := by
      rw [abs_mul,abs_mul,abs_of_nonneg hg]
    _ ≤ B*(256*(|q'-q|+|p'-p|)*sizeSquared x)+|v'-v| *(32*sizeSquared x) :=
      add_le_add (mul_le_mul hB (metric_variation q p q' p' hq hp hq' hp' x)
        (abs_nonneg _) ((abs_nonneg _).trans hB))
        (mul_le_mul_of_nonneg_left hgn (abs_nonneg _))
    _ = _ := by ring

end EulerCoefficientBounds
