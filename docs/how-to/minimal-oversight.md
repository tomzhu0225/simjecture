# Methods and progress oversight in minimal mode

Minimal mode keeps planning, native tools, search, coding and exploratory calculations
with the worker. The host owns acceptance, provenance, deadlines and independent
review. A successful numerical process is not a supported scientific result.

New studies expose all available installed tools. Evidence that uses a scientific
instrument requires a short, source-bound methods review; unused tools require no
qualification work. Ordinary Python calculations do not acquire this gate just
because other tools are installed. An explicit operator requirement can require
methods review for every evidence run. Existing studies keep their saved policy.

## Commission, review, collect evidence

Use `lab.run(..., stage="exploration")` for commissioning and debugging. Exploration
receipts cannot be retrospectively relabelled as claim evidence. Then submit:

```python
method = lab.method(
    source="calculation.py",
    inputs=["diagnostics.py"],
    capability="flash-my-application",
    model="Resistive MHD; declared closure and neglected terms",
    geometry="Physical axes, domain, initial state, boundary conditions",
    observable="Operational definition of the measured event and falsifier",
    validation="Actual evolution benchmark, conservation and refinement evidence",
    rationale="Why this instrument; observed blockers versus anticipated difficulty",
    validation_experiments=["exp_commissioning_id"],
    blockers=[],
)
```

End the native turn so the host can review the proposal. The host also detects a
durable request and takes over after a short grace period if the CLI keeps running. `lab.status()` includes
its verdict. An approved method permits `lab.run(..., method=method["id"],
stage="evidence")`; it does not accept a scientific conclusion. Changes to its source,
listed dependencies or runtime identity require a revised proposal. Parameter cases
can vary under the same implementation; the later claim review checks their scope.

The reviewer receives frozen source, commissioning source/results, the original task,
and operator requirements. It should distinguish an isolated operator test from a
benchmark that evolves the actual solver. Physics validity remains a scientific
judgment; this is not an automatic proof of solver correctness.

Large source and result files are preserved through hashed references and paged
read-only retrieval. Director reviews can run alongside a worker without a periodic
forced interruption. See [operating settings](operating-limits.md) for the browser
controls, CLI and exact scope of these allowances.

## Optional explicit operator requirements

Pass `--requirements-file requirements.json` when launching a minimal study:

```json
{
  "require_method_review": true,
  "required_capability_prefixes": ["flash-", "warpx-"]
}
```

The requirements become immutable study state. Evidence must use a registered capability
whose name matches a listed prefix. Neither the worker nor the methods reviewer can
waive this rule. Prefix matching checks the selected runtime identity, not the physics
inside a binary; methods and claim reviews remain necessary. Native tools and exploration
are still available. Changing explicit task requirements requires a new study.

## Building a new runtime

### Solver development permission

New minimal studies **allow experimental solver development by default**. In
**Autonomous research → Edit proposal**, use **Allow experimental solver development**
to retain or disable this permission. The monitor's new-study dialog exposes the
same choice. CLI launches use `--allow-solver-development` (the new-study default)
or `--no-allow-solver-development`. The policy is frozen into the study contract;
resuming cannot change it. Continuation preparation inherits an explicit parent
choice and lets the operator change it for the new phase.

Permission covers separately named experimental solver builds. Preserve the reference
installation, record the need and validation plan, build in a writable fork, and retain
exact source/build identities. It does not authorize publication or upstream changes.
Turning it off keeps the supplied instrument implementations and blocks new capability
registrations; experiment and analysis scripting remains available. Provider-native
tools are unchanged. This is a scientific permission enforced in managed registration
and review, not a new operating-system confinement boundary.

Older studies without this field retain their original instructions. The software
does not infer new permissions or retrofit their records. The restricted public trial
retains its host-provided solver policy rather than advertising unsupported development.
Explicit operator constraints and host filesystem permissions remain binding.

An operator-authorized builder can produce a new capability descriptor. Place it in the
study's configured capability directory, then call `lab.register_capability(name)`.
The service appends its hash without replacing any original or previously added identity.
Changing a runtime requires a new name. Registration proves identity, not qualification.
The runtime still needs commissioning and methods review.

Registration can include structured development provenance:

```python
build = lab.register_capability(
    "warpx-repaired-transport", machine="gpu-worker",
    development={
        "parent_capability": "warpx-reference--at-gpu-worker",
        "change_type": "numerical",  # numerical, physical, or diagnostic
        "rationale": "Correct an observed transport error in the private implementation.",
        "preserved_assumptions": "Keep the equations, geometry, drive and physical coefficients.",
        "validation_plan": "Test advection, boundaries, conservation and numerical refinement.",
        "build_experiments": ["exp_build_receipt"],
    },
)
```

Build receipt references must name completed recorded experiments. Metadata describes
intent; runtime/source identity and numerical qualification still need verification.
The worker, director and reviewers see the permission and recorded provenance.
Numerical repairs should preserve the declared equations. Physical-model changes need
declared variants and a prospective repair branch when outside the original claim.
Implementation failures do not establish physical counterexamples.

**Evidence & review → Solver development** shows registered versions, provenance,
validation plans and method-review scopes. An approved instrument benchmark qualifies
that benchmark only. Each evidence run using a newly registered build needs an approved
production method matching its source, dependencies and runtime, even when the initial
study had no installed instruments. No approval applies automatically to the whole solver.

For an execution worker, place the descriptor in one of that worker's already
configured capability directories and register it on that machine:

```python
instrument = lab.register_capability("warpx-new-build", machine="gpu-worker")
lab.run("calculation.py", capability=instrument["name"],
        outputs=["result.json"], stage="exploration")
```

The returned name includes the machine alias. It also works with `lab.method`,
`lab.commit` and `lab.read_instrument`, and appears in `lab.machines()`.
A study with exactly one worker can infer the machine. Registration verifies the
worker identity, launcher and existing instrument hashes; it does not replace the
frozen execution pool. Keep original descriptors and reference sources protected,
and give builders permission to add separate descriptors rather than edit originals.

Operators may authorize inspection of solver source through their selected provider.
Protect the reference installation with filesystem read-only permissions and use a
separate writable problem/build directory. Include source/build hashes and compiler
logs in the build record. Source-access permission is distinct from publication permission.

## Adjustable storage allowances

Experiments have a workspace allowance and the study has a shared storage allowance.
The process's per-file ceiling follows its admitted workspace allowance, including
build outputs; it has no additional fixed 512 MiB ceiling. Input staging is bounded
by the same workspace allowance. Time, memory and aggregate storage checks remain.
Receipts report the executor hash and actual execution limits.

On a dedicated machine, an operator can delegate storage increases at launch:

```bash
simjecture study --campaign ./study --hypothesis-file hypothesis.txt \
  --director --director-storage-increases
```

The director sees current allowances and its authority. It can request larger
`max_experiment_bytes` and `max_total_bytes` in its structured decision, with a reason.
The host grants authorized increases and wakes the worker; rejected requests remain
visible in the director record. There is no extra preset ceiling on a delegated
increase, but physical disk space and operator-owned shared-machine capacity remain
finite. Workers can explain blockers in `lab.note`; they cannot grant themselves
more storage through the worker API. Hosted/shared deployments retain their limits
unless the operator explicitly delegates this authority.

Every grant records its director decision, reason, sequence and before/after values
in `storage_adjustments/`. `lab.status()` exposes the current allowances and history.
The research monitor's **Evidence & review → Research director** section shows current
allowances, delegated authority, granted before/after values, reasons and rejected requests.
New experiments use the increased allowance; existing experiments keep their original
reservation. Neither grants nor restarts extend the campaign deadline or change the
scientific contract. An operator may enable this for an existing dedicated study with
`ResearchService(root).configure_resource_policy(director_can_increase=True, reason=...)`.

## Instrument registration recovery

Remote instrument registration probes the frozen worker and fingerprints its installed
capabilities. A large inventory can take longer than the default **60 seconds, one attempt**.
This is an operational deadline, not a statement about the solver's validity.
Transport errors now distinguish a timeout from failure to start the connection.
`lab.status()['registration']` contains current limits, delegated authority and the five
most recent attempts, including elapsed time and error. Full records remain in
`registration_attempts/`; they are operational records, not scientific evidence.

New minimal studies permit director tuning of these probes. Use
`--no-director-registration-tuning` to retain operator control, or explicitly delegate
an older study with `--director-registration-tuning` on resume. An operator can also call
`ResearchService(root).configure_registration_policy(director_can_tune=True, reason=...)`.
Delegation is immutable once explicitly recorded. The worker cannot grant itself limits.

The director can return `registration_tuning` with `timeout_seconds`, `max_attempts` and
a concrete reason. The host records before/after settings in `registration_adjustments/`
and wakes the worker to retry. It can increase or decrease both settings. Retries apply
only to transport uncertainty, with short backoff; worker rejections and frozen worker,
configuration or existing instrument identity changes still fail. Every attempt and
backoff fits within the compute cutoff, preserving the report reserve and original
campaign deadline. Active numerical jobs keep their settings and identities.

The research monitor's **Evidence & review → Research director** section shows the
probe limits, recent failures, and granted or rejected tuning requests. A new probe
failure also brings the next strategy review forward instead of being hidden in chat.

## Progress recovery

The host inspects observable actions and durable records after native turns. Two turns
without new work add explicit recovery instructions; at three it starts a fresh native
session, retaining the study, experiment receipts, usage accounting and original deadline.
Repeated nonprogress receives responsive backoff and further bounded recovery.
Private model reasoning is not examined. A distinct action is a progress signal, not
proof of scientific progress; periodic independent review checks the latter.
The host keeps a bounded history of useful actions across narration-only turns.
Repeated `lab.status()`, review-status or journal polling does not reset recovery.
Actual recorded progress is tracked separately from provisional tool activity.

### Wait for feedback without spending worker turns

Use a durable wait when no useful work can proceed before a result:

```python
lab.wait("Await the recorded comparison", experiments=[receipt["id"]])
# Or methods=[...], reviews=[...], reports=[...].
# For a genuine operator blocker:
lab.wait("Await operator guidance on the unavailable instrument", for_operator=True)
```

End the native turn after requesting a wait. The host parks worker inference, while
experiments, supervision and the original campaign clock continue. A terminal receipt,
new operator steering or explicit director wake-up resumes the worker. Already settled
receipts return their terminal state immediately. This does not complete the study or
extend its deadline. The monitor shows the reason under **Worker awaiting feedback**.

Minimal workers checkpoint at most every five minutes so one long native turn cannot
postpone host checks indefinitely. Detached recorded experiments continue. Long builds
should use an idempotent builder whose result can be recovered after a checkpoint.
Every fifteen minutes, or during sustained nonprogress (at most once per two minutes),
the host can invoke a separate progress reviewer even if the worker requests no review.
Methods and progress decisions do not complete or falsify a study. Normal uncertainty
continues until the existing deadline or an independently accepted conclusion.

## Results and reporting

Declare raw arrays and compact result documents separately:

```python
receipt = lab.run(
    "calculation.py",
    outputs=["result.json", "history.npz", "snapshots.npz"],
    review_documents=["result.json"],
    method=method["id"],
)
```

If `review_documents` is omitted, compact text outputs are selected automatically.
All artifacts retain hashes; the reviewer sees raw-file metadata, not binary contents.
Large remote file catalogues are saved once in content-addressed `artifact_indexes/`.
Review packets contain the index location, count and SHA-256, together with a reference
to the unchanged full execution receipt. Large console output is explicitly excerpted;
the original remains in that receipt. This avoids overflowing a methods packet merely
because a numerical run generated many files.

Tool-free reviewers can request a bounded inventory excerpt through `evidence_requests`:

```json
{
  "experiment": "exp_ID",
  "inventory": {
    "sha256": "INDEX_SHA256_FROM_PACKET",
    "names": ["case/fields000100/Header"]
  }
}
```

Use the actual 64-character index hash. Alternatively supply `offset` and `limit`
(at most 32 entries) to page through the catalogue. Inventory requests and ordinary
JSON-output requests are separate. A changed index or mismatched hash is rejected.
Use strict JSON (`null` and a reason for undefined statistics), numeric arrays instead
of pickle/object arrays, and periodic on-disk checkpoints. Non-finite JSON and explicit
failed checks are surfaced as output findings, not silently interpreted as scientific
failure or success. Record analysis of raw data if a conclusion depends on it.

The host maintains `STUDY_LEDGER.md` and `research_report.json` separately from agent
notes. They distinguish execution from scientific status, list missing committed cases,
show output findings and include supervision/usage state. Interrupted native turns
may not return token counters; missing usage is explicitly flagged rather than counted
as zero. Each native invocation saves `usage.json` with its role, thread ID, cumulative
counters and coverage. Resumed counters replace earlier counters rather than being
summed. A later worker counter can cover interrupted turns; an ephemeral reviewer
with no usage remains unknown. The monitor shows missing native threads and historical
coverage gaps. Cached input and reasoning output remain subsets of input and output.
Provider billing is not inferred from these totals. Runtime estimates for unfinished
validation are heuristics, not reservations or promises. `RESULTS.md` remains the worker's
scientific narrative and should cite receipts and stay consistent with the ledger.

The cooperative execution backend is not a hostile-agent security boundary. Native
work can occur outside the evidence service; important exploratory findings need fresh
recorded evidence. These checks improve observability and acceptance discipline rather
than claiming to intercept every native action or to guarantee a valid discovery.

## Approval conditions and exploratory pilots

New methods/progress verdicts include `prerequisites`, an explicit list of unmet
conditions. `continue` requires an empty list. Conditional approval is rejected and
must be reviewed again; a recommendation for subsequent work is different from a
condition required to make the present approval valid.

Label timing and rank-comparison pilots with `purpose="timing"` or `purpose="parity"`
and `stage="exploration"`. Reviewers receive those labels; such pilots are not claim
tests. Missing purpose is unknown, not an inferred scientific objective.

The host's recorded stage controls evidence eligibility. A JSON output containing
`scientific_evidence_eligible=false` is preserved and flagged for independent review;
it does not itself force a solver rerun. Explain whether it is stale metadata or a
real limitation. Exploration still cannot become claim evidence, and artifact hashes
are still checked. This does not allow rewriting previous results.

## Checking numerical repair bounds

For conjunctive inclusive bounds, supplement the prose acceptance rule:

```python
commitment = lab.commit(
    "A minimally repaired prediction for the rate",
    source="calculation.py",
    cases=[["--S", "2000"]],
    acceptance="Both predeclared bounds on the S=2000 rate must hold",
    numerical_bounds=[
        {"metric": "S2000.rate", "lower": 0.025, "upper": 0.030},
        {"metric": "S2000.rate", "lower": 0.028},
    ],
    rationale="Explain the parent failure and preserve its unaffected predictions",
)
```

Repeated metric names mean AND. Use different names for different cases. Empty
intersections and non-finite bounds are rejected before recording the commitment.
This optional check validates feasibility, not the physics or the measured outcome;
natural-language rules and scientific acceptance still require independent review.

## Independent report assessment

An inconclusive report can be assessed during the investigation, before the protected
finalization reserve:

```python
request = lab.assess_report(report="RESULTS.md", reason="Assess the bounded findings and limits")
lab.wait("Await independent report feedback", reports=[request["id"]])
# After wake-up:
assessment = lab.report_assessment_status(request["id"])
```

The host freezes the report and its scientific snapshot, then uses a fresh read-only
reviewer. Exploratory, failed and inherited results retain their stages. The reviewer
can accept an honest unresolved report or request concrete revisions. Report acceptance
does not approve or falsify the hypothesis. An unchanged report and evidence record
reuse their request, rather than generating repeated reviewer calls. Changed reports
receive a new identity.

The director can set `report_assessment="RESULTS.md"` to request this host action and
`park_worker=true` to await feedback without worker inference. A prose `next_action`
asking the host to route a report is insufficient. Parking cannot accompany a replan
or wake-up, and cannot bypass an outstanding replan acknowledgement. New operator
guidance remains effective while parked.

In the monitor, **Evidence & review → Independent report assessments** shows requests,
verdicts, revisions and frozen-report links. **Assess current report** queues the same
operation for a running minimal study in an operator workspace. Read-only hosted views
show assessment records without exposing operator controls.

Scientific claim review remains separate: its dispositions are `supported`, `falsified`
and `unresolved`. It requires claim evidence; an exploratory report belongs in
`assess_report`, rather than a claim-review request.

## Research director: stop and replan

Earlier studies retain their saved progress-oversight policy when upgraded.

New minimal studies enable a research director by default. The launch settings in
the workspace expose the switch, reviewer/director model and effort; CLI launches
accept `--director` and `--no-director`. Existing launches retain their saved
policy, including studies created before the director existed. Other workflow
modes retain their existing supervision.

The director uses the reviewer route with a fresh context and checks execution
strategy about every five minutes, including when the worker is waiting for a
long experiment. Since rc2, new studies can defer model
reviews of healthy, unchanged work to at most 15 minutes, with operational checks
at up to one-minute intervals during deferral. A changed record/plan or steering,
pending replan, transport failure, stale telemetry, runtime risk or near deadline
restores the shorter cadence. Existing stored study policies retain their cadence.
An idle worker awaiting operator feedback can also use this deferral. A director
decision to park that worker becomes the current reviewed state; the wait record
it creates does not itself count as new evidence. New worker plans or results
still trigger strategy review.
The monitor shows this policy and a deferred review's latest scheduled time.
Native worker turns still checkpoint within five minutes.
Each director call has a two-minute allowance, separate from the worker's turn
allowance; invalid or interrupted decisions receive a bounded retry delay.
It receives remaining wall time, recorded coverage/cost, active experiment
telemetry and recent plans. The audit repair also identifies evidence changed
since the last successful strategy review; extensive methods qualification
remains a separate review. It evaluates scientific usefulness and budget
feasibility separately. Its role is to obtain useful complete trajectories before
refining details, without imposing a fixed phase schedule.

A `replan` decision can name active experiment IDs to stop. The host requests
those stops, preserves available partial data and wakes the worker. It does not
stop the campaign, change the hypothesis/deadline, or accept a scientific claim.
Transport failures leave cancellation unconfirmed; the UI shows that distinction.
Failed control calls retain the valid decision and their individual errors, so
other requested stops and worker replanning can proceed. Available partial data
are retained; the host does not claim a confirmed stop until it is observed.
The usual independent methods and claim reviews remain in force.

The director also sees whether the worker is waiting for experiments. It can use
`continue` with `wake_worker=true` to resume the worker for a concrete parallel
task, such as submitting completed qualification for review, while leaving the
simulations running. A `next_action` sentence alone does not wake a parked worker.
This adds no replan-acknowledgement gate and grants no scientific approval. The
decision card in **Evidence & review** shows when a worker wake-up was requested.
Ordinary waits still avoid unnecessary provider turns.

The worker reads `lab.director_status()` and records its response:

```python
plan = lab.note('Test adaptive stepping over the radiation peak, then compare '
                'a stricter CFL setting before refining the spatial mesh.',
                kind='next_test', estimated_seconds=600)
lab.director_ack('director_ID', response='plan', plan=plan['id'],
                 reason='This provides an affordable complete trajectory and '
                        'a temporal accuracy comparison.')
```

A reasoned `response='challenge'` is also allowed. New numerical submissions
require acknowledgement of the latest replan, even after a later continue review;
reads, idempotent replay and short
exploratory diagnostics remain available. Acknowledgement records a response,
not scientific approval. Decisions and responses appear in **Evidence & review**.
The durable records live under `director/` and `director-acks/`.

The audit repair makes derived journal, bounded-context and report/navigation
errors visible under **Harness diagnostics** while allowing the study to keep
working. Recovery contexts cite actual receipts and never create scientific
approval. Primary scientific-state failure still stops work, and supervisor
completion requires a persisted final report. After an early error stop, the
monitor retains its cause and unused wall time even when the original deadline
has since expired. It also separates role-level cached/uncached input and source
execution time from submission-to-result latency; native counters are not invoices.

`lab.cancel('exp_ID', reason='...')` can stop a named experiment in the current
study. `lab.run(..., monitor={...})` optionally publishes bounded live JSON or
FLASH log timing. Live observations and their linear estimates are operational,
not scientific evidence. Receipt-backed `lab.progress` remains the recorded
metric interface; neither kind of target changes scientific acceptance.
SSH monitoring requires a prepared worker advertising that feature. Older frozen
workers remain usable without a monitor; prepare a new worker/study to add monitoring.

## Protected time for a final report

New minimal studies launched from the CLI or GUI reserve the last quarter of the
wall budget for reporting, with a 10-minute maximum and a 2-minute minimum
(capped at half of very short budgets). A 30-minute continuation therefore has
22.5 minutes for numerical work and 7.5 minutes for finishing. Existing studies
keep their saved policy; a continuation receives a new policy and deadline.

The host bounds experiment execution and agent turns at the numerical cutoff.
It then wakes the worker to update `research/RESULTS.md`, with findings, figures,
provenance and limitations. Bounded exploratory postprocessing remains available
through `lab.analyze` during the first 40% of the reserve. Native provider tools
remain available; the cutoff controls registered experiments, not every possible
command a provider can execute.

A separate reviewer assesses the frozen report. A useful report may be accepted
while the hypothesis remains unresolved. This assessment never promotes exploratory
results, imports parent approvals or approves a scientific claim. Normal claim
review remains separate. If needed, the host allows one report revision and review
within the original deadline. Provider failure or an unfinished review leaves an
explicitly unreviewed report; the host does not infer a scientific answer.

**Evidence & review → Report & finalization** shows the numerical cutoff, finishing
phase, report assessment and frozen report link. `lab.status()` and
`research_report.json` expose the same information. Editing the narrative after
assessment marks it as changed since review. Both the original study and its
continuation remain independently inspectable.

Reports open with whether a credible counterexample was found, then distinguish
**falsified**, **supported within the tested scope**, and **unresolved**. The absence
of a counterexample alone does not establish support. An unresolved report must
explain the specific obstacle to judgment and the next discriminating test.
Report review and the independent claim verdict are shown separately: finishing
the document cannot silently turn an exploratory result into accepted evidence.

Admitted diagnostic jobs survive the numerical cutoff until their own drafting
deadline. The host waits for their receipts and resumes the writer before freezing
the report. Unused drafting time becomes review time; a report-review transport
failure can receive one retry within the original study deadline. It never grants
an extra scientific run or extends the operator's wall budget.
