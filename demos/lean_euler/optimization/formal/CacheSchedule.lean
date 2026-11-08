import Mathlib.Data.Finset.Card
import Mathlib.Data.Fintype.Card

namespace CacheSchedule
-- One step, immutable old state, initially empty cache. The only way to create
-- a cached thermodynamic value is Eval. Use consumes it for one direction;
-- Drop permits arbitrary eviction. No stale or cross-cell substitution exists.
inductive Command (ι : Type) where
  | eval (cell : ι)
  | use (axis : Fin 3) (cell : ι)
  | drop (cell : ι)
  deriving DecidableEq

variable {ι : Type} [DecidableEq ι]

def legal (ready : Finset ι) : List (Command ι) → Prop
  | [] => True
  | .eval i :: tail => legal (insert i ready) tail
  | .use _ i :: tail => i ∈ ready ∧ legal ready tail
  | .drop i :: tail => legal (ready.erase i) tail

def evaluated : List (Command ι) → Finset ι
  | [] => ∅
  | .eval i :: tail => insert i (evaluated tail)
  | _ :: tail => evaluated tail

def used : List (Command ι) → Finset ι
  | [] => ∅
  | .use _ i :: tail => insert i (used tail)
  | _ :: tail => used tail

def evalCount : List (Command ι) → Nat
  | [] => 0
  | .eval _ :: tail => 1+evalCount tail
  | _ :: tail => evalCount tail

def useCount : List (Command ι) → Nat
  | [] => 0
  | .use _ _ :: tail => 1+useCount tail
  | _ :: tail => useCount tail

-- Directional preparation outputs must cover all three axes at every cell.
def complete (trace : List (Command ι)) : Prop :=
  ∀ i : ι, ∀ a : Fin 3, Command.use a i ∈ trace

theorem used_needs_eval (trace : List (Command ι)) (ready : Finset ι)
    (valid : legal ready trace) : used trace ⊆ ready ∪ evaluated trace := by
  induction trace generalizing ready with
  | nil => simp [used]
  | cons cmd tail ih =>
    cases cmd with
    | eval i =>
      have h := ih (insert i ready) valid
      simpa [used, evaluated, Finset.insert_union, Finset.union_insert] using h
    | use a i =>
      obtain ⟨available, rest⟩ := valid
      have h := ih ready rest
      simp only [used, evaluated, Finset.insert_subset_iff]
      exact ⟨Finset.mem_union_left _ available, h⟩
    | drop i =>
      have h := ih (ready.erase i) valid
      intro j hj
      rcases Finset.mem_union.mp (h hj) with hj | hj
      · exact Finset.mem_union_left _ (Finset.mem_of_mem_erase hj)
      · exact Finset.mem_union_right _ hj

theorem evaluated_card_le_count (trace : List (Command ι)) :
    (evaluated trace).card ≤ evalCount trace := by
  induction trace with
  | nil => simp [evaluated, evalCount]
  | cons cmd tail ih =>
    cases cmd with
    | eval i =>
      have h := Finset.card_insert_le i (evaluated tail)
      simp only [evaluated, evalCount]
      omega
    | use a i => exact ih
    | drop i => exact ih

theorem use_mem (trace : List (Command ι)) (a : Fin 3) (i : ι)
    (h : Command.use a i ∈ trace) : i ∈ used trace := by
  induction trace with
  | nil => simp at h
  | cons cmd tail ih =>
    rcases List.mem_cons.mp h with h | h
    · subst cmd
      simp [used]
    · cases cmd <;> simp_all [used]

theorem thermodynamic_lower_bound [Fintype ι] (trace : List (Command ι))
    (valid : legal ∅ trace) (allOutputs : complete trace) :
    Fintype.card ι ≤ evalCount trace := by
  have coverage : (Finset.univ : Finset ι) ⊆ evaluated trace := by
    intro i _
    have h := used_needs_eval trace ∅ valid (use_mem trace 0 i (allOutputs i 0))
    simpa using h
  have hcard := Finset.card_le_card coverage
  simp only [Finset.card_univ] at hcard
  exact le_trans hcard (evaluated_card_le_count trace)

-- Canonical cached schedule: evaluate each cell once, then use it in all axes.
def uses (cells : List ι) : List (Command ι) :=
  cells.flatMap (fun i => [.use 0 i, .use 1 i, .use 2 i])
def cached (cells : List ι) : List (Command ι) := cells.map Command.eval ++ uses cells
-- Reference schedule recomputes immediately before each directional use.
def reference (cells : List ι) : List (Command ι) :=
  cells.flatMap (fun i => [.eval i, .use 0 i, .eval i, .use 1 i, .eval i, .use 2 i])

theorem legal_prepare (cells : List ι) (ready : Finset ι) (tail : List (Command ι)) :
    legal ready (cells.map Command.eval ++ tail) = legal (ready ∪ cells.toFinset) tail := by
  induction cells generalizing ready with
  | nil => simp
  | cons i cells ih =>
    simp only [List.map_cons, List.cons_append, legal, List.toFinset_cons]
    rw [ih]
    simp [Finset.insert_union, Finset.union_insert]

theorem uses_legal (cells : List ι) (ready : Finset ι)
    (available : ∀ i ∈ cells, i ∈ ready) : legal ready (uses cells) := by
  induction cells with
  | nil => trivial
  | cons i cells ih =>
    have hi := available i (by simp)
    have ht := ih (fun j hj => available j (by simp [hj]))
    simpa [uses, legal, hi] using ht

theorem cached_legal (cells : List ι) : legal ∅ (cached cells) := by
  rw [cached, legal_prepare]
  apply uses_legal
  intro i hi
  simpa using hi

theorem cached_complete [Fintype ι] :
    complete (cached (Finset.univ : Finset ι).toList) := by
  intro i a
  apply List.mem_append_right
  apply List.mem_flatMap.mpr
  refine ⟨i, by simp, ?_⟩
  have h := a.isLt
  match a with
  | ⟨0, _⟩ => simp
  | ⟨1, _⟩ => simp
  | ⟨2, _⟩ => simp
  | ⟨n+3, _⟩ => omega

omit [DecidableEq ι] in
theorem evalCount_append (a b : List (Command ι)) :
    evalCount (a++b) = evalCount a+evalCount b := by
  induction a with
  | nil => simp [evalCount]
  | cons cmd tail ih => cases cmd <;> simp [evalCount, ih, Nat.add_assoc]

omit [DecidableEq ι] in
theorem cached_eval_count (cells : List ι) : evalCount (cached cells) = cells.length := by
  have prep : evalCount (cells.map Command.eval) = cells.length := by
    induction cells with
    | nil => rfl
    | cons i cells ih => simp [evalCount, ih, Nat.add_comm]
  have consumption : evalCount (uses cells) = 0 := by
    clear prep
    induction cells with
    | nil => rfl
    | cons i cells ih => simpa [uses, evalCount] using ih
  simp [cached, evalCount_append, prep, consumption]

omit [DecidableEq ι] in
theorem reference_eval_count (cells : List ι) : evalCount (reference cells) = 3*cells.length := by
  induction cells with
  | nil => rfl
  | cons i cells ih => simp [reference, evalCount] at *; omega

theorem reference_legal (cells : List ι) (ready : Finset ι) : legal ready (reference cells) := by
  induction cells generalizing ready with
  | nil => trivial
  | cons i cells ih => simpa [reference, legal] using ih (insert i ready)

theorem cold_use_rejected (i : ι) (a : Fin 3) (tail : List (Command ι)) :
    ¬ legal ∅ (.use a i :: tail) := by
  simp [legal]

theorem evicted_use_rejected (i : ι) (a : Fin 3) (tail : List (Command ι)) :
    ¬ legal ∅ (.eval i :: .drop i :: .use a i :: tail) := by
  simp [legal]

theorem cache_optimal [Fintype ι] :
    legal ∅ (cached (Finset.univ : Finset ι).toList) ∧
    complete (cached (Finset.univ : Finset ι).toList) ∧
    evalCount (cached (Finset.univ : Finset ι).toList) = Fintype.card ι ∧
    (∀ other : List (Command ι), legal ∅ other → complete other →
      evalCount (cached (Finset.univ : Finset ι).toList) ≤ evalCount other) := by
  have count : evalCount (cached (Finset.univ : Finset ι).toList) = Fintype.card ι := by
    simp [cached_eval_count]
  refine ⟨cached_legal _, cached_complete, count, ?_⟩
  intro other valid coverage
  rw [count]
  exact thermodynamic_lower_bound other valid coverage

omit [DecidableEq ι] in
theorem saves_two_evaluations_per_cell (cells : List ι) :
    evalCount (reference cells) = evalCount (cached cells) + 2*cells.length := by
  rw [reference_eval_count, cached_eval_count]
  omega

-- The rest of the kernel is fixed. In this library-cost model, one Eval,
-- directional Use, and Drop have nonnegative weights t, f, and d respectively.
-- A single-pass implementation consumes exactly three directional records/cell.
def dropCount : List (Command ι) → Nat
  | [] => 0
  | .drop _ :: tail => 1+dropCount tail
  | _ :: tail => dropCount tail

def libraryCost (t f d : Nat) (trace : List (Command ι)) : Nat :=
  t*evalCount trace + f*useCount trace + d*dropCount trace

omit [DecidableEq ι] in
theorem useCount_append (a b : List (Command ι)) :
    useCount (a++b) = useCount a+useCount b := by
  induction a with
  | nil => simp [useCount]
  | cons cmd tail ih => cases cmd <;> simp [useCount, ih, Nat.add_assoc]

omit [DecidableEq ι] in
theorem dropCount_append (a b : List (Command ι)) :
    dropCount (a++b) = dropCount a+dropCount b := by
  induction a with
  | nil => simp [dropCount]
  | cons cmd tail ih => cases cmd <;> simp [dropCount, ih, Nat.add_assoc]

omit [DecidableEq ι] in
theorem cached_other_counts (cells : List ι) :
    useCount (cached cells) = 3*cells.length ∧ dropCount (cached cells) = 0 := by
  have prep : useCount (cells.map Command.eval) = 0 ∧
      dropCount (cells.map Command.eval) = 0 := by
    induction cells with
    | nil => simp [useCount, dropCount]
    | cons i cells ih => simpa [useCount, dropCount] using ih
  have consume : useCount (uses cells) = 3*cells.length ∧ dropCount (uses cells) = 0 := by
    clear prep
    induction cells with
    | nil => simp [uses, useCount, dropCount]
    | cons i cells ih => simp [uses, useCount, dropCount] at *; omega
  simp [cached, useCount_append, dropCount_append, prep, consume]

omit [DecidableEq ι] in
theorem reference_other_counts (cells : List ι) :
    useCount (reference cells) = 3*cells.length ∧ dropCount (reference cells) = 0 := by
  induction cells with
  | nil => simp [reference, useCount, dropCount]
  | cons i cells ih => simp [reference, useCount, dropCount] at *; omega

omit [DecidableEq ι] in
theorem cached_library_cost (cells : List ι) (t f d : Nat) :
    libraryCost t f d (cached cells) = (t+3*f)*cells.length := by
  rw [libraryCost, cached_eval_count, (cached_other_counts cells).1,
    (cached_other_counts cells).2]
  simp only [Nat.mul_zero, Nat.add_zero, Nat.add_mul, Nat.mul_assoc, Nat.mul_left_comm]

omit [DecidableEq ι] in
theorem reference_library_cost (cells : List ι) (t f d : Nat) :
    libraryCost t f d (reference cells) = (3*t+3*f)*cells.length := by
  rw [libraryCost, reference_eval_count, (reference_other_counts cells).1,
    (reference_other_counts cells).2]
  simp only [Nat.mul_zero, Nat.add_zero, Nat.add_mul, Nat.mul_assoc, Nat.mul_left_comm]

theorem weighted_cache_optimal [Fintype ι] (t f d : Nat) (other : List (Command ι))
    (valid : legal ∅ other) (coverage : complete other)
    (singlePass : useCount other = 3*Fintype.card ι) :
    libraryCost t f d (cached (Finset.univ : Finset ι).toList) ≤
      libraryCost t f d other := by
  have lower := thermodynamic_lower_bound other valid coverage
  have h := Nat.mul_le_mul_left t lower
  rw [libraryCost, cached_eval_count, (cached_other_counts _).1,
    (cached_other_counts _).2]
  simp only [Finset.length_toList, Finset.card_univ, Nat.mul_zero, Nat.add_zero]
  rw [libraryCost, singlePass]
  exact le_trans (Nat.add_le_add_right h _) (Nat.le_add_right _ _)

omit [DecidableEq ι] in
theorem weighted_saving (cells : List ι) (t f d : Nat) :
    libraryCost t f d (reference cells) = libraryCost t f d (cached cells) + 2*t*cells.length := by
  rw [reference_library_cost, cached_library_cost]
  have h : 3*t+3*f = (t+3*f)+2*t := by omega
  rw [h, Nat.add_mul]

omit [DecidableEq ι] in
theorem weighted_strict_improvement (cells : List ι) (t f d : Nat)
    (nonempty : 0 < cells.length) (positive : 0 < t) :
    libraryCost t f d (cached cells) < libraryCost t f d (reference cells) := by
  rw [weighted_saving]
  have extra : 0 < 2*t*cells.length := Nat.mul_pos (Nat.mul_pos (by decide) positive) nonempty
  omega
end CacheSchedule
