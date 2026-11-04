-- A concrete convex physical-state region. Membership of a whole evolved
-- trajectory is not asserted by these pointwise geometric bounds.
noncomputable section
namespace EulerPhysicalRegion
open EulerEntropy EulerEntropyTaylor EulerEnergyBounds EulerVectorEstimates
abbrev State := Fin 5 → ℝ

def region : Set State := {u | 1/4 ≤ u 0 ∧ u 0 ≤ 4 ∧ u 4 ≤ 4 ∧ 1/4 ≤ EulerAdmissible.pressure u}

theorem region_admissible (u : State) (hu : u ∈ region) : EulerAdmissible.Admissible u := by
  exact ⟨by linarith [hu.1],by linarith [hu.2.2.2]⟩

theorem pressure_le_support (u : State) (hr : 0 < u 0) (v : EulerAdmissible.Vec) :
    EulerAdmissible.pressure u ≤ EulerAdmissible.supportEnergy u v := by
  rw [EulerAdmissible.complete_square u v hr]
  have hh : 0 ≤ u 0/2*((u 1/u 0-v 0)^2+(u 2/u 0-v 1)^2+(u 3/u 0-v 2)^2) := by positivity
  linarith

theorem pressure_concave_pair (u v : State) (hr : 0 < u 0) (hs : 0 < v 0)
    (a b : ℝ) (ha : 0 ≤ a) (hb : 0 ≤ b) (hab : a+b=1) :
    a*EulerAdmissible.pressure u+b*EulerAdmissible.pressure v ≤
      EulerAdmissible.pressure (a • u+b • v) := by
  let w := a • u+b • v
  have hw : 0 < w 0 := by
    have hh := EulerAdmissible.positive_convex_pair (u 0) (v 0) a hr hs ha (by linarith)
    have he : 1-a=b := by linarith
    simpa only [he] using hh
  let z := EulerAdmissible.fromVelocity w
  have he : a*EulerAdmissible.supportEnergy u z+b*EulerAdmissible.supportEnergy v z =
      EulerAdmissible.supportEnergy w z := by dsimp [EulerAdmissible.supportEnergy,w]; ring
  calc
    _ ≤ a*EulerAdmissible.supportEnergy u z+b*EulerAdmissible.supportEnergy v z :=
      add_le_add (mul_le_mul_of_nonneg_left (pressure_le_support u hr z) ha)
        (mul_le_mul_of_nonneg_left (pressure_le_support v hs z) hb)
    _ = _ := he.trans (EulerAdmissible.supportEnergy_at_velocity w hw)

theorem region_convex : Convex ℝ region := by
  intro u hu v hv a b ha hb hab
  have hr := region_admissible u hu
  have hs := region_admissible v hv
  refine ⟨?_,?_,?_,?_⟩
  · change 1/4 ≤ a*u 0+b*v 0
    nlinarith [mul_le_mul_of_nonneg_left hu.1 ha,mul_le_mul_of_nonneg_left hv.1 hb]
  · change a*u 0+b*v 0 ≤ 4
    nlinarith [mul_le_mul_of_nonneg_left hu.2.1 ha,mul_le_mul_of_nonneg_left hv.2.1 hb]
  · change a*u 4+b*v 4 ≤ 4
    nlinarith [mul_le_mul_of_nonneg_left hu.2.2.1 ha,mul_le_mul_of_nonneg_left hv.2.2.1 hb]
  · have hh := pressure_concave_pair u v hr.1 hs.1 a b ha hb hab
    have h1 := mul_le_mul_of_nonneg_left hu.2.2.2 ha
    have h2 := mul_le_mul_of_nonneg_left hv.2.2.2 hb
    linarith

theorem pressure_upper (u : State) (hu : u ∈ region) : EulerAdmissible.pressure u ≤ 4 := by
  have hr := (region_admissible u hu).1
  have hn : 0 ≤ (u 1^2+u 2^2+u 3^2)/(2*u 0) := by positivity
  dsimp [EulerAdmissible.pressure]
  linarith [hu.2.2.1]

def velocitySquared (u : State) : ℝ := (u 1/u 0)^2+(u 2/u 0)^2+(u 3/u 0)^2
def shiftedMomentumSquared (u k : State) : ℝ :=
  (k 1-(u 1/u 0)*k 0)^2+(k 2-(u 2/u 0)*k 0)^2+(k 3-(u 3/u 0)*k 0)^2
def thermalShift (u k : State) : ℝ := pressureD u k/EulerAdmissible.pressure u-k 0/u 0

theorem kinetic_pressure_identity (u : State) (hr : u 0 ≠ 0) :
    u 0*velocitySquared u = 2*(u 4-EulerAdmissible.pressure u) := by
  dsimp [velocitySquared,EulerAdmissible.pressure]
  field_simp
  ring

theorem velocity_squared_bound (u : State) (hu : u ∈ region) : velocitySquared u ≤ 30 := by
  have hr := (region_admissible u hu).1
  have hn : 0 ≤ velocitySquared u := by dsimp [velocitySquared]; positivity
  have he := kinetic_pressure_identity u (ne_of_gt hr)
  have hm := mul_le_mul_of_nonneg_right hu.1 hn
  nlinarith [hu.2.2.1,hu.2.2.2]

theorem conservative_hessian_squares (u k : State) (hu : EulerAdmissible.Admissible u) :
    conservativeHessian u k = (k 0)^2/u 0+u 0*(thermalShift u k)^2+
      shiftedMomentumSquared u k/EulerAdmissible.pressure u := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  dsimp [conservativeHessian,hessianForm,toPrimitive,primitiveD,thermalShift,shiftedMomentumSquared]
  field_simp
  ring

theorem hessian_components (u k : State) (hu : u ∈ region) :
    (k 0)^2 ≤ 4*conservativeHessian u k ∧
    shiftedMomentumSquared u k ≤ 4*conservativeHessian u k ∧
    (thermalShift u k)^2 ≤ 4*conservativeHessian u k := by
  have hadm := region_admissible u hu
  have hr := hadm.1
  have h0 : 0 ≤ (k 0)^2/u 0 := by positivity
  have h1 : 0 ≤ u 0*(thermalShift u k)^2 := mul_nonneg hadm.1.le (sq_nonneg _)
  have hy : 0 ≤ shiftedMomentumSquared u k := by dsimp [shiftedMomentumSquared]; positivity
  have h2 : 0 ≤ shiftedMomentumSquared u k/EulerAdmissible.pressure u := div_nonneg hy hadm.2.le
  have he := conservative_hessian_squares u k hadm
  have hEn : 0 ≤ conservativeHessian u k := by linarith
  have hk : (k 0)^2/u 0 ≤ conservativeHessian u k := by linarith
  have hY : shiftedMomentumSquared u k/EulerAdmissible.pressure u ≤ conservativeHessian u k := by linarith
  have hZ : u 0*(thermalShift u k)^2 ≤ conservativeHessian u k := by linarith
  refine ⟨?_,?_,?_⟩
  · have hh := (div_le_iff₀ hadm.1).mp hk
    have hm := mul_le_mul_of_nonneg_right hu.2.1 hEn
    nlinarith
  · have hh := (div_le_iff₀ hadm.2).mp hY
    have hm := mul_le_mul_of_nonneg_right (pressure_upper u hu) hEn
    nlinarith
  · have hm := mul_le_mul_of_nonneg_right hu.1 (sq_nonneg (thermalShift u k))
    nlinarith

def momentumSquared (k : State) : ℝ := k 1^2+k 2^2+k 3^2
def velocityPair (u k : State) : ℝ := (u 1/u 0)*k 1+(u 2/u 0)*k 2+(u 3/u 0)*k 3
def shiftedPair (u k : State) : ℝ :=
  (u 1/u 0)*(k 1-(u 1/u 0)*k 0)+(u 2/u 0)*(k 2-(u 2/u 0)*k 0)+
    (u 3/u 0)*(k 3-(u 3/u 0)*k 0)

theorem three_cauchy (a b c x y z : ℝ) :
    (a*x+b*y+c*z)^2 ≤ (a^2+b^2+c^2)*(x^2+y^2+z^2) := by
  nlinarith [sq_nonneg (a*y-b*x),sq_nonneg (a*z-c*x),sq_nonneg (b*z-c*y)]

theorem three_sum_bound (x y z : ℝ) : (x+y+z)^2 ≤ 3*(x^2+y^2+z^2) := by
  nlinarith [sq_nonneg (x-y),sq_nonneg (x-z),sq_nonneg (y-z)]

theorem size_parts (k : State) : k 0^2 ≤ sizeSquared k ∧ momentumSquared k ≤ sizeSquared k ∧
    k 4^2 ≤ sizeSquared k := by
  dsimp [sizeSquared,momentumSquared]
  constructor
  · nlinarith [sq_nonneg (k 1),sq_nonneg (k 2),sq_nonneg (k 3),sq_nonneg (k 4)]
  constructor
  · nlinarith [sq_nonneg (k 0),sq_nonneg (k 4)]
  · nlinarith [sq_nonneg (k 0),sq_nonneg (k 1),sq_nonneg (k 2),sq_nonneg (k 3)]

theorem velocity_pair_bound (u k : State) (hu : u ∈ region) :
    (velocityPair u k)^2 ≤ 30*momentumSquared k := by
  have hh := three_cauchy (u 1/u 0) (u 2/u 0) (u 3/u 0) (k 1) (k 2) (k 3)
  have hm := mul_le_mul_of_nonneg_right (velocity_squared_bound u hu)
    (show 0 ≤ momentumSquared k by dsimp [momentumSquared]; positivity)
  change (velocityPair u k)^2 ≤ velocitySquared u*momentumSquared k at hh
  exact hh.trans hm

theorem shifted_pair_bound (u k : State) (hu : u ∈ region) :
    (shiftedPair u k)^2 ≤ 30*shiftedMomentumSquared u k := by
  have hh := three_cauchy (u 1/u 0) (u 2/u 0) (u 3/u 0)
    (k 1-(u 1/u 0)*k 0) (k 2-(u 2/u 0)*k 0) (k 3-(u 3/u 0)*k 0)
  have hm := mul_le_mul_of_nonneg_right (velocity_squared_bound u hu)
    (show 0 ≤ shiftedMomentumSquared u k by dsimp [shiftedMomentumSquared]; positivity)
  change (shiftedPair u k)^2 ≤ velocitySquared u*shiftedMomentumSquared u k at hh
  exact hh.trans hm

theorem pressureD_decomposition (u k : State) (hr : u 0 ≠ 0) :
    pressureD u k=k 4-velocityPair u k+(velocitySquared u/2)*k 0 := by
  dsimp [pressureD,velocityPair,velocitySquared]
  field_simp

theorem pressureD_bound (u k : State) (hu : u ∈ region) :
    (pressureD u k)^2 ≤ 768*sizeSquared k := by
  have hadm := region_admissible u hu
  have hparts := size_parts k
  have hvel := velocity_squared_bound u hu
  have hvel0 : 0 ≤ velocitySquared u := by dsimp [velocitySquared]; positivity
  have hkin : (velocitySquared u/2)^2 ≤ 225 := by nlinarith
  have hterm : ((velocitySquared u/2)*k 0)^2 ≤ 225*sizeSquared k := by
    calc
      _ = (velocitySquared u/2)^2*k 0^2 := by ring
      _ ≤ 225*k 0^2 := mul_le_mul_of_nonneg_right hkin (sq_nonneg _)
      _ ≤ _ := mul_le_mul_of_nonneg_left hparts.1 (by norm_num)
  have hpair := (velocity_pair_bound u k hu).trans
    (mul_le_mul_of_nonneg_left hparts.2.1 (by norm_num : (0 : ℝ) ≤ 30))
  have hs := three_sum_bound (k 4) (-velocityPair u k) ((velocitySquared u/2)*k 0)
  rw [pressureD_decomposition u k (ne_of_gt hadm.1)]
  nlinarith [hparts.2.2]

theorem shifted_momentum_bound (u k : State) (hu : u ∈ region) :
    shiftedMomentumSquared u k ≤ 62*sizeSquared k := by
  have he : shiftedMomentumSquared u k ≤ 2*momentumSquared k+2*velocitySquared u*k 0^2 := by
    dsimp [shiftedMomentumSquared,momentumSquared,velocitySquared]
    nlinarith [sq_nonneg (k 1+(u 1/u 0)*k 0),sq_nonneg (k 2+(u 2/u 0)*k 0),
      sq_nonneg (k 3+(u 3/u 0)*k 0)]
  have hparts := size_parts k
  have hm := mul_le_mul_of_nonneg_right (velocity_squared_bound u hu) (sq_nonneg (k 0))
  nlinarith

theorem thermal_shift_bound (u k : State) (hu : u ∈ region) :
    (thermalShift u k)^2 ≤ 24608*sizeSquared k := by
  obtain ⟨hr0,hr4⟩ := EulerCoefficientBounds.reciprocal_bounds (u 0) hu.1
  obtain ⟨hp0,hp4⟩ := EulerCoefficientBounds.reciprocal_bounds (EulerAdmissible.pressure u) hu.2.2.2
  have hr2 : (1/u 0)^2 ≤ 16 := by nlinarith
  have hp2 : (1/EulerAdmissible.pressure u)^2 ≤ 16 := by nlinarith
  have hrterm : (k 0/u 0)^2 ≤ 16*sizeSquared k := by
    calc
      _ = (1/u 0)^2*k 0^2 := by ring
      _ ≤ 16*k 0^2 := mul_le_mul_of_nonneg_right hr2 (sq_nonneg _)
      _ ≤ _ := mul_le_mul_of_nonneg_left (size_parts k).1 (by norm_num)
  have hpterm : (pressureD u k/EulerAdmissible.pressure u)^2 ≤ 12288*sizeSquared k := by
    calc
      _ = (1/EulerAdmissible.pressure u)^2*(pressureD u k)^2 := by ring
      _ ≤ 16*(pressureD u k)^2 := mul_le_mul_of_nonneg_right hp2 (sq_nonneg _)
      _ ≤ 16*(768*sizeSquared k) := mul_le_mul_of_nonneg_left (pressureD_bound u k hu) (by norm_num)
      _ = _ := by ring
  dsimp [thermalShift]
  nlinarith [sq_nonneg (pressureD u k/EulerAdmissible.pressure u+k 0/u 0)]

theorem hessian_upper_bound (u k : State) (hu : u ∈ region) :
    conservativeHessian u k ≤ 100000*sizeSquared k := by
  obtain ⟨hr0,hr4⟩ := EulerCoefficientBounds.reciprocal_bounds (u 0) hu.1
  obtain ⟨hp0,hp4⟩ := EulerCoefficientBounds.reciprocal_bounds (EulerAdmissible.pressure u) hu.2.2.2
  have h0 : k 0^2/u 0 ≤ 4*sizeSquared k := by
    calc
      _ = (1/u 0)*k 0^2 := by ring
      _ ≤ 4*k 0^2 := mul_le_mul_of_nonneg_right hr4 (sq_nonneg _)
      _ ≤ _ := mul_le_mul_of_nonneg_left (size_parts k).1 (by norm_num)
  have h1 : u 0*(thermalShift u k)^2 ≤ 98432*sizeSquared k := by
    calc
      _ ≤ 4*(thermalShift u k)^2 := mul_le_mul_of_nonneg_right hu.2.1 (sq_nonneg _)
      _ ≤ 4*(24608*sizeSquared k) := mul_le_mul_of_nonneg_left (thermal_shift_bound u k hu) (by norm_num)
      _ = _ := by ring
  have h2 : shiftedMomentumSquared u k/EulerAdmissible.pressure u ≤ 248*sizeSquared k := by
    have hy : 0 ≤ shiftedMomentumSquared u k := by dsimp [shiftedMomentumSquared]; positivity
    calc
      _ = (1/EulerAdmissible.pressure u)*shiftedMomentumSquared u k := by ring
      _ ≤ 4*shiftedMomentumSquared u k := mul_le_mul_of_nonneg_right hp4 hy
      _ ≤ 4*(62*sizeSquared k) := mul_le_mul_of_nonneg_left (shifted_momentum_bound u k hu) (by norm_num)
      _ = _ := by ring
  rw [conservative_hessian_squares u k (region_admissible u hu)]
  nlinarith [size_nonnegative k]

theorem momentum_recovery_bound (u k : State) (hu : u ∈ region) :
    momentumSquared k ≤ 248*conservativeHessian u k := by
  obtain ⟨hr,hY,hZ⟩ := hessian_components u k hu
  have he : momentumSquared k ≤ 2*shiftedMomentumSquared u k+2*velocitySquared u*k 0^2 := by
    dsimp [shiftedMomentumSquared,momentumSquared,velocitySquared]
    nlinarith [sq_nonneg (k 1-2*(u 1/u 0)*k 0),sq_nonneg (k 2-2*(u 2/u 0)*k 0),
      sq_nonneg (k 3-2*(u 3/u 0)*k 0)]
  have hm := mul_le_mul_of_nonneg_right (velocity_squared_bound u hu) (sq_nonneg (k 0))
  nlinarith

theorem energy_recovery_identity (u k : State) (hu : EulerAdmissible.Admissible u) :
    k 4=EulerAdmissible.pressure u*thermalShift u k+
      (EulerAdmissible.pressure u/u 0+velocitySquared u/2)*k 0+shiftedPair u k := by
  have hr := ne_of_gt hu.1
  have hp := ne_of_gt hu.2
  dsimp [thermalShift,pressureD,velocitySquared,shiftedPair]
  field_simp
  all_goals ring

theorem energy_recovery_bound (u k : State) (hu : u ∈ region) :
    k 4^2 ≤ 12084*conservativeHessian u k := by
  have hadm := region_admissible u hu
  obtain ⟨hr,hY,hZ⟩ := hessian_components u k hu
  have hp4 := pressure_upper u hu
  have hp2 : (EulerAdmissible.pressure u)^2 ≤ 16 := by nlinarith [hadm.2]
  have hpdiv : EulerAdmissible.pressure u/u 0 ≤ 16 :=
    (div_le_iff₀ hadm.1).mpr (by nlinarith [hu.1])
  have hpdiv0 : 0 ≤ EulerAdmissible.pressure u/u 0 := div_nonneg hadm.2.le hadm.1.le
  have hvel := velocity_squared_bound u hu
  have hvel0 : 0 ≤ velocitySquared u := by dsimp [velocitySquared]; positivity
  have hcoef : (EulerAdmissible.pressure u/u 0+velocitySquared u/2)^2 ≤ 961 := by nlinarith
  have ht0 : (EulerAdmissible.pressure u*thermalShift u k)^2 ≤ 64*conservativeHessian u k := by
    calc
      _ = (EulerAdmissible.pressure u)^2*(thermalShift u k)^2 := by ring
      _ ≤ 16*(thermalShift u k)^2 := mul_le_mul_of_nonneg_right hp2 (sq_nonneg _)
      _ ≤ 16*(4*conservativeHessian u k) := mul_le_mul_of_nonneg_left hZ (by norm_num)
      _ = _ := by ring
  have ht1 : ((EulerAdmissible.pressure u/u 0+velocitySquared u/2)*k 0)^2 ≤
      3844*conservativeHessian u k := by
    calc
      _ = (EulerAdmissible.pressure u/u 0+velocitySquared u/2)^2*k 0^2 := by ring
      _ ≤ 961*k 0^2 := mul_le_mul_of_nonneg_right hcoef (sq_nonneg _)
      _ ≤ 961*(4*conservativeHessian u k) := mul_le_mul_of_nonneg_left hr (by norm_num)
      _ = _ := by ring
  have ht2 := (shifted_pair_bound u k hu).trans (mul_le_mul_of_nonneg_left hY (by norm_num : (0 : ℝ) ≤ 30))
  have hh := three_sum_bound (EulerAdmissible.pressure u*thermalShift u k)
    ((EulerAdmissible.pressure u/u 0+velocitySquared u/2)*k 0) (shiftedPair u k)
  rw [energy_recovery_identity u k hadm]
  nlinarith

theorem hessian_coercivity (u k : State) (hu : u ∈ region) :
    (1/12500 : ℝ)*sizeSquared k ≤ conservativeHessian u k := by
  have hr := (hessian_components u k hu).1
  have hm := momentum_recovery_bound u k hu
  have he := energy_recovery_bound u k hu
  have hEn := hessian_nonnegative (toPrimitive u) (primitiveD u k)
    (by dsimp [toPrimitive]; exact one_div_pos.mpr (region_admissible u hu).1) (region_admissible u hu).2
  change 0 ≤ conservativeHessian u k at hEn
  dsimp [sizeSquared,momentumSquared] at *
  nlinarith

end EulerPhysicalRegion
