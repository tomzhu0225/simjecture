-- A general deterministic adaptive oracle machine. Unbounded internal state
-- and infinite paths are allowed; only valid inputs must terminate.
noncomputable section
namespace Machines
open Recovery Grid Optimality

inductive Action (S O : Type) where
  | done : O → Action S O
  | ask : Recovery.Space → (ℝ → S) → Action S O

structure Machine (S O : Type) where
  step : S → Action S O

inductive Executes {S O : Type} (m : Machine S O) (f : Recovery.Space → ℝ) : S → List Recovery.Space → O → Prop where
  | done {s o} : m.step s = .done o → Executes m f s [] o
  | ask {s q next qs o} : m.step s = .ask q next →
      Executes m f (next (f q)) qs o → Executes m f s (q::qs) o

theorem same_answers {S O : Type} (m : Machine S O) (f g : Recovery.Space → ℝ)
    {s : S} {qs : List Recovery.Space} {o : O} (h : Executes m f s qs o)
    (same : ∀ q ∈ qs, g q=f q) : Executes m g s qs o := by
  induction h with
  | done h => exact Executes.done h
  | @ask s q next qs o h tail ih =>
    apply Executes.ask h
    have hq := same q (by simp)
    rw [hq]
    apply ih
    intro x hx
    exact same x (by simp [hx])

def Correct {S : Type} (m : Machine S (Recovery.Space → ShearEuler.State)) (s : S)
    (t L eps : ℝ) : Prop :=
  (∀ f, Recovery.Admissible L f → ∃ qs o, Executes m f s qs o) ∧
  (∀ f, Recovery.Admissible L f → ∀ qs o, Executes m f s qs o → ∀ x, Recovery.InCube x →
    ‖o (ShearEuler.flow t x)-ShearEuler.solution f t (ShearEuler.flow t x)‖ ≤ eps)

def ofTree {O : Type} : Machine (Recovery.QueryTree O) O where
  step a := match a with
    | .done o => .done o
    | .ask q next => .ask q next

theorem tree_executes {O : Type} (a : Recovery.QueryTree O) (f : Recovery.Space → ℝ) :
    Executes ofTree f a (a.queries f) (a.run f) := by
  induction a with
  | done o => exact Executes.done rfl
  | ask q next ih => exact Executes.ask rfl (ih (f q))

theorem tree_execution_output {O : Type} (a : Recovery.QueryTree O) (f : Recovery.Space → ℝ)
    (qs : List Recovery.Space) (o : O) (h : Executes ofTree f a qs o) : o = a.run f := by
  induction h with
  | @done s o hs =>
    cases s with
    | done value => simpa [ofTree,QueryTree.run,Action.done.injEq] using hs.symm
    | ask q next => simp [ofTree] at hs
  | @ask s q next qs o hs ht ih =>
    cases s with
    | done value => simp [ofTree] at hs
    | ask p follow =>
      have hh : p=q ∧ follow=next := by simpa [ofTree,Action.ask.injEq] using hs
      rcases hh with ⟨rfl,rfl⟩
      exact ih

theorem tree_correct (a : Recovery.QueryTree (Recovery.Space → ShearEuler.State)) (t L eps : ℝ)
    (h : Optimality.AccurateEuler t L eps a) : Correct ofTree a t L eps := by
  constructor
  · intro f hf
    exact ⟨a.queries f,a.run f,tree_executes a f⟩
  · intro f hf qs o he x hx
    rw [tree_execution_output a f qs o he]
    exact h f hf x hx

theorem density_component_error (f : Recovery.Space → ℝ) (o : Recovery.Space → ShearEuler.State)
    (t eps : ℝ) (x : Recovery.Space)
    (h : ‖o (ShearEuler.flow t x)-ShearEuler.solution f t (ShearEuler.flow t x)‖ ≤ eps) :
    |o (ShearEuler.flow t x) 0-f x| ≤ eps := by
  have hc := (norm_le_pi_norm (o (ShearEuler.flow t x)-ShearEuler.solution f t (ShearEuler.flow t x)) 0).trans h
  simpa [ShearEuler.solution,ShearEuler.conserved,ShearEuler.density,ShearEuler.inverse_flow,Real.norm_eq_abs] using hc

theorem machine_query_lower {S : Type} (m : Machine S (Recovery.Space → ShearEuler.State)) (s : S)
    (t L eps K : ℝ) (b : Recovery.Space → ℝ)
    (hb : ContDiff ℝ 1 b) (hbounds : ∀ x, 0 ≤ b x ∧ b x ≤ 1) (h0 : b 0 = 1)
    (hz : ∀ x, 1/2 ≤ ‖x‖ → b x = 0) (hlip : ∀ x y, |b x-b y| ≤ K*‖x-y‖)
    (heps : 0 < eps) (hepsmax : eps ≤ 1/4) (n : ℕ) (hn : 0 < n)
    (hbudget : 2*eps*K*(n:ℝ) ≤ L) (correct : Correct m s t L eps)
    (qs : List Recovery.Space) (o : Recovery.Space → ShearEuler.State)
    (run : Executes m (fun _ => 3/2) s qs o) : n^3 ≤ qs.length := by
  by_contra small
  obtain ⟨i,hi⟩ := Optimality.exists_unqueried_cell b hz n hn qs (by omega)
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
  have ep : Executes m fplus s qs o := by
    apply same_answers m (fun _ => 3/2) fplus run
    intro q hq
    simp [fplus,Recovery.perturb,hi q hq]
  have em : Executes m fminus s qs o := by
    apply same_answers m (fun _ => 3/2) fminus run
    intro q hq
    simp [fminus,Recovery.perturb,hi q hq]
  have hp := density_component_error fplus o t eps _
    (correct.2 fplus hplus qs o ep _ (Grid.center_in_cube n hn i))
  have hm := density_component_error fminus o t eps _
    (correct.2 fminus hminus qs o em _ (Grid.center_in_cube n hn i))
  simp [fplus,fminus,Recovery.perturb,h0] at hp hm
  have hp' := abs_le.mp hp
  have hm' := abs_le.mp hm
  linarith

theorem general_machine_work_lower : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps t : ℝ, 1 ≤ L → 0 < eps → eps ≤ 1/(4*K) →
    ∀ (S : Type) (m : Machine S (Recovery.Space → ShearEuler.State)) (s : S), Correct m s t L eps →
    ∀ qs o, Executes m (fun _ => 3/2) s qs o → ∀ additional : ℕ,
      (L/(4*K*eps))^3 ≤ ((qs.length+additional):ℝ) := by
  obtain ⟨b,K,hK,hb,hbounds,h0,hz,hlip⟩ := Recovery.exists_base_bump
  refine ⟨K,hK,?_⟩
  intro L eps t hL he hsmall S m s hcorrect qs o hrun additional
  have hKp : 0 < K := by linarith
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
  have hqueries := machine_query_lower m s t L eps K b hb hbounds h0 hz hlip he hem n hn hbudget hcorrect qs o hrun
  have hqueriesR : (n:ℝ)^3 ≤ (qs.length:ℝ) := by exact_mod_cast hqueries
  calc
    _ ≤ (n:ℝ)^3 := pow_le_pow_left₀ (by positivity) hnlarge 3
    _ ≤ (qs.length:ℝ) := hqueriesR
    _ ≤ ((qs.length+additional):ℝ) := by exact_mod_cast Nat.le_add_right qs.length additional

theorem certified_general_optimality : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps t : ℝ, ∀ hL : 1 ≤ L, ∀ he : 0 < eps, eps ≤ 1/(4*K) →
    let n := Optimality.resolution L eps
    let hn := Optimality.resolution_positive L eps (lt_of_lt_of_le (by norm_num) hL) he
    Correct ofTree (Optimality.eulerAlgorithm n hn t) t L eps ∧
    (∀ f : Recovery.Space → ℝ, ((Work.toleranceProgram f L eps).work:ℝ) ≤ 312*(L/eps)^3) ∧
    (∀ (S : Type) (m : Machine S (Recovery.Space → ShearEuler.State)) (s : S), Correct m s t L eps →
      ∃ qs o, Executes m (fun _ => 3/2) s qs o ∧
        ∀ additional : ℕ, (L/(4*K*eps))^3 ≤ ((qs.length+additional):ℝ)) := by
  obtain ⟨K,hK,lower⟩ := general_machine_work_lower
  refine ⟨K,hK,?_⟩
  intro L eps t hL he hsmall
  have hLp : 0 < L := by linarith
  have hKp : 0 < K := by linarith
  have heL : eps ≤ L := by
    have hh := (le_div_iff₀ (by positivity : 0 < 4*K)).mp hsmall
    nlinarith
  refine ⟨tree_correct _ t L eps (Optimality.euler_algorithm_accurate L eps t hLp he),?_,?_⟩
  · intro f
    exact Work.total_work_upper f L eps hLp he heL
  · intro S m s hcorrect
    obtain ⟨qs,o,hrun⟩ := hcorrect.1 (fun _ => 3/2) (Certificate.family_nonempty L hLp.le)
    exact ⟨qs,o,hrun,fun additional => lower L eps t hL he hsmall S m s hcorrect qs o hrun additional⟩
end Machines
