# First autonomous run

To explore the interface before supplying an API key, replay the committed
Gray–Scott record. This is read-only and starts neither a model call nor a
simulation:

```bash
uv sync --frozen
uv run python demos/gray_scott_counterexample/verify_record.py
uv run simjecture web demos/gray_scott_counterexample/record --read-only
```

See [Recorded Gray–Scott demo](../demos/gray-scott.md) for the scientific result
and the boundaries of that record.

For a fresh setup, use the [one-command installer](installation.md), then open the
workspace. Enter a compatible API endpoint/key in **Connections**, or use a native CLI
that you have already installed and authenticated. Choose the agent/model in the composer.

Ask the agent to prepare a bounded study, for example:

> Test whether explicit Euler for y' = -y preserves nonnegativity for every positive
> time step. Search for a counterexample, record the Python calculation, and request
> independent review. A reviewed negative answer completes the study. Budget five minutes.

Review the prepared brief, open **Autonomous research**, and start it. The workspace
uses the existing minimal research core, with recorded experiments and independent
review. A timeout without review is incomplete work, not an accepted negative answer.
The advanced **New hypothesis** form remains at `/monitor` for explicit mode and
execution configuration. See the [workspace walkthrough](research-workspace.md).

For a terminal or automated run, follow [Run a headless study](../how-to/headless-studies.md).
It covers native CLI setup, mode and completion-policy choices, monitoring, and
resuming within the original budget. The optional
[terminal dashboard](terminal-ui.md) remains available for browserless operation.
