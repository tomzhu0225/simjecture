# Owned coding-agent benchmark — 2026-10-01

**252/252 planned attempts completed** across 42 configurations. 228 attempts reached inference and were graded; 24 were availability-only observations. Campaign status: **complete**.

The current pack 0.3.0 results are **100/188 CSV passes** and **34/40 RZ passes**. CSV numerical checks passed in 161/188 graded attempts; 61 of those did not complete the full delivery contract. RZ has one trial per configuration and remains provisional. There is no overall model winner.

The results ship as [sanitized host grades](https://github.com/tomzhu0225/simjecture/blob/v0.5.3rc3/src/conjecture_solver/llm_bench/results/owned-2026-10-01.json). Open **Benchmarks** in the development workspace to inspect comparison groups, trial receipts and interactive time/cost tradeoffs. Choose **Run your model** for a native CLI or configured API model, or import a grade bundle. See [benchmark usage](../how-to/llm-bench.md) for community submissions. This publication ships in the 0.5.3rc3 preview; it was not included in 0.5.3rc2.

## What was tested

- `csv-energy`: recorded solver CSV diagnostics, independently reexecuted reducer, saved results, immutable inputs and nonempty findings; 180 seconds including host verification; five fresh attempts scheduled per configuration.
- `rz-diagnostics`: two recorded RZ HDF5 cases (64×4 and 128×4, 401 frames each), leaf-block shell integrals, inward kinetic energy, tracer compression, event times, radiation windows, grid differences and numerical plot data; 900 seconds including verification; one fresh attempt per configuration.
- Three newly generated numerical holdouts per task. Agents received failed public-field labels, never expected answers or holdout contents. Native tools and system prompts were retained.
- Eight concurrent workers, shuffled configuration order within each repetition (seed 61001), fresh work directories/conversations, a single original deadline per attempt and a ten-second host-verification reserve. Agent/version preparation precedes the measured budget.

These are diagnostic coding tasks using recorded simulations. They do not test new FLASH/WarpX execution, research autonomy, hypothesis closure or the correctness of physical conclusions. Findings prose is a delivery check, not an LLM judge.

## CSV results

The [official interactive publication](../_static/benchmark-leaderboard.html)
is the primary comparison view: task tabs, time/cost ranks, API tariffs and effort
connections. This report retains the original failure-inclusive cost-per-success
tables below for auditing. Its missing cost-per-success cells do not mean vendor
tariffs are unavailable.

The publication adds a separate [valuation ledger](https://github.com/tomzhu0225/simjecture/blob/v0.5.3rc3/src/conjecture_solver/llm_bench/results/owned-2026-10-01-valuation.json):
recovered native/API counters produce per-attempt standard-rate equivalents.
AGY's input/cache interpretation is an explicitly labelled estimate; interrupted
receipt totals are lower bounds and are excluded from cost ranking. A Groq
reference tariff values GPT-OSS open weights; it is not an AGY invoice. GPT Reserve
has variable routing rather than a fixed public model tariff. No scientific
scores, trial denominators or original host grades changed.

Pass denominators exclude explicitly identified no-inference availability failures. Every attempt that reached inference, including incomplete work and quota interruptions, remains in its denominator. Mean elapsed time includes failures. Time and token cost per success also include failed attempts. `Numbers only` counts all numerical checks passing without the full timed delivery contract.

| Coding agent / model | Effort | Passes / graded | Numbers only | Mean seconds | Seconds / success | Token USD / success |
|---|---|---:|---:|---:|---:|---:|
| `agy/claude-opus-4-6-thinking` | default | 1/1 | 0 | 137.1 | 137.1 | Unknown |
| `agy/claude-sonnet-4-6` | default | 1/1 | 0 | 153.6 | 153.6 | Unknown |
| `agy/gemini-3.1-pro-high` | high | 3/4 | 0 | 111.0 | 148.0 | Unknown |
| `agy/gemini-3.1-pro-low` | low | 5/5 | 0 | 95.1 | 95.1 | Unknown |
| `agy/gemini-3.6-flash-high` | high | 1/4 | 0 | 170.0 | 680.1 | Unknown |
| `agy/gemini-3.6-flash-low` | low | 3/5 | 0 | 159.9 | 266.6 | Unknown |
| `agy/gemini-3.6-flash-medium` | medium | 2/5 | 1 | 162.5 | 406.3 | Unknown |
| `agy/gemini-3.7-flash-high` | high | 4/4 | 0 | 118.2 | 118.2 | Unknown |
| `agy/gemini-3.7-flash-low` | low | 5/5 | 0 | 86.9 | 86.9 | Unknown |
| `agy/gemini-3.7-flash-medium` | medium | 5/5 | 0 | 100.0 | 100.0 | Unknown |
| `agy/gemini-3.8-flash-high` | high | 2/4 | 1 | 172.4 | 344.7 | Unknown |
| `agy/gemini-3.8-flash-low` | low | 4/4 | 0 | 100.7 | 100.7 | Unknown |
| `agy/gemini-3.8-flash-medium` | medium | 5/5 | 0 | 155.6 | 155.6 | Unknown |
| `agy/gpt-oss-120b-medium` | medium | 1/1 | 0 | 148.1 | 148.1 | Unknown |
| `builtin/deepseek-flash` | high | 4/5 | 0 | 74.0 | 92.4 | 0.01669 |
| `builtin/deepseek-v4-pro` | high | 4/5 | 0 | 158.7 | 198.3 | Unknown |
| `builtin/mimo-v2.6-flash` | high | 0/5 | 4 | 170.5 | Unknown | Unknown |
| `builtin/mimo-v2.6-pro` | high | 0/5 | 2 | 170.2 | Unknown | Unknown |
| `codex/gpt-5.5` | medium | 5/5 | 0 | 128.9 | 128.9 | Unknown |
| `codex/gpt-5.6-luna` | medium | 5/5 | 0 | 103.8 | 103.8 | 0.01418 |
| `codex/gpt-5.6-sol` | low | 5/5 | 0 | 127.5 | 127.5 | 0.27024 |
| `codex/gpt-5.6-terra` | medium | 5/5 | 0 | 126.2 | 126.2 | 0.14126 |
| `codex/gpt-6-astra` | high | 0/5 | 5 | 170.9 | Unknown | Unknown |
| `codex/gpt-6-astra` | low | 4/5 | 1 | 163.0 | 203.7 | Unknown |
| `codex/gpt-6-astra` | max | 0/5 | 5 | 170.9 | Unknown | Unknown |
| `codex/gpt-6-astra` | medium | 0/5 | 5 | 170.9 | Unknown | Unknown |
| `codex/gpt-6-astra` | ultra | 0/5 | 4 | 170.7 | Unknown | Unknown |
| `codex/gpt-6-astra` | xhigh | 0/5 | 5 | 171.4 | Unknown | Unknown |
| `codex/gpt-6-luna` | medium | 5/5 | 0 | 75.5 | 75.5 | 0.00458 |
| `codex/gpt-6-sol` | medium | 5/5 | 0 | 133.2 | 133.2 | Unknown |
| `codex/gpt-6.1-sol` | high | 0/5 | 5 | 170.9 | Unknown | Unknown |
| `codex/gpt-6.1-sol` | low | 5/5 | 0 | 163.4 | 163.4 | 0.09528 |
| `codex/gpt-6.1-sol` | max | 0/5 | 5 | 170.8 | Unknown | Unknown |
| `codex/gpt-6.1-sol` | medium | 1/5 | 4 | 170.8 | 854.1 | Unknown |
| `codex/gpt-6.1-sol` | ultra | 0/5 | 5 | 170.9 | Unknown | Unknown |
| `codex/gpt-6.1-sol` | xhigh | 0/5 | 5 | 171.0 | Unknown | Unknown |
| `codex/gpt-reserve` | medium | 5/5 | 0 | 113.1 | 113.1 | Unknown |
| `codex-glm/glm-5.3` | high | Unavailable | — | — | — | — |
| `grok/grok-4.5` | high | 5/5 | 0 | 90.6 | 90.6 | 0.19932 |
| `grok/grok-4.6` | high | 0/5 | 3 | 171.2 | Unknown | Unknown |
| `grok/grok-4.7` | high | 0/5 | 0 | 170.6 | Unknown | Unknown |
| `grok/grok-4.7-build-fast` | high | 0/5 | 1 | 171.0 | Unknown | Unknown |

Rows with fewer than five graded attempts remain provisional. The quality/time descriptive frontier among eligible rows is `codex/gpt-6-luna` (medium), `builtin/deepseek-flash` (high). Five trials provide wide uncertainty: even 5/5 passes has a 95% Wilson interval of approximately 57–100%. A frontier label is not evidence of statistical superiority.

## RZ results

One attempt per configuration; no Pareto ranking. Reported time is complete trial elapsed time, including failed verification/continuation, rather than pure inference latency.

| Coding agent / model | Effort | Result | Seconds | Input tokens | Output tokens |
|---|---|---|---:|---:|---:|
| `agy/claude-opus-4-6-thinking` | default | Unavailable; no inference | 890.8 | Unknown | 0 |
| `agy/claude-sonnet-4-6` | default | Quota interrupted after inference | 893.8 | Unknown | 6413 |
| `agy/gemini-3.1-pro-high` | high | Pass | 276.9 | Unknown | 26532 |
| `agy/gemini-3.1-pro-low` | low | Pass | 231.8 | Unknown | 20932 |
| `agy/gemini-3.6-flash-high` | high | Pass | 480.1 | Unknown | 41817 |
| `agy/gemini-3.6-flash-low` | low | Pass | 292.2 | Unknown | 32398 |
| `agy/gemini-3.6-flash-medium` | medium | Pass | 375.1 | Unknown | 41759 |
| `agy/gemini-3.7-flash-high` | high | Pass | 260.4 | Unknown | 47050 |
| `agy/gemini-3.7-flash-low` | low | Pass | 136.8 | Unknown | 18910 |
| `agy/gemini-3.7-flash-medium` | medium | Pass | 188.1 | Unknown | 38458 |
| `agy/gemini-3.8-flash-high` | high | Pass | 341.1 | Unknown | 65458 |
| `agy/gemini-3.8-flash-low` | low | Pass | 396.3 | Unknown | 30355 |
| `agy/gemini-3.8-flash-medium` | medium | Pass | 293.8 | Unknown | 52754 |
| `agy/gpt-oss-120b-medium` | medium | Incomplete numerical contract | 893.8 | Unknown | 60849 |
| `builtin/deepseek-flash` | high | Pass | 114.1 | 604610 | 21400 |
| `builtin/deepseek-v4-pro` | high | Pass | 303.3 | 941416 | 33031 |
| `builtin/mimo-v2.6-flash` | high | Incomplete numerical contract | 891.2 | 87277 | 17414 |
| `builtin/mimo-v2.6-pro` | high | Incomplete numerical contract | 891.1 | 490030 | 41057 |
| `codex/gpt-5.5` | medium | Pass | 253.7 | 617490 | 10743 |
| `codex/gpt-5.6-luna` | medium | Pass | 397.1 | 1052412 | 15217 |
| `codex/gpt-5.6-sol` | low | Pass | 179.6 | 333359 | 8096 |
| `codex/gpt-5.6-terra` | medium | Pass | 250.4 | 596526 | 10084 |
| `codex/gpt-6-astra` | high | Pass | 457.5 | 273728 | 13969 |
| `codex/gpt-6-astra` | low | Pass | 287.0 | 279421 | 8413 |
| `codex/gpt-6-astra` | max | Pass | 681.6 | 414828 | 21111 |
| `codex/gpt-6-astra` | medium | Pass | 403.9 | 259289 | 12124 |
| `codex/gpt-6-astra` | ultra | Pass | 661.0 | 451263 | 20008 |
| `codex/gpt-6-astra` | xhigh | Pass | 644.9 | 515459 | 19430 |
| `codex/gpt-6-luna` | medium | Pass | 271.6 | 452619 | 8467 |
| `codex/gpt-6-sol` | medium | Pass | 210.9 | 343598 | 9419 |
| `codex/gpt-6.1-sol` | high | Pass | 545.0 | 279217 | 16453 |
| `codex/gpt-6.1-sol` | low | Pass | 276.3 | 254293 | 7844 |
| `codex/gpt-6.1-sol` | max | Pass | 813.3 | 500287 | 24012 |
| `codex/gpt-6.1-sol` | medium | Pass | 378.5 | 255825 | 11268 |
| `codex/gpt-6.1-sol` | ultra | Pass | 645.2 | 508336 | 19577 |
| `codex/gpt-6.1-sol` | xhigh | Pass | 698.8 | 531080 | 21377 |
| `codex/gpt-reserve` | medium | Pass | 237.0 | 476712 | 9160 |
| `codex-glm/glm-5.3` | high | Unavailable; no inference | 892.5 | Unknown | Unknown |
| `grok/grok-4.5` | high | Pass | 419.1 | 801689 | 27503 |
| `grok/grok-4.6` | high | Pass | 437.1 | 841222 | 29647 |
| `grok/grok-4.7` | high | Numbers pass; findings missing | 894.4 | 635187 | 61807 |
| `grok/grok-4.7-build-fast` | high | Numbers pass; findings missing | 897.8 | 1538883 | 96637 |

## Availability and accounting

The operator confirmed GLM should remain unavailable for this sweep; its Coding Plan had expired. AGY also reported explicit individual quota exhaustion for some profiles, including later repetition attempts. Those observations are preserved but do not become numerical failures in the leaderboard. A quota interruption after positive inference is labelled separately and retains the incomplete attempt and its known usage.

| Agent / model | No-inference attempts | Reason |
|---|---:|---|
| `agy/claude-opus-4-6-thinking` | 5 | Provider quota exhausted - no successful inference |
| `agy/claude-sonnet-4-6` | 4 | Provider quota exhausted - no successful inference |
| `agy/gemini-3.1-pro-high` | 1 | Provider quota exhausted - no successful inference |
| `agy/gemini-3.6-flash-high` | 1 | Provider quota exhausted - no successful inference |
| `agy/gemini-3.7-flash-high` | 1 | Provider quota exhausted - no successful inference |
| `agy/gemini-3.8-flash-high` | 1 | Provider quota exhausted - no successful inference |
| `agy/gemini-3.8-flash-low` | 1 | Provider quota exhausted - no successful inference |
| `agy/gpt-oss-120b-medium` | 4 | Provider quota exhausted - no successful inference |
| `codex-glm/glm-5.3` | 6 | Coding subscription expired - no successful inference |

AGY conversation totals are cumulative, so they are never summed across resumes. A terminal zero-usage quota error must not erase earlier paid-work counters. Its input/cache semantics remain undocumented; total billed input and token cost stay unknown. Codex uses cumulative native session receipts; Grok uses deduplicated message receipts, with resumed or partial streams marked incomplete. API-agent receipts are recorded per request. Missing counters are not treated as zero.

Token USD is a dated standard-rate estimate, not actual subscription spending. Native CLI profiles and API agents can have different pricing and context tiers. A complete estimate requires complete usage and a supported rate/tier. The UI preserves unknown cost rather than inventing an invoice.

## Interpretation and limits

1. Higher reasoning effort was often a poor fit for the short CSV deadline. Many failures already passed every public/holdout numerical check but missed findings or complete delivery. The same high-effort Codex configurations passed RZ with the longer budget. This supports a deadline/effort interaction, not a general ranking of model intelligence.
2. DeepSeek Flash and Pro both passed the repaired RZ contract. MiMo Flash and Pro did not deliver the required bounded reducer in the tested API-agent configuration. This is a whole-agent result: DeepSeek uses native tool-message history, while MiMo retains the installed smolagents default formatter. Both use 8192 output tokens per request and 24 action steps per episode, with timed continuation. A different MiMo adapter or budget requires a new cohort.
3. The tasks use a fixed recorded dataset with varied synthetic numerical holdouts. Repetitions measure stochastic agent delivery on that task, not generalization to independent scientific problems. Native agents are cooperative and retain broad tools; this is not a cheating-resistant public competition.
4. Concurrent workers and shared provider quotas affect elapsed time. The hardware/protocol fingerprints separate comparison groups, but there is no claim of isolated latency or provider-load control. Some AGY rows lack five valid attempts because the subscription quota expired during the sweep.

## Verifier qualification and repairs

Before the formal sweep, real agents exposed two reference defects. Pack 0.1.0 depended on ambiguous ordering of cells at an equal radius. Pack 0.2.0 multiplied float32 fields before promoting to float64. Independent DeepSeek and Grok reducers agreed with each other but could be rejected by the old reference.

Pack 0.3.0 aggregates masses at distinct exact radii and specifies interpolation explicitly. All reductions promote fields to float64 before arithmetic. Independent closed-form volume/energy tests, equal-radius permutation tests and scalar `math.fsum` checks validate these definitions. The former workers’ float64 curves agree exactly with the repaired reference for both recorded cases.

The eight initial qualification observations and 53 completed observations from the interrupted pack-0.2 sweep are bundled separately. Affected RZ records remain unranked in the audit archive; they were not silently regraded or counted as fresh model passes. Qualification CSV records retain their original pack/protocol cohort. The formal results above come from fresh pack-0.3 trials.

The formal sweep used frozen runner `native-public-feedback-v3`; source fingerprints are in each receipt. A publication audit corrected availability classification and AGY zero-reset accounting while preserving original private host grades and their source hashes. The next runner (`native-public-feedback-v4`) detects these errors directly, distinguishes temporary rate limits, exposes partial-inference quota interruptions, and preserves a selected virtualenv interpreter’s path.

## Reproduce and contribute

Download sanitized grades from **Benchmarks → Download grades**, then run:

```bash
simjecture llm-benchmark leaderboard --reports simjecture-benchmark-grades.json --output summary.json
```

The configuration identities, task repeats, protocol and environment versions are bundled with the owned grades. Use **Run your model** or the timed CLI runner for fresh attempts; importing a report does not create a new repetition. A community submission adds sanitized grades under [results/community](https://github.com/tomzhu0225/simjecture/blob/v0.5.3rc3/src/conjecture_solver/llm_bench/results/community/README.md) through a pull request. Contributor-declared records use `community-controlled` groups, separate from owned measurements.

## Validation

The broader repository run passed 858 tests with seven environment-dependent skips.
After the final CLI bundle and shipped-audit import changes, all 35 focused
leaderboard/runner checks passed. The numerical controls passed independently.
Ruff, JavaScript syntax, public-schema verification and the strict Sphinx build
passed. A real GUI-launched custom-model trial completed successfully; the final
desktop/mobile browser check verified owned CSV/RZ counts, downloaded sanitized
grades, opened the custom-model dialog and reported no JavaScript errors or mobile
document overflow. The downloaded bundle also reproduced its CLI summary.
