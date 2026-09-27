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

For a terminal run, write a bounded statement in `hypothesis.txt` and its test
scope, resource constraints and acceptance criteria in `instructions.md`:

```bash
uv run simjecture study --campaign artifacts/first-study \
  --hypothesis-file hypothesis.txt --instructions-file instructions.md \
  --backend codex-glm --model glm-5.3 --wall-seconds 3600
```

The terminal shows current activity, elapsed/remaining time and experiment/review
counts. Use `--quiet` to suppress progress. Select `--mode structured` or
`--mode frontier` when starting a new directory. Existing mode, backend and wall
deadline are retained on resume.

Minimal records include `research.json`, immutable experiment snapshots,
prospective repair commitments, independent review receipts and a final
`research_report.json`. A clean agent exit is only a checkpoint. Under the default CLI `repair` completion policy, a supported root
or an accepted falsification followed by a supported repair completes the study;
uncertainty stays unresolved. Numerical convergence and physical validity remain
scientific obligations. See [minimal research](../how-to/research-service.md).

Inspect or control the same directory:

```bash
uv run simjecture status artifacts/first-study
uv run simjecture watch artifacts/first-study
uv run simjecture web artifacts/first-study
uv run simjecture pause artifacts/first-study
uv run simjecture resume artifacts/first-study
```

Pause stops the native agent at the supervisor boundary. Already recorded jobs
may finish within their existing limits; the wall deadline continues. Cancel or
deadline exhaustion terminates active recorded jobs. A provider outage pauses
with the evidence intact rather than inventing a scientific conclusion.

The optional [Terminal interface](terminal-ui.md) offers the same mode/backend
selection and a dashboard for SSH and headless machines. The legacy `simjecture
mvp` and [DSH](../how-to/deepseek-harness.md) entry points remain available; their
workbench/commissioning contracts are unchanged.
