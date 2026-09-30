# Builtin DeepSeek adapter: measured tool-protocol repair

On 2026-09-29, nineteen live `deepseek-flash` trials compared the current adapter
with native tool-message history, a stronger action instruction, deterministic
checkpoints and completion checks against verified artifacts. All nineteen passed
the registered numerical and delivery criteria. The production change adopts
**native tool-message history only**, in the builtin DeepSeek worker path.

## What changed

Previous tool calls and their results now retain structured call IDs and native
`assistant.tool_calls` / `tool` messages instead of becoming prose such as
`Calling tools: ...`. The adapter preserves provider-required private reasoning
separately from public activity, removes legacy textual stop delimiters on this
path, and keeps actual tool failure information available to the next action.
Existing conversation files remain readable. No model prose is promoted to a
tool invocation by this conversion.

The original explicit-completion guard still operates. Minimal mode, fresh
autonomous sessions, the 24-step limit, generated summaries at that limit and
independent scientific review rules are unchanged. Interactive conversations
continue to retain history. Native CLI backends keep their existing transports.
This is an internal adapter improvement, not a new research mode or a GUI setting;
tool activity and token accounting use the existing terminal and web views.

## Screening and confirmation

Fifteen screening trials used eight-step slices: three matched blocks, two with
the original energy contract and one with a revised radiation-energy definition.
Each of five variants received the same files and saved diagnosis, fresh context,
provider configuration, tools, per-trial budgets and independent grader.

Native history produced zero completion-check retries in its three screening
trials, compared with nine across the matching baseline trials. The other three
changes had mixed or worse overall results, so they were not enabled by default.
Their internal hooks remain available to the evaluation scripts only. The
verified-completion condition additionally depends on a complete task-specific
grader; it cannot automatically establish completion of open scientific research.

The candidate was selected before four new confirmation runs at the normal
24-step limit. Totals across one original-contract and one changed-contract task
per adapter were:

| Metric | Existing adapter | Native tool history | Change |
|---|---:|---:|---:|
| Numerical checks and delivery | 2/2 | 2/2 | Equal |
| Completion-check retries | 8 | 1 | −87.5% |
| Total input tokens | 325,478 | 196,239 | −39.7% |
| Uncached input tokens | 28,646 | 14,223 | −50.3% |
| Output tokens | 19,259 | 16,155 | −16.1% |
| Provider requests | 28 | 20 | −28.6% |
| Summed wall time | 88.97 s | 73.48 s | −17.4% |

All confirmation runs finished inside one slice with no forced summary. Thus
confirmation supports using the adapter under the normal limit, but does not test
continuity across a natural 24-step boundary. The remaining retry in the changed
native trial is a reason to retain the completion guard.

## Validation and limits

The grader reexecutes each submitted reducer on an archive and five unseen
synthetic cases: 54 numerical/boolean checks, an agreeing saved result, a nonempty
findings file and frozen-input integrity. Reexecution of all exported submissions
on a second machine reproduced **1,026/1,026 checks**. Missing reports, fabricated
success flags, changed frozen inputs and a stale-contract implementation were
rejected in preflight. Report existence does not validate every prose claim.

Protocol regressions cover parallel call/result pairing, failed calls, text-only
promises, false/unavailable completion receipts, private reasoning continuity and
incomplete checkpoints at both short and 24-step limits. Tests passed with
smolagents 1.24.0 and 1.26.0. The deployed benchmark implementation was frozen;
the final integration also preserves the recorded error on failed native calls.

This is an explicitly specified archived-data recovery task, not a new FLASH or
WarpX simulation, a comparison between LLMs, or proof of better ten-hour research
completion. Samples are small, provider cache state was not reset, and native
history plus removal of legacy stop delimiters were tested together. No response
was locally trimmed in these trials; a separate delimiter-only ablation was not
run. No currency prices or retrospective invoices were inferred.

The entire batch consumed **2,144,914 input tokens** (1,843,712 cached),
**141,061 output tokens**, **223 successful requests**, and **687.53 summed
trial-seconds**, within the registered aggregate caps. The common diagnosis was
reused from the previous experiment and is not charged again here.

Registered plans, selection, scripts and detailed results are under
`research/evaluations/adapter-overhead-20260929/`. Public traces, submitted code,
grader records and local revalidation are retained under
`artifacts/adapter-overhead-20260929/`. Private credentials and reasoning/session
files are excluded from the exports.

## Longer follow-up: two fifteen-minute FLASH investigations

On 2026-09-30, a further matched pair used real FLASH 4.8 aluminum RZ calculations
at 128 and 256 radial cells, four axial cells and a requested 20 ns endpoint.
Both used the same frozen launcher, two MPI ranks per case, raw HDF5/CSV reduction
contract, builtin tools, fresh sessions and normal 24-step limit. They executed
through the numerical service with `proot-cooperative`. Independent numerical
grading replaced the scientific review loop for this adapter benchmark; its
results are exploratory observations, without physical-method or claim approval.

An initial pilot stopped at a 1.5M-input-token reservation after about 7.4 minutes.
Both fine-grid jobs were cancelled, so that pilot does not answer the intended
wall-time comparison. A fresh pair received the original 900-second limit and
larger equal token allowances (4M input / 125K output each). Preserve and report
the pilot separately; no existing study's deadline was extended.

| Reported quantity | Existing adapter | Native tool history |
|---|---:|---:|
| Worker turns | 5 | 4 |
| Successful provider requests | 78 | 73 |
| Completion-check retries | 16 | 0 |
| Total input tokens | 2,020,475 | 1,669,082 |
| Uncached input tokens | 153,467 | 139,482 |
| Output tokens | 67,472 | 54,684 |
| Recorded solver-wait time | 381.79 s | 388.81 s |
| Elapsed wall time | 901.15 s | 900.27 s |
| Complete two-grid task | No | No |

Native history used 17.4% less reported input, 9.1% less uncached input and 19.0%
less output. Both crossed the normal action boundary and resumed saved work.
There is one repetition per adapter; shared cache state, concurrent CPU work,
sampling and different action choices limit causal performance claims. The two
deadline-interrupted requests have unknown usage and are excluded from these
reported response totals. No invoice is reconstructed.

Both coarse cases completed, taking about 265 seconds through the numerical
launcher. Both fine cases hit the 780-second experiment limit before reaching
20 ns. The full 75-check delivery criterion therefore could not be evaluated;
the recorded zero pass count means the required complete matrix was unavailable,
not that every reported numerical value was wrong. This was a benchmark runtime
calibration failure, not evidence that either adapter refused to run FLASH.

Post-run independent checks of the completed coarse case plus three unseen
synthetic cases reproduced 60/60 values for native and 59/60 for baseline. The
baseline interpreted `delta_stored_J` over compression, whereas the grader used
the full recorded window. That window was not explicitly stated for this key in
the task brief, so this discrepancy is not a fair model-accuracy ranking. The
remaining 59 shared comparisons passed for both adapters. Both wrote reports
and labelled plots, and both disclosed the failed refinement and missing physical
energy terms.

The compression criterion selected a single HDF5 sample at the supplied 1 ns
cadence. The resulting zero-width integral is zero by definition and cannot
establish a physical absence of compression radiation. Both workers recognized
this limitation. The coarse result's total broadband ratio was about 1.531,
but the failed fine case has a shorter radiation integration window, so its
late-time ratio cannot serve as a matched 20 ns convergence comparison.

The longer task supports the transport-efficiency improvement and demonstrates
continued work across actual action-limit checkpoints. It establishes no better
scientific completion rate. The next benchmark should time its slowest required
solver case first, reserve analysis/recovery time, qualify the diagnostic sampling
cadence and explicitly define every quantity's integration window. These changes
must precede a new launch, rather than relabel these observations afterward.

Additional preparation issues are retained in the audit: a directory was initially
declared where the experiment interface expects files, and a private grader's
bytecode cache needed the same permissions as its source. Both were corrected;
the equal-wall pair began with protected grader source and bytecode. The pilot's
native worker attempted to search the grader directory; no such attempt appears
in the equal-wall pair. Stale child `run-receipt.json` files initially raised an
orphan-process concern, but direct process checks found no remaining solver or
benchmark processes. No cancellation defect is established by those stale files.

The equal-wall pair consumed **3,689,557 reported input tokens**, 3,396,608 cached,
and **122,156 output tokens** across 151 successful requests. Including the
separately reported pilot: **6,388,625 input**, 5,878,528 cached, and **238,292 output**
across 256 successful requests. The pilot's two incomplete request receipts were
locally rejected at the input reservation before submission; the equal-wall
pair's two interrupted responses remain unknown. Scripts, frozen plans, results,
plots and revalidation are under `research/evaluations/long-adapter-20260930/` and
`artifacts/long-adapter-20260930/`. Existing defaults and runtime code were not
changed by this follow-up.
