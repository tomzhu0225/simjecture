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

## Model scoring status

The separately registered four-checkpoint A100 scoring attempt restored its
assets and passed the small convolution/gradient check. It then failed a saved
adapter probability reproduction check before scoring any of the 96 assigned
model/observation pairs. There are no valid new model scores from that attempt.
The runtime was released and its status, preparation metadata and kernel result
were preserved off-runtime.

The first runner saved the qualification table only after every probe passed,
so the offending probability vector was not retained. That limits diagnosis.
The next diagnostic runner must save every probe before checking its tolerance,
verify loaded adapter tensors, and qualify the primary base/SFT execution path
before using it for comparisons. The failure is not a scientific performance
result for either method.

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
