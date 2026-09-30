# Changelog

This project follows semantic versioning. Dates use ISO 8601.

## Unreleased — SSH experiment workers

- Add standalone local/SSH headless numerical workers for minimal studies, with
  frozen runtime identities, CPU/RAM/GPU admission and asynchronous execution.
- Preserve job identity across lost replies, SSH interruptions and coordinator
  restarts; enforce worker deadlines and confirm descendant cancellation.
- Add the Machines workspace page, visible study pool selection, placement and
  transport status, bounded read-only source access and verified artifact retrieval.
- Preserve pool selection when preparing continuation phases. Keep research agents
  and independent scientific review central; Simote remains optional.


## 0.5.3rc1 (preview) — 2026-09-30

First repairs from the aluminium stagnation campaign audit. Minimal remains the
default; this preview does not change worker session policy or claim scientific
improvements from a new long campaign.

- Recognize provider `402 Insufficient Balance` errors in native result envelopes.
  Pause with a credit/quota explanation and keep Resume and the original deadline.
- Explain and evaluate alternative instrument requirements as **any of**, in methods
  review, claim review, study status and the browser; FLASH or WarpX never means both.
- Bound long plan notes before evicting current evidence. Preserve references to the
  newest completed experiment, method and claim review even in small recovery briefs.
- Let methods/progress reviewers request recorded JSON excerpts through the host,
  with hash checks, bounded size and at most two retrieval rounds. Requests and failed
  retrievals cannot grant approval; record each review packet and response.
- Record builtin provider requests before agent-step aggregation, including completion
  retries, failures, native cache/reasoning usage when reported, and context sizes/hashes.
  Preserve unknown counters and avoid adding request and legacy step totals together.
- Show live request counts, worker/reviewer token breakdown, missing usage, provider
  retry time and actionable provider errors in terminal/browser views. Monetary cost
  is explicitly unavailable without billing data; no price assumptions are invented.
- Preserve native tool-call/result messages in builtin DeepSeek worker conversations,
  including private reasoning continuity. Nineteen controlled live repair trials
  informed this choice; retain the completion guard, session policy and review gates.
  Record response finish reasons, call counts and text trimming for further audits.
- Ship experimental **Simjecture Bench 0.1.0**, independently versioned CSV and
  recorded-RZ diagnostic coding tasks, portable CLI preparation/grading and Harbor
  task-format export. Verify varied numerical holdouts, saved outputs, input hashes
  and numerical plot data; keep scientific claim approval separate.
- Add a visible Benchmarks workspace entry for preparation with the chosen agent
  and independent grading after delivery. Preparation makes no provider request.
  Timed framework trials use the external runner; interactive chat is exploratory.
- Document the matched MiMo 2.6 Flash/Pro and DeepSeek V4.1 Flash pilot, including
  cache usage, continuation/setup differences and limits of single-trial evidence.

See [audit and next phases](docs/research/stagnation-deep-audit-20260929.md) and
[preview scope](docs/testing/0.5.3rc1-acceptance.md), and
[adapter benchmark](docs/testing/native-api-adapter.md).

## 0.5.2 — 2026-09-29

Stable release of the conversation-first research workspace tested in rc1/rc2,
plus continuation, steering, review recovery and the ITER diagnostics pack.
Minimal mode remains the default; structured/frontier modes remain selectable.
The versioned installer preserves existing research data and older program folders.

- Add an optional ITER diagnostics/data pack with pinned CHERAB/Raysect,
  CHERAB-ITER/IMAS extensions and IMAS tools. Install/check from the CLI or GUI;
  run a visible, monitored numerical demo with plots. Add source-based agent
  guidance and separate setup entries for JOREK, SOLPS-ITER and DINA-PS.

- Offer Prepare directly or Prepare with agent from the continuation dialog.
  Chat preparation carries parent context across turns and lets the agent draft
  the brief and select inherited files without losing lineage or instruments.
- Add Continue investigation and Send guidance to study cards and the experiment
  monitor. Review a linked phase's brief, selected inherited files, model and new
  budget before launch; retain the original study and evidence status.
- Snapshot continuation context with verified hashes and immutable parent lineage.
  Add CLI continuation and advisory steering; show queued/checkpoint delivery in
  the web interface and include guidance in independent review packets.
- Detect empty/truncated built-in review replies, record finish reasons and usage,
  and use bounded recovery with a larger output allocation and a DeepSeek
  non-thinking retry. Back off repeated invalid oversight without granting approval.
- Reconcile expired deadlines/dead supervisors in live status and write final
  reports when a supervisor exits through an external error.

## 0.5.2rc2 (preview) — 2026-09-27

- Provision scientific compilers, MPI, HDF5 and other prerequisites in managed
  environments for the included tools. Preserve diagnostic logs and validate the
  installed runtime using the selected execution backend before reporting success.
- Verify all five one-click tools from empty runtime directories, real agent-assisted
  FLASH and WarpX CUDA builds, GPU execution, and browser uploads of licensed source.
- Handle restricted root installations with a dedicated non-root account, safe
  launchers, failed-install retry and upgrade rollback.
- Make the autonomous research screen follow preparation, proposal, execution and
  results. Return finished reports to the interactive agent without interrupting
  active work; preserve queued delivery across restarts and link explanations to evidence.
- Support follow-up studies in the same conversation with separate briefs and reports.
  Remove duplicate navigation labels and collapse routine workspace metadata.
- Accept source archive uploads up to 64 MiB. Keep installation commands separate
  from simulations, support checks for registered custom tools, and reject runtimes
  whose host paths or interpreter symlinks cannot work in the execution backend.

- Keep installation skills readable while runtimes are incomplete; retry the
  pinned Singularity-EOS source fetch after transient transport failures and
  populate its required ports-of-call dependency. Package a relocatable Python
  runtime when using uv-managed Python, avoiding broken sandbox symlinks. Incomplete runtimes with missing
  declared identity files are not listed as installed.
- Require an explicit completion handoff after DeepSeek text-only progress replies,
  continuing tools instead of marking promises as completed answers. Bound repeated
  protocol failures and retain usage accounting for completion-check requests.
- Move routine workspace controls and execution status into the left sidebar,
  remove the redundant top bar, and make execution warnings dismissible with
  expandable diagnostics. Keep conversation-blocking notices prominent.
- Use draggable sidebar edges and compact chevron tabs instead of text hide/show
  buttons. Drag to the outer edge to collapse, pull or click the tab to reopen,
  and retain panel widths and collapsed state across reloads.
- Replace source-path dialogs for FLASH and WarpX CUDA with **Install with agent**,
  opening prepared setup conversations that reference the bundled deployment skills.
- Prefer Bubblewrap, with a checked PRoot cooperative fallback for namespace-restricted
  hosts running under a dedicated non-root account. Show a dismissible sidebar warning
  about the lack of filesystem/network security isolation; retain explicit backend
  choices and immutable study execution modes. Use the selected backend for tool checks.
- Show failed tool installations directly on catalogue cards, including tools
  that are not yet installed. Bootstrap checksummed Micromamba for WarpX CPU
  and separate solver provisioning from experiment-sandbox readiness.
- Support DeepSeek thinking-mode tool choice and plain-text final answers. Keep
  required provider reasoning metadata in private session storage and preserve
  it when resuming a conversation, without displaying it in chat or activity.
- Clarify SSH forwarding when a local port is already occupied.
- Show only simulations in the left sidebar. Separate Simulations and Commands
  into right-side tabs with independent selections, counts and links; incoming
  commands no longer open the simulation monitor.

## 0.5.2rc1 (preview) — 2026-09-27

- Add a Linux/WSL one-command installer with checksummed release bundles, automatic
  Python/uv setup, a persistent launcher, SSH forwarding guidance and separate version/data folders.
- Add the conversation-first research workspace with optional compatible API setup,
  auto-detected native CLIs, per-conversation agent/model controls and agent-prepared studies.
- Keep named simulation folders and live logs beside conversations; link interactive
  runs, figures, files and autonomous studies with a resizable side monitor.
- Render equations, highlighted code and saved figures; add larger typography, persistent
  light/dark themes and confirmed conversation/folder deletion with active-run guards.
- Preserve scroll position and expanded details during live refreshes.
- Discover existing FLASH applications and WarpX CPU/GPU builds, including native-input
  versus Python-binding availability; expose shipped research skills to browser workers.
- Resume native chat sessions and retain structured API history per conversation/model/
  connection. Never reuse worker sessions for independent review.
- Remove the default interactive-turn time ceiling, show public progress and recent tools,
  and retain user-selected autonomous/simulation deadlines. Clarify interruptions and
  preserve job statuses; discourage untracked temporary simulation
  runs, and include an HDF5 reader in the workspace environment.
- Accept an independently reviewed negative answer as completion when the study's
  selected policy is `answer`; retain the existing `repair` policy.

## 0.5.1 — 2026-09-26

- Update bundled FLASH and Python experiment skills with guided-study/HDF5 lessons,
  mode-correct interfaces, pilot interpretation and acceptance-rule checks.

- Preserve classic instrument access across assignment rollover; retain role and branch scope.
- Require explicit methods-review prerequisites and reject conditional approval; distinguish
  timing/parity pilots from scientific evidence.
- Surface output eligibility annotations to review without forcing metadata-only solver reruns.
- Check explicit numerical repair bounds for empty intersections before execution.
- Cancel through the complete durable job store, report unknown outcomes, and continue cleanup
  when one job fails cancellation.
- Document the guided MiMo v2.6 Pro / DeepSeek V4.1 Flash comparison, including tool-protocol,
  duration and usage limitations; refresh the README around current modes and trust boundaries.
- Restore guided anchors in all native study modes, with a separate model-free readiness run
  and instrument-scoped review that cannot authorize hypothesis evidence.
- Add explicit non-root PRoot cooperative execution for hosts without Linux namespaces;
  keep Bubblewrap the default and never silently weaken isolation.
- Retry transient provider failures with interruptible backoff until the original deadline;
  pause authentication, permission and exhausted-quota failures for operator attention.

- Make experiment journaling and bounded context delivery automatic in minimal mode,
  following AIDE's controller-managed pattern. Add budget-limited checkpoint synthesis
  with receipt-bound citations and no authority over scientific acceptance.

- Add optional evidence-linked research notes, preserved corrections, discriminating
  test plans and experiment lineage, informed by autoresearch/AIDE source inspection.
- Resume from a bounded research brief and generate a machine-readable attempt ledger;
  compare hash-verified result metrics without replacing missing values with zeros.

- Add source-bound methods review for new instrument-backed minimal studies,
  optional immutable instrument requirements, and append-only registration of new builds.
- Recover native sessions that repeat intentions without work; add independent progress
  review, bounded host checkpoints and immediate handoff of durable review requests.
- Separate exploration from evidence and compact review documents from hashed binary
  outputs; detect changed inputs, dead workers and questionable result fields.
- Generate a live host evidence ledger with missing-case coverage, budget warnings,
  review status and incomplete token-accounting indicators.
- Support operator-authorized read-only solver-source inspection and useful build
  diagnostics. Record the reconnection-run audit and live MiMo validation results.

## 0.5.0 — 2026-09-21

- Default new native-agent studies to minimal, with structured and frontier
  selectable in the CLI, browser and TUI. Mode and backend are separate choices;
  DSH/API remain explicitly labelled legacy routes. Existing records retain their mode.
- Preserve active counterexample search, minimal-change repair rationale,
  branching hypothesis ancestry and fresh prospective validation in the smaller service.
- Add live terminal activity, job/review counts and remaining budget; project
  minimal evidence and hypothesis trees into the browser and terminal interface.
- Preserve deadlines across pause/resume, surface provider failures as resumable
  states, and verify numerical-worker identity before cancellation.
- Make the launch package usable with native agent logins without installing DSH;
  retain an optional `setup.sh --with-dsh` path.
- Retain measured limitations: simple-task follow-ups completed faster but used
  more tokens; the previous hard FLASH trial did not establish superiority to a plain agent.

## 0.4.0 — 2026-09-20

- Updated the bundled DSH integration to the tested `0.1.5-rc.2` runtime,
  including current session, tool-call, prompt and structured-output APIs.
  The Python release and DSH bundle now share version `0.4.0`.
- Enabled native web search, page retrieval, shell, filesystem, skills,
  workflows and configured plugins for research agents. Scientific calls retain
  role restrictions; independent judges retain their frozen-case isolation.
- Separated the native research workspace from authoritative campaign files.
  Upgrades start a fresh `.research-v1` conversation, reconcile existing kernel
  state, and preserve older conversations. Built-in DSH file/shell policies
  protect records; arbitrary installed plugins remain trusted process code.
- Added `read_workspace_image` for bounded PNG, JPEG and WebP image inspection
  through MCP, with dimensions and content hashes. Inspection is not evidence
  acceptance and requires a vision-capable model.
- Extended the Simote scientific tool catalog for image reads. Matching Simote
  changes add AGY workers and judges; Simote remains a separate optional app.
- Added real-runtime DSH tests for role isolation, context pruning, V2/V3 log
  migration, durable-job recovery and complete CLI/MCP pause/resume behavior.
- Verified native search, fetch, file writing and image inspection with real
  DeepSeek API calls on non-simulation research tasks.
- Added a Linux launch bundle containing the wheel, source distribution,
  matching DSH profile, setup/launch scripts and SHA-256 checksums.

## 0.3.2 — 2026-09-09

- Added `simjecture-call`, a one-shot JSON transport for trusted supervisors,
  including Simote's SSH bridge, with sandbox readiness probing and durable
  campaign recovery.
- Added persistent, claim-scoped scientific role assignments with tool filters,
  operation budgets, idempotent retries, session tracking, and validated handoffs.
  Independent adjudication continues to use the existing evidence and claim gates.
- Documented the optional Simote campaign workspace and Codex/Grok role workflow.
- Included a hashed audit extract and offline verifier for a live Codex/Grok
  integration campaign. This validates the transport and scientific role workflow
  on a finite Euler error-bound claim; it is not a new scientific discovery.
- Bundled built-in capability descriptors in wheels and discover them alongside
  packaged skills, so installed deployments can use the same resource catalog.
- Clarified the distinction between authored Python source and upstream
  observation data when declaring experiment inputs.

## 0.3.1 — 2026-08-30

- Added equation-of-state capabilities for atoMEC, Singularity-EOS, and M-ANEOS, with a shared `eos` skill that records each code's model limits.
- Added an Optab opacity-table capability and `opacity` skill. Optab is documented as an abundance-consuming table generator, not an EOS solver.
- Added `simjecture install` bootstraps for the EOS and opacity profiles, matching the WarpX CPU provisioning path.
- FLASH install accepts an operator-owned `--repository` Git remote. Simjecture never ships a FLASH URL; a Git-ignored overlay can store local setup defaults.

## 0.3.0 — 2026-08-27

- Added FLASH 4.8 2D compressible resistive-MHD application capability, commissioning protocol, and rank/timing calibrations.
- Added sealed directory inputs in execution sandbox with recursive deterministic manifest hashing and read-only container mounting.
- Clarified child claim evidence lineage and stale scientific execution binding protections.
- Added a FLASH 2D Resistive-MHD island-coalescence demonstration with figures
  generated from the guided HDF5 anchor, a real Web UI capture, and an
  explicitly labelled campaign audit. The root interval is falsified; the
  repair branch remains open because its evidence lineage did not close.
- Added the `flash-demo` optional dependency for HDF5-backed figure
  regeneration.
- Enhanced Web UI test suite with proxy isolation.

## 0.2.2 — 2026-08-24

- Fixed a process-lifecycle race where the supervisor that launched a short
  durable job could observe the child after exit but before `Popen.poll()`
  receipted it, incorrectly recording `outcome_unknown` instead of the known
  terminal result.
- Made the release workflow install the sandbox runtime and locked test
  environment, then run lint and the full deterministic test suite before any
  distribution can be uploaded to PyPI.

## 0.2.1 — 2026-08-23

- Extracted a model-independent campaign kernel while preserving the existing
  hypothesis graph, evidence contracts, commissioning, sandbox, capability,
  provenance, and claim-closure rules.
- Added a strict DeepSeek Harness profile backed by 21 native MCP scientific
  tools, with generic execution and delegation surfaces disabled.
- Split the DSH reasoning loop into a persistent, compact Lead Scientist and
  fresh claim-scoped Falsifier/Experimenter, Repair Scientist, and tool-free
  Judge sessions. Role-specific tool filters, mutation guards, structured
  handoffs, and kernel rechecks prevent a child from silently exceeding its
  scientific assignment.
- Moved durable job waiting beneath the model-facing tool call. Simulations are
  submitted once, read-only status checks no longer consume model turns, and
  cancellation leaves the job recoverable rather than resubmitting it.
- Added one-step-delayed, model-free context elision for completed large tool
  exchanges and oversized results. Deterministic receipts shrink the active
  model surface while the full append-only DSH log and campaign artifacts remain
  intact; semantic compaction stays at 50% for the tested DeepSeek route.
- Added an ordinary-Python experiment skill that separates `run_python` from
  named capability execution, records exact JSON validation checks, and avoids
  capability-only commissioning fields in NumPy/SciPy contracts.
- Clarified that `observation_sufficient` records contract compliance rather
  than self-certified scientific support. Falsifier handoffs and Judge
  preparation now require closure-eligible evidence before adjudication, which
  prevents a sufficient verdict from being persisted against an unclosable
  claim.
- Added idempotent detached simulation jobs, verified cancellation, bounded
  status reports, single-writer enforcement, and authenticated worker receipts
  that recover known outcomes after an MCP restart without rerunning work.
- Added a lifetime root-campaign lease, restart-discoverable jobs and budgets,
  cumulative active-time accounting, and durable cancellation after supervisor
  restart. Custom skill and capability discovery roots replay in workers.
- Validated the official DSH MCP client against the Python bridge and the
  release-pinned CUDA WarpX/openPMD capability.
- Shipped the pinned DSH profile inside the Python wheel and added
  `simjecture dsh-profile` so installed deployments can pack the exact bundle.

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
