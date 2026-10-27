# Base versus continued SFT: collection in progress

Snapshot: **2026-10-27 03:43 UTC**. Eighteen continuation episodes have completed;
all passed the frozen per-episode workflow, numerical and report verifiers.
Together with the two preserved earlier attempts, these cover 20 of the original
64 assignments. One earlier base attempt failed at its first provider call before
any scientific action. It remains in the primary analysis. The full registered
audit and comparisons await terminal collection; this is an interim inspection.

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
Continue all originally assigned cases under the fixed resource bounds, retain
failures, and calculate the registered family/repetition comparisons only after
collection stops. Equal observed verification counts will not prove population
equivalence in scientific quality.

A future prospective comparison should test whether inexpensive fixed early
expert attention can obtain the same benefit. The current observations do not
separate learned selection from the benefit of earlier parallel expert advice.
Such an arm would be a separate study, not an addition to the current assignment
manifest. Quiet-family attention remains a proxy for unnecessary interruptions,
not an adjudicated false-alert rate.

## Resource continuity

Inference remains on the remote A100 and physics on the remote P40s. Local
control processes were lost in Windows/WSL restarts while remote collection
continued. Credential renewal was restored before the remote guard's expiry
cutoff. A temporary Windows task, `Simjecture-R7-20261027`, runs a bounded
credential/release check every ten minutes, expires at 09:34:48 UTC, and is
configured for automatic deletion one minute later. The check returns after
renewal; superseded resident helper processes have been stopped. It adds no
local model or simulation work.
The remote guard retains the original continuation deadline and spending ceiling.
