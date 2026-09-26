# Minimal-mode harness audit and remediation — 2026-09-24

The ten-hour reconnection investigation ended at its original deadline without a
qualified scientific conclusion. This audit led to harness changes and a remote
installation update. The original run and its frozen requirements remain historical
records; this work does not rehabilitate its scientific results or restart it.

## What the run demonstrated

- 397 native worker turns; 345 contained only public agent messages and no completed
  observable tool actions. The longest consecutive message-only streak was 63 turns.
- The new trace observer's three-turn recovery threshold would first have triggered
  at turn 7. This is a retrospective detection test, not proof that recovery would
  have completed the original plasma study.
- 24 recorded experiments: 20 successful processes, three timeouts, one deadline
  cancellation. All used custom Python rather than FLASH or WarpX.
- No FLASH build attempt preceded the decision to avoid anticipated Fortran failures.
- All 121 recorded artifact hashes matched the stored files at audit time.
- No independent claim review was submitted. A revised claim was prospectively
  committed, but its validation matrix was not completed.
- The baseline onset metric was censored. This cannot establish either support or
  falsification of the original timing hypothesis.

## Implemented changes

| Finding | Change | Boundary of the fix |
|---|---|---|
| Review depended entirely on the worker submitting a conclusion | Host-triggered periodic progress review; mandatory source-bound methods review for new instrument-backed studies | Methods approval permits evidence collection, never scientific acceptance |
| Solver substitution relied on anticipated problems | Reviewer receives original instructions, source, actual commissioning outputs/code, and observed blocker receipts; optional immutable instrument requirements | Scientific suitability still requires judgment; a capability name alone does not establish physics |
| A worker could submit review and keep its turn open, starving the judge | Host detects durable methods/claim requests and takes over after a two-second grace period | Requests survive interruption; the original cutoff still applies |
| Arbitrary native turn duration could postpone host checks | Minimal workers checkpoint at five minutes; detached recorded experiments continue | Long native builds need an idempotent, recoverable builder |
| Repeated intention-only turns consumed the budget | Observable-progress detection; corrective prompt after two stagnant turns; fresh native session after three; bounded repeated recovery and responsive backoff | Distinct commands are only progress signals, not proof of useful science |
| An experiment worker could disappear while its receipt remained running | Process-identity reconciliation marks disappearance as execution failure | Does not turn an infrastructure failure into scientific falsification |
| FLASH source was hidden by our precautionary policy | Operator-authorized source inspection, filesystem-protected reference installation, writable problem/build area | Does not grant publication rights or make cooperative execution a security sandbox |
| Compiler errors omitted useful context | Remote builder exposes full build logs and diagnostic tails; adds source-tree and builder hashes to build identity | The intentionally invalid build tested the failure path; no new reconnection application was compiled |
| New helper-built capabilities could not enter the frozen registry | Append-only capability registration with immutable existing identities | New runtimes still need methods review and commissioning |
| Temporary exploration had weaker provenance | Explicit exploration/evidence stages; exploration cannot be relabelled as claim evidence | Native tools remain unrestricted; not every temporary native file is automatically captured |
| Source changes could invalidate prior numerical qualification | Approval bound to exact source/dependency/runtime identity; changed implementation needs a revised method | Parameter variations and final scientific scope remain claim-review responsibilities |
| A separate Laplacian check was presented as solver commissioning | Methods packets include actual commissioning source and results; reviewer checks evolution, conservation, geometry and diagnostics | This is a review safeguard, not a generic mathematical validator |
| Binary outputs would break claim review | Separate compact review documents from hashed raw artifacts; preserve integrity checks for both | Reviewers explicitly do not inspect binary content without a recorded analysis |
| Non-finite JSON and failed checks were easy to miss | Output findings flag invalid JSON constants and explicit false checks; expose them in status/review packets | Flags do not themselves prove a claim false; invalid legacy artifacts are not rewritten |
| An experiment could change its own frozen input files | Detect input-hash mutations and fail execution | Cooperative native processes are still trusted, not adversarially isolated |
| Reporting was stale and contradictory | Host-written STUDY_LEDGER.md and research_report.json; separate execution/scientific status, coverage, findings and supervision state | Worker narrative is retained separately and is not automatically scientifically corrected |
| Refinement controls were left until the deadline | Missing committed-case coverage, measured runtime estimate and analysis/review reserve warning | Estimates are heuristic; the cutoff is not extended and incomplete evidence is not accepted |
| Instructions hard-coded an incorrect storage budget | Generated guide now uses actual per-study limits | Resource policy still comes from the operator |
| Interrupted native turns could lack usage counters | Explicit incomplete-usage counter; available cumulative counters are preserved across session recovery | Missing worker counters are not inferred as zero |
| UI could imply activity despite a stalled model | Shared terminal/status data expose nonprogress and oversight counters | Full visual redesign is outside this patch |

The two key access/governance changes and the additional failures above are covered
by the implementation. Minimal mode retains native tools, free exploration, and
agent-owned scientific planning. Ordinary arithmetic without installed instruments
needs no mandatory methods hierarchy.

## Validation

- Local full suite: **616 passed, 9 skipped**. Skips cover optional MCP dependencies,
  solver runtimes absent locally, and PRoot tests that require the remote environment.
- Remote non-root oversight and execution-backend tests: **19 passed**.
- Artifact audit: **121/121 hashes matched** for the original investigation.
- Read-only source test: agent read a FLASH source file successfully; an actual write
  open was denied. The reference directory was also not writable.
- Compiler diagnostic test: an intentionally invalid user configuration failed as
  expected, and the agent could read the complete build log.
- Two live MiMo v2.6 Pro methods reviews: unsupported MHD substitution **revise**;
  exact finite arithmetic **continue**. Neither decision closed a scientific claim.
  Reported usage: **18,694 input + 1,392 output = 20,086 tokens**, no cached input.
  Reasoning tokens are a subset of output, not additional usage. No billed-credit
  estimate is inferred from these counters.
- An initial 180-second end-to-end run submitted its review but kept the worker
  turn open and reached the cutoff before adjudication. This exposed the handoff bug
  fixed above. The subsequent run uses a 300-second budget; its result is recorded
  in `validation.json`: **completed with independently accepted support in about
  95 seconds**, one worker turn, one recorded experiment and one claim review.
  This is not a same-budget performance comparison. Available judge usage was
  9,987 input + 247 output = 10,234 tokens. The worker was interrupted for handoff
  and returned no final usage counter; total run token usage is therefore unknown.
- Ruff and documentation build with warnings treated as errors: passed.
- Final remote installation: all eight changed Python modules hash-match the tested
  local implementation. Subsequent targeted evidence/oversight tests: 37 passed.

The first live-review fixture attempted to freeze its protocol after commissioning;
this was correctly rejected. The corrected fixture froze requirements before executing
any experiment. An initial remote pytest invocation also used an inaccessible root
working directory; all 19 tests subsequently passed with a usable working directory.

## Deployment and use

Implementation is on the existing `execution-backends` development branch in the
`simjecture-remote-support` worktree. The separate dirty original worktree was not
modified. The development wheel remains 0.5.1.dev0; nothing was published to PyPI.

The remote installation and source checkout were updated. A new reconnection input
bundle was prepared with explicit FLASH/WarpX instrument requirements and authorized
source inspection. It has **not** been launched. The historical run's instructions,
receipts and outputs were not rewritten.

See [minimal oversight usage](../../../docs/how-to/minimal-oversight.md) for the new
methods, capability registration and review-document interfaces.

## Remaining scientific and engineering limits

This patch does not validate the custom MHD solver or resolve the reconnection
hypothesis. Its current-sheet qualification failed in inspected outputs, full refinement
controls were incomplete, and its commissioning did not establish the full evolution
scheme. Future runs need actual solver evolution/conservation benchmarks and meaningful
connectivity diagnostics; the harness cannot infer these universally from filenames or
self-declared passed flags.

We have not run a new long-duration plasma campaign or a multi-model completion-rate
benchmark. The live checks demonstrate two reviewer decisions and a small agent flow,
not improved discovery rates across frontier models. The proposed observer/reviewer
cadences need measurement on longer work. Native exploratory activity is not fully
captured, and source access plus cooperative execution is not an adversarial boundary.

## Follow-up: guided MiMo / DeepSeek comparison, 2026-09-26

The next guided runs exposed additional defects in assignment continuity, methods
approval, evidence annotations and cancellation. The repairs and remaining limitations
are recorded in [the follow-up repair report](../guided-model-comparison-2026-09-26/RESULTS.md).
The [public model comparison](../../../docs/research/llm-comparison.md) separates
observed model/provider behavior from harness failures and reports cached and uncached
usage separately. Neither configuration produced an independently accepted conclusion.

An interval extending beyond an allowed band does not falsify the entire band if the
interval still overlaps it. Any earlier narrative treating that condition alone as
falsification is not endorsed by this audit. Infeasible repaired acceptance bounds
likewise establish a specification error, not a physical counterexample.
