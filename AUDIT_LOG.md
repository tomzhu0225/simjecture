# rc3 audit and polish log

## Scope and safety
- Requested 2026-10-01: audit code/performance, GUI usability and design, wording, documentation, public API, contributions, and long-running harness behavior.
- Branch: `audit/rc3-polish`; baseline: `2f66b8d06c20b18cfea20188acad60b83fa25ec0` (`0.5.3rc3`). No main merge or history rewriting.
- Changes are committed in small logical steps, with targeted regression tests and app smoke checks after major changes. No publication or remote pushes are assumed.
- This cloud environment exposes 9 logical CPUs, approximately 9.7 GiB RAM, and no GPU. No connected user computer or saved coding environment is available.
- Bubblewrap fails namespace setup; PRoot installs but ptrace is prohibited. We will not weaken host security restrictions. Real isolated long simulations may consequently be skipped with evidence.
- Earlier standalone bundled Gray–Scott reproduction succeeded (four cases, approximately 111 seconds), but does not establish harness or model-driven campaign operation.
- No live model billing, private credentials, or remote-worker authentication will be used without established authorized access.

## Work plan
1. Establish broad test and static-analysis baseline; identify reproducible code/API defects and measurable performance opportunities.
2. Walk first-use GUI workflows, improve shared visual/accessibility patterns and wording, retain existing functionality.
3. Reconcile docs and contributor workflow with verified rc3 source behavior; draft authorship consideration policy for maintainer review.
4. Integrate focused fixes, validate existing tests and smoke flows, summarize remaining limitations and decisions.

## Running record
- 2026-10-01: fetched main and confirmed baseline remains current; created separate audit branch. Existing untracked deployment artifacts are preserved and excluded from commits.

## Final summary
Pending completion. All test results, skips, performance measurements and review decisions will be recorded below.

### 2026-10-01 — Atomic event-ledger append
- Reproduced hash-chain corruption with six concurrent SQLite connections: all writes succeeded but chain verification failed.
- Reserved the SQLite writer with `BEGIN IMMEDIATE` before reading replay identity/chain head; commit/rollback now encloses the full append. Public method signatures are unchanged.
- Added concurrent writer/shared-idempotency and failed-insert rollback regression tests.
- Validation: 99 affected tests passed (ledger, models, parameters, research client, campaign, control, search, proposals, orchestration, web); focused Ruff and CLI help passed. Web tests supply the basic app smoke.
- No full numerical or autonomous-model claim is made by these tests.

### Baseline validation
- Pristine rc3 in a separate detached worktree: **754 passed, 93 failed, 28 skipped**, 193.39 seconds. Baseline Ruff across source/tests passed.
- The unmodified suite is not green in this environment. Many failures require working Bubblewrap or browser binaries; each remaining failure is being compared/classified rather than hidden with blanket skips.

### Indexed campaign replay
- Added a backwards-compatible `(campaign_id, sequence)` SQLite index; reopening an existing ledger installs it without altering events.
- Synthetic in-memory benchmark: 40,000 events across 8 campaigns, median of 5 batches of 500 queries. Campaign-head lookup: **1618.25 → 1.35 µs**; incremental-tail retrieval: **294.29 → 49.84 µs**. Query results were checked equal. These are query timings, not end-to-end simulation speedups; indexing incurs storage/write overhead.
- Validation: 71 affected tests passed; schema export check and Ruff passed. Parent's combined ledger/web/worker/accounting suite: 29 passed; CLI smoke passed.

### Harness polling and usage-log memory
- Single-job status/artifact polling now reconciles only the selected receipt; aggregate status and resource reservations still reconcile the full job set, but avoid a second history read.
- Provider accounting streams JSONL and retains accounting fields rather than complete per-request context metadata. Totals/replay precedence remain unchanged.
- Synthetic 1,000-history-job status benchmark: **19.884 → 0.072 ms** median (276.5×); 20 MB provider-log benchmark: peak Python allocation **40.08 → 0.324 MB** (123.7× reduction), identical totals. This is measured orchestration overhead, not measured model-token savings or solver throughput.
- Validation: 50 focused tests passed, 14 real-runtime tests skipped; Ruff, CLI smoke and parent combined web suite passed. Runtime skips are explicitly not successful simulations.
- Fresh probes confirm Bubblewrap network-namespace and PRoot ptrace operations are prohibited. Long isolated WarpX runs remain skipped; no host security controls were weakened.
