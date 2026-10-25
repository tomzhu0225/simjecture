# Autonomous coprocessor exploration: 24 October 2026

The full small-model → independent judge → scoped repair → original-worker
continuation loop works on real WarpX tasks. A model advantage over simple rules
is still unproven, and the existing LoRA has shown no new action improvement.
The strongest new results are a better experiment/reward contract, faster local
inference, and an actual correction to alert-deferral bookkeeping.

The subsequent [25 October comparison](../monitor-generalization-20261025/RESULTS.md)
tests frozen generic rules and the model on additional raw diagnostic mechanisms,
with healthy controls, real worker continuations and 48 identical-input base/LoRA
predictions. It reports collector-censored outcomes separately from a corrected
completion follow-up. The figures below retain the scope of the 24 October stage.

## What the real workers showed

| Study | Main trajectories | Finding |
|---|---:|---|
| [Public-checkpoint continuations](../monitor-paired-20261024/RESULTS.md) | 32 | All numeric reports correct; extra prescribed attention used 48 starts versus 33 for waiting. Mean operational value −0.0207; strict rewards withheld for five pairs with unknown feedback need. |
| [Parked worker: observe/rules/model](../monitor-parked-20261024/RESULTS.md) | 12 | Model fault runs took 116–120s versus 217–246s for observe-only; rules were faster at 99–107s. Demonstrates a wakeup opportunity, not ML superiority. |
| [Required/advisory helper handoffs](../monitor-help-feedback-20261024/RESULTS.md) | 4 | Required workers imported and acknowledged real helper artifacts. Advisory workers could finish without another turn solely for optional advice. |
| [Reference/fast runtime](../monitor-kernels-20261024/RESULTS.md) | 8 | Fast fault runs dispatched while parked; reference repeats waited for fallback. One fast run made a stale second request, denied by the judge. Fresh histories differ. |
| [Timed observations](../monitor-timer-20261024/RESULTS.md) | 8 | No actual timer event was delivered: fault requests occurred earlier and healthy workers resumed quickly. This cohort does not establish a timer benefit. |

All 64 reports in these main cohorts met independent numeric accuracy and
configuration-coverage checks. That is reporting success, not scientific approval
of every diagnosis. The known injected mechanisms, tiny per-condition samples,
shared GPU and public-context replays limit generalization and causal claims.
Commissioning and prefix workers are tracked separately in the native ledger.

Separate grace-period commissioning exposed an integration bug: host-deferred
alerts had already consumed cooldown, so later correct model requests were
blocked. Both original runs remain recorded. After the fix, one corrected timed
check exercised the complete loop in 118 seconds/four native starts, with no
fallback, duplicate wake or required-feedback miss. It is a mechanism validation,
not a randomized improvement estimate. Raw model choice, host override and actual
execution now have separate auditable provenance.

## What changed

- A checkpoint collector and incident/feedback ledger support real wait/intervene
  continuations and withhold strict rewards when measurements are unknown.
- Optional `feedback_requirement='required'|'advisory'` is frozen before help
  dispatch; an operator can require it. Legacy omitted-field hashes remain
  compatible. This records obligation, not objective help usefulness.
- A bounded elapsed-time observer can revisit quiet parked streams. Deferred
  alerts can release their unused cooldown reservation without erasing a newer
  alert's reservation. Default production monitoring remains disabled.
- An opt-in FLA-prefill runtime reduced warm retained-packet latency from 3.794 s
  to 2.220 s, a 1.71x speed ratio, with unchanged weights and 16/16 probe choices.
  Floating-point probabilities changed by up to 1.51 percentage points; this is
  not a LoRA gain or calibrated confidence. A later identical-input replay of
  sixteen live observations also agreed on 32/32 choices. Its validated scope is
  inference, not training backpropagation.

The pinned baseline remains `internlm/Intern-Decision-4B`. Base and existing V1
LoRA chose the same actions on all eight new frozen checkpoints; the largest
probability shift was about 1.53 percentage points. No new adapter was trained in
this stage: the prescribed/greedy cohorts are not sampled PPO data, and the
mechanism families are not a task-disjoint test set.

## Practical decision

Keep this work in the isolated monitor package and draft [PR46](https://github.com/tomzhu0225/simjecture/pull/46).
Use deterministic checks for explicit process/receipt invariants. The 4B research
target is ambiguous streaming evidence while a worker is busy or parked, with
incident deduplication, declared feedback obligations and measured interruption
costs. Research planning stays with the director; repair permission stays with a
fresh independent judge. Neither role needs to be delegated to the coprocessor.

[The literature review](REVIEW.md) and [next-data design](NEXT.md) explain how to
collect held-out incidents, sampled behavior probabilities and actual downstream
value before another LoRA. The tested 4B training configuration already fit within
12.16 GiB peak allocated CUDA memory on the earlier A100 run; useful new data and
reward attribution are the present constraints.

All 229 experimental native starts ended under the 240 cap, with at most four
reserved roles concurrently, and the native lease is closed. No Colab runtime
was allocated in this stage. At 01:23 UTC the live CLI showed 1229.53 compute units,
zero usage/hour and no active Colab assignments or sessions. Raw plots, traces,
weights and process receipts stay
local; compact audits, protocols, figures and reproduction instructions are in
Git and indexed in the personal knowledge library. The monitor contract suite
passes 60 tests locally; the PR links the full required CI checks.
