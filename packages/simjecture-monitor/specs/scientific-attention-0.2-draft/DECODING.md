# Constrained masked-decision decoding profile

`scientific-route-question/v1` is an optional decoding and training profile for
the existing scientific attention 0.2 contract. It keeps the same observation,
five masked fields and single model forward pass. It changes the distribution
over their combined answers. It is not a new scientific alert rule or an adopted
community standard.

## Public constraint and normalized distribution

The model scores route, question reference, basis and two evidence references.
An ordinary route must use question `none`. A knowledge/literature route must
use a question alias present in that observation. All visible questions remain
structurally selectable, including resolved questions; the existing host gate
separately checks usefulness, freshness, persistence and active/recent work.
No scientific measurement, fault label or outcome enters the constraint.

For raw candidate probabilities `p_r` and `p_q`, the profile uses

```text
P(r, q | observation) = p_r(r) p_q(q) I(valid(r,q)) / Z
Z = sum over valid (r,q) of p_r(r) p_q(q)
```

The other three fields retain their independent normalized distributions. The
finite-precision implementation normalizes saved marginal probabilities before
reporting validity mass. Sampling draws the route/question pair jointly; greedy
decoding selects the joint maximum. It never repairs an already sampled answer
by inventing a question or citation. A distribution with no positive mass on
valid combinations is an error, not an invented observation decision.

At most 16 visible questions produce 85 valid route/question pairs. This is
small host-side arithmetic, with no added model tokens or forward passes.
The scientific field schema must match the compiler. General decision inputs
use the unchanged `independent/v1` profile.

## Serving, collection and training bindings

Enable the same profile in the attention server and prospective workflow plan:

```text
--decision-distribution scientific-route-question/v1
```

Both single-adapter and named-adapter servers accept this flag. The collection
plan binds it before execution, checks server health and forwards it to every
sampled request. The workflow runner also forwards it for greedy evaluations.
A mismatched server cannot silently substitute another distribution.

The service retains raw model probabilities and the original independent greedy
answers. Its actual decoded answer is recorded separately. A sampled behavior
receipt includes the distribution version, seed, sampled joint log probability,
support hash and log validity mass, alongside the existing prompt/model/adapter
identities. Replay verifies these bindings against the actual input schema.
The episode exporter and trainer reject a distribution inconsistent with the
prospective plan. Old receipts without a version mean `independent/v1` and retain
their original seeded draws.

The policy-gradient loss differentiates the normalized joint distribution,
including the derivative of `log Z`; it does not use the unmasked log
probability for a masked sample. Its KL term uses the same factors, with the
existing numerical reference floor. Before updating, the initial adapter must
reproduce both the raw probabilities and the recorded constrained action log
probabilities. No constrained A100 optimizer update has yet been validated.

This follows established action-masking practice: the sampling distribution and
policy-gradient distribution must agree. [Huang and Ontañón's analysis](https://arxiv.org/html/2006.14171v3)
provides the theoretical justification and examines mismatched implementations.
The profile is an application of that method to a scientific tool contract.

## Validity is not false-alert calibration

Conditioning removes impossible combinations but redistributes their mass among
valid choices, including expert requests. It can therefore increase the rate of
valid proposals. It supplies no episode-level false-alert guarantee and no proof
of workflow benefit. Host admission and explicit worker help remain unchanged.

The [saved-trace audit](https://github.com/tomzhu0225/simjecture/blob/93a5c3b/research/evaluations/action-constraint-audit-20261026/RESULTS.md)
shows this tradeoff directly. Any subsequent efficacy comparison must use the
same decoding contract for its model arms and evaluate actual scientific work,
healthy-episode false alerts and general-decision retention separately.
