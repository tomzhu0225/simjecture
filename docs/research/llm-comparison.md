# MiMo and DeepSeek: guided reconnection comparison

The September 25–26, 2026 runs suggest that **DeepSeek V4.1 Flash made more useful
progress in minimal mode than MiMo v2.6 Pro in this particular study**. Neither
configuration delivered an independently accepted scientific conclusion. Both
structured runs spent much of their time commissioning and revising infrastructure.
These observations motivate harness repairs, not a general model ranking.

## What was compared

Each model ran once in minimal mode and once in structured (classic) mode on the
same remote machine, using the same guided island-coalescence hypothesis, FLASH
capability, operator instructions and harness revision `de4c8a6`. Both worker and
reviewer used the arm's model. FLASH ran on CPUs; the machine's P40 GPUs were not
used for these experiments.

The MiMo runs lasted six hours. The operator stopped the DeepSeek runs after about
four hours fifty minutes, once sufficient operational differences were visible.
Both had been allocated six hours. The DeepSeek provider alias was `deepseek-flash`;
the provider's model listing identified it as **DeepSeek-V4.1-Flash**.

This was not a controlled model-only experiment. MiMo used Codex code-mode tools
and Responses Lite; DeepSeek required standard JSON function tools and no Responses
Lite because of provider tool compatibility. The base instructions, high reasoning
setting and configured context size were matched, but the tool protocols differed.
Runs occurred on different days, and there was only one trial per configuration.
Changing both worker and reviewer also prevents separating their contributions.

## Observed work

| Configuration | Elapsed time | Observed progress | Accepted science |
|---|---:|---|---|
| MiMo, minimal | 6 h | 11 successful and 1 failed exploration processes; production methods approval only near the cutoff; no qualified scaling sweep | None |
| DeepSeek, minimal | ~4 h 50 min | Production approval around 2 h; seven 256² control cases by around 3 h; additional refinement and fresh prediction work | None |
| MiMo, structured | 6 h | 6 successful, 8 failed recorded jobs; no completed production matrix | None |
| DeepSeek, structured | ~4 h 50 min | 16 successful, 15 failed jobs; one final commissioning job cancelled; repeated instrument revisions; no completed production matrix | None |

Job totals include analysis and commissioning tasks. One successful job can contain
multiple solver cases, or no solver case at all. These are not simulation success
rates. The structured DeepSeek arm **did submit a late commissioning batch**: an
initial status interpretation based on stale worker prose missed it. Its cancellation
and lack of completed production records do not mean the agent never launched work.

DeepSeek's minimal arm reported a preliminary exponent of −0.4139 with a 95%
interval of [−0.4861, −0.3418], using five admissible cases. This is an agent-produced
analysis, not an independently validated reconnection result. The interval excludes
exactly −0.5 under that analysis but overlaps the original band [−0.60, −0.40]. It
therefore does not establish rejection of the entire band. Censored high-S cases
also cannot falsify a claim explicitly restricted to admissible pre-plasmoid cases.
Different analyzer normalizations prevent direct comparison of scalar rates between
MiMo and DeepSeek.

A later proposed repair required both R ≤ 0.029297 and
R ≥ 1.08 × 0.027231 = 0.02940948. This intersection is empty. Failure of that test
is a specification error, not evidence of physical falsification.

## Token accounting

Counters include worker and reviewer usage. Cached input is already part of input;
reasoning tokens are already part of output. Do not add them again.

| Configuration | Input | Cached input | Uncached input | Output | Input + output |
|---|---:|---:|---:|---:|---:|
| MiMo, minimal | 18,768,134 | 14,537,216 | 4,230,918 | 229,172 | 18,997,306 |
| DeepSeek, minimal | 62,576,544 | 60,373,888 | 2,202,656 | 638,484 | 63,215,028 |
| MiMo, structured | 40,812,304 | 27,382,400 | 13,429,904 | 520,346 | 41,332,650 |
| DeepSeek, structured | 143,911,083 | 141,405,440 | 2,505,643 | 1,923,636 | 145,834,719 |

MiMo minimal is a **lower bound**: eight reviewer threads lacked usage counters.
Interrupted DeepSeek turns were accounted for from available native cumulative
counters; they were not counted as zero. DeepSeek's larger total mostly consists
of cached input, while its reported uncached input is smaller. Different provider
accounting and cache pricing mean these counters do not establish billed cost or
cost per accepted result. No arm had an accepted result.

## Separating model behavior from harness defects

The DeepSeek minimal trajectory shows that the supplied task and solver were usable:
it reached a parameter sweep much earlier. MiMo's slower transition from commissioning
to evidence is an observed configuration-level weakness here. There is no evidence
that model size made it unable to follow commands, or that either model is generally
unsuitable for research.

The harness contributed independently identifiable problems:

- Classic assignment rollover lost access to existing child instruments, encouraging
  duplicate registration and repeated review.
- A worker-authored `scientific_evidence_eligible=false` annotation blocked otherwise
  recorded evidence. Removing only that output annotation changed the bound driver
  and prompted four costly reruns.
- Methods reviewers could return `continue` while imposing unmet conditions in prose.
  Progress reviews sometimes treated short exploratory pilots as scientific tests.
- An impossible numerical acceptance conjunction was not checked before execution.
- Classic cancellation failed while parsing a CLI response, leaving a job for manual
  cleanup. Narrative status also lagged durable job state.

The follow-up patch preserves assignment scope, makes review prerequisites explicit,
checks supplied numerical acceptance bounds, exposes eligibility annotations for
review without making them host policy, and cancels through the durable job store.
See [methods oversight](../how-to/minimal-oversight.md) for the revised API behavior.
These are regression-tested repairs; they have not yet demonstrated improved
long-run scientific completion.

## What to test next

Keep minimal as the default and retain structured temporarily as a regression baseline.
A bounded comparison should first verify instrument reuse, evidence collection,
review handoff and cancellation. Then compare useful validated cases, accepted
claims, elapsed time, uncached/cached input and output separately. Use repeated
matched-duration trials and disclose provider tool differences. A different reviewer
model would help probe correlated mistakes, but is not a substitute for numerical
checks or physical validation.

Separating solver execution, immutable raw data and independently versioned analysis
still needs a fuller provenance API. The annotation fix does not automatically permit
arbitrary analysis changes or retrospective promotion of exploration. Likewise,
numerical-bound checks cover explicit intervals, not arbitrary natural-language logic.

Repository evidence: `research/evaluations/guided-model-comparison-2026-09-26/`
contains sanitized measurements and the repair record. Private operational logs,
credentials and model reasoning are not published.
