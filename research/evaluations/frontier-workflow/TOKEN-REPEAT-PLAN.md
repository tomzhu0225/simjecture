# Token-accounted repeat

Repeat the two original tasks, both workflows, GLM 5.3, 900-second campaign
budget and 180-second session interval, at most two simultaneous runs. Preserve
the original five frozen implementation files, including their known limitations;
this evaluates the original comparison, not the later client/path fixes. Other
imported package files come from the current worktree. Check the four originally
recorded implementation hashes before launch and record the complete source tree.

The only CLI change removes `--ephemeral` for fresh reviewers so their incremental
usage survives interruption. Reviewers remain fresh, read-only and subject to the
same tool-free acceptance check. Do not read unrelated session contents or expose
private traces. Associate session logs by the exact thread IDs emitted by these
invocations. Collect workers and reviewers separately, then combine.

Use the last cumulative native `total_token_usage` once per unique thread, never
sum resumed thread snapshots. Capture completed inference calls even when the
outer agent turn is interrupted. Also record completed-turn usage as a cross-check,
missing sessions, non-completed invocations, and cumulative counter regressions.
Cached input and reasoning output are reported separately, not added again to
input/output totals. No prices or subscription-credit costs are inferred.
Requests interrupted before usage is emitted remain unmeasured; describe totals
as reported usage rather than complete billing. Retain all four outcomes, including
failures. Compare equal-budget usage and accepted outcomes without treating lower
usage alone as efficiency or making statistical claims from this small sample.
