-- Assembled after the component proofs. This theorem ties the physical
-- solution, finite-query algorithm, uniform accuracy and work bounds together.
noncomputable section
namespace Certificate

theorem admissible_is_classical_euler (L : ℝ) (rho0 : Recovery.Space → ℝ)
    (hf : Recovery.Admissible L rho0) :
    ContDiff ℝ 1 (fun tx : ℝ × ShearEuler.Space => ShearEuler.solution rho0 tx.1 tx.2) ∧
    (∀ t x, deriv (fun s => ShearEuler.solution rho0 s x) t +
      deriv (fun s => ShearEuler.eulerFlux (ShearEuler.solution rho0 t (Function.update x 0 s)) 0) (x 0) +
      deriv (fun s => ShearEuler.eulerFlux (ShearEuler.solution rho0 t (Function.update x 1 s)) 1) (x 1) +
      deriv (fun s => ShearEuler.eulerFlux (ShearEuler.solution rho0 t (Function.update x 2 s)) 2) (x 2) = 0) ∧
    (∀ x, ShearEuler.solution rho0 0 x = ShearEuler.conserved (rho0 x) ![x 1,x 2,1]) ∧
    (∀ t x, deriv (fun s => ShearEuler.flow s x) t = ShearEuler.velocity t (ShearEuler.flow t x)) := by
  refine ⟨ShearEuler.solution_is_C1 rho0 hf.1,?_,ShearEuler.initial_state rho0,ShearEuler.boundary_moves_with_fluid⟩
  intro t x
  apply ShearEuler.physical_euler_equations
  · exact hf.1.differentiable (by norm_num) _
  · intro a
    have h := (hf.2.1 a).1
    linarith

theorem family_nonempty (L : ℝ) (hL : 0 ≤ L) : Recovery.Admissible L (fun _ => 3/2) := by
  refine ⟨contDiff_const,?_,?_⟩
  · intro x
    norm_num
  · intro x y
    simp only [sub_self,abs_zero]
    exact mul_nonneg hL (norm_nonneg _)

-- Minimax-order optimality, with one fixed positive lower-bound constant.
-- Both upper and lower orders are (L/epsilon)^3. No best-constant claim.
theorem certified_work_optimality : ∃ K : ℝ, 1 ≤ K ∧
    ∀ L eps t : ℝ, ∀ hL : 1 ≤ L, ∀ he : 0 < eps, eps ≤ 1/(4*K) →
    let n := Optimality.resolution L eps
    let hn := Optimality.resolution_positive L eps (lt_of_lt_of_le (by norm_num) hL) he
    Optimality.AccurateEuler t L eps (Optimality.eulerAlgorithm n hn t) ∧
    (∀ f : Recovery.Space → ℝ,
      (Work.toleranceProgram f L eps).value = (Optimality.samplingAlgorithm n).run f ∧
      ((Work.toleranceProgram f L eps).work:ℝ) ≤ 312*(L/eps)^3 ∧
      ((Optimality.eulerAlgorithm n hn t).queries f).length = n^3) ∧
    (∀ competitor : Recovery.QueryTree (Recovery.Space → ShearEuler.State),
      Optimality.AccurateEuler t L eps competitor → ∀ additional : ℕ,
      (L/(4*K*eps))^3 ≤ (Work.chargedWork competitor (fun _ => 3/2) additional:ℝ)) := by
  obtain ⟨K,hK,lower⟩ := Work.total_work_lower
  refine ⟨K,hK,?_⟩
  intro L eps t hL he hsmall
  have hLp : 0 < L := by linarith
  have hKp : 0 < K := by linarith
  have heL : eps ≤ L := by
    have hh := (le_div_iff₀ (by positivity : 0 < 4*K)).mp hsmall
    nlinarith
  refine ⟨Optimality.euler_algorithm_accurate L eps t hLp he,?_,?_⟩
  · intro f
    exact ⟨Work.solver_program_matches_query_algorithm f _,Work.total_work_upper f L eps hLp he heL,
      Optimality.euler_algorithm_queries _ _ t f⟩
  · intro competitor hcorrect additional
    exact lower L eps t hL he hsmall competitor hcorrect additional
end Certificate
