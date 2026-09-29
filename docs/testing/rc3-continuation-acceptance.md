# rc3 continuation and steering acceptance — 2026-09-29

This is a development preview deployed on the operator's remote machine, not a
published GitHub/PyPI release. The existing scientific study remains unchanged.

## Automated checks

- Full suite:738passed,7skipped (optional operator-installed scientific runtimes),
  174.77seconds. Subsequent focused tests cover the final reviewer-budget and
  compact-handoff adjustments.
- Final continuation/steering and browser suite:11passed. Checks cover parent
  immutability, new budgets after expiry, selected-file snapshots and tamper
  detection, path/credential exclusions, durable/idempotent steering, reviewer
  visibility, read-only HTTP rejection, empty-review recovery and oversight backoff.
- Chromium exercises the monitor→workspace continuation dialog, file selection,
  editable brief, linked phase launch and queued guidance shown in the study card.
  It confirms no new study launches merely by preparing the proposal.
- Lint, changed-file formatting, JavaScript syntax and the warning-as-error Sphinx
  documentation build pass. Pre-existing formatting differences in unrelated files
  were left untouched.
- Wheel and versioned installer source bundle were built; the latter includes the
  new continuation module. No scientific source, tables, credentials or raw run data
  were added to release artifacts.

## Real remote checks

An isolated rc3 Python environment was installed alongside rc2 on117.50.196.111.
The web interface on loopback8766 now serves rc3, explicitly scans the existing
research directory and shows the old study as budget-exhausted rather than running.
The separate older workspace on8765 was not replaced.

A continuation test used the actual stopped Z-pinch study as parent, copied four
working programs, verified the frozen snapshot, delivered an operator note and
confirmed that the parent manifest hash was unchanged. It launched no research
agent or simulation.

The exact previously failing independent-review prompt was replayed using the
existing DeepSeek connection. An intermediate replay reproduced an empty length-
limited reply, then recovered through the bounded non-thinking retry. Inspection
also found that smolagents model defaults override per-call `max_tokens`; the final
implementation therefore sets the reviewer allocation at model construction.
With that correction the final real replay returned a schema-valid `needs_revision`
verdict on attempt1 in15.60seconds (59,456input /2,845output tokens reported).
This is a transport/schema test. It did not apply a verdict or resolve the old review.

The deployed GUI was tested through SSH forwarding in Chromium with no page errors.
Using its actual Continue investigation dialog created a Z-pinch continuation draft:
11selected files, DeepSeek Flash, and a proposed editable10-hour budget. It directs
independent boundary accounting followed by resolved RZ/selected3D mechanism tests.
The draft is visible in Autonomous research and has NOT been launched. No new research
allocation begins until Start research is selected.

Local screenshots: `artifacts/workspace-preview/continuation-proposal.png`,
`study-guidance.png`, and `remote-rc3-continuation.png`. Remote acceptance records are
under `/srv/simjecture-stagnation-20260928/rc3-validation/`; the active interface log
is `/srv/simjecture-stagnation-20260928/web-rc3.log`.


## Agent-guided continuation follow-up

The dialog now offers Cancel, Prepare directly and Prepare with agent. Browser
and provider-protocol tests cover opening chat with no prewritten constraints,
agent-created briefs, follow-up conversation, and retaining parent lineage and
instruments. An existing direct draft can also be discussed via its visible
Prepare with agent button. Selected inherited paths are validated when the agent
changes them. A missing model leaves recoverable preparation state, not a hidden
failed research launch.

Follow-up validation: chat/provider regression tests passed; the final browser,
image/simulation and continuation-focused group passed23tests. The deployed dialog
on8766 was checked in Chromium: all three actions are visible, with no page errors.
No real preparation conversation or research run was started by that deployment
check. The existing Z-pinch draft was preserved. The active runtime is now
`rc3-chat-venv`, with `web-rc3-chat.log`; the earlier environment remains available.
