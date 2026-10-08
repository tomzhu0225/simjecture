# The autonomous research loop

You bring a scientific question, a starting hypothesis and the conditions under
which an answer would matter. Simjecture gives an agent a bounded period in which
to investigate it, while keeping an inspectable connection between each claim,
the experiments behind it and the decisions made in review.

![A human frames the question; the worker tests and challenges it; a falsification leads to a committed repair and fresh experiments; independent review can accept a conclusion or return missing evidence.](../_static/architecture/research-loop.svg)

## 1. Agree on the question

Start in a conversation. Supply the physical model, relevant observations or paper,
available instruments and a time budget. The agent can help turn these into a
testable statement. Review the study brief before launching; the original question
and operator requirements become part of the record.

A useful hypothesis predicts a measurable outcome in a stated domain. For example,
"energy error below this threshold implies position error below that threshold
over twenty orbits" specifies an implication that an experiment can challenge.
"Study orbital dynamics" leaves the success criterion open.

## 2. Let the agent choose the experiments

In the default **minimal** mode, the worker chooses its plan, writes code, uses
its native tools and selects which numerical experiments to run next. It can
develop diagnostics, commission an instrument and explore alternatives. A research
director can check whether its strategy is still useful and affordable, and request
a recorded replan.

The worker submits decisive computations through the experiment service. Each
submission preserves the source and declared inputs, command, runtime identity,
execution outcome and output hashes. You can follow active jobs and open the
actual files from the study.

## 3. Search for a counterexample

A successful simulation tells you that a computation ran. The scientific question
is whether its result challenges or supports the stated prediction. A candidate
counterexample needs the relevant controls: units, reference calculations, numerical
resolution, model assumptions and uncertainty.

For a supported claim, the reviewer requires evidence of an active challenge.
Boundary cases, failure-prone regimes or an exhaustive finite test can be useful.
The worker explains which tests challenged the claim and what happened.

## 4. Repair a falsified hypothesis

With the **Seek a supported claim or tested repair** completion policy, an accepted
counterexample starts another scientific step. The agent proposes a replacement,
explains the smallest justified change and preserves the parent claim and its
counterexample.

Before testing that replacement, it commits its statement, acceptance rule and
exact planned computations. Fresh experiments then test those predictions. The
system checks source and command identity and that the committed cases were run;
the reviewer judges whether the repair explains the failure and is scientifically
meaningful. Further counterexamples can produce further branches.

The **Answer the question** policy also permits a reviewed falsification of the
original claim to finish the study. New browser studies default to this policy;
the headless CLI defaults to the repair policy. The hosted public trial currently
uses answer policy; use a local workspace or CLI study for the full repair loop.
Choose deliberately when preparing the brief. Research **mode** and **completion policy** are separate settings.

## 5. Review the evidence independently

A separate agent context examines the target claim, frozen source, results,
controls, counterexample search and, for a repair, its ancestry and prospective
commitment. It can accept support or falsification, or return specific evidence
gaps. Gaps send the worker back to investigation while time remains.

The worker cannot approve its own claim through the research API. An independent
agent review is still a model judgment; domain experts remain responsible for
interpreting physical adequacy and any publication claim. The record makes that
judgment inspectable.

## Keep human insight in the loop

You can inspect intermediate results and send guidance at a checkpoint: consider
a neglected mechanism, compare against a paper, or seek a cheaper complete
calculation. The original claim and requirements stay fixed within the phase.
Changing them or adding time creates a linked continuation with selected prior
files and an explicit new brief.

At the deadline, incomplete work remains incomplete. A normal model exit, a failed
solver or an attractive plot does not constitute a reviewed answer. Partial work
can still inform the next phase.

## What you take away

- A scientific narrative linked to experiments and reviews.
- The original hypothesis and any committed replacements, with their relationships.
- Frozen experimental inputs and recorded outputs, including failures and interruptions.
- Review decisions, missing evidence, steering and strategy changes.
- Reported model usage and execution costs, with missing measurements identified.

Read [the evidence system](evidence-and-claims.md), follow the
[first investigation](../getting-started/first-run.md), or inspect a
[recorded example](../demos/index.md).
