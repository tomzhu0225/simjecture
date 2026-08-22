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

## Human interfaces

The browser dashboard, Textual dashboard, `status`, and `watch` consume one
UI-neutral monitor projection. That projection derives claim status, current
typed action, token usage, heartbeats, and terminal state from durable files;
the clients do not maintain a competing scientific database.

The version 0.1.1 web server adds only a narrow localhost API around this
projection and the existing reviewed launch/pause/resume/stop functions. Its
hypothesis graph uses the same scientific-versus-validation claim classifier as
the TUI. This boundary also allows a future reasoning engine to change without
rewriting the scientific interface or campaign record.

## Trust boundary

The system can establish that a declared computation ran through the expected
instrument and satisfied registered gates. It cannot make an imperfect
diagnostic scientifically correct, turn a simulation result into empirical
truth, or eliminate the need for independent interpretation.
