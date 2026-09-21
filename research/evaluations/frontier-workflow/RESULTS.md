# First measured redesign iteration

This is a small GLM 5.3 pilot, not a model ranking or a claim that Simjecture has
completed autonomous science. The requested model was `glm-5.3` through the
operator's real codex-glm login. No model responses were mocked.

## Four live runs

Each task/condition received 900 seconds. The structured condition used fixed
180-second sessions; the researcher condition used that interval as an inactivity
watchdog and resumed its native thread. **The three-minute interval is shorter
than the production ten-minute interval:** this deliberately exercises checkpoint
churn and is not an estimate of production speedup. At most two runs overlapped.

| Task | Workflow | Worker invocations | Distinct worker threads | Approved contracts | Accepted final conclusion |
|---|---|---:|---:|---:|---|
| Euler accuracy / repair | Structured | 5 | 5 | 0 | No |
| Euler accuracy / repair | Researcher | 3 | 1 | 1 | No |
| Midpoint conservation | Structured | 5 | 5 | 0 | No |
| Midpoint conservation | Researcher | 2 | 1 | 1 | No |

All four reached the host budget. No unresolved result was labelled scientific
completion. Review requests interrupted at the boundary remain queued in the
researcher condition. Details: [pilot-results.json](pilot-results.json).

Both Euler runs produced reference-consistent exploratory ratios, approximately
2.02696, 2.01325, 2.00657 and 2.00327. The structured run obtained these sooner
(~168 seconds vs ~268 seconds). The researcher later generated fresh data after
contract approval (~531 seconds), but linking failed on array-path syntax.
Neither finished the repair-and-review cycle. The structured midpoint run also
produced numerically correct exploratory energy errors. The researcher midpoint
run obtained design approval but suffered execution errors and did not complete
an accepted result. Contract approval and a higher operation count must not be
mistaken for superior scientific output.

## Changes supported by observed failures

1. Preserve context and working notes: ten fresh worker threads became two
   retained threads across the two tasks, without changing acceptance authority.
2. Put review requests in a durable host queue. Do not lose a pending request
   when a model turn or host budget ends.
3. Remove model-authored transport bookkeeping. Both conditions encountered
   operation-ID/active-claim errors unrelated to the mathematics.
4. Define useful JSON evidence paths. The original checker rejected otherwise
   correct numerical rows because it supported object keys but not array indices.
   The updated checker passes the original failed assertions without changing
   the evidence or expected values. See [path-regression-results.json](path-regression-results.json).
5. Separate proposal approval from scientific conclusion. A proposal reviewer
   supplied an approved design with a next action to execute it; the old shape
   validator unnecessarily treated that as a contradiction. Design approval may
   now suggest a next action, but required gaps still force rejection. Scientific
   adjudication remains strict and unchanged.

## Real follow-up client exercise

After the paired pilot ended, a separate GLM call exercised the new client.
It wrote and executed an Euler measurement script through the kernel, produced
reference-consistent numbers, and repeated its request. Both requests returned
`job_c300f1d4b4a52a1f50efd9c8c874e2d6`: one job, not two computations.
No manual operation IDs, active-claim bindings or transport research notes were
supplied; no client errors were reported. The exercise took approximately 118
seconds and left its claim open. It is an interface test, **not** a matched speed
comparison or scientific qualification. See [client-probe-results.json](client-probe-results.json).

## Decision and remaining work

Ship the researcher workflow as **opt-in**. The tests support less context loss
and identify concrete interface repairs. They do not yet show improved rates of
completed scientific investigations, and they say nothing direct about Astra
performance. The revised client/path behavior was tested after the paired pilot;
do not attribute those fixes to the original A/B numbers.

Retain the structured workflow as a selectable baseline. Next evaluation should
use normal production session intervals, multiple repetitions and harder tasks,
including the physical reconnection study, while recording source/contract
correctness and reviewer disagreements. A direct Astra trial should keep the
same evidence standards. Native tool access remains a cooperative-agent trust
model; same-account native agents are not adversarially isolated from host files.

Raw transcripts, invocation records and numerical outputs are retained locally
under `.private/frontier-eval/` in the isolated development worktree. Compact
metrics omit private reasoning transcripts and credentials. Code/task hashes for
the first pilot are recorded in its launch manifest; pre-follow-up source copies
are retained under `.private/frontier-eval/implementation-v1/`.

## Token accounting correction

The initial collector summed `turn.completed.usage` across resumed invocations.
Those receipts are cumulative for the native thread, so this double-counted the
Euler researcher's earlier usage. The originally reported 2,842,890 input and
20,478 output tokens are withdrawn. Its recovered **worker-only** cumulative
usage is 1,663,490 input and 12,171 output tokens, including interrupted turns.
Workers and reviewers must be combined for workflow comparisons.

The collector now reads incremental native session counters once per unique
thread and includes reviewer receipts. Corrected first-pilot data are in
[original-recovered-token-usage.json](original-recovered-token-usage.json).
One original Euler reviewer was interrupted in ephemeral mode and has no receipt;
provider requests cut off before reporting usage remain unmeasured. A fresh repeat
retains reviewer sessions to close the former gap. These are reported token counts,
not a subscription-credit or monetary cost measurement.

The completed [token-accounted repeat](TOKEN-RESULTS.md) found 50.7% higher reported input-plus-output usage for frontier across the two tasks, with no accepted final conclusions in either workflow.
