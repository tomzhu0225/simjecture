-- Explicit derivative and finite-difference bounds for the actual Euler flux
-- on the concrete convex physical region. Constants are intentionally coarse.
noncomputable section
namespace EulerPhysicalFluxBounds
open EulerEntropy EulerEntropyTaylor EulerPhysicalRegion EulerEnergyBounds EulerVectorEstimates
open scoped BigOperators
abbrev State := Fin 5 → ℝ

def normalVelocity (u : State) (d : Fin 3) : ℝ := u ⟨d.val+1,by omega⟩/u 0
def normalShift (u k : State) (d : Fin 3) : ℝ := k ⟨d.val+1,by omega⟩-normalVelocity u d*k 0
def normalVelocityD (u k : State) (d : Fin 3) : ℝ := normalShift u k d/u 0

def fluxD (u k : State) (d : Fin 3) : State :=
  let v := normalVelocity u d
  let dv := normalVelocityD u k d
  ![k ⟨d.val+1,by omega⟩,
    k 1*v+u 1*dv+(if d=0 then pressureD u k else 0),
    k 2*v+u 2*dv+(if d=1 then pressureD u k else 0),
    k 3*v+u 3*dv+(if d=2 then pressureD u k else 0),
    (k 4+pressureD u k)*v+(u 4+EulerAdmissible.pressure u)*dv]

theorem normal_velocity_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : u t 0 ≠ 0) (d : Fin 3) :
    HasDerivAt (fun s => normalVelocity (u s) d) (normalVelocityD (u t) k d) t := by
  have hh := ((hasDerivAt_pi.mp hu) ⟨d.val+1,by omega⟩).div ((hasDerivAt_pi.mp hu) 0) hr
  convert hh using 1
  dsimp [normalVelocityD,normalShift,normalVelocity]
  field_simp

theorem flux_derivative {u : ℝ → State} {k : State} {t : ℝ}
    (hu : HasDerivAt u k t) (hr : u t 0 ≠ 0) (d : Fin 3) :
    HasDerivAt (fun s => EulerAdmissible.eulerFlux (u s) d) (fluxD (u t) k d) t := by
  have hv := normal_velocity_derivative hu hr d
  have hp := pressure_derivative hu hr
  have hif (j : Fin 3) : HasDerivAt (fun s => if d=j then EulerAdmissible.pressure (u s) else 0)
      (if d=j then pressureD (u t) k else 0) t := by
    by_cases h : d=j
    · simpa only [h,if_true] using hp
    · simpa only [h,if_false] using hasDerivAt_const t (0 : ℝ)
  apply hasDerivAt_pi.mpr
  intro i
  fin_cases i
  · exact (hasDerivAt_pi.mp hu) ⟨d.val+1,by omega⟩
  · exact (((hasDerivAt_pi.mp hu) 1).mul hv).add (hif 0)
  · exact (((hasDerivAt_pi.mp hu) 2).mul hv).add (hif 1)
  · exact (((hasDerivAt_pi.mp hu) 3).mul hv).add (hif 2)
  · exact (((hasDerivAt_pi.mp hu) 4).add hp).mul hv

theorem component_square_bound (k : State) (j : Fin 5) : k j^2 ≤ sizeSquared k := by
  rw [size_as_sum]
  exact Finset.single_le_sum (fun i _ => sq_nonneg (k i)) (Finset.mem_univ j)

theorem normal_velocity_bound (u : State) (hu : u ∈ region) (d : Fin 3) :
    (normalVelocity u d)^2 ≤ 30 := by
  have hv := velocity_squared_bound u hu
  fin_cases d <;> dsimp [normalVelocity,velocitySquared] at * <;>
    nlinarith [sq_nonneg (u 1/u 0),sq_nonneg (u 2/u 0),sq_nonneg (u 3/u 0)]

theorem normal_shift_bound (u k : State) (hu : u ∈ region) (d : Fin 3) :
    (normalShift u k d)^2 ≤ 62*sizeSquared k := by
  have hy := shifted_momentum_bound u k hu
  fin_cases d <;> dsimp [normalShift,normalVelocity,shiftedMomentumSquared] at * <;>
    nlinarith [sq_nonneg (k 1-(u 1/u 0)*k 0),sq_nonneg (k 2-(u 2/u 0)*k 0),
      sq_nonneg (k 3-(u 3/u 0)*k 0)]

theorem fluxD_momentum_bound (u k : State) (hu : u ∈ region) (d j : Fin 3) :
    (k ⟨j.val+1,by omega⟩*normalVelocity u d+u ⟨j.val+1,by omega⟩*normalVelocityD u k d+
      (if d=j then pressureD u k else 0))^2 ≤ 7974*sizeSquared k := by
  have h0 : (k ⟨j.val+1,by omega⟩*normalVelocity u d)^2 ≤ 30*sizeSquared k := by
    calc
      _ = (normalVelocity u d)^2*k ⟨j.val+1,by omega⟩^2 := by ring
      _ ≤ 30*k ⟨j.val+1,by omega⟩^2 :=
        mul_le_mul_of_nonneg_right (normal_velocity_bound u hu d) (sq_nonneg _)
      _ ≤ _ := mul_le_mul_of_nonneg_left (component_square_bound k _) (by norm_num)
  have h1 : (u ⟨j.val+1,by omega⟩*normalVelocityD u k d)^2 ≤ 1860*sizeSquared k := by
    have he : u ⟨j.val+1,by omega⟩*normalVelocityD u k d=
        normalVelocity u j*normalShift u k d := by dsimp [normalVelocityD,normalVelocity]; ring
    rw [he]
    calc
      _ = (normalVelocity u j)^2*(normalShift u k d)^2 := by ring
      _ ≤ 30*(normalShift u k d)^2 :=
        mul_le_mul_of_nonneg_right (normal_velocity_bound u hu j) (sq_nonneg _)
      _ ≤ 30*(62*sizeSquared k) := mul_le_mul_of_nonneg_left (normal_shift_bound u k hu d) (by norm_num)
      _ = _ := by ring
  have h2 : (if d=j then pressureD u k else 0)^2 ≤ 768*sizeSquared k := by
    by_cases hd : d=j
    · simpa only [hd,if_true] using pressureD_bound u k hu
    · simp only [hd,if_false,zero_pow (by norm_num : (2 : ℕ) ≠ 0)]
      exact mul_nonneg (by norm_num) (size_nonnegative k)
  have hh := three_sum_bound (k ⟨j.val+1,by omega⟩*normalVelocity u d)
    (u ⟨j.val+1,by omega⟩*normalVelocityD u k d) (if d=j then pressureD u k else 0)
  linarith

theorem fluxD_energy_bound (u k : State) (hu : u ∈ region) (d : Fin 3) :
    ((k 4+pressureD u k)*normalVelocity u d+
      (u 4+EulerAdmissible.pressure u)*normalVelocityD u k d)^2 ≤ 219256*sizeSquared k := by
  have hadm := region_admissible u hu
  have hsum : (k 4+pressureD u k)^2 ≤ 1538*sizeSquared k := by
    nlinarith [component_square_bound k 4,pressureD_bound u k hu,sq_nonneg (k 4-pressureD u k)]
  have h0 : ((k 4+pressureD u k)*normalVelocity u d)^2 ≤ 46140*sizeSquared k := by
    calc
      _ = (normalVelocity u d)^2*(k 4+pressureD u k)^2 := by ring
      _ ≤ 30*(k 4+pressureD u k)^2 :=
        mul_le_mul_of_nonneg_right (normal_velocity_bound u hu d) (sq_nonneg _)
      _ ≤ 30*(1538*sizeSquared k) := mul_le_mul_of_nonneg_left hsum (by norm_num)
      _ = _ := by ring
  have hpE : EulerAdmissible.pressure u ≤ u 4 := by
    have hr := hadm.1
    have hn : 0 ≤ (u 1^2+u 2^2+u 3^2)/(2*u 0) := by positivity
    dsimp [EulerAdmissible.pressure]
    linarith
  have hc0 : 0 ≤ (u 4+EulerAdmissible.pressure u)/u 0 := by
    apply div_nonneg _ hadm.1.le
    linarith [hadm.2]
  have hc32 : (u 4+EulerAdmissible.pressure u)/u 0 ≤ 32 :=
    (div_le_iff₀ hadm.1).mpr (by linarith [hu.1,hu.2.2.1,pressure_upper u hu])
  have hc2 : ((u 4+EulerAdmissible.pressure u)/u 0)^2 ≤ 1024 := by nlinarith
  have h1 : ((u 4+EulerAdmissible.pressure u)*normalVelocityD u k d)^2 ≤ 63488*sizeSquared k := by
    calc
      _ = ((u 4+EulerAdmissible.pressure u)/u 0)^2*(normalShift u k d)^2 := by
        dsimp [normalVelocityD]; ring
      _ ≤ 1024*(normalShift u k d)^2 := mul_le_mul_of_nonneg_right hc2 (sq_nonneg _)
      _ ≤ 1024*(62*sizeSquared k) := mul_le_mul_of_nonneg_left (normal_shift_bound u k hu d) (by norm_num)
      _ = _ := by ring
  nlinarith [sq_nonneg ((k 4+pressureD u k)*normalVelocity u d-
    (u 4+EulerAdmissible.pressure u)*normalVelocityD u k d)]

theorem fluxD_bound (u k : State) (hu : u ∈ region) (d : Fin 3) :
    sizeSquared (fluxD u k d) ≤ 250000*sizeSquared k := by
  have h0 := component_square_bound k ⟨d.val+1,by omega⟩
  have h1 := fluxD_momentum_bound u k hu d 0
  have h2 := fluxD_momentum_bound u k hu d 1
  have h3 := fluxD_momentum_bound u k hu d 2
  have h4 := fluxD_energy_bound u k hu d
  change (k 1*normalVelocity u d+u 1*normalVelocityD u k d+
    (if d=0 then pressureD u k else 0))^2 ≤ _ at h1
  change (k 2*normalVelocity u d+u 2*normalVelocityD u k d+
    (if d=1 then pressureD u k else 0))^2 ≤ _ at h2
  change (k 3*normalVelocity u d+u 3*normalVelocityD u k d+
    (if d=2 then pressureD u k else 0))^2 ≤ _ at h3
  change k ⟨d.val+1,by omega⟩^2+
    (k 1*normalVelocity u d+u 1*normalVelocityD u k d+(if d=0 then pressureD u k else 0))^2+
    (k 2*normalVelocity u d+u 2*normalVelocityD u k d+(if d=1 then pressureD u k else 0))^2+
    (k 3*normalVelocity u d+u 3*normalVelocityD u k d+(if d=2 then pressureD u k else 0))^2+
    ((k 4+pressureD u k)*normalVelocity u d+(u 4+EulerAdmissible.pressure u)*normalVelocityD u k d)^2 ≤
      250000*sizeSquared k
  nlinarith [size_nonnegative k]

theorem physical_flux_lipschitz (u v : State) (hu : u ∈ region) (hv : v ∈ region) (d : Fin 3) :
    sizeSquared (EulerAdmissible.eulerFlux v d-EulerAdmissible.eulerFlux u d) ≤
      (1200 : ℝ)^2*sizeSquared (v-u) := by
  have hseg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :=
    EulerEntropyRegion.segment_in_region region region_convex u v hu hv t ht
  have hcomponent (j : Fin 5) :
      (EulerAdmissible.eulerFlux v d j-EulerAdmissible.eulerFlux u d j)^2 ≤ 250000*sizeSquared (v-u) := by
    let f := fun t => EulerAdmissible.eulerFlux (EulerEntropyConvexity.segment u v t) d j
    let df := fun t => fluxD (EulerEntropyConvexity.segment u v t) (v-u) d j
    have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t :=
      (hasDerivAt_pi.mp (flux_derivative (EulerEntropyConvexity.segment_derivative u v t)
        (ne_of_gt (region_admissible _ (hseg t ht)).1) d)) j
    obtain ⟨t,ht,he⟩ := exists_hasDerivAt_eq_slope f df (by norm_num : (0 : ℝ) < 1)
      (fun t ht => (hd t ht).continuousAt.continuousWithinAt)
      (fun t ht => hd t ⟨ht.1.le,ht.2.le⟩)
    simp [f,df,EulerEntropyConvexity.segment] at he
    rw [← he]
    exact (component_square_bound _ j).trans (fluxD_bound _ _ (hseg t ⟨ht.1.le,ht.2.le⟩) d)
  rw [size_as_sum]
  simp only [Pi.sub_apply]
  calc
    _ ≤ ∑ j : Fin 5, 250000*sizeSquared (v-u) := Finset.sum_le_sum (fun j _ => hcomponent j)
    _ = 1250000*sizeSquared (v-u) := by simp; ring
    _ ≤ _ := by nlinarith [size_nonnegative (v-u)]

theorem concrete_region_bounds : EulerEntropyRegion.RegionBounds region 100000 (1/12500) 1200 := by
  exact ⟨region_convex,region_admissible,(fun u hu k => hessian_upper_bound u k hu),
    (fun u hu k => hessian_coercivity u k hu),(fun u hu v hv d => physical_flux_lipschitz u v hu hv d)⟩

theorem region_wave_speed_bound (u : State) (hu : u ∈ region) (d : Fin 3) :
    EulerAdmissible.waveSpeed u d ≤ 12 := by
  have hadm := region_admissible u hu
  have hv2 := normal_velocity_bound u hu d
  have hv : |normalVelocity u d| ≤ 6 := by nlinarith [sq_abs (normalVelocity u d),abs_nonneg (normalVelocity u d)]
  have hc : Real.sqrt (2*EulerAdmissible.pressure u/u 0) ≤ 6 := by
    apply Real.sqrt_le_iff.mpr
    refine ⟨by norm_num,?_⟩
    apply (div_le_iff₀ hadm.1).mpr
    nlinarith [pressure_upper u hu,hu.1]
  have he : EulerAdmissible.fromVelocity u d=normalVelocity u d := by
    fin_cases d <;> rfl
  dsimp [EulerAdmissible.waveSpeed]
  rw [he]
  linarith

theorem regional_global_speed_bound {I : Type*} [Fintype I] [Nonempty I]
    (u : I → State) (hu : ∀ i, u i ∈ region) (d : Fin 3) : EulerAdmissible.globalSpeed u d ≤ 12 := by
  exact (Finset.sup'_le_iff Finset.univ_nonempty _).mpr
    (fun i _ => region_wave_speed_bound (u i) (hu i) d)

theorem coarse_viscosity_requirement (a : ℝ)
    (h : (100000 : ℝ)*(1+1200^2) ≤ a*(1/12500)/2) : 3600002500000000 ≤ a := by
  linarith

-- This rejects these coarse constants as a certificate for the present
-- wave-speed recipe. It does not reject the method's actual entropy behavior.
theorem current_speeds_fail_coarse_viscosity {I : Type*} [Fintype I] [Nonempty I]
    (u : I → State) (hu : ∀ i, u i ∈ region) (d : Fin 3) :
    ¬ ((100000 : ℝ)*(1+1200^2) ≤ EulerAdmissible.globalSpeed u d*(1/12500)/2) := by
  intro h
  have hlo := coarse_viscosity_requirement _ h
  have hhi := regional_global_speed_bound u hu d
  linarith

def restState : State := ![1,0,0,0,1]
def softDirection : State := ![1,0,0,0,2]
def hardDirection : State := ![2,0,0,0,-1]

theorem rest_state_in_region : restState ∈ region := by
  norm_num [restState,region,EulerAdmissible.pressure,Matrix.cons_val_two,Matrix.cons_val_three,
    Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail]

theorem initial_family_contains_rest (A delta : ℝ) :
    EulerInitialRegion.initialState A delta 0 (Real.pi/2) (Real.pi/2)=restState := by
  have hpi : (2 : ℝ)*(Real.pi/2)=Real.pi := by ring
  simp [EulerInitialRegion.initialState,EulerInitialRegion.density,EulerInitialRegion.pressure,
    EulerInitialRegion.velocity,EulerAdmissible.primitive,EulerAdmissible.kinetic,restState,hpi]

theorem rest_hessian_values : conservativeHessian restState softDirection=2 ∧
    sizeSquared softDirection=5 ∧ conservativeHessian restState hardDirection=13 ∧
    sizeSquared hardDirection=5 := by
  norm_num [restState,softDirection,hardDirection,conservativeHessian,hessianForm,toPrimitive,
    primitiveD,pressureD,sizeSquared,EulerAdmissible.pressure,Matrix.cons_val_two,Matrix.cons_val_three,
    Matrix.cons_val_four,Matrix.vecHead,Matrix.vecTail]

theorem rest_curvature_constraints (K : Set State) (M lambda L : ℝ)
    (hK : EulerEntropyRegion.RegionBounds K M lambda L) (hrest : restState ∈ K) :
    13/5 ≤ M ∧ lambda ≤ 2/5 := by
  obtain ⟨hs,hss,hh,hhs⟩ := rest_hessian_values
  have hupper := hK.hessian_upper restState hrest hardDirection
  have hlower := hK.hessian_lower restState hrest softDirection
  rw [hh,hhs] at hupper
  rw [hs,hss] at hlower
  constructor <;> linarith

-- Even optimal global Euclidean curvature constants on a region containing
-- this rest state cannot meet this sufficient criterion when a<=12. A sharper
-- entropy estimate is needed; this is not an impossibility theorem for Euler.
theorem global_criterion_obstruction (K : Set State) (M lambda L a : ℝ)
    (hK : EulerEntropyRegion.RegionBounds K M lambda L) (hrest : restState ∈ K)
    (ha0 : 0 ≤ a) (ha12 : a ≤ 12) : ¬ (M*(1+L^2) ≤ a*lambda/2) := by
  obtain ⟨hM,hlambda⟩ := rest_curvature_constraints K M lambda L hK hrest
  have hprod := mul_le_mul_of_nonneg_left hlambda ha0
  have hnonneg := mul_nonneg (by linarith : 0 ≤ M) (sq_nonneg L)
  intro h
  nlinarith

theorem current_speeds_fail_any_region_constants {I : Type*} [Fintype I] [Nonempty I]
    (u : I → State) (hu : ∀ i, u i ∈ region) (M lambda L : ℝ)
    (hK : EulerEntropyRegion.RegionBounds region M lambda L) (d : Fin 3) :
    ¬ (M*(1+L^2) ≤ EulerAdmissible.globalSpeed u d*lambda/2) := by
  exact global_criterion_obstruction region M lambda L _ hK rest_state_in_region
    (EulerAdmissible.globalSpeed_positive u (fun i => region_admissible (u i) (hu i)) d).le
    (regional_global_speed_bound u hu d)

end EulerPhysicalFluxBounds
