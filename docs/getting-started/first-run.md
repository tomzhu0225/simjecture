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

To start a new study, install and log in to a supported native agent CLI
(Codex GLM, Codex, Grok or AGY), then open the browser:

```bash
uv run simjecture web
```

In **New hypothesis**, choose mode, backend and model separately. **Minimal** is
the default. It keeps the agent's native tools and planning freedom while recording
experiments, counterexample searches, hypothesis repairs and independent reviews.
Structured and frontier modes remain selectable. DSH and direct API routes are
explicit legacy choices and require their separate provider configuration.

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
`research_report.json`. A clean agent exit is only a checkpoint. A supported root
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
