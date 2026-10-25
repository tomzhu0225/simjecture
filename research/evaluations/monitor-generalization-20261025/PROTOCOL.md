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
