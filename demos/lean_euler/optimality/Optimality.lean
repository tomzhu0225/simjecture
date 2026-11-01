import Mathlib.Data.Finset.Card

noncomputable section
namespace Optimality
open Recovery Grid

-- The lower bound applies to arbitrary adaptive sampling, not a prespecified
-- finite set of candidate solvers.
theorem at_most_one_cell (b : Recovery.Space → ℝ)
    (hz : ∀ x, 1/2 ≤ ‖x‖ → b x = 0)
    (n : ℕ) (hn : 0 < n) (q : Recovery.Space) (i j : Grid.Cell n)
    (hi : b ((n:ℝ) • (q-Grid.center n i)) ≠ 0)
    (hj : b ((n:ℝ) • (q-Grid.center n j)) ≠ 0) : i = j := by
  have hp : (0:ℝ) < n := by exact_mod_cast hn
  have normi : ‖(n:ℝ) • (q-Grid.center n i)‖ < 1/2 := lt_of_not_ge (fun h => hi (hz _ h))
  have normj : ‖(n:ℝ) • (q-Grid.center n j)‖ < 1/2 := lt_of_not_ge (fun h => hj (hz _ h))
  rw [norm_smul,Real.norm_eq_abs,abs_of_pos hp] at normi normj
  by_contra hne
  have sep := Grid.centers_separated n hn i j hne
  have tri := norm_sub_le_norm_sub_add_norm_sub (Grid.center n i) q (Grid.center n j)
  rw [norm_sub_rev (Grid.center n i) q] at tri
  have hscale : (n:ℝ)*(1/(n:ℝ)) = 1 := by field_simp
  nlinarith

theorem exists_unqueried_cell (b : Recovery.Space → ℝ)
    (hz : ∀ x, 1/2 ≤ ‖x‖ → b x = 0)
    (n : ℕ) (hn : 0 < n) (queries : List Recovery.Space)
    (small : queries.length < n^3) :
    ∃ i : Grid.Cell n, ∀ q ∈ queries, b ((n:ℝ) • (q-Grid.center n i)) = 0 := by
  classical
  let fallback : Grid.Cell n := fun _ => ⟨0,hn⟩
  let select (q : Recovery.Space) : Grid.Cell n :=
    if h : ∃ i : Grid.Cell n, b ((n:ℝ) • (q-Grid.center n i)) ≠ 0 then h.choose else fallback
  let observed : Finset (Grid.Cell n) := queries.toFinset.image select
  have hc : observed.card < (Finset.univ : Finset (Grid.Cell n)).card := by
    calc
      observed.card ≤ queries.toFinset.card := Finset.card_image_le
      _ ≤ queries.length := List.toFinset_card_le queries
      _ < n^3 := small
      _ = (Finset.univ : Finset (Grid.Cell n)).card := by simp
  obtain ⟨i,_,hi⟩ := Finset.exists_mem_notMem_of_card_lt_card hc
  refine ⟨i,?_⟩
  intro q hq
  by_contra hneq
  have hex : ∃ j : Grid.Cell n, b ((n:ℝ) • (q-Grid.center n j)) ≠ 0 := ⟨i,hneq⟩
  have hselect : b ((n:ℝ) • (q-Grid.center n (select q))) ≠ 0 := by
    dsimp [select]
    rw [dif_pos hex]
    exact hex.choose_spec
  have heq : select q = i := at_most_one_cell b hz n hn q _ i hselect hneq
  apply hi
  exact Finset.mem_image.mpr ⟨q,List.mem_toFinset.mpr hq,heq⟩

-- A density-recovery specification is necessary for every full-state Euler
-- approximation because density is its first conserved component.
def AccurateDensity (L eps : ℝ) (a : Recovery.QueryTree (Recovery.Space → ℝ)) : Prop :=
  ∀ f, Recovery.Admissible L f → ∀ x, Recovery.InCube x → |a.run f x-f x| ≤ eps

theorem adaptive_query_lower_bound (b : Recovery.Space → ℝ) (K L eps : ℝ)
    (hb : ContDiff ℝ 1 b) (hbounds : ∀ x, 0 ≤ b x ∧ b x ≤ 1) (h0 : b 0 = 1)
    (hz : ∀ x, 1/2 ≤ ‖x‖ → b x = 0)
    (hlip : ∀ x y, |b x-b y| ≤ K*‖x-y‖)
    (heps : 0 < eps) (hepsmax : eps ≤ 1/4)
    (n : ℕ) (hn : 0 < n) (hbudget : 2*eps*K*(n:ℝ) ≤ L)
    (a : Recovery.QueryTree (Recovery.Space → ℝ)) (correct : AccurateDensity L eps a) :
    n^3 ≤ (a.queries (fun _ => 3/2)).length := by
  by_contra hnq
  obtain ⟨i,hi⟩ := exists_unqueried_cell b hz n hn (a.queries (fun _ => 3/2)) (by omega)
  let fplus := Recovery.perturb b (2*eps) n (Grid.center n i)
  let fminus := Recovery.perturb b (-2*eps) n (Grid.center n i)
  have hplus : Recovery.Admissible L fplus := by
    apply Recovery.perturb_admissible b K L (2*eps) n (Grid.center n i) hb hbounds hlip
    · positivity
    · rw [abs_of_pos (by positivity)]
      linarith
    · simpa [abs_of_pos (by positivity : 0 < 2*eps)] using hbudget
  have hminus : Recovery.Admissible L fminus := by
    apply Recovery.perturb_admissible b K L (-2*eps) n (Grid.center n i) hb hbounds hlip
    · positivity
    · rw [abs_of_neg (by linarith)]
      linarith
    · rw [abs_of_neg (by linarith)]
      convert hbudget using 1; ring
  have ep : a.run fplus = a.run (fun _ => 3/2) := by
    apply Recovery.adaptive_indistinguishability
    intro q hq
    simp [fplus,Recovery.perturb,hi q hq]
  have em : a.run fminus = a.run (fun _ => 3/2) := by
    apply Recovery.adaptive_indistinguishability
    intro q hq
    simp [fminus,Recovery.perturb,hi q hq]
  have hp := correct fplus hplus (Grid.center n i) (Grid.center_in_cube n hn i)
  have hm := correct fminus hminus (Grid.center n i) (Grid.center_in_cube n hn i)
  rw [ep] at hp
  rw [em] at hm
  simp [fplus,fminus,Recovery.perturb,h0] at hp hm
  have hp' := abs_le.mp hp
  have hm' := abs_le.mp hm
  linarith

-- The reconstructed velocity is exact. Density approximation propagates to
-- all five conserved components with a uniform factor at most 3/2.
theorem conserved_error (r s : ℝ) (a : Recovery.Space) (ha : Recovery.InCube a) :
    ‖ShearEuler.conserved r ![a 1,a 2,1]-ShearEuler.conserved s ![a 1,a 2,1]‖ ≤
      (3/2)*|r-s| := by
  have h1 := ha 1
  have h2 := ha 2
  have hr := abs_nonneg (r-s)
  have hk0 : 0 ≤ (a 1^2+a 2^2+1)/2 := by positivity
  have hk1 : (a 1^2+a 2^2+1)/2 ≤ 3/2 := by nlinarith [sq_nonneg (a 1-1),sq_nonneg (a 2-1)]
  apply (pi_norm_le_iff_of_nonneg (by positivity)).mpr
  intro i
  fin_cases i <;> simp [ShearEuler.conserved,ShearEuler.kinetic,Real.norm_eq_abs]
  · nlinarith
  · rw [← sub_mul,abs_mul,abs_of_nonneg h1.1]
    nlinarith
  · rw [← sub_mul,abs_mul,abs_of_nonneg h2.1]
    nlinarith
  · nlinarith
  · rw [← sub_mul,abs_mul,abs_of_nonneg hk0]
    nlinarith

def samples (f : Recovery.Space → ℝ) (n : ℕ) : Grid.Cell n → ℝ := fun i => f (Grid.center n i)
def reconstruct (n : ℕ) (hn : 0 < n) (data : Grid.Cell n → ℝ) (t : ℝ) (x : Recovery.Space) : ShearEuler.State :=
  ShearEuler.conserved (data (Grid.locate n hn (ShearEuler.invFlow t x))) (ShearEuler.velocity t x)

theorem uniform_full_state_error (f : Recovery.Space → ℝ) (L : ℝ) (hL : 0 ≤ L)
    (hf : Recovery.Admissible L f) (n : ℕ) (hn : 0 < n) (t : ℝ) (a : Recovery.Space)
    (ha : Recovery.InCube a) :
    ‖reconstruct n hn (samples f n) t (ShearEuler.flow t a)-
      ShearEuler.solution f t (ShearEuler.flow t a)‖ ≤ 3*L/(4*(n:ℝ)) := by
  have hc := Grid.center_covers_cube n hn a ha
  have hd := hf.2.2 (Grid.center n (Grid.locate n hn a)) a
  rw [norm_sub_rev] at hd
  have hd' : |f (Grid.center n (Grid.locate n hn a))-f a| ≤ L/(2*(n:ℝ)) := by
    calc
      _ ≤ L*‖a-Grid.center n (Grid.locate n hn a)‖ := hd
      _ ≤ L*(1/(2*(n:ℝ))) := mul_le_mul_of_nonneg_left hc hL
      _ = L/(2*(n:ℝ)) := by ring
  simp only [reconstruct,samples,ShearEuler.solution,ShearEuler.density,
    ShearEuler.inverse_flow,ShearEuler.material_velocity]
  calc
    _ ≤ (3/2)*|f (Grid.center n (Grid.locate n hn a))-f a| := conserved_error _ _ a ha
    _ ≤ (3/2)*(L/(2*(n:ℝ))) := mul_le_mul_of_nonneg_left hd' (by norm_num)
    _ = 3*L/(4*(n:ℝ)) := by ring

-- The density lower bound above is unconditional once the fixed bump supplied
-- by Mathlib has been instantiated.
theorem exists_lower_bound_constant : ∃ K : ℝ, 1 ≤ K ∧
    ∀ (L eps : ℝ) (n : ℕ), 0 < eps → eps ≤ 1/4 → 0 < n → 2*eps*K*(n:ℝ) ≤ L →
    ∀ a : Recovery.QueryTree (Recovery.Space → ℝ), AccurateDensity L eps a →
      n^3 ≤ (a.queries (fun _ => 3/2)).length := by
  obtain ⟨b,K,hK,hb,hbounds,h0,hz,hlip⟩ := Recovery.exists_base_bump
  refine ⟨K,hK,?_⟩
  intro L eps n he hmax hn hbudget a hcorrect
  exact adaptive_query_lower_bound b K L eps hb hbounds h0 hz hlip he hmax n hn hbudget a hcorrect

def resolution (L eps : ℝ) : ℕ := ⌈3*L/(4*eps)⌉₊

theorem resolution_positive (L eps : ℝ) (hL : 0 < L) (he : 0 < eps) : 0 < resolution L eps := by
  apply Nat.one_le_ceil_iff.mpr
  positivity

theorem accuracy_at_tolerance (f : Recovery.Space → ℝ) (L eps : ℝ)
    (hL : 0 < L) (he : 0 < eps) (hf : Recovery.Admissible L f)
    (t : ℝ) (a : Recovery.Space) (ha : Recovery.InCube a) :
    ‖reconstruct (resolution L eps) (resolution_positive L eps hL he)
      (samples f (resolution L eps)) t (ShearEuler.flow t a)-
      ShearEuler.solution f t (ShearEuler.flow t a)‖ ≤ eps := by
  apply (uniform_full_state_error f L hL.le hf _ (resolution_positive L eps hL he) t a ha).trans
  have hceil := Nat.le_ceil (3*L/(4*eps))
  have hn : (0:ℝ) < resolution L eps := by exact_mod_cast resolution_positive L eps hL he
  apply (div_le_iff₀ (by positivity : (0:ℝ) < 4*(resolution L eps:ℝ))).mpr
  have hh := (div_le_iff₀ (by positivity : (0:ℝ) < 4*eps)).mp hceil
  change 3*L ≤ eps*(4*(⌈3*L/(4*eps)⌉₊:ℝ))
  nlinarith

theorem resolution_work_upper (L eps : ℝ) (hL : 0 < L) (he : 0 < eps) (heL : eps ≤ L) :
    ((resolution L eps)^3 : ℝ) ≤ (2*L/eps)^3 := by
  have hc := (Nat.ceil_lt_add_one (by positivity : (0:ℝ) ≤ 3*L/(4*eps))).le
  have hn : (resolution L eps:ℝ) ≤ 2*L/eps := by
    dsimp [resolution]
    apply hc.trans
    apply (le_div_iff₀ he).mpr
    have hcancel : (3*L/(4*eps))*eps = 3*L/4 := by field_simp
    nlinarith
  exact pow_le_pow_left₀ (by positivity) hn 3

theorem optimal_query_scaling : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps : ℝ, 1 ≤ L → 0 < eps → eps ≤ 1/(4*K) →
    ∀ a : Recovery.QueryTree (Recovery.Space → ℝ), AccurateDensity L eps a →
      (L/(4*K*eps))^3 ≤ ((a.queries (fun _ => 3/2)).length:ℝ) := by
  obtain ⟨K,hK,lower⟩ := exists_lower_bound_constant
  refine ⟨K,hK,?_⟩
  intro L eps hL he hsmall a hcorrect
  have hKp : 0 < K := by linarith
  have hLp : 0 < L := by linarith
  have hprod : 4*K*eps ≤ 1 := by
    have hh := (le_div_iff₀ (by positivity : 0 < 4*K)).mp hsmall
    nlinarith
  have hem : eps ≤ 1/4 := by nlinarith
  let x : ℝ := L/(2*K*eps)
  have hx2 : 2 ≤ x := by
    apply (le_div_iff₀ (by positivity : 0 < 2*K*eps)).mpr
    nlinarith
  let n := ⌊x⌋₊
  have hn : 0 < n := by
    have hh : 1 ≤ n := (Nat.one_le_floor_iff x).mpr (by linarith)
    omega
  have hfloor : (n:ℝ) ≤ x := Nat.floor_le (by linarith)
  have hfloor2 : x < (n:ℝ)+1 := Nat.lt_floor_add_one x
  have hnlarge : L/(4*K*eps) ≤ (n:ℝ) := by
    have heq : L/(4*K*eps) = x/2 := by dsimp [x]; ring
    rw [heq]
    linarith
  have hbudget : 2*eps*K*(n:ℝ) ≤ L := by
    have hh := (le_div_iff₀ (by positivity : 0 < 2*K*eps)).mp hfloor
    nlinarith
  have hqueries := lower L eps n he hem hn hbudget a hcorrect
  have hqueriesR : (n:ℝ)^3 ≤ ((a.queries (fun _ => 3/2)).length:ℝ) := by exact_mod_cast hqueries
  exact (pow_le_pow_left₀ (by positivity) hnlarge 3).trans hqueriesR

def samplingAlgorithm (n : ℕ) : Recovery.QueryTree (Grid.Cell n → ℝ) :=
  Recovery.tabulate (Grid.cells n) (Grid.center n)

theorem sampling_values (n : ℕ) (f : Recovery.Space → ℝ) :
    (samplingAlgorithm n).run f = samples f n := by
  funext i
  exact Recovery.tabulate_values (Grid.cells n) (Grid.center n) f i (Grid.mem_cells n i)

theorem sampling_queries (n : ℕ) (f : Recovery.Space → ℝ) :
    ((samplingAlgorithm n).queries f).length = n^3 := by
  simp [samplingAlgorithm,Recovery.tabulate_queries,Grid.cells_length]

def eulerAlgorithm (n : ℕ) (hn : 0 < n) (t : ℝ) : Recovery.QueryTree (Recovery.Space → ShearEuler.State) :=
  (samplingAlgorithm n).map (fun data => reconstruct n hn data t)

def AccurateEuler (t L eps : ℝ) (a : Recovery.QueryTree (Recovery.Space → ShearEuler.State)) : Prop :=
  ∀ f, Recovery.Admissible L f → ∀ x, Recovery.InCube x →
    ‖a.run f (ShearEuler.flow t x)-ShearEuler.solution f t (ShearEuler.flow t x)‖ ≤ eps

theorem euler_algorithm_accurate (L eps t : ℝ) (hL : 0 < L) (he : 0 < eps) :
    AccurateEuler t L eps (eulerAlgorithm (resolution L eps) (resolution_positive L eps hL he) t) := by
  intro f hf x hx
  simp only [eulerAlgorithm,Recovery.QueryTree.run_map,sampling_values]
  exact accuracy_at_tolerance f L eps hL he hf t x hx

theorem euler_algorithm_queries (n : ℕ) (hn : 0 < n) (t : ℝ) (f : Recovery.Space → ℝ) :
    ((eulerAlgorithm n hn t).queries f).length = n^3 := by
  simp only [eulerAlgorithm,Recovery.QueryTree.queries_map,sampling_queries]

def densityReduction (t : ℝ) (a : Recovery.QueryTree (Recovery.Space → ShearEuler.State)) :
    Recovery.QueryTree (Recovery.Space → ℝ) :=
  a.map (fun output x => output (ShearEuler.flow t x) 0)

theorem euler_implies_density (t L eps : ℝ) (a : Recovery.QueryTree (Recovery.Space → ShearEuler.State))
    (hcorrect : AccurateEuler t L eps a) : AccurateDensity L eps (densityReduction t a) := by
  intro f hf x hx
  have h := hcorrect f hf x hx
  have hcoord := norm_le_pi_norm (a.run f (ShearEuler.flow t x)-ShearEuler.solution f t (ShearEuler.flow t x)) 0
  have hh := hcoord.trans h
  simpa [densityReduction,Recovery.QueryTree.run_map,ShearEuler.solution,ShearEuler.conserved,
    ShearEuler.density,ShearEuler.inverse_flow,Real.norm_eq_abs] using hh

theorem optimal_euler_query_scaling : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps t : ℝ, 1 ≤ L → 0 < eps → eps ≤ 1/(4*K) →
    ∀ a : Recovery.QueryTree (Recovery.Space → ShearEuler.State), AccurateEuler t L eps a →
      (L/(4*K*eps))^3 ≤ ((a.queries (fun _ => 3/2)).length:ℝ) := by
  obtain ⟨K,hK,lower⟩ := optimal_query_scaling
  refine ⟨K,hK,?_⟩
  intro L eps t hL he hsmall a hcorrect
  have h := lower L eps hL he hsmall (densityReduction t a) (euler_implies_density t L eps a hcorrect)
  simpa only [densityReduction,Recovery.QueryTree.queries_map] using h
end Optimality
