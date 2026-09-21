# Minimal default follow-up: stronger scientific rules, mixed efficiency

Historical evaluation snapshot: see [v0.5.0 release validation](../release-0.5.0/RESULTS.md) for the subsequent interface and packaging work.


Minimal is now the default for new native-agent studies, with structured and
frontier selectable. This follows the operator's preferred design; it is not a
claim of proven superiority. The [design note](DESIGN.md) describes changes,
external references and compatibility boundaries.

## Fresh real-model tests

Both GLM 5.3 studies completed under the strengthened scientific rules and passed
the common external assessment, including independent numerical checks. Each
had a 900-second maximum and used the same finite task definitions as v2.
No historical outcomes were rewritten.

| Task | Previous minimal revision | This revision | Previous tokens | This revision tokens |
|---|---:|---:|---:|---:|
| Euler | 428 s | 358 s | 536,518 | 1,118,516 |
| Midpoint | 274 s | 176 s | 245,582 | 410,718 |

The Euler comparator is the last fresh scoped-review run; the midpoint comparator
is the full-protocol follow-up. These are one-trial comparisons across revisions,
not randomized repetitions or a causal ablation. Both new tasks ran concurrently.
External grading was separate and the midpoint grader overlapped the Euler run.

Euler retained all four original counterexamples and changed only the incorrect
ratio interval [3.5,4.5] to the theory-motivated first-order interval [1.9,2.1].
The parent, minimal-change rationale, acceptance rule and exact command were
committed before separate fresh validation. The reviewer saw the original
counterexample evidence and accepted the bounded repair. This is finite-domain
support, not a general convergence theorem.

Midpoint attempted to find a threshold violation by checking every requested
post-step diagnostic: 700 observations across the three step sizes. Its maximum
energy error was 3.430589146091734e-14, below the specified 1e-11 bound. Exhaustive
finite-domain testing satisfied the challenge requirement without an extra
planning or search stage.

## What the token results actually say

Wall time fell by approximately 16% and 36%, but reported tokens increased by
108% and 67%. Thus **this iteration did not demonstrate token savings**.

| Task | Worker tokens | Internal reviewer tokens | Input | Cached input (subset) | Output |
|---|---:|---:|---:|---:|---:|
| Euler | 1,026,455 | 92,061 | 1,105,760 | 902,784 | 12,756 |
| Midpoint | 313,834 | 96,884 | 402,566 | 266,112 | 8,152 |

Euler's worker accounts for most of its increase; internal review changed from
88,275 to 92,061 tokens. Midpoint increased in both worker and reviewer usage.
Native calls and context/cache behavior differed between runs. The evidence does
not isolate a cause or establish that the extra scientific fields alone explain
the cost. Native base-instruction metadata remained unchanged in the Euler audit.

The narrower engineering changes do reduce supplied text:

- Euler's first worker prompt was 5,744 bytes; its continuation was 428 bytes.
- Completed Euler status was 4,672 bytes compact versus 12,851 bytes full.
- Completed midpoint status was 1,920 bytes compact versus 4,254 bytes full.

These byte measurements are not tokenizer measurements or end-to-end savings.
Full metadata and scientific instructions remain available from receipt files,
`lab.status(compact=False)` and `RESEARCH_GUIDE.md`.

The common external graders used another **89,652 reported tokens**, excluded
from the comparison table. Cumulative native counters are counted once per
unique thread. Cached input is part of input; reasoning output is part of output.
No subscription cost is inferred. Implementation-assistant usage and requests
without emitted usage counters are not measured.

## Validation and remaining work

The full regression suite passed **564 tests with 5 optional-runtime skips**.
After additional resume-guide, packet-construction and disposition-validation
hardening, the focused service/supervisor/launcher suite passed **36 tests**.
Lint and whitespace checks passed. Tests cover nested repairs, missing ancestor
falsifications, missing or forged challenge references, mutated counterexamples,
legacy record compatibility, durable guides, all three launch modes and mode
preservation on resume.

Live trials used frozen source recorded in [measurements.json](measurements.json).
Later guide regeneration, nonrecursive ancestor packet construction, defensive
support validation, launcher alias consolidation and display-mode metadata were
regression-tested separately, not silently attributed to the frozen live runs.
[export_results.py](export_results.py) regenerates public measurements from the
private receipts; no raw model transcripts are published.

The earlier one-hour FLASH benchmark remains the hard-task evidence: minimal
completed 13/17 required cases versus plain's 14/17, and the full independent
reference remained unresolved because the low-resistivity grid-convergence gate
failed. This iteration did not repeat that costly matrix and cannot establish a
hard-plasma or frontier-model improvement.

The next optimization target is model context and tool-response volume measured
per request, preserving counterexample evidence and review quality. A controlled
repeat is needed before asserting an efficiency gain. Browser/TUI and legacy
API/DSH launch integration remain outstanding; this default applies to the new
native-agent study command and its supervisor aliases. Changes remain in the
`simjecture-frontier` development worktree, not merged or published.
