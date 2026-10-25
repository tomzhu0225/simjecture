# Broader raw-observation coprocessor comparison

Freeze policy code, prompts, thresholds, eligibility and analysis rules before
collecting the held-out outcomes. This follows the user's concern that a detector
written for the old stopped/running fixture did not test general monitoring.
The base is pinned Intern-Decision-4B with the validated FLA inference profile;
no model or LoRA update occurs during evaluation.

## Question and arms

Compare no proactive watcher, generic operational rules, the unchanged 4B, and a
hybrid using rules for clear operational evidence and the model otherwise. All
arms retain explicit worker help, an independent scoped repair judge and the
same fallback. Each monitor receives the same bounded raw observation schema:
public native tool events, current process/receipt facts, actual tool output and
artifact excerpts, elapsed time and declared work expectations. No host-generated
fault label, case identifier, expected action, hidden evaluation result or
HARNESS_CONTRACT_ERROR marker is supplied. A metadata collector may count events
or time their age; it must not diagnose the case for the model.

The generic baseline is frozen before test fixture implementation. It checks
nonzero terminal exits, repeated unsuccessful commands, persistent lack of new
output outside a declared quiet window, repeated output without advancement,
and literal request/source identity disagreements in a published record. It
respects completion, active assistance and recent recovery. It has no branch on
test family, fixture filename or hand-written diagnostic phrase. These are
reasonable operational heuristics, not an optimal rule system or a claim that
all useful domain invariants have been encoded.

Development/commissioning covers normal completion, explicit command failure
and declared quiet work. Test families are excluded from policy tuning. This is
local development separation, not proof that a pretrained model has never seen
similar concepts. The same experiment author defines fixtures and baselines;
there is no independent blinded benchmark author.

## Main cohort

Eight families × four arms × two repetitions:64 real native-worker trajectories.
Four healthy families cover progressing long work, quiet work within an announced
window, transient publication/retry recovery, and a resolved earlier error.
Four problem families cover a consumer waiting for the wrong artifact pattern,
incorrect diagnostic unit conversion, wrong input/output source binding, and a
nonconvergent diagnostic update cycle. Case names and truth remain in the host
manifest; execution roots are random UUIDs. The test fixture implementation and
all assignments are frozen before the first main trajectory. No tuning against
main outcomes or selecting only model-favorable cases is allowed.

Each worker performs the actual64/40 and128/80 WarpX controls, yields for an
asynchronous diagnostic/publication stage, and resumes to repair/recheck or finish
its report. The workflow includes controlled publication/progress timing so that
observers have a decision opportunity. These delays are part of the experimental
workflow and must not be reported as natural WarpX simulation time. Numerical
checks use independent saved-plot analysis and the original0.05/1e-11 tolerances.
Correctly reporting a failed numerical check remains valid reporting. The
pipeline's output can be wrong even with exit code0; successful execution does
not itself establish report accuracy.

Use a common90-second parked fallback and650-second trajectory budget, at most
four parent turns and four scientific executions. At most two parent controllers
and four native roles run concurrently. A new independent lease permits at most
288 native starts, ten per trajectory, with a six-hour absolute expiry. The old
closed lease is not reopened. Keep the local model below60% of GPU memory and
preserve unrelated processes. Colab is available if needed but is not allocated
merely to repeat a feasible local test.

Four separately declared commissioning trajectories exercise each arm using the
development conditions, and are excluded before the main cohort. Commissioning
must verify process ownership, public observation contents, feedback delivery,
scientific verification and cleanup. Instrumentation corrections are recorded
before main collection; any later correction requires preserving affected runs
and explicitly separating the new collection version.

## Measurements and interpretation

Record numeric report correctness/coverage, complete task time, actual solver
executions, all downstream native starts, model calls/latency/errors, first
observable evidence and actual dispatch, fallback use, raw/effective decisions,
feedback obligations/acknowledgments, false wakes on healthy cases and missed
pre-fallback attention on persistent blockers. Preserve every failure. Delay
benefits require an actual dispatch and subsequent useful validated action;
a raw class choice is not an executed intervention.

Report all per-case outcomes and unweighted components first. Summarize family
and healthy/problem subsets with paired-by-seed descriptive differences; these
are fresh native histories, not cloned private provider states or matched future
randomness. A model improvement requires better completed-work outcomes or
recovery cost without a material healthy false-alarm burden. Two repetitions are
exploratory, insufficient for a broad superiority claim. No retrospective reward
weight search or test-driven LoRA training is part of this stage.

Pre-collection interface details: proactive decisions are evaluated while the
main worker is parked for asynchronous work. The observer records a new factual
snapshot every five seconds, including quiet periods. Each trajectory permits
one discretionary attention request; explicit worker requests and required
feedback remain available afterward. This fixed budget prevents repeated model
alerts from creating an uncontrolled cascade and makes a premature first request
an observable policy cost. No model call is needed while assistance is active or
after the discretionary budget is used. The claim is limited to this parked-work
interface; unproductive private reasoning by an actively thinking worker is not
measured here. All policies receive the same compact task and bounded public
snapshot; any model-side event omission is flagged as an observation-contract
violation rather than silently accepted as an equal-information comparison.

Pre-collection execution details: failed or inaccurate terminal diagnostics can
be reprocessed through a supported command that reuses the existing physical
outputs. Every arm can therefore recover after ordinary completion/fallback;
the observer is not the only path to correcting a result. Parent concurrency
is grouped within counterbalanced policy blocks (reverse order in repeat2), so
an observation-only task is not paired concurrently with a model task. Raw
publication histories and objective recurrence counters are visible to both
policies. No policy parameters are changed after the baseline freeze.

A separate identical-input diagnostic comparison will select the first parked
observation at or after10,25,40seconds from each observation-only main trajectory,
before that parking interval ends. Missing selections remain missing. Apply the
same frozen rule/model/hybrid decisions to these exact packets after collection;
this supplements the live outcomes and does not create training data or matched
private-state trajectories. It prevents differing live histories from being
mistaken for a same-input policy comparison.

Pre-main baseline correction: during the design review, before any held-out
outcome, the new operational comparator was found to omit the scientific-check
route already implemented in the earlier generic RulesPolicy. The main rules
and hybrid arms will include that pre-existing condition: a published
`original_checks_passed=false` routes director attention, subject to the same
busy/completed safeguards. This is a raw tool result, not an injected-fault label;
it can also produce an unnecessary wake on a legitimate negative scientific
result. The original operational policy remains unchanged and archived. A final
policy freeze records the added composition and driver hashes before main
collection. This explicit amendment supersedes the initial baseline composition;
there has been no tuning against held-out model or worker outcomes. The original
operational-only policy is retained for the identical-input diagnostic analysis.

Final scientific contract before main collection: report the absolute saved
peak electric field in V/m for each run, as well as the original relative checks
and calibration. Independent host code reads the actual field arrays and checks
reported peaks with relative tolerance1e-6. In the unit-conversion family the
relative checks still operate on the original arrays and can pass, while the
absolute reported quantity is converted incorrectly. Thus this case does not
supply a ready-made failed-check alarm. The source unit convention and actual
raw/stated quantities are public observations for both policies.

The initial four commissioning runs (v1) all completed their earlier numeric
contract; they remain excluded setup records. Before main collection, v2 corrects
an observation-task wording mix-up (worker execution instructions belonged in
the worker brief), explicitly documents supported reprocessing, enables the
stronger pre-existing-check comparator, and validates the added absolute quantity.
Run four new v2 commissioning cases before the main cohort. No held-out problem
family has been executed or used to tune either policy. Both commissioning
versions remain available with their own source revisions and scopes.

Collection v2 scheduling amendment (after eight v1 assignments started): the
first attempted main cohort exposed an experiment-driver defect. After a terminal
pipeline, an explicit `lab.wait` for help was immediately defeated by repeated
`process_terminal` notifications, consuming later native turns before assistance
returned. Six trajectories ended and two active trajectories were interrupted;
the remaining56 assignments were not started. Preserve the full v1 manifest and
all outcomes, excluding the entire v1 batch from the comparative cohort. No
policy, model, observation task or scientific fixture is tuned from these runs.

Before restarting all64 assignments as v2, treat completion as a one-time edge,
respect explicit help waits, and explicitly wake the service on returned feedback
or the common90-second fallback. A separate real healthy-workflow commissioning
forces one post-completion required helper request and verifies actual return,
acknowledgment and final scientific accuracy. Two regression checks cover pending
help and repeated terminal notifications. The common turn/time caps are unchanged.
The six-hour native lease retains its original absolute deadline; raise its total
start allowance from288 to512 to account for the discarded collection and
additional commissioning. Four simultaneous roles and ten starts per trajectory
remain the limits. No additional Colab allocation or model training is required.
