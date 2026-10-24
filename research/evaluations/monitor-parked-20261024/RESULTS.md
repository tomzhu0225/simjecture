# A real wakeup opportunity while the worker is parked

The unchanged 4B coprocessor detected an actual receipt/adapter contradiction,
requested an independent repair judge, and enabled the original scientific
worker to resume. Both fault runs finished in 116–120 seconds with four native
agent starts, compared with 217–246 seconds and six starts for observe-only.
Public-state rules handled the same structured fault faster: 99–107 seconds,
also four starts. This supports the usefulness of background attention in this
fixture; it does not establish that the learned model is better than rules.

## Measured cohort

Twelve fresh live trajectories, two per cell, followed the frozen
[protocol](PROTOCOL.md). Two earlier commissioning trajectories were excluded
before the cohort and remain in the local record. Every cohort run completed
both actual WarpX controls (64 cells/40 steps and 128 cells/80 steps). All twelve
numeric reports agreed with independent analysis of saved diagnostics, with the
original field tolerance 0.05 and charge-residual tolerance 1e-11 preserved.
This verifies report accuracy and completion, not independent scientific acceptance
of the worker's diagnosis or of a physical hypothesis.

| Condition | Observer | Total seconds, both runs | Parked seconds, mean | Native starts per run | Contradiction to judge, mean |
|---|---|---:|---:|---:|---:|
| Defective adapter | Observe only | 246.47 / 217.34 | 90.33 | 6 | 113.18 s |
| Defective adapter | Rules | 106.70 / 98.68 | 26.60 | 4 | 0.051 s |
| Defective adapter | 4B model | 116.31 / 119.92 | 41.65 | 4 | 11.34 s |
| Healthy | Observe only | 68.89 / 73.34 | 0.76 | 2 | No judge |
| Healthy | Rules | 74.32 / 76.88 | 2.76 | 2 | No judge |
| Healthy | 4B model | 72.21 / 73.80 | 3.77 | 2 | No judge |

Model fault response latencies were 11.08 and 11.59 seconds. The mean full task
time was 49.1% lower than observe-only (118.12 versus 231.90 seconds), with two
fewer native starts per fault run. These are descriptive small-sample differences,
not confidence intervals or an estimate across research tasks. All forty cohort
native starts ended; all twelve final feedback audits are measurable, with zero
required-feedback misses or duplicate wakeups. No model transport errors occurred.
There were 24 actual solver runs in this cohort, plus four in commissioning.

## What the small model actually did

The worker submitted real asynchronous simulations and yielded. A private test
completion adapter deliberately returned `running` after the process had stopped
successfully. The monitor saw raw public process receipts and adapter state while
the worker was parked. Its action was `request_repair_judge`, not permission to
edit the harness. A fresh native judge considered the evidence; a separately
scoped proposer repaired the private classification bridge through fixed isolated
tests. After host validation applied that change, ordinary completion resumed
the original worker, which analyzed its saved results and acknowledged the actual
returned repair digest. The model initiated one judge request in each fault run.
Neither healthy model run requested a judge.

Observe-only also retained explicit worker help/repair requests. Its common
90-second fallback woke the worker, which diagnosed and requested repair itself.
Thus the comparison is earlier background detection versus later worker recovery,
with the same fallback and authority path available. Rules received the same
public contradiction events; the pre-commissioning polling amendment is recorded
in the protocol. The model was not given hidden case identifiers or a privileged
permission channel.

## Interpretation and limits

The earlier [32-continuation study](../monitor-paired-20261024/RESULTS.md) mostly
showed redundant intervention when an awake worker immediately received the
errors. This study exposes a different opportunity: evidence appears while that
worker is waiting. It demonstrates the complete model-to-judge-to-repair-to-worker
loop with real scientific computation.

This is an injected, repeated, known completion-classification fault in a private
fixture, on a shared GPU, with two repetitions per cell and fresh worker sessions.
It is not a repair of the installed supervisor, a fully wedged-host watchdog, or
a task-disjoint generalization test. Native starts are an operational proxy, not
provider request counts or a billing total. The base model and existing LoRA
weights were not changed for this study. For this explicit boolean contradiction,
rules are the preferable first implementation; the model's value on ambiguous
streaming incidents remains unproven.

The next bounded test compares inference runtimes at identical weights. Future
RL collection should target incidents that rules cannot already resolve, with
held-out mechanism families, declared feedback needs, replayed wait outcomes,
and behavior probabilities collected on the actual training runtime.

[Machine audit](audit.json) and [per-run measurements](measurements.csv) retain
trial identifiers, artifact hashes, actual judge start times and feedback status.
[Reproduction instructions](REPRODUCE.md) identify the source and local raw record.
