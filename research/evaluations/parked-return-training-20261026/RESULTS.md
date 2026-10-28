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
