# First autonomous run

Choose a bounded hypothesis whose outcome can be evaluated with ordinary Python
before attaching an expensive simulator.

```bash
export DEEPSEEK_API_KEY='your-process-local-key'

uv run simjecture mvp \
  --hypothesis "For this specified Gray–Scott reaction-diffusion model, increasing feed rate monotonically increases the late-time spatial variance over the declared interval." \
  --output artifacts/gray-scott-first-run
```

The output directory contains the immutable manifest, complete transcript,
claim ledger, artifact provenance, final report, and the agent's workspace.

Important distinctions:

- `workbench` executions may inform design but can never become evidence.
- `evidence` executions must match a prospectively registered program and exact
  command.
- an installed capability must be commissioned before producing scientific
  evidence.
- `unresolved` is a valid result when the observation or instrument is
  insufficient.

Repeating a completed command against the same durable ledger returns the stored
result rather than silently starting another campaign.

Inspect the durable directory without starting another campaign:

```bash
uv run simjecture status artifacts/gray-scott-first-run
uv run simjecture watch artifacts/gray-scott-first-run
```

`status` and `watch` are headless. They do not report a campaign as running
merely because `mvp_report.json` is absent, and they do not invent a scientific
completion percentage. They also show provider token usage from the transcript
when those fields were recorded.

```bash
uv run simjecture pause artifacts/gray-scott-first-run
uv run simjecture resume artifacts/gray-scott-first-run
```

Pause waits for the current action to finish. It does not freeze a simulator
with SIGSTOP.

The optional terminal dashboard is documented in
[Terminal interface](terminal-ui.md). It is a projection of the same artifacts.
