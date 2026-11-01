# Work-optimal reconstruction for a restricted 3D Euler family

This example proves **minimax-order work optimality** for a precisely fixed
family of full, three-dimensional, compressible Euler problems. It constructs a
finite representation with certified uniform error in all five conserved
variables. Every deterministic adaptive point-query algorithm that solves the
same family has a matching worst-case work lower bound:

\[
W^*(L,\varepsilon)=\Theta((L/\varepsilon)^3).
\]

The result is about the asymptotic exponent under an exact-real RAM/oracle cost
model. It does not identify the best constant or fastest implementation.
[report.pdf](report.pdf) explains the result, numerical example, and limitations.
The input/output contract was frozen in [CONTRACT.json](CONTRACT.json) before
new theorem construction; it remains unchanged. Its status field is historical;
[record/ledger.json](record/ledger.json) records the achieved result.

## The physical family

All variables are nondimensional. Take material coordinates \(a=(X,Y,Z)\in[0,1]^3\), pressure \(p=1\), and
ideal-gas ratio \(\gamma=2\). The moving domain is the image of the cube under

\[
F_t(a)=(X+tY,Y+tZ,Z+t).
\]

The initial velocity is \((Y,Z,1)\). The initial density can be **any** globally
C1 function with \(1\le\rho_0\le2\) and Lipschitz constant at most \(L\ge1\)
in the coordinate maximum norm. It need not be a sinusoid, polynomial, or
function of only one phase. The exact solution is

\[
\rho(t,x)=\rho_0(F_t^{-1}(x)),\quad
v(t,x)=(y-tz+t^2,z-t,1),\quad
U=(\rho,\rho v,1+\rho|v|^2/2).
\]

Lean checks C1 regularity, actual derivatives in the canonical conservative
Euler equations, the initial state, and equality of material-wall and fluid
velocities. The target time in the frozen example is in [0,1]; the formulas and
proved bounds happen to hold for every real time. The exact solution is the
specified accuracy reference. Uniqueness among all possible Euler solutions is
not formalized.

The velocity has nonzero vorticity and nonzero convective acceleration. It is
nevertheless prescribed analytically and independent of the density. This is a
pressure-uniform, exactly reducible Euler family: the numerical task is recovering
and transporting its arbitrary three-dimensional density. It excludes pressure
gradients, shocks, turbulence, and general initial/boundary conditions.

## Algorithm, accuracy, and work

Choose \(n=\lceil3L/(4\varepsilon)\rceil\), query the initial density at all
\(n^3\) material-cell centers, and retain those samples. To evaluate the returned
field, map a point back with \(F_t^{-1}\), select its cell, and combine its stored
density with the exact velocity and pressure. No further density queries or
time steps are required. The output is this finite table plus a fixed evaluation
rule, rather than an infinite list of point values.

Every material point lies at most \(1/(2n)\) from its cell center. The density
error is at most \(L/(2n)\); the full conserved-state maximum-component error is
at most \(3L/(4n)\le\varepsilon\). This is a uniform reconstructed-field bound,
not a sampled error or a cell-average-only claim.

`Work.lean` defines the counted scalar operations, center computation, array
fills, and loop recurrence. It charges grid enumeration, array storage,
resolution selection, oracle calls, and the output descriptor. Its simple RAM
implementation costs

\[
19n^3+4n^2+4n+12\le39n^3\le312(L/\varepsilon)^3
\]

for the stated small-tolerance regime. Scalar cast/add/divide, ceiling, index
operations, point queries, and array writes have unit cost. Finite functions
represent RAM arrays with constant-time indexing; this is not a bound for
persistent linked function closures. The bound concerns construction of the
finite field representation. Evaluating an arbitrary number of additional
requested output points has additional cost. The NumPy implementation is not
extracted from Lean, and its vectorized allocations differ from this RAM program.

## Why competing algorithms cannot improve the exponent

The lower bound permits arbitrary internal state and output representations,
adaptive queries anywhere in R3, and arbitrary postprocessing. A machine only
needs to terminate on admissible inputs. It receives point values of the initial
density, not an analytic formula, derivatives, integrals, or training data.

On a constant-density transcript, fewer queries than disjoint small cells leave
one cell untouched. Lean constructs globally smooth positive density functions
that agree at every query but differ by \(4\varepsilon\) inside that cell. Their
bounds and Lipschitz membership are proved, including the smooth bump's existence.
Adaptivity cannot distinguish them because all answers along the transcript are
identical. The same output cannot approximate both within \(\varepsilon\).

The theorem supplies one fixed \(K\ge1\) such that, for
\(0<\varepsilon\le1/(4K)\), every correct competitor needs at least
\((L/(4K\varepsilon))^3\) queries in the worst case. Each query costs one unit;
additional scalar and memory work cannot reduce that lower bound. **K is
existential, not numerically evaluated.** The result certifies scaling, not a
sharp finite-tolerance complexity constant or a wall-time ratio.

## Formal evidence and local reproduction

The central theorem is `Machines.certified_general_optimality`. Physical
correctness is collected in `Certificate.admissible_is_classical_euler`.
The finite sampling program is connected to its query semantics by
`Work.solver_program_matches_query_algorithm`. The input class is nonempty;
smoothness/Lipschitz membership of the adversarial inputs is discharged, not
assumed as an unproved numerical stability premise.

The retained audit checks 20 named statements. Transitive dependencies are
limited to Lean's standard `propext`, `Classical.choice`, and `Quot.sound`.
`record/formal-results.json` contains the exact names, hashes, and outcomes.
The changed-resolution negative control fails to check. A separate valid smooth
numerical example exhibits error above the target for that insufficient grid.

From the repository root:

```bash
.venv/bin/simjecture install lean
.venv/bin/simjecture doctor --profile lean
.venv/bin/python demos/lean_euler/optimality/run_local.py --output artifacts/euler-optimality-replay
```

This runs the NumPy example and the bounded Lean capability through Simjecture's
local lab, retaining receipts. It creates a private local worker in the output
directory and reserves 8 GB for the proof job (the default 4 GB address-space
limit was insufficient for the loaded analysis libraries). Use a new output directory for each replay.
For trusted direct proof checking:

```bash
.venv/bin/python demos/lean_euler/optimality/check_formal.py --output artifacts/euler-optimality-proof --negative-control
```

`assemble.py` builds one self-contained source from the tracked components;
there are no untracked local Lean imports. The installer fetches the necessary
pinned Mathlib dependency closure. The proof requires no network at execution.

The local floating-point results illustrate the theorem but do not certify IEEE
rounding or Python execution. Timings are descriptive and make no comparison
against a general-purpose solver with different boundary conditions. Earlier
Rusanov/MUSCL benchmarks in the sibling directories concern different contracts.

## Prior work and interpretation

Function recovery from point samples and matching error lower bounds have a
substantial literature, including [Micchelli, Rivlin, and Winograd (1976)](https://research.ibm.com/publications/the-optimal-recovery-of-smooth-functions).
Affine motions of 3D Euler fluids also have prior work, for example
[Sideris](https://arxiv.org/abs/1512.03288), whose physical-vacuum family differs
from the material-wall family here. This PR does not claim a new mathematical
principle or priority. Its result is a reproducible, machine-checked connection
between a defined Euler family, physical-field accuracy, an actual sampling
algorithm, and a matching information/work lower bound.
