import Mathlib.Analysis.Normed.Group.Constructions
import Mathlib.Analysis.Normed.Field.Basic
import Mathlib.Data.Real.Archimedean
import Mathlib.Data.Fintype.Pi
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.FieldSimp
import Mathlib.Tactic.Ring
import Mathlib.Tactic.FinCases

noncomputable section
namespace Grid
abbrev Space := Fin 3 → ℝ
abbrev Cell (n : ℕ) := Fin 3 → Fin n

def center (n : ℕ) (i : Cell n) : Space := fun d => ((i d:ℕ)+1/2 : ℝ)/n

def locate1 (n : ℕ) (hn : 0 < n) (x : ℝ) : Fin n :=
  ⟨min ⌊(n:ℝ)*x⌋₊ (n-1), lt_of_le_of_lt (min_le_right _ _) (by omega)⟩
def locate (n : ℕ) (hn : 0 < n) (x : Space) : Cell n := fun d => locate1 n hn (x d)

theorem locate1_bounds (n : ℕ) (hn : 0 < n) (x : ℝ) (hx0 : 0 ≤ x) (hx1 : x ≤ 1) :
    (locate1 n hn x:ℕ) ≤ (n:ℝ)*x ∧ (n:ℝ)*x ≤ (locate1 n hn x:ℕ)+1 := by
  have hnR : (0:ℝ) < n := by exact_mod_cast hn
  have hx : 0 ≤ (n:ℝ)*x := mul_nonneg hnR.le hx0
  have hlo := Nat.floor_le hx
  have hhi := (Nat.lt_floor_add_one ((n:ℝ)*x)).le
  dsimp [locate1]
  by_cases h : ⌊(n:ℝ)*x⌋₊ ≤ n-1
  · simpa [min_eq_left h] using And.intro hlo hhi
  · have hm : min ⌊(n:ℝ)*x⌋₊ (n-1) = n-1 := min_eq_right (by omega)
    rw [hm]
    have hnsub : ((n-1:ℕ):ℝ) = (n:ℝ)-1 := by rw [Nat.cast_sub (by omega)]; norm_num
    rw [hnsub]
    constructor
    · have hh : (n:ℝ)-1 ≤ (⌊(n:ℝ)*x⌋₊:ℝ) := by
        rw [← hnsub]
        exact_mod_cast (show n-1 ≤ ⌊(n:ℝ)*x⌋₊ by omega)
      linarith
    · nlinarith

theorem center_error_coordinate (n : ℕ) (hn : 0 < n) (x : ℝ)
    (hx0 : 0 ≤ x) (hx1 : x ≤ 1) :
    |x-(((locate1 n hn x:ℕ):ℝ)+1/2)/(n:ℝ)| ≤ 1/(2*(n:ℝ)) := by
  obtain ⟨hl,hu⟩ := locate1_bounds n hn x hx0 hx1
  have hp : (0:ℝ) < n := by exact_mod_cast hn
  apply (abs_le).mpr
  have hA : (n:ℝ)*((((locate1 n hn x:ℕ):ℝ)+1/2)/(n:ℝ)) = ((locate1 n hn x:ℕ):ℝ)+1/2 :=
    mul_div_cancel₀ _ (ne_of_gt hp)
  have hB : (n:ℝ)*(1/(2*(n:ℝ))) = 1/2 := by field_simp
  constructor <;> nlinarith

theorem center_covers_cube (n : ℕ) (hn : 0 < n) (x : Space)
    (hx : ∀ d, 0 ≤ x d ∧ x d ≤ 1) :
    ‖x-center n (locate n hn x)‖ ≤ 1/(2*(n:ℝ)) := by
  apply (pi_norm_le_iff_of_nonneg (by positivity)).mpr
  intro d
  simpa [center,locate,Real.norm_eq_abs] using center_error_coordinate n hn (x d) (hx d).1 (hx d).2

theorem center_in_cube (n : ℕ) (hn : 0 < n) (i : Cell n) :
    ∀ d, 0 ≤ center n i d ∧ center n i d ≤ 1 := by
  intro d
  have hp : (0:ℝ) < n := by exact_mod_cast hn
  have hi : ((i d:ℕ):ℝ) < n := by exact_mod_cast (i d).isLt
  have h0 : (0:ℝ) ≤ (i d:ℕ) := Nat.cast_nonneg _
  dsimp [center]
  constructor
  · positivity
  · apply (div_le_iff₀ hp).mpr
    have hj : ((i d:ℕ):ℝ)+1 ≤ n := by exact_mod_cast (Nat.succ_le_of_lt (i d).isLt)
    linarith

theorem number_of_cells (n : ℕ) : Fintype.card (Cell n) = n^3 := by simp [Cell]

theorem centers_separated (n : ℕ) (hn : 0 < n) (i j : Cell n) (hne : i ≠ j) :
    1/(n:ℝ) ≤ ‖center n i-center n j‖ := by
  have hp : (0:ℝ) < n := by exact_mod_cast hn
  obtain ⟨d,hd⟩ : ∃ d, i d ≠ j d := Function.ne_iff.mp hne
  have hv : (i d:ℕ) ≠ (j d:ℕ) := by exact fun h => hd (Fin.ext h)
  have hdif : (1:ℝ) ≤ |((i d:ℕ):ℝ)-((j d:ℕ):ℝ)| := by
    rcases lt_or_gt_of_ne hv with h | h
    · have hh : ((i d:ℕ):ℝ)+1 ≤ (j d:ℕ) := by exact_mod_cast (Nat.succ_le_of_lt h)
      rw [abs_of_nonpos (by linarith)]
      linarith
    · have hh : ((j d:ℕ):ℝ)+1 ≤ (i d:ℕ) := by exact_mod_cast (Nat.succ_le_of_lt h)
      rw [abs_of_nonneg (by linarith)]
      linarith
  have heq : center n i d-center n j d = (((i d:ℕ):ℝ)-((j d:ℕ):ℝ))/(n:ℝ) := by
    dsimp [center]
    ring
  calc
    1/(n:ℝ) ≤ |center n i d-center n j d| := by
      rw [heq,abs_div,abs_of_pos hp]
      exact div_le_div_of_nonneg_right hdif hp.le
    _ ≤ ‖center n i-center n j‖ := by
      simpa only [Real.norm_eq_abs,Pi.sub_apply] using norm_le_pi_norm (center n i-center n j) d

def cells (n : ℕ) : List (Cell n) :=
  (List.finRange n).flatMap (fun i => (List.finRange n).flatMap (fun j =>
    (List.finRange n).map (fun k => ![i,j,k])))

theorem mem_cells (n : ℕ) (i : Cell n) : i ∈ cells n := by
  have heq : ![i 0,i 1,i 2] = i := by
    funext d
    fin_cases d <;> rfl
  simp only [cells,List.mem_flatMap,List.mem_finRange,true_and,List.mem_map]
  exact ⟨i 0,i 1,i 2,heq⟩

theorem cells_length (n : ℕ) : (cells n).length = n^3 := by
  simp [cells,List.length_flatMap]
  ring
end Grid
