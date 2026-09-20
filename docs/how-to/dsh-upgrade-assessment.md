# DSH upgrade assessment — 2026-09-20

Migration implemented: Simjecture profile `0.2.3` pins DSH `0.1.5-rc.2`.
The scientific CampaignKernel and its evidence contract remain unchanged.
The adapter changes and validation described below replace the earlier
recommendation to retain `0.1.1-rc.2` pending compatibility work.

The official npm registry currently tags `0.1.5-rc.2` as `latest` and `next`,
and `0.1.6-alpha.2` as `alpha`. These are all prereleases. The recommended first
migration target is the default-channel `0.1.5-rc.2`, keeping the alpha work
separate. Versions were checked with `npm view @deepseek-ai/dsh dist-tags --json`.

## Compatibility findings addressed

The audit inspected upstream tag `dsh-v0.1.5-rc.2`, commit
`fb2c4b9e698e30edb738bca4cf0618587db7d203`.

| Boundary | Previous adapter | Upstream target | Migration requirement |
| --- | --- | --- | --- |
| Session history | `runner.js` and `context-elider.js` read `session.events` | `Session` exposes `snapshotEvents()` and `eventAt()` instead | Migrate history access and exercise resume, summarization, and pruning against real DSH |
| Surface replacement | `context-elider.js` writes `{ op: 'replace', start, end }` | `SurfaceOp` requires `startSeq` and `endSeq` | Update replacement events and test balanced tool exchanges and preserved original history |
| Durable sessions | Existing campaign-local DSH logs | Target includes session-format V3 and V2-to-V3 migration | Test upgrade on copies of old logs, including restart and failed migration; retain originals for rollback |
| Profile composition | Pinned headless profile, disabled generic tools, seven lead tools and scoped workers | Plugin composition and runtime have evolved | Inspect resolved configuration and actual tool catalogs; test mandatory MCP startup failure and every role restriction |

Primary source files:

- [Session history implementation](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.5-rc.2/packages/core/session/src/index.ts)
- [Surface event types](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.5-rc.2/packages/core/session/src/types.ts)
- [V2-to-V3 migration](https://github.com/deepseek-ai/deepseek-harness/blob/dsh-v0.1.5-rc.2/packages/session/session-format-v2-to-v3/src/migration.ts)
- [Official releases](https://github.com/deepseek-ai/deepseek-harness/releases)

The `0.1.6` release notes additionally describe headless stdin/session/JSON-event
support, MCP SDK v2, asynchronous agent initialization, deprecation of synchronous
history readers, and changes to plugin loading. Those features may eventually
simplify our custom driver, but do not by themselves replace its campaign budget,
control-file, activity projection, and reconciliation responsibilities. An alpha
migration should use its asynchronous history API rather than adopting a newly
deprecated synchronous interface.

## Why the scientific kernel does not need to change

DSH owns model requests, retries, conversation history, compaction, and child
sessions. CampaignKernel owns contracts, claim disposition, evidence provenance,
sandboxing, durable simulation jobs, and the deterministic finish gate. The
confirmed upstream breaks are in the JavaScript adapter's DSH APIs, not the
scientific MCP contract. No kernel schema migration is justified by these changes.

The version-change acceptance criteria require a real-runtime adapter smoke test in addition
to the existing bundle tests: fresh campaign, each scoped role, tool-free judge,
context pruning, pause/resume on migrated logs, interrupted durable job recovery,
and finalization only through the kernel gate. Existing source-string/fake tests
alone cannot qualify a DSH version change. Install and test an isolated profile;
do not migrate active campaign logs in place during evaluation.

## Completed validation

The adapter now uses `snapshotEvents()` / `eventAt()`, V3 surface replacement
fields, the renamed `ToolCallId` export, and `personaPrefix`. Removed profile
rows no longer produce missing-entry warnings. Claim guards attach at
`agent/created`, before a child receives its first prompt. The Blocker Resolver
allows DSH's schema-validated `structured_output` handoff. The Judge uses the
supported schema subset and explicitly rejects inconsistent decision/disposition
pairs before calling the kernel.

The checked-in Node tests run real DSH services with deterministic model output.
They cover original-history preservation, V2-to-V3 migration, fresh/resumed lead
sessions, each worker's first-call mutation guard, independent judge tools and
usage, and job reconciliation without model polling or resubmission. A complete
CLI/profile/Python-MCP test verifies the exact lead tool catalog, immutable
snapshot access, rejection of premature finalization, pause/resume, and no model
request after mandatory MCP startup failure. No paid-provider or long-running
scientific campaign was used for qualification. Production profiles and existing
campaign logs were not modified during this work.
