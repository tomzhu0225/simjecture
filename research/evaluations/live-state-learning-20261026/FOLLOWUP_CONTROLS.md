# Controls needed to interpret the workflow timing differences

Status: **implemented for prospective use; not commissioned or evaluated with new
native workers**. The ongoing 64-assignment base/SFT comparison remains frozen
at source `04f905c`, with its original instructions and four arms. None of the
changes below has been deployed into that cohort or used for model training.

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
