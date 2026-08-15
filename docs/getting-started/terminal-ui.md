# Terminal interface

The terminal interface is a human-facing projection of durable MVP artifacts.
It does not replace `mvp_manifest.json`, `transcript.jsonl`,
`hypothesis_ledger.json`, `mvp_report.json`, or `artifact_provenance.json`.
Those files remain the source of truth. Model prose is never treated as
scientific status.

The scientific package does not depend on the terminal UI. Headless hosts can
inspect a run without installing Textual.

## Headless status and watch

These commands work after `uv sync --frozen` with no extra:

```bash
uv run simjecture status artifacts/my-campaign
uv run simjecture status artifacts/my-campaign --json
uv run simjecture watch artifacts/my-campaign
uv run simjecture watch artifacts/my-campaign --jsonl
```

`status` prints one snapshot and exits. `watch` follows newly fsynced
transcript records and exits when a terminal report appears or the campaign
pauses at an action boundary. Ctrl-C stops the viewer only; it does not cancel
the scientific campaign.

A missing report is **not** reported as running. The phase is `initialized` for
a manifest-only directory, `incomplete (no terminal report)` when a transcript
exists without `mvp_report.json`, and `paused (action boundary)` after a
cooperative pause. Live process liveness is known only when this interface
launched the runner or can verify a supervisor record.

There is no fabricated “percentage scientifically solved.” The projection shows
elapsed envelope, claim counts, heartbeats, provider token usage from assistant
transcript rows, and completed actions.

## Optional interactive dashboard

```bash
uv sync --extra tui
uv run simjecture tui
uv run simjecture tui artifacts/my-campaign
```

Without a run directory the dashboard lists recent `artifacts/` campaigns and
offers a new-run form. The form keeps the root hypothesis separate from an
optional operational instruction, shows installed capabilities from their
descriptors, and reviews the contract before launch.

The run dashboard presents three related views of the durable ledger:

- **Hypothesis tree:** only scientific claims, with the immutable root followed
  by `refines`, `alternate`, and `succeeds` daughters in parent-child order.
- **Validation claims:** instrument, diagnostic, and control claims belonging
  to the selected hypothesis, including non-scientific successor chains.
- **Complete audit ledger:** every typed claim in durable ledger order, opened
  with `[v]` for provenance review.

Arrow keys select a hypothesis and update its validation pane. `Enter` opens
the selected record with its kind, relation, parent, evidence-contract count,
linked-evidence count, status, and closure reason. The projection retains
orphaned legacy records visibly rather than silently dropping them.

Launch materializes `operator_input/hypothesis.txt` and invokes
`--hypothesis-file`. If an instruction is supplied it is written to
`operator_input/instruction.txt` and passed with `--instruction-file`. The
controller stdout/stderr stream is redirected to `controller.log`. No shell
string is constructed.

If Textual is not installed, `simjecture tui` exits with a short message
telling you to run `uv sync --extra tui`.

## Pause, resume, and cancellation

Pause is cooperative and happens at the **next action boundary**. The current
model turn or capability command is allowed to finish. The runner does not use
SIGSTOP. No terminal report is written, so the same contract can be resumed.

```bash
uv run simjecture pause artifacts/my-campaign
uv run simjecture resume artifacts/my-campaign
uv run simjecture resume artifacts/my-campaign --detach
```

`pause` writes `operator_input/control.json` only when a supervisor record still
matches the live PID, process start time, exact command line, and run output
directory. `resume` rebuilds argv from the structured
`operator_input/launch.json` contract and contained input files. Every MVP
resource, retry, routing, ledger, skill, capability, and guided-commissioning
option is recorded. The cumulative active wall-time budget is preserved across
sessions; pause is not a way to replenish it.

Automatic resume is intentionally limited to self-contained contracts. Guided
commissioning is copied and content-addressed under `operator_input/`. If a
launch uses an external ledger, custom skill directory, custom capability
directory, or executable, `resume` refuses and tells the operator to repeat the
reviewed original command. It never follows a stored path outside the run.

An exclusive `operator_input/runner.lock` prevents two agents from appending to
the same transcript or claim ledger. Resume also refuses when that lock is
owned or when a terminal report exists.

In the dashboard:

- `[v]` opens the complete scientific and validation claim ledger;
- `[p]` requests that action-boundary pause;
- `[r]` resumes a paused or incomplete run from the stored launch record;
- `[c]` still sends SIGINT to a verified process so the runner can write a
  `cancelled` report;
- `[q]` leaves the UI without signalling.

Cancellation waits run outside the Textual event loop, so the dashboard remains
responsive while SIGINT and bounded SIGTERM fallback are pending. Arbitrary
host PIDs are never signalled. Partial workspace files remain non-evidentiary.

Scientific and artifact text is rendered literally: Rich-style bracket markup
inside units, intervals, hypotheses, logs, or model answers is never interpreted
by the dashboard.
