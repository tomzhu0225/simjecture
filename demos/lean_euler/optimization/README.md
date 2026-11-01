# 3D Euler optimization — stages 1 and 2

The research target is a provable optimum within a specified solver class.
Stage 1 tests a faster implementation of a fixed discrete update.
[Stage 2](formal/README.md) now proves exact-real equivalence, conservation, and
minimum cost within an explicit thermodynamic-caching schedule class.
**General 3D Euler time-to-accuracy optimality remains open.** PR #90 remains draft.

The restricted problem is ideal-gas compressible Euler (`gamma=2`), five
conservative variables, uniform periodic Cartesian cells, first-order shared-face
Rusanov flux, and a forward-Euler step at the same supplied timestep. The candidate
caches old-state pressure and sound speed once and reuses them in all three axes.
It keeps the numerical flux, grid, timestep, and arithmetic ordering of the
remaining update unchanged. This is implementation optimization, not discovery
of a new discretization.

## Run and inspect

```bash
.venv/bin/python demos/lean_euler/optimization/run_local.py \
  --output artifacts/lean-euler/optimization-replay-001
```

Use a new directory. The driver runs the experiment through the real Simjecture
lab sandbox with frozen source inputs. The committed
[record](record/optimization.json) contains all 11 timing samples per kernel and
grid, source hashes, trajectory checks, and claim statuses.
The [PDF](report.pdf) covers the measured stage-1 result and the checked stage-2 cache optimum. It
does not claim an optimal Euler method or verified floating-point execution.

## Observed evidence

| Grid | Reference / cached median time |
|---|---:|
| 16³ | 1.166× |
| 32³ | 1.046× |
| 48³ | 1.203× |
| 64³ | 1.249× |

Timing order was shuffled deterministically after warm-up. Each timed call
includes cache creation and output allocation. Timestep selection, setup,
trajectory validation, and analysis are excluded, so these ratios are not
end-to-end time-to-solution speedups. The host is a Ryzen 9 9900X under WSL2;
these are CPU/NumPy measurements, with no GPU optimization or isolation from
other host activity.

The candidate and reference were bitwise identical at every checked step:
8³ and 12³ random states (8 steps each), 16³ coupled flow (20 steps), and a 24³
spherical pressure blast (20 steps). Density and pressure remained positive;
maximum absolute drift of a volume-weighted conserved total was 1.66e-14.
These are finite empirical checks. The blast has no validated reference solution
in this stage, and there is no shock accuracy or convergence claim.

Stage 2 instruments the `3N` to `N` pressure/sound-speed evaluation counts and
proves N minimal in a cold-cache Eval/Use/Drop interface. See the explicit class
restrictions and weighted-cost theorem in [the formal record](formal/README.md).
The numerical timing ratio is still empirical, and no hardware optimum follows.

## Step-by-step capability gates

1. **Same-update improvement — completed empirically.** Freeze the discrete
   method, test general nonlinear 3D states, retain failures and all timing samples.
2. **Formal equivalence and cost model — completed within the stated class.**
   Fifteen audited theorems cover the concrete real-valued Euler flux/update,
   fresh-cache equivalence, fixed-ratio iterates, conservation, the N-call lower
   bound and a matching cached schedule. Weighted library-cost optimality excludes
   algebraic bypasses, warm caches and changed numerical methods. NumPy/Lean
   correspondence remains empirical; no floating-point refinement is claimed.
3. **Time to a prescribed accuracy.** Add manufactured smooth solutions and
   independently validated shock problems, resolution studies, stronger reference
   solvers, and accuracy/admissibility gates. Count all steps and preprocessing.
4. **Broader algorithm discovery.** Expand flux, reconstruction, and time
   integration choices only after the previous evidence chain is reliable. A
   new class needs a new upper/lower-bound argument. There is no promised date
   for a general Euler optimality proof.

Established positivity-preserving Euler schemes illustrate why conservation,
positivity, accuracy, and optimality need separate arguments:
[Zhang and Shu, 2010](https://www.math.purdue.edu/~zhan1966/research/paper/euler.pdf).
[Clawpack's Riemann-solver documentation](https://www.clawpack.org/riemann.html)
describes the directional interface solves used in multidimensional methods.
Neither source establishes an optimality theorem for this candidate.
