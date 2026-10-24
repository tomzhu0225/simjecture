# Declare helper feedback requirements before dispatch

All four fresh real-worker validation runs passed: two declared the helper's
result required, and two declared it advisory before dispatch. All four ran the
two actual WarpX controls and produced numeric reports agreeing with independent
saved-diagnostic verification. This closes a measurement gap; it does not show
an improved decision policy or determine whether a help request was necessary.

| Declared requirement | Total seconds | Worker turns | Native starts | Actual helper handoff |
|---|---:|---:|---:|---|
| Required, repeat 1 | 162.87 | 2 | 4 | Imported verified NOTES.md; acknowledged actual digest |
| Required, repeat 0 | 179.85 | 2 | 4 | Imported verified NOTES.md; acknowledged actual digest |
| Advisory, repeat 1 | 118.54 | 1 | 3 | Helper completed; no import or help acknowledgment |
| Advisory, repeat 0 | 118.01 | 1 | 3 | Helper completed; no import or help acknowledgment |

These task instructions deliberately differ in the obligation being validated.
The table is not a causal estimate that required help is slower or unnecessary.
All four temporary helpers returned real artifacts from frozen source context.
The two required workers imported through `lab.import_helper_artifact`, checked
the notes, and acknowledged actual returned feedback before finalizing. Advisory
workers finished their accurate reports without adding a turn solely to wait
for optional advice. The validation controller still reconciled helper lifecycle
and retained the late results. No required-feedback miss or unknown declaration
remained. Fourteen native agent starts and eight actual solver runs were used.

## Interface and boundaries

`lab.request_help(..., feedback_requirement='required' | 'advisory')` freezes the
explicit declaration with the question, attached file hashes and CONTEXT.json
before dispatch. Replaying the same key with a changed declaration is rejected.
The optional operator policy
`helper_policy.require_feedback_requirement=True` rejects a missing declaration
before queueing help. Without that opt-in, omission remains valid and preserves
legacy request IDs and hashes. Omission means unknown intent, not advisory intent.

The experimental feedback collector respects this declaration. Legacy
unacknowledged help without it still withholds a strict scalar reward. The old
32-continuation outcomes remain unchanged: five pairs were not retrospectively
made eligible. This change does not grant new repair powers or make the core
production finalizer automatically enforce experimental feedback obligations.

A declaration records intended obligation, not objective usefulness. A policy
could otherwise game the reward by marking difficult feedback advisory. Future
studies should pin safety/science-critical obligations in the operator protocol,
audit declarations and content, and measure help value against actual wait
outcomes. Merely acknowledging a digest does not prove advice was understood or
scientifically correct. This cohort validates lifecycle/provenance, not semantic
review quality.

[Protocol](PROTOCOL.md) was committed before collection at `0f06819`.
[Audit](audit.json) checks pre-dispatch frozen declarations, immutable context and
attachment hashes, actual artifact imports, feedback and final report digests.
Raw source is local under
`/home/tomzhu0225/src/simjecture-monitor-coprocessor/artifacts/feedback-v2-20261024`.
Each trial retains `VALIDATION.json`, native public events, request/context files,
helper results/import receipts, feedback ledger and saved scientific diagnostics.
The local `audit.py` regenerates this compact audit. Fresh runs use
`packages/simjecture-monitor/scripts/declared_help_trials.py` with a new output
root and newly prepared bounded native lease; do not overwrite this cohort.

The API/lifecycle subset passed 43 tests, including eight new declaration tests.
The scientific completion score verifies the original numeric report contract;
it is not scientific approval of the helper's notes. No new LoRA was trained.
