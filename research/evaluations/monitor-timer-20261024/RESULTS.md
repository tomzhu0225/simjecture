# Quiet-stream observations and a pre-dispatch cooldown bug

The eight fresh timer-comparison trajectories all completed accurate numeric
reports. They do **not** establish a timer benefit: no timer event was actually
delivered in that cohort. Both timed fault runs requested repair before the
first timer, and later timer opportunities were suppressed while the judge was
active. Healthy workers resumed before fifteen seconds. Timing differences
between those runs therefore cannot be credited to the timer feature.

A separate grace-period mechanism check then exposed a host integration bug:
an alert deliberately deferred by the host still consumed the sixty-second
alert cooldown. The model repeatedly requested a judge on the new timer inputs,
but those requests were blocked. This was not a model choice to wait.
The original runs remain intact; the bookkeeping fix has regression coverage.

## Original eight-run comparison

[Protocol](PROTOCOL.md) froze healthy/fault × event-only/timed × two repeats,
identical fast-runtime base weights and downstream policy, before collection.
The public timer reports actual elapsed parked time and current receipt/process/
adapter state every fifteen seconds; it provides no recommended action.

| Condition | Timed observations enabled | Total seconds | Native starts | Actual timer events |
|---|---|---:|---:|---:|
| Fault | No | 139.31 / 115.26 | 5 / 4 | 0 / 0 |
| Fault | Yes | 120.89 / 111.68 | 4 / 4 | 0 / 0 |
| Healthy | No | 80.88 / 74.15 | 2 / 2 | 0 / 0 |
| Healthy | Yes | 78.38 / 77.27 | 2 / 2 | 0 / 0 |

All four fault runs obtained a native judge while the worker was parked. There
were no healthy judge wakeups, model errors or missed required feedback. One
event-only run incurred a stale additional judge after the protected bridge was
already repaired. The cohort used twenty-five native starts and sixteen actual
solver executions. These are fresh trajectories with varying native histories,
not matched private-state forks or evidence of learned policy improvement.

[Audit](audit.json), [timer-event audit](timer-audit.json) and
[per-run measurements](measurements.csv) preserve the complete original cohort.
A zero delivered-event count is an unexercised treatment, not a successful
negative test of the timer's effect on missed incidents.

## Original grace commissioning: retained integration failure

Two separately labelled commissioning runs introduced an explicit ten-second
transient-state grace period. The host discarded early coprocessor repair alerts
while preserving raw model choices and recording each override in
`GRACE_DEFERRALS.json`. Explicit worker repair remained available. These are
prescribed host decisions, not learned model deferrals.

| Commissioning arm | Full task time | Native starts | First contradiction to judge | Fallback |
|---|---:|---:|---:|---|
| Event only | 202.92 s | 6 | 94.44 s | Yes |
| Timed | 224.92 s | 8 | 73.86 s | Yes |

Both reports were independently verified complete. The timed arm delivered five
clock observations. On those observations the raw model consistently chose
`request_repair_judge`; the first was already a new, post-grace input. However,
`AlertGate.accept` had marked the initial discarded alert as consuming cooldown.
New correct choices were suppressed until that reservation aged out. Repair
then completed too late to avoid fallback. The timed run also incurred two
stale additional judge wakes; its worse outcome is not evidence that the model
preferred to wait. [Original commissioning audit](commissioning-original-audit.json)
retains the two outcomes, separate from the eight-run comparison.

The fix adds `AlertGate.defer_before_dispatch(alert)` and invokes it only when
the grace fixture discards a route before dispatch. It releases that reservation
and fingerprint without clearing a newer alert's cooldown. Default routing is
unchanged. Regression tests reproduce the blocked retry and protect against
out-of-order release. Raw policy choice, host eligibility override and actual
native dispatch remain distinct records; future reward attribution needs all
three.

## Corrected timed mechanism: one verified complete loop

At source `7a298a0`, a single corrected timed check completed in **117.99 seconds**
with **four native starts**, **48.23 seconds parked**, no deterministic fallback,
no duplicate judge wake and no missed required feedback. Its numeric report
matched independent saved-diagnostic analysis. The first actual judge started
19.13 seconds after the public contradiction.

Two initial raw model judge requests were host-deferred at contradiction ages
4.02 and 8.04 seconds. The first timer observation then produced another actual
model judge choice. Its exact packet hash matches the dispatched authority's
incident; that judge granted the scoped repair, the proposer passed fixed host
checks, and the original worker resumed and acknowledged the actual repair.
[Corrected temporal audit](commissioning-corrected-audit.json) binds those raw
choices, overrides, timer event, authority packet and final verified report.

This is one deliberately exercised mechanism check, not a corrected randomized
event-only comparison, an efficacy estimate or an RL improvement. The original
two broken-fixture results remain recorded. Their extra recovery calls left
fifteen starts under the unchanged 240 cap, so the protocol was amended before
corrected collection to one case requiring twelve reserved slots. No resource
allowance was increased. All 229 experimental native processes have now exited,
the native lease is closed, and further GPU checks replay recorded inputs only.

## Scope and replay

Collection sources: `c98624c` for the original eight, `8e6695a` for the original
grace commissioning. Their native parents had imported those versions before
subsequent additive code changes. The corrected source and manifest are retained
with its separate record. All stages preserve the original numerical criteria
and use real native Astra roles and actual bounded WarpX jobs. Scientific
verification checks reporting accuracy and coverage, not independent correctness
of every diagnosis. No new adapter is trained.

Raw local roots are `artifacts/timer-live-20261024`,
`artifacts/grace-live-20261024` and `artifacts/grace-corrected-20261024` in the
research worktree. Each retains public events, exact model packets/actions,
actual simulation output/receipts, native start accounting, scoped authority
outcomes, feedback ledger and report digests. `MODEL_RELEASE.json` records owned
server cleanup. The unamended original `RESULTS.json` files remain local.

Recompute a study's measurements with `scripts/audit_parked_study.py --root ROOT
--budget artifacts/paired-20261024/native-budget.json --output NEW_OUTPUT` under
the root `.venv` (script path under `packages/simjecture-monitor`). Run fresh
collections with `run_heartbeat_study.py` and a new bounded lease/output root.
The original comparison waits for the four runtime servers to release; grace
commissioning uses `--grace-commissioning` and a previous single-server study.
The corrected single check additionally uses `--timer-only`. Never overwrite an
old root or reuse its expired lease. The protocol records the resource-driven
amendment from two proposed corrected cases to one; the total240 cap was not
increased.
