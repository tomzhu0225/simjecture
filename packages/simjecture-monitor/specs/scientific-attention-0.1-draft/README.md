# Scientific attention interface 0.1 draft

This is a proposed reusable contract for inexpensive decision models supervising
scientific workflows. It specifies observations, model-visible representations,
attention requests and host admission rules. Model weights and training methods
are replaceable. This draft is not an adopted community standard or a validated
low-false-alert deployment policy.

The reference code is isolated from the existing experimental runners. It does
not change the frozen October 25 comparisons, enable production monitoring,
dispatch agents, train a model or allocate compute. See the [study results](https://github.com/tomzhu0225/simjecture/blob/93a5c3b/research/evaluations/monitor-generalization-20261025/RESULTS.md)
for what has actually been measured.

## Three records with different responsibilities

1. **Observation:** the canonical, versioned scientific context and public evidence.
   Full source identities and hashes remain here for replay and audit.
2. **PackedView:** the exact text supplied to a model, its digest, tokenizer/counting
   profile, selected evidence and explicit omissions. A character limit is not a
   token budget. The adapter counts its full actual input, including chat framing.
3. **Decision:** a proposed action bound to that packet and model view. The host
   separately records admission, actual dispatch, returned assistance and final
   outcome. Admission alone is not an executed intervention.

JSON schemas are in [schemas](schemas). Structural schema validation is necessary
but not sufficient: the cross-field and temporal requirements below must also be
implemented. The [Python reference](../../src/simjecture_monitor/attention_contract.py)
validates cross-field invariants; [admission code](../../src/simjecture_monitor/attention_admission.py)
demonstrates the temporal rules. The JSON contract can be implemented without
Python, Simjecture or the Intern-Decision model.

## Inputs and their priority

| Input block | Required meaning | Why it belongs in the small context |
|---|---|---|
| Task and scientific contract | Current objective, phase, original units and criteria; a valid negative result remains valid science | Defines what progress and correctness mean |
| Current state | Worker active/parked/unknown; workflow closure; assistance for this incident | Prevents obsolete or duplicate requests |
| Timing and expectations | Operation age, actual progress age, heartbeat age, declared quiet window, remaining retries and budget | Distinguishes liveness, progress and expected waiting |
| Scientific evidence | Measurements with units, validity, public references, source roles and ages | Supports semantic checks beyond process exit codes |
| Recent events | Relevant tool results, changes, unresolved evidence and previous assistance | Supplies enough temporal context to recognize recurrence or recovery |
| Coverage | Required channels missing, excerpts and omitted evidence | Makes uncertainty visible instead of inventing normality |

Producers MUST distinguish observed instrument facts, host facts, worker claims
and operator declarations using `origin`. A worker's expectation is not verified
physics. Source hashes bind records; they do not prove that a measurement is true.
Public reference values must retain their scientific source and interpretation.
Hidden evaluator labels, expected actions, split names and retrospective rewards
MUST NOT enter the model view.

Measurements preserve their numeric values and units. Missing and invalid values
are explicit nulls, never zero. Non-finite JSON numbers are rejected. Dimensionless
values use an explicit convention such as `1`. Domain profiles must define their
metric names, unit vocabulary, reference conventions and progress milestones.
There is no universal physical-convergence threshold in this interface.

All duration comparisons use one observer's monotonic clock, identified by
`clock_id`. A restart or incomparable clock invalidates old timing decisions.
Simulation physical time is a scientific measurement with its own unit; it is
not the observer's elapsed wall time. A fresh heartbeat establishes liveness and
does not reset the age of scientific progress. Progress must belong to the
current operation and its declared milestone definition.

`workflow_state=complete` means the host has closed the workflow under its
declared completion contract, including required feedback. Process exit zero,
report-file existence or an agent's claim does not establish closure. New evidence
that invalidates a closed workflow must open a new host-owned incident/revision.

`incident_id` groups a suspected issue; it is not a fault diagnosis. The host owns
it and keeps it stable across repeated observations, changing output text and
alternative requested recipients. New incidents and reopened generations must
follow a recorded lifecycle. A model cannot mint identities to evade deduplication.
Assistance state is scoped to this incident; help for another worker or independent
problem must not suppress its attention request.

## Efficient representation and token budgets

Standardize semantic fields and output meanings, not numeric token IDs. Token IDs,
chat templates, special markers and cache behavior differ between model families.
Each adapter publishes the exact mapping and checks any claimed single-token
symbols against its own tokenizer.

The reference view uses a fixed instruction/action prefix followed by a
self-contained state and selected evidence. It replaces opaque record/source IDs
with short aliases and keeps hashes, storage locations and transport identities
in the audit receipt. Meaningful source roles and published request/source
disagreements stay visible. A semantically meaningful filename or run property
must not disappear merely because opaque IDs are shortened.
Aliases are local to a PackedView; consumers resolve them through that view's
receipt and must not assume `e2` identifies the same evidence in another packet.

The default format is named, minified JSON. An experimental column-based format
shares field names across rows and measurements. Both contain the same selected
semantic information; equality is checked in the conformance tests. That does
not establish equal model comprehension or predictions. Keep the chosen renderer
fixed and versioned during evaluation and training.

The producer's required-evidence selection policy must be declared before seeing
evaluation outcomes. The reference packer keeps task, criteria, timing, current
assistance, coverage and all required evidence. It adds optional evidence in
recency order, dropping whole records with an omission receipt. It never truncates
a required quantity, unit, reference or scientific criterion to fit. If the
required view is too large, it returns `insufficient_budget`; the adapter must
not send that oversized view or relabel the failure as an `observe` prediction.

Candidate budgets are 512, 1,024, 2,048 and 4,096 full input tokens. These are
experimental profiles, not a claim that one size is optimal. Choose a profile by
measuring intervention quality and alert behavior as well as cost. A fixed prefix
may support caching in some backends; the existing inference profile has not
established such a cache benefit. Count the full input even when reporting cache
savings separately.

Transport can deliver events incrementally, but a stateless model still needs a
self-contained decision context. Sending only the latest delta is not equivalent.
Repeated identical content need not trigger inference on every poll; the host
can schedule evaluation on new evidence and meaningful timer boundaries, such
as the end of a declared quiet allowance. Record the polling and inference cadence
separately so reduced calls do not conceal delayed detection.

## Output vocabulary and evidence

| Symbol in the reference profile | Action | Effect requested |
|---|---|---|
| A | `observe` | Continue the normal observation schedule |
| B | `recheck` | Collect bounded additional evidence using approved readers; no expert wake |
| C | `request_worker_help` | Ask the director to arrange bounded worker assistance |
| D | `wake_director` | Request scientific/workflow review |
| E | `request_repair_judge` | Request independent harness diagnosis and permission review |

The model never approves science, grants permissions, edits thresholds, executes
a repair or directly stops a simulation. Explicit worker help, hard deadlines
and mandatory process cleanup are handled by the host independently of this
discretionary interface.

The deployable profile also requires a short evidence basis (`silence`,
`repetition`, `measurement`, `source` or `missing`) and selected visible evidence
aliases. For example, a compact decoder might emit:

```json
{"action":"D","basis":"measurement","evidence":["e2"]}
```

The adapter maps these symbols/aliases to the canonical Decision and supplies the
packet/model-view/policy identity from its own records. The model does not spend
tokens copying hashes or inventing incident IDs. No free-form chain of thought
is required. A citation points to observed evidence; it does not prove the
interpretation is correct. Model-generated reasoning tags remain claims.

An action-only backend can use `evidence_basis=whole_view` and
`basis=unspecified` in shadow evaluation. It must not fabricate evidence
attribution. The reference admission profile requires selected evidence and a
basis before automatic attention; therefore the legacy four-action model is
not a drop-in deployable implementation of this draft. The existing V1 LoRA,
four-action probabilities and new five-action probabilities are distinct policies.

The interface separates `ok`, `insufficient_input` and `inference_error`.
The latter two have `action=null`. Softmax scores may be retained in a separate
backend audit record with calibration provenance; they are not universal
probabilities that an alert is justified. Adding a confidence number to the
output would not by itself control false alerts.

## Admission and avoidable alerts

The host validates the packet/view binding, current operation and revision,
clock and freshness, evidence visibility, current assistance and durable incident
history before any dispatch. A response may be valid for its original packet
and still be obsolete because the workflow has recovered. Missing required
telemetry requests observation rather than silently establishing health or fault.

For a silence-based request, the reference derives unexplained silence as follows:

```text
unknown progress or quiet context: unknown
inside declared quiet window:     0
after declared quiet window:      min(progress_age, time_since_quiet_end)
no declared quiet window:         progress_age
```

This directly addresses the observed expiry defect: 35 seconds since the last
progress record and 0.14 seconds since quiet ended give 0.14 seconds of unexplained
silence. Quiet allowances must remain within the host's fixed deadline and policy;
they cannot extend those limits. Silence logic does not suppress unrelated
scientific contradictions simply because a quiet interval exists.

The illustrative reference profile requires 30 seconds of unexplained silence
for silence-based attention, then two distinct observations spanning five seconds.
Confirmation gaps over ten seconds reset persistence; a response older than
15 seconds is stale. These settings demonstrate the contract, not optimal
production thresholds. They trade delay against avoidable attention and need
domain-specific development/evaluation. Repeated delivery or repeated inference
on one snapshot cannot count as multiple confirmations. Two similar observations
show persistence, not independent proof that a diagnosis is right.

Host admission does not consume the incident's dispatch allowance. Only an actual
recorded dispatch does. The host persists this transaction and the returned
result/acknowledgment lifecycle. The reference gate is in-memory conformance code;
it has no durable restart behavior, dispatcher or independent watchdog. It is
not a substitute for those production components.

`recheck` also needs host rate and resource limits. The model may select among
predeclared readers or request a later observation; it cannot generate arbitrary
shell commands, unrestricted file reads or an endless extra-observation loop.
Uncertainty that remains after the observation budget uses the host's declared
fallback. That fallback is recorded separately from a learned escalation.

## How to establish a low false-alert rate

Keep these outcomes separate:

- Mechanically invalid requests: stale, duplicate, invisible evidence or violated
  observation/authority contracts.
- Incorrect anomaly interpretations, assessed using scientific evidence.
- Avoidable expert dispatches, assessed through returned work and controlled
  intervention-versus-waiting continuations. A healthy-case alert can still help;
  an acknowledged alert can still be unhelpful. Unknown utility stays unknown.
- Missed actionable incidents, detection delay and final scientific outcomes.

Report avoidable dispatches per healthy workflow-hour, missed incidents, time to
useful intervention, observation coverage, total expert usage, simulation waste
and monitor cost. Measure long healthy periods with realistic incident prevalence.
Reporting zero alerts alone rewards a monitor that never acts. If no false
dispatch occurs in H healthy hours, a Poisson approximation gives a 95% upper rate
bound of about 3/H; that calculation depends on the rate model and does not
guarantee behavior under correlated incidents or distribution shift.

Use separate development incidents to choose thresholds and fit any calibrator.
Freeze them before evaluation. Compare named JSON and column formats, token
budgets, temporal context, evidence citations, rechecking and admission gates
through ablations. Compare maintained rules, a cheap classifier, the unchanged
decision model, supervised training and RL using the same observation/authority
contracts. Use repeated randomized continuations for intervention value and
task-level uncertainty, not individual correlated packets as independent trials.

The known October 25 quiet-window cases are now development regressions. They
must not be counted as new held-out successes. A new learned-policy evaluation,
long healthy exposure and end-to-end worker trials remain to be done.

## Current conformance and token measurements

Twelve conformance tests exercise quiet expiry, true persistent silence, replayed
snapshots, recovery during inference, missing state, ungrounded choices, incident
deduplication, packing/omissions, numeric validity, lossless serialization,
out-of-order responses and agreement with the published schemas/examples.
They validate these reference rules, not a production false-alert rate.

[Token measurements](token-counts.json) use three synthetic development examples
and the pinned Intern-Decision tokenizer. They include its existing route-only
chat scaffold and decision slot; no model weights were loaded. Grounded output
prompting and model comprehension remain unvalidated.
The [exact named model input](examples/model-input.txt) and its
[canonical observation](examples/progress.json) can be inspected side by side.

| Same complete semantic input | Named JSON tokens | Column format tokens |
|---|---:|---:|
| Current progress and measurements | 747 | 685 |
| Quiet-window expiry | 751 | 689 |
| The same core plus twelve older events | 2,472 | 2,158 |

The column format used about 8–13% fewer tokens on these examples. At a 2,048-token
budget the history example retained 12 of 15 records with named JSON and 14 of 15
with columns; all required records remained. A 512-token cap could not fit the
required view and correctly reported insufficient budget. These are serialization
measurements, not latency, accuracy or false-alert improvements.

Generate or check the language-neutral examples and schemas:

```bash
.venv/bin/python packages/simjecture-monitor/scripts/export_attention_contract.py \
  --output packages/simjecture-monitor/specs/scientific-attention-0.1-draft --check
.venv/bin/pytest packages/simjecture-monitor/tests/test_attention_contract.py -q
```

To repeat token measurements using a separate tokenizer environment:

```bash
.venv/bin/python packages/simjecture-monitor/scripts/export_attention_contract.py \
  --output /tmp/new-attention-contract-measurement \
  --tokenizer artifacts/models/Decision-verified \
  --tokenizer-python artifacts/model-fast-env/bin/python
```

## Relationship to existing standards and adoption

[CloudEvents 1.0.2](https://github.com/cloudevents/spec/blob/v1.0.2/cloudevents/spec.md)
provides an event envelope with source, identity and type. An adapter can carry
that provenance into canonical observations; this draft does not replace its
transport or claim CloudEvents conformance. The additional layer is the scientific
decision context, its model view and the meaning of an attention request.

Persistence and deduplication are established monitoring techniques. Prometheus
documents [pending alert durations](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
and Alertmanager documents [grouping and inhibition](https://prometheus.io/docs/alerting/latest/alertmanager/).
The research question is how to combine such controls with scientific semantics
and learned intervention value, and measure the resulting tradeoffs.

Before a stable release, validate a grounded model adapter and a second independent
producer/consumer implementation, add language-neutral temporal conformance traces,
and run a prospective evaluation. Any incompatible field/action semantics require
a new version; records retain the original schema, renderer, tokenizer and policy
identities. This proposal can remain an optional Simjecture package while other
projects implement the same contract. Community adoption and interoperability
are outcomes to establish, not properties claimed by naming a draft standard.
