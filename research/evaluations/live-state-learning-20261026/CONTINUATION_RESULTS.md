# Base versus continued SFT: partial replication

**Latest terminal audit:** R10 stopped at a workflow boundary for the user's
review and released its A100 at **2026-10-27 10:58:46 UTC**. It added eight
attempts: six verified completions and two SFT workflow completion failures.
The original cohort now has **55 attempted assignments: 49 verified, four
earlier infrastructure failures and two workflow failures; nine remain
unstarted**. All 56 R10 native starts are closed. The user subsequently approved
continuation, and R11 has launched for exactly those nine unstarted IDs under
the unchanged R9 parent deadline and cumulative spending ceiling. All three
[saved prediction probes passed](continuation-r11-model-qualification.json)
before timed collection; the first remaining rules/source-binding assignment
was running at the 11:20:25 UTC snapshot.

The [R11 manifest](continuation-r11-manifest.json),
[registration](continuation-r11-registration.json),
[physics qualification](continuation-r11-qualification.json) and
[launch record](continuation-r11-launch.json) retain the exact replacement phase.
The first allocation POST lost its transport without returning an endpoint;
a subsequent account query found zero allocations. One retry on the same route
succeeded. The failed allocation is preserved, and no scientific ID was retried.
Registration and all operation hashes were verified before allocation.

[The terminal R10 record](replication-through-r10.json) reports zero audit
violations. The registered SFT-minus-base restricted-time estimate is
**+36.3 seconds** (95% interval **−113.2 to +200.9**), from 14 pairs in eight
mechanism families. The predefined whole-infrastructure-block sensitivity gives
**+6.1 seconds** (−114.9 to +127.3), from 11 pairs in seven families. The primary
SFT-minus-worker-only estimate is −0.3 seconds (97.5% interval −157.7 to +155.5),
and SFT-minus-rules is +42.2 seconds (−125.5 to +204.2). These partial estimates
establish no overall advantage. Both scientific failures stay in the primary
and sensitivity analyses with the registered 650-second penalty.

The operator pause caused the model transport to close before terminal saved
probability probes could finish. The failure is retained explicitly; R10 has
successful initial model qualification but no successful terminal probability
qualification. No scientific assignment was interrupted by this pause.

Both resumed SFT source-binding workflows were **not verified**. Their physical
controls succeeded and judge-authorized repairs were applied, but each worker
exhausted its four permitted turns without a final report and left one required
help return unacknowledged. Their observed 327- and 361-second durations are not
timing wins. [The first complete outcome and feedback trace](continuation-r10-source-binding-outcome.json)
and both audited records are retained. These are failures under the registered
workflow budget, not P40 transport failures or failed numerical controls. They
do not alone isolate the causal contribution of model decisions versus the
controller's coordination limits.

**Historical R9 audit:** R9 completed nine additional workflows, all verified, then
stopped when a read-only P40 readiness check failed before the next assignment.
No additional scientific attempt failed. At that point there were **47 recorded original
outcomes: 43 verified and four earlier infrastructure failures; 17 IDs remain
unstarted**. The runtime was released at **2026-10-27 08:39:51 UTC**, and its
temporary local control task and failsafe exited. R10 was a separate owned
allocation; its outcomes are not included in the historical terminal R9 figures.

[The terminal R9 audit](replication-through-r9.json) reports zero consistency
violations. Its partial registered SFT-minus-base restricted-time estimate is
+28.5 seconds (95% interval −137.8 to +212.0). The original whole-infrastructure-block
sensitivity gives −8.0 seconds (−137.1 to +121.5). Neither establishes an overall
gain. The [17 remaining assignments](continuation-unstarted-after-r9.json) are
prepared without replaying any attempted ID. The preflight retained exit code
255 but discarded stderr, so its exact cause is undetermined; a subsequent
identical read-only check succeeded. The exception also skipped the final
probability-probe section. Initial model qualification passed, but terminal R9
probability qualification must not be claimed.

The [R10 manifest](continuation-r10-manifest.json),
[registration](continuation-r10-registration.json),
[qualification](continuation-r10-qualification.json) and
[launch/recovery record](continuation-r10-launch.json) preserve the resumption.
The first registration transfer failed before host startup. Allocation still
obtained a guarded runtime, but initial startup returned nonzero; inspection
confirmed that no campaign, native budget or registration had been created.
Registration and startup were then completed on that same owned runtime. The
initial failure record remains unchanged; no scientific assignment was retried.

Historical R8 collection stopped on **2026-10-27 at 06:17 UTC**. Through R8,
**38 of 64 original assignments were attempted: 34 verified and four affected by
infrastructure failures**. Twenty-six original assignments were then unstarted.
R8 contributed eight attempts, seven verified, before a P40 SSH connection
timeout. Its audit reports zero consistency violations. That model runtime was
released automatically. R9 has since resumed the unstarted assignments on a
fresh, separately bounded runtime and later stopped as described above. Its
outcomes are not included in the historical R8 analysis below.

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

At **2026-10-27 08:34 UTC**, eight R9 workflows had completed and passed their
per-workflow verifiers. Their controller receipts match their final outcomes,
quality receipts match, and their native starts are closed. Together with the
retained earlier attempts, this gives **46 recorded outcomes: 42 verified and four
infrastructure failures**. This inspection is not the terminal campaign audit;
R9 is still collecting. [The eight outcomes and actual attention/return records](continuation-r9-interim-evidence.json)
are retained without recomputing or selecting a new model.

The newly completed four-arm artifact-consumer block took 337.3 seconds with SFT,
323.3 with base, 349.4 with rules and 341.6 with worker-only execution. All four
verified. SFT, rules and worker-only used five native starts; base used four.
SFT and rules each dispatched one automatic request. This block provides no
SFT timing advantage over base. The registered overall comparison awaits all
original assignments, with this block retained alongside favorable cases.

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
