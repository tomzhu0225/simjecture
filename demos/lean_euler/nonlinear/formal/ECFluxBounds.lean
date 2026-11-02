-- Consistency bounds for the actual logarithmic-mean numerical flux on the
-- concrete physical region. Region membership during evolution is separate.
noncomputable section
namespace EulerECFluxBounds
open EulerEntropy EulerPhysicalRegion EulerEnergyBounds EulerVectorEstimates
open EulerEntropyConservativeFlux EulerLogMean
abbrev State := Fin 5 → ℝ
abbrev Vec := Fin 3 → ℝ

theorem near_add (a b c d h A B : ℝ) (ha : |a-c| ≤ A*h) (hb : |b-d| ≤ B*h) :
    |(a+b)-(c+d)| ≤ (A+B)*h := by
  have he : (a+b)-(c+d)=(a-c)+(b-d) := by ring
  rw [he]
  have hh := abs_add_le (a-c) (b-d)
  linarith

theorem near_sub (a b c d h A B : ℝ) (ha : |a-c| ≤ A*h) (hb : |b-d| ≤ B*h) :
    |(a-b)-(c-d)| ≤ (A+B)*h := by
  have he : (a-b)-(c-d)=(a-c)-(b-d) := by ring
  rw [he]
  have hh := abs_sub (a-c) (b-d)
  linarith

theorem near_mul (a b c d h A D Ca Cb : ℝ)
    (hA : |a| ≤ A) (hD : |d| ≤ D) (ha : |a-c| ≤ Ca*h) (hb : |b-d| ≤ Cb*h) :
    |a*b-c*d| ≤ (A*Cb+D*Ca)*h := by
  have he : a*b-c*d=a*(b-d)+(a-c)*d := by ring
  have h1 := mul_le_mul hA hb (abs_nonneg (b-d)) ((abs_nonneg a).trans hA)
  have h2 := mul_le_mul ha hD (abs_nonneg d) ((abs_nonneg (a-c)).trans ha)
  rw [he]
  have hh := abs_add_le (a*(b-d)) ((a-c)*d)
  simp only [abs_mul] at hh
  nlinarith

theorem near_inv (b c h m C : ℝ) (hm : 0 < m) (hb : m ≤ b) (hc : m ≤ c)
    (he : |b-c| ≤ C*h) : |1/b-1/c| ≤ (C/m^2)*h := by
  have hbpos := hm.trans_le hb
  have hcpos := hm.trans_le hc
  have hn := (abs_nonneg (b-c)).trans he
  have hprod : m^2 ≤ b*c := by nlinarith [mul_le_mul hb hc hm.le hbpos.le]
  have hid : 1/b-1/c=(c-b)/(b*c) := by field_simp
  rw [hid,abs_div,abs_of_pos (mul_pos hbpos hcpos),abs_sub_comm c b]
  calc
    _ ≤ (C*h)/(b*c) := div_le_div_of_nonneg_right he (mul_pos hbpos hcpos).le
    _ ≤ (C*h)/m^2 := div_le_div_of_nonneg_left hn (sq_pos_of_pos hm) hprod
    _ = _ := by ring

theorem near_div (a b c d h m A Ca Cb : ℝ) (hm : 0 < m) (hb : m ≤ b) (hd : m ≤ d)
    (hA : |a| ≤ A) (ha : |a-c| ≤ Ca*h) (hbd : |b-d| ≤ Cb*h) :
    |a/b-c/d| ≤ (A*Cb/m^2+Ca/m)*h := by
  have hi := near_inv b d h m Cb hm hb hd hbd
  have hdi : |1/d| ≤ 1/m := by
    rw [abs_of_pos (one_div_pos.mpr (hm.trans_le hd))]
    exact one_div_le_one_div_of_le hm hd
  have hh := near_mul a (1/b) c (1/d) h A (1/m) Ca (Cb/m^2) hA hdi ha hi
  calc
    _ = |a*(1/b)-c*(1/d)| := by congr 1; ring
    _ ≤ (A*(Cb/m^2)+(1/m)*Ca)*h := hh
    _ = _ := by ring

theorem average_abs_bound (a b B : ℝ) (ha : |a| ≤ B) (hb : |b| ≤ B) : |average a b| ≤ B := by
  have hh := abs_add_le a b
  dsimp [average]
  rw [abs_div,abs_of_pos (by norm_num : (0 : ℝ) < 2)]
  linarith

theorem average_near_left (a b h C : ℝ) (he : |b-a| ≤ C*h) :
    |average a b-a| ≤ (C/2)*h := by
  have hh : average a b-a=(b-a)/2 := by dsimp [average]; ring
  rw [hh,abs_div,abs_of_pos (by norm_num : (0 : ℝ) < 2)]
  linarith

theorem mean_near_left (a b : ℝ) (ha : 0 < a) (hb : 0 < b) :
    |logMean a b-a| ≤ |b-a| := by
  have hh := between a b ha hb
  rcases le_total a b with hab | hba
  · rw [min_eq_left hab,max_eq_right hab] at hh
    rw [abs_of_nonneg (sub_nonneg.mpr hh.1),abs_of_nonneg (sub_nonneg.mpr hab)]
    linarith
  · rw [min_eq_right hba,max_eq_left hba] at hh
    rw [abs_of_nonpos (sub_nonpos.mpr hh.2),abs_of_nonpos (sub_nonpos.mpr hba)]
    linarith

theorem size_from_components (k : State) (h : ℝ) (_hh : 0 ≤ h) (hk : ∀ j, |k j| ≤ h) :
    sizeSquared k ≤ 5*h^2 := by
  have hj (j : Fin 5) : k j^2 ≤ h^2 := by
    have ht := mul_self_le_mul_self (abs_nonneg (k j)) (hk j)
    nlinarith [sq_abs (k j)]
  dsimp [sizeSquared]
  linarith [hj 0,hj 1,hj 2,hj 3,hj 4]

theorem pressure_difference_bound (u v : State) (hu : u ∈ region) (hv : v ∈ region)
    (h : ℝ) (hh : 0 ≤ h) (hnear : ∀ j, |v j-u j| ≤ h) :
    |EulerAdmissible.pressure v-EulerAdmissible.pressure u| ≤ 64*h := by
  have hsize := size_from_components (v-u) h hh hnear
  let f := fun t => EulerAdmissible.pressure (EulerEntropyConvexity.segment u v t)
  let df := fun t => pressureD (EulerEntropyConvexity.segment u v t) (v-u)
  have hseg (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) :=
    EulerEntropyRegion.segment_in_region region region_convex u v hu hv t ht
  have hd (t : ℝ) (ht : t ∈ Set.Icc (0 : ℝ) 1) : HasDerivAt f (df t) t :=
    pressure_derivative (EulerEntropyConvexity.segment_derivative u v t)
      (ne_of_gt (region_admissible _ (hseg t ht)).1)
  obtain ⟨t,ht,he⟩ := exists_hasDerivAt_eq_slope f df (by norm_num : (0 : ℝ) < 1)
    (fun t ht => (hd t ht).continuousAt.continuousWithinAt)
    (fun t ht => hd t ⟨ht.1.le,ht.2.le⟩)
  have hs := pressureD_bound (EulerEntropyConvexity.segment u v t) (v-u) (hseg t ⟨ht.1.le,ht.2.le⟩)
  have habs : |df t| ≤ 64*h := abs_le_of_sq_le_sq (by dsimp [df]; nlinarith) (by positivity)
  simp [f,EulerEntropyConvexity.segment] at he
  rwa [← he]

theorem momentum_abs_bound (u : State) (hu : u ∈ region) (j : Fin 3) :
    |u ⟨j.val+1,by omega⟩| ≤ 6 := by
  have hr := (region_admissible u hu).1
  have hkin : u 1^2+u 2^2+u 3^2=2*u 0*(u 4-EulerAdmissible.pressure u) := by
    dsimp [EulerAdmissible.pressure]
    field_simp
    ring
  have hm : 2*u 0*(u 4-EulerAdmissible.pressure u) ≤ 30 := by
    have he : u 4-EulerAdmissible.pressure u ≤ 15/4 := by linarith [hu.2.2.1,hu.2.2.2]
    nlinarith [mul_le_mul_of_nonneg_left he hr.le,hu.2.1]
  fin_cases j <;> dsimp
  all_goals apply abs_le_of_sq_le_sq _ (by norm_num : (0 : ℝ) ≤ 6)
  all_goals nlinarith [sq_nonneg (u 1),sq_nonneg (u 2),sq_nonneg (u 3)]

theorem velocity_abs_bound (u : State) (hu : u ∈ region) (j : Fin 3) :
    |EulerAdmissible.fromVelocity u j| ≤ 6 := by
  have hh := EulerPhysicalFluxBounds.normal_velocity_bound u hu j
  have he : EulerAdmissible.fromVelocity u j=EulerPhysicalFluxBounds.normalVelocity u j := by
    fin_cases j <;> rfl
  rw [he]
  exact abs_le_of_sq_le_sq (by linarith) (by norm_num)

theorem velocity_difference_bound (u v : State) (hu : u ∈ region) (hv : v ∈ region)
    (h : ℝ) (hnear : ∀ j, |v j-u j| ≤ h) (j : Fin 3) :
    |EulerAdmissible.fromVelocity v j-EulerAdmissible.fromVelocity u j| ≤ 100*h := by
  have hh := near_div (v ⟨j.val+1,by omega⟩) (v 0) (u ⟨j.val+1,by omega⟩) (u 0)
    h (1/4) 6 1 1 (by norm_num) hv.1 hu.1 (momentum_abs_bound v hv j)
    (by simpa only [one_mul] using hnear ⟨j.val+1,by omega⟩) (by simpa only [one_mul] using hnear 0)
  norm_num at hh
  fin_cases j <;> exact hh

theorem beta_bounds (u : State) (hu : u ∈ region) : 1/32 ≤ beta u ∧ beta u ≤ 8 := by
  have hp := (region_admissible u hu).2
  have hpupper := pressure_upper u hu
  dsimp [beta]
  constructor
  · apply (le_div_iff₀ (by positivity : 0 < 2*EulerAdmissible.pressure u)).mpr
    linarith [hu.1]
  · apply (div_le_iff₀ (by positivity : 0 < 2*EulerAdmissible.pressure u)).mpr
    linarith [hu.2.1,hu.2.2.2]

theorem beta_difference_bound (u v : State) (hu : u ∈ region) (hv : v ∈ region)
    (h : ℝ) (hh : 0 ≤ h) (hnear : ∀ j, |v j-u j| ≤ h) : |beta v-beta u| ≤ 2050*h := by
  have hp := pressure_difference_bound u v hu hv h hh hnear
  have hden : |2*EulerAdmissible.pressure v-2*EulerAdmissible.pressure u| ≤ 128*h := by
    have he : 2*EulerAdmissible.pressure v-2*EulerAdmissible.pressure u=
        2*(EulerAdmissible.pressure v-EulerAdmissible.pressure u) := by ring
    rw [he,abs_mul,abs_of_pos (by norm_num : (0 : ℝ) < 2)]
    linarith
  have hr : |v 0| ≤ 4 := by rw [abs_of_pos (region_admissible v hv).1]; exact hv.2.1
  have he := near_div (v 0) (2*EulerAdmissible.pressure v) (u 0) (2*EulerAdmissible.pressure u)
    h (1/2) 4 1 128 (by norm_num) (by linarith [hv.2.2.2]) (by linarith [hu.2.2.2]) hr
    (by simpa only [one_mul] using hnear 0) hden
  norm_num at he
  exact he

theorem near_scale (s a b h C : ℝ) (he : |a-b| ≤ C*h) :
    |s*a-s*b| ≤ (|s| *C)*h := by
  rw [← mul_sub,abs_mul]
  have hh := mul_le_mul_of_nonneg_left he (abs_nonneg s)
  nlinarith

theorem quotient_abs_bound (a b m A : ℝ) (hm : 0 < m) (hb : m ≤ b) (ha : |a| ≤ A) :
    |a/b| ≤ A/m := by
  rw [abs_div,abs_of_pos (hm.trans_le hb)]
  exact (div_le_div_of_nonneg_right ha (hm.trans_le hb).le).trans
    (div_le_div_of_nonneg_left ((abs_nonneg a).trans ha) hm hb)

structure ParameterRegion (r b : ℝ) (v : Vec) : Prop where
  density_lower : 1/4 ≤ r
  density_upper : r ≤ 4
  beta_lower : 1/32 ≤ b
  beta_upper : b ≤ 8
  speed_bound : speedSquared v ≤ 30

theorem parameter_velocity_abs (r b : ℝ) (v : Vec) (hv : ParameterRegion r b v) (j : Fin 3) :
    |v j| ≤ 6 := by
  have hh := hv.speed_bound
  dsimp [speedSquared] at hh
  have h0 : (v 0)^2 ≤ (6 : ℝ)^2 := by nlinarith [sq_nonneg (v 1),sq_nonneg (v 2)]
  have h1 : (v 1)^2 ≤ (6 : ℝ)^2 := by nlinarith [sq_nonneg (v 0),sq_nonneg (v 2)]
  have h2 : (v 2)^2 ≤ (6 : ℝ)^2 := by nlinarith [sq_nonneg (v 0),sq_nonneg (v 1)]
  fin_cases j
  · exact abs_le_of_sq_le_sq h0 (by norm_num)
  · exact abs_le_of_sq_le_sq h1 (by norm_num)
  · exact abs_le_of_sq_le_sq h2 (by norm_num)

theorem physical_parameter_region (u : State) (hu : u ∈ region) :
    ParameterRegion (u 0) (beta u) (EulerAdmissible.fromVelocity u) := by
  refine ⟨hu.1,hu.2.1,(beta_bounds u hu).1,(beta_bounds u hu).2,?_⟩
  exact velocity_squared_bound u hu

theorem average_diagonal (x : ℝ) : average x x=x := by dsimp [average]; ring

theorem parameter_flux_component_bound (rL rR bL bR : ℝ) (vL vR : Vec) (d : Fin 3)
    (hL : ParameterRegion rL bL vL) (hR : ParameterRegion rR bR vR)
    (h : ℝ) (hh : 0 ≤ h) (hrnear : |rR-rL| ≤ h) (hbnear : |bR-bL| ≤ 2050*h)
    (hvnear : ∀ j, |vR j-vL j| ≤ 100*h) (j : Fin 5) :
    |parameterFlux rL rR bL bR vL vR d j-parameterFlux rL rL bL bL vL vL d j| ≤ 100000000*h := by
  have hrLp : 0 < rL := by linarith [hL.density_lower]
  have hrRp : 0 < rR := by linarith [hR.density_lower]
  have hbLp : 0 < bL := by linarith [hL.beta_lower]
  have hbRp : 0 < bR := by linarith [hR.beta_lower]
  let lr := logMean rL rR
  let lb := logMean bL bR
  let rb := average rL rR
  let bb := average bL bR
  let vb : Vec := fun i => average (vL i) (vR i)
  let mass := lr*vb d
  let mass0 := rL*vL d
  let phat := rb/(2*bb)
  let p0 := rL/(2*bL)
  let mom : Vec := fun i => mass*vb i+(if d=i then phat else 0)
  let mom0 : Vec := fun i => mass0*vL i+(if d=i then p0 else 0)
  let thermal := 1/(2*lb)-average (speedSquared vL) (speedSquared vR)/2
  let thermal0 := 1/(2*bL)-speedSquared vL/2
  have hrLabs : |rL| ≤ 4 := by rw [abs_of_pos hrLp]; exact hL.density_upper
  have hrRabs : |rR| ≤ 4 := by rw [abs_of_pos hrRp]; exact hR.density_upper
  have hlrabs : |lr| ≤ 4 := by
    rw [abs_of_pos (positive rL rR hrLp hrRp)]
    exact (between rL rR hrLp hrRp).2.trans (max_le hL.density_upper hR.density_upper)
  have hlb : 1/32 ≤ lb := (le_min hL.beta_lower hR.beta_lower).trans (between bL bR hbLp hbRp).1
  have hbb : 1/32 ≤ bb := by dsimp [bb,average]; linarith [hL.beta_lower,hR.beta_lower]
  have hrbabs : |rb| ≤ 4 := average_abs_bound rL rR 4 hrLabs hrRabs
  have hlrnear : |lr-rL| ≤ 1*h := by simpa only [one_mul] using (mean_near_left rL rR hrLp hrRp).trans hrnear
  have hlbnear : |lb-bL| ≤ 2050*h := (mean_near_left bL bR hbLp hbRp).trans hbnear
  have hrbnear : |rb-rL| ≤ (1/2)*h := average_near_left rL rR h 1 (by simpa only [one_mul] using hrnear)
  have hbbnear : |2*bb-2*bL| ≤ 2050*h := by
    have he := near_scale 2 bb bL h (2050/2) (average_near_left bL bR h 2050 hbnear)
    norm_num at he
    exact he
  have hlbnear2 : |2*lb-2*bL| ≤ 4100*h := by
    have he := near_scale 2 lb bL h 2050 hlbnear
    norm_num at he
    exact he
  have hvL (i : Fin 3) := parameter_velocity_abs rL bL vL hL i
  have hvR (i : Fin 3) := parameter_velocity_abs rR bR vR hR i
  have hvb (i : Fin 3) : |vb i| ≤ 6 := average_abs_bound _ _ _ (hvL i) (hvR i)
  have hvbn (i : Fin 3) : |vb i-vL i| ≤ 50*h := by
    have he := average_near_left (vL i) (vR i) h 100 (hvnear i)
    norm_num at he
    exact he
  have hmass : |mass| ≤ 24 := by
    dsimp [mass]
    rw [abs_mul]
    have he := mul_le_mul hlrabs (hvb d) (abs_nonneg (vb d)) (by norm_num : (0 : ℝ) ≤ 4)
    linarith
  have hmass0 : |mass0| ≤ 24 := by
    dsimp [mass0]
    rw [abs_mul]
    have he := mul_le_mul hrLabs (hvL d) (abs_nonneg (vL d)) (by norm_num : (0 : ℝ) ≤ 4)
    linarith
  have hmassnear : |mass-mass0| ≤ 206*h := by
    have he := near_mul lr (vb d) rL (vL d) h 4 6 1 50 hlrabs (hvL d) hlrnear (hvbn d)
    norm_num at he
    exact he
  have hphat : |phat| ≤ 64 := by
    have he := quotient_abs_bound rb (2*bb) (1/16) 4 (by norm_num) (by linarith) hrbabs
    norm_num at he
    exact he
  have hp0 : |p0| ≤ 64 := by
    have he := quotient_abs_bound rL (2*bL) (1/16) 4 (by norm_num) (by linarith [hL.beta_lower]) hrLabs
    norm_num at he
    exact he
  have hphatnear : |phat-p0| ≤ 2099208*h := by
    have he := near_div rb (2*bb) rL (2*bL) h (1/16) 4 (1/2) 2050
      (by norm_num) (by linarith) (by linarith [hL.beta_lower]) hrbabs hrbnear hbbnear
    norm_num at he
    exact he
  have hmom0 (i : Fin 3) : |mom0 i| ≤ 208 := by
    have hpif : |(if d=i then p0 else 0)| ≤ 64 := by
      by_cases hd : d=i
      · simpa only [hd,if_true] using hp0
      · simp only [hd,if_false,abs_zero]
        norm_num
    have he := mul_le_mul hmass0 (hvL i) (abs_nonneg (vL i)) (by norm_num : (0 : ℝ) ≤ 24)
    have hs := abs_add_le (mass0*vL i) (if d=i then p0 else 0)
    rw [abs_mul] at hs
    dsimp [mom0]
    linarith
  have hmomnear (i : Fin 3) : |mom i-mom0 i| ≤ 2101644*h := by
    have hprod := near_mul mass (vb i) mass0 (vL i) h 24 6 206 50 hmass (hvL i) hmassnear (hvbn i)
    norm_num at hprod
    have hpif : |(if d=i then phat else 0)-(if d=i then p0 else 0)| ≤ 2099208*h := by
      by_cases hd : d=i
      · simpa only [hd,if_true] using hphatnear
      · simp only [hd,if_false,sub_self,abs_zero]
        positivity
    have he := near_add (mass*vb i) (if d=i then phat else 0) (mass0*vL i) (if d=i then p0 else 0)
      h 2436 2099208 hprod hpif
    norm_num at he
    exact he
  have hsL : |speedSquared vL| ≤ 30 := abs_le.mpr ⟨by dsimp [speedSquared]; nlinarith [sq_nonneg (vL 0),sq_nonneg (vL 1),sq_nonneg (vL 2)],hL.speed_bound⟩
  have hsR : |speedSquared vR| ≤ 30 := abs_le.mpr ⟨by dsimp [speedSquared]; nlinarith [sq_nonneg (vR 0),sq_nonneg (vR 1),sq_nonneg (vR 2)],hR.speed_bound⟩
  have hsbar : |average (speedSquared vL) (speedSquared vR)| ≤ 30 := average_abs_bound _ _ _ hsL hsR
  have hsnear : |speedSquared vR-speedSquared vL| ≤ 3600*h := by
    have hsq (i : Fin 3) : |vR i*vR i-vL i*vL i| ≤ 1200*h := by
      have he := near_mul (vR i) (vR i) (vL i) (vL i) h 6 6 100 100 (hvR i) (hvL i) (hvnear i) (hvnear i)
      norm_num at he
      exact he
    have he := near_add (vR 0*vR 0+vR 1*vR 1) (vR 2*vR 2) (vL 0*vL 0+vL 1*vL 1) (vL 2*vL 2)
      h (1200+1200) 1200 (near_add _ _ _ _ h 1200 1200 (hsq 0) (hsq 1)) (hsq 2)
    have hid : speedSquared vR-speedSquared vL=
        (vR 0*vR 0+vR 1*vR 1+vR 2*vR 2)-(vL 0*vL 0+vL 1*vL 1+vL 2*vL 2) := by
      dsimp [speedSquared]
      ring
    rw [hid]
    convert he using 1
    ring
  have hthermalnear : |thermal-thermal0| ≤ 1050500*h := by
    have hi := near_div 1 (2*lb) 1 (2*bL) h (1/16) 1 0 4100
      (by norm_num) (by linarith) (by linarith [hL.beta_lower]) (by norm_num) (by simp) hlbnear2
    have hs := near_div (average (speedSquared vL) (speedSquared vR)) 2 (speedSquared vL) 2 h 2 30 1800 0
      (by norm_num) (by norm_num) (by norm_num) hsbar
      (by convert average_near_left _ _ h 3600 hsnear using 1; ring) (by simp)
    norm_num1 at hi hs
    have he := near_sub _ _ _ _ h 1049600 900 hi hs
    norm_num at he
    simpa only [thermal,thermal0,one_div,mul_inv_rev] using he
  have hthermal0 : |thermal0| ≤ 31 := by
    have hi := quotient_abs_bound 1 (2*bL) (1/16) 1 (by norm_num)
      (by linarith [hL.beta_lower]) (by norm_num)
    have hs := quotient_abs_bound (speedSquared vL) 2 2 30 (by norm_num) (by norm_num) hsL
    have he := abs_sub (1/(2*bL)) (speedSquared vL/2)
    norm_num1 at hi hs
    dsimp [thermal0]
    linarith only [he,hi,hs]
  have henergy : |(mass*thermal+vb 0*mom 0+vb 1*mom 1+vb 2*mom 2)-
      (mass0*thermal0+vL 0*mom0 0+vL 1*mom0 1+vL 2*mom0 2)| ≤ 63079178*h := by
    have ht := near_mul mass thermal mass0 thermal0 h 24 31 206 1050500 hmass hthermal0 hmassnear hthermalnear
    have hv (i : Fin 3) := near_mul (vb i) (mom i) (vL i) (mom0 i) h 6 208 50 2101644
      (hvb i) (hmom0 i) (hvbn i) (hmomnear i)
    norm_num at ht hv
    have he := near_add _ _ _ _ h ((25218386+12620264)+12620264) 12620264
      (near_add _ _ _ _ h (25218386+12620264) 12620264
        (near_add _ _ _ _ h 25218386 12620264 ht (hv 0)) (hv 1)) (hv 2)
    norm_num at he
    exact he
  simp only [parameterFlux,fluxWithMeans,diagonal,average_diagonal]
  fin_cases j
  · change |mass-mass0| ≤ _
    linarith only [hmassnear,hh]
  · change |mom 0-mom0 0| ≤ _
    linarith only [hmomnear 0,hh]
  · change |mom 1-mom0 1| ≤ _
    linarith only [hmomnear 1,hh]
  · change |mom 2-mom0 2| ≤ _
    linarith only [hmomnear 2,hh]
  · change |(mass*thermal+vb 0*mom 0+vb 1*mom 1+vb 2*mom 2)-
        (mass0*thermal0+vL 0*mom0 0+vL 1*mom0 1+vL 2*mom0 2)| ≤ _
    linarith only [henergy,hh]

theorem flux_component_consistency_bound (u v : State) (hu : u ∈ region) (hv : v ∈ region)
    (d : Fin 3) (j : Fin 5) :
    |ecFlux u v d j-EulerAdmissible.eulerFlux u d j| ≤ 100000000*Real.sqrt (sizeSquared (v-u)) := by
  let h := Real.sqrt (sizeSquared (v-u))
  have hh : 0 ≤ h := Real.sqrt_nonneg _
  have hsq : h^2=sizeSquared (v-u) := Real.sq_sqrt (size_nonnegative (v-u))
  have hnear (j : Fin 5) : |v j-u j| ≤ h := by
    apply abs_le_of_sq_le_sq _ hh
    rw [hsq]
    exact EulerPhysicalFluxBounds.component_square_bound (v-u) j
  have he := parameter_flux_component_bound (u 0) (v 0) (beta u) (beta v)
    (EulerAdmissible.fromVelocity u) (EulerAdmissible.fromVelocity v) d
    (physical_parameter_region u hu) (physical_parameter_region v hv) h hh (hnear 0)
    (beta_difference_bound u v hu hv h hh hnear)
    (fun i => velocity_difference_bound u v hu hv h hnear i) j
  rw [← canonical_flux_consistency u (region_admissible u hu) d]
  exact he

theorem flux_consistency_bound (u v : State) (hu : u ∈ region) (hv : v ∈ region) (d : Fin 3) :
    sizeSquared (ecFlux u v d-EulerAdmissible.eulerFlux u d) ≤
      (300000000 : ℝ)^2*sizeSquared (v-u) := by
  have hh := size_from_components (ecFlux u v d-EulerAdmissible.eulerFlux u d)
    (100000000*Real.sqrt (sizeSquared (v-u))) (by positivity)
    (fun j => flux_component_consistency_bound u v hu hv d j)
  have hs := Real.sq_sqrt (size_nonnegative (v-u))
  nlinarith [size_nonnegative (v-u)]

theorem flux_with_means_swap (rL rR bL bR lr lb : ℝ) (vL vR : Vec) (d : Fin 3) :
    fluxWithMeans rL rR bL bR lr lb vL vR d=fluxWithMeans rR rL bR bL lr lb vR vL d := by
  have hr : average rL rR=average rR rL := by dsimp [average]; ring
  have hb : average bL bR=average bR bL := by dsimp [average]; ring
  have hv (i : Fin 3) : average (vL i) (vR i)=average (vR i) (vL i) := by dsimp [average]; ring
  have hs : average (speedSquared vL) (speedSquared vR)=average (speedSquared vR) (speedSquared vL) := by
    dsimp [average]
    ring
  simp only [fluxWithMeans,hr,hb,hv,hs]

theorem flux_symmetric (u v : State) (hu : EulerAdmissible.Admissible u)
    (hv : EulerAdmissible.Admissible v) (d : Fin 3) : ecFlux u v d=ecFlux v u d := by
  dsimp only [ecFlux,parameterFlux]
  rw [symmetric (u 0) (v 0) hu.1 hv.1,
    symmetric (beta u) (beta v) (beta_positive u hu) (beta_positive v hv)]
  exact flux_with_means_swap _ _ _ _ _ _ _ _ d

theorem flux_consistency_bound_right (u v : State) (hu : u ∈ region) (hv : v ∈ region) (d : Fin 3) :
    sizeSquared (ecFlux u v d-EulerAdmissible.eulerFlux v d) ≤
      (300000000 : ℝ)^2*sizeSquared (v-u) := by
  rw [flux_symmetric u v (region_admissible u hu) (region_admissible v hv),size_sub_comm v u]
  exact flux_consistency_bound v u hv hu d

end EulerECFluxBounds
