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

The interface has five connected projections:

- **Claim graph:** one view of the durable ledger, with all four claim kinds as
  first-class nodes: `scientific`, `instrument`, `diagnostic`, and `control`.
  Claim records and inspectors retain their relations, including `refines`,
  `alternate`, `instrument_of`, `diagnostic_of`, and `control_for`.
  Scientific-only mode is a visual filter over this graph, not a second
  hypothesis data structure.
  A derived commissioning-stage node exposes the workflow dependency hidden by
  the parent-owned ledger representation. Scientific hierarchy arrows remain
  parent → child; prerequisite arrows point instrument claim → **qualifies** →
  commissioning → **enables evidence for** → scientific target. Diagnostic and
  control prerequisites likewise point into their scientific target. The stage
  and every supporting-claim inspector name that target. This exposes the
  capability evidence gate and guided starting point without becoming a fifth
  durable claim kind or changing the underlying ledger.
- **Claim inspector:** click any of the four node kinds to see its rationale,
  parent and child relations, prospective evidence contracts, linked evidence,
  closure reason, and iteration metadata.
- **Execution monitor:** recent simulations and calculations appear as separate
  runs. Select one run to inspect its state, command binding, elapsed time,
  heartbeat I/O, workspace size, return code, and bounded console excerpt.
- **Research trace:** typed model decisions, the model-authored `research_note`,
  tool outcomes, retries, routes, and input/output/reasoning/cache token counts.
  This is an auditable laboratory trace, not a representation of a provider's
  private hidden chain-of-thought.
- **Artifacts and conclusion:** contained workspace results, generated figures,
  audit records, and the terminal answer when one exists.

The graph uses the bundled Dagre engine to compute both left-to-right and
top-to-bottom layered layouts, then selects the orientation that permits the
largest on-screen text while every visible node still fits. This happens on
first load and whenever the claim set changes. Scroll over the canvas to zoom
around the cursor, drag empty canvas to pan, use **Fit all** to recover the
complete view, or use the plus/minus controls for centered zoom. Each node is
keyboard-selectable and independently draggable. Positions are stored under a
campaign-specific browser key and never written into the durable run; **Reset
layout** removes the local arrangement and recomputes the optimal layout. Node
copy is line-bounded, ellipsized, and clipped to its box. The four kinds use
distinct node treatments while their status is shown separately, so claim type
is never inferred from supported or falsified state. Expanded contract and
evidence sections remain open while the one-second live refresh advances. The
header theme button switches between the high-contrast light and dark palettes
and remembers the choice locally.

Human-facing scientific text is rendered as sanitized Markdown throughout the
campaign heading, claim inspector, contracts, evidence assessments, research
notes, and conclusion. Inline code, fenced code, lists, tables, links, and TeX
delimiters are supported; TeX is converted to MathML. The browser bundles its
pinned parser, sanitizer, and math renderer locally and makes no CDN request.
Raw HTML, images, form controls, embedded objects, and unsafe links are removed
before display. For legacy natural-language hypotheses that predate the
Markdown convention, a conservative display-only adapter recognizes common
ASCII forms such as `0 < theta_0 <= 2.5 rad` and
`T_0 = 2*pi*sqrt(L/g)` and supplies TeX delimiters before rendering. Explicit
Markdown math and inline code are left untouched. The underlying JSON record
remains unchanged.

The built-in `scientific-markdown` skill tells the autonomous agent how to use
this presentation layer without moving estimator definitions, units,
normalizations, thresholds, or validation checks out of machine-readable
evidence artifacts.

The execution monitor deliberately does not invent a percentage for an
unbounded scientific search. A running command uses an indeterminate activity
bar and reports only observed state, heartbeat, time, I/O, and resource values.
When several runs exist, the left-hand list selects the one shared console view;
the page does not create a wall of simultaneous terminals.

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
