# Faster decisions at unchanged weights, with a live reliability limit

The optional FLA-prefill runtime reduced warm retained-packet decision latency
from 3.794 to 2.220 seconds, a 1.71x speed ratio, on the shared local RTX 4000 Ada.
It kept all sixteen probe choices unchanged. This is an inference improvement,
not a new LoRA or a demonstrated improvement in learned decision quality.

Eight fresh live worker trajectories then completed with independently verified
numeric reports. Both faster-runtime fault runs obtained a judge while parked;
both reference-runtime fault runs deferred until the 90-second worker fallback.
Fresh native histories and event ordering differ, so these small live results
cannot attribute the routing difference solely to kernel arithmetic or latency.
One fast run also caused an unnecessary second judge after the repair, which the
judge denied. Faster inference does not make the policy reliably correct.

## Offline same-packet gate

[Protocol](PROTOCOL.md) froze the live comparison after the offline gate passed.
Eight exact public checkpoint packets, two repetitions, identical base weights,
no adapter and matching prompt/configuration/adapter identities were checked.

| Runtime | Warm median decision | Peak allocated CUDA memory | Choice agreements |
|---|---:|---:|---:|
| Reference Torch path | 3.794 s | 9.49 GiB | 16/16 |
| FLA gated-delta kernels | 2.402 s | 9.27 GiB | 16/16 |
| FLA plus prefill convolution | 2.220 s | 9.06 GiB | 16/16 |

The largest probability difference from reference was 0.015102, about 1.51
percentage points, for both FLA profiles. These scores are not calibrated
probabilities of incident correctness. Agreement on these sixteen decisions does
not establish equivalence on every future input. The reference and candidate
used two Torch CPU threads and the same GPU with another simulation present;
this is not an isolated throughput, energy or power benchmark. Model loading,
first-use compilation and shared-server queuing are outside the warm median.

The final convolution passed sixteen actual CUDA comparisons across FP32/BF16,
127/512 tokens, bias present/absent and activation absent/SiLU. Maximum absolute
errors were 1.91e-6 for FP32 and 6.10e-5 for BF16 in those cases. Packed input was
explicitly rejected. A prior fused-activation prototype had larger rounding
errors and remains in the raw record; the final adapter retains the reference
rounding boundary before SiLU. This check validates inference, not training
backpropagation or cached/packed generation.

## Eight fresh live trajectories

The ABBA sequence was reference, FLA-prefill, FLA-prefill, reference. Each block
ran one healthy and one defective-adapter task concurrently, with two repetitions
per profile/condition. Both profiles used the same current worker instructions,
scientific controls, downstream policy and common fallback. Four separate
warmup model calls are retained outside the live decision records.

| Condition | Runtime | Total seconds, both runs | Native starts | Judge while parked |
|---|---|---:|---:|---:|
| Adapter fault | Reference | 210.97 / 200.87 | 6 / 6 | 0/2 |
| Adapter fault | FLA-prefill | 120.09 / 142.47 | 4 / 6 | 2/2 |
| Healthy | Reference | 92.58 / 95.92 | 2 / 2 | 0/2 |
| Healthy | FLA-prefill | 100.56 / 74.69 | 2 / 2 | 0/2 |

First contradiction-to-native-judge time was 7.08 and 4.07 seconds in the fast
fault runs, versus 90.90 and 93.40 seconds for reference after fallback. Median
recorded model execution per fault trajectory was about 2.01–2.09 seconds for
fast and 3.55–3.57 seconds for reference; transport/queue latency is distinct.
The study used thirty native agent starts and sixteen actual solver executions.
All eight final numeric reporting scores were complete, with zero model errors
or missed required feedback. There was one duplicate wake: the fast second
fault run's model requested another judge on the unchanged, already repaired
bridge. Its denied request and extra downstream director increased that run to
six starts. Repeated raw action choices while a judge was already active were
not counted as separate successful dispatches.

Both reference runs chose defer on a parked contradiction, then received no new
eligible observation until fallback changed worker state. The earlier
[12-run study](../monitor-parked-20261024/RESULTS.md) had caught both faults with
the reference runtime. The newer worker instructions and actual public event
histories differ, so neither old success nor new failure is a controlled prompt
or precision ablation. Together they show why the successful demonstration is
not a robust detection guarantee. Structured completion rules remain faster and
more reliable for this explicit invariant.

A separate [timed-observation follow-up](../monitor-timer-20261024/PROTOCOL.md)
tests whether bounded elapsed-time evidence helps a model reconsider during a
quiet stream. It leaves this eight-run cohort unchanged. The post-hoc identical-input replay selected sixteen recorded observations from
the runtime and timer studies: the first eligible parked contradiction per fault
trial and first parked healthy record (first recorded healthy input if none).
There were no missing selections. Across two repetitions per input, reference
and fast runtimes agreed on **32/32 choices**, with maximum probability difference
**0.0122163**, about 1.22 percentage points. Exact prompt hashes matched and all
probabilities were finite and normalized. [Replay audit](runtime-replay-audit.json)
retains selection provenance, model identities, file hashes and all comparisons.

This sampled-state numerical agreement does not establish identical complete
policies or identify why fresh live trajectories diverged. It provides no basis
for crediting changed weights, and it does not create on-policy RL trajectories.
A controlled full-stream timing replay would be needed to isolate event-window
and inference-delay effects.

[Offline audit](offline-audit.json), [CUDA checks](convolution-validation.json),
[live audit](audit.json) and [per-run measurements](measurements.csv) preserve the
components, identities and hashes. [Reproduction](REPRODUCE.md) identifies local
raw records and pinned collection source. No new adapter was trained, no A100
was allocated, and no installed production supervisor was modified.
