# Shared study navigation integration log

## Scope and base

- Work date: 2026-10-02 (UTC)
- Local branch: `feat/rc4-shared-study-navigation`
- Exact integration base: `cc4ae638cc69911f2fd252cb1bbe8bee4cabf149`
  (released `v0.5.3rc4`, also current upstream main when checked)
- rc4 includes the exact audit head `c13585139973d7ab2d5057938db2f3c332b5c64d`
  above public rc3 `2f66b8d06c20b18cfea20188acad60b83fa25ec0`.
- The first read-only upstream check still found rc3. After the user's rc4 update,
  a fresh check verified annotated tag `v0.5.3rc4` and its peeled commit above.
- The original audit-based navigation branch was preserved. A new rc4 worktree
  received only the seven incremental navigation commits. All implementation/test
  commits applied cleanly because rc4's web code matches the audit head. The sole
  conflict was the changelog: rc4's release section was retained and the new
  navigation notes remain under Unreleased. No audit commits were duplicated.
- rc4 version, installer, packaging exclusions, release acceptance notes, and
  dependency-lock changes are preserved. No push, merge, release, deployment,
  history rewrite, credential use, or paid model call was performed.

## Implemented

1. Shared URL builders and a semantic Conversation → Study → Evidence & review
   trail in the existing workspace and study-details pages.
2. Explicit selected-study cards and study-preserving conversation/mode links.
   Reloads and newly launched studies retain an unambiguous selection.
3. Study details resolves its owning conversation from server-side, path-checked
   workspace records. The return and continuation links use that exact owner.
4. Implicit continuation reuses an owned conversation, with busy and pending-brief
   guards. Direct CLI and read-only inspection remain available; standalone
   continuation retains its create-on-submit fallback.
5. Monitor campaign choices update the URL and respond to Back/Forward. Stale
   snapshot/study-list responses cannot overwrite a newer choice.
6. Continuation dialogs capture their source context, suppress duplicate requests,
   preserve retryable form errors, and dismiss on route departure. Late results
   do not drag a user away from newer navigation. Before submission, Cancel/Escape
   does not prepare a proposal. During a pending POST, Cancel/Escape is disabled
   because cancellation could not guarantee the server had not prepared it.
7. Ordinary simulation results are explicitly distinguished from independent
   scientific acceptance. Graphs, evidence, advanced controls, and scientific
   storage/contracts are retained; this is not a frontend rewrite.

## Validation record

See the review pack's `TEST_RESULTS.md` for final commands, counts, failure
comparison, and bundle/patch checks. New coverage includes ownership, standalone
fallback, legacy launched briefs, read-only state, captured continuation identity,
repeated/cancelled flows, reload/mode state, navigation races, and monitor history.

During integration, the local HTTP/CSP test caught the missing server allowlist
entry for the new JavaScript module. It was corrected in a separate commit and
retested. A successful syntax check alone would not have caught that issue.

## Known limits and review needs

- Rendered desktop/mobile browser QA and screenshots were unavailable. The
  Playwright-managed Chromium binary is absent; the prior system Chromium attempt
  could not create required sockets, and the cloud browser rejected local URLs.
  No security restriction was bypassed. Deterministic DOM tests and HTTP checks
  are not a visual inspection. Runnable browser acceptance tests are included.
- The full inherited suite has known environment/runtime failures; the review
  pack distinguishes current outcomes from historical audit results.
- Standalone continuation has no durable request-key replay journal. After an
  ambiguous lost POST response, check for the created `Continue:` conversation
  before resubmitting. Repeated pending clicks are suppressed; owned retries
  reuse the owner and protect an existing proposal.
- Navigation selection is URL-backed, not a server-side last-view preference.
  Opening a conversation without a study in its link selects its latest study.
- Existing unrelated unlaunched proposals are not silently cleared. Resolve the
  proposal or active conversation turn before preparing another continuation.

## rc4 integration guidance

This pack is incremental from the exact released rc4 commit named above. It
contains only the navigation integration, not the earlier audit fixes or rc4's
release/packaging changes. Import the bundle or apply the patch on a separate
branch starting at that rc4 commit. Both routes were checked to reconstruct the
same final Git tree.

For a later branch that has changed these areas, likely overlap points are
`web/workspace.py` (continuation/ownership), `web/application.py` (snapshot
projection), `web/server.py` (asset allowlist), `web/static/workspace.js`
(routes/actions/study cards), `web/static/app.js` (monitor selection/control
links), both HTML shells, and `interface.css`. Preserve later features and the
new regression tests when resolving conflicts. Keep conversation ownership
authoritative and path-checked, and do not relax read-only controls or independent
evidence semantics. Rerun validation after conflict resolution; the current
results apply to the supplied rc4-based tree.
