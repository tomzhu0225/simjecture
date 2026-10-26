# Scientific attention training and retention results

Supervised adaptation substantially improves agreement with the authored
scientific attention interface. The measured-return RL pilot completes real
training, but its scientific snapshot score matches an equal-update supervised
control. Neither result establishes that a scientific workflow benefits from
the coprocessor. This report covers completed training and static evaluations
on 25–26 October 2026; the prospective workflow comparison is a separate test.

The [protocol](PROTOCOL.md) specifies the training, exclusions, test boundaries
and retention gates. [Training evidence](training-evidence.json) contains the
original metric payloads, archive/member hashes, completed update records and
retention audit. No checkpoint was selected using these test results.

## Models and executed updates

The base is `internlm/Intern-Decision-4B`, revision
`38c9dafbbef52dd04bae943c0c6ac918419adfd5`. The adaptations use rank-16 LoRA on
the language backbone, with 32,464,896 trainable parameters. They are adapter
updates, not full-parameter training. All optimizer work ran on remote A100s;
physical simulations ran on the remote P40 host. The local host performed
editing, orchestration and lightweight checks.

The supervised mixture contains 4,096 authored scientific examples, 400
procedural examples and 1,024 independent generic rehearsal examples. The
selected supervised checkpoint completed 512 updates with accumulation 4 and
learning rate 5e-5. Those updates process 2,048 training examples, less than one
full pass over the 5,520-row mixture. Selection among the scheduled checkpoints
used the development split only.

The reward pilot prepares four public checkpoints from real native workers and
WarpX controls: healthy progress, an unreported worker-owned adapter blocker,
an adapter incompatible with the next mesh, and a protected adapter defect.
It samples four five-field decisions from each checkpoint at temperature 3 and
executes all 16 continuations. Independent saved-field verification checks the
reports. Accurately reporting a failed original physics check counts as
successful reporting; changing an acceptance threshold does not.

An earlier preparation failed before sampling. A subsequent pilot completed its
continuations but contained one unconfirmed solver transfer; that entire reward
dataset was excluded before optimization. The retained third pilot has 16
eligible measured returns. Its data SHA-256 is
`34b004019b4da5e5d4f2ad5cca6d02d33fcb41b2bbe8295963123b16ae020e39`.

Both new updates start from the selected supervised adapter:

| Update | Data | Optimizer steps | Learning rate | Input token range |
|---|---|---:|---:|---:|
| Continued SFT | Original supervised mixture | 8 | 1e-5 | 339–1,459 |
| RL | 16 executed continuation returns | 8 | 1e-5 | 3,853–5,818 |

Both use accumulation 4. RL uses clipped policy ratios in [0.8, 1.2], a KL
coefficient of 0.02, and at most two passes over the logged samples. The initial
behavior probabilities reproduce with maximum error zero; both saved adapters
reload with maximum probability error zero on their recorded probes.

The RL baseline is the mean return of the other sampled actions for the same
checkpoint. There is no guaranteed dedicated wait control at every checkpoint.
Consequently, a positive training advantage does not establish that assistance
was better than continuing unaided. The newer measured-wait collector in
[PR 68](https://github.com/tomzhu0225/simjecture/pull/68) adds that comparison;
these evaluated weights were not trained with it.
The pilot also resumes the main worker immediately from each public checkpoint.
It therefore measures assistance to an awake worker, rather than the value of
interrupting the deployed parked-worker wait. This is a training/deployment
difference that an explicit wait baseline alone does not resolve.

## Authored scientific snapshot test

The test contains 1,024 snapshots: 512 with a quiet preference and 512 with an
expert-attention preference. Training, development and test use different seeds
and wording within the same eight authored mechanism families. This tests
transfer within those templates, not new scientific domains or unseen failure
mechanisms.

The main score requires a valid choice, structurally valid evidence/basis
binding, and an acceptable authored route. It does not independently assess
semantic entailment of the cited evidence or the value of executing that route.

| Model | Valid cited acceptable routes | Accuracy | Expert proposals on 512 quiet snapshots | Missed preferences on 512 expert snapshots |
|---|---:|---:|---:|---:|
| Base | 553/1,024 | 54.00% | 93 | 292 |
| Selected SFT | 997/1,024 | 97.36% | 5 | 19 |
| Continued SFT | 998/1,024 | 97.46% | 5 | 18 |
| RL | 998/1,024 | 97.46% | 5 | 18 |

The large base-to-SFT change measures learning of the interface and its authored
preferences. The additional RL update offers no advantage over continued SFT on
this score. The five quiet-snapshot proposals are not five real-world false
alerts: an actual alert must also pass the host admission rules, and its value
depends on the downstream worker outcome.

All four comparisons use the same A100-SXM4-80GB evaluation runtime and pinned
base. The test dataset hash is
`006dc11cafed9b33122a6f477ac2adc4aeea1fccb252b6a28ebdcc6feb9e7a4e`.

## General decision retention

Seven public suites contain 10,751 input records and 12,351 scored decisions.
The typed-decision suite contributes five decisions per input. The macro score
is the unweighted mean of the seven suite accuracies. All evaluations complete
without inference failures.

The predeclared gate permits at most two percentage points of macro loss from
the base and at most three points of loss on each suite with at least 300 scored
decisions. It is a point-estimate gate, not a statistical equivalence result.

| Model | Macro accuracy | Change from base | Retention gate |
|---|---:|---:|---|
| Base | 90.0133% | — | Reference |
| Selected SFT | 87.9063% | −2.1070 points | Fail |
| Continued SFT | 88.3426% | −1.6707 points | Pass |
| RL | 88.2643% | −1.7490 points | Pass |

Passing the gate does not mean every capability is preserved. RL loses 7.21
points on the 111-example hard suite and 2.80 points on typed decisions. Continued
SFT loses 8.11 and 2.25 points respectively. Both retain ToolACE accuracy and
slightly improve AG News; both lose accuracy on WildJailbreak. All per-suite
counts and dataset hashes are retained in the evidence JSON.

## What remains to establish workflow value

The prospective comparison uses real native workers and saved-field scientific
verification, with no automatic intervention, fixed rules, continued SFT and RL
under the same corrected host. Its outcome measures are whole-workflow
completion, actual elapsed time, agent starts, and quiet-episode attention.
Failures and unstarted resource-limited assignments must be reported separately.

The earlier 64-workflow cohort contains experimental collector and transport
failures and remains a separate study. Those defects are in this research
implementation; they do not demonstrate an upstream production Simjecture bug.
Its outcomes cannot be repaired retrospectively by substituting runs from the
new host.

The [earlier paired continuation study](../monitor-paired-20261024/RESULTS.md)
already tested prescribed assistance against waiting and found no reporting
improvement, with more agent starts for assistance. Future wait-controlled
training must therefore be evaluated on fresh workflows rather than treated as
an assumed solution. The actual benefit may depend on when an otherwise capable
worker is unavailable, what it can already observe, and whether assistance
arrives early enough to change its work.

These static results support a reproducible experimental training path. They do
not support publishing the adapter as a proven scientific-workflow improvement.
The [next research design](RESEARCH_NEXT.md) relates this evidence to nearby work,
episode-level false-alert calibration and a stronger continuation comparison.

## Retained artifacts

The following archives are preserved off the disposable Colab runtime under
`/home/simjecture/investigations/scientific-attention-20261025/checkpoints` on the
remote coordinator. Archive hashes and exact metric member hashes are in
`training-evidence.json`; weights remain in the separately verified adapter
archives.

| Archive | Contents |
|---|---|
| `recovery-evaluation-v2.tar.gz` | Base and selected-SFT scientific/general evaluation records |
| `final-evaluation-v3-metadata.tar.gz` | Continued-SFT and RL evaluation records |
| `main-git-03-selected.tar.gz` | Selected supervised adapter and training records |
| `return-pilot-continued-sft-v3.tar.gz` | Continued-SFT adapter and update records |
| `return-pilot-rl-v3.tar.gz` | RL adapter and update records |
| `return-pilot-samples-v3.tar.gz` | Sampled behavior decisions and probabilities |

The current adapter weight SHA-256 identities are:

```text
Selected SFT   922bfef8e221f5df39ec3a3740d3e9e97fbcd2358c34679f774a0085227ae780
Continued SFT  76bf1bdf4c6d6a261211057d3cab4c8609131788827569f9c33f802d3491dab5
RL             dac85c84f7dc7416baed29c04beaad8482df5998a0be90d827e22e713754f0be
```
