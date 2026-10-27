# Scientific action-constraint audit

The optional constrained decoder removes invalid route/question combinations
and now uses the same normalized distribution in serving, collection, replay
and the RL objective. Its gradient checks pass. This is a contract and
implementation result, not improved scientific decision quality or a workflow
win. No model inference, optimizer update or simulation ran in this audit.

The [decoding profile](../../../packages/simjecture-monitor/specs/scientific-attention-0.2-draft/DECODING.md)
defines the reusable interface and probability calculation. The
[evidence bundle](evidence.json) retains the saved-trace projection, the remote
tensor-test report and source fingerprints. It analyzes the nine observations
from the earlier [parked commissioning](../parked-return-training-20261026/RESULTS.md),
whose original outcomes remain unchanged and excluded from training.

## Recorded probabilities and projected choices

All nine original independent draws replay exactly, including their original
log probabilities. The original trace has two invalid knowledge-helper requests
with no question. Joint constrained sampling produces nine structurally valid
choices from the same stored field probabilities and seeds. Those choices were
not executed. Their different random-number consumption also means that the
projected draws are not a paired estimate of policy effectiveness.

| Offline quantity across these nine observations | Value |
| --- | ---: |
| Original invalid sampled outputs | 2 of 9 |
| Projected invalid sampled outputs | 0 of 9 |
| Mean probability mass on invalid route/question combinations before conditioning | 17.74% |
| Mean probability of a structurally valid expert proposal before conditioning | 40.78% |
| Mean probability of an expert proposal after conditioning | 49.57% |

These are temperature-3 exploration distributions from one progressing-work
episode. They are not calibrated alert probabilities, independent episodes or
population estimates. Expert proposal means worker help, director or repair
judge; it does not mean admission or actual dispatch. Conditioning increases
expert-proposal mass here, so structural validity alone cannot be advertised as
a false-alert reduction. No report outcome or utility is assigned to the offline
projected choices.

## Verification

The lightweight package suite passes 243 tests. Its optional tensor-test module
is skipped locally because PyTorch is absent. Both tensor tests pass separately
on the remote CPU coordinator using PyTorch 2.11.0+cpu, Pydantic 2.14.1 and
pytest 9.1.1, with no CUDA available. They use five-by-ten toy logits, not model
weights. They compare constrained log probabilities and KL against full
five-field enumeration, check finite-difference gradients, and verify zero
gradient on impossible knowledge routes when no question exists. Ruff passes.

Contract tests cover both question-present and question-absent observations,
unchanged legacy draws/general fields, zero valid probability, changed decoder
receipts, unbound questions, and both distributions through collection/export.
The trainer also checks the selected constrained action probability during its
initial behavior replay. A real A100 training update through this path remains
unverified; the mathematical checks do not substitute for it.

## Remaining learning problem

The earlier commissioning pair gave a positive relative workflow return despite
zero automatic dispatches. The new decoder does not repair that noisy credit
assignment. Next work should record costs at decision times, compare
reward-to-go with whole-episode returns, and use repeated controls with an
action-independent baseline. The baseline must not use the evaluated action or
future outcome from its own episode.

Removing pre-action rewards and using a state-dependent baseline are established
policy-gradient methods; [the Spinning Up derivation](https://spinningup.openai.com/en/latest/spinningup/rl_intro3.html)
explains their expected-gradient and variance properties. Whether they reduce
variance enough in this scientific environment still requires measurement.
No new efficacy claim or model release is supported by this decoder audit.
