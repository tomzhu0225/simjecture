# Conjecture 1 — scientific attention adapter

By Simjecture. [Conjecture 1 v0.1 is public on Hugging Face](https://huggingface.co/tomzhu0225/Conjecture-1-4B/tree/v0.1).
The immutable release tag points to commit
`90c57d47e26c012811c51312698ee41475b1baab`. This repository document retains its
historical filename; the published model card accompanies that tag.

**Experimental research preview.** This continued-SFT PEFT LoRA adapter requires
the pretrained Intern-Decision-4B base separately. It has not established a
reliable overall workflow advantage. The completed 64-assignment comparison
contains 58 verified completions, four infrastructure failures and two SFT
workflow failures. Mixed/negative findings and general-decision regressions
are included in the public release.

The [publication receipt](conjecture-1-publication.json) records the verified
remote weight hash, package hash and unauthenticated public tag lookup. The
portable adapter passed a fresh A100 reload before release. Publication is
availability of an experimental checkpoint, not validation of scientific efficacy.

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
The two training stages total 2,080 example presentations; this is not a claim
that all 5,520 mixture rows were processed or that every presentation was unique.
The 1,024 generic rehearsal rows were constructed independently of the public
retention benchmarks. Actual training inputs ranged from 339 to 1,459 tokens;
the recorded live-state evaluation used 3,200–4,964-token inputs.

The full training mixture and all scientific evaluation splits were rebuilt from
the pinned source and match the original byte hashes. An audit found no identical
compiled visible inputs or shared IDs between training, development and test.
The training mixture has 5,506 distinct visible inputs among 5,520 rows. Its
constructed mechanisms remain shared across splits; this is not task-disjoint
generalization. See [the reproduction record](REPRODUCTION.md) for source,
data and weight identities and the original training commands.

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

| Decision-formatted public suite | Input records | Scored decisions | Base accuracy | Continued SFT |
|---|---:|---:|---:|---:|
| JevBench easy | 48 | 48 | 100.00% | 100.00% |
| JevBench original | 72 | 72 | 98.61% | 98.61% |
| JevBench hard | 111 | 111 | 73.87% | 65.77% |
| ToolACE | 310 | 310 | 96.45% | 96.45% |
| Typed decisions | 400 | 2,000 | 80.45% | 78.20% |
| AG News | 7,600 | 7,600 | 90.84% | 90.91% |
| WildJailbreak | 2,210 | 2,210 | 89.86% | 88.46% |

These are option-scoring evaluations using the pinned JevBench scorer, not
free-form agent executions. All reported static evaluations completed without
inference errors. The [exact retained metrics](candidate-static-evaluation-summary.json)
include dataset hashes and counts; this table is a documentation update, with
no new model execution or optimizer update.

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
All 64 original assignments now have audit records: 58 verified completions,
four infrastructure failures and two SFT workflow completion failures. The
registered SFT-minus-base restricted-completion estimate is +12.6 seconds
(95% interval −116.1 to +148.3); excluding the predefined whole
infrastructure-affected blocks gives +11.9 seconds (−91.1 to +110.3).
Neither establishes an overall advantage. SFT verifies 13/16 workflows;
base, rules and worker-only execution each verify 15/16. Mean restricted
completion times are 364.4, 351.8, 338.5 and 356.0 seconds, respectively.
An unsuccessful workflow contributes 650 seconds, so these are not raw runtime
means. Publication-retry and unstable-update workflows show favorable repeated
SFT differences, while protected source selection fails in both SFT repeats.
See [the completed record](CONTINUATION_RESULTS.md) for all arms, intervals,
infrastructure sensitivity and individual paired effects.

Both R10 SFT source-binding workflows failed completion verification despite
successful physical controls and authorized repairs. Their four main-worker turns
were exhausted during replanning/help/reprocessing, leaving no final reports and
one required return unacknowledged in each. These are retained as unsuccessful
workflows under the registered limits, each receiving the 650-second restricted
completion penalty. Model attention can consume coordination capacity
as well as save it; these data do not establish that every early intervention
helps a capable worker.

Inspection of recorded worker prompts found general research execution/review
guidance alongside the experiment's different wrapper/report protocol. This
common instruction context may influence discretionary help requests; its causal
effect is unmeasured. A separate task-focused pilot without a decision model
also reproduced a completion failure after routine help: corrected processing
finished after the fourth worker turn, but the loop offered no fifth reporting
turn despite unused wall time and native-start allowance. A prospective control
permits additional resumptions within the same resource limits and is being
commissioned. See [the control record](FOLLOWUP_CONTROLS.md). These observations
do not replace the original results or establish model benefit under a revised
harness. Reported model measurements remain conditional on the original harness.

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
[the license evidence](pinned-base-license-evidence.json). The complete pinned
upstream listing contains no additional NOTICE or attribution file. Training-data
provenance and exact split reproduction are recorded separately. These checks
alone do not complete release.

A portable candidate copy preserves the weight-file hash and changes only the
base repository reference and pinned revision in its configuration. After timed
collection stopped for transport recovery, a separate fresh A100 load matched
all 496 adapter tensors exactly and reproduced all three saved base/SFT probes,
with maximum probability discrepancy `6.19e-8` against the unchanged `1e-4`
tolerance. [The reload evidence](portable-reload-evidence.json) records this check.
The completed scientific comparison used the original adapter and configuration;
no optimizer ran during export or reload.

The registered workflow evidence and infrastructure sensitivity analysis are
complete and support an experimental artifact release with the limitations
above. They do not support an efficacy or production-readiness claim. Before
publishing, include the checked notices and portable reload receipt without
changing the weight tensors, and include exact
input/compiler, training and evaluation manifests. Disclose the general regressions and observed attention
errors. Publish only claims supported by that completed evidence.

The [training/retention report](https://github.com/tomzhu0225/simjecture/blob/docs/scientific-attention-results/research/evaluations/scientific-attention-training-20261025/TRAINING_RESULTS.md),
[live-state results](OBSERVATION_RESULTS.md), [workflow protocol](PROTOCOL.md)
and retained evidence files are the current sources. The release decision is
pending; no scientific-workflow win is claimed here.
