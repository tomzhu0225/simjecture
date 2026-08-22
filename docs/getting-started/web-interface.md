# Web interface

The local web interface is the primary human-facing view of a Simjecture
campaign. It makes the scientific structure visible without replacing the
durable record. `mvp_manifest.json`, `transcript.jsonl`,
`hypothesis_ledger.json`, `mvp_report.json`, and artifact provenance remain the
sources of truth.

## Open a recorded campaign

The browser interface is included in the core installation and has no Node.js
build or optional Python dependency:

```bash
uv sync --frozen
uv run simjecture web demos/gray_scott_counterexample/record
```

This starts a local server at `http://127.0.0.1:8765/` and opens the default
browser. Use `--no-open` to print the address without opening it, or `--port 0`
to select an available local port automatically.

The interface has four connected projections:

- **Hypothesis tree:** scientific claims and their `root`, `refines`,
  `alternate`, or `succeeds` relationships. Node color represents the durable
  claim disposition, not an interpretation of model prose.
- **Claim inspector:** rationale, prospective evidence contracts, linked
  evidence, closure reason, and instrument/diagnostic/control claims belonging
  to the selected scientific hypothesis.
- **Live activity:** typed model actions, tool completions, heartbeats, retries,
  token usage, elapsed envelope, and the verified execution state.
- **Artifacts and conclusion:** contained workspace results, generated figures,
  audit records, and the terminal answer when one exists.

The graph can be zoomed and each node is keyboard-selectable. Validation claims
remain outside the scientific hypothesis tree and appear in the selected
hypothesis's inspector, matching the terminal interface.

## Follow or control a campaign

Attach the browser to an existing output directory:

```bash
uv run simjecture web artifacts/my-campaign
```

The server polls only durable, fsynced state. A missing terminal report is not
enough to label a process as running: the green `running` state requires a
supervisor record that still matches the PID, process start time, command line,
and output directory.

Pause, resume, and stop use the same verified control functions as the CLI and
Textual dashboard. Pause is cooperative at the next action boundary. Stop sends
SIGINT and a bounded SIGTERM fallback only to a verified process. Closing the
browser or pressing Ctrl-C in the server terminal does not stop a campaign.

For review or screen sharing, disable every mutation:

```bash
uv run simjecture web demos/gray_scott_counterexample/record --read-only
```

## Launch a hypothesis

Run `simjecture web` without a campaign path and select **New hypothesis**. The
form keeps the immutable root hypothesis separate from optional operational
guidance and records the execution envelope before starting the runner. The
child process inherits provider credentials from the terminal environment; the
browser never asks for, stores, or returns an API key.

```bash
export DEEPSEEK_API_KEY='your-process-local-key'
uv run simjecture web --runs-root artifacts
```

Campaigns launched in the browser use the same structured
`operator_input/launch.json` contract as the TUI and CLI. No shell command is
constructed from hypothesis text.

## Local security boundary

Version 0.1.1 is intentionally local-first rather than a hosted service:

- the server refuses non-loopback bind addresses;
- mutating requests require an unguessable per-process control token and a
  same-origin JSON request;
- no cross-origin access is enabled;
- artifact paths are contained inside the selected run and symbolic links are
  not served;
- a restrictive content-security policy blocks external scripts and frames.

It does not provide remote authentication, multi-user ownership, or a public
deployment boundary. Use the headless commands or TUI over SSH; do not proxy the
v0.1.1 local server onto a network.

## Keep the terminal clients

The browser, Textual dashboard, `status`, and `watch` are clients of the same
durable projection. The TUI remains useful over SSH and on machines without a
browser. See [Terminal interface](terminal-ui.md).
