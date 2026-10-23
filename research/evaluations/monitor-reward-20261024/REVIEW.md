# Reward design for a scientific monitoring coprocessor

Continue the 4B experiment with a better measured intervention target. The
current pilot establishes an executable training loop, but its reward and
evaluation cannot establish whether the coprocessor adds useful assistance.
The immediate target is the expected benefit of waking a capable agent now
compared with waiting, including the extra work and time each choice causes.

The literature supports this direction. It does not establish that a particular
reward or training algorithm will improve Simjecture. The proposed changes below
need new measured continuations before another effectiveness claim.

## What the existing data can tell us

The [audit](audit.json) reconstructs all 119 model-visible states from their
recorded event identities, verifies each state hash, and leaves the original
dataset unchanged. Its frozen SHA-256 is
`5389a307bb29754dee5e2391b4ff7946683d01cb60815a305d80147a60abedfa`.

Three findings change the next experiment:

1. **Case identifiers were visible in 64 of 119 inputs.** These are exact
   identifiers such as `harness-71` and `recoverable-analysis-97`, embedded in
   observed paths. Events omitted by token packing are excluded from this count.
   Both early sampled repair calls and the later grounded harness call saw such
   identifiers. This creates a possible shortcut; it does not prove the model
   used it. New rollouts need opaque filesystem roots and actor observations
   without case, treatment or split metadata.
2. **A feedback condition dominated one training comparison.** Both analysis
   episodes reported independently matching diagnostics. One received quality
   zero because an extra inferred help request, created after its report, was
   canceled at shutdown. Replacing only the binary feedback condition with a
   metric-only quality check shrinks the within-family return gap from 1.04044
   to 0.04044, a 96.1% reduction. This is a sensitivity analysis of the reward
   definition, not a counterfactual worker experiment. Metric-only grading also
   omits meaningful delivery quality and is not the proposed replacement.
3. **Proposals and interventions differ.** There were 46 non-wait proposals,
   but the gate accepted 22 and suppressed 24. Accepted alerts do not necessarily
   equal dispatched native sessions. Training and evaluation need the executed
   treatment, incident identity and delivery outcome alongside the sampled
   action. Suppressed proposals must not be charged as real agent invocations.

All four original episodes remain valid under their declared v1 protocol.
None contains the paired waiting continuation, explicit needed-feedback audit
and incident-based duplicate accounting required by the proposed reward.
Rewriting those records into a new supposedly measured dataset would be wrong.

The sampled collector and base/adapter evaluator now assign opaque trial
directories and retain case/seed/policy mappings in host manifests. This removes
the identified directory-name channel for new runs through those entrypoints.
It is not complete blinding: full observations still need auditing, and task,
fault and budget factors must be counterbalanced. The legacy v1 batch driver
retains its historical named layout and should not be used for the new study.

## Relevant research and what transfers

| Research | Relevant result | Consequence for this experiment |
| --- | --- | --- |
| [Mozannar and Sontag, ICML 2020](https://proceedings.mlr.press/v119/mozannar20b.html) | Models can learn expert deferral through a cost-sensitive objective for the combined system. | Optimize the worker plus coprocessor outcome; standalone action accuracy is insufficient. |
| [Joshi, Parbhoo and Doshi-Velez, 2022](https://arxiv.org/html/2109.06312) | Sequential learning-to-defer compares handing off now with delaying, including future interventions and expert cost. | Early intervention may be valuable. Do not penalize a call solely because a visible failure has not happened yet. |
| [Foerster et al., AAAI 2018](https://ojs.aaai.org/index.php/AAAI/article/view/11794) | COMA addresses team credit assignment with an action-specific counterfactual baseline. | Whole-study success can credit a monitor for work the worker would have done anyway. Estimate marginal intervention value. |
| [Zhang, Feng and You, Router-R1, 2025](https://arxiv.org/html/2506.09033) | Sequential LLM routing combines outcome and invocation-cost rewards, with hierarchical validity handling. | Measure the cost of the capable-agent chain and compare quality/cost tradeoffs. |
| [Qian et al., ToolRL, NeurIPS 2025](https://papers.nips.cc/paper_files/paper/2025/file/97c5b2707228e7e3fb67e4ecc2e0e607-Paper-Conference.pdf) | Reward granularity and scaling change tool-use learning behavior in their experiments. | Keep quality, feedback, dispatch and timing components inspectable; ablate their effects. |
| [Ng, Harada and Russell, ICML 1999](https://people.eecs.berkeley.edu/~russell/papers/icml99-shaping.pdf) | Potential-based shaping preserves optimal policies under the paper's MDP assumptions. | Avoid free bonuses for raising alerts or obtaining grants. Dense shaping needs a justified state, discount and terminal convention. |
| [Zhu et al., Intern-Decision, 2026](https://arxiv.org/html/2610.22131v1) | The released model learns supervised symbols at masked decision positions; labels and provenance are excluded from visible evidence. | Keep the existing 4B interface, blind case metadata and test a supervised baseline before attributing gains to RL. |

In deferral papers, *defer* means handing control to an expert. In our API,
`defer` means continuing to observe. The concepts must be mapped with that
opposite naming convention in mind.

The medical deferral results concern different experts and environment dynamics.
COMA uses a learned centralized critic and marginalizes the current action; this
proposal instead starts with repeated measured continuation pairs. Router-R1
and ToolRL evaluate answer/tool tasks, not unattended scientific streams. Their
benchmark gains cannot be transferred numerically to this project.

Potential shaping of the form `gamma*Phi(next)-Phi(current)` is a useful design
discipline, not a guarantee for our bounded observation windows. They are not
established Markov states, and actions take variable wall time. No potential
shaping is enabled by the new scorer.

## The proposed reward experiment

At a public checkpoint, preserve the worker transcript, relevant files,
simulation state, original scientific criteria, remaining budgets and frozen
model configuration. Start repeated paired continuations from that checkpoint:
one receives a specified intervention, the other keeps observing under the
same downstream policy. Randomize branch execution order. Native agents remain
stochastic; matching a public prefix is not identical hidden state or common
provider randomness. Report uncertainty across repetitions.

For each continuation, measure the components of a utility:

```text
U = verified report/progress quality
    - agent-start cost proxy
    - elapsed-time cost
    - genuinely needed feedback left unintegrated
    - redundant dispatched wakeups

intervention reward = U(intervene now) - U(wait)
```

Verified reporting of a failed scientific hypothesis can earn full quality.
A successful judge grant earns no bonus by itself. An early inspection may earn
positive value if it actually improves the compared outcome enough to justify
its cost. A denied request can also have information value; denial alone is not
an automatic negative label. A monitor should never need to manufacture a
blocker to gain reward for resolving it.

The new [scoring implementation](../../../packages/simjecture-monitor/src/simjecture_monitor/reward.py)
keeps these components separate and refuses to calculate a paired reward when
the waiting outcome, independent verification receipt or required measurements
are missing. It checks matching public checkpoint, observation, worker config,
criteria, budget and replicate identities. A measured native-worker failure is
retained with its verified low quality. An unmeasured component is not zero.
Receipt hashes are provenance fields supplied by trusted host collection; the
pure scorer alone cannot authenticate files, enforce blinding or prove a causal
effect. The v1 learner and its frozen data are unchanged.

The default coefficients are starting points for a prospective ablation, not
learned economic prices. Agent starts omit differences in token counts and GPU
residency. At the old relative weights, one additional agent start costs as
much as 130 seconds of study time if quality is unchanged. That tradeoff needs
an explicit development-set choice and a reported Pareto frontier. Unknown
provider usage remains unknown. Time cost now continues beyond the nominal
horizon rather than flattening during an overrun.

Feedback must be measured from actual result availability, need and worker
acknowledgment. A report file's modification time cannot prove understanding.
Canceling an inferred request that produced no needed information should not
erase otherwise verified numerical work. Duplicate penalties need a durable
incident identity and apply to unnecessary dispatched work, including its
interruptions; they are an explicit extra preference beyond invocation cost.

## How to improve and test the model

First validate collection and reward behavior on a small forked pilot. It must
include actionable blockers and long healthy progress, expected scientific
failures, workers that recover themselves, beneficial preemptive assistance,
and already resolved incidents. A case needs observable predictive features to
support a learned choice. Identical actor inputs with different hidden injected
labels cannot provide deterministic action supervision. Hidden labels may be
used to audit outcomes, not smuggled into the policy's context.

Then keep the base 4B model fixed and build reviewed supervision from these
observations. Experts assess the evidence and admissible actions; measured
continuations assess benefit. A case whose action advantage is uncertain should
remain uncertain rather than receive a fabricated confident label.

The model comparison should include the unchanged 4B policy, state-aware rules,
a supervised adapter, continued supervised training and RL continuations from
the same supervised checkpoint. Compare episode-level and paired rewards with
matched optimizer budgets, and account separately for their feedback-collection
costs. Split by underlying task and defect mechanism before fitting adapters or
choosing coefficients. The old adapter remains an exploratory comparison.

Evaluate useful interventions and missed incidents at a fixed wake budget,
unnecessary wakeups per healthy hour, time to useful intervention, independently
verified final reporting, and total capable-agent/monitor resources. Balanced
fault cases help diagnose behavior, but a separate rare-incident mixture is
needed to assess deployment false alarms. One scalar score cannot replace
those measurements.

The next experiment is specified in [protocol.json](protocol.json). No new
adapter has been trained from this audit, and no Colab allocation is needed for
the review or scoring checks. A new learning run requires the collection and
acknowledgment instrumentation described above.
