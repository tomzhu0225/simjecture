# Evidence needed for a scientific attention coprocessor

A useful research contribution would show when inexpensive monitoring helps
scientific agents, what observations it requires, and how to limit unnecessary
interruptions across workflows. The present training results establish an
executable adaptation path. They do not yet establish those broader claims.
This is a research plan, not a report of additional completed experiments.

## Nearby work changes the comparison

| Primary source | Relevant result or scope | Consequence for this study |
|---|---|---|
| [Avatar](https://arxiv.org/html/2609.10509v1), September 2026 preprint | A scientific workflow architecture exposes common observation/action interfaces to rule and LLM policies. Its experiments include recovery, scaling and molecular campaign steering. The LLM helps some infrequent decisions but performs worse on a fast scaling loop. | Scientific orchestration and a shared action catalog are existing research directions. Compare attention-only monitoring with direct orchestration, and measure inference overhead. |
| [Real-Time Detection and Repair of LLM Agent Failures](https://arxiv.org/html/2608.02464v1), August 2026 preprint | Cheap learned telemetry monitoring is combined with deterministic checks and live repair comparisons. The paper reports deployment-specific calibration needs and compares repair with repeated resampling from the same prefix. | Include a cheap learned telemetry baseline, a deterministic verifier, and an explicit continuation control. A detector score alone is insufficient. |
| [Conformal Risk Control](https://arxiv.org/html/2208.02814v4), revised June 2025 | Expected-risk guarantees require an appropriate bounded monotone loss and exchangeable calibration/test units. The basic guarantee does not apply unchanged to a non-monotone loss. | Define the calibration unit and loss before using a guarantee. Correlated polls and action-dependent future trajectories need special treatment. |
| [ScienceAgentBench](https://arxiv.org/abs/2410.05080), ICLR 2025 | The benchmark derives 102 scientific programming tasks from 44 papers in four disciplines, with expert validation. It evaluates programs, execution results and costs. | It offers an external source of scientific tasks. Its program-output interface would need a new streaming/attention adapter; current Simjecture results are not results on that benchmark. |

These sources support a narrower novelty claim than “a small model watching
scientific agents.” The potential contribution is the measured combination of
scientific evidence, attention decisions, bounded authority, calibrated
interruptions and verified downstream value. Its distinctiveness still needs
comparison with the relevant systems.

## Define two different kinds of alert error

An **unsupported alert** lacks sufficient current evidence for the requested
attention. An **unhelpful intervention** has no positive downstream value after
its costs. These differ: a real anomaly can already be handled by the worker,
while an apparently healthy simulation can still justify a knowledge lookup.
Neither a quiet fixture label nor successful final reporting settles both
questions.

Keep separate measurements for structural validity, independently adjudicated
support at dispatch, and measured intervention advantage. A reviewer assessing
support should see the same public evidence available at dispatch, without the
model identity, hidden injected label or eventual outcome. Subsequent scientific
verification should use the original task criteria and saved artifacts.

## Calibrate at the episode level

The proposed risk unit is a complete scientific episode over a declared
monitoring horizon. Count whether that episode experiences any unsupported
automatic dispatch, rather than treating each correlated poll as an independent
trial. Also report dispatches per hour, duplicate dispatches, missed actionable
incidents and detection delay.

Collect a separate calibration set with benign slow progress, retries that
recover, expected negative scientific results, delayed publication, and resolved
historical errors. Freeze the worker/tool distribution and the evidence
representation. A shadow observer can score these episodes without changing
their trajectories. Threshold selection uses this calibration set only; the
final test uses new episodes and unchanged thresholds.

For a fixed trace, an episode maximum score can support a monotone threshold
rule. In a live workflow, dispatch changes subsequent worker behavior and
observations, so monotonicity and exchangeability cannot simply be assumed from
the shadow test. Verify deployed episode risk prospectively. Repeatedly scoring
the same evidence does not supply independent confirmation votes.

As a scale illustration, zero false alerts in 299 independent healthy episodes
gives a one-sided exact 95% binomial upper bound below 1%:

```text
upper bound with zero events = 1 − 0.05 ** (1 / n)
n = 299  →  upper bound ≈ 0.997%
```

This calculation assumes independent comparable episodes and a frozen policy.
It is not a guarantee under domain shift or a statement that 299 correlated
replays suffice. Four quiet configurations cannot substantiate a 1% deployment
claim, even if none raises an alert.

## Measure intervention value before a larger update

Use the measured-wait collector to freeze public checkpoints, actual behavior
distributions and all continuation assignments before seeing returns. Every
state gets independent no-intervention controls and sampled policy continuations
in randomized order. Both paths retain explicit worker help. New branches start
fresh native sessions with the same public context and artifacts; no private
provider state is claimed to be cloned.

Train on the resulting difference in verified quality and declared costs, while
retaining the individual components. Repeated controls reduce noise but do not
make a small sample a reliable value estimate. Failed transfers and missing
measurements remain ineligible instead of becoming invented negative scientific
rewards. Known worker failures under the declared budget remain measured
outcomes. Do not choose reward coefficients or discard states because they make
the learned policy look better.

The next full evaluation should include worker-only execution, fixed rules,
a cheap learned telemetry detector, the frozen base decision model, an
equal-update SFT control and the RL model. Use the same public observations,
attention interface, permissions and worker budgets. Report actual model
serving work alongside worker usage and solver work. Agent starts alone are not
a monetary cost estimate.

## Scientific scope and release conditions

Extend beyond the eight existing mechanism templates. Hold out whole failure
mechanisms and scientific tasks, include naturally occurring failures, and add
at least one independently maintained scientific workflow. Freeze rules and
learned policies before collecting those tests. Include long-running tasks where
the worker is genuinely parked or cannot see a terminal event, as well as tasks
where an awake worker can already recover without assistance.

The reusable interface should remain an optional observer/attention tool.
Explicit help, completion checks, process supervision and hard resource limits
remain host responsibilities. The monitor requests a reviewer or repair judge;
it does not grant itself or the director new authority. Literature and knowledge
lookup requests need a concrete unresolved question and evidence identity, not
a generic request to “research more.”

Before presenting weights as a demonstrated improvement, require a prospective
workflow benefit with uncertainty reported, episode-level alert calibration on
the declared deployment distribution, and the general-retention evaluation.
Publish the input/output schema, packing policy, training/receipt provenance,
task splits, frozen baselines, ablations and measured limitations with any
released adapter. An implementation artifact or a transparent negative study
can be useful without claiming that these efficacy conditions have been met.
