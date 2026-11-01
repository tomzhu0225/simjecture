import Mathlib.Analysis.Calculus.BumpFunction.InnerProduct
import Mathlib.Analysis.Calculus.ContDiff.RCLike
import Mathlib.Data.Fintype.Pi
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.FunProp
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.FinCases
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Ring

noncomputable section
open scoped Topology ContDiff
namespace Recovery
abbrev Space := Fin 3 → ℝ

def InCube (x : Space) : Prop := ∀ d, 0 ≤ x d ∧ x d ≤ 1

def Admissible (L : ℝ) (f : Space → ℝ) : Prop :=
  ContDiff ℝ 1 f ∧ (∀ x, 1 ≤ f x ∧ f x ≤ 2) ∧
    (∀ x y, |f x-f y| ≤ L*‖x-y‖)

-- This supplies the hard inputs constructively from the library's proved
-- existence theorem. The Lipschitz constant is fixed before grid refinement.
theorem exists_base_bump : ∃ (b : Space → ℝ) (K : ℝ),
    1 ≤ K ∧ ContDiff ℝ 1 b ∧ (∀ x, 0 ≤ b x ∧ b x ≤ 1) ∧ b 0 = 1 ∧
    (∀ x, 1/2 ≤ ‖x‖ → b x = 0) ∧
    (∀ x y, |b x-b y| ≤ K*‖x-y‖) := by
  let base : ContDiffBump (0 : ℝ) :=
    { rIn := 1/4, rOut := 1/2, rIn_pos := by norm_num, rIn_lt_rOut := by norm_num }
  let b : Space → ℝ := fun x => base (x 0)*base (x 1)*base (x 2)
  have hb : ∀ x, 0 ≤ b x ∧ b x ≤ 1 := by
    intro x
    have h01 : base (x 0)*base (x 1) ≤ 1 := by
      simpa using mul_le_mul (base.le_one (x := x 0)) (base.le_one (x := x 1)) base.nonneg (by norm_num : (0:ℝ) ≤ 1)
    have h012 : b x ≤ 1 := by
      simpa [b] using mul_le_mul h01 (base.le_one (x := x 2)) base.nonneg (by norm_num : (0:ℝ) ≤ 1)
    exact ⟨mul_nonneg (mul_nonneg base.nonneg base.nonneg) base.nonneg,h012⟩
  have hd : ContDiff ℝ 1 b := by
    have hbase : ContDiff ℝ 1 base := base.contDiff
    dsimp [b]
    fun_prop
  have hz : ∀ x, 1/2 ≤ ‖x‖ → b x = 0 := by
    intro x hx
    have hnot : ¬ ∀ d : Fin 3, ‖x d‖ < 1/2 := by
      intro h
      have hh := (pi_norm_lt_iff (by norm_num : (0:ℝ) < 1/2)).mpr h
      linarith
    obtain ⟨d,hd⟩ := not_forall.mp hnot
    have hzero : base (x d) = 0 := by
      apply base.zero_of_le_dist
      simpa [base,dist_zero_right] using le_of_not_gt hd
    fin_cases d
    · have hh : base (x 0) = 0 := hzero
      simp [b,hh]
    · have hh : base (x 1) = 0 := hzero
      simp [b,hh]
    · have hh : base (x 2) = 0 := hzero
      simp [b,hh]
  have hs : Function.support b ⊆ Metric.closedBall 0 (1/2) := by
    intro x hx
    have hh : ‖x‖ < 1/2 := lt_of_not_ge (fun h => hx (hz x h))
    simpa only [Metric.mem_closedBall,dist_zero_right] using hh.le
  have hc : HasCompactSupport b :=
    (isCompact_closedBall (0 : Space) (1/2)).of_isClosed_subset isClosed_closure (closure_minimal hs Metric.isClosed_closedBall)
  obtain ⟨K, hK⟩ := ContDiff.lipschitzWith_of_hasCompactSupport hc hd (by simp)
  refine ⟨b, max (K:ℝ) 1, le_max_right _ _, hd, hb, ?_, hz, ?_⟩
  · have hbase : base 0 = 1 := base.one_of_mem_closedBall (by simp [base])
    simp [b,hbase]
  · intro x y
    calc
      |b x-b y| ≤ (K:ℝ)*‖x-y‖ := by simpa only [Real.norm_eq_abs] using hK.norm_sub_le x y
      _ ≤ max (K:ℝ) 1*‖x-y‖ := mul_le_mul_of_nonneg_right (le_max_left _ _) (norm_nonneg _)

-- A decision tree permits adaptive real-valued queries and arbitrary outputs.
-- Every path terminates; no input formula or hidden density oracle is in a leaf.
inductive QueryTree (Output : Type) where
  | done : Output → QueryTree Output
  | ask : Space → (ℝ → QueryTree Output) → QueryTree Output

def QueryTree.run {O : Type} (a : QueryTree O) (f : Space → ℝ) : O :=
  match a with
  | .done o => o
  | .ask q next => (next (f q)).run f

def QueryTree.queries {O : Type} (a : QueryTree O) (f : Space → ℝ) : List Space :=
  match a with
  | .done _ => []
  | .ask q next => q :: (next (f q)).queries f

theorem adaptive_indistinguishability {O : Type} (a : QueryTree O) (f g : Space → ℝ)
    (same : ∀ q ∈ a.queries f, g q = f q) : a.run g = a.run f := by
  induction a with
  | done o => rfl
  | ask q next ih =>
    have hq : g q = f q := same q (by simp [QueryTree.queries])
    simp only [QueryTree.run,hq]
    apply ih (f q)
    intro p hp
    exact same p (by simp [QueryTree.queries,hp])

def QueryTree.map {O P : Type} (a : QueryTree O) (f : O → P) : QueryTree P :=
  match a with
  | .done o => .done (f o)
  | .ask q next => .ask q (fun y => (next y).map f)

theorem QueryTree.run_map {O P : Type} (a : QueryTree O) (g : O → P) (f : Space → ℝ) :
    (a.map g).run f = g (a.run f) := by
  induction a with
  | done o => rfl
  | ask q next ih => exact ih (f q)

theorem QueryTree.queries_map {O P : Type} (a : QueryTree O) (g : O → P) (f : Space → ℝ) :
    (a.map g).queries f = a.queries f := by
  induction a with
  | done o => rfl
  | ask q next ih => simp [QueryTree.map,QueryTree.queries,ih]

def tabulate {I : Type} [DecidableEq I] (qs : List I) (loc : I → Space) : QueryTree (I → ℝ) :=
  match qs with
  | [] => .done (fun _ => 0)
  | i::rest => .ask (loc i) (fun y => (tabulate rest loc).map (fun data => Function.update data i y))

theorem tabulate_queries {I : Type} [DecidableEq I] (qs : List I) (loc : I → Space) (f : Space → ℝ) :
    (tabulate qs loc).queries f = qs.map loc := by
  induction qs with
  | nil => rfl
  | cons i rest ih => simp [tabulate,QueryTree.queries,QueryTree.queries_map,ih]

theorem tabulate_values {I : Type} [DecidableEq I] (qs : List I) (loc : I → Space) (f : Space → ℝ) :
    ∀ i ∈ qs, (tabulate qs loc).run f i = f (loc i) := by
  induction qs with
  | nil => simp
  | cons j rest ih =>
    intro i hi
    simp only [tabulate,QueryTree.run,QueryTree.run_map]
    by_cases hij : i=j
    · subst i
      simp
    · rw [Function.update_of_ne hij]
      apply ih i
      simpa [hij] using hi

def perturb (b : Space → ℝ) (a n : ℝ) (c : Space) (x : Space) : ℝ :=
  3/2+a*b (n • (x-c))

theorem perturb_admissible (b : Space → ℝ) (K L a n : ℝ) (c : Space)
    (hb : ContDiff ℝ 1 b) (hbounds : ∀ x, 0 ≤ b x ∧ b x ≤ 1)
    (hlip : ∀ x y, |b x-b y| ≤ K*‖x-y‖)
    (hn : 0 ≤ n) (ha : |a| ≤ 1/2) (hcost : |a| *K*n ≤ L) :
    Admissible L (perturb b a n c) := by
  refine ⟨?_,?_,?_⟩
  · unfold perturb
    fun_prop
  · intro x
    have hab : |a*b (n • (x-c))| ≤ 1/2 := by
      rw [abs_mul,abs_of_nonneg (hbounds _).1]
      calc
        |a| *b (n • (x-c)) ≤ |a| *1 := mul_le_mul_of_nonneg_left (hbounds _).2 (abs_nonneg _)
        _ ≤ 1/2 := by simpa using ha
    have hh := abs_le.mp hab
    dsimp [perturb]
    constructor <;> linarith
  · intro x y
    have heq : perturb b a n c x-perturb b a n c y = a*(b (n • (x-c))-b (n • (y-c))) := by
      dsimp [perturb]
      ring
    rw [heq,abs_mul]
    have hnorm : ‖n • (x-c)-n • (y-c)‖ = n*‖x-y‖ := by
      rw [← smul_sub,sub_sub_sub_cancel_right,norm_smul,Real.norm_eq_abs,abs_of_nonneg hn]
    calc
      |a| *|b (n • (x-c))-b (n • (y-c))| ≤ |a| *(K*‖n • (x-c)-n • (y-c)‖) :=
        mul_le_mul_of_nonneg_left (hlip _ _) (abs_nonneg _)
      _ = (|a| *K*n)*‖x-y‖ := by rw [hnorm]; ring
      _ ≤ L*‖x-y‖ := mul_le_mul_of_nonneg_right hcost (norm_nonneg _)
end Recovery
