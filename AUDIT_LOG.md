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

### Public MCP input validation
- Enforce nested required artifact fields (`path` and `sha256`) and reject nonfinite numeric inputs before kernel dispatch. Valid tool schemas and inputs remain compatible; callers relying on malformed inputs will now receive validation errors.
- Added regressions for missing nested fields, NaN/infinity and valid fractional/integer timeouts.
- Parent verification: 67 API/client/one-shot/web tests passed, one optional MCP SDK test skipped; generated schemas unchanged and checked; Ruff passed.

### Research client transport errors
- Convert malformed/empty transport JSON, non-object responses and missing successful results into useful `RuntimeError` diagnostics. Successful response recording and replay behavior are preserved.
- Added deterministic subprocess-response tests, including successful response persistence. This standardizes invalid-response exception behavior rather than changing valid API signatures.
- Validation included the 67-test API/web smoke above and focused client tests.

### Canonical idempotency payloads
- Compare the already-canonical JSON representation for replay identity. Python equality previously conflated `true` with `1` and rejected equivalent tuple/list JSON arrays.
- Added scalar-representation and equivalent-container tests; clarified the ledger's real single-thread-per-connection contract.
- Validation: 75 affected tests reported by the worker, plus 21 parent ledger/web tests, Ruff and CLI smoke passed. Changed behavior applies to ambiguous or mismatched replay payloads.

### Contribution and security guidance
- Expanded reproducible bug reports, setup, existing code-style rules, regression/PR expectations, provenance and license guidance.
- Added **DRAFT ONLY** paper-authorship consideration text. No threshold, guarantee or final criteria adopted; Bowen must decide the process and paper-specific requirements.
- Corrected security descriptions: native agents are trusted host processes; numerical isolation does not cover them; cooperative PRoot is not an OS security boundary; local UI is not a public multi-user service.
- Validation: strict Sphinx warning-as-error build and local link checks passed; CLI/schema and no-key artifact replay checks passed. Authorship/security wording still warrants maintainer review.

### rc3 documentation reconciliation
- Corrected rc2/rc3 installation wording, actual built-in/native backend selection, minimal versus classic deadlines/policies, DSH bundle filenames/tools, SSH worker selection and benchmark-versus-simulation distinctions.
- Audited 47 public Markdown pages structurally using strict Sphinx/link checks. Current guides received source/CLI spot-check review; historical experiment records received scope/version/link checks, not fresh scientific revalidation.
- Verified schemas and recorded Gray–Scott/GEM/agent-role artifact verifiers; prepared a no-key coding-benchmark task and exported the leaderboard. Those checks do not run fresh FLASH/WarpX or call models.
- Preserved historical measured claims and identified uncertain remaining tasks for maintainer review rather than rewriting old evidence.

### Efficient worker input replay
- Respect the worker's verified complete/size staging acknowledgement, stopping retransmission of already-complete frozen inputs; validate partial offsets and final acknowledgement and reject size changes.
- A completed 3 MiB + 7 byte replay now takes **1 staging RPC instead of 4**. Worker-side whole-file hash verification is retained; this is a transfer-protocol test, not a remote SSH run.
- Added partial/completed replay, empty/exact-boundary input and malformed acknowledgement tests. Parent recovery/web smoke: 26 passed; broader owned harness checks: 60 passed, 14 runtime skips.

### Waiting and benchmark reproducibility
- Added a synthetic supervisor scheduling test: five pending-job waits cause zero provider turns; a terminal receipt produces one wake. This checks scheduling policy without real model/token billing or numerical execution.
- Added bounded reproducible ledger and harness microbenchmark scripts in `scripts/benchmarks/`. Fixtures/measurement scope are explicit; runtime variation means repeated timing ratios differ.
- Validation: synthetic wait test and combined web/recovery smoke passed; scripts passed Ruff and benchmark smoke runs. No actual model-token savings claimed.
