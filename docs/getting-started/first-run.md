# Run your first investigation

This tutorial takes a scientific question through counterexample search and a
fresh test of a revised hypothesis. Use it to see how the autonomous worker and
evidence system cooperate. The [recorded orbital study](../demos/kepler-energy.md)
provides an example you can inspect before spending model usage.

## Prepare the workspace

[Install Simjecture](installation.md) locally and select a compatible API model or
an authenticated native CLI in the composer. The full repair-loop walkthrough
below uses the local workspace. The [hosted trial](https://simjecture.com) supplies
its configured model and compute and currently uses the `answer` completion
policy; it can demonstrate recorded experiments and review of the original claim.

The following study uses ordinary Python, NumPy and SciPy. No external simulation
package is required. For the complete source-checkout recipe and the exact recorded
operator input, see [the demo page](../demos/kepler-energy.md).

## Start with a testable question

Paste this into a conversation:

> Help me prepare a study of orbital accuracy. For a planar Kepler orbit with
> GM=1 and semimajor axis 1, does keeping relative energy error below 0.001
> guarantee position error below 0.01 over twenty periods? Use fixed-step
> kick-drift-kick leapfrog, eccentricities 0, 0.3 and 0.6, and 64, 128, 256 or
> 512 steps per period. Compare with an independently checked reference orbit.
> Search for a counterexample. If the claim fails, propose a justified minimal
> repair and commit its predictions before collecting fresh validation evidence.
> Prepare a twenty-minute study with the repair completion policy.

This is a finite, educational numerical question. The agent still has to implement
and check its computations, choose its experiments, explain any repair and submit
its evidence for independent review.

## Review the brief and launch

Open **Autonomous research** and choose **Draft from this conversation**, or
**Grill me** if you want the agent to ask focused preparation questions.

Before pressing **Start research**, check:

- The original claim, finite case family, units and error definitions.
- The reference calculation and numerical controls the investigation needs.
- **Minimal** mode and **Seek a supported claim or tested repair** completion.
- A wall budget permitted by your local resources and model allowance.

New browser briefs normally use **Answer the question**, which can finish after a
reviewed root falsification. Choose the repair policy explicitly for this tutorial.
With a shorter budget, review or repair may remain unfinished; you can still
inspect the partial record.

## Follow the investigation

The study view shows active experiments and remaining time. Open **Evidence &
review** to inspect the original claim, recorded computations, methods and review
requests. The worker can use its existing tools and change its plan; source and
outputs used as evidence retain their recorded identities.

When a candidate counterexample appears, inspect its energy and position errors
at the same physical times. Then inspect the controls used to justify the
reference. A plot alone does not establish that the antecedent was satisfied.

If the original claim is accepted as falsified, look for a committed replacement
and **new experiment IDs** validating it. The rejected claim stays in the record.
A request for more evidence should lead to additional work while the budget allows.
See [the research loop](../concepts/research-loop.md) for the roles and feedback paths.

## Read the outcome

Open the final narrative alongside the host-generated study ledger. Identify:

1. The exact claim accepted or left open.
2. The experiments and numerical controls cited by the reviewer.
3. Whether a replacement was committed before its validation runs.
4. The domain, remaining limitations and reason the study stopped.

A supported repair is conditional on its declared numerical scope. A study that
runs out of time has partial findings, even when some individual experiments
succeeded. You can [steer or continue the investigation](../how-to/continuation-steering.md)
with a new question or budget while retaining the previous phase.

For other working styles, see [the workspace guide](research-workspace.md) and
[headless studies](../how-to/headless-studies.md).
