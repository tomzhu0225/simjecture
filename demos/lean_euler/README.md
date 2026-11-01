# Lean and compressible Euler: local commissioning example

This staged example adds formal proof checking to an ordinary Simjecture local
study. It is a scripted commissioning exercise, not an autonomous algorithm
discovery result. The public record was produced on 2026-11-01 on Linux/WSL2.

## Reproduce

From the repository root, with the project environment installed:

```bash
.venv/bin/simjecture install lean
.venv/bin/simjecture doctor --profile lean
.venv/bin/python demos/lean_euler/run_local.py --output artifacts/lean-euler/replay-001
```

Choose a new output directory each time. The driver submits two real exploratory
lab experiments, one with the standard Python capability and one with
`lean-4.24.0`, and waits for their durable receipts. Inspect `ledger.json`,
`receipts.json`, and `study/experiments/*/workspace/`. No API credentials or remote
model calls are needed. The study has no independent scientific review; its
exploration receipts are not an accepted campaign conclusion.

Installation supports Linux x86_64 and needs Python with venv/pip, Git, curl,
and disk space for the Lean toolchain and selected Mathlib cache (allow 6 GB).
The recipe verifies the official Lean archive SHA256 and Mathlib commit, then
uses the pinned Mathlib cache. It installs under `.runtime/lean-4.24.0` without
changing a default Lean toolchain. Runtime downloads are not included in Git.

Upstream dependencies: [Lean v4.24.0](https://github.com/leanprover/lean4/releases/tag/v4.24.0)
(Apache-2.0) and [Mathlib v4.24.0](https://github.com/leanprover-community/mathlib4/tree/v4.24.0)
(Apache-2.0). The [Lean axiom collector](https://github.com/leanprover/lean4/blob/v4.24.0/src/Lean/Util/CollectAxioms.lean)
is used to inspect transitive proof dependencies. These are pinned compatible
versions, not a claim to use the latest releases.

## Progression and observed results

1. **Scalar warm-up:** `Decay.lean` proves nonnegativity of forward Euler for
   `y' = -y` when `y >= 0` and `h <= 1`, and checks the failure at `y=1, h=2`.
   This ODE integrator example is separate from the compressible Euler PDE.
2. **Finite-volume theorem:** `Conservation.lean` proves shared-flux cancellation
   over any finite cell type with a bijective periodic predecessor. A second
   theorem composes three flux differences, covering Cartesian 3D grids
   component by component. It also proves constant-state preservation for a
   constant numerical flux. Arithmetic is real-valued and cell volume is uniform;
   volume and `dt/dx` factors can be incorporated into the flux/state variables.
3. **Compressible Euler witness:** `euler.py` searches a declared finite grid of
   exact rational inputs. With `gamma=2`, three periodic states `(rho,m,E)` equal
   to `(1,0,1/2), (1,0,1/2), (2,0,1)` are initially admissible. Their velocity is
   zero and sound speed is exactly one. A Rusanov step with `dt/dx=4`, `a=1`
   yields `(3,1,3/2), (3,-1,3/2), (-2,0,-1)`. It conserves the totals while
   violating positive density. `Witness.lean` checks initial admissibility,
   sound-speed squared, and the high cell's resulting density `-2`.
4. **Numerical 3D reference:** a first-order Rusanov finite-volume scheme with
   shared periodic face fluxes evolves a smooth contact wave to `t=0.1` with
   `gamma=2`, pressure one, velocity `(0.5,0.2,-0.1)`, and sinusoidal density.
   The exact solution is translation of that wave. Initialization and comparison
   use exact cell averages. The timestep is `0.3 / sum(max(|v_d|+c)/dx_d)`;
   this is an experimental choice, not a formally proved universal CFL bound.

| Grid | Steps | Density L1 error | Largest absolute conserved-total drift |
|---|---:|---:|---:|
| 8³ | 14 | 0.0399061 | 4.45e-15 |
| 16³ | 28 | 0.0291065 | 8.44e-15 |
| 32³ | 56 | 0.0169497 | 2.05e-13 |

All three runs retained positive density and pressure. Seven named theorems
passed the axiom audit, using only `propext`, `Classical.choice`, and `Quot.sound`.
The [checked ledger](record/ledger.json) contains the proof receipts, hashes,
axioms, exact search trace, numerical values, and unresolved claims. The adjacent
record directories retain the generated audits and compiler logs; source files
live in this demo directory. Compiled `.olean` files can be recreated.

## Specification and implementation alignment

In `euler.step`, `face` is the shared outgoing flux and `np.roll(face, 1, axis)`
is the incoming value supplied by the predecessor permutation in `update`.
`dt/dx` scales each face flux. The three directional differences use fluxes from
the same old state and match `update3D` algebraically. Each of the five conserved
components uses the scalar theorem. `rational_step` and `Witness.face` use the
same Rusanov formula in the one-dimensional three-component restriction, with
zero transverse momentum. This is a documented correspondence, not a verified
translation of Python or NumPy into Lean.

A broken two-cell update using unequal transfer values `1/4` and `1/2` changes
total mass by exactly `1/4`; the numerical record includes that negative control.

## Limits and next experiment

The theorem formalizes abstract finite-volume conservation, not Euler flux
admissibility for arbitrary states. The rational witness falsifies unrestricted
positivity; a failed proof attempt by itself would not do so. Decreasing error
on three grids is numerical evidence, not a PDE convergence theorem. Floating
point refinement, entropy, shocks, a general CFL positivity theorem, novel
algorithms, matched-accuracy speedups, and optimality are all unproved here.

The next research experiment can let a Simjecture agent propose a precise CFL
positivity claim, search for exact counterexamples, refine the assumptions, and
attempt a proof while recording every revision. That autonomous trace must be
run and evaluated separately from this scripted demonstration.
