# Demo refresh audit — 2026-10-08

These records distinguish useful numerical work, accepted scientific conclusions,
agent mistakes and harness defects. The original campaigns are preserved. Fixes
made after a cutoff are not credited to the autonomous worker.

## Observed outcomes

| Investigation | Budget and worker | Result |
|---|---|---|
| [Kepler orbit](../demos/kepler-energy.md) | Luna medium; completed in 399.5 seconds | Accepted root falsification and fresh, independently supported finite repair |
| [FLASH island coalescence](../demos/island-coalescence.md) | One hour; Luna medium | Four completed prospective trajectories rejected by a faulty path diagnostic; no accepted claim |
| Same FLASH question | One hour; Sol medium | Five baseline runs, two complete refinements and recoverable full-window output from a third; final processing and scientific review remained incomplete |
| [FLASH → WarpX](../demos/flash-warpx-patch.md) | Two hours; Sol high | Actual state transfer and completed spatial, timestep, particle-count and boundary controls; no accepted claim |

The three plasma runs used a separate Sol-high reviewer context and a research
director. Budgets, models and concurrent machine use differ from the historical
six-hour DeepSeek/classic campaign. These observations do not establish a general
ranking of models or workflows.

## Fixed defects and tested improvements

**Ancestor review ordering.** The first Kepler attempt exposed a host scheduling
error: repair support was repeatedly reviewed before its parent's falsification
had been accepted. The corrected scheduler processes ancestors first and leaves
dependent reviews queued without repeatedly spending provider calls. The fresh
Kepler run completed the full loop after that correction.

**Discovery isolation.** A compact audit has some of the filenames of a live
study, but may omit its immutable commissioning snapshot. Auto-discovery allowed
that expected integrity error to prevent the web interface from opening another
study. Discovery now skips that invalid candidate; explicit loads and resumes
still reject it. CI first reported one failure with 1,299 passes; the corrected
commit passed 1,303 tests with seven skips, plus real WarpX, packaging and docs
checks. Further changes have their own later validation.

**Director-to-worker coordination.** During the coupled study, the director
repeatedly requested review preparation while a solver ran. The host had parked
the worker after its preceding turn, and a `continue` decision did not wake it.
The instruction was therefore not an immediate parallel task. After both studies
ended, the director schema gained `wake_worker`, its packet gained the waiting
state, and the GUI gained an explicit wake-up-request message. Tests verify that
the worker resumes without stopping the solver or creating a replan gate, while
ordinary waiting still avoids unnecessary provider turns. This host behavior is
tested; an improvement in real-model completion rate has not yet been measured.

**Reusable coordinate quadrature.** Luna's diagnostic mixed a cell-centre gauge
with cell-boundary integration. The reviewer flagged earlier alignment problems
but approved a repair that still contained the half-cell error. A post-run
coordinate-consistent calculation reduces its apparent 0.18–0.25 discrepancy to
approximately $10^{-7}$ on the same fields. An optional, narrowly scoped helper
is now in the FLASH skill, with analytic controls for unequal spacings and shifted
origins. The original faulty source and its results are unchanged.

**CUDA runtime qualification.** Operator commissioning exposed WSL GPU-path,
isolated CuPy/header-discovery and nested native-library identity issues. The
installer and registration fixes passed an actual device kernel, openPMD
readback and a sandboxed kinetic trajectory before the two-hour clock started.

## What remains

- **Analysis runtime and instrument requirements need a clearer separation.**
  The Sol FLASH campaign attempted campaign plotting in a runtime without
  Matplotlib. It recovered with SVG, but changing the bound source at the end
  left its processing unapproved. The current required-capability rule applies
  to every evidence method/run, including postprocessing; ordinary `lab.analyze`
  records exploration. A future design should allow an appropriate reviewed
  analysis runtime while preserving verified upstream solver inputs and the
  operator's instrument requirement. That rule has not been weakened here.
- **Local resource limits should be easier to discover and configure.** The
  enlarged kinetic loader exceeded the executor's 4 GiB resident-memory default,
  not the GPU's device-memory capacity. The worker successfully batched loading.
  The limit itself worked; local allocation visibility and configuration remain
  an improvement opportunity. The SSH execution-pool resource interface already
  has a different allocation path.
- **Validate each case before finishing the scan.** Sol's $S_\eta=500$ trajectory
  reached the primary flux window, but stride-two sampling discarded the last
  needed crossing. This was discovered in the final combined analysis. The FLASH
  guidance now recommends prospectively qualified endpoint handling and immediate
  per-case checks. No retrospective eligibility change was applied to the record.
- **Keep figures separate from frozen numerical measurements where practical.**
  Cosmetic or dependency repairs should not unnecessarily change the analysis
  implementation that must be reviewed. Test the exact runtime and final report
  command during commissioning.
- **Leave time for review in the actual critical path.** The coupled worker
  launched a fresh run too late, then cancelled it after comparing its measured
  cost with the remaining budget. A written reserve is not a demonstrated
  completion plan. The wake-up correction addresses one coordination problem,
  but does not guarantee good model planning or a completed investigation.
- **Read receipts alongside worker prose.** Both longer runs left stale statuses
  in `RESULTS.md`. The host's execution and verdict records are authoritative;
  the exported worker reports retain their original wording.

The [FLASH operating guidance](https://github.com/tomzhu0225/simjecture/blob/main/skills/flash-mhd/references/guided-studies.md)
collects the reusable lessons. The diagnostic correction, editorial plots and
this audit were produced by the operator after the corresponding runs; they are
not autonomous recoveries or accepted new scientific evidence.

## Thirty-minute continuation trials

Both studies received separate 1,800-second continuations from commit
`4d76a14f443b42d06dfec8d6539df7d7b01feabd`, with unchanged original hypotheses,
requirements and model/effort routes. No interpretation of the exponent was
supplied. Frozen parent manifest, experiment, method and claim-review hashes were
checked after both runs: none changed. The original records remain intact.

| Observation | Island continuation | FLASH → WarpX continuation |
|---|---|---|
| Recorded executions | 12 succeeded; 1 diagnostic cancelled | 5 succeeded |
| New numerical work | Five base cases and two matched refinements completed | Fine 576² / 32-ppc full-window control completed in 566.6 s |
| Native input / cached / output tokens | 4,527,873 / 3,925,376 / 20,873 | 4,066,383 / 3,548,544 / 33,144 |
| Scientific outcome | Unresolved; no accepted claim review | Unresolved; no accepted claim review |
| Report outcome | Narrative retained; review timed out; stale pending-analysis passage remains | Quantitative narrative retained; review timed out |

The director wake-up change was exercised by both models: report and control
preparation proceeded while numerical jobs continued. The coupled director
explicitly deferred the fresh-seed run when its measured cost no longer fit the
compute allowance. These are observed behaviors, not a general completion-rate
or token-efficiency benchmark.

The protected report phase also exposed two concrete host defects. First,
entering finalization cancelled an analysis job even though its admission
permitted execution into the drafting window. The worker reran it successfully,
but the report-drafting call ended before incorporating its terminal result.
Second, report review received a fixed 135-second call allowance. Both reviews
hit that limit and the host marked finalization finished despite remaining wall
time. The original reports and failed review status are preserved; no verdict
was inferred from reviewer commentary.

**Subsequent fixes, after the trials ended:** preserve admitted diagnostic work
at the numerical cutoff, wait for its receipt within the draft allowance and
resume the writer to incorporate it. Donate unused drafting time to review and
allow one bounded remaining-budget retry after a review transport failure.
Ask report reviewers to return clear blocking corrections promptly rather than
repeating the entire methods audit. Sixty-three focused tests passed, including
regressions for each observed transition. These later corrections have not yet
been validated by another paid plasma campaign; the two trials cannot establish
their real-model completion rate.

The new field/evidence figures are operator renderings from the preserved arrays.
Their plotting bundles retain source hashes and selection metadata; they add no
claim approvals. The full raw simulations, original compact records and new
continuation records remain distinct.
