# Monitoring coprocessor: overnight exploration, 23–24 October 2026

The event-monitoring and real-return learning loop works as an experimental
integration. A pinned 4B policy can observe real Codex workers and WarpX
outputs, wake assistance or an independent repair judge, and be updated from
measured downstream returns. These experiments **do not establish that the
model improves scientific work or beats simple rules**. Keep this work on the
research branch until a larger, better controlled evaluation establishes value.

The production helper workflow was separately merged in
[PR 45](https://github.com/tomzhu0225/simjecture/pull/45). This package uses that
workflow but does not activate a coprocessor or harness self-modification in
ordinary studies.

## What actually ran

The policy was `internlm/Intern-Decision-4B`, revision
`38c9dafbbef52dd04bae943c0c6ac918419adfd5`, served resident in BF16 on a Colab
A100. Workers, directors, judges and repair proposers used native
`gpt-6-astra` sessions on the local host. Native-worker credentials stayed on
the host. WarpX executed on the local RTX 4000 Ada; its saved plots were checked
by a separate analysis process using the original tolerances.

Four task families exercised nominal 64/128-cell controls, the existing
256-cell charge-residual discrepancy, an injected worker-owned analysis
recursion bug, and an injected private process-status adapter bug. The latter
two are engineering fault injections. They are not newly discovered solver
bugs. The charge discrepancy remains unresolved; a reproduced failure is not
new scientific evidence or permission to weaken a criterion.

The monitor tails public completed tool activity and incremental diagnostic
files. A timestamp audit found observations before process completion for 51
of the 52 observed simulation streams across the three main cohorts. A one-second polling loop submits inference only when substantive
observations or host state change. It excludes private reasoning. A bounded
4,096-token view records omitted events and prompt hashes. This is a tested
observation allowance, not a measurement of the checkpoint's maximum context.

The four actions are `defer`, `request_worker_help`, `wake_director`, and
`request_repair_judge`. Explicit worker help and repair requests remain
available in every comparison arm. The model cannot grant repair authority.

## Initial comparison: useful engineering evidence, confounded efficacy test

Twelve fresh trajectories covered four tasks with an unchanged greedy model,
simple public-state rules, and a 60-second periodic director wake. They ran
30 actual WarpX simulations. Eleven final reports agreed with independently
recomputed numerical diagnostics.

| Policy | Capable-agent launches | Completed director decisions | Authority requests | Monitor errors |
| --- | ---: | ---: | ---: | ---: |
| Unchanged 4B | 20 | 7 | 4 | 26 |
| Rules | 21 | 8 | 3 | 0 |
| Periodic | 26 | 15 | 1 | 0 |

A launch is a native worker/judge start, including failed invocations. It is
not a billable request count. Authority requests can launch a judge and a
repair proposer. Some provider token counters were missing; recorded usage
remains a lower bound. These counts do not establish a cost reduction.

Three limitations prevent a clean efficacy interpretation:

- The model arms include an SSH outage. All 26 monitor errors are retained.
- The nominal task originally advertised four allowed simulations while its
  wrapper enforced two. Alerts after that mismatch are not clean false alarms.
- The original two-turn driver could accept a provisional report before late
  repair feedback reached the worker. The rules/harness trajectory retained
  such a stale report after an authority failure and later worker-requested
  repair. This is not evidence that the model outperformed the rule detector.

The experimental driver was corrected before the learning cohort: consistent
simulation limits, up to three parent turns, asynchronous idle director calls,
response-arrival timestamps, and explicit continuation after help or repair.
Two learning-collection pilots were excluded together after diagnosing a
host-side response-retrieval delay. Their artifacts remain retained.

## A real coprocessor-to-repair-to-worker chain

In clean sampled episode `harness-97`, the monitor observed a completed
zero-exit simulation being classified as running. It requested the independent
judge about **37 seconds before** the worker wrote its own repair request.
The sampled action agreed with the unchanged policy's greedy action on that
packet. The judge inspected the evidence and permitted only `bridge.py` for
180 seconds. A separate read-only proposer returned the replacement; the host
checked original hashes, scope, expiry and isolated invariants, then applied it
about **76 seconds after** the alert. The original worker resumed, reran the
affected analysis and produced a report matching the saved diagnostics.

This demonstrates feasible orchestration. It does not establish how much
completion time the intervention saved: the worker was also capable of asking
for help, and there was no paired counterfactual continuation.

The authority mechanism also rejected healthy-component edits. In the clean
learning cohort, repeated alerts after a successful repair led to fresh denials.
This protects the file but still wastes attention. Incident resolution needs a
durable identity; cooldowns and packet hashes alone do not prevent stale
failures from provoking another judge.

There was a more revealing failure in `harness-71`: sampling selected a judge
call while the greedy policy would have deferred and the observed stream had
not yet shown the defect. The judge discovered the planted bug by inspecting
its source. A completion-only reward can credit this premature investigation.
Future training must assess whether the alert was grounded in contemporaneous
evidence, and charge for unjustified escalation, alongside downstream outcome.

## Real-return adaptation

Four eligible episodes (two harness and two recoverable-analysis trajectories)
provided **119 sampled decisions**, with no model-service failures. All four
reports matched raw numerical diagnostics. Three satisfied the stronger
report-and-feedback closure criterion; one did not, and its negative return
was retained. Its numerical work was correct; an extra inferred help request
remained unfulfilled and was canceled at shutdown after the final report.

The prospective utility was
`R = Q - 0.02*N - 0.1*min(T/650, 1)`, where `Q` requires independently verified
metrics, required controls and delivered final feedback; `N` counts capable-
agent starts, and `T` is study elapsed time. This is an explicitly chosen
research utility, not a monetary estimate or scientific truth score. Feedback
closure is currently a timestamp-based proxy: the final report must postdate
recorded help resolution and authority outcomes. It does not establish that the
worker understood every message. Explicit durable acknowledgments would be a
better training signal, and cancellation bookkeeping should be distinguished
from delivery of new information. The original rewards remain unchanged.

Returns were 0.7761, 0.7862, -0.2372 and 0.8032. LoRA updated 7,372,800 parameters
with a clipped categorical policy-gradient objective, a within-family
leave-one-out return baseline and KL regularization against the unchanged
policy. Eight optimizer steps made two passes over the four episodes.

Exact training prompts matched the logged behavior prompts. Initial action
probabilities reproduced the recorded distribution within 1.2e-7. Gradients
were finite and nonzero. Saving and reloading the adapter reproduced the
checked predictions exactly. Training took 805.5 seconds and peaked at
12,157,827,584 allocated CUDA bytes. Adapter weights, optimizer state, RNG state,
training history and source bundle were retained and copied back with hashes.

This is a real policy update from actual worker returns, not a scripted reward
table. Four episodes are far too few to infer generalization; there is no
equal-step supervised control and no claim of RL superiority.

## Fresh base/adapter evaluation

All four fresh trajectories completed with independently matching metrics,
no undelivered final feedback and no monitor-service errors. They ran ten
actual WarpX simulations. Both policies deferred on every observed decision:
44 base decisions and 35 adapted decisions. Each trajectory used one capable
worker launch and no director or authority calls.

| Case | Base elapsed seconds | Adapted elapsed seconds | Outcome |
| --- | ---: | ---: | --- |
| Nominal controls | 184.7 | 181.8 | Both report the original passing controls correctly |
| Charge discrepancy | 278.9 | 260.3 | Both preserve and report the original failure |

No learned intervention occurred, so the small elapsed-time differences cannot
be attributed to improved routing. On an identical probe, adaptation changed
the defer probability from 0.90765 to 0.91084; the argmax remained unchanged.
Checkpoint configuration and adapter-file hashes establish that the second
endpoint really loaded the saved adapter.

These task families were excluded from optimization but were seen during
exploratory design. This is not a confirmatory held-out benchmark. The cohort
checks normal behavior and artifact integrity; it establishes no RL benefit.

## Local deployment and resource accounting

The full pinned checkpoint and trained adapter are now verified on the local
host. Both ran on the RTX 4000 Ada. Twelve identical observation packets,
1,070–4,027 tokens each, were evaluated twice per policy against saved A100
predictions. Both local policies matched the A100's chosen action on all
24 checks.

| Local policy | Resident allocated VRAM | Peak allocated VRAM | Warm median decision time |
| --- | ---: | ---: | ---: |
| Base | 8.55 GiB | 9.49 GiB | 4.03 seconds |
| Adapted | 8.58 GiB | 9.52 GiB | 4.62 seconds |

An unrelated simulation was concurrently using the GPU; its pre-benchmark
utilization was 99%. These are contended measurements, not isolated speed or
power estimates. Optional optimized causal-convolution and gated-delta kernels
were absent, so the model used reference PyTorch implementations. The first
local model load took 75.7 seconds; the subsequent adapted load took 8.3 seconds.
Resident serving is essential for frequent observation.

The local probabilities were not identical to the A100 values: maximum absolute
differences were 0.0181 for base and 0.0125 for adapted. Agreement of the selected
action on this small set does not guarantee agreement near decision boundaries.
Do not silently relax the training behavior-reproduction check when changing
hardware or kernels.

A 4B coprocessor fits this local GPU, but it consumes substantial VRAM alongside
the simulation. Low marginal orchestration cost remains a measurement question.
One-second stream polling is cheap; it does not imply one model inference per
second. Inference is asynchronous and triggered by changed evidence.

Colab was released at 2026-10-23 17:00:40 UTC. The subsequent account query
reported **zero active assignments**, **0.00 CU/hour**, and a balance decrease
of **23.15 compute units**, below the 40-CU ceiling. This is the reported balance
change at that timestamp. All recorded native experimental workers and judges
had exited. Model processes were also stopped after the local measurements.

At the observed allocation rate of 6.77 CU/hour, a hypothetical 1,000-CU pool
covers about 148 A100 runtime hours. Colab is suitable for bounded training and
evaluation; an always-on monitor needs a separate resource plan. The local
checkpoint cache avoids repeating this night's transfer overhead.

## Scope of repair authority

The repair target is a private test adapter, not the installed Simjecture
supervisor. Judge and proposer sessions use read-only native execution. The
host applies a single file atomically only after fixed checks run under
Bubblewrap without network or access to host user files. Grants expire and are
single-use; rollback refuses to overwrite later edits. A regression test now
ensures a retried judge's grant cites the successful response trace. No affected
historical successful-retry grant was found in these cohorts.

The parent worker still uses Simjecture's existing same-account cooperative
execution model. This prototype is not a complete security boundary against
that worker. The observer also shares the supervisor's event loop and lacks
durable recovery. A fully wedged supervisor cannot reliably be rescued by this
observer. Production repair would need an independent watchdog, a protected
capability service, verified restart/rollback, and operator-configured scope.

## What to develop next

Keep the model's job narrow: identify evidence that merits attention and
route it, while the capable agent diagnoses and decides the scientific action.
The promising target is an otherwise unattended stream: a silent worker loop,
a long simulation with an evolving diagnostic problem, or conflicting results
from parallel workers. The present short solver runs and capable workers often
resolve issues without needing a second agent.

Before more RL, build a prospective incident benchmark with long healthy
stretches and explicit onset/resolution times. Include non-keyword cases where
rules can plausibly miss a problem. Compare identical workers and permissions
under rules, unchanged model, supervised adaptation and RL, with multiple
trajectories. Measure grounded wakeups, missed actionable incidents, time to
useful intervention, final feedback delivery, and total capable-agent/GPU use.

Cross-worker contradiction detection, drift from research requirements and
recognition of obsolete work remain candidate extensions, not implemented
validated capabilities. An independent observer and incident state machine
have higher priority than expanding the action menu.

## Validation

Eighteen local contract tests passed, including actual isolated repair checks.
Repository lint and whitespace checks passed. CI additionally exercises the
existing deterministic core, documentation, Windows boundaries and the WarpX
instrument. The research implementation and report are in
[draft PR 46](https://github.com/tomzhu0225/simjecture/pull/46).

The comparison driver limited concurrent parent trajectories to two; helper,
director, judge and proposer roles could add concurrent processes. A global
cap over all capable-agent roles is not implemented by this research package.

## Records

A [subsequent reward audit on 24 October](../monitor-reward-20261024/REVIEW.md)
found case-labelled identifiers in 64 of the 119 actual model views and large
sensitivity to the binary feedback condition. It adds qualifications and a new
prospective design; the original trajectories, rewards and adapter remain frozen.

The machine-local evidence root is
`/home/tomzhu0225/src/simjecture-monitor-coprocessor/artifacts/overnight-20261023`.
Raw native traces, full learning packets and model files are deliberately
outside Git. See [measurements.json](measurements.json), the
[prospective protocol](protocol.json), [learning protocol](rl_protocol.json),
[replay instructions](REPRODUCE.md), and
[package documentation](../../../packages/simjecture-monitor/README.md).
