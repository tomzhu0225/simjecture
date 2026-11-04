-- This file is assembled after Optimality.lean. Costs use a unit-cost RAM:
-- scalar cast/add/divide, oracle query, array write, loop test/increment each
-- cost one. Real constants are literals; arrays have constant-time indexing.
-- Ceiling and index arithmetic are also unit-cost scalar instructions.
-- These are abstract operation counts, not floating-point or elapsed time.
noncomputable section
namespace Work
open Recovery Grid Optimality

structure Metered (A : Type) where
  value : A
  work : ℕ

def literal (r : ℝ) : Metered ℝ := ⟨r,0⟩
def cast (i : ℕ) : Metered ℝ := ⟨i,1⟩
def add (a b : Metered ℝ) : Metered ℝ := ⟨a.value+b.value,a.work+b.work+1⟩
def divide (a b : Metered ℝ) : Metered ℝ := ⟨a.value/b.value,a.work+b.work+1⟩
def coordinate (n i : ℕ) : Metered ℝ := divide (add (cast i) (literal (1/2))) (literal n)
def centerProgram (n : ℕ) (i : Grid.Cell n) : Metered Grid.Space :=
  ⟨fun d => (coordinate n (i d)).value,
    (coordinate n (i 0)).work+(coordinate n (i 1)).work+(coordinate n (i 2)).work⟩
def sampleProgram (f : Recovery.Space → ℝ) (n : ℕ) (i : Grid.Cell n) : Metered ℝ :=
  let c := centerProgram n i
  ⟨f c.value,c.work+1+1⟩ -- one oracle query and one destination-array write

theorem center_program_correct (n : ℕ) (i : Grid.Cell n) :
    (centerProgram n i).value = Grid.center n i := rfl

theorem sample_program_correct (f : Recovery.Space → ℝ) (n : ℕ) (i : Grid.Cell n) :
    (sampleProgram f n i).value = f (Grid.center n i) ∧ (sampleProgram f n i).work = 11 := by
  exact ⟨rfl,rfl⟩

-- RAM arrays are represented semantically as finite functions; update writes
-- one cell. This does not assert a cost bound for persistent function closures.
def fill (f : Recovery.Space → ℝ) (n : ℕ) (cells : List (Grid.Cell n)) : Metered (Grid.Cell n → ℝ) :=
  match cells with
  | [] => ⟨fun _ => 0,2⟩ -- loop initialization and final condition test
  | i::rest =>
    let head := sampleProgram f n i
    let tail := fill f n rest
    ⟨Function.update tail.value i head.value,head.work+tail.work+2⟩

-- Every iteration adds its body, increment and condition test.
def loopWork (n body : ℕ) : ℕ :=
  match n with
  | 0 => 2
  | k+1 => loopWork k body+body+2

theorem loop_work (n body : ℕ) : loopWork n body = 2+n*(body+2) := by
  induction n with
  | zero => simp [loopWork]
  | succ n ih => simp [loopWork,ih]; ring

theorem fill_work (f : Recovery.Space → ℝ) (n : ℕ) (cells : List (Grid.Cell n)) :
    (fill f n cells).work = loopWork cells.length 11 := by
  induction cells with
  | nil => rfl
  | cons i rest ih =>
    simp [fill,sampleProgram,centerProgram,coordinate,divide,add,cast,literal,ih,loop_work]
    omega

theorem fill_values (f : Recovery.Space → ℝ) (n : ℕ) (cells : List (Grid.Cell n)) :
    ∀ i ∈ cells, (fill f n cells).value i = f (Grid.center n i) := by
  induction cells with
  | nil => simp
  | cons j rest ih =>
    intro i hi
    by_cases hij : i=j
    · subst i
      simp only [fill,Function.update_self]
      exact (sample_program_correct f n j).1
    · simp only [fill,Function.update_of_ne hij]
      exact ih i (by simpa [hij] using hi)

-- First enumerate the triples in three nested counted loops, writing three
-- index words per cell. Then fill the density array. This intentionally simple
-- implementation pays for all enumeration and storage rather than assuming
-- grid construction is free. The final three words retain n, T, and the table.
def enumerationWork (n : ℕ) : ℕ := loopWork n (loopWork n (loopWork n 3))
def solverProgram (f : Recovery.Space → ℝ) (n : ℕ) : Metered (Grid.Cell n → ℝ) :=
  let table := fill f n (Grid.cells n)
  ⟨table.value,enumerationWork n+n^3+1+table.work+3⟩

theorem solver_program_values (f : Recovery.Space → ℝ) (n : ℕ) :
    (solverProgram f n).value = Optimality.samples f n := by
  funext i
  exact fill_values f n (Grid.cells n) i (Grid.mem_cells n i)

theorem solver_program_matches_query_algorithm (f : Recovery.Space → ℝ) (n : ℕ) :
    (solverProgram f n).value = (Optimality.samplingAlgorithm n).run f := by
  rw [solver_program_values,Optimality.sampling_values]

theorem solver_work_exact (f : Recovery.Space → ℝ) (n : ℕ) :
    (solverProgram f n).work = 19*n^3+4*n^2+4*n+8 := by
  simp [solverProgram,enumerationWork,fill_work,loop_work,Grid.cells_length]
  ring

theorem solver_work_linear (f : Recovery.Space → ℝ) (n : ℕ) (hn : 0 < n) :
    (solverProgram f n).work ≤ 35*n^3 := by
  rw [solver_work_exact]
  have hn1 : 1 ≤ n := hn
  have hn2 : n ≤ n^2 := by nlinarith
  have hn3 : n^2 ≤ n^3 := by nlinarith
  nlinarith

-- Three scalar operations and one ceiling choose n from L and epsilon.
def toleranceProgram (f : Recovery.Space → ℝ) (L eps : ℝ) : Metered (Grid.Cell (Optimality.resolution L eps) → ℝ) :=
  let p := solverProgram f (Optimality.resolution L eps)
  ⟨p.value,4+p.work⟩

theorem tolerance_work_linear (f : Recovery.Space → ℝ) (L eps : ℝ)
    (hL : 0 < L) (he : 0 < eps) :
    (toleranceProgram f L eps).work ≤ 39*(Optimality.resolution L eps)^3 := by
  have h := solver_work_linear f _ (Optimality.resolution_positive L eps hL he)
  have hn := Optimality.resolution_positive L eps hL he
  have hp : 1 ≤ (Optimality.resolution L eps)^3 := one_le_pow₀ hn
  dsimp [toleranceProgram]
  omega

-- A query is a unit-cost instruction. Any additional scalar/memory work is
-- nonnegative. This lower bound therefore covers all such charged algorithms.
def chargedWork {O : Type} (a : Recovery.QueryTree O) (f : Recovery.Space → ℝ) (additional : ℕ) : ℕ :=
  (a.queries f).length+additional

theorem total_work_upper (f : Recovery.Space → ℝ) (L eps : ℝ)
    (hL : 0 < L) (he : 0 < eps) (heL : eps ≤ L) :
    ((toleranceProgram f L eps).work:ℝ) ≤ 312*(L/eps)^3 := by
  have hwork := tolerance_work_linear f L eps hL he
  have hw : ((toleranceProgram f L eps).work:ℝ) ≤
      39*((Optimality.resolution L eps:ℝ)^3) := by exact_mod_cast hwork
  have hn := Optimality.resolution_work_upper L eps hL he heL
  calc
    _ ≤ 39*((Optimality.resolution L eps:ℝ)^3) := hw
    _ ≤ 39*(2*L/eps)^3 := mul_le_mul_of_nonneg_left hn (by norm_num)
    _ = 312*(L/eps)^3 := by ring

theorem total_work_lower : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps t : ℝ, 1 ≤ L → 0 < eps → eps ≤ 1/(4*K) →
    ∀ a : Recovery.QueryTree (Recovery.Space → ShearEuler.State), Optimality.AccurateEuler t L eps a →
    ∀ additional : ℕ,
      (L/(4*K*eps))^3 ≤ (chargedWork a (fun _ => 3/2) additional:ℝ) := by
  obtain ⟨K,hK,lower⟩ := Optimality.optimal_euler_query_scaling
  refine ⟨K,hK,?_⟩
  intro L eps t hL he hsmall a hcorrect additional
  apply (lower L eps t hL he hsmall a hcorrect).trans
  simp only [chargedWork,Nat.cast_add]
  exact le_add_of_nonneg_right (Nat.cast_nonneg _)
end Work
