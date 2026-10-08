# System architecture

The system deliberately separates scientific autonomy from execution authority.

## Workflow scope

New studies default to minimal mode. Native CLI agents retain their host tools;
the built-in API agent also supports minimal mode. Minimal studies record their
own research ledger, experiment receipts and independent reviews, with an absolute
wall deadline that survives restart. Their saved completion policy distinguishes
`answer` (a reviewed negative answer can complete the root) from `repair` (a
falsified root needs a supported repair). See [minimal research](../how-to/research-service.md).

The kernel/DSH architecture below describes the classic campaign route. Its
contracts and active-time accounting must not be assumed to describe the minimal
study launcher. Structured and frontier modes remain available explicitly.

## Human problem contract

The operator supplies the root hypothesis, operational instruction, resource
limits, installed capabilities, and any guided commissioning package. These
inputs are recorded before the agent begins.

## Reasoning harness

The model decides how to operationalize the hypothesis, which diagnostics to
write, which sub-hypotheses to register, and which admissible experiment to run
next. The built-in runner and the DSH profile are interchangeable reasoning
front ends; neither is the authority for scientific state or evidence.

## Native tool boundary

Under DeepSeek Harness, scientific role filters restrict authoritative Simjecture
MCP operations. Native shell, filesystem, web, skills, workflows and configured
plugins remain available for research in a separate working directory. DSH owns
the provider, conversation, retry policy, compaction and model-facing session.
The profile uses DSH's `workspace-write` policy and non-interactive `never`
approval policy; it does not OS-isolate arbitrary plugin code. CampaignKernel
remains the scientific mutation and evidence gate. A composite adjudication tool
freezes the case, runs a fresh tool-free DSH child with a strict verdict schema,
and commits the verdict through raw endpoints hidden from researcher roles.
See [DSH setup and trust boundaries](../how-to/deepseek-harness.md).

## Campaign kernel

The model-independent Python kernel validates typed actions and owns the root
hypothesis, hypothesis graph, claim ledger, evidence contracts, commissioning,
skills, capability registry, provenance, and workspace policy. The legacy MVP
runner delegates to this same kernel, so changing the reasoning harness does not
create a second scientific implementation.

The autonomous loop exposes three operational roles. The **Falsifier**
commissions tools and searches for counterexamples. After a valid
falsification, the **Scientist** proposes a minimal `repairs` successor. When a
bounded search finds no counterexample, an independent **Judge** sees only the
auditable evidence package. The Judge reports two separate facts: whether the
record is complete enough for a terminal decision (`sufficient` or
`insufficient`), and, when it is sufficient, the scientific disposition such as
`supported`, `instrument_limited`, or `unresolved`. Record completeness never
implies support. Roles are explicit workflow contexts, not claims of different
underlying model providers.

An accepted verdict does not itself end the process. Guarded finalization checks
the entire scientific frontier and writes the report only when no open claim or
unrepaired counterexample remains. A falsified scientific frontier therefore
requires a minimal repair child; an honestly documented instrument limit may
terminate as `instrument_limited`, and an irreducible bounded ambiguity may
terminate as `unresolved`.

## Sandbox and capabilities

Recorded experiment code defaults to a network-isolated Bubblewrap workspace. Installed
capabilities are harness-owned executable environments mounted read-only into
the same sandbox. Skills explain interfaces and numerical practice but grant no
authority by themselves. Native research agents are trusted host processes, not
enclosed by that numerical sandbox. The explicitly selected `proot-cooperative`
backend supplies execution bookkeeping without OS-enforced filesystem or network
isolation; see [restricted hosts](../how-to/restricted-containers.md).

## Scientific state

The claim ledger stores root, scientific, instrument, diagnostic, and control
claims with explicit lineage and disposition. Evidence contracts freeze the
observable, decision rule, uncertainty criterion, inconclusive conditions,
machine validations, source identity, and allowed commands before decisive
execution. A `claim_decision` contract is allowed to support or falsify its
claim. A `terminal_record` contract documents why a bounded campaign cannot
decide the scientific proposition and may only end as `instrument_limited` or
`unresolved`. This distinction prevents a contract written to recognize a
failed antecedent or blocked instrument from being treated as positive evidence
for the hypothesis.

## Durable operational state

The reasoning harness retains its model session. Under DSH, a stable session ID
and event-sourced log live inside the campaign; pause, process restart, and
resume reopen that session instead of constructing a blank conversation.
Simjecture journals simulator
intents before dispatch and stores content hashes, operation identifiers,
cancellation records, process identities, and authenticated worker receipts.
Long jobs survive an MCP restart. A missing or unverifiable receipt remains an
unknown operational outcome and cannot become scientific evidence. The bounded
snapshot exposes durable jobs, operation bindings, and remaining budgets to a
fresh session. One root runner/MCP process holds the campaign ownership lease;
detached workers hold explicit active-job writer leases. For this classic campaign route, budget accounting is cumulative active execution
time, not elapsed calendar time between sessions. Minimal studies instead retain
an absolute wall deadline, including pauses and provider waiting.

## Human interfaces

The browser dashboard, Textual dashboard, `status`, and `watch` consume one
UI-neutral monitor projection. That projection derives claim status, current
typed action, loop stage and role, token usage, heartbeats, and terminal state
from durable files;
the clients do not maintain a competing scientific database.

The local web server provides a localhost API around this
projection and the existing reviewed launch/pause/resume/stop functions. Its
hypothesis graph uses the same scientific-versus-validation claim classifier as
the TUI. This boundary also allows a future reasoning engine to change without
rewriting the scientific interface or campaign record.

## Trust boundary

The system can establish that a declared computation ran through the expected
instrument and satisfied registered gates. It cannot make an imperfect
diagnostic scientifically correct, turn a simulation result into empirical
truth, or eliminate the need for independent interpretation.

Recorded evidence snapshots and completed adjudications are audit artifacts;
operational state and append-only journals continue to evolve during a study. If later review finds a semantic or scientific error, Simjecture
preserves the original bytes and attaches a corrective audit record instead of
rewriting history.
