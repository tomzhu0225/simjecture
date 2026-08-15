# Electromagnetic time integration

Select the evolve scheme from the physical timescales and observable. Do not
infer a timestep from a familiar dimensional value alone. Record `dt` in
seconds and normalized to every potentially limiting plasma, cyclotron,
collision, transit, growth, drive, and diagnostic timescale.

## Explicit electromagnetic PIC

Omitting `warpx_evolve_scheme` uses WarpX's explicit default. For an auditable
choice, construct `picmi.ExplicitEvolveScheme()` and pass it to
`picmi.Simulation(..., warpx_evolve_scheme=evolve_scheme)`.

For an explicit Yee update, enforce the multidimensional electromagnetic CFL
condition

`c*dt*sqrt(sum_i(1/dx_i**2)) < 1`.

For equal cells in two dimensions this gives `dt < dx/(c*sqrt(2))`. Also
resolve any plasma, gyro, collision, particle-crossing, or source timescale
that can affect the proposed observable. A CFL-passing step is not by itself
an accurate kinetic step.

## Implicit electromagnetic PIC

The pinned 26.07 PICMI runtime exposes:

- `picmi.ThetaImplicitEMEvolveScheme(nonlinear_solver=..., theta=...)`;
- `picmi.SemiImplicitEMEvolveScheme(nonlinear_solver=...)`;
- `picmi.NewtonNonlinearSolver(...)` and
  `picmi.PicardNonlinearSolver(...)`; and
- `picmi.GMRESLinearSolver(...)` for a Newton solve when appropriate.

Pass the selected evolve object through
`picmi.Simulation(..., warpx_evolve_scheme=evolve_scheme)`. Require nonlinear
convergence and preserve the configured tolerance, iteration limit, iteration
history, and failure state. Inspect `warpx_used_inputs_file` for
`algo.evolve_scheme = theta_implicit_em` or `semi_implicit_em`, the intended
`implicit_evolve.nonlinear_solver`, and the exact `warpx.const_dt`.

Implicit advancement removes the explicit electromagnetic CFL condition as a
stability restriction; it does not remove accuracy restrictions. The step
must still resolve the dynamics used as evidence, particle motion relevant to
the estimator, collisions or forcing as implemented, diagnostic sampling, and
changes in the represented state. Qualify the chosen step against a smaller
`dt` while holding the physical case, duration, seed policy, and estimator
fixed. Reject a run whose nonlinear solve fails or whose result depends
materially on solver tolerances.

On the local 2D CUDA/openPMD 26.07 runtime, theta-implicit Picard has
repeatedly aborted with CUDA error 700 inside current deposition when a
loaded 2D electromagnetic plasma is advanced, even when the one-step implicit
wiring smoke succeeds. That is a scheme-specific solver-path failure, not an
openPMD/HDF5 failure. If the operator forbids implicit evolution or requires
explicit electromagnetic PIC, do not spend the campaign commissioning implicit
loaded-plasma cases. Use `ExplicitEvolveScheme` (or the
explicit default), enforce the multidimensional CFL condition, and treat
implicit only as a documented unavailable path.
