# Decision after the new real-worker measurements

The useful research target remains a small background observer that notices an
unreported blocker or emerging inconsistency while the main worker is occupied
or parked. The target is earlier useful attention under a fixed interruption
budget. Directing the overall research plan and granting repair authority remain
large-agent roles. A decision-model alert is a request for attention, not a
scientific judgment or a permission grant.

The [32 continuation measurements](../monitor-paired-20261024/RESULTS.md) found
no reporting-score gain and more native starts from prescribed extra attention.
The [parked-worker study](../monitor-parked-20261024/RESULTS.md) demonstrated a
real model-origin wake/judge/repair/resume loop, but rules solved its explicit
receipt contradiction faster. These observations justify keeping rules for
structured process invariants and studying models on ambiguous public evidence.
They do not justify training a larger policy on duplicated known faults.

The [feedback declaration validation](../monitor-help-feedback-20261024/RESULTS.md)
closes a concrete reward-measurement gap. Required/advisory intent is frozen
before dispatch, with operator opt-in enforcement. Legacy missing intent remains
unknown and its strict reward is withheld. The declaration is not a necessity
oracle: an operator must pin critical obligations and audit policy-selected
labels to avoid rewarding a policy that evades required feedback.

## What to collect next for actual RL

1. Separate incident mechanisms before generating trajectories. Keep whole
   mechanism families, stream orderings and task templates out of training.
   More repeats of these eight checkpoints are useful for variance estimates,
   not a task-disjoint test. Preserve a rules/observe/periodic comparator.
2. Include quiet-stream temporal evidence, expected long-running computation,
   self-recovery, unreported analysis loops, contradictory diagnostics and stale
   resolved incidents. The budgeted timer follow-up tests the observation gap
   separately from training. Record actual observation age and queue delay.
3. Freeze scientific criteria and downstream policy. At an eligible public
   checkpoint, collect actual randomized wait/intervention continuations with
   identical restored files, public context, worker configuration and budget.
   Call them public-context replays; never imply access to private model state
   or matched future randomness. Retain aborts and late/duplicate interventions.
4. Preserve outcome components: independently checked report correctness and
   coverage, time to useful validated action, late/false wakeups, all downstream
   native starts, actual cumulative usage with uncovered calls marked unknown,
   feedback obligations and acknowledgment. Keep reporting accuracy separate
   from scientific insight; the present Q=1 checks numeric reporting and does
   not independently grade diagnosis quality.
5. For policy-gradient training, collect sampled decisions with exact prompt,
   model/runtime identity, action probability and eligible live trajectory
   return. The current prescribed-action and greedy cohorts supply analysis,
   not interchangeable on-policy records. Counterfactual value estimates may
   inform a separately specified baseline; do not relabel them as sampled PPO
   data. Check policy ratios before updating and saved-adapter identity after.
6. Fix reward weights and delay discount before seeing test outcomes. Report
   unweighted components and cost/latency sensitivity alongside any scalar.
   Required feedback failure can impose a justified gate; undeclared need
   withholds the scalar. Do not turn every pending optional helper into total
   scientific failure. Potential shaping should preserve the intended terminal
   objective rather than insert arbitrary bonuses for waking a director.
7. Keep a locked test set and a no-update adapter control. Report held-out
   decision/value changes, false alarms, latency and native costs. An altered
   probability or a lower training loss alone is not an improvement.

The literature supporting deferral, counterfactual credit and shaping is linked
in [the primary-source review](REVIEW.md). These are design implications from
that review and the local measurements, not claims that a cited paper already
solves scientific worker supervision.

## Model and compute decision

Continue the pinned `internlm/Intern-Decision-4B` baseline rather than changing
model, reward, observation and worker policy at once. Its original measured
4B LoRA job already fit within 12.16 GiB peak allocated CUDA memory, so the
available A100 is adequate for that tested configuration. Memory feasibility is
not evidence of training benefit. Keep the V1 adapter frozen: on eight new
public checkpoints it changed no greedy action, with a largest probability
shift of about 1.53 percentage points. No new adapter was trained in this stage.

The optional FLA runtime is an operational improvement under numerical and action
checks, with no changed weights. Its floating-point probabilities differ, so
future training must log behavior probabilities on that runtime. Do not loosen
the existing policy-identity/ratio checks to reuse old logs. Local experiments
use the shared Ada GPU without stopping the unrelated simulation; Colab remains
unallocated during this stage. Spend future A100 time only after sampled data,
held-out mechanisms and a measurable target are ready.

At the measured 2.22-second warm decision time, a single sequential server's
idealized service ceiling is about 0.45 decisions/second before queuing and
other overhead. This is a calculation from the local benchmark, not an isolated
throughput result. A resident 4B also occupies substantial VRAM. Use cheap process
invariants and event filtering continuously, with the 4B invoked on changed or
coarsely aged ambiguous evidence and deduplicated per incident. The target is
second/minute-scale workflow supervision, not numerical feedback at plasma
simulation timesteps. Typed diagnostic summaries should carry the evidence;
raw simulation fields and long private agent histories are not the model input.

The grace commissioning also shows a credit-assignment hazard: a raw correct
model request can be blocked by host eligibility/cooldown bookkeeping before any
native judge starts. Log raw choice, eligibility reason, effective route and
execution receipt separately. A deliberately deferred reservation must not be
counted as an executed interruption or silently labelled a learned wait choice.
Whether a future optimizer should learn the host gate's behavior depends on its
observed state and specified environment contract; these prescribed greedy
commissioning runs are not sampled PPO data. The fixed gate is exercised
separately, retaining the original failed commissioning rather than rewriting it.
