# Native review of live scientific observations

All 12 assigned auditor calls completed, producing two judgments for each of
24 saved observations. The reviewers selected the same preferred route in
20 cases. Their acceptable-route sets overlap in all 24. Four observations
remain uncertain and are retained for review. These are separate contexts of
the same native model, not independent human judgments or causal intervention
labels. No judgment has entered an optimizer.

The [evidence bundle](observation-evidence.json) retains the frozen assignments,
exclusion reasons, every successful judgment and all 15 native attempts,
including three provider failures. Prompt/schema hashes, candidate/citation
binding, recovery assignment links and the absence of auditor tool use pass
the postprocessor. The audit is complete; optimizer eligibility remains false.

Three older first observations labelled their worker active after it had
parked. They were excluded before auditing, with their hashes and reasons
retained. The independent snapshot fix is [PR 73](https://github.com/tomzhu0225/simjecture/pull/73).
No source workflow, scientific output or original decision was rewritten.

After the original audit lease ended, a separate bounded recovery phase used
the remaining ten starts under the original overall 18-start ceiling. It kept
all outstanding assignments and prompts unchanged and imposed 180 seconds
between completed calls. Seven calls completed without further provider errors;
the combined audit used 15 starts. Earlier failures remain visible. This reports
what happened and does not identify the cause of the intermittent 429 errors.

The uncertain cases concern an initial calibration overshoot, an oscillating
update near the ordinary wake boundary, and whether artifact-selection evidence
justifies immediate assistance or a bounded recheck. These alternatives matter:
a reasonable decision need not have a unique route label. The 90-second fallback
is present in the original declared-task evidence, so this contextual information
was available in the model view as well as the auditor instructions.

## Earlier failed scoring attempt

The separately registered four-checkpoint A100 scoring attempt restored its
assets and passed the small convolution/gradient check. It then failed a saved
adapter probability reproduction check before scoring any of the 96 assigned
model/observation pairs. There are no valid new model scores from that attempt.
The runtime was released and its status, preparation metadata and kernel result
were preserved off-runtime.

The first runner saved the qualification table only after every probe passed,
so the offending probability vector was not retained. That limits diagnosis.
The subsequent diagnostic saved every probe before checking its tolerance,
verified loaded adapter tensors, and qualified the primary base/SFT execution
path before using it for comparisons. The earlier failure is not a scientific
performance result for either method; its root cause remains unidentified.

## Qualified base versus continued-SFT decisions

The subsequent remote A100 run completed all 48 assigned predictions: the same
24 recorded scientific observations, scored with the unadapted pretrained base
and the exact continued-SFT checkpoint used in the 223.9-second workflow result.
Both use temperature 1, the same input/compiler and independent field decoding.
There were no inference errors or optimizer updates.

All 496 loaded adapter tensors match the saved checkpoint exactly. Disabling
the adapter reproduces the pre-adapter base probe with zero probability error.
Both saved SFT probes reproduce before and after scoring, with maximum absolute
probability discrepancy below 2.85e-8 against the unchanged 1e-4 tolerance.
A duplicate named copy of the same adapter also reproduces those probes. Thus
named selection by itself is not sufficient to explain the earlier failed run.

| Recorded-state measure | Pretrained base | Continued SFT |
|---|---:|---:|
| Route acceptable to both reviewers | 16/24 | 18/24 |
| Route acceptable to both, excluding four uncertain states | 13/20 | 16/20 |
| Correct route on seven states where both require an expert | 0/7 | 5/7 |
| Any expert route on those seven states | 0/7 | 7/7 |
| Expert proposals on eleven states where both accept only observing | 0/11 | 2/11 |

The base selects `observe` in all 24 cases. SFT recognizes the persistent update
loop, artifact-consumer problem, and three unit-conversion snapshots. It routes
the two protected source-binding defects to the director, whereas both reviewers
require the repair judge. Its two proposals on unanimous observe-only states
concern a publication retry and a progressing commissioning job. On a third
disputed state near the ordinary wake boundary, SFT proposes help that only one
reviewer accepts.

SFT therefore changes useful detection behavior and introduces unnecessary-
attention candidates. The net gain on the two-reviewer route criterion is two
states: five improved and three worsened, with sixteen unchanged. This is a
small, correlated development sample from eight earlier episodes, judged by two
contexts of the same large model. It is not 24 independent workflow outcomes,
an estimate of a deployment false-alert rate, or proof of causal time savings.
The unanimous-observe diagnostic is supplementary, not a new training target.

These scores also have a narrower meaning than the earlier authored test's
54.0% to 97.5% improvement. That test measures the authored scientific contract
and routing targets; this audit measures reviewer acceptance of routes on
actual recorded states. Their percentages are not directly interchangeable.

Median forward-call time was 0.268 seconds for base and 0.409 seconds for SFT on
this A100; inputs ranged from 3,200 to 4,964 tokens. These are component timings,
not complete-workflow timings. The runtime was released after preserving all
outputs. The recorded compute balance decreased by 0.21 units during this
allocation; billing can lag, so this is not a final metered cost.

## Primary research question

The practical target is a useful scientific coprocessor, whichever training
method achieves it. RL superiority over SFT is not a release requirement.
The earlier clean cohort's continued-SFT mean of 223.9 seconds versus 277.2 for
worker-only execution is a promising observed reduction of about 19%. Its
rule comparison and the limited replication still require caution.

That cohort omitted the unadapted pretrained base model. A fresh repeated
workflow comparison must make base versus the exact continued-SFT checkpoint
its primary post-training comparison, while retaining worker-only execution
and strong rules as deployment references. Keep scientific tasks, workers,
permissions, decoding policy, hardware and budgets matched. Existing frozen
checkpoints can answer this question without another optimizer update. The
previously reported cohort remains exploratory and is not retrospectively
relabelled as a confirmatory SFT study.
