# Scientific attention 0.2 draft: knowledge support and training data

This proposed interface adds scoped knowledge support to the
[0.1 draft](../scientific-attention-0.1-draft/README.md). Both versions remain
available. It is a research contract, not an adopted community standard or an
enabled production feature. No new model has been trained against this version.

## Decision and observation changes

The five attention actions retain their meanings. Two additional fields describe
the requested support without multiplying the action vocabulary:

| Field | Values | Meaning |
| --- | --- | --- |
| `support_kind` | `none`, `knowledge_lookup`, `literature_review` | What support is requested |
| `question_ref` | Visible question alias or `null` | Which recorded knowledge gap it addresses |

For example, a scripted preference after a recent unsuccessful knowledge search is:

```json
{"action":"request_worker_help","support_kind":"literature_review","question_ref":"q0","basis":"missing","evidence":["e1","e2"]}
```

The model emits this small `Choice` payload. The host binds its aliases to canonical
IDs and the exact input hash in `Decision`; it does not ask the model to reproduce
hashes. A request remains provisional until host admission. Requests never grant
repair authority or approve a scientific conclusion.

`knowledge_lookup` permits `recheck` for a bounded approved retrieval, or
`request_worker_help`/`wake_director` for interpretation. `literature_review`
permits the latter two expert routes. `none` requires `question_ref=null`.
The model selects an existing question; it does not invent arbitrary search
commands. A host adapter must supply questions and execute approved tools.

Observations add `questions`, `retrieval_history` and an explicit
`retrieval_history_complete` flag. Each question has its text, public supporting
evidence, context hash and resolution state. Retrieval records include the
question/context, requested support and action, execution status, result category,
age, reuse allowance, retry cooldown and receipt references. A completed search
requires a receipt even when it found nothing. Context hash equality means the
recorded setup matches; it does not prove scientific applicability.

The packed view preserves all question and retrieval evidence, even if originally
marked optional. An insufficient budget is reported explicitly. Raw IDs/hashes
become aliases and context-equality flags. Named and column formats retain the
same knowledge content. The 0.1 token measurements do not measure this larger
0.2 prompt; actual training-template tokenization remains necessary.

## Avoiding repeated attention

The reference gate retains freshness, grounding, quiet-window and persistence
checks from 0.1. It also suppresses work for resolved questions, active same-context
investigations and recent reusable results of the same work. Unknown history
requests a recheck. Failed retrievals honor a cooldown; changed context or expired
results can justify another lookup. A recent cheap search can still lead to helper
interpretation or a literature review. Matches do not establish applicability;
no matches do not establish that relevant research is absent.

Persistence is separate for each policy and support/question route. A changed
current choice interrupts confirmation, and different questions cannot supply
each other's confirmations. Actual expert dispatch is deduplicated across routes
for the same incident. Cheap lookups update retrieval history and do not consume
the expert dispatch allowance. Durable transactions, context/revision maintenance,
retrieval execution and independent deadline monitoring remain host responsibilities.
These mechanisms have conformance tests, not a measured deployment false-alert rate.

The JSON schemas cover structure. Reference Python validation additionally checks
compatible actions, cross-record references and result receipts. Host admission
checks temporal and current-state constraints. Schema validity alone is insufficient.

## Pointwise data and LoRA

A visible observation paired with a desired `Choice` is a pointwise supervised
example. This supports SFT or teacher distillation. LoRA specifies which parameters
are updated, independently of dataset size and training objective; a large SFT
dataset can train a LoRA adapter. Full-parameter fine-tuning is a separate compute
and generalization decision. See the [PEFT LoRA documentation](https://huggingface.co/docs/peft/main/en/conceptual_guides/lora).

Defining the interface makes examples checkable; it does not identify the best
intervention. Keep three sources of supervision distinct:

1. **Scripted procedural examples:** schema use, quiet periods, retrieval history,
   missing state and straightforward consistency checks. These bootstrap behavior.
2. **Reviewed scientific decisions:** real trace prefixes and diverse constructed
   cases, labeled by knowledgeable reviewers or a validated stronger teacher.
   Preserve uncertainty and multiple defensible choices instead of forcing an
   invented unique optimum. Future evidence may inform review labels but must not
   appear in the student's pre-decision input.
3. **Executed intervention outcomes:** actual continuations after the proposed
   action, including scientific correctness, unnecessary interruptions, missed
   problems, detection delay and expert/compute cost. These can support utility
   estimation and subsequent RL with the required behavior-policy provenance.

The included generator implements only the first layer. It reads visible state to
produce transparent scripted preferences; it is not a scientific utility oracle.
Its recommendation to review literature after an unsuccessful scoped search is an
authored curriculum preference, not a finding that review is always worthwhile.
Synthetic generation followed by filtering has precedent in
[Self-Instruct](https://arxiv.org/abs/2212.10560); that does not validate our labels.

The pilot contains **16,000 examples in 1,000 base-context groups**, with 16 scripted
conditions per group. There are 13,024 training rows, 1,600 validation rows and
1,376 synthetic-audit rows. All variants of a context remain in one split. Exact
input duplication, conflicting targets and cross-split context-group leakage are
zero in this build. These checks do not exclude semantic/template leakage:
all three splits share the 16 mechanisms and three synthetic science vocabularies.
They are not 16,000 independent scientific tasks or a real-task test set.

The mixture includes 7,000 `observe` preferences, two kinds of healthy quiet
conditions, pending/recent/stale/different-context searches, resolved questions,
missing telemetry, persistent silence and straightforward measurement/receipt
disagreements. Its class frequencies are authored, not estimated deployment rates.
Variants share a base context but are not guaranteed one-factor causal pairs.

Each JSONL row stores `input_text` and `target` separately from provenance and
supervision. **Train only on these two fields**, not the complete row. Utility and
behavior-probability labels are null, and `rollout_validated` is false. The full
input is not silently truncated; the eventual trainer must tokenize its actual
chat template and reject or explicitly repack oversized examples. The existing
four-action RL learner is not a trainer for this new multi-field target.

Before increasing volume, review label quality and add harder valid negatives,
scientific ambiguity, unit conversions, stale/incomplete observations, multiple
simultaneous issues and prompt variations. Hold out entire task families and real
episodes for evaluation. Tune alert thresholds on development data, then report
false expert wakes per healthy operating hour together with missed incidents,
detection delay and scientific completion on untouched real workflows. Matching
this scripted teacher alone cannot demonstrate an advantage over rules.

## Reproduction

Run from the repository root with the monitor package on `PYTHONPATH`:

```bash
export PYTHONPATH=packages/simjecture-monitor/src
.venv/bin/python packages/simjecture-monitor/scripts/export_attention_support.py \
  --output packages/simjecture-monitor/specs/scientific-attention-0.2-draft --check
.venv/bin/python packages/simjecture-monitor/scripts/build_attention_curriculum.py \
  --groups 1000 --seed 20261025 --output /path/to/new/bootstrap-16k
.venv/bin/pytest packages/simjecture-monitor/tests -q
```

The builder refuses an existing output directory. The local pilot is in
`artifacts/attention-support-20261025/bootstrap-16k/`; its
[manifest](bootstrap-manifest.json) records exact data/source hashes, split and
action counts. Only the manifest and small examples are committed. A failed build
without a manifest is incomplete. No model inference, training, native worker,
simulation or Colab allocation is performed by these commands.
