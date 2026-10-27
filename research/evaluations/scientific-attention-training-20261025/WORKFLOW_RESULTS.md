# Trained scientific attention models in real workflows

All 28 executed workflows completed with independently verified scientific
reports. Worker-only execution also solved all seven tested configurations, so
this cohort has no completion-rate improvement to attribute to a coprocessor.
RL did not improve on continued supervised training. The supervised model has
an exploratory timing signal against worker-only execution, but neither model
demonstrates a reliable timing advantage over the fixed rules.

[Workflow evidence](workflow-evidence.json) preserves the assignments, adapter
qualification, original audit, per-trial records and coverage accounting.
[Training results](TRAINING_RESULTS.md) report the separate static evaluations;
the 97% snapshot score is not this workflow's success metric.

## Frozen comparison and coverage

The planned comparison contains eight configurations and four arms. Seven
complete four-arm blocks ran on 26 October 2026. The final `recovered_history`
block never started because the predeclared rule requires 48 remaining native
starts before a new block. Those four unstarted assignments are reported
separately and do not enter completion denominators as failures.

Each configuration uses fresh parameters within a previously explored mechanism
family. Native Codex workers execute actual WarpX controls on the remote P40
host, then interpret an asynchronous diagnostic bundle and produce a report.
The environment includes controlled publication/progress delays; those delays
are not natural WarpX solver time. Independent verification recomputes the
original numerical quantities from saved fields and checks the report and
required workflow obligations.

All arms use source `352f18383fe71e06aaa3c972faefc092f0fa9ed6`, the same worker,
solver backend, permissions and budgets. Explicit worker help and repair
requests remain available in every arm. Automatic monitoring polls at a
five-second cadence while the worker is parked, with at most one discretionary
attention dispatch per workflow. Two workflows may run concurrently. The task
declares no retrieval question, so it does not test literature/knowledge lookup
utility or unrestricted monitoring of an actively working agent.

Continued-SFT and RL adapters share one resident base model on the same remote
A100. Both reproduce their saved probability probes before collection
(maximum discrepancy below 1.5e-7, qualification tolerance 1e-4). The weights and
host are unchanged throughout the cohort; no training or static benchmarking
runs concurrently with its timed trials.

## Completion, time and attention

| Setup | Verified complete | Mean elapsed seconds | Native starts, total | Automatic attention requests | Quiet configurations with automatic attention |
|---|---:|---:|---:|---:|---:|
| Worker only | 7/7 | 277.2 | 32 | 0 | 0/3 |
| Fixed rules | 7/7 | 265.1 | 31 | 4 | 0/3 |
| Continued SFT | 7/7 | 223.9 | 29 | 5 | 1/3 |
| RL | 7/7 | 227.0 | 31 | 6 | 2/3 |

There are no collector failures, model-service errors, or artifact/accounting
inconsistencies in the audit. No unconfirmed solver transfer triggered the
cohort's infrastructure stop. All 123 workflow native starts are closed; the
separate authentication preflight accounts for one additional start in the
validation lease. Native starts are process invocations across roles, not
provider request counts or a billing estimate.

The quiet configurations are progressing work, announced silence and publication
retry. Their alerts are a proxy for potentially unnecessary attention, not an
independent adjudication of false alerts. Three quiet configurations are too few
to estimate a low deployment false-alert rate.

## Paired differences and uncertainty

The primary audit compares RL with each baseline. It uses 10,000 paired
percentile bootstrap resamples, seed 20261026, clustered by the seven represented
mechanism families. There is one configuration per family and one execution per
arm/configuration. Negative time differences favor RL.

| RL minus comparator | Mean elapsed difference, seconds | Descriptive 95% interval | Mean native-start difference |
|---|---:|---:|---:|
| Worker only | −50.2 | [−108.6, +0.9] | −0.14 |
| Fixed rules | −38.1 | [−128.6, +46.9] | 0.00 |
| Continued SFT | +3.1 | [−3.6, +9.5] | +0.29 |

Every trial completes, so actual and restricted completion time coincide here.
The timing intervals include zero. The bootstrap completion difference collapses
to zero because every sampled completion indicator equals one; that degeneracy
does not establish population equivalence or rule out different failure rates.

A supplementary, exploratory calculation gives continued SFT minus worker-only
time of **−53.3 seconds**, interval **[−109.9, −4.3]**. Against rules it gives
**−41.2 seconds**, interval **[−134.5, +43.8]**. These supplementary comparisons
have no multiple-comparison adjustment and do not replace the nominated RL
comparison. They motivate a fresh replication rather than a release claim.

The raw audit retains generic descriptive text from the earlier eight-family,
two-configuration design. The actual arrays and bootstrap cluster count used
here contain seven families and one configuration each; the calculations above
use those actual records.

## Decisions and where time was spent

| Configuration | Rules | Continued SFT | RL |
|---|---|---|---|
| Progressing work | Observe | Observe | Wake director |
| Publication retry | Observe | Request worker help | Request worker help |
| Announced silence | Observe | Observe | Observe |
| Unstable update cycle | Request worker help | Request worker help | Request worker help |
| Wrong artifact pattern | Request worker help | Request worker help | Request worker help |
| Unit conversion | Wake director | Wake director | Wake director |
| Protected source selection | Request repair judge | Wake director | Wake director |

Rules are fastest on each of the four problem configurations in this cohort.
For protected source selection, rules route directly to the repair judge and
finish in 240 seconds with five native starts. Continued SFT takes 355 seconds
and eight starts; RL takes 370 seconds and nine starts. All ultimately produce
verified reports. This illustrates why detecting a problem and choosing a
useful intervention are separate evaluation targets.

The overall rule mean also includes two quiet runs with substantially more
native work despite no automatic alert. Such variation matters when each arm
has only one native-worker execution per configuration. A point mean cannot
identify whether an individual alert caused a time saving. Public-checkpoint
controls and repeated prospective workflow runs answer complementary questions.

## Interpretation and next experiment

This cohort supports a working optional attention integration and a possible
supervised timing benefit over worker-only execution on these fixtures. It does
not establish RL superiority, a win over strong rules, a low false-alert rate,
or transfer to unfamiliar scientific workflows. The earlier confounded
64-workflow comparison remains separate; its failed runs are not replaced with
these repaired-host outcomes.

The reward pilot used public checkpoints that resume an awake worker. The next
training comparison should collect decisions and outcomes from the actual
parked-worker lifecycle, with its ordinary terminal-event/fallback behavior as
the no-intervention control. It should retain the stronger rule baseline,
repeat native-worker runs, and include scientific mechanisms outside the
existing authored templates. [Research design](RESEARCH_NEXT.md) describes the
additional calibration and generalization evidence needed.

No model weights are published as a demonstrated scientific-workflow
improvement on the strength of this cohort. The A100 allocation was released
after collection and audit; scientific artifacts and exact adapter archives
remain on the remote coordinator. The local host ran no model inference or
scientific simulations during this validation phase.
