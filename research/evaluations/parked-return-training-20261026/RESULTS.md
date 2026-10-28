# Parked workflow commissioning results

The collector recorded nine sampled decisions during a real worker's parked
interval, and both assigned workflows produced independently verified reports.
Offline export now passes all execution checks. This commissions the collection
path; it does not demonstrate an intervention benefit or supply training data.
No optimizer ran and no new weights were produced.

The [prospective protocol](PROTOCOL.md) was frozen before execution. The
[evidence bundle](commissioning-evidence.json) retains the plan, adapter
qualification, episode measurements, all nine decision/admission summaries,
physical receipt hashes, original export error and corrected export provenance.
The original source was `f68935348a203513d06a6a9b0147475cebcea0ea`.

## Actual execution

| Assignment | Verified report | Elapsed seconds | Native starts | Sampled decisions | Automatic dispatches |
| --- | --- | ---: | ---: | ---: | ---: |
| No automatic attention | Yes | 489.55 | 6 | 0 | 0 |
| SFT512 policy, sampled at temperature 3 | Yes | 220.05 | 2 | 9 | 0 |

Each workflow executed both real WarpX controls on the P40. All four physics
receipts succeeded. The model ran on the remote A100; no local inference,
training or simulation was used. The released runtime reproduced the original
adapter's two saved probes after converting their temperature: maximum
probability discrepancy was below `1.3e-7` against a `1e-4` tolerance.

All nine requests had recorded responses, occurred inside the recorded parked
interval and did not overlap an active main-worker invocation. The sampled
worker resumed on the ordinary terminal event. The control also used the
ordinary fallback and returned-attention paths; worker-requested assistance
remained available. These were separate native episodes, not a shared private
worker trajectory.

Five model outputs proposed observation. Two proposed waking the director: one
was held because the declared silence allowance had not expired, and one
required rechecking because the observed state had changed. Two other outputs
requested a knowledge helper without specifying a question. The output
contract rejected both. These were invalid sampled combinations, not inference
transport failures. No automatic proposal dispatched assistance in either arm.

The first measured model call took 10.70 seconds; the following eight took
0.43–0.45 seconds each. Their total was 14.22 seconds for 43,334 input tokens
across nine calls. These are end-to-end model scoring measurements on this
A100, not isolated forward time, billing costs or a local-device benchmark.

## Export repair and verification

The original exporter failed after execution with `KeyError: 'forward_seconds'`.
It incorrectly expected the older monitor model's timing field in a
`DecisionModel.predict()` result, which supplies only total scoring time. The
integration fixture also included that nonexistent field and therefore missed
the bug. This defect belongs to this experimental implementation in PR 70.

The corrected exporter records only measured inference count, input tokens and
total scoring time. The integration test now uses the actual timing schema.
Export ran offline into a new directory using the saved observations and
receipts. No scientific episode or model call was rerun. Before/after hashes
confirm that the original plan, campaign, native budget and controller failure
record were unchanged. The corrected `READY.json` reports two verified episodes
and nine decisions, with `split=commissioning` and optimizer eligibility false.
The original failed export is retained.

The updated package passes 235 tests and Ruff. A separate trainer correction
normalizes the row-averaged loss to the number of sampled episodes, including
episodes with zero decision opportunities. It was not deployed into the frozen
commissioning run and has not yet been exercised by a real optimizer update.
The A100 was released, native invocations are closed and temporary access
credentials were removed.

## What this says about reward design

The declared utilities are 0.92615 for the sampled episode and 0.80469 for its
control. Subtracting them gives +0.12146, despite zero automatic dispatches.
That difference cannot identify an intervention effect. Independent worker
trajectories vary, and monitoring can itself affect timing. This one pair does
not estimate the size or direction of either effect.

If a training episode received such a positive advantage, the current episodic
surrogate would increase the likelihood of all its sampled choices, including
the ineffective and invalid ones. A likelihood-ratio episodic estimator is not
invalid merely because one trajectory has noisy credit. However, this result
shows why a small cohort and a configuration-level wait mean can provide a poor
learning signal. Nine correlated polls do not provide nine independent returns.
The commissioning split prevents this example from entering the optimizer.

Before scaling updates, the next design should address two different problems:

- Restrict exploration to combinations allowed by the public action contract.
  For example, a knowledge request must reference an available question. Use the
  same constrained distribution and its normalization in sampling, probability
  replay and training. This handles output consistency; it does not establish
  that a scientifically valid alert was useful.
- Reduce return variance with repeated randomized episodes and a baseline based
  only on information available before a decision. Compare reward-to-go with
  the current whole-episode return, and keep baseline fitting separate from its
  evaluated episodes. Do not declare zero dispatch proof of zero timing effect,
  discard inconvenient episodes or invent per-action usefulness labels.

A subsequent study must still demonstrate improved verified work or cost on
fresh scientific tasks, against both worker-only and frozen strong baselines,
while measuring false alerts per complete healthy episode. The earlier
28-workflow comparison remains unchanged: it did not establish an RL advantage
or a reliable timing advantage over rules.


## Prospective collector configuration after control qualification

The original two-episode commissioning result above is unchanged. A separate
[no-model control pilot](../live-state-learning-20261026/FOLLOWUP_CONTROLS.md)
exposed a four-turn experiment limit and subsequently qualified six workflows
with task-focused instructions and up to twelve parent turns, still inside the
same 650-second and twelve-total-native-start ceilings.

The return collector now accepts explicit `--worker-prompt`,
`--parent-turn-limit`, `--maximum-parallel-workflows` and
`--minimum-gap-seconds` settings. Historical defaults remain inherited prompts,
four turns, two parallel workflows and no gap. A prospective qualified-host
configuration uses `task_protocol`, twelve turns, one workflow and a 90-second
gap. These choices are frozen in the plan and host-context hash; changing them
produces disjoint episode IDs. Lease admission accounts for serial execution
and every gap. An interrupted serial cohort retains failed and unstarted IDs.

For new plans, export verifies actual turn limits/counts, the task-protocol
receipt against task text and registered renderer hash, and measured controller
intervals against concurrency and spacing. Exported episodes retain these
execution identities. Legacy datasets can still be read without retroactively
inventing those receipts. These additions do not turn old commissioning rows
into optimizer data or change the reward formula.

Twenty-eight collector/return tests pass, including serial failure preservation,
complete-cohort-only training export, both action distributions, changed prompt
rejection, resumption-limit mismatch, and concurrency/gap violations. These tests
use process doubles; native sampling with this revised collector still requires
its own commissioning before training.


C12 was subsequently [registered](../live-state-learning-20261026/sampling-commission-c12-registration.json)
and [launched](../live-state-learning-20261026/sampling-commission-c12-launch.json)
on a newly owned remote A100. Read-only validation against all six actual pilot
records passed, then both fresh P40 controls and native authentication passed.
The first allocation POST failed without an endpoint; an account reconciliation
found no assigned runtime and unchanged observed balance. One recorded retry on
the same isolated route succeeded. The original C12 deadline and credit ceiling
were retained. No proxy configuration or global node was changed.

At this launch snapshot the model was being deployed, so new native sampling,
probability qualification and collection export were still pending. The launch
receipt is not a completed experiment. The six prospective IDs remain separate
from every earlier pilot and the original 64-workflow comparison.


The first C12 deployment then exceeded its 240-second asset-upload timeout.
A metadata observation shortly beforehand showed 222,363,648 of 240,457,000 bytes
transferred. No model preparation, inference or scientific assignment began;
the native-workflow counter stayed zero. The controller stopped, the remote
guard released its owned endpoint, and the temporary local control task was
removed. Fresh account reconciliation showed no assigned runtime and 1,106.11 CU,
a 0.56-CU observed decrease from the phase baseline, subject to billing lag.

[C13 replacement evidence](../live-state-learning-20261026/sampling-commission-c13-replacement.json)
retains this failure and the replacement plan. The payload now includes only the
continued-SFT adapter needed for this commission: 120,562,046 compressed bytes.
Its adapter/configuration bytes match the original hashes exactly; the unused RL
adapter was excluded. The transfer bound is 600 seconds, still within the same
parent phase deadline. The six original IDs, scientific source, sampler, model,
native-start ceiling, 08:49:37 UTC deadline and cumulative 20-CU ceiling remain
unchanged. No scientific attempt was rerun. The replacement runtime is separately
owned and guarded; this record establishes launch, not completed qualification.


The smaller deployment subsequently completed. The fresh A100 loaded the pinned
base and continued-SFT adapter, and all [three saved probability probes](../live-state-learning-20261026/sampling-commission-c13-model-qualification.json)
passed before native collection: maximum discrepancies were `1.90e-8`, `2.84e-8`
and `6.19e-8` against the unchanged `1e-4` tolerance. Actual prompt hashes matched.
The collector then entered the registered commissioning campaign using the
constrained distribution. At this saved qualification snapshot it was waiting
through the initial 90-second gap; scientific outcomes were not yet available.


## Completed C12/C13 native sampling commission

All six assigned workflows completed verified scientific reports; all twelve
physical solver receipts succeeded. There were no missing required feedback
acknowledgments, duplicate wakeups, malformed sampled proposals or unstarted
assignments. Collection/export checks passed for twenty decisions across three
sampled episodes. The commissioning split remains optimizer-ineligible by design.
The [terminal evidence](../live-state-learning-20261026/sampling-commission-c13-completed.json)
retains every episode, proposal/admission, actual alert, measured utility and
accounting record. No training update ran.

| Mechanism | No automatic attention: seconds / native starts | Sampled SFT: seconds / native starts | Actual automatic action |
|---|---:|---:|---|
| Unit conversion | 263.20 / 3 | 266.50 / 5 | Wake director once |
| Healthy progress | 167.54 / 2 | 151.65 / 2 | None |
| Protected source binding | 389.10 / 6 | 369.62 / 8 | Wake director once |

The descriptive mean is 262.59 seconds for sampled SFT versus 273.28 for waiting,
a 3.91% reduction, with fifteen versus eleven total native starts. One pair per
configuration cannot establish a repeatable efficiency advantage. The healthy
pair differs in elapsed time despite zero automatic dispatches in both arms;
its difference cannot be attributed to a successful intervention. The protected
sampled workflow used five parent turns and completed, exercising the revised
resumption path with real model decisions in the loop.

The policy proposed `wake_director` sixteen times and `observe` four times.
Only two wake proposals dispatched. In the healthy episode, eight of nine samples
proposed waking: six were rejected as ungrounded and two did not establish
persistence. Zero actual healthy wakes therefore reflects the host gate and is
not evidence that the learned policy has solved false alerts. These nine polls
are one correlated trajectory, not a measured deployment false-positive rate.

An [offline decoder audit](../live-state-learning-20261026/sampling-commission-c13-decoding.json)
reused the saved probabilities without model execution. Both independent and
contract-constrained greedy decoding would select director on five of the nine
healthy observations, versus eight sampled choices. Thus sampling contributes,
but deterministic decoding alone does not remove the proposal problem on this
trace. These are alternative choices on stored states, not executed alternative
workflows or counterfactual dispatch/timing outcomes. The structural decoder
eliminated missing-question combinations in this run; that is a different
criterion from scientifically warranted attention.

The twenty scoring calls consumed 93,753 input tokens and 29.888 seconds in
aggregate. The first two unit-conversion calls took 11.117 and 11.106 seconds;
subsequent calls took 0.301–0.455 seconds. Three prior reference probes had passed,
so reference-probe warmup alone did not remove these early delays. Their cause
is not established by these records. The costs remain in the measured outcomes.

Initial and terminal base/SFT reproduction checks all passed with maximum
probability discrepancy `6.19e-8`. All 26 workflow native starts closed; with
authentication the phase used 27 of its 73-start ceiling. The owned A100 was
released automatically at 07:50:08 UTC (15:50 China time), before its deadline.
The expiring local control task was removed and the local failsafe acknowledged
release. Recorded balance decreased by 4.79 CU from the phase baseline, including
the failed deployment and recovery; this is observed accounting, not a final
itemized billing statement.

The next model-development priority is reducing unsupported and premature wake
proposals while retaining sensitivity to actual diagnostic faults. Training
examples should include realistic healthy trajectories and genuinely ambiguous
states; development/test episodes and measured workflow returns must remain
separate. This commission validates the collection path and exposes that target;
it does not authorize relabelling its commissioning rows as training returns.
