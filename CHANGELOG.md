# Changelog

This project follows semantic versioning. Dates use ISO 8601.

## Unreleased

- Extracted a model-independent campaign kernel while preserving the existing
  hypothesis graph, evidence contracts, commissioning, sandbox, capability,
  provenance, and claim-closure rules.
- Added a strict DeepSeek Harness profile backed by 18 native MCP scientific
  tools, with generic execution and delegation surfaces disabled.
- Added idempotent detached simulation jobs, verified cancellation, bounded
  status reports, single-writer enforcement, and authenticated worker receipts
  that recover known outcomes after an MCP restart without rerunning work.
- Added a lifetime root-campaign lease, restart-discoverable jobs and budgets,
  cumulative active-time accounting, and durable cancellation after supervisor
  restart. Custom skill and capability discovery roots replay in workers.
- Validated the official DSH MCP client against the Python bridge and the
  release-pinned CUDA WarpX/openPMD capability.

## 0.1.1 — 2026-08-22

- Added a dependency-free, localhost-only browser interface with an interactive
  scientific hypothesis graph, claim/evidence inspector, live activity,
  simulation artifacts, terminal conclusions, and token/resource summaries.
- Added `simjecture web`, recent-campaign discovery, browser-based campaign
  launch, and verified pause/resume/stop controls. A per-session control token,
  same-origin checks, loopback-only binding, and contained artifact delivery
  keep the local control surface narrow.
- Extracted hypothesis and validation-claim projections into a shared,
  UI-neutral module so the web interface and Textual dashboard preserve the
  same scientific semantics.
- Kept the durable campaign files authoritative: the browser is a live
  projection and never treats model prose as claim status or fabricates a
  scientific completion percentage.
- Added the enforced Falsifier → Scientist → Judge loop: prospective evidence
  falsifies the active claim, a typed `repairs` successor must accommodate the
  decisive counterexample, and an independent adjudication must accept bounded
  support before completion.
- Kept auxiliary formulas and estimator checks out of the scientific hypothesis
  tree by default, and strengthened continuous-domain adjudication so finite
  grids alone cannot establish universal or strict-monotonicity claims.
- Made direct `simjecture mvp` processes appear live in the browser through the
  durable runner lock, not only through Web/TUI supervisor records.
- Reduced plain-Python prompt overhead while preserving the full commissioning
  protocol for installed capabilities, compacted old authored actions without
  changing the durable transcript, enabled official DeepSeek JSON responses,
  and exposed provider-coverage diagnostics for literature searches.
- Made the Web interface the primary interactive client. The optional Textual
  dashboard remains supported in maintenance mode for SSH and browserless use.

## 0.1.0 — 2026-08-15

- Added a read-only MVP run monitor and headless `status` / `watch` commands.
  A missing report is incomplete, not running. `watch` Ctrl-C stops the viewer
  only.
- Added an optional Textual dashboard (`uv sync --extra tui`) that attaches to
  a run directory, launches through `--hypothesis-file`, and can cancel a
  verified child process. Audit artifacts remain authoritative; no fabricated
  scientific completion percentage is shown.
- Added action-boundary pause/resume through `operator_input/control.json`,
  headless `pause`/`resume`, and verified detach/reattach via supervisor
  records. Pause does not use SIGSTOP and does not write a terminal report.
- Made resume replay every structured MVP option, enforce one runner per output
  directory, and preserve the cumulative wall-time envelope across sessions.
  Automatic replay refuses external writable/configuration paths rather than
  trusting paths supplied by an imported run artifact.
- Bound attached-run controls to PID, process start time, exact command line,
  and output directory. Stored hypothesis, instruction, and guided inputs are
  contained and content-addressed; conflicting launches cannot overwrite them.
- Rendered hypotheses, claims, logs, and artifacts as literal terminal text,
  moved cancellation waits off the UI thread, and corrected long-watch,
  historical-heartbeat, and terminal-finish projections.
- Split the dashboard's flat claim list into a scientific hypothesis tree and
  validation claims linked to the selected hypothesis. A complete audit-ledger
  view remains available for every scientific, instrument, diagnostic, and
  control claim.
- Projected provider token usage from durable assistant transcript records.
- Added the domain-neutral natural-language hypothesis sandbox.
- Added prospective evidence contracts, claim-level provenance, commissioned
  capability execution, and guarded claim closure.
- Added durable model and simulator actions with restart and replay semantics.
- Added an optional release-pinned WarpX CPU/CUDA capability and diagnostic
  skill system.
- Added analytic, electrostatic PIC, nonlinear Landau, reaction-diffusion, and
  two-dimensional collisionless GEM evaluation records.
- Added curated Sphinx/MyST documentation, citation metadata, release licensing,
  contribution guidance, and private-first publication infrastructure.
- Made JSON evidence validation treat equal finite integer and floating-point
  values consistently while preserving Boolean type separation.
- Bounded capability runtime-integrity scans to standard package metadata roots,
  avoiding repeated whole-runtime filesystem walks.
- Made sandboxed Python commands use the harness's locked interpreter and
  read-only scientific package set, including NumPy, SciPy, Matplotlib, and
  pandas, without exposing the host home or user site.
- Added idempotent `install` profiles and a read-only, JSON-capable `doctor` for
  the core scientific stack and release-pinned WarpX CPU/CUDA capabilities.
- Added self-contained, integrity-checked Gray–Scott and collisionless GEM
  records that can be inspected without an API key or simulator runtime.

This release is an auditable research prototype of the evidence harness and
recorded campaigns. It does not claim unrestricted scientific problem solving.
Independently confirmed new results, and use of the same tooling in further
simulation-gated fields, are the next step.
