# Stage 3: total work at a prescribed Euler solution error

This adds an accuracy-aware **empirical** ruler: compare complete simulations at
the same physical final time and error tolerance. It also checks analytic-reference
identities and reusable conditional error/work lemmas in Lean. It does **not**
prove a nonlinear Euler convergence theorem or global time-to-accuracy optimum.

## Frozen problem and accuracy contract

`contract.json` fixes a nondimensional periodic unit cube, ideal gas gamma=2,
pressure one, velocity `(0.5,0.2,-0.1)`, and density

`rho(x,y,z,t) = 1 + 0.1 sin(2*pi*(x+y+z-0.6*t))`.

The final time is 0.05. This is a smooth entropy/contact wave embedded in the 3D
Euler system; the varying density is transported at constant pressure and velocity.
It is a one-phase transport problem, not a test of general nonlinear 3D interactions
or shocks. The code evolves all five conservative variables on a full 3D grid.
The exact cell averages multiply the sinusoidal amplitude by `sinc(1/n)^3`.

The primary error is volume-weighted L1 density error against those exact cell
averages, in **absolute nondimensional density units**. Targets are 0.02, 0.01,
and 0.005. The latter is 0.5% of mean density one; it is not 0.5% relative error
in the much smaller density perturbation. All component L1/Linf errors, pressure
and velocity drift, positivity, and conserved totals are retained. A numerical
method can pass this observable's criterion without satisfying every possible
physical accuracy requirement.

Six grids (8³, 16³, 24³, 32³, 48³, 64³), four methods, and three shuffled-order
trials are specified before the primary sweep. Selection is minimum sampled
cell-stage work per method among cases meeting the tolerance. Fastest sampled
wall time is reported separately. This is a finite catalogue comparison.

## Methods and accounting

- `reference`: original first-order Rusanov/forward-Euler implementation.
- `cached`: stage-1 thermodynamic caching in the update; timestep selection
  still repeats its old work.
- `fused`: shares old-state thermodynamics between timestep selection and the
  first-order update, avoiding physical-flux construction just to get wave speeds.
- `muscl_rk2`: a separate second-order comparison using conservative-variable
  MC-limited linear reconstruction, Rusanov interface fluxes, and SSPRK2.
  It rejects inadmissible reconstructed states/stages; it has no general
  positivity-preserving limiter or formal accuracy proof here.

The three first-order variants produce identical recorded solutions and timestep
sequences. The second-order method intentionally changes the discrete solution.
It is a standard method comparison, not a newly discovered numerical algorithm.

Solve timing includes analytic initial-data construction, all timestep choices,
all stages/steps, allocation, and per-step admissibility checks. Final error
analysis is timed separately; the report also gives solve-plus-analysis time.
Process startup, file serialization and experiment orchestration are outside the
per-solve timing and included in the lab receipt's job time.

Work proxies are cell-stage updates and EOS evaluations of individual cells.
They are **not equal-cost FLOPs**: a MUSCL stage costs more than a first-order
stage. Actual pressure-call instrumentation checks the EOS counts. The primary
sweep's total calibration cost is retained separately from the cost of one
selected solve. Performance is exploratory, on one non-isolated CPU host;
no GPU or production-code speedup is claimed.

## Representation matters

`representation.py` applies the same MC-limited piecewise-linear density
reconstruction to selected outputs, then estimates continuous-domain L1 error
with tensor-product Gauss quadrature of orders 3 and 5. This is a numerical audit,
not an interval-certified continuum bound. Reconstruction setup time is counted
in its single-solve audit, while these timings are not substitutes for repeated
performance trials.

A retained negative control demonstrates the distinction: a one-cell projection
has zero cell-average error for this wave but substantial continuous density error.
The 8³ MUSCL case passes the 0.01 projected target while failing the same numerical
reconstructed-field target. The report does not present those two norms as
interchangeable. The target-0.005 first-order 64³ and second-order 16³ outputs both
pass the numerical reconstruction audit.

## What Lean proves, and what remains conditional

`ContactReference.lean` checks the ideal-gas contact embedding, velocity recovery,
the algebraic reduction of Euler residuals to the scalar transport residual,
and the component error factors. Its residual inputs are density derivatives;
it is an algebraic identity, not an independent formalization of the full PDE.
`WaveDerivative.lean` checks the derivative of the affine-phase sine profile and
the phase transport cancellation. The analytic cell-average integration formula
is independently checked by numerical quadrature, not formally integrated here.

`ErrorWork.lean` proves:

- a convex scalar stencil is nonexpansive in the uniform input error;
- if `e_(k+1) <= e_k + delta`, then `e_m <= e_0 + m*delta`;
- with zero initial error, a certified per-step defect `C/n^2`, and at most
  `K*n` steps, the error is at most `K*C/n`, so that condition can admit a grid
  for a requested epsilon;
- `m <= k*n` gives cell-stage work `n^3*m <= k*n^4`;
- under such a certificate's resolution requirement, choosing a larger grid
  cannot lower this work expression.

**The stability/defect hypotheses have not been discharged for the nonlinear
Rusanov or MUSCL/RK2 implementations.** No fitted convergence curve is substituted
for a proof. The uniform-error lemma and the measured L1 error are also distinct;
on a unit-volume domain a true uniform bound would imply an L1 bound, but that
Euler-specific proof chain is still open. The local NumPy reference agreement
and tolerance passes remain empirical floating-point evidence.

## Reproduce

```bash
.venv/bin/simjecture install lean
.venv/bin/python demos/lean_euler/accuracy/run_local.py \
  --output artifacts/lean-euler/accuracy-replay-001
```

Use a new output directory. The driver runs the timing sweep before validation
and proof jobs, so those jobs do not intentionally compete with the primary
benchmark. Expect several minutes on this host. The records contain the frozen
contract, all trials, all errors, sampled selections, source hashes, negative
controls, Lean audits, and job receipts. The [PDF report](report.pdf) and its
standalone figures are generated from those records.

The next proof milestone is to discharge stability and local-defect bounds for
a precisely restricted Euler solution/method class, or produce a certified
case-specific error bound. The next empirical milestone is a smooth nonlinear
vortex and an independently validated shock test. Neither is silently inferred
from success on this entropy wave.

The [Clawpack Euler discussion](https://www.clawpack.org/riemann_book/html/Euler_approximate.html)
provides background on constant-pressure/velocity contact structure. The
[official solver comparison](https://www.clawpack.org/pyclaw/solvers.html)
discusses why more expensive high-order steps can reduce overall cost on smooth
problems. We implement our own small reference; we do not benchmark Clawpack here.
