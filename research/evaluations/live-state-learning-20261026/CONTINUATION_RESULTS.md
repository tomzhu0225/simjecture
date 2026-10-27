# Base versus continued SFT: partial replication

Latest fully audited collection stopped on **2026-10-27 at 06:17 UTC**. Through R8,
**38 of 64 original assignments were attempted: 34 verified and four affected by
infrastructure failures**. Twenty-six original assignments were then unstarted.
R8 contributed eight attempts, seven verified, before a P40 SSH connection
timeout. Its audit reports zero consistency violations. That model runtime was
released automatically. R9 has since resumed the unstarted assignments on a
fresh, separately bounded runtime; its pending outcomes are not included in the
terminal R8 analysis below.

[The terminal evidence](replication-through-r8.json) retains all 38 audit records,
the unchanged registered analysis, transport reconciliation and resource-release
receipt. The [remaining assignment list](continuation-unstarted-after-r8.json)
contains only the 26 unstarted IDs. The separately frozen
[R9 manifest](continuation-r9-manifest.json) and
[launch record](continuation-r9-launch.json) govern their resumed execution.
Failed attempts will not be replayed or replaced.

| Partial registered comparison: SFT minus baseline | All-attempt estimate | Interval | Whole-infrastructure-block sensitivity | Interval |
|---|---:|---:|---:|---:|
| Pretrained base | +7.6 s | −171.1 to +207.8 s (95%) | −12.4 s | −166.5 to +145.4 s (95%) |
| Rules | −41.4 s | −184.9 to +77.5 s (97.5%) | −11.4 s | −137.7 to +107.9 s (97.5%) |
| Worker only | −78.1 s | −225.0 to +73.0 s (97.5%) | −49.7 s | −190.5 to +104.9 s (97.5%) |

Negative differences favor SFT. These estimates weight mechanism families equally,
then repetitions within family, and use the registered hierarchical bootstrap.
They measure restricted completion time, with unsuccessful attempts assigned
650 seconds. The base comparison has ten paired attempts from seven families;
the other two comparisons have nine pairs from six families. Unmatched records
remain in the audit. The sensitivity excludes entire infrastructure-affected
blocks 01, 08 and 10, leaving seven complete four-arm blocks from five families.
It is conditional on those exclusions and does not replace the primary analysis.
Every interval includes zero: this partial study establishes no overall advantage.

For an accessible descriptive view, those seven unaffected blocks have mean
verified times of **268.2 s SFT, 294.3 s base, 291.9 s rules and 322.7 s worker
only**. These equally weighted episode means differ from the registered
family-weighted estimates above. They are not the final 64-assignment result.
All four arms verified in these seven blocks; this does not establish population
equivalence in scientific quality. SFT admitted attention in two of five
quiet-family episodes, which is an interruption proxy, not an adjudicated
false-alert rate.

## R9 continuation

The fresh runtime restored the same continued-SFT adapter and pretrained-base
comparator on an A100-SXM4-80GB. All three saved prediction probes passed before
the first scientific assignment, with maximum probability discrepancy below
`6.2e-8`; [the fresh checks are retained](continuation-r9-model-qualification.json).
Collection began at **2026-10-27 07:29:52 UTC**. The scientific source,
worker instructions, decoder, thresholds and original assignment order are
unchanged. This is inference and evaluation, with no optimizer updates.

The new lease ends at **2026-10-27 15:21:17 UTC**, has a 55-compute-unit ceiling,
and permits only the remaining 469 native starts after 170 retained starts and
one successful R9 authentication preflight. The original overall ceiling remains
640. The first two assignments complete the already infrastructure-affected
block 10; the remaining six blocks each contain all four arms.

The P40 connection uses a study-specific SSH alias permitting three TCP
connection-establishment attempts. An established remote command is never
replayed. Both original plasma controls passed before launch using the same
executable and diagnostic reader. The frozen wrapper's 180-second transport
limit remains. A first read-only setup check found an incorrectly formatted
host-key alias; it submitted no solver or native job and is retained separately.
Strict key verification remains enabled after correcting the alias.

[Registration](continuation-r9-registration.json),
[physics qualification](continuation-r9-qualification.json) and the exact
`continuation-r9-operations/` scripts preserve this phase. A remote release guard
and a temporary Windows credential/deadline task protect its resource bounds.
The first scheduled check exited early; a manual renewal, a subsequent invocation
through Task Scheduler, and its normal ten-minute trigger all completed
successfully. Its initial termination cause remains undetermined.

The first resumed worker-only `recovered_history` assignment subsequently
completed and passed all workflow verifiers in **404.9 seconds**. Both original
plasma controls ran successfully, and the worker reconciled its required help
before finishing. [Its complete outcome and physics receipts are retained](continuation-r9-first-workflow.json).
This is one new execution, not evidence of a model effect. It belongs to block 10,
which remains excluded from the registered infrastructure sensitivity because of
the earlier SFT transport failure.

## Earlier trace inspection

Historical snapshot: **2026-10-27 03:43 UTC**. Eighteen continuation episodes had completed;
all passed the frozen per-episode workflow, numerical and report verifiers.
Together with the two preserved earlier attempts, these cover 20 of the original
64 assignments. One earlier base attempt failed at its first provider call before
any scientific action. It remains in the primary analysis. The full registered
audit and comparisons were pending at that snapshot; the newer partial audit is above.

The exact adapter is the continued-SFT checkpoint behind the earlier 224-second
mean. No new training, checkpoint selection or scientific-host change was made.
Both model arms use the same pinned pretrained base, with its adapter disabled
for the base comparator. All native scientific workers use the same configuration.

| Completed family | Repeats per arm | Continued SFT | Pretrained base | Rules | Worker only |
|---|---:|---:|---:|---:|---:|
| Publication retry | 2 | 175.6 s | 423.1 s | 412.4 s | 418.1 s |
| Announced quiet period | 2 | 301.3 s | 174.4 s | 172.7 s | 191.9 s |

These are mean verified completion times. They are descriptive results for two
previously explored mechanisms, not independent scientific domains or a final
population effect. The first artifact-consumer block also has completed results,
but its base arm was the earlier provider failure; it cannot supply a clean
timing comparison. All 18 individual continuation outcomes, timing, native starts,
attention counts and selected public help traces are retained in
[the interim evidence](continuation-interim-evidence.json).

## What the traces show

In both publication-retry episodes, SFT requested one early automatic worker-help
intervention and used three native starts. The base, rule and worker-only episodes
each used six native starts. In the first traced SFT episode the director explained
that the diagnostic publication delay was expected and already resolving. It
returned advisory guidance, made no source repair, and did not spawn a temporary
helper. Normal process completion resumed the main worker.

In the corresponding base episode, the completed bundle prompted the main worker
to request a required technical source/arithmetic check. The director spawned a
temporary helper with a 120-second deadline. That helper timed out; the worker
also resumed at the experiment's common 90-second fallback before the helper
deadline. This sequence accounts for substantial elapsed time and additional
native starts. Early reassurance is a plausible explanation for avoiding later
help, but one trace does not establish that counterfactual.

The quiet SFT episodes took 186.4 and 416.1 seconds. The slow one dispatched **zero
automatic alerts**. Its main worker independently requested a technical check of
the already completed bundle, followed by a helper timeout and extra resumptions.
The model proposed one director request, but the host rejected it as ungrounded.
This is not evidence that an admitted SFT false alert caused the delay. It is
evidence that stochastic main-worker help choices can dominate end-to-end timing.

The 90-second fallback is explicitly present in the experiment's registered
driver and tests, including while waiting for help. The production research
supervisor instead checks durable wait subjects and stays parked until a wake
condition. This inspection did not establish an independent upstream scheduling
bug. The running study retains its registered fallback in every arm.

## Remaining inference

The publication-retry gain is large enough to investigate seriously. The quiet
results prevent treating those first favorable cases as a general SFT win.
Continue only unstarted originally assigned cases under explicit resource bounds,
retain failures, and preserve the registered family/repetition analysis. Equal
observed verification counts will not prove population
equivalence in scientific quality.

A future prospective comparison should test whether inexpensive fixed early
expert attention can obtain the same benefit. The current observations do not
separate learned selection from the benefit of earlier parallel expert advice.
Such an arm would be a separate study, not an addition to the current assignment
manifest. Quiet-family attention remains a proxy for unnecessary interruptions,
not an adjudicated false-alert rate.

The subsequent [worker-instruction audit and prospective controls](FOLLOWUP_CONTROLS.md)
identify another limitation: the inherited general research guidance describes
an execution/review path that the benchmark-specific task overrides. Whether
that framing contributes to discretionary help requests remains unmeasured.
The current comparison keeps those common instructions unchanged.

## Resource continuity

During collection, inference used the remote A100 and physics the remote P40s. Local
control processes were lost in Windows/WSL restarts while remote collection
continued. Credential renewal was restored before the remote guard's expiry
cutoff. The temporary Windows control task was unregistered after observing the
remote release receipt. That model runtime is released and its recorded study
actors exited. R9 uses the new bounded lease described above; the old lease
was not extended.

Two separate local CPU plasma controls have passed the original numerical checks
and closely reproduced the P40 references. This qualifies a numerical fallback
for those small controls, not a commissioned remote-worker-to-local execution
path. Training remains remote. See [the transport record](TRANSPORT_RECOVERY.md)
for backend differences and resource measurements.
