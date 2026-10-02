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

## Final summary — 2026-10-01

Completed the feasible audit and polish pass on `audit/rc3-polish`, based on rc3 commit `2f66b8d`. Source changes were committed in logical steps without merging main, rewriting history, or pushing remotely. This is a review branch, not a release or production-readiness certification.

### Requested work and outcome
1. **Code/performance:** fixed ledger concurrency and replay identity, extreme-range numerical interpolation, worker polling/staging, resource accounting and failure recovery. Kept refactoring focused; no speculative large-scale rewrite or indiscriminate dead-code removal.
2. **GUI usability:** fixed wrong-conversation submission/stale-navigation races, draft preservation, retries and disabled-state behavior. Executable JavaScript and local HTTP tests pass; rendered workflow review is blocked.
3. **Wording:** clarified first-use help, connection errors, SSH expectations, actual backend choices and completion policies.
4. **GUI consistency:** added shared theme/interface primitives, accessibility semantics, focus treatment, reduced-motion behavior and narrow-layout rules. Final visual review remains necessary on a supported browser.
5. **Documentation:** reconciled current guides with source/CLI, built 47 public Markdown pages, checked 5,765 local links/assets and parsed 11 Python examples. Historical scientific records were preserved and scope-qualified rather than silently rewritten or claimed freshly reproduced.
6. **API:** improved nested required/finite-number validation, deadline/timeout validation before persistence, clear client errors and uncertain transport recovery. Valid signatures/schemas remain compatible; invalid inputs and malformed responses now fail more explicitly. Broad API redesign was deferred.
7. **Contributions:** improved setup/style/PR guidance and added **DRAFT ONLY** paper-authorship consideration wording, with criteria explicitly reserved for Bowen.
8. **Harness/long simulations:** added regression and synthetic recovery/idle-wait/resource tests. Long isolated WarpX, live provider and remote-worker runs remain untested because prerequisites/authorized access are unavailable. No isolation bypass was used.

### Final verification
- **Python suite:** 862 passed, 93 failed, 26 skipped (194.49 s). Pristine baseline: 754 passed, 93 failed, 28 skipped. Test-ID comparison found **zero new failing tests**; all 93 baseline failure IDs remain. Added 106 tests, all passing; two previously skipped checks passed after optional dependencies became available.
- The suite is **not fully green** here. Browser/runtime failures and downstream missing-evidence cascades remain; representative cascades were reproduced and traced to sandbox denial. Rerun the remaining failures on a supported host rather than interpreting this comparison as a full integration pass.
- **DSH JavaScript suite:** 14 passed, no skips. Optional MCP SDK handshake tests passed. All tracked Python Ruff checks passed; non-vendor frontend JavaScript syntax checks and `git diff --check` passed.
- **App smoke:** CLI help, workspace/monitor HTTP responses, new static assets and CSP checks passed after changes. Strict Sphinx build and generated-schema consistency passed.
- **Fresh numerical checks:** built-in kinetic-sufficiency and electrostatic-PIC benchmark commands both passed their expected falsification checks. PIC energy drift: Maxwellian 6.060e-7; two-stream 2.145e-6. These are bounded in-process benchmarks, not WarpX or a live agent campaign.
- **Packaging:** built the credential-free source archive and checked new CSS inclusion. Fresh-home installer got through download/checksums but was blocked fetching managed Python by TLS `UnknownIssuer`. Certificate verification was not disabled; a complete clean-install smoke remains unverified.

### Measured performance (synthetic, reproducible)
- 40,000-row / 8-campaign SQLite query fixture: head lookup **1618.25 → 1.35 µs**; incremental replay **294.29 → 49.84 µs**. Index creation/write/storage cost is not included.
- 1,000 historical-job targeted status poll: **19.884 → 0.072 ms** median. Admission/aggregate status intentionally still reconcile history for correctness.
- 20 MB provider JSONL fixture: peak Python allocation **40.08 → 0.324 MB**, identical accounting totals; no measured model-token saving claimed.
- Completed 3 MiB + 7 byte input replay: **4 → 1 staging RPCs**, with worker hash verification retained.
- Reproduce via `scripts/benchmarks/benchmark_ledger_index.py` and `scripts/benchmarks/harness_polling.py`; timing varies with host load. These are not solver-speedup claims.

### Skipped or limited checks and reasons
- Full Bubblewrap execution: prohibited network-namespace operation (`NETLINK_ROUTE`). PRoot: prohibited `ptrace`. Neither restriction was weakened.
- Long WarpX/GPU/SSH campaigns: runtime/isolation prerequisites and verified remote/model access unavailable. No credentials or paid provider calls used.
- Rendered desktop/mobile GUI and screenshots: Chromium socket creation fails; the separate browser rejects the local URL. DOM-state and HTTP tests do not substitute for visual inspection.
- Clean installer end-to-end: managed Python download failed certificate verification; source packaging itself passed.
- Historical scientific/benchmark claims: artifact integrity and documentation consistency checks only, except the explicitly listed fresh numerical benchmarks. External links and every historical numerical claim were not independently revalidated.
- Repository-wide semantic perfection, security certification and live multi-provider behavior are outside what these bounded checks establish. Detailed per-change outcomes follow.

### Decisions for Bowen
1. Review GUI appearance, keyboard/mobile behavior and the remaining baseline failures on a Linux host supporting the required execution/browser features before merging.
2. Decide paper-authorship criteria and discussion/credit process; the draft creates no entitlement or adopted policy.
3. Decide how CPU reservations should relate to explicit capability thread counts/MPI ranks. This pass fixes per-process CPU-time budgeting but does not silently override pinned OpenMP/BLAS settings, enforce affinity, or impose aggregate MPI quotas.
4. Review invalid-input/error-contract tightening for downstream clients; decide whether broader API versioning/typing work is desirable. No broad public API redesign was imposed.
5. Review the historical FLASH interpretation notice and deployment trust boundary for native agents; no historical evidence or agent privilege model was silently rewritten.
6. Decide when to push/open a PR and which supported host should run long acceptance tests. This branch remains local and unmerged; a review bundle/patch is supplied separately.

## Detailed change record


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
- Validation: 71 affected tests passed; schema export check and Ruff passed. Combined ledger/web/worker/accounting suite: 29 passed; CLI smoke passed.

### Harness polling and usage-log memory
- Single-job status/artifact polling now reconciles only the selected receipt; aggregate status and resource reservations still reconcile the full job set, but avoid a second history read.
- Provider accounting streams JSONL and retains accounting fields rather than complete per-request context metadata. Totals/replay precedence remain unchanged.
- Synthetic 1,000-history-job status benchmark: **19.884 → 0.072 ms** median (276.5×); 20 MB provider-log benchmark: peak Python allocation **40.08 → 0.324 MB** (123.7× reduction), identical totals. This is measured orchestration overhead, not measured model-token savings or solver throughput.
- Validation: 50 focused tests passed, 14 real-runtime tests skipped; Ruff, CLI smoke and combined web suite passed. Runtime skips are explicitly not successful simulations.
- Fresh probes confirm Bubblewrap network-namespace and PRoot ptrace operations are prohibited. Long isolated WarpX runs remain skipped; no host security controls were weakened.

### Public MCP input validation
- Enforce nested required artifact fields (`path` and `sha256`) and reject nonfinite numeric inputs before kernel dispatch. Valid tool schemas and inputs remain compatible; callers relying on malformed inputs will now receive validation errors.
- Added regressions for missing nested fields, NaN/infinity and valid fractional/integer timeouts.
- Integration verification: 67 API/client/one-shot/web tests passed, one optional MCP SDK test skipped; generated schemas unchanged and checked; Ruff passed.

### Research client transport errors
- Convert malformed/empty transport JSON, non-object responses and missing successful results into useful `RuntimeError` diagnostics. Successful response recording and replay behavior are preserved.
- Added deterministic subprocess-response tests, including successful response persistence. This standardizes invalid-response exception behavior rather than changing valid API signatures.
- Validation included the 67-test API/web smoke above and focused client tests.

### Canonical idempotency payloads
- Compare the already-canonical JSON representation for replay identity. Python equality previously conflated `true` with `1` and rejected equivalent tuple/list JSON arrays.
- Added scalar-representation and equivalent-container tests; clarified the ledger's real single-thread-per-connection contract.
- Validation: 75 affected tests in focused validation, plus 21 integration ledger/web tests, Ruff and CLI smoke passed. Changed behavior applies to ambiguous or mismatched replay payloads.

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
- Added partial/completed replay, empty/exact-boundary input and malformed acknowledgement tests. Recovery/web smoke: 26 passed; broader focused harness checks: 60 passed, 14 runtime skips.

### Waiting and benchmark reproducibility
- Added a synthetic supervisor scheduling test: five pending-job waits cause zero provider turns; a terminal receipt produces one wake. This checks scheduling policy without real model/token billing or numerical execution.
- Added bounded reproducible ledger and harness microbenchmark scripts in `scripts/benchmarks/`. Fixtures/measurement scope are explicit; runtime variation means repeated timing ratios differ.
- Validation: synthetic wait test and combined web/recovery smoke passed; scripts passed Ruff and benchmark smoke runs. No actual model-token savings claimed.

### Reject invalid service durations before persistence
- Reject NaN/infinity, nonpositive values, booleans, strings and unrepresentably large durations before study/experiment state is partially written; failed validation can be retried with valid inputs.
- Existing valid deadline/timeout signatures are preserved. Added 16 boundary/retry regressions; 87 service-family/web tests passed, plus 27 integration boundary/web tests; Ruff/CLI smoke passed.

### Correct historical summaries and remaining installation drift
- Qualified FLASH demo summaries: the historical root interval overlaps the allowed band, so the historical ledger label does not independently establish falsification. Original audit JSON, result data and figures are preserved.
- Clarified legacy launch archive versus workspace installer, legacy monitor DSH default versus conversation backends, and CLI repair versus workspace answer completion policies.
- Added guidance for reporting blocked/failed/running long checks honestly. Strict docs build passed; 5,765 generated local link/asset references checked without missing targets; 11 Python fenced examples parsed (not executed).
- Historical scientific measurements, external links, paid models and GPU/SSH solver execution are not newly validated.

### Numerical parameter interpolation
- Fixed finite extreme log/linear ranges whose intermediate ratio/span overflowed (e.g. log midpoint of [1e-300,1e300] incorrectly mapped to upper bound rather than 1).
- Retained ordinary seeded-design formulas exactly; only overflowing intermediate cases use weighted interpolation. Added six extreme-range regressions.
- Validation: 58 parameters/models/search/campaign/domain/web tests passed; parameter/GUI/web integration: 46 passed; Ruff and CLI smoke passed.

### GUI workflows, wording and shared interface primitives
Problems found and fixed:
- A conversation change while submitting could send a message to the wrong conversation, clear a newer draft or apply stale project data. Capture destination/draft and reject stale navigation results.
- Generic action cleanup re-enabled Send despite the backend rejecting messages during an active agent run. Preserve that disabled state; repeated benchmark submits are guarded.
- Failed API connection saves left misleading pending text; now report failure and allow retry. SSH password input clears when its dialog closes.
- Workspace and monitor had divergent theme behavior; share preference bootstrap and common typography, palette/focus/spacing/radius primitives. Added reduced-motion treatment, constrained dialogs and narrow benchmark layout.
- Added keyboard skip navigation without corrupting hash routes, named dialogs, current-navigation/mode accessibility semantics and concrete first-use/SSH instructions.
Validation: 72 GUI/workspace tests passed, one pre-existing namespace-dependent skip; integration 46 passed. All non-vendor JavaScript syntax checks, Ruff and local HTTP/CSP asset smoke checks passed.
**Limit:** actual rendered desktop/mobile/browser QA and screenshots remain blocked. Shell Chromium cannot create required sockets, and the separate cloud browser rejects the local URL. No rendering or visual-polish certification is claimed; Bowen should review the appearance on a supported browser.

### Allocated CPU-time budget and uncertain worker replies
- Account for explicitly allocated CPUs in per-process `RLIMIT_CPU` seconds so threaded jobs do not lose most of their wall-clock allowance. None/one-CPU behavior, other limits and explicit capability OpenMP/BLAS settings remain unchanged. This is not CPU affinity, an aggregate MPI quota or a host security-policy change.
- Example constructed limit: 8 allocated CPUs × 2.5 seconds yields 21 CPU seconds including cushion, versus the old 4. Invalid/nonfinite allocations are rejected before limit calls. Tests mock limit calls rather than changing host limits.
- Treat malformed/inconsistent worker success envelopes as transport uncertainty (`WorkerUnavailable`), retaining genuine worker rejections as semantic errors; do not prematurely fail a possibly running experiment.
- Validation: CPU construction/transport/staging/web suite passed, including a recovery test for malformed replies; CLI and Ruff passed. Actual multi-core isolated runs remain untested due host restrictions.

### Independent review corrections
- Independent review found that targeted polling could leave unrelated stale jobs counted against admission. Reconcile once under the existing admission lock; per-job polls stay O(1). Four saturation regressions reclaim 256 expired/disappeared/cancelled receipts and preserve the genuinely-live queue cap.
- Independent review also found that generic bootstrap transport legitimately returns scalar success values. Keep generic result compatibility while requiring object results only at the worker-RPC boundary.
- These audit-introduced integration regressions were fixed in follow-up commits before final validation, without rewriting history.
- Validation: independent harness review 49 passed; focused harness scope 88 passed, 14 environment-gated skips; review/web regression smoke passed. Two hundred seeded randomized provider logs matched pristine accounting totals. Ruff passed.
