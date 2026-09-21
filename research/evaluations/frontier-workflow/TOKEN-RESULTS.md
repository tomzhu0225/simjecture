# Token-accounted repeat results

This repeats the original two GLM 5.3 tasks and workflows with 900-second budgets, 180-second session intervals and at most two simultaneous runs. The original five frozen implementation files were restored, including the original interface limitations. This does not test the subsequent client/path fixes. Reviewer sessions were retained for accounting; reviewers were still fresh and subject to the same acceptance rules.

## Reported worker plus reviewer usage

| Task | Workflow | Input | Cached input (included) | Uncached input | Output | Input + output | Accepted final |
|---|---|---:|---:|---:|---:|---:|---|
| euler | frontier | 1,499,849 | 1,373,184 | 126,665 | 18,114 | 1,517,963 | No |
| euler | structured | 1,136,754 | 1,040,064 | 96,690 | 13,690 | 1,150,444 | No |
| midpoint | frontier | 1,634,854 | 1,513,024 | 121,830 | 20,340 | 1,655,194 | No |
| midpoint | structured | 941,154 | 861,440 | 79,714 | 14,428 | 955,582 | No |

Cached input is a subset of input, and reasoning output is a subset of output. The total adds input and output only. These are native provider-reported counts, not subscription-credit or monetary charges.

## Accounting coverage

- euler-frontier: workers 1 threads / 2 invocations; reviewers 2 threads / 2 invocations; 0 threads missing usage; 1 invocations without a completed-turn event; 0 threads with counter regressions.
- euler-structured: workers 5 threads / 5 invocations; reviewers 0 threads / 0 invocations; 0 threads missing usage; 5 invocations without a completed-turn event; 0 threads with counter regressions.
- midpoint-frontier: workers 1 threads / 5 invocations; reviewers 0 threads / 0 invocations; 0 threads missing usage; 1 invocations without a completed-turn event; 0 threads with counter regressions.
- midpoint-structured: workers 5 threads / 5 invocations; reviewers 0 threads / 0 invocations; 0 threads missing usage; 5 invocations without a completed-turn event; 0 threads with counter regressions.

The collector reads incremental native counters, including those written before agent-turn interruption, and counts each unique thread once. It does not sum cumulative resumed-turn snapshots. A provider request cut off before emitting usage can still be unmeasured; reported totals are not guaranteed to match billing.

## Original report correction

The earlier Euler frontier figure of 2,842,890 input and 20,478 output double-counted cumulative resumed-thread receipts. Its recovered worker-only usage is 1,663,490 input and 12,171 output. The first pilot also has one interrupted ephemeral reviewer with no usage receipt. See [corrected original accounting](original-recovered-token-usage.json).

## Interpretation

Across both tasks, frontier reported **3,173,157 total tokens** versus **2,106,026** for structured, a **50.7% increase**. Uncached input was 248,495 versus 176,404 (40.9% more), and output was 38,454 versus 28,118 (36.8% more). Neither workflow reached an accepted final conclusion. Frontier obtained one Euler contract approval; structured obtained none. This repeat does not demonstrate a token-efficiency or accepted-outcome advantage for frontier.

Compare usage together with scientific outcome. Fewer restarts do not establish token efficiency, and lower usage without an accepted result is not a successful investigation. This small repeat cannot establish model rankings or production performance; the 180-second interval deliberately stresses interruptions and differs from the production 600-second default.

[Detailed tokens](token-repeat-usage.json) · [Scientific run metrics](token-repeat-results.json) · [Predeclared protocol](TOKEN-REPEAT-PLAN.md)
