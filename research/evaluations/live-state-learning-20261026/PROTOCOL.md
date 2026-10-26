# Live scientific observation audit

This phase checks the mismatch between the authored training snapshots and the
actual observation stream before another optimizer update. It uses saved data
and native read-only judgments; no model training or scientific simulation is
part of this audit. Later model-effectiveness evaluation requires fresh runs.

Select the first, middle and last eligible observation from each of the seven
completed worker-only episodes of `qualified32-clean`, plus the corresponding
three observations from the parked commissioning episode. Eligibility requires
a submitted parked-worker state and receipt inside a recorded parking interval.
Retain all exclusion reasons. This selection uses neither model predictions nor
future scientific success labels. The earlier preparation attempt stopped on
an inconsistent active-state record before any native judgment; it is preserved.

Two separate ephemeral `gpt-6-astra` high-reasoning auditor contexts assess each
of 24 observations. Each call handles four observations, giving 12 assigned
calls. Deterministic reviewer-specific shuffles use seeds `202610260497` and
`202610260498`. Auditors see the actual public model view and answer schema,
not the fixture family, original proposals, admissions, later outcomes or one
another's judgments. Shell/execution and web tools are disabled. Observations
remain data, not instructions to the auditor.

Each judgment gives the five proposed answer fields, acceptable route
alternatives, certainty, whether attention before the ordinary terminal event
or 90-second fallback appears warranted, and an evidence-based reason. These
are model judgments, not human ground truth or measured intervention returns.
Report disagreement and uncertainty; do not turn consensus into a causal label.
Validate every candidate and citation against its own visible input.

The remote coordinator freezes row/provenance, prompt, schema and runner hashes
in `live-label-audit-v2/PLAN.json` before execution. A separate native lease
allows at most 18 starts, one per invocation, at most two concurrent calls and
one hour overall. The initial 12 calls consume the existing original allowance:
611 of 640 starts were used before this audit. Six slots are reserved for
explicitly recorded adjudication or diagnosed recovery, not automatic retries.
Each native call is bounded to 360 seconds. Stop scheduling after a failed pair
and preserve all failed/unstarted assignments. No Colab allocation is needed.

These historical trajectories become development material for subsequent
training design. Their previously reported workflow results stay unchanged,
but they cannot be reused as untouched validation of a model trained from these
judgments. Labels are not automatically eligible for optimization: first audit
the actual outputs, uncertainties, conflicts and evidence binding.

## Operational amendments

The initial pair stopped after one provider 429 failure and one success. A
separate recovery controller, frozen at 09:09:50 UTC, retained the successful
response and retried/scheduled the outstanding assignments serially, with at
least 60 seconds between starts. Two calls succeeded, then a further 429 stopped
that controller. A second recovery controller was frozen at 09:17:14 UTC with a
120-second gap after each completed call. It also stops on any failure.

Both amendments keep the original prompts, schema, assignments, overall native
start ceiling and deadline. Failed attempts remain in their original folders;
successful responses are not overwritten or rerun. A failed provider request is
not a scientific judgment. Separate recovery plans record their runner hashes
and the original plan/status hashes. The postprocessor verifies input hashes,
recovery-to-original assignment binding, candidate/citation binding, coverage
and absence of tool use before summarizing agreement. These scheduling changes do not create additional
independent reviewers or relax optimizer eligibility.

## Direct pretrained-base versus SFT workflow replication

The next effectiveness study compares the unadapted pretrained Intern-Decision-4B
with the exact continued-SFT checkpoint behind the earlier 223.9-second mean.
Worker-only and the frozen generic operational/check rules remain deployment
comparators. RL superiority is not a success or release requirement. No new
optimizer update precedes this comparison.

Use the existing eight workflow mechanisms, one newly assigned fixture seed per
mechanism, and two independent executions of every arm/configuration: 64 assigned
workflows in 16 four-arm blocks. These are fresh trajectories within previously
explored mechanisms, not a claim of unseen-mechanism generalization. In this
fixture generator a new seed changes only the minimum aggregation duration;
do not describe that as a substantially new scientific problem. Both repetitions
retain the same fixture seed but start separate worker contexts and physical jobs.
Freeze the assignment manifest before any new worker starts. Balance arm positions
across blocks and randomize block order with seed 202610261337.

Run one complete workflow at a time to remove inter-episode contention for the
shared physics backend and worker provider. Helpers within that workflow may run
concurrently. All arms use the same source, worker model/settings, task text,
permissions, 90-second fallback, one discretionary attention allowance, scientific
verifier, and two real WarpX controls. Use the fresh-snapshot fix for every model
arm, temperature 1 and the original independent decoder. Do not change the
decoding contract while measuring this checkpoint ablation. Pin all source,
model, backend and environment identities in the execution manifest; qualify
SFT against its saved probes before and after collection. Verify that disabled
adapter predictions match the unadapted base before collection.

The primary comparison is SFT minus base restricted completion time. A verified
completion contributes its elapsed time capped at 650 seconds; an unverified or
unfinished workflow contributes 650 seconds. Report verified completion counts
alongside time, actual elapsed time, native role starts, model input tokens and
latency, assistance use, and returned-feedback misses. An early failure must not
look like a speed improvement. Report all assigned trials, including failures,
and retain infrastructure failures separately without silently replacing them.

Compute paired differences inside each four-arm block. Use 10,000 hierarchical
bootstrap replicates (seed 202610261338), resampling the eight mechanism families
and then the two repetitions within each selected family. Report a descriptive
95% interval for the primary SFT/base contrast. For the two secondary deployment
contrasts, SFT/worker-only and SFT/rules, report 97.5% intervals for each as a
Bonferroni adjustment across those two contrasts. Eight mechanism clusters still
limit precision. Equal observed completion counts do not establish population
equivalence. A faster but less successful model is not an unqualified win.

For the four healthy/recovering mechanisms, report episode-level automatic
attention incidence, uncertainty, and the actual public evidence behind each
dispatch. This incidence is a potentially unnecessary-attention proxy, not an
adjudicated false-alert rate. Keep model proposals, host rejections and admitted
dispatches distinct. Do not train on these evaluation outcomes or use them to
select another checkpoint before reporting the frozen comparison.

This study receives a separate prospective resource lease; it does not extend
an expired earlier lease. Planned bounds are eight hours, at most 100 Colab
compute units, 640 native starts, at most 12 starts per workflow, and at most
six simultaneous native roles within the single active workflow. Before each
new block require room for all four 750-second controller bounds and 48 native
starts. Stop new assignments on infrastructure failure, preserve the incomplete
block, and release the owned A100 after results are copied off-runtime. All
inference stays on the remote A100, all physics on the remote P40 host. The
local machine only orchestrates and stores small evidence/code artifacts.

### Execution record

The native `gpt-6-astra` preflight completed successfully. Its one start is
deducted from the registered ceiling, leaving at most 639 workflow role starts.
The remote P40 preflight found the pinned solver binary unchanged and both GPUs
idle apart from small resident allocations. GPU 0 remains the frozen backend.

The first allocation attempt obtained an A100 but its SSH master failed because
the control pathname plus SSH's temporary suffix exceeded the Unix socket limit.
No timed workflow started. The guard released that runtime; all 64 assignments
remain recorded as unstarted in that attempt. This is an orchestration setup
failure, not a scientific outcome or a checkpoint performance result.

Recovery uses shorter `rep2` resource names and the separate output directory
`base-sft-replication-v2`. It preserves the assignment-manifest hash, source
revision, checkpoints, original eight-hour deadline and 100-unit spending
ceiling. It does not replace or rerun a scientific trial. Both model inference
and physical jobs remain off the local host. The first attempt's records are
retained separately.

The [registration](replication-registration.json) binds source, controller,
analysis, preflight and backend hashes. The [launch record](replication-launch.json)
records the owned processes and lease. Exact deployment, serving, serial
collection and finalization scripts are retained in `replication-operations/`.
The finalizer audits every started trial, separately lists unstarted assignments,
then runs the registered hierarchical comparison. Early failures receive the
650-second penalty; unstarted trials do not receive fabricated outcomes.

Local analysis checks verified that resampling retains variation between
repetitions even when family means agree, rejects duplicate block/arm records,
caps verified completion times at the shared horizon, and cannot turn an early
failure or an unstarted comparator into an apparent timing advantage. These are
checks of the analysis implementation, not scientific results.

### Interruption after two starts

Recovery passed all three base/SFT probability probes and began the registered
first block. The rules episode completed and independently verified both real
WarpX controls and its final report in 351.5 seconds, with four native starts
and one automatic help request. The base episode's first native invocation
returned HTTP 429; no simulation or model attention decision ran in that episode.
It remains a recorded failure, with the prescribed 650-second restricted-time
penalty, rather than a replacement trial.

The long-lived proxy tunnel through the local host also disconnected. The
coordinator's A100 SSH link was lost, so final probability requalification could
not run. Collection stopped before SFT or worker-only started: two attempted,
62 unstarted, and zero complete four-arm blocks. There is no SFT/base workflow
contrast from this attempt. The [interruption evidence](replication-interruption.json)
retains the outcomes, verification, coverage and failed native events.

A read-only account check reported ordinary usage allowed, 34% of the weekly
Codex window used, and no reached-limit or spend-control flag. This does not
identify the reason for the 429. The allocated A100 was explicitly released
through the already approved local US route when the broken forwarding tunnel
prevented the remote guard from doing so; absence of that owned endpoint was
verified. Native actors and the owned P40 connection were closed.

Before further scientific assignments, test a direct coordinator-to-Colab link
and bounded recovery from an intentionally dropped owned SSH connection using
saved qualification inputs only. Keep the existing attempted episodes intact.
The optional transport adapter may replay an identical stateless prediction
once within 20 seconds; it never dispatches assistance or relaxes host freshness
checks. This engineering commissioning is not another scientific test episode.
