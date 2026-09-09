# Scientific roles with Simote agent sessions

Simote can run Codex and Grok CLI agents as claim-scoped Simjecture workers.
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
   team section, using the same named SSH compute machine. Select Codex or Grok
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
   Codex/Grok instance receives a fresh session, empty working directory, no
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
