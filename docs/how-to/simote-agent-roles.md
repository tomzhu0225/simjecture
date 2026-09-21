# Scientific roles with Simote agent sessions

Simote can run Codex, Grok, and AGY (Antigravity) CLI agents as claim-scoped Simjecture workers.
Simjecture remains the authority for evidence, claim disposition, jobs, budgets,
and campaign finalization. The native API runner and DSH profile remain available.

Install the matching Simjecture checkout on the compute worker, including the
`simjecture-call` entry point. Restart Simote after updating its server. Agents
and their logins remain on the Simote host; compute happens through the existing
SSH bridge. This integration uses the selected bot's engine and model.

In Simote, enable **Simjecture campaigns** under **Settings → General →
Experimental features**. It is off by default: standalone Simote does not need
Simjecture, load its campaign page, poll campaigns, or expose campaign tools to
ordinary agent sessions. Disabling it hides the page and prevents new campaign
and role launches; existing assigned work can finish and records are preserved.

## Run a shared campaign

1. Configure a campaign-owner bot and one or more worker bots in the same Simote
   team section, using the same named SSH compute machine. Select Codex, Grok, or AGY
   agent engines for the workers, with their existing local logins.
2. Ask the owner to use `simjecture_open_campaign`. The owner keeps the campaign
   under its workspace. Scientific worker tasks share that campaign; they do not
   create copies under their own bot workspaces.
3. The owner calls `simjecture_assign_role`, for example:

   ```json
   {
     "campaign_id": "invariant-test",
     "assignment_id": "falsify-root-1",
     "agent_id": "YOUR_GROK_BOT_ID",
     "role": "falsifier",
     "claim_id": "claim_root",
     "max_operations": 100
   }
   ```

   This starts a fresh task on the selected bot. Other supported roles are
   `lead_scientist`, `repair_scientist`, and `blocker_resolver`. The target bot
   must be idle. A Repair Scientist requires a falsified parent.
4. The worker reads `simjecture_snapshot` and uses the typed `simjecture_*`
   tools exposed from its role-filtered kernel catalog. The supervisor binds
   the campaign identity. Every mutating
   operation ID begins with its assignment ID and `:`. The worker finishes with
   `simjecture_handoff`; the kernel record must substantiate claimed
   falsifications and linked evidence. A handoff ends that assignment, not the
   campaign. Only one unfinished scientific worker assignment may own a claim.
5. For independent review, the owner or assigned lead calls
   `simjecture_adjudicate` with `campaign_id`, `judge_bot_id`, `operation_id`,
   `claim_id`, `contract_version`, and `case_for_sufficiency`. The selected
   Codex/Grok/AGY instance receives a fresh session, empty working directory, no
   conversation history or Simote integrations, and only the frozen case.
   Tool activity invalidates the review. Only a successful text-only response
   reaches Simjecture's existing verdict validation and scientific gates.
6. The owner or lead uses the official `finalize_campaign` tool only when the
   scientific frontier is ready. A chat reply never finalizes a campaign.

Assignments appear as named tasks in Simote, with the normal streamed agent
activity. `simjecture_snapshot` includes assignment identities, operation counts,
session history, and handoffs. The optional **Simjecture** sidebar page shows a
hypothesis graph, claim contracts, linked evidence previews, jobs, role tasks,
and the final report. You can create or attach a campaign, assign workers,
request independent review, cancel jobs, and finalize through the same kernel
gates. The existing Simjecture web dashboard is also available.

AGY workers require the instance's full-auto setting, because its headless CLI
cannot approve MCP calls interactively. Simote mounts named scientific MCP tools
for each turn and removes them before a tool-free judge starts. AGY uses a global
MCP configuration, so Simote serializes AGY child lifetimes to prevent one task
from receiving another task's credentials. User-configured MCP entries remain
preserved; any observed judge tool use rejects the review, as for other engines.

## Recovery and boundaries

Campaign creation first probes Bubblewrap namespace support. A GPU container
that denies user namespaces is not a compatible scientific worker, even if
SSH and ordinary commands work. Use a compatible Linux host; no fallback skips
isolation or turns a failed run into evidence. `simjecture-call --workspace
./campaigns --probe` checks readiness without creating a campaign.

Parallel agent tool calls are queued per campaign. A narrowly identified
pre-dispatch writer conflict may be retried while a detached job commits its
receipt; ambiguous errors are returned for explicit operation-ID recovery.

Reopen the same Simote task to continue after a server restart. The task retains
its campaign routing and native session cursor. A new session must read a
snapshot before scientific work. Reuse the original operation ID and arguments
after a lost response; neither the assignment budget nor the kernel's operation
journal resets. Existing jobs are reconciled by the kernel on reopen.

Repeating `simjecture_assign_role` with the same identity returns the existing
task. It does not automatically rerun a previously dispatched task. A changed
assignment needs a new ID. An inconclusive or blocked handoff is preserved;
start a new assignment for subsequent work. A saved judge verdict is reused
after a remote commit failure; an operation cannot silently bind a new case.

The Simote role registry contains routing metadata only. Authoritative
assignments live in `role_assignments.json` beside the campaign ledger, outside
the experiment sandbox. The campaign supervisor lease serializes one-shot
calls. A campaign already owned by a running DSH/native supervisor cannot also
be driven through this transport.

Role enforcement covers the Simjecture tool boundary and Simote's remote tool
endpoint. Provider CLIs may also have native local tools or user-configured
integrations; this feature does not turn those CLIs into OS-isolated processes.
It never copies SSH credentials into those processes. Scientific outputs still
have to pass the existing sandbox, provenance, and evidence gates.

## Headless supervisor interface

Any trusted supervisor can use the same role boundary without running Simote.
First open a campaign normally, then issue a JSON assignment with exactly
`assignment_id`, `agent_id`, `role`, `claim_id`, and `max_operations`:

```bash
simjecture-call --workspace ./campaigns --campaign invariant-test \
  --issue-assignment-file assignment.json

simjecture-call --workspace ./campaigns --campaign invariant-test \
  --assignment-id falsify-root-1 --agent-id grok-worker --session-id session-1 \
  snapshot
```

Pass `--arguments-file` for tool arguments, `--list` for the role's tool catalog,
or `--handoff-file` for a structured final handoff. The supervisor supplies the
authenticated identity flags; they must never come from model tool arguments.

The DSH profile retains its existing role orchestration and guards. This
transport adds a persistent boundary for external agent sessions without
changing recorded campaigns or their scientific acceptance rules.

## Persistent CLI supervision

An external worker's exit or handoff is a checkpoint, not permission to end a
campaign. To run AGY or Grok without an interactive Simote owner, prepare an
initialized campaign with `MVPAgentConfig(require_independent_contract_review=True)`
and an operator instruction file, then start the persistent supervisor:

```bash
simjecture-supervise --campaign /absolute/path/to/campaign \
  --state-dir /absolute/path/to/supervisor-state \
  --instructions-file /absolute/path/to/instructions.txt \
  --backend grok --model grok-4.6 --judge-model grok-4.6 \
  --wall-seconds 21600 --turn-seconds 600
```

From a checkout, `python -m conjecture_solver.agent_supervisor` is equivalent.
The supervisor resumes unfinished assignments and issues successors after
inconclusive or blocked handoffs. Local turn/operation limits do not reset the
campaign deadline or end the study. Its durable `state.json` and `events.jsonl`
record progress. Restarting with the same state directory preserves the deadline.
One persistent supervisor can own a campaign at a time.

Workers request independent review by writing `review-request.json` in their
native research directory, with `claim_id`, `contract_version`, and
`case_for_sufficiency`. The supervisor freezes the kernel case and launches a
fresh judge through the selected CLI backend in an empty directory. Any observed judge tool activity rejects
the verdict. Only the kernel can accept the verdict or finalize the campaign.
Judge rejection and insufficient evidence return to experimental work.

With the default strict repair loop, an accepted `unresolved` or
`instrument_limited` record leaves the scientific claim open. Normal completion
requires independently accepted support for the original claim or its repair
frontier. A falsified frontier requires a repair and further testing. Existing
legacy claims already closed as unresolved require explicit recovery; the
supervisor refuses to reinterpret them as success.

The wall-time boundary saves `budget_exhausted`, preserves the open ledger and
cancels active jobs. Operator controls are separate: write
`{"command":"pause"}` or `{"command":"cancel"}` to the supervisor's
`control.json`. Repeated infrastructure/provider failures pause with a recorded
error; they never count as scientific completion. Remove a pause command before
resuming. This does not OS-sandbox the agent's native tools or alter its global
MCP configuration; numerical jobs retain Simjecture's sandbox and evidence rules.

### Contract and qualification review

New persistent runs require `require_independent_contract_review=True`. The
legacy default remains false so historical manifests remain readable; the
persistent supervisor refuses that legacy policy instead of silently accepting
old qualification. Start a new reviewed campaign to requalify an instrument;
old artifacts may be supplied as unaccepted research context.

A worker first registers its prospective contract, then writes
`contract-review-request.json` containing only `claim_id` in its research
folder. The host freezes the original hypothesis, parent statement, exact
contract, bound program sources, and optional operator-owned
`operator_input/scientific_protocol.txt`. A separate review must approve this
packet before evidence execution or sufficient evidence linking. A changed
contract, source, or frozen protocol invalidates the approval.

After collecting and linking prospective instrument/diagnostic/control evidence,
the worker writes `qualification-review-request.json` with `claim_id`. This
second review includes actual linked output and provenance; only approval permits
supported closure. Execution status, stage labels and output counts cannot stand
alone as physical qualification checks, even if labelled with the expected
aspect. The kernel enforces both reviews; workers have no approval tool.

Reviews and transcript hashes persist outside the numerical workspace in
`scientific_reviews.json`. These are scientific reviews, not user confirmation
prompts. Judge transport accepts a single outer JSON fence, validates semantics,
and retries malformed output once in a fresh context. It never changes an invalid
scientific disposition to make a verdict acceptable. Observed judge tool activity
rejects the response. Worker native tools remain available. Both CLI backends
retain their existing logins; the supervisor does not rewrite global MCP settings.

### Optional researcher workflow

Use `--workflow frontier` to let one researcher organize experiments, pursue
supporting claims and test repairs without switching scientific roles. The
structured workflow remains the default. Both use the same evidence contracts,
provenance checks, independent reviews and completion rules.

For a campaign configured with independent contract review:

```bash
simjecture-supervise --campaign /absolute/path/to/campaign \
  --state-dir /absolute/path/to/new-supervisor-state \
  --instructions-file /absolute/path/to/research-instructions.md \
  --workflow frontier --backend codex-glm --model glm-5.3 \
  --wall-seconds 21600 --turn-seconds 600
```

The `codex` backend uses the same native CLI protocol and requires an explicit
`--model`. Each backend retains its existing login. Native thread resumption is
currently implemented for `codex` and `codex-glm`; AGY and Grok retain the stable
research directory and kernel state across invocations. Do not switch workflow
or backend inside an existing supervisor state directory.

The researcher keeps a stable `research/` directory. Native tools remain
available, and detached numerical jobs need not block other research. In this
mode `--turn-seconds` is an inactivity watchdog: provider output or kernel action
activity resets it. It cannot extend the campaign's fixed wall deadline. A model
ending its turn does not declare the science finished. Review requests move to a
durable host queue, which survives a pause or deadline; resuming an exhausted
budget does not create a new deadline.

Inside the generated research directory, the agent can use the scoped client:

```python
from lab import lab

lab.write("measure.py", "print('measurement')\n")
result = lab.run_python(["measure.py"], inputs=[], request_key="probe-1")
# After registering an actual prospective evidence contract:
lab.request_review("contract")
```

The client fills in operation IDs, the assigned claim and administrative notes.
Scientific inputs and declared artifact dependencies remain explicit. Repeating
an identical request reuses its receipt; use a different `request_key` for an
intentional replicate. `run_python` also binds this identity to the entry script
and contract revision. The client cannot approve evidence or finalize a campaign.
For other operations use `lab.call(tool, arguments)` and inspect the generated
adapter's `schema TOOL` output.

Evidence validation paths support object keys and array indices, for example
`rows.0.N`, `rows[0].N` and `$.rows[0].N`. Wildcards, slices, expressions and
negative indices are unsupported. Checks retain strict scalar comparison rules.
A design reviewer may approve a proposal and suggest executing it next; required
evidence or design gaps still prevent approval. Design approval is not a
scientific conclusion.

Native agents run under a cooperative trust model with access to their host
account. These role checks do not provide adversarial isolation from host files.
Numerical execution retains its existing sandbox and evidence rules.

The first real GLM pilot supports reduced context loss, but neither workflow
completed an accepted scientific conclusion within its short budgets. Keep this
mode opt-in pending further evaluation. See the
[measured results](https://github.com/tomzhu0225/simjecture/blob/main/research/evaluations/frontier-workflow/RESULTS.md) and
[design notes](https://github.com/tomzhu0225/simjecture/blob/main/research/evaluations/frontier-workflow/DESIGN.md).

For the smaller service with explicit experiment/review receipts and agent-owned
planning, see [agent-owned research](research-service.md). Minimal is now the
default for new native-agent studies; select `--mode structured` or `--mode
frontier` for the alternatives. Existing campaigns retain their recorded mode
and record format. The browser/TUI now select these native modes too; DSH/API remain explicit legacy choices.
