# Research service: implementation and real benchmark results

The smaller service is implemented and remains opt-in. It removes much of the
mandatory planning and instrument bookkeeping, preserves native tools, records
experiments and reviews, and lets the agent own its investigation. The simple
trials are encouraging. The harder FLASH trial does **not** establish an advantage
over a plain native agent. Do not replace the default workflow on this evidence.

All workers requested GLM 5.3 through codex-glm. These are real model calls and
real numerical executions, not simulated agents. This is a workflow comparison;
it does not establish performance for Astra, Grok, AGY or raw DSH.

## Simple tasks: first frozen matrix

Each task had a 900-second budget. “Evidence adequate” is the common external
assessment of the actual deliverable, including prospective repair when needed.
It is separate from the workflow's own completion status. Tokens include workers
and in-budget reviewers, but exclude the common external grader.

| Task | Workflow | Seconds | Evidence adequate | Workflow outcome | Reported tokens |
|---|---|---:|---|---|---:|
| Euler | Plain | 591 | Yes | Agent exited | 663,240 |
| Euler | Structured | 902 | No | Deadline | 1,015,707 |
| Euler | Frontier | 902 | Yes | Deadline | 1,535,160 |
| Euler | Minimal prototype | 507 | Yes | Completed | 515,332 |
| Midpoint | Plain | 373 | Yes | Agent exited | 320,766 |
| Midpoint | Structured | 902 | Yes | Deadline | 1,431,208 |
| Midpoint | Frontier | 902 | Yes | Deadline | 1,388,670 |
| Midpoint | Minimal prototype | 240 | Yes | Completed | 203,758 |

The prototype minimal service used fewer total reported tokens than plain on both
simple tasks, but more uncached input: Euler 48,417 versus 34,392; midpoint 25,928
versus 21,063. Total tokens alone are not a monetary-cost comparison.

The structured-midpoint grader initially lacked an existing execution receipt.
After restoring that receipt and independently reproducing every output row, the
common assessment passed. The original rejection is preserved; its internal
ledger was not rewritten. Frontier likewise had adequate mathematical evidence
without achieving internal completion. This distinguishes useful research from
harness bookkeeping success.

## Follow-up fixes and fresh tests

Adding the full frozen protocol to every reviewer exposed a coordination bug:
the reviewer sometimes judged the whole study instead of its requested claim.
It withheld approval of a valid original falsification because the repair was
unfinished, then labelled a supported repair with the original claim's outcome.

Reviews now carry an explicit target statement and claim ID. The response schema
requires that ID, the host checks it, and the prompt separates claim review from
study completion. Two fresh real reviewer calls correctly accepted original
falsification and repair support; the old ledger remains unchanged.

| Minimal revision | Task | Seconds | Evidence adequate | Internal outcome | Tokens |
|---|---|---:|---|---|---:|
| Full protocol, before target fix | Euler | 901 | Yes | Deadline | 1,249,329 |
| Full protocol, before target fix | Midpoint | 274 | Yes | Completed | 245,582 |
| Explicit review target, fresh run | Euler | 428 | Yes | Completed | 536,518 |

These are separate follow-ups, not extra independent wins for the first matrix.
The final target fix has a fresh end-to-end Euler test, not another full plasma
matrix. It also has host-level regression tests.

## Hard task: one-hour FLASH plasma investigation

The finite hypothesis concerns whether aligned ablation-like density modulation
changes integrated core Ohmic dissipation by more than 5% in a driven resistive
MHD current sheet. The predefined matrix requires 17 cases: paired amplitudes
at three resistivities and two grids, two temporal refinements, and three
transport controls. See [the frozen protocol](assets/plasma-protocol.md).
This diagnostic alone does not demonstrate topological reconnection, MRT or a
complete Z-pinch.

| Workflow | Seconds | Required cases completed | Justified hypothesis completion | Reported tokens |
|---|---:|---:|---|---:|
| Plain | 3,616 | 14/17 | No | 4,748,986 |
| Structured | 3,602 | 0/17 | No | 10,655,043 |
| Frontier | 3,602 | 1/17 | No | 12,595,965 |
| Current minimal | 3,603 | 13/17 | No | 4,961,038 |

Structured ran preliminary calculations, but none met the required full-case
specification. Plain produced the most completed cases but no final result
document before its deadline. Frontier reported insufficient evidence. Minimal
produced an incomplete report and correctly identified a measured spatial
convergence failure; its missing high-resistivity fine pair and temporal pair
prevented completion. All ten unique reported baseline integrals agree with
independent raw-field recomputation to 2.4e-16 relative error.

Independent reference calculations completed all 17 cases outside agent budgets.
At resistivity 0.001, integrated dissipation changes by **5.970% and 5.832%**
between the 256 and 384 grids, failing the predeclared 5% qualification threshold.
The other resistivities and all transport controls pass their corresponding
checks. Fine-grid fractional modulation effects are approximately 0.0891%,
0.0333%, and 0.3119%; the common temporal allowance is 0.2800 percentage points.
Small observed effects do not override the failed qualification: the finite
hypothesis remains **unresolved**, neither supported nor falsified. Further
refinement needs an explicitly revised protocol, not relaxed post-hoc scoring.

The hard task is therefore also a test of recognizing numerical insufficiency.
Minimal did this correctly, but there is no hard-task completion advantage and
plain achieved greater case coverage. Minimal used about 4.5% more total reported
tokens, with 274,759 uncached input tokens versus plain's 70,671.

## What changed and what still limits the result

The service provides asynchronous experiment receipts, immutable source/input
snapshots, runtime identity and output hashes, durable review requests, and
prospective repair commitments tied to fresh executions. A fixed deadline
survives restarts; an ordinary model exit or inconclusive review does not finish
the study. The native agent retains its tools. Numerical jobs retain Bubblewrap.
The supervisor waits for recorded jobs when an agent yields instead of repeatedly
calling the model just to poll. See [usage and trust boundaries](../../../docs/how-to/research-service.md).

Real testing exposed and corrected several issues:

- Initial native MPI affinity differed from sandbox affinity. That attempt was
  invalidated, retained for accounting, and restarted with verified equal CPU
  access. A repeated reference case reproduced its integral exactly.
- The initial minimal hard run grouped about 3.7 GiB into a hidden 2 GiB job cap.
  It was superseded after 1,183 seconds. The current revision exposes a 4 GiB
  experiment limit and 8 GiB recorded-store limit with dynamic reservations.
- Native plain jobs survived the outer deadline. Six benchmark-owned MPI
  processes were cleaned up afterward and recorded. Its 15-second cleanup grace
  explains the extra wall time; incomplete cases were not credited.
- The current minimal worker made real implementation mistakes: an incorrect
  HDF5 time lookup, a control-analysis failure, a timed-out batch and arithmetic
  on a missing temporal allowance. It repaired enough to report honest partial
  results. A lighter harness does not remove scientific coding errors.
- A redundant external grading packet exceeded practical context size. Identical
  document copies and redundant observer bodies were deduplicated while keeping
  their locations/hashes and plan history; the final assessment completed.

There is one trial per task/workflow/revision. Current-revision runs started later
on shared hardware and a shared provider; this is not a clean simultaneous speed
comparison. Reviewers use the same requested model family, supplemented by
independent deterministic checks. No statistically established completion-rate
or frontier-model claim follows. Agents have cooperative same-account access;
this is not adversarial evidence isolation. The new record format is not yet
integrated into the existing dashboard.

## Accounting and reproducibility

[measurements.json](measurements.json) contains per-run input, cached input,
output, worker/reviewer categories, outcomes and frozen implementation file
hashes. [export_results.py](export_results.py) regenerates it from private run
receipts and exact native session IDs. Resumed cumulative counters are counted
once per unique thread, including interrupted turns where usage exists. Cached
input is a subset of input, and reasoning output a subset of output. Missing
usage is not zero; requests interrupted before counters were emitted can be
unmeasured. No subscription credit or billed cost is inferred.

Separate overhead, excluded from the comparison table:

| Category | Reported tokens |
|---|---:|
| Common external grading, current assessments | 760,399 |
| Superseded grading attempts with usage | 42,980 |
| Two target-review diagnostic calls | 86,224 |
| Invalidated CPU-affinity attempt | 11,373,619 |
| Superseded minimal storage-cap trial | 2,331,213 |

One thread in the invalidated attempt has no usage counter. Root assistant
implementation/research usage is unavailable and is not included. Raw model
transcripts and large field datasets remain private. Reference calculations are
outside agent time/token budgets. The installed FLASH binary SHA-256 is
`07fb0e270a8cf237e7a66cda443f962628d407c5b91e20b891f8d0e838b27b7f`.

Validation: broad regression suite **229 passed, 5 skipped**; optional unavailable
scientific capabilities account for skips. The installed driven-sheet FLASH
capability was exercised directly in these real benchmarks. Development remains
in the separate `simjecture-frontier` worktree; no merge or publication occurred.
