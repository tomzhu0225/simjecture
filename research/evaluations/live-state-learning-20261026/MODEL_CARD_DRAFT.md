# Scientific attention adapter: continued-SFT candidate

**Unpublished release draft.** This candidate has not established a reliable
workflow advantage over the pretrained base and strong deployment comparators.
The repeated-workflow study is collecting the remaining original assignments
after an infrastructure interruption. No weight upload or public release is
implied by this document. The pinned base declares Apache-2.0; distribution
notice checks, a destination repository and write authentication remain pending.

## Identity and intended use

This PEFT LoRA adapter specializes `internlm/Intern-Decision-4B`, pinned to
`38c9dafbbef52dd04bae943c0c6ac918419adfd5`, for proposing attention in autonomous
scientific workflows. The adapter weights have SHA-256
`76bf1bdf4c6d6a261211057d3cab4c8609131788827569f9c33f802d3491dab5`.
Its original adapter configuration has SHA-256
`5ab93c62a751ccfe082c88caabd6c40c064d04442e3b1e164387690af6e8ba6a`.
The pretrained base is required separately; this is not a standalone model.

The tested role is an assistant to a capable worker, director and independent
repair judge. It proposes whether visible evidence warrants observing, checking
again, requesting help, or escalating for review. It does not approve science,
execute tools, grant repair authority, or replace the main scientific worker.

The scientific tests concern bounded asynchronous one-dimensional WarpX control
and diagnostic/reporting workflows. They do not establish autonomous discovery,
performance across scientific disciplines, or a production reliability claim.

## Inputs, outputs and host responsibilities

The tested interface is the Simjecture scientific-attention 0.2 draft. Only
public state and decision questions enter the masked-chat input. Training
targets, future outcomes and hidden fixture labels remain outside that input.
The five scored fields are `route`, `question_ref`, `basis`, `evidence_primary`
and `evidence_secondary`. Evidence and question aliases are bound to canonical
identities by the host, rather than generated as arbitrary identifiers.

Routes combine attention with optional knowledge lookup or literature review.
Such support requires a question supplied by the host. The plasma workflow
tests declare no retrieval questions and therefore do not validate retrieval
or literature-review utility.

Serving uses a single masked-position forward pass, temperature 1 and the
original independent field decoder. The full-input allowance is 8,192 tokens;
the server explicitly reports inputs beyond that allowance. Optional constrained
route/question decoding is a separate implementation and is not part of this
checkpoint's reported workflow comparison.

The tested workflow polls every five seconds while the main worker is parked,
allows at most one automatic expert request, and retains a 90-second fallback.
It does not establish the benefit of polling an actively reasoning worker.

The host must validate combinations and evidence, check freshness and current
state, respect announced quiet periods, suppress duplicate work, and separately
record actual dispatch. A proposal is not an admitted alert. Model option
probabilities have not been calibrated as probabilities of scientific failure.

## Training

The initial supervised mixture contains 4,096 authored scientific examples,
400 procedural examples and 1,024 general decision examples. The selected run
performed 512 optimizer steps with accumulation 4 and learning rate `5e-5`;
2,048 examples were processed, rather than a complete pass over that mixture.
LoRA rank is 16, alpha 32, with 32,464,896 trainable parameters.

This candidate then received eight continued-SFT updates with learning rate
`1e-5` and accumulation 4. It is the continued-SFT control from the earlier
SFT/RL experiment, not the RL checkpoint. The later live-state reviewer
judgments and repeated-workflow outcomes have not been used to update it.

## Evaluation available so far

| Measure | Pretrained base | Continued SFT |
|---|---:|---:|
| Authored scientific contract/routing test | 54.0% | 97.5% |
| General-decision macro accuracy across seven suites | 90.0133% | 88.3426% |
| Route acceptable to both live-state reviewers | 16/24 | 18/24 |
| Accepted expert route on seven states where both require an expert | 0/7 | 5/7 |
| Expert proposal on eleven unanimous observe-only states | 0/11 | 2/11 |

The authored test contains 1,024 cases. General evaluation contains 10,751 input
records and 12,351 scored decisions. The macro score weights the seven suites
equally. Continued SFT passes the predeclared point-estimate tolerance of two
percentage points of macro loss and three points per suite with at least 300
decisions. This does not show universal retention: it loses 8.11 points on the
111-example hard suite and 2.25 points on typed decisions. It should not be
presented as a general-decision replacement with no regressions.

The live-state sample consists of 24 correlated observations from eight earlier
episodes, judged by separate contexts of the same large model. These judgments
are not human ground truth or causal intervention outcomes. The base observed
throughout. SFT detects several problems but also proposes attention that both reviewers
consider unnecessary. It routes two protected harness defects to the director
where both reviewers expected the independent repair judge.

An earlier exploratory seven-episode-per-arm cohort measured means of 223.9
seconds for this adapter, 265.1 for rules and 277.2 for worker-only execution.
It omitted the pretrained-base arm. These promising observed differences do not
answer the missing base/SFT workflow comparison. The subsequently registered
64-workflow replication retained its initial verified rules episode and
provider-failed base episode, then resumed only previously unstarted assignments.
At the 2026-10-27 03:43 UTC snapshot, another 18 episodes had completed and passed
their verifiers. The first two fully repeated families show large gains on
publication-retry workflows and a slower SFT mean on quiet workflows. These are
interim observations, not a completed effect estimate or a release gate. See
[the continuation record](CONTINUATION_RESULTS.md) for all arms and caveats.

## Reproduction and release requirements

The tested runtime is a remote NVIDIA A100-SXM4-80GB, PyTorch 2.11.0 with CUDA
13.0, Transformers 5.20.1, PEFT 0.21.2, huggingface-hub 1.33.0 and FLA 0.6.0.
Use the pinned Simjecture input compiler and `fla-prefill` execution profile.
This draft does not claim validated CPU, P40 or quantized inference performance.

Reload verification checks all 496 adapter tensors, the disabled-adapter base
prediction and saved probability probes. Both SFT probes reproduced before and
after the recorded-state evaluation with maximum discrepancy below `2.85e-8`
against the unchanged `1e-4` tolerance. The original weights remain preserved
off the disposable A100 runtime.

The pinned base README declares Apache-2.0. Its `LICENSE` and `LICENSE-QWEN`
files contain Apache License 2.0 with Shanghai AI Laboratory and Alibaba Cloud
copyright notices, respectively. Their exact text and hashes are retained in
[the license evidence](pinned-base-license-evidence.json). Checking the complete
upstream distribution for additional notices and training-data provenance
remains part of packaging; this metadata check alone does not complete release.

Before publishing, complete the registered workflow evidence and its
infrastructure sensitivity analysis, finish attribution and data checks,
package a portable adapter configuration without
changing the weight tensors, and include exact input/compiler, training and
evaluation manifests. Disclose the general regressions and observed attention
errors. Publish only claims supported by that completed evidence.

The [training/retention report](https://github.com/tomzhu0225/simjecture/blob/docs/scientific-attention-results/research/evaluations/scientific-attention-training-20261025/TRAINING_RESULTS.md),
[live-state results](OBSERVATION_RESULTS.md), [workflow protocol](PROTOCOL.md)
and retained evidence files are the current sources. The release decision is
pending; no scientific-workflow win is claimed here.
