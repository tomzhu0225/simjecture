# Changelog

This project follows semantic versioning. Dates use ISO 8601.

## 0.1.0 — research preview

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

This release is an auditable research prototype of the evidence harness and
recorded campaigns. It does not claim unrestricted scientific problem solving.
Independently confirmed new results, and use of the same tooling in further
simulation-gated fields, are the next step.
