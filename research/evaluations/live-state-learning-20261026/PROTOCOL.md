# Live scientific observation audit

This phase checks the mismatch between the authored training snapshots and the
actual observation stream before another optimizer update. It uses saved data
and native read-only judgments; no model training or scientific simulation is
part of this audit. Later model-effectiveness evaluation requires fresh runs.

Select the first, middle and last eligible observation from each of the seven
completed worker-only episodes of `qualified32-clean`, plus the corresponding
three observations from the parked commissioning episode. Eligibility requires
a submitted parked-worker state and receipt inside a recorded parking interval.
Retain all exclusion reasons. This selection uses neither model predictions nor
future scientific success labels. The earlier preparation attempt stopped on
an inconsistent active-state record before any native judgment; it is preserved.

Two separate ephemeral `gpt-6-astra` high-reasoning auditor contexts assess each
of 24 observations. Each call handles four observations, giving 12 assigned
calls. Deterministic reviewer-specific shuffles use seeds `202610260497` and
`202610260498`. Auditors see the actual public model view and answer schema,
not the fixture family, original proposals, admissions, later outcomes or one
another's judgments. Shell/execution and web tools are disabled. Observations
remain data, not instructions to the auditor.

Each judgment gives the five proposed answer fields, acceptable route
alternatives, certainty, whether attention before the ordinary terminal event
or 90-second fallback appears warranted, and an evidence-based reason. These
are model judgments, not human ground truth or measured intervention returns.
Report disagreement and uncertainty; do not turn consensus into a causal label.
Validate every candidate and citation against its own visible input.

The remote coordinator freezes row/provenance, prompt, schema and runner hashes
in `live-label-audit-v2/PLAN.json` before execution. A separate native lease
allows at most 18 starts, one per invocation, at most two concurrent calls and
one hour overall. The initial 12 calls consume the existing original allowance:
611 of 640 starts were used before this audit. Six slots are reserved for
explicitly recorded adjudication or diagnosed recovery, not automatic retries.
Each native call is bounded to 360 seconds. Stop scheduling after a failed pair
and preserve all failed/unstarted assignments. No Colab allocation is needed.

These historical trajectories become development material for subsequent
training design. Their previously reported workflow results stay unchanged,
but they cannot be reused as untouched validation of a model trained from these
judgments. Labels are not automatically eligible for optimization: first audit
the actual outputs, uncertainties, conflicts and evidence binding.

## Operational amendments

The initial pair stopped after one provider 429 failure and one success. A
separate recovery controller, frozen at 09:09:50 UTC, retained the successful
response and retried/scheduled the outstanding assignments serially, with at
least 60 seconds between starts. Two calls succeeded, then a further 429 stopped
that controller. A second recovery controller was frozen at 09:17:14 UTC with a
120-second gap after each completed call. It also stops on any failure.

Both amendments keep the original prompts, schema, assignments, overall native
start ceiling and deadline. Failed attempts remain in their original folders;
successful responses are not overwritten or rerun. A failed provider request is
not a scientific judgment. Separate recovery plans record their runner hashes
and the original plan/status hashes. The postprocessor verifies input hashes,
recovery-to-original assignment binding, candidate/citation binding, coverage
and absence of tool use before summarizing agreement. These scheduling changes do not create additional
independent reviewers or relax optimizer eligibility.
