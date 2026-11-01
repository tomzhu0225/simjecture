import Mathlib.Data.Rat.Cast.Order
import Mathlib.Tactic.Ring
import Mathlib.Tactic.FieldSimp

namespace Poisson
-- Exact discrete Dirichlet problem: 2*u_i-u_(i-1)-u_(i+1)=f_i,
-- with two zero boundary values and an arbitrary finite rational RHS.

-- Reverse sweep: returns the input count and the weighted source moment.
def moment : List ℚ → Nat × ℚ
  | [] => (0, 0)
  | x :: xs =>
    let (n, w) := moment xs
    (n + 1, w + (n + 1 : Nat) * x)

-- Forward sweep: interior values and the right boundary it reaches.
def sweep : List ℚ → ℚ → ℚ → List ℚ × ℚ
  | [], d, left => ([], left + d)
  | x :: xs, d, left =>
    let current := left + d
    let (rest, right) := sweep xs (d - x) current
    (current :: rest, right)

-- Independent stencil specification, including output shape.
def Equations : ℚ → List ℚ → List ℚ → ℚ → Prop
  | _, [], [], _ => True
  | left, x :: xs, u :: us, right =>
    2*u - left - us.headD right = x ∧ Equations u xs us right
  | _, _, _, _ => False

def solve (f : List ℚ) : List ℚ :=
  (sweep f ((moment f).2 / ((moment f).1 + 1 : Nat)) 0).1

theorem moment_count (f : List ℚ) : (moment f).1 = f.length := by
  induction f with
  | nil => rfl
  | cons x xs ih => simp [moment, ih]

theorem sweep_length (f : List ℚ) (d left : ℚ) :
    (sweep f d left).1.length = f.length := by
  induction f generalizing d left with
  | nil => rfl
  | cons x xs ih => simp [sweep, ih]

theorem sweep_head (f : List ℚ) (d left : ℚ) :
    (sweep f d left).1.headD (sweep f d left).2 = left + d := by
  cases f <;> simp [sweep]

theorem sweep_equations (f : List ℚ) (d left : ℚ) :
    Equations left f (sweep f d left).1 (sweep f d left).2 := by
  induction f generalizing d left with
  | nil => trivial
  | cons x xs ih =>
    simp only [sweep, Equations]
    constructor
    · rw [sweep_head]
      ring
    · exact ih (d - x) (left + d)

theorem sweep_boundary (f : List ℚ) (d left : ℚ) :
    (sweep f d left).2 = left + ((moment f).1 + 1 : Nat) * d - (moment f).2 := by
  induction f generalizing d left with
  | nil => simp [sweep, moment]
  | cons x xs ih =>
    simp only [sweep, moment]
    rw [ih]
    push_cast
    ring

theorem solve_correct (f : List ℚ) :
    (solve f).length = f.length ∧ Equations 0 f (solve f) 0 := by
  have positive : (0 : ℚ) < ((moment f).1 + 1 : Nat) := by
    exact_mod_cast Nat.succ_pos (moment f).1
  have boundary : (sweep f ((moment f).2 / ((moment f).1 + 1 : Nat)) 0).2 = 0 := by
    rw [sweep_boundary]
    field_simp [ne_of_gt positive]; ring
  constructor
  · exact sweep_length _ _ _
  · have h := sweep_equations f ((moment f).2 / ((moment f).1 + 1 : Nat)) 0
    rw [boundary] at h
    exact h
theorem equations_reconstruct (f us : List ℚ) (left right : ℚ)
    (h : Equations left f us right) :
    sweep f (us.headD right - left) left = (us, right) := by
  induction f generalizing us left right with
  | nil =>
    cases us with
    | nil => simp [sweep]
    | cons u us => simp [Equations] at h
  | cons x xs ih =>
    cases us with
    | nil => simp [Equations] at h
    | cons u us =>
      change 2*u - left - us.headD right = x ∧ Equations u xs us right at h
      have current : left + (u - left) = u := by ring
      have delta : u - left - x = us.headD right - u := by
        rw [← h.1]
        ring
      simp only [List.headD_cons, sweep, current, delta]
      rw [ih us u right h.2]

theorem solve_unique (f us : List ℚ) (h : Equations 0 f us 0) : us = solve f := by
  have hn : (((moment f).1 + 1 : Nat) : ℚ) ≠ 0 := by
    exact_mod_cast Nat.succ_ne_zero (moment f).1
  have reconstruction := equations_reconstruct f us 0 0 h
  simp only [sub_zero] at reconstruction
  have boundary := sweep_boundary f (us.headD 0) 0
  rw [reconstruction] at boundary
  simp only [zero_add] at boundary
  have hd : us.headD 0 = (moment f).2 / ((moment f).1 + 1 : Nat) := by
    apply (eq_div_iff hn).2
    rw [mul_comm]
    exact sub_eq_zero.mp boundary.symm
  rw [hd] at reconstruction
  exact (congrArg Prod.fst reconstruction).symm

-- Ghost trace of scalar actions: list/branch inspection, input reads, scalar
-- arithmetic/casts, and explicit output writes each have unit cost. Trace
-- construction itself is instrumentation, erased from the executed algorithm.
inductive Event where
  | control | read | increment | cast | add | sub | mul | div
  | emit (value : ℚ)

def output : List Event → List ℚ
  | [] => []
  | .emit value :: tail => value :: output tail
  | _ :: tail => output tail

def cost (trace : List Event) : Nat := trace.length

def momentRun : List ℚ → (Nat × ℚ) × List Event
  | [] => ((0, 0), [.control])
  | x :: xs =>
    let (result, trace) := momentRun xs
    let n := result.1 + 1
    ((n, result.2 + n*x),
      [.control, .read] ++ trace ++ [.increment, .cast, .mul, .add])

def sweepRun : List ℚ → ℚ → ℚ → (List ℚ × ℚ) × List Event
  | [], d, left => (([], left+d), [.control, .add])
  | x :: xs, d, left =>
    let current := left+d
    let (result, trace) := sweepRun xs (d-x) current
    ((current :: result.1, result.2),
      [.control, .read, .add, .sub, .emit current] ++ trace)

def solveRun (f : List ℚ) : List ℚ × List Event :=
  let (m, first) := momentRun f
  let d := m.2 / (m.1 + 1 : Nat)
  let (result, second) := sweepRun f d 0
  (result.1, first ++ [.increment, .cast, .div] ++ second)

theorem moment_erasure (f : List ℚ) : (momentRun f).1 = moment f := by
  induction f with
  | nil => rfl
  | cons x xs ih => simp [momentRun, moment, ih]

theorem sweep_erasure (f : List ℚ) (d left : ℚ) :
    (sweepRun f d left).1 = sweep f d left := by
  induction f generalizing d left with
  | nil => rfl
  | cons x xs ih => simp [sweepRun, sweep, ih]

theorem solve_erasure (f : List ℚ) : (solveRun f).1 = solve f := by
  simp [solveRun, solve, moment_erasure, sweep_erasure]

theorem output_append (a b : List Event) : output (a ++ b) = output a ++ output b := by
  induction a with
  | nil => rfl
  | cons event tail ih => cases event <;> simp [output, ih]

theorem moment_output (f : List ℚ) : output (momentRun f).2 = [] := by
  induction f with
  | nil => rfl
  | cons x xs ih => simp [momentRun, output_append, output, ih]

theorem sweep_output (f : List ℚ) (d left : ℚ) :
    output (sweepRun f d left).2 = (sweepRun f d left).1.1 := by
  induction f generalizing d left with
  | nil => rfl
  | cons x xs ih => simp [sweepRun, output, ih]

theorem trace_correct (f : List ℚ) :
    output (solveRun f).2 = solve f ∧ Equations 0 f (output (solveRun f).2) 0 := by
  have h : output (solveRun f).2 = solve f := by
    simp [solveRun, output_append, moment_output, output, sweep_output,
      sweep_erasure, moment_erasure, solve]
  exact ⟨h, h ▸ (solve_correct f).2⟩

theorem moment_cost (f : List ℚ) : cost (momentRun f).2 = 6*f.length + 1 := by
  induction f with
  | nil => rfl
  | cons x xs ih => simp [momentRun, cost] at *; omega

theorem sweep_cost (f : List ℚ) (d left : ℚ) :
    cost (sweepRun f d left).2 = 5*f.length + 2 := by
  induction f generalizing d left with
  | nil => rfl
  | cons x xs ih =>
    have h := ih (d-x) (left+d)
    simp [sweepRun, cost] at *
    omega

theorem solve_cost (f : List ℚ) : cost (solveRun f).2 = 11*f.length + 6 := by
  simp only [solveRun, cost, List.length_append, List.length_cons, List.length_nil]
  have hm := moment_cost f
  have hs := sweep_cost f ((momentRun f).1.2 / ((momentRun f).1.1 + 1 : Nat)) 0
  simp only [cost] at hm hs
  omega

theorem output_length_le_cost (trace : List Event) : (output trace).length ≤ cost trace := by
  induction trace with
  | nil => rfl
  | cons event tail ih =>
    cases event <;> simp_all [output, cost]
    all_goals omega

theorem equations_length (f us : List ℚ) (left right : ℚ)
    (h : Equations left f us right) : us.length = f.length := by
  induction f generalizing us left with
  | nil => cases us <;> simp_all [Equations]
  | cons x xs ih =>
    cases us with
    | nil => simp [Equations] at h
    | cons u us => simpa using congrArg Nat.succ (ih us u h.2)

-- Quantifies over every correct completed scalar trace, including algorithms
-- unlike the constructed two-sweep solver. The lower bound follows from writes.
theorem any_solver_lower_bound (f : List ℚ) (trace : List Event)
    (correct : Equations 0 f (output trace) 0) : f.length ≤ cost trace := by
  rw [← equations_length f (output trace) 0 0 correct]
  exact output_length_le_cost trace

-- Explicit matching bounds, hence asymptotic work optimality up to constants.
-- N > 0 absorbs the fixed setup cost; no bit-cost or wall-time claim is made.
theorem work_optimal (f : List ℚ) (nonempty : 0 < f.length) :
    Equations 0 f (output (solveRun f).2) 0 ∧
    cost (solveRun f).2 = 11*f.length + 6 ∧
    (∀ trace : List Event, Equations 0 f (output trace) 0 →
      f.length ≤ cost trace ∧ cost (solveRun f).2 ≤ 17 * cost trace) := by
  refine ⟨(trace_correct f).2, solve_cost f, ?_⟩
  intro trace correct
  have lower := any_solver_lower_bound f trace correct
  constructor
  · exact lower
  · rw [solve_cost]
    omega
end Poisson
