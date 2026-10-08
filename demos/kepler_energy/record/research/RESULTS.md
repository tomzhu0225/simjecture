# Kepler leapfrog study

## Finding

The original implication is falsified on its requested finite grid. For the circular orbit at 256 steps per period, maximum relative energy error is `9.06e-8`, yet maximum same-time position error over 20 periods is `0.02528a`. The independent review accepted this counterexample and checked the recorded KDK source and retained trajectory (`exp_70ff32e6d28ef9ccd7312295`; `review_9e9e9a5528a825b402183851`). This is consistent with accumulated phase error: energy stays close to its initial value while the numerical orbital phase drifts.

The full 12-case grid is in `metrics.json` and the raw trajectories are in the original experiment workspace. The original-grid result contains five counterexamples among the six cases whose energy error is below `0.001`; cases that fail the energy antecedent do not count as counterexamples.

## Prospective finite-case repair

The replacement commitment (`commit_40654c6537acaacae7b59687`) limits its claim to four exact tuples, with no interpolation to other resolutions or eccentricities. All four committed runs complete 20 periods and meet the `0.01a` position bound:

| Eccentricity | Steps per period | Maximum position error / a | Maximum relative energy error | Experiment |
|---:|---:|---:|---:|---|
| 0.0 | 2048 | 0.0003951 | 2.22e-11 | `exp_084c13fbf06a58ffd855107e` |
| 0.3 | 2048 | 0.001546 | 5.12e-6 | `exp_affe2b99eebe88e0f1007a6f` |
| 0.6 | 4096 | 0.006428 | 1.74e-5 | `exp_13f2a87e5162dfa757f15bdc` |
| 0.6 | 8192 | 0.001607 | 4.36e-6 | `exp_c528e177145130b1c958ea00` |

The additional challenge probe at `(e,N)=(0.6,2048)` has energy error `6.97e-5` but position error `0.02571a` (`exp_5d1bbee42a8dc38ea8c5c889`). It is outside the repair's finite scope and independently demonstrates why energy error alone is not a phase-accuracy test.

For every repair case, the maximum Kepler-equation residual is at most `1.5e-14`, initial position mismatch is zero, and period closure mismatch is below `2.5e-16a`. A separately integrated DOP853 solution differs from the analytic reference by at most `8.2e-10a` for eccentric cases and `2.7e-12a` for the circular case. The KDK update is explicitly half kick, full drift, half kick under inverse-square acceleration. `kepler_results.png` plots KDK and exact trajectories, position error, relative energy error, and unwrapped phase error against physical time.

The repair is deliberately finite and does not establish a general minimum-resolution law. Its independent review is the remaining completion step.
