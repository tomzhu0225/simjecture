# System architecture

The system deliberately separates scientific autonomy from execution authority.

## Human problem contract

The operator supplies the root hypothesis, operational instruction, resource
limits, installed capabilities, and any guided commissioning package. These
inputs are recorded before the agent begins.

## Reasoning agent

The model decides how to operationalize the hypothesis, which diagnostics to
write, which sub-hypotheses to register, and which admissible experiment to run
next. Its output is a typed single action, not unrestricted host code execution.

## Sandbox and capabilities

Ordinary code runs inside a network-isolated Bubblewrap workspace. Installed
capabilities are harness-owned executable environments mounted read-only into
the same sandbox. Skills explain interfaces and numerical practice but grant no
authority by themselves.

## Scientific state

The claim ledger stores root, scientific, instrument, diagnostic, and control
claims with explicit lineage and disposition. Evidence contracts freeze the
observable, decision rule, uncertainty criterion, inconclusive conditions,
machine validations, source identity, and allowed commands before decisive
execution.

## Durable operational state

Model calls and simulator intents are journaled before dispatch. Content hashes,
idempotency keys, cancellation records, heartbeats, and replay logic distinguish
scientific failure from provider, scheduler, or process failure.

## Trust boundary

The system can establish that a declared computation ran through the expected
instrument and satisfied registered gates. It cannot make an imperfect
diagnostic scientifically correct, turn a simulation result into empirical
truth, or eliminate the need for independent interpretation.
