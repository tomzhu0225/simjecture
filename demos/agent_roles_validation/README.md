# Live Codex/Grok role validation

This is an actual subscription-CLI integration run, using Simote's Codex and
Grok drivers, its role-filtered MCP tools, a real loopback SSH connection, and
Simjecture's Bubblewrap execution/evidence kernel. No model or scientific
execution was mocked. It deliberately tests a simple false claim, not a new
scientific discovery.

- Grok falsified the original 0.001 error bound for ten binary64 Euler steps.
- A fresh Codex Repair Scientist changed only the bound to 0.02 and registered
  a prospective contract without running an experiment.
- A fresh Grok Falsifier generated new evidence. An intentionally dropped
  contract-registration response was recovered by retrying identical arguments
  and the same operation ID; the durable result did not change.
- A fresh, tool-free Codex judge accepted the evidence for the repaired finite
  claim. Simjecture then finalized the record with all five claims closed.

The supervisor was reopened between phases, and the first Falsifier's session
was also resumed during integration debugging. Failed commissioning controls
remain in the record alongside their corrected successors. The worker models
were Grok 4.6 and GPT-6 Astra, using Grok CLI 1.0.13 and Codex CLI 0.153.4.

The original binary64 reference subtraction reports an error of
0.01920100107144218. The refined enclosure against mathematical exp(-1) is
[0.019201001071442167, 0.01920100107144217]. Both reject 0.001 and lie below
0.02. The verifier independently checks the refined interval at 80-digit
precision:

```bash
python3 demos/agent_roles_validation/verify_record.py
```

The configured GPU containers denied Bubblewrap namespaces. Their attempted
runs remained non-evidence; successful validation used the local Linux CPU
through SSH instead. Campaign creation now probes this prerequisite first.

`record/` is an explicit audit extract with agent-authored programs, numerical
artifacts, provenance, claims, and the final report. It omits provider logs,
native session cursors, worker authentication material, and runtime resource
caches, and is not a resumable backup. `sha256.json` binds the extract's files.
The original finalizer report is preserved byte-for-byte; its elapsed time
describes finalization, not the full external CLI workflow.
The opt-in reproduction scripts live in the sibling Simote checkout under
`scripts/live-scientific-campaign.ts` and `scripts/export-scientific-validation.py`.
