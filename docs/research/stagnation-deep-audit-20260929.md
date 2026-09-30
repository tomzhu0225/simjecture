# Detailed audit: the aluminium stagnation campaigns

Implementation follow-up: [0.5.3rc1 scope and validation](../testing/0.5.3rc1-acceptance.md)
records the first correctness/observability repairs. The diagnosis and proposed
later experiments below remain the original audit; session policy, spending caps
and the model-versus-harness benchmark are not yet implemented.

Date: 2026-09-29. Scope: the first autonomous campaign and its continuation,
including model transport, worker recovery, review packets, experiment receipts,
and selected scientific reductions. This supersedes the causal attributions in
the initial retrospective. It is not a new claim of physical validation.

## Audit method and limits

I downloaded the campaigns' saved event streams, prompts, review packets/verdicts,
experiment receipts, selected outputs, and agent-written analysis programs. I also
inspected the deployed Python transport and smolagents 1.26.0 implementation.
The deployed continuation transport and oversight modules match the local files
examined. The first campaign predates reviewer repairs; current code must not be
assumed to describe all its historical behavior.

The detailed log snapshot includes continuation events through approximately 19:24
China time. It was collected while the run was active, so state-file counters and
stream totals can differ at the boundary. Use the frozen log-derived numbers below
for this analysis, not as a final invoice. No paid model requests, solver runs,
production changes, or deadline changes were made for the audit.

Offline reproductions used the deployed provider classifier, the actual method
check, and the worker's radiation-window helper. Reproduction code and results:
`artifacts/stagnation-audit-20260929/{analyse_logs.py,audit-statistics.json,reproduce_findings.py,offline-reproductions.json}`.
The raw archive is local/private and is not intended for repository publication.

## Overall diagnosis

This was a mixture of agent errors and harness defects. The evidence does not
support blaming the model alone or treating every agent mistake as a missing
harness feature. The most damaging interaction was:

1. Workers repeatedly began fresh sessions and re-established context.
2. Bounded briefs discarded actual experiment/review information before verbose
   plans, so the durable memory was often least useful exactly when it grew large.
3. Reviewers could not retrieve omitted artifacts and sometimes repeated obsolete
   findings or misinterpreted a machine-readable requirement.
4. Distinct tool activity usually reset the no-progress detector, even without a
   new scientific result or repaired blocker.
5. The worker made substantive coding and scientific-analysis mistakes, while
   spending additional work on API probing and inadequate methods submissions.

None of these observations establish that a particular stronger model would solve
the physical problem. That needs a controlled comparison using a frozen workspace.

## 1. Worker continuity and token use

### Measured facts

| Metric | First campaign | Continuation log snapshot |
|---|---:|---:|
| Recorded total input tokens | 126,362,191 | 173,867,652 |
| Recorded total output tokens | 5,472,739 | 3,796,257 |
| Worker input tokens | 115,590,624 | 173,124,918 |
| Worker output tokens | 3,774,404 | 3,550,369 |
| Worker usage events | 1,963 | 2,086 |
| Worker tool events | 3,135 | 3,141 |
| Action-limit endings | 8 | 69 |
| Worker timeouts/checkpoints | 167 | 16 |

These are repeated input processing, not unique text. Cache discounts, incomplete
usage, and account-level charges prevent converting them directly to RMB.

The continuation main worker accounts for about 99.57% of recorded input. In the
first campaign the reviewer/summary share was materially larger: about 8.52% of
input and 31.03% of output. My earlier statement that reviewer costs were minor
applies to the continuation, not both campaigns.

The continuation called `read_file` for:

| File | Calls | Distinct worker turns |
|---|---:|---:|
| CONTINUATION.md | 83 | 78 |
| RESEARCH_BRIEF.md | 67 | 66 |
| RESEARCH_GUIDE.md | 63 | 59 |
| RESULTS.md | 51 | 51 |

The first campaign read RESEARCH_GUIDE.md 158 times across 116 worker turns.
Reading an updated brief is not necessarily waste. Repeatedly rebuilding context
from guides and stale result notes, however, is a measured behavior rather than a
hypothetical explanation. These read counts do not attribute an exact token cost.

### Mechanism verified in code

`workspace_agent.run_agent` restores/saves conversation history only for interactive
workspace/project requests. Autonomous invocations construct a fresh
`ToolCallingAgent`. They receive a durable prompt/brief and filesystem state, not
the preceding full conversation. With a wall limit, the agent has 24 steps.
At that limit smolagents makes another model call to synthesize a final answer.
The supervisor can then launch another fresh agent.

In the continuation snapshot, those 69 forced finalizations account for
6,363,346 input and 342,899 output tokens: about 3.68% and 9.66% of worker usage,
respectively. These are measured calls, not projected savings. Some summaries
could be useful; replacing them needs to preserve useful handoff information.

Within a session, the model receives accumulated action/observation history.
`read_file` can return up to 256 KB; terminal output can return 24,000 characters.
The adapter can call the model up to four times when plain text appears instead
of a structured tool action or completion. It combines those calls' usage into
one step event. Thus a large usage event is not necessarily one enormous prompt.
For example, turn 59 has 45 `thinking` emissions and 25 usage events. API failures
and interrupted calls also affect those counts; the difference is not an exact
count of billable successful requests.

I found no evidence in the inspected callback path that the supervisor simply sums
the same cumulative usage counter repeatedly. The large total is not explained
away as a demonstrated accounting duplication. Nevertheless, raw request-level
usage is missing, so the exact bill remains unreconciled.

### Attribution and repair

Frequent restart is a harness choice. Redundant reading and poor action selection
are also agent behaviors. The cost of their interaction is not separable from this
run alone. Test persistent bounded sessions and compact handoffs against the current
behavior; do not assume that unlimited history or aggressive compaction is better.

## 2. The recovery brief discards evidence before plans

This is a directly observed harness defect in prioritization, not merely a weak
model forgetting something.

`ResearchNotebook.brief(max_bytes=16000)` removes entries in this order when over
budget: recent experiments, methods, automatic journal, controller summaries, then
notes. Long notes include prospective plans, alternatives, and old interpretations.

In continuation review packet `oversight-00024`:

- Twenty experiment-journal entries existed; zero were retained.
- Eight controller summaries existed; zero were retained.
- Two method records existed; zero were retained.
- Twenty recent experiments existed; zero were retained.
- Eight of nine notes were retained.

The same pattern appears in `oversight-00014` and the post-recharge packet
`oversight-00123`. The brief does disclose omission counts, but the reviewer is
explicitly prohibited from using tools. It cannot resolve the omission itself.

This directly limits what the reviewer can know. It does not prove every rejection
was wrong: several scientific blockers remained real. It does explain why calling
the reviewer again with essentially the same packet cannot establish whether a
new analysis repaired an old problem.

**Repair:** reserve a small non-evictable section for current jobs, newest outcomes,
unresolved review findings, and the artifact/version resolving each finding. Bound
each note before dropping whole evidence categories. For details, use a structured
artifact request fulfilled by the host or a read-only retrieval tool. Treat absent
packet evidence as an information request, not proof the experiment never happened.

## 3. Reviewers changed OR into AND

The frozen requirements list `required_capability_prefixes: ["flash-", "warpx-"]`.
The actual method and evidence checks use `any(...)`: one matching instrument
family satisfies the requirement. The original operator protocol also explicitly
says FLASH **or** a justified, separately qualified WarpX capability.

Offline replay confirms FLASH alone passes the instrument-family check; WarpX
alone passes; an unrelated family fails. This does not bypass method approval or
other scientific requirements.

Nevertheless, continuation reviewer `oversight-00024` says the contract requires
both families and demands WarpX as an additional prerequisite. Other method reviews
repeat the same interpretation. The worker even recorded a WarpX capability probe.
My earlier steering/status interpretation did not catch this semantic mismatch.

**Attribution:** the reviewer model made an interpretation error. The harness sent
an ambiguous list name without its evaluated semantics and then accepted the
contradictory interpretation as authoritative feedback. Preparation/operator review
also failed to challenge it. This is a shared failure, not justification for adding
WarpX to a FLASH radiation-MHD campaign.

**Repair:** expose explicit `any_of` semantics and a host-evaluated requirement
result with the satisfying capability. Reviewers should assess scientific adequacy,
not redefine deterministic contract logic. Reject or request correction of feedback
that contradicts evaluated requirements. Preserve legitimate energy/resolution
objections; correcting this one false blocker does not approve the whole method.

## 4. Review failure and worker interruption differ between campaigns

The first campaign records 191 invalid oversight attempts and only six completed
oversight events. In 187 saved oversight streams the final result is empty and the
recorded output usage is 8,192 tokens. This supports output-budget exhaustion as
an important contributor, though the provider's reasoning/final split was not saved.

It also records 159 worker interruptions with reason `review_handoff`. Combined
with fresh worker sessions, this created substantial restart pressure. The final
claim review remained queued when the campaign stopped on transport failure.

The continuation has zero empty-result oversight streams in the snapshot and one
schema-invalid oversight result. Reviewer output allocation and retry changes have
already improved transport. Do not present these existing repairs as future work.

**Remaining repair:** regression-test the actual failure sequence: pending review,
unavailable reviewer, retry backoff, worker checkpoint, recovery. One pending review
must not repeatedly interrupt an otherwise useful worker while review transport
is unavailable. Keep scientific rejection separate from transport failure.

## 5. Quota failure: reproduced harness defect

The snapshot records 117 insufficient-balance errors, 117 reconnect attempts, and
6,781.9 seconds of backoff waits. Replenishment restored work.

The error event is a `result` with `is_error=true` and error text in `result`.
The classifier extracts `error` or `message`, overlooking that field. Separately,
its quota regex does not match HTTP 402 or `Insufficient Balance`.
Offline replay reproduces classification as `transient`, `retryable=true`; moving
the same text into `message` still reproduces the failure. Both layers need repair.

**Repair:** normalize provider error envelopes, classify known payment/credit errors,
and expose an actionable blocked state with resume or a sparse recovery probe.
Maintain the original deadline unless the operator explicitly changes the budget.
CLI and GUI should show provider wait, active work, and elapsed time separately.

This outage consumed wall time, but failed credit requests are not proven to have
consumed paid tokens. Do not attribute RMB cost to retry counts without billing data.

## 6. Progress detection confuses varied activity with progress

The continuation has 85 completed `research_progress` events in the snapshot; all
are true. In the first campaign 177 of 178 are true.

`observe_turn` considers either a changed durable signature **or different recent
tool arguments** progress. Consequently, different inspection commands can reset
the no-progress streak without a new result, successful repair, or resolved review.
New code is also not automatically a validated repair.

An offline replay holds the durable signature constant, starts with a streak of
five, and supplies one `ls .` tool event. The real function reports progress and
resets the streak to zero. This reproduces the behavior without a model call.

**Repair:** retain separate activity and evidence-progress signals. Do not ban
debugging or require a new simulation every turn. Track concrete changes such as
an error disappearing on replay, a reduction passing a check, an experiment finishing,
or a scientific comparison changing the decision. Use long stalls to trigger one
focused recovery review, not repeated general reviews or automatic termination.

## 7. The 3D path failure was primarily an agent submission error

The failed recorded 3D job has `binding.capability=null`. Its generator tries a host
FLASH path; that path is unavailable inside the experiment sandbox. Earlier RZ jobs
correctly bound the FLASH capability, which supplies `FLASH_ROOT`. The source code
and protocol explain that capability path. Thus this is not evidence that the
harness randomly broke a correctly bound FLASH run.

The agent failed to supply the existing capability. It had enough information to
repair this. Prior successful host-side/scratch commissioning did not validate
this particular submission.

**Proportionate improvement:** show the effective capability, mounts, and environment
in submission previews, and offer a cheap `validate_submission`/preflight path.
Reuse the known working launcher. A new scheduler or a blanket prohibition on native
tools is not justified. A capability-only omission should be caught without adding
domain-specific reasoning to the generic harness.

## 8. The agent also submitted inadequate method declarations

All six continuation method records in the snapshot use production scope. Their
model/observable fields contain placeholders such as `m`/`o`, `t`/`t`, or
`test-minimal`/`test`. Several have no validation evidence; some omit imported
modules from their source binding.

The reviewer correctly objected to these deficiencies, even while wrongly requiring
WarpX. Some submissions appear to be API probes. They should not be confused with
complete methods proposals whose only obstacle is a bad reviewer.

**Attribution:** principally poor agent use of the API. Existing instrument-readiness
scope was available but not used here. Do not invent a new methods framework to
replace an unused existing capability.

**Proportionate improvement:** cheap dry-run validation and a clear working example;
separate probe requests from durable review submissions. Preserve a useful error
message instead of making the agent learn the interface by launching reviews.
Avoid arbitrary prose-length requirements that encourage longer meaningless text.

## 9. Scientific analysis errors are real agent errors

Verified examples:

- A successful 2 ns FLASH pilot became a failed experiment because postprocessing
  raised an interpolation-length error and the promised figure was absent.
- Another completed RZ case had a `dictionary changed size during iteration` error
  in the agent-written reduction. Two larger axial cases separately hit their
  solver time limits. These are different failure types.
- `eblib.py` labels a reference time `t_ref_ns` but stores seconds. The causal
  reducer multiplies it by 1e-9. Recorded case C therefore has a purported 6 ns
  reference represented as approximately 6e-18 seconds in dependent windows.
- The compression helper indexes the high-cadence radiation time array with indices
  from the lower-cadence radius array. Offline replay with a true 2 ns minimum
  reports 0.2 ns. It also labels second-valued bounds as nanoseconds.
- The earlier energy reduction double-counts radiation contained in internal energy
  and mixes control volumes. Corrected outputs address parts of this, but a
  corrected displayed reference time does not validate previously computed windows.
- A later radius-scan reduction (`exp_fe1a41d43ac5653bc0230035`) computes
  instantaneous volume-integrated E·J, then uses its final value as accumulated
  energy without a time integral. It reports about 1.94e10 as `whole_W_EJ_J`
  for case A. The code returns power in watts at one snapshot and subtracts an
  independently time-integrated quantity in joules. This is a new dimensional
  error in a supposed accounting repair, not evidence of enormous physical heating.
  Its small total-energy residual at a selected internal surface also does not
  establish whole-domain closure merely by changing the measurement surface.

These errors invalidate particular diagnostics, not automatically the whole-window
broadband energy ratio. Distinguish unaffected observables from dependent products.

**Attribution:** agent scientific/coding failures, including failures to validate
inherited analysis. The harness cannot generally infer correct plasma energetics.
Our preparation should also have attached explicit tested limits to inherited helpers.

**Repair:** a small optional, versioned FLASH diagnostic package with explicit time
arrays, units, control-volume definitions, and manufactured checks. Keep the agent
free to implement alternatives, but require the same validation evidence for claims.
This is scientific tooling, not proof the generic agent runtime was defective.

## 10. Token observability is insufficient for exact cost attribution

The builtin adapter emits only input/output totals after agent steps. It drops
cache-hit/miss and reasoning subdivisions even if the provider supplies them.
Retries inside `generate` are aggregated. Tool observations in the log are shortened
to 1,500 characters even when the model received more. Calls interrupted before
callbacks can lack usage. These limitations cannot be repaired retrospectively by
inventing a token-per-character estimate and calling it a bill.

**Repair:** record provider-native usage at each actual request boundary, with
request ID, parent action/session, retry reason, completion status, model identity,
context component byte counts/hashes, and cost-estimate assumptions. Preserve reported
versus estimated values. Count reasoning tokens without storing private reasoning
text. Attribute full tool outputs via local artifact hashes and bounded previews.
Deduplicate accounting by request/attempt identity, not by timestamps alone.

Do not send another large campaign merely to discover where its money went. First
replay deterministic requests and a short real transport exercise with a spending cap.

## Scientific status and scope discipline

The four RZ comparison runs remain useful numerical observations. They do not
establish that the trailing-plasma mechanism uniquely explains experimental radiation
excess. A no-trailing case from the first campaign also exceeds unity, and cumulative
radiation versus peak kinetic energy alone is an insufficient discriminator.

The continuation's most important task was independent energy accounting, followed
by qualified axial/non-axisymmetric evidence. It spent substantial time repairing
and repackaging reductions. The investigator should have separated these deliverables
and closed the highest-impact uncertainty first. That is a planning issue involving
the worker, reviewer, and human steering—not a reason to add more compulsory stages.

The user was right to challenge my interpretation of the spectral cutoffs. We should
not silently replace a broadband question with an arbitrary hard-X-ray criterion.
Likewise, the OR/AND review mistake should have been caught before advising the
worker to treat WarpX absence as a hard blocker.

There is also a prospectivity limit: the later causal note explicitly cites the
already observed A/B outcomes before declaring its sensitivity thresholds. C/D
were subsequent tests, but the A/B comparison must not be described as independent
confirmation of a threshold selected with those results in hand. The existing
commitment/evidence machinery can preserve this distinction; the investigator must
use it correctly. Exploratory observations remain valuable without upgrading their
evidential status.

## Implementation plan

### Phase A: correctness and visibility, without changing scientific strategy

1. Normalize and replay real provider errors; add credit-blocked/resume behavior.
2. Expose evaluated `any_of` instrument requirements to reviewers and both interfaces.
3. Fix brief retention priorities; reserve evidence/outcome/review slots and include
   versioned resolution links. Add bounded artifact retrieval for reviewers.
4. Record per-request native usage and retry identity. Add CLI/GUI breakdowns and
   monetary/token budgets with explicit unknown-cost states.

Acceptance: sanitized 402 fixtures classify correctly; FLASH satisfies the existing
alternative requirement; the captured oversized packet retains the latest completed
experiment and unresolved review; usage fixtures reconcile exactly without duplicate
retry charges. No scientific approval is automatically granted by these fixes.

### Phase B: continuity and efficient recovery

5. Prototype resumable bounded worker sessions across normal supervisor checkpoints.
   Inject new steering/review results as deltas. Use explicit compaction when needed;
   do not accumulate unlimited history or strip required provider reasoning fields.
6. Replace unconditional action-limit final-answer generation with a cheap durable
   checkpoint where possible. Preserve a compact useful handoff when changing sessions.
   Separately measure plain-text-to-tool retry overhead; evaluate native structured
   tool history against the present textual action/observation adapter with the same
   tools and instructions. Do not silently assume a provider supports forced tool choice.
7. Separate activity, implementation progress, and evidence progress. Prevent a
   queued/unavailable reviewer from causing repetitive worker interruption.

Acceptance: use a frozen captured workspace and deterministic fake provider first.
Then compare current versus repaired behavior on the same bounded recovery task,
same model, same budget and at least three repetitions. Measure repeated guide reads,
requests, cached/uncached input, completed repairs, and reviewer correctness. A lower
token count with worse evidence quality is a failed optimization. State numerical
improvement targets prospectively after the instrumentation baseline, not after results.

### Phase C: remove avoidable experiment integration mistakes

8. Add submission preview/dry-run validation for capability, inputs, and runtime paths.
   Exercise the actual registered FLASH launcher, including the 3D path.
9. Separate simulation execution, reduction, and claim qualification in status and
   receipts. Support reanalysis of immutable solver outputs without rerunning FLASH.
   Existing analysis-only runs already demonstrate part of this; improve the entry
   point instead of creating another framework.
10. Repair and qualify the optional analysis helpers against recorded data and simple
    analytic fixtures. Report dependency invalidation when an observable changes.

Acceptance: missing-capability replay gives a targeted preflight error; corrected
submission launches through the real sandbox; a reduction failure preserves the
successful simulation and permits reanalysis; the 2 ns clock fixture remains 2 ns;
stored radiation and control-volume checks catch the known failures.

### Phase D: distinguish model ability from harness contribution

Use a two-by-two comparison: current versus repaired harness, and DeepSeek versus
one independently chosen stronger model. Freeze the workspace, tool permissions,
task, diagnostic defects, and spending limits. Do not change several prompts and
libraries along with the model and call it a model comparison.

Tasks should include: repair the recorded capability omission; diagnose the time-grid
bug; assess the mixed-volume budget without falsely approving it; prepare an adequate
method submission; then execute one bounded discriminating scientific comparison.
Keep at least one held-out defect/case so success is not just replaying the repair notes.

Score correct repairs, false scientific approvals, artifact reproducibility, quality
of bounded conclusions, wall time, paid cost where known, and incomplete accounting.
Review blind to model/harness condition where possible. Offline replay does not
replace live evaluation, but it removes easy regressions before spending tokens.

Only after those checks should another long plasma campaign be launched. It should
start from a verified drive/energy diagnostic, preserve the original scientific
question, and have a declared cost budget and measurable mechanism discriminator.
This plan does not require retiring minimal mode or imposing a rigid reasoning tree.

### Implementation locations and release boundaries

| Change | Principal existing module | Regression fixture |
|---|---|---|
| Error normalization and credit state | provider_retry.py; workspace_agent.py; study_status.py | Captured sanitized 402 result envelope, temporary connection failure, recovery |
| Evaluated alternative requirements | research_methods.py; research_oversight.py | FLASH passes existing any-of rule; reviewer cannot turn it into all-of |
| Evidence-preserving recovery packet | research_notebook.py; research_journal.py | Oversized captured notes cannot evict all current results/review blockers |
| Request-level usage | workspace_agent.py; agent_supervisor.py; status/web usage paths | Two internal requests, one interrupted request, cache fields, no double counting |
| Worker continuation/checkpoint | workspace_agent.py; research_supervisor.py | Resume after tool, running job, review backoff, operator steering, and crash |
| Evidence-progress signal | research_oversight.py | New inspection command alone does not reset the evidence-stall clock |
| Instrument preflight | research_service.py; capability/experiment launcher | Missing FLASH binding versus correctly bound short 3D run |
| Scientific helper validation | Optional FLASH skill/analysis resources | Mismatched diagnostic cadences, power versus energy, duplicate reservoir membership |

Ship correctness/observability separately from session-policy experiments. That makes
regressions attributable and avoids declaring a broad redesign successful merely
because a different model completed an easier task. The present audit changed only
documents and local audit artifacts; none of these production repairs has been applied.

Latest read-only status check, 19:35:55 China time: continuation still running, round
106, 28 successful and four failed recorded jobs, and no claim-review requests.
Those additional successes include analysis work; they do not establish new accepted
physics. The original 19:40:51 deadline remains unchanged. Detailed quantitative
audit counts above intentionally retain their earlier frozen snapshot.

## What I would not build yet

- A new top-level scheduler: the observed failures do not require one.
- A mandatory extensive diagnostic framework for every research domain.
- More general-purpose reviewer calls without better evidence access.
- A weaker acceptance gate to make the completion rate look better.
- A claim that a model is incapable based on this confounded run.
- Automatic session persistence without measuring its cache/context costs.

The immediate target is a small set of reproduced defects and information-flow
failures, followed by controlled testing of continuity. The scientific mistakes
remain part of the agent evaluation rather than being relabeled as harness bugs.
