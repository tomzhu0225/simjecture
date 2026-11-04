# Stage 2: checked Euler cache equivalence and a scoped optimum

This stage formalizes the actual five-component, gamma=2 Euler/Rusanov update
used by the NumPy example. It proves exact-arithmetic equivalence and a minimum
cost **within a fixed caching-schedule interface**. It does not establish an
optimal Euler discretization, hardware implementation, or time to a PDE error.

## Mathematical result

`EulerCache.lean` defines density, the three momenta, total energy, ideal-gas
pressure, sound speed, directional physical fluxes, the spectral bound and the
Rusanov face flux. It defines both sequential three-axis updates separately:
the reference recomputes thermodynamics; the candidate accepts cached values.

`step_equivalence` proves equality of all five updated components at all cells
whenever the cache contains thermodynamics of the **same old state**. This is
not a finite-grid test. The index type and periodic neighbor permutations are
arbitrary; Cartesian periodic grids are instances. `admissible_step_equivalence`
states the result on positive-density/positive-pressure inputs. Algebraic
substitution actually needs no admissibility hypothesis in Lean's total real
operations; physical interpretation does. No positivity of the updated state is
asserted, and no CFL restriction is invented.

`trajectory_equivalence` lifts the result to every finite number of steps with
fixed timestep/grid ratios and a freshly constructed cache each step.
`cached_conservation` proves component-wise conservation of the concrete cached
Rusanov update on finite periodic grids. Uniform volume can multiply the sums.
`face_consistency` checks the equal-state numerical flux identity.

These are models over mathematical reals. They do not verify Python execution,
IEEE rounding, NaNs, or a compiler. The numerical correspondence checks below
are a separate evidence layer.

## Cost theorem and algorithm class

`CacheSchedule.lean` defines an operational interface for one old-state epoch:

- `Eval(i)` computes and stores the pressure/sound-speed pair for cell i.
- `Use(a,i)` consumes that pair for directional flux/speed preparation. It is
  legal only while cell i is present in the cache.
- `Drop(i)` evicts a value; another Eval is needed before a later Use.

The cache is initially empty. All three directions at every cell must be used.
Only Eval creates a cached pair. Arbitrary ordering, redundant evaluations and
evictions are permitted. Algebraic bypasses, half-pair caching, sharing between
numerically equal cells, warm/precomputed caches, different flux formulas,
changed time integration, lazy output, and skipping constant cells are outside
this class. Data remain immutable throughout the epoch. The cache-state model
tracks availability; the value-correctness side is the fresh-cache hypothesis
and construction in `EulerCache.lean`. This is a library interface model, not a
compiler-verified execution semantics for NumPy.

The lower bound is derived: every used cell must have been evaluated, and the
number of distinct evaluated cells cannot exceed the number of Eval commands.
Complete coverage therefore forces **at least N Eval commands**. The cached
schedule is legal, complete, and uses exactly N; the reference uses 3N. This is
a dependency/interface lower bound, not a lower bound for all Euler algorithms.

For nonnegative integer weights t, f, d per Eval, Use, and Drop, respectively,
the checked single-pass library cost is:

| Schedule | Eval count | Use count | Drop count | Library cost |
|---|---:|---:|---:|---|
| Reference | 3N | 3N | 0 | (3t + 3f)N |
| Cached | N | 3N | 0 | (t + 3f)N |

`weighted_cache_optimal` proves the candidate has no larger weighted cost than
any legal, complete schedule with exactly 3N Uses. `weighted_saving` proves an
exact saving of 2tN against the reference. It is strictly positive for N>0 and
t>0. The unchanged face-combination/update work is outside these counts; adding
an identical common cost preserves the comparison. Cache-capacity effects,
variable instruction costs and bandwidth are not represented. These weights
are not fitted CPU/GPU timings, so the theorem does not predict a speed ratio.

## Connection to the executable

The `instrument.py` job wraps the actual reference and candidate pressure and
square-root calls. It measures 3N versus N scalar-cell evaluations, checks a
literal scalar transcription of the Lean flux/update against NumPy, and rejects
a stale-pressure negative control. It also checks the axis-major schedules used
by NumPy. The canonical Lean witnesses are cell-major; both orders satisfy the
same contract/counts because the old state is immutable. These finite checks do
not replace the theorem and do not close the floating-point refinement gap.

The stage-1 1.05–1.25× measured one-step speed ratios remain independent empirical
evidence. No new timing result is manufactured from the cost theorem.

## Reproduce and inspect

```bash
.venv/bin/simjecture install lean
.venv/bin/python demos/lean_euler/optimization/formal/run_local.py \
  --output artifacts/lean-euler/formal-replay-001
```

Use a new directory. The two real exploratory Simjecture lab jobs produce
`formal-results.json`, `instrumentation.json`, the claim ledger and full receipts.
The compact `record/` retains proof/audit logs, source hashes and measured counts.
The checker refuses placeholders/custom axioms and audits transitive dependencies.
These are assistant-authored scripted proofs, without independent scientific
review or an autonomous discovery claim.

A replay initially exceeded the sandbox's virtual-memory allowance while loading
unneeded tactics. Removing the unused broad imports allowed the proofs to run
inside the existing limit. Failed local attempts remain under the artifact root;
compiler/proof failures were never classified as mathematical counterexamples.
