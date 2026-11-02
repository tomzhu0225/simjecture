# Nonlinear 3D Euler: replacement research family

**Solver accuracy and optimality are not proved.** This is the replacement for
the analytically known affine-shear example, which remains useful only as a
reconstruction theorem and a test of the formal-proof workflow.

The intended physical problem is an unforced, inviscid, compressible
Taylor–Green-type vortex on the periodic cube [0,2π]³, with γ = 2. A common
initial-condition family is parameterized by vortex strength A ∈ [1/2,1] and
density perturbation δ ∈ [−0.05,0.05]:

\[
\rho_0=1+\delta\sin x\sin y\sin z,
\qquad
v_0=A(\sin x\cos y\cos z,-\cos x\sin y\cos z,0),
\]
\[
p_0=1+\frac{A^2}{16}(\cos 2x+\cos 2y)(\cos 2z+2),
\qquad E_0=p_0+\rho_0|v_0|^2/2.
\]

Density is initially at least 0.95 and pressure at least 0.625. The formulas
specify only the initial state. The solver must compute subsequent density,
velocity and pressure using the coupled Euler equations. All competitors may use
these explicit formulas: there is no artificial sample-only initial-data oracle.

This is adapted from the compressible three-dimensional inviscid Taylor–Green
benchmark used in [Ranocha et al., section 5.1](https://link.springer.com/article/10.1007/s42967-021-00159-w).
The gamma, density and amplitude choices here are explicit adaptations, not an
exact reproduction of that study. The often-cited analytically solvable
**two-dimensional incompressible** Taylor–Green flow is a different problem.
We do not claim to prove that no analytical representation of this problem could
ever exist. We require a numerical evolution problem with no prescribed future
trajectory or exact solution supplied to the algorithm.

## Check that the dynamics cannot be frozen

Initially v_z vanishes everywhere, so the advective vertical-momentum fluxes
vanish. At x = y = 0, z = π/4, density is one and

\[
\partial_z p_0=-A^2/4,\qquad
\left.\partial_t(\rho v_z)\right|_{t=0}=A^2/4\ge1/16.
\]

The vertical velocity must therefore start changing. Initial fields cannot
simply be transported by the previously prescribed affine shear. Nonzero
acceleration by itself is not a theorem of analytical unsolvability; it is a
concrete check that this particular shortcut is invalid.

`InitialDynamics.lean` differentiates the actual trigonometric pressure. Its
last theorem states the algebraic consequence of the initial vertical Euler
balance, explicitly assuming that balance. These are diagnostic initial-data
lemmas, not an existence, convergence or solver-optimality certificate.

`probe.py` advances all five fields using the existing first-order Rusanov
reference, with no access to a positive-time exact solution. Six runs use grids
16³ and 32³, three parameter values, and T = 0.25. They check emergence of
vertical motion, changing pressure, sampled admissibility, and conservation.
Initialization uses cell-center values, not exact cell averages. These runs
commission the problem; they do not establish continuum accuracy or optimality.

## The useful optimality question

The objective is total work to achieve a specified error in the **evolved
solution**. The proposed norm is the maximum, over all five nondimensional
conserved components, of volume-normalized L1 error in a specified continuous
reconstruction at T. Both spatial and temporal errors count.

The initial search scope is conservative explicit local finite-volume methods,
with stencil radius at most two and one to three Runge–Kutta stages. This scope
still needs a rigorous competitor definition before any optimality theorem is
attempted. Coefficients/rules must work across the parameter family; all
parameter-specific precomputation is charged.

The remaining proof obligations are substantive:

1. Establish a common smooth existence interval, admissibility and regularity
   bounds. T = 0.25 is the initial numerical target, not a proved smooth-time bound.
2. Prove a full-solver accuracy bound for an actual discretization/reconstruction.
3. Prove its total work, including setup, time steps, rejected steps, fluxes,
   checks and any accuracy certification or preprocessing.
4. Prove a matching lower bound on necessary work within the finalized class.

A mesh-refinement plot, finite catalogue ranking, stage/CFL count, output-size
bound or initial-data sampling lower bound does not complete this goal.

From the repository root:

```bash
.venv/bin/python demos/lean_euler/nonlinear/probe.py --output artifacts/nonlinear-euler-probe
.venv/bin/python -m conjecture_solver.lean_check demos/lean_euler/nonlinear/InitialDynamics.lean --theorem NonlinearEuler.positive_initial_pressure_force --output artifacts/nonlinear-euler-initial-proof
```

Use new output directories. The retained record contains the initial diagnostic
proof and baseline numerical results; no unknown continuum solution is stored as
an exact reference.

## Active solver work

The goal is active; [GOAL_STATUS.json](GOAL_STATUS.json) records the current
front and the unresolved requirements. `finite_volume.py` implements a
conservative global-speed Rusanov candidate with analytic conservative-cell
initial averages and a clipped CFL timestep. It evolves the full nonlinear
system and does not use an exact positive-time solution.

The formal solver foundations now check:

- Convexity of the positive-density/positive-pressure state region and
  admissible Euler flux splitting.
- Positivity of the complete nonlinear update with wave speeds and timestep
  computed from the current finite grid, plus periodic conservation.
- An exact unsafe-splitting counterexample.
- A positive primitive-variable energy form that symmetrizes the principal
  coefficients, connected by actual differentiation to the conservative Euler
  equations.
- Energy contraction for the constant-coefficient principal update, derived
  from positive matrix weights and a finite-sum Jensen inequality.
- Explicit state-box norm/coefficient bounds, an exact varying-coefficient
  energy defect, and a principal-update growth bound under stated spatial
  difference bounds. Both before/after energies here use the old local metric.
- A 3D grid embedding with constant 8 independent of mesh resolution.
- An exact counterexample to varying-metric contraction: at CFL 1/2, the
  energy of a particular error field grows from 5 to 125/16. This is an
  auxiliary stability diagnostic, not a replacement physical problem.

These are **not a global stability, convergence, or optimality theorem**.
Common smooth-time bounds, uniform numerical regularity, an actual full-solve
error estimate, and matching complexity bounds remain open. The initial-cell
average formulas have an independent quadrature check; their formal
initialization/reconstruction bridge also remains to be proved.

Forty-five named solver-foundation statements and the independent numerical checks
are retained under `record/solver`. Replay them through the bounded local lab:

```bash
.venv/bin/python demos/lean_euler/nonlinear/run_solver_study.py --output artifacts/nonlinear-solver-foundations
```

The replay uses an isolated local worker with the same pinned Lean runtime and
an 8 GB proof-job memory allowance. `check_solver.py` and `assemble_solver.py`
provide the corresponding trusted direct check. The Python implementation is
not a verified extraction and the numerical checks do not certify IEEE error.

The [current PDF report](report.pdf) describes the checked statements and their
premises. For the varying-coefficient principal update, the energy estimate is

\[
E_{\rm after}\le[1+756\Delta t(256BK+32D)]E_{\rm before}.
\]

It assumes specific volume q = 1/ρ and pressure in [1/4,4], a valid CFL ratio,
|a_d| + |v_d| ≤ B, and neighboring differences bounded by |Δq| + |Δp| ≤ hK
and |Δv_d| ≤ hD. Here Δt = ratio × h. The constant stays independent of the
number of cells if B, K and D have uniform bounds. Those bounds are **not yet
proved for the nonlinear trajectory**. Metric variation in time, nonlinear
update remainders and common smooth existence remain required work.

`GridSobolev.lean` proves |f(i,j,k)|² ≤ 8 E₃(f). Its one-dimensional building
block is E₁(f) = n⁻¹ Σf² + n Σ(f(k+1)−f(k))²; E₂ and E₃ recursively apply the
same construction in the other coordinates. Thus E₃ contains eight mixed
forward differences, with each coordinate differentiated at most once, scaled
to unit coordinates. This controls values from derivative energies, not the
growth of those derivative energies during evolution.

The energy audit is replayed in
`artifacts/lean-euler/20261102/nonlinear/research/lab-energy-03`. The earlier
`lab-energy-01` attempt is retained: its final negative-control proof hit Lean's
simplifier recursion limit. Factoring the computation into smaller checked
lemmas resolved it without increasing checker limits.

## Entropy and the accuracy-based lower-bound route

`Entropy.lean` derives the actual gradient and Hessian of
η(U) = −ρ log(p/ρ²). `EntropyConvexity.lean` proves convexity on the admissible
conserved-state domain and the finite averaging inequality.
`EntropyDynamics.lean` proves the canonical entropy-flux potential and the
local entropy balance implied by differentiable conservative Euler balance.
These are connected to the actual physical flux and entropy definitions.
They do not establish smooth existence or the periodic integral theorem.

The entropy-calculus replay is
`artifacts/lean-euler/20261102/nonlinear/research/lab-entropy-01`: three successful
bounded jobs cover candidate validation, entropy diagnostics, and 29 named
Lean statements. The new `validate_entropy.py` records nine trajectories on
16³/32³/64³ grids and 24 randomized one-step checks. All tested updates lose
mathematical entropy. For A = 1, δ = 0.05, total discrete entropy loss falls
from 0.05806 at n = 16 to 0.02051 at n = 64. Loss divided by h changes from
0.14785 to 0.20894. These observations are consistent with a leading error
proportional to h, but do not certify a rate or an error constant.

The proposed argument is to prove actual-step entropy dissipation, accumulate
it over time, and connect it to unavoidable error in the evolved output.
The explicit time discretization must be included; semidiscrete entropy
stability is insufficient. See [Tadmor (2003), §§7–8](https://www.math.umd.edu/~tadmor/pub/TV%2Bentropy/Tadmor_Acta2003.pdf)
for the established spatial/time entropy framework. That reference is not
imported as a formal theorem.

The original search scope includes higher-order methods. First-order Rusanov
cannot be called optimal in that scope merely because these foundations pass.
A proposed LF/Rusanov class with convex reconstruction remains under
investigation. Its scientific justification, actual dissipation, necessary
accuracy and complete work bounds all require proof. None of the measured
entropy ratios is used as a certified universal constant.

## Conditional finite-step dissipation

The expanded proof now combines actual conserved-variable entropy calculus,
Rusanov face fluxes, periodic summation, a six-neighbor increment bound and the
finite-step Taylor remainder. `EntropyRegion.lean` states the result using an
explicit convex state region K. Both old and updated states must belong to K.
Throughout K, the actual entropy Hessian must have bounds λ I ≤ D²η ≤ M I,
and each physical flux must be L-Lipschitz in the five-component Euclidean norm.

For r = Δt/h and global directional viscosities between a_min and a_max,
sufficient conditions are

\[
M(1+L^2)\le a_{\min}\lambda/2,\qquad
3Mr(a_{\max}^2+L^2)\le a_{\min}\lambda/8.
\]

Here “viscosity” means artificial numerical diffusion: a_d is the coefficient
of the state jump in the Rusanov face flux, −(a_d/2)(U_right−U_left). It is not
physical fluid viscosity; the target PDE remains inviscid 3D Euler. The theorem
guarantees a one-step entropy inequality, not a complete accurate solution.

The proved conclusion for the actual nonlinear update is

\[
\sum_i\eta(U_i^{\rm new})\le\sum_i\eta(U_i)
-\frac{r a_{\min}\lambda}{8}\sum_{\text{forward periodic faces}}|\Delta U|^2.
\]

This is a **conditional method theorem**. It does not prove trajectory membership
in K. Concrete constants and a limitation of this criterion are now proved below.
The current wave-speed recipe cannot satisfy the criterion on that region;
reducing the timestep alone does not fix the viscosity condition. This theorem
is not the requested continuum-accuracy or optimality result.

The 37-statement replay is retained in
`artifacts/lean-euler/20261102/nonlinear/research/lab-step-02`. The first batch
compiled the mathematical source but hit Lean's recursion limit in the generated
auditor. The checker now generates a separate audit command for each declaration;
an 80-theorem regression test checks the fix without changing Lean's limits.

## Concrete state bounds and a failed proof criterion

`PhysicalRegion.lean` proves convexity of

\[
K=\{U:1/4\le\rho\le4,\ E\le4,\ p\ge1/4\}.
\]

It derives the actual conservative entropy Hessian's sum-of-squares formula,
with lower constant λ = 1/12500 and upper constant M = 100000.
`PhysicalFluxBounds.lean` derives the actual Euler flux derivative and the
finite flux Lipschitz bound L = 1200. `InitialRegion.lean` proves that every
spatial point of the complete parameterized initial family lies in K.
The evolving trajectory and initialization by exact cell averages still need
their formal bridges.

These coarse constants would require viscosity at least
3,600,002,500,000,000 in the global criterion. A stronger exact obstruction
shows that improving the global constants alone is insufficient on K:

- The rest state U* = (1,0,0,0,1) occurs in every initial-family member at
  (0,π/2,π/2).
- Two actual Hessian evaluations at U* force M ≥ 13/5 and λ ≤ 2/5 for any
  valid global curvature bounds on K.
- Every physical directional wave speed in K, and hence every computed
  directional maximum on a grid contained in K, is at most 12.
- Consequently M(1+L²) ≥ 13/5, while aλ/2 ≤ 12/5: the criterion cannot hold.

This rejects the **sufficient global criterion for this wave-speed recipe**.
It does not refute the solver's actual entropy behaviour or show that the
research goal is impossible. The next work needs a sharper estimate using
Euler's entropy-weighted structure and local state variation, or a different
consistent numerical flux. The physical family and full accuracy/work goal
are unchanged. The complete 45-statement replay is retained in
`artifacts/lean-euler/20261102/nonlinear/research/lab-region-01`.
