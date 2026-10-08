# From an experiment to a scientific claim

An investigation should let you trace its conclusion back to the exact question,
method, computation and observations that support it. Simjecture records those
connections and requires a separate review before accepting a scientific claim.
This page describes the current **minimal** workflow.

## Three different kinds of progress

| Record | What it establishes | What remains to be checked |
|---|---|---|
| Exploratory result | An idea, pilot or diagnostic worth investigating | Suitability as decisive evidence |
| Successful recorded experiment | The frozen command ran and produced the recorded outputs | Numerical validity and scientific interpretation |
| Independently reviewed claim | A separate reviewer accepted support or falsification within a stated scope | External scientific scrutiny, model adequacy and any wider generalization |

A solver failure is not a physical counterexample. A timeout is not support for
an unbroken hypothesis. A reviewer requesting more work leaves the claim open.
These distinctions are visible in the study ledger and **Evidence & review**.

## What an experiment records

The service snapshots the submitted source and declared local inputs before
execution. Its receipt records arguments, source/input identities, the selected
runtime, execution status and retained output hashes. For remote jobs it also
tracks the worker and submission identity. Important analysis must be recorded
if a conclusion depends on it.

A review rechecks artifact identity. It does not accept a changed output merely
because the filename is the same. A failed, cancelled or unconfirmed execution
remains labelled accordingly; useful partial data may guide another experiment.

Native agent tools remain available for exploration. Their outputs do not
silently become accepted scientific evidence. Read [execution boundaries](architecture.md#execution-and-trust)
for the distinction between a cooperative agent and a confined numerical job.

## How methods become eligible

Instrument-backed studies can require methods review. The worker submits the
implementation, runtime binding, commissioning experiments and known limits.
The methods reviewer checks the proposed procedure before evidence execution.
Changes to bound source or dependencies require a revised proposal.

A readiness check establishes that a tool can execute its checked example.
Commissioning must also address the model, boundaries and diagnostics relevant
to the proposed study. A simple Python calculation does not need an artificial
hierarchy of instrument claims. The study's recorded requirements determine
which methods gates apply. See [methods oversight](../how-to/minimal-oversight.md).

## Counterexamples and minimal repairs

A candidate counterexample must meet the original claim's assumptions and violate
its prediction. The reviewer checks the numerical controls needed to distinguish
that failure from an implementation or measurement error.

A repair preserves its parent statement and the evidence that falsified it. The
worker must explain which assumption, scope or bound changes and why that change
is the smallest scientifically justified repair. Restricting the domain merely to
hide a failed case does not supply that explanation.

Before validation, the worker commits the replacement statement, acceptance rule,
source and exact planned commands. All committed cases need fresh recorded
execution. The service rejects altered committed inputs and retrospective
relabelling of previous runs. Independent review checks whether the replacement
predicts something beyond the observations used to design it.

For any supported claim, the worker must supply evidence of a counterexample
search: the challenge strategy, actual experiments and their outcomes. There is
no mandatory number of experiments; their adequacy depends on the proposition.

## What independent review does

The reviewer runs in a separate context and receives the target claim, operator
requirements, selected experimental evidence, source and scientific argument.
For a repair it also receives its ancestry and accepted counterexamples. Codex
reviewers can inspect relevant source and data with read-only tools; other
backends retain their configured review restrictions.

The reviewer can accept support, accept falsification, or identify missing
evidence and a next test. The research API exposes submission and review status;
it does not let the worker grant itself scientific approval. The host separately
checks whether the verdict satisfies the study's completion policy.

Some checks are deterministic: unchanged recorded outputs, committed commands,
claim identity and completed required cases. Other checks are scientific judgments:
reference accuracy, convergence, relevant controls and the meaning of a repair.
Independent review makes those judgments explicit; it does not guarantee they
are correct or replace expert review.

## When a study finishes

| Completion policy | Reviewed outcomes that can complete the study |
|---|---|
| **Answer the question** (`answer`) | Support or falsification of the original claim; a qualifying supported repair can also complete it |
| **Seek a supported claim or tested repair** (`repair`) | Support for the original claim, or accepted falsification followed by an independently supported repair |

The local browser defaults to `answer`; the CLI defaults to `repair`. The hosted
public trial currently uses `answer`. Both completion policies can use
minimal mode. A repair's ancestry must have accepted falsifications before a
supported descendant can complete the study.

Ordinary agent exit and unresolved review gaps keep the investigation open while
its budget permits. The absolute wall deadline survives restarts and includes
pauses and provider waiting. Budget exhaustion preserves partial findings without
turning them into an accepted scientific conclusion.

## Inspect the record

Start with **Evidence & review** in the workspace. For a minimal study on disk:

| Location | Contents |
|---|---|
| `research.json` | Original hypothesis, budget, mode and saved scientific policy |
| `experiments/` | Frozen numerical workspaces and execution receipts |
| `commitments/` | Prospective repair statements and planned cases |
| `reviews/` | Claim-review requests and decisions |
| `director/`, `director-acks/` | Strategy decisions and the worker's recorded responses |
| `STUDY_LEDGER.md`, `research_report.json` | Host-generated summaries of execution and scientific state |
| `research/RESULTS.md` | The worker's scientific narrative, citing the underlying records |

See [the current recorded demo](../demos/kepler-energy.md) for concrete examples.
The original [classic evidence model](../archive/classic-evidence-and-claims.md)
remains documented separately for historical campaigns and explicit legacy use.
