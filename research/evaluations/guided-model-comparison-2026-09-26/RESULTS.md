# Guided reconnection model comparison and repair follow-up — 2026-09-26

The public interpretation and comparison are in
[the LLM comparison page](../../../docs/research/llm-comparison.md).
`measurements.json` contains sanitized aggregates from the two final monitor snapshots,
including their hashes. Original harness revision: `de4c8a6`. These are historical
observations, not a new benchmark of the repair.

## Evidence behind the repairs

1. `AgentSupervisor.assign` restored descendants only for frontier mode. Structured
   successor assignments lost child instrument access after local allowance rollover.
   The DeepSeek structured tree accumulated instrument versions v1 through v8.
2. DeepSeek minimal's `ic_run.py` before/after diff removed only the output entry
   `scientific_evidence_eligible: False`. Four repeat simulations followed. Host stage
   and source provenance already existed; output annotations should not define policy.
3. Methods approval contained unmet commissioning conditions while returning `continue`.
   Timing/parity pilots were also criticized as if they were completed hypothesis tests.
4. Commitment `commit_4bb4303527199a0903ebf530` required incompatible S=2000 rate bounds:
   [0.025512, 0.029297] AND R >= 1.08 * 0.027231. The lower threshold is 0.02940948.
5. The structured supervisor logged `cancellation_error` with
   `Expecting value: line 1 column 1 (char 0)`. The active commissioning job
   `job_e4e3d1c7865cba90591539c3bafcff0f` needed explicit kernel cancellation after
   supervisor exit. This is evidence of a cleanup transport failure, not proof of
   snapshot truncation in that particular run.

## Implemented repairs

- Successor assignments inherit existing grants for the same claim and role, plus
  reachable commissioning descendants. Structured roles do not receive unrelated
  scientific branches. Frontier retains descendant access. Role/tool restrictions remain.
- Methods verdicts require an explicit `prerequisites` list. `continue` with unmet
  prerequisites fails schema validation and leaves the method queued; execution also
  rejects imported approvals containing unmet prerequisites. Legacy completed approvals
  without this new field retain their saved policy. A reviewer can still omit a real
  condition; this is not a proof checker for its prose.
- Timing and parity purposes are recorded and exposed to oversight. Review instructions
  distinguish exploration from claim evidence and treat missing purpose as unknown.
- Output eligibility annotations become visible review findings rather than automatic
  host vetoes. Artifact hashes, source bindings, exploration exclusion, fresh repair
  commitments and independent scientific acceptance remain enforced. Existing records
  are not rewritten or promoted. Actual source changes still need methods review.
- Optional `numerical_bounds` in prospective commitments are finite, case-qualified,
  inclusive bounds. Contradictory conjunctions fail before any commitment or job is
  created. Feasibility does not establish physical correctness or satisfy the bound.
- Scientific review instructions distinguish an exact exponent from an interval claim,
  censoring from falsification, and impossible acceptance from failed physics.
- Cancellation enumerates the complete durable job store directly, attempts every active
  job even when another fails, and records errors and remaining jobs. It no longer
  depends on parsing a one-shot CLI response. Cleanup does not claim success when jobs
  remain or their outcomes are unknown; process identity checks still apply.

## Still open

- A general solver/raw-data/analysis lineage API is not implemented by this patch.
  Metadata-only reruns are addressed; arbitrary analysis changes need explicit provenance.
- Better live structured reporting should expose completed case counts separately from
  job counts. The public comparison corrects the stale-narrative interpretation.
- No causal model ranking or claim that the new harness completes reconnection is justified.
  Follow-up live trials are needed. No long campaign was restarted by this repair.

## Validation

- Full release environment: **664 passed, 7 skipped**. Skips require PRoot/non-root
  execution or locally absent WarpX, FLASH and EOS runtimes.
- DSH tests against the real MCP profile: **14 passed**.
- Ruff, public schema consistency and Sphinx with warnings as errors: passed.
- All three portable recorded-demo verifiers: passed.
- Installed v0.5.1 wheel import/version smoke: passed; launch archive checksums verified.
- No new token-consuming model comparison or long plasma run was launched. These
  checks validate the repair mechanics, not improved scientific completion rates.
