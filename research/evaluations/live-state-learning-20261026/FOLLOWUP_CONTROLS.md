# Controls needed to interpret the workflow timing differences

Status: **first native commissioning attempt incomplete; the revised resumption
control is collecting a separate native qualification round**. The original 64-assignment base/SFT comparison completed
at source `04f905c`, with its original instructions and four arms. None of the
changes below was deployed into that cohort or used for model training.

## First native commissioning outcome

The [first pilot record](followup-control-first-attempt.json) contains two actual
protected-source workflows with task-focused instructions and no decision model.
Worker-only execution verified in 371.2 seconds with six native starts. Routine
help did not verify: it stopped in 277.4 seconds after seven native starts.
The ordinary audit has no consistency violations. The additional commission
audit correctly rejects the failed workflow and retains four unstarted IDs.
Routine dispatch, acknowledged help return and an applied judge-authorized repair
were all exercised; numerical/report completion is still required.

The failed routine-help trace isolates an experimental scheduling limit. After
its fourth main-worker turn, corrected postprocessing completed and emitted a
terminal wake, but the loop ended without a fifth report-writing turn. Both
physical controls and protected repair succeeded, required feedback was
acknowledged, and no final report existed. The workflow used only 277 of the
650 seconds and seven of the 12 permitted native starts. This reproduces the
completion failure without a learned attention policy. It does not prove that
all earlier model-arm differences arose from the same cause, and it does not
erase any historical outcome.

The limit is in this experiment's `range(1, 5)` worker loop, not an independently
established production Simjecture bug. The prospective `--parent-turn-limit`
option permits 1–12 main-worker resumptions while the existing wall deadline and
shared native-start guard still apply to every role. Its default remains four,
and the default task text is byte-for-byte unchanged. A new commission will
register 12 for both arms, use new assignment IDs, and retain the two original
pilot outcomes. It receives only the original pilot's unused native starts and
unexpired wall budget, not a renewed two-hour allowance.

Nondefault commissioning verifies the limit recorded in each actual outcome
and requires at least one successful workflow to exercise a resumption beyond
four turns. Missing coverage remains incomplete. Thirty-six targeted checks
pass, covering the new audit requirement, unchanged resource ceilings, invalid
limit rejection, original completion/feedback checks, and existing controls.
These checks do not replace the forthcoming native qualification.

The [second-round manifest](followup-control-v2-manifest.json) pins source
`8626a773f8995a42ee99f24703b13ecb386d7679` and all 543 source files. It uses
disjoint IDs and retains the first round's failed outcome and four unstarted
assignments. Its allowance is the remaining **59 of the original 73 native
starts**, with no extension of the original **14:19:33 UTC** deadline.
The actual child runner ends its native allowance approximately 30 seconds
earlier. Fresh physics checks passed before the new authentication and workers.

At the [saved launch snapshot](followup-control-v2-launch.json), the first three
new workflows had verified. The new routine-help protected-repair trial required
five main-worker turns and eight native starts, completing in 402.5 seconds.
This exercises the previously unavailable fifth resumption and completes the
report within the original per-workflow wall and shared-start limits. The paired
worker-only trial verified in 322.7 seconds with four main-worker turns; the
healthy worker-only trial also verified. These are integration observations,
not an estimate of learned-policy benefit. Full six-trial qualification remains
pending at this snapshot. [Physics receipts](followup-control-v2-qualification.json)
and exact second-round operator scripts are retained alongside the first round.

## Recorded instruction mismatch

The actual initial worker prompt combines general Simjecture research guidance
with a task-specific external-solver protocol. The general guidance recommends
reserving time for independent review, describes `lab.run`, and directs a worker
to submit an experiment to `lab.review`. The task protocol instead requires
supplied native-shell wrappers, asks for an engineering report from their saved
results, and forbids claiming scientific acceptance or requesting report review.
The resumed generic brief also reports the ordinary lab experiment ledger, which
contains no experiments because this fixture executes the real solver elsewhere.

The specific task overrides the general workflow guidance, and the experiment
does **not** require a help request. Nevertheless, the extra instructions and
unrepresentative ledger may affect how a worker interprets completion and seeks
technical assistance. This is a hypothesis about behavior, not proof of the
cause of any observed timing difference.

[The prompt audit](worker-prompt-audit.json) retains source hashes and exact
excerpts from a base publication-retry episode, its SFT counterpart, and the slow
quiet SFT episode. Their task protocols have the same byte hash. These findings
do not show an asymmetric prompt advantage between arms, and do not erase the
observed comparison within that harness. They limit what its effects can imply
about a well-integrated scientific workflow.

The mismatch comes from the experimental wrapper's reuse of whole-study research
instructions for a bounded engineering evaluation. The general instructions are
appropriate to the production research lifecycle. This inspection establishes
no independent upstream bug and does not justify removing production review.

## Optional task-focused instructions

`scientific_workflow_trials.py --worker-prompt task_protocol` selects the new
instruction control. The default remains `inherited`. The control retains the
exact original task, numerical criteria, protected-component boundaries,
assistance API and required-feedback obligations. It describes the actual
wrapper execution/completion path and clarifies that there is no minimum number
of help requests needed to finish.

It continues to deliver director replans, help results, operator guidance,
oversight, provider-recovery instructions and independent repair-authority
outcomes. The durable guide uses the same instructions. A receipt records the
mode, task hash and renderer hash. The mode rejects inherited continuation or
guided-commissioning phases whose special requirements it does not implement.
It is not a replacement for ordinary Simjecture research prompts.

The [static preview](worker-task-protocol-preview.txt) preserves the exact
3,782-character task protocol inside 5,893 characters of instructions. The
recorded original initial prompt had 33,963 characters including dynamic context.
[Preview metadata](worker-prompt-preview.json) records this comparison. This is
not a token count or latency benchmark. The control changes both instruction
scope and length, so a future measured effect cannot be attributed to one phrase
or to context length alone.

## Routine expert-attention baseline

`--arm routine_help` requests a bounded worker-help review at the first eligible
parked opportunity. It cites the first available visible source and makes no
anomaly classification. There are no family labels, failure thresholds, fitted
weights or model calls in this policy.

The baseline uses the same observation packing, action schema, freshness and
state checks, persistence requirement, pending-assistance suppression and actual
dispatch accounting as the other arms. The experiment retains its one automatic
expert-request allowance and the same downstream director/helper permissions.
The policy cannot bypass a closed workflow or already dispatched incident.

A cited source and structural admission do not establish that attention is
semantically warranted. Routine review deliberately spends expert attention
without detecting a problem. Report its cost, independently assessed support
and actual downstream value; do not present it as an anomaly detector with a
calibrated score. Its purpose is to test whether generic early expert advice can
obtain the benefit currently attributed to selective learned attention.

## Validation and next execution

Thirteen focused tests pass. They cover preservation of the inherited default,
selection of the new prompt through the experiment supervisor, task/feedback and
authority preservation, and use of the shared admission path by routine help.
These checks do not establish native-worker behavior or scientific benefit.

After the current cohort is terminal and its attempted/unstarted coverage is
audited, commission the new modes separately on healthy execution, worker-owned
diagnostic assistance and protected-component repair. Check actual solver and
report verification, explicit help/wait/return behavior, authority boundaries,
and the one-request allowance before counting new comparative outcomes.

### Prepared integration commission

The [six-assignment manifest](followup-control-commission-manifest.json) now pins
scientific source `45f0204061ef44d8b9c974c3d5d85a2c7fe5c8f1`, all 537 tracked
regular files under its source/script/monitor-package directories, and the four
new planning, execution and audit tools. It has not been executed. Every trial
uses `task_protocol`; worker-only and routine-help arms each cover healthy
progress, worker-owned unit conversion, and protected source binding. This is
integration qualification on known mechanisms, not a model comparison or unseen
scientific-task validation.

`plan_control_commission.py` builds this plan directly from an immutable Git
commit and refuses to overwrite an existing output. For example, from the
repository root:

```bash
PYTHONPATH=packages/simjecture-monitor/src python \
  packages/simjecture-monitor/scripts/plan_control_commission.py \
  --source . --revision 45f0204061ef44d8b9c974c3d5d85a2c7fe5c8f1 \
  --output /path/to/new-control-plan.json
```

`run_control_commission.py` supplies the bounded serial coordinator. Before
creating a campaign or calling a native worker, it requires a complete original
comparison with no audit violations, closed prior native roles, and a release
receipt for the prior owned model runtime. It checks both source and operator
tool hashes and requires successful matched physics qualification of the chosen
backend within the preceding 15 minutes. A terminal partial phase does not meet
the completion requirement: the check rejected the actual 38-of-64 R8 record.
[Preparation evidence](followup-control-preparation.json) retains that result.

The separate proposed allowance is two hours and 73 native starts: one native
authentication preflight plus at most 12 starts per workflow, with one workflow
and at most six native roles active at a time. Native workers still use the
large-model provider. No decision-model server, GPU allocation or optimizer
update is part of this commission. The runner preserves the selected virtualenv
interpreter path, reserves each attempted ID before launching its process, stops
on an unsuccessful assignment, and retains its outcome and logs. Unstarted IDs
remain unstarted even when outcome parsing or auditing fails.

After execution, the pinned ordinary workflow auditor checks numerical/report
completion and artifact consistency. `audit_control_commission.py` additionally
binds the actual prompt-mode receipt to the task and renderer hashes. It checks
the automatic-dispatch allowance and required-feedback reconciliation. At least
one actual routine expert dispatch, an acknowledged help return, and a completed
judge-authorized protected repair must have been exercised. A proposal, grant
without deployment, or missing return cannot fill those coverage requirements.
Missing coverage leaves commissioning incomplete; it is not evidence of benefit
or a reason to fabricate an exercised path.

Twenty-two selected tests pass, including the new planner/auditor and runner
failure-path checks plus the existing prompt/routine-policy checks. The runner
tests substitute local process doubles and do not claim native integration
qualification. All outputs remain ineligible for optimization by default, and
the ongoing original cohort has not loaded these tools or changed instructions.

Then freeze a fresh assignment manifest, source revision, resource bounds and
analysis before starting a comparison. Within a comparison, all policy arms must
share the selected worker instructions. A causal comparison of the two instruction
modes also needs contemporaneously randomized inherited-prompt controls; historical
times alone cannot isolate that effect from changing worker/provider conditions.
Use completed pilot variance to choose the prospective sample size, not interim
success to stop collection or select favorable mechanisms.

These controls do not replace the need for new scientific tasks and mechanisms,
independently assessed unsupported alerts, and general-decision retention. The
prepared adapter bundle remains unpublished. Its earlier documentation snapshot
must be refreshed with these limitations and the completed evaluation before any
release decision.

## Autonomous commissioning sequence

After the user approved the continuation plan and requested autonomous execution
without a formal goal, the six-assignment pilot was staged on the coordinator.
The scientific source archive matches its registered SHA-256 and all 537 file
hashes. A separate operator archive from commit `e0ae6fa` matches the four
registered planning, execution and audit tool hashes.

The first staging import check exposed an environment configuration issue:
`replication-env` deliberately prepends the original `04f905c` source through a
`.pth` hook, ahead of a new `PYTHONPATH`. That environment is correct for the
running frozen comparison but cannot select the new control source. It was left
unchanged. A separate `control-commission-env` now uses the same base Python and
existing dependency directories through plain path entries, without executing
their research-source hooks. Actual import receipts verify the operator module
from `e0ae6fa` and the scientific prompt renderer from `45f0204`; both command
help checks pass. The actual 55-record partial predecessor is still rejected.
This staging problem is not an independently established production bug.

[The staging evidence](followup-control-staging.json) retains the failure,
environment qualification and bounded sequence registration. Exact setup and
sequence scripts are in `followup-control-operations/`. The sequence waits for
all 64 original assignments, zero audit violations, closed native roles and the
R11 GPU release. It then runs fresh matched physics qualification and invokes
the registered two-hour, 73-start pilot with no decision-model server or GPU
allocation. No optimizer update is scheduled. An unsuccessful qualification or
pilot is preserved and stops this sequence.

At the saved staging snapshot the sequence was waiting, with no pilot campaign,
new native worker or physics qualification started. This is a ready execution
path, not evidence that the new controls work or improve workflow performance.
