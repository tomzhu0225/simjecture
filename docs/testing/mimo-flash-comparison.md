# MiMo v2.6 Flash/Pro and DeepSeek V4.1 Flash: measured coding trials

On 2026-09-30, **DeepSeek completed a two-grid FLASH diagnostic task, while
MiMo Flash completed the simulations but did not deliver the analysis within the
15-minute budget**. A separate three-minute CSV coding control passed for both.
These observations support trying MiMo Flash on bounded analysis assignments; they
do not establish that its current configuration can reliably replace DeepSeek
for a larger investigation.

A subsequent **MiMo v2.6 Pro trial completed the same FLASH assignment and
passed the CSV control**. Its registered follow-up and limits are reported below.

## Common setup and qualification

Both used MiMo Code 0.1.14, its OpenAI-compatible adapter, native tool history,
reasoning enabled, an 8192-token response limit, a 262144-token context limit
and 24 actions per interactive prompt. Background memory writing and delegation
were disabled in the matched trials. Tools could read source, write code and
run analysis. The native client was selected because the configured MiMo account
is a Token Plan subscription for supported coding tools, rather than an
unrestricted application API account. [Provider integration guidance](https://mimo.mi.com/docs/zh-CN/tokenplan/integration/tools-overview)

The provider model IDs were `mimo-v2.6-flash` and `deepseek-flash`. DeepSeek's
authenticated model listing identified the latter as `DeepSeek-V4.1-Flash`,
with default high reasoning effort. MiMo's unchanged model alias had already
received the provider's September 25 update addressing tool repetition.
No dated weight revision was pinned. [Xiaomi's update](https://mimo.xiaomi.com/zh/blog/mimo-v2-6-tool-call-repetition)

Numerical work used the actual Simjecture 0.5.3rc1 numerical service,
`proot-cooperative`, the frozen FLASH 4.8 capability and read-only solver source.
This is a supervised coding-worker comparison: the full research supervisor,
methods approval and independent scientific-claim review loop were not run.
It is not a comparison of minimal versus structured research modes, nor a
measurement of the builtin API adapter's completion-check retries.

Before paid trials, the exact launcher successfully ran 64×4 and 128×4 RZ cases
to 20 ns, two MPI ranks each. The 0.05 ns output cadence produced 401 plots per
case, with 150 and 30 compression-window samples. This fixes the earlier
benchmark's slow 256-cell case and one-sample window. The new brief explicitly
defines stored-energy change over the full record; neither the previous task
nor its results were altered.

## Fifteen-minute task

Each arm had to launch two fresh cases, reduce raw HDF5/CSV data, compare inward
kinetic energy with escaping radiation, save a result and report, and produce
two plots. Grading reexecuted the submitted reducer on both real cases and three
unseen numerical fixtures: 75 quantities/flags. It also checked the saved result,
report, readable plots and preservation of frozen inputs.

| Observation | MiMo v2.6 Flash | DeepSeek V4.1 Flash |
|---|---:|---:|
| Required FLASH cases | 2/2 succeeded | 2/2 succeeded |
| Complete task delivered | No | Yes |
| Independent numerical comparisons | Not evaluated: no reducer | 75/75 |
| First host verification | Not reached | 400.45 s |
| Finished response receipts | 22 | 48 |
| Reported input tokens | 878,201 | 2,692,318 |
| Cached input | 834,624 | 2,590,848 |
| Uncached input | 43,577 | 101,470 |
| Output, including reasoning once | 11,175 | 29,422 |

The two models' solver times were essentially identical: about 102 seconds for
n64 and 285–287 seconds for n128. Their CSV input hashes also agree. FLASH access,
installation, runtime and missing inputs therefore do not explain this task's
delivery difference.

DeepSeek wrote and tested a reducer, inspected relevant read-only Fortran source,
and produced agreeing results and plots. It required one continuation after its
24-action checkpoint. MiMo wrote a submission script and progress note but no
reducer, final result, findings or plots. Its smaller token total accompanies
incomplete delivery and is not evidence of better task efficiency.

MiMo's client log records 31 stream starts for 22 finished responses plus one
unfinished response. Several repeated attempts were separated by roughly
one-minute waits; the longest finished response took 281.37 seconds. DeepSeek's
longest was 30.43 seconds. These are client observations, consistent with
timeout/retry recovery. They do not identify the upstream HTTP failure cause,
distinguish provider load from every possible adapter issue, or supply token
receipts for each interrupted attempt. A general reasoning-capacity judgment
cannot be inferred from those stalls.

MiMo also spent actions searching for ratio definitions and a reference reducer
outside its assigned study, including the evaluation code directory. The private
grading source was unreadable: its file owner differed from the runner and mode
was 0600; it was subsequently assigned explicit root ownership. Observed outputs
show public briefs and filenames, without the private reference implementation
or expected numeric values. This is a scope-compliance concern and a reason to
improve trial isolation. A missing analysis cannot be scored as 75 arithmetic
failures. The original brief also left the ratio and signed mass-drift formulas
implicit; those should be explicit before a repetition.

## Separate three-minute CSV control

To test coding ability without solver waits or a longer investigation, fresh
sessions received existing CSVs and three explicit equations. Each had to write
and execute a standard-library reducer, save results and explain that operator
agreement does not prove whole-domain energy closure. The grader checked two
real cases and three unseen CSV fixtures.

| Observation | MiMo v2.6 Flash | DeepSeek V4.1 Flash |
|---|---:|---:|
| Independent comparisons and delivery | 15/15, passed | 15/15, passed |
| Required files last written | 78.73 s | 79.36 s |
| First recorded host grade | 114.35 s | 113.69 s |
| Finished response receipts | 6 | 20 |
| Reported input tokens | 164,603 | 2,561,585 |
| Cached input | 146,048 | 2,426,496 |
| Uncached input | 18,555 | 135,089 |
| Output, including reasoning once | 2,954 | 12,436 |

DeepSeek read four large CSV previews, each roughly 50 KB, into model context.
Its prompt grew from about 21K input tokens to about 132K on the following
request; subsequent requests repeatedly included the larger history. MiMo
sampled headers and a few rows, then computed from files. This is an observed
model action choice with a measurable context cost. A tested table-preview tool
may help, but this trial did not benchmark that proposed tool or show that the
existing Simjecture builtin reader has the same behavior.

Both controls had an unfinished final response at cancellation, despite already
passing the file-based criterion. Those requests have unknown usage. The control
is deliberately easier, and its results must not be pooled with the simulation
task as repeated measurements of the same assignment.

## Accounting, operator issues and validation

The initial Flash/DeepSeek paid batch, including the preliminary coding checks, reported
**6,587,873 input tokens** (6,258,368 cached; 329,505 uncached),
**60,425 output tokens** and **108 finished response receipts**. MiMo accounted
for 1,222,054 input and 16,386 output; DeepSeek for 5,365,819 input and 44,039
output. These are lower bounds: four response records were unfinished and
repeated stream attempts lack separate native usage receipts. Client-normalized
missing values can become zero. Cache and reasoning are not added twice; no
currency invoice or subscription-credit conversion is reconstructed.

The preliminary MiMo check wrote numerically correct outputs in its client-home
directory rather than the assigned project and triggered automatic checkpoint
writing. The matched tasks subsequently used explicit project paths and disabled
background memory writing for both. Preliminary usage is included in spending,
but that check is not counted as a matched-task success.

An initial terminal-capture launch stopped before any model request because
`timeout` lacked `--foreground`. Fresh studies retained the failed attempt and
original deadlines. A calibration collector's workspace-key assumption was also
corrected after the solver jobs had succeeded. Neither issue is a demonstrated
production Simjecture defect. DeepSeek's continuation was initially pasted but
needed a separate Enter to submit; the delay remains inside its budget. The
interactive guard was 885 seconds within each 900-second study, so MiMo's effective
terminal access was slightly shorter than the advertised upper bound. These
operator effects limit clean wall-time attribution.

Private grading source, bytecode and calibration answer metadata were protected.
No observed tool receipt shows reading calibration answers. Older study directories
remained discoverable under the cooperative runner account; this was not an
adversarial isolation test. Exports omit credentials, session databases, private
reasoning, terminal captures, solver binaries/source and material tables.

Reexecution on a second machine reproduced DeepSeek's **75/75** full-task
comparisons and both controls' **15/15** comparisons. Eighteen independent
closed-form clock/energy checks passed, and corrupted quantities were rejected.
Report existence and passing numeric checks do not validate every prose claim
or establish the physical radiation mechanism. All benchmark clients and FLASH
processes were stopped after the tests.

## Pro follow-up on the same tasks

At the user's request, a subsequent sequential trial changed the model ID to
`mimo-v2.6-pro`. The frozen task, launcher, grader, package hashes, 900-second
study deadline, 180-second CSV deadline, client version, native transport,
reasoning setting, 8192-token response limit, 262144-token context limit and
24-action checkpoint were preserved. The CSV control used exactly the same
four input files, verified by SHA-256, as the previous controls.

Pro ran under a separate unprivileged UID to prevent reading the earlier models'
submissions. It had the same registered solver and source access. This is a
useful isolation improvement but a disclosed environment difference. The trial
ran later and without simultaneous peer simulations; provider load and cache
state were not controlled. It is one additional arm, not a statistical repetition
or a model-only causal estimate.

| Full FLASH assignment | MiMo Flash | MiMo Pro | DeepSeek V4.1 Flash |
|---|---:|---:|---:|
| Required solver cases succeeded | 2/2 | 2/2 | 2/2 |
| Complete task and independent checks | Not delivered | Passed 75/75 | Passed 75/75 |
| First recorded host verification | Not reached | 790.85 s | 400.45 s |
| Reported input tokens | 878,201 | 1,710,612 | 2,692,318 |
| Cached input | 834,624 | 1,636,096 | 2,590,848 |
| Uncached input | 43,577 | 74,516 | 101,470 |
| Output including reasoning once | 11,175 | 24,417 | 29,422 |
| Finished response receipts | 22 | 32 | 48 |

Pro spent its first 24 responses submitting the jobs, inspecting the capability,
source and completed diagnostic files, and writing a progress note. It had not
yet written its reducer at that checkpoint. The same continuation policy was
applied when it was idle and recorded jobs were complete; the prompt provided
status and remaining time without numerical answers. Its next turn produced
the reducer, agreeing result, report and both labelled plots. No failed-check
values or solution code were supplied.

The last required file was written at 740.13 seconds, the final public response
finished at about 788.81 seconds, and the first full host grade passed at 790.85
seconds, all within the original deadline. Timing includes client startup, solver
execution, action checkpoints and operator observation. Thus the verification
time is not a pure inference-latency measurement. Its solver times were 100.19
and 276.48 seconds, similar to the earlier arms.

Pro used **36.5% less reported input, 26.6% less uncached input and 17.0% less
output than DeepSeek** on the full assignment. These are token comparisons,
without assuming equal provider prices or subscription-credit multipliers.
Its longest finished response took 113.17 seconds. The client recorded 37 stream
starts and 32 finished response receipts, without separate usage receipts for
the five additional starts; all final main-task response records were complete.

| Separate CSV control | MiMo Flash | MiMo Pro | DeepSeek V4.1 Flash |
|---|---:|---:|---:|
| Checks and delivery | Passed 15/15 | Passed 15/15 | Passed 15/15 |
| Required files last written | 78.73 s | 101.06 s | 79.36 s |
| First recorded host verification | 114.35 s | 151.13 s | 113.69 s |
| Reported input tokens | 164,603 | 340,400 | 2,561,585 |
| Uncached input | 18,555 | 55,856 | 135,089 |
| Output including reasoning once | 2,954 | 7,126 | 12,436 |
| Finished response receipts | 6 | 11 | 20 |

Pro's control completed with standard-library code and the required energy-scope
caveats. It logged three edit-tool errors while making follow-up edits; the
persisted code and result still passed all checks. Its final response completed
within the control deadline, with no unfinished response record. The lighter
Flash control remains more economical in reported tokens and faster in required
file delivery in these single trials.

### Pro preparation issue, accounting and validation

Creating the separate runner exposed a filesystem-access issue: its account
could not traverse the shared MPI toolchain's parent. The initial study setup
failed, and the operator mistakenly started the native client before checking
that setup had succeeded. That invalid preparation session is excluded from
the scored task, and its **211,117 input / 1,984 output tokens, seven finished
responses and one unfinished response** are retained in spending. This was an
operator setup error, not evidence of Pro's task accuracy or a production
Simjecture regression.

A named-user traversal ACL was then granted on the runtime parent, preserving
the earlier studies' permissions. An unpaid, fresh 64×4, 1 ns FLASH calculation
passed through the exact numerical launcher under that account. Only then was
the new scored study created with a fresh deadline. The operator helper now
refuses preparation without a passed launcher receipt, and reports preparation
errors before a model prompt should be sent.

The Pro follow-up batch, including that invalid preparation, reported
**2,262,129 input tokens** (2,095,360 cached; 166,769 uncached),
**33,527 output tokens** and **50 finished response receipts**. Main and CSV
assignments alone reported 2,051,012 input and 31,543 output. Unfinished
preparation and intermediate stream-attempt usage remain unknown; no invoice
is reconstructed. These totals are separate from the earlier Flash/DeepSeek
batch above.

Reexecution of exported Pro code on the local machine reproduced **75/75**
full-task and **15/15** CSV checks against both real cases and unseen fixtures.
The plots were visually inspected for readable labelled units and both grids.
Numeric agreement, scope flags and reports passed the coding criterion; full
scientific-method and claim reviews were not run. All Pro clients and FLASH
processes were stopped. Sanitized evidence and accounting are retained under
`artifacts/model-comparison-20260930/pro/`; host orchestration is in `pro_trial.py`.

## Decision and next experiments

DeepSeek delivered the larger assignment faster. Pro demonstrated a viable
alternative on the same task with fewer reported tokens. Flash passed the smaller
control but did not deliver the full assignment. These are configuration-level
observations; a repeated comparison and longer scientific campaign are needed
before judging research reliability or cost per accepted scientific result.

Before another long assignment:

1. Record per-attempt transport status, stream progress and interrupted usage;
   test recovery on the same deadline and preserved files.
2. State every returned metric's formula, units, window and control volume.
   Scope source lookup to the assigned workspace and registered read-only
   capabilities, with filesystem protection for other trials and graders.
3. Benchmark small schema/row previews and computation from files against large
   native-tool previews. Measure accepted outputs and uncached/cached input
   separately; do not assume a preview tool saves tokens before testing it.
4. Repeat the full matched task after these specific changes. Single trials per
   model plus an easier control do not establish a population completion rate or ten-hour
   autonomous research performance.

No production defaults, research modes or scientific acceptance rules changed
in this comparison. Machine-specific operator scripts and sanitized trial receipts,
submitted code/plots and local validation are retained in the operator's local
evaluation/artifact directories. Those scripts are not public installable tooling.
The portable, independently versioned [Simjecture Bench pack](../how-to/llm-bench.md)
ships the recorded numerical inputs and a strengthened diagnostic replay contract.
