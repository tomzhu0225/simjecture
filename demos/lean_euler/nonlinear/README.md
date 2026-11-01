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
