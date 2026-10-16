# Extend an active study

Use **Extend time** beside the study clock in the workspace or experiment monitor.
Choose +1, +6 or +12 hours, or enter another amount. Review the current and proposed
deadline before confirming. The dialog also shows active experiment limits.

An extension adds wall time and can consume more model credit and compute. It
keeps the investigation, agent context, evidence and original scientific scope.
The running supervisor observes the new clock without a restart and notifies the
director to update its plan. The protected report reserve stays the same length.
If report writing has already started, that bounded pass can finish; research
resumes under the new clock and the extended study gets a fresh closing report.

## From a terminal or external agent

```bash
simjecture study budget --campaign ./runs/my-study
simjecture study extend --campaign ./runs/my-study --hours 12 \
  --reason "Observe the collision and relaxation window" \
  --request-key extra-relaxation-time
```

Both commands return JSON. Repeating an extension with the same request key and
arguments returns its original receipt without adding time again. Reusing that
key for different arguments is rejected. A separate intentional extension needs
a new key. Without `--request-key`, the CLI creates a new key for that invocation.

The local operator HTTP API exposes the same operation:

```text
POST /api/workspace/extend-study
X-Simjecture-Token: <token from /api/bootstrap>
Content-Type: application/json

{"campaign":"<registered campaign ID>","hours":12,
 "reason":"Observe relaxation","request_key":"extra-relaxation-time"}
```

Browser requests also send `expected_deadline`, so a concurrent change requires
reviewing the updated preview. Read-only sessions cannot grant extensions. Hosted
trial allowances remain controlled by the host; this local operator endpoint does
not provide a way around public usage limits.

`research.json` is the authoritative campaign clock. Its `budget_extensions` array
preserves each grant, previous and new deadlines, operator identity, reason and
retry key. The original launch request remains unchanged. External watchdogs
should read `simjecture study budget` instead of retaining a launch-time cutoff.

## Requests from the research agent

The worker may call:

```python
lab.request_time(hours=12, reason="The measured runtime needs another collision window")
```

The director can return `time_request` with `hours` and a concrete `reason`.
Neither operation grants time. The request appears beside the study clock for
the operator to review. Agents must plan against the current budget until an
extension is granted. Use `--request-id` to grant a request from the terminal.

## What an extension does not change

Individual experiments keep their recorded timeouts and execution deadlines,
including limits clipped to the earlier campaign cutoff. Extending the study
does not automatically lengthen those jobs. Inspect their limits in the dialog
and use retained checkpoints for a new recorded experiment when needed.

Ended, cancelled and expired studies use **Continue investigation** with a new
budget. Extensions do not revive a terminal study or change an accepted result.
Existing supervisors from releases without live budget support need one ordinary
pause/resume using updated code; installing a package does not modify a running
Python process.
