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
