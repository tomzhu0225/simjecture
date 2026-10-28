# Reproducing the continued-SFT candidate

Conjecture 1 v0.1 is [public on Hugging Face](https://huggingface.co/tomzhu0225/Conjecture-1-4B/tree/v0.1)
as an experimental adapter. Publication does not establish a workflow win. The registered 64-assignment comparison is
complete and found no reliable overall workflow advantage. The portable copy has passed a separate fresh A100 reload
and probability check. No new optimizer updates were performed during this
preparation.

## Identities

| Component | Pinned identity |
|---|---|
| Base | `internlm/Intern-Decision-4B`, revision `38c9dafbbef52dd04bae943c0c6ac918419adfd5` |
| Initial training source | `37f4773bee1af218c3687b2bdce5d9b2120ad875` |
| Continued-SFT source | `352f18383fe71e06aaa3c972faefc092f0fa9ed6` |
| Trainer in both revisions | SHA-256 `2eb73ee4d065d459b279c01017b213165aa7e3976dfe6a576b5cc09c7f99c109` |
| Evaluated adapter weights | SHA-256 `76bf1bdf4c6d6a261211057d3cab4c8609131788827569f9c33f802d3491dab5` |
| Original adapter configuration | SHA-256 `5ab93c62a751ccfe082c88caabd6c40c064d04442e3b1e164387690af6e8ba6a` |
| Portable adapter configuration | SHA-256 `f4f837242ce1749736b833544fdcc6c584a80f75ffc886eaaaea8a39eac7c132` |
| Training mixture | SHA-256 `af040302d72ec38c1ce29e73b0cf0bf1809bec072baff5d8db5cb3f8ee160756` |

The [preparation evidence](release-preparation-evidence.json) records the copied
source archive and file hashes, actual data reproduction, adapter export,
split-overlap audit and pinned upstream distribution listing. The original
adapters and training archives remain unchanged on the coordinator. Initial
export and reload ran offhost. The 129.9 MB portable adapter was subsequently
copied to the local host for release packaging, with its weight and configuration
hashes verified; this copy did not load a model or run inference/training.

A 13-file candidate bundle has been assembled offhost with documentation,
provenance, reproduction scripts and notices. Its
[package receipt](candidate-package-receipt.json) records every file hash and
records the initial preparation stage. The subsequent
[portable reload receipt](portable-reload-evidence.json) establishes mechanical
reload equivalence. The completed workflow comparison supplies negative/mixed
efficacy evidence, retained in the release documentation. That initial package
receipt is historical: the final public release contains 32 files and binds
its complete package to SHA-256
`05bda467517afb4e902f5767361609970b94d921c845fc3e46eee6c7828a959d`.
The [publication receipt](conjecture-1-publication.json) records the verified
release commit and remote weight identity.

## Data

Use a separate checkout at the initial training revision above. These CPU-only
commands create new output directories and require that checkout's Python
dependencies. They neither load a model nor start an optimizer:

```bash
python release-operations/reproduce_data.py \
  --source /study/source-37f4773 --output /study/reproduced-data
python release-operations/audit_data.py \
  --source /study/source-37f4773 --data /study/reproduced-data \
  --output /study/data-audit.json
```

Both commands were executed on the remote coordinator. All scientific split
hashes and the training mixture matched the original records exactly. The
mixture contains 4,096 authored scientific examples, 400 procedural examples,
and 1,024 independently constructed generic routing/priority examples. It has
5,506 distinct compiled visible inputs among 5,520 rows; repeated inputs with
conflicting targets are rejected by the original mixture builder.

The development split contains 512 scientific examples and the test split 1,024.
The audit found zero shared IDs or identical compiled visible inputs between
each pair of splits. The scientific mechanisms and generator templates are
shared: this check does not establish task-disjoint or semantic generalization.
The targets are authored/scripted preferences, not measured rewards or human
adjudication of actual intervention utility. Public general benchmark examples
are not inputs to this reconstructed training mixture.

## Training recipe

Training and inference require the remote A100 environment recorded in
[the model-card draft](MODEL_CARD_DRAFT.md). Reproducing data does not require
training again. For a deliberate retraining run, the original commands use
`packages/simjecture-monitor/scripts/train_decisions.py` from the pinned source:

```bash
python train_decisions.py \
  --base /models/pinned-base --data /study/reproduced-data/mixture/train.jsonl \
  --output /study/initial-sft --mode sft \
  --steps 512 --accumulation 4 --rank 16 --learning-rate 5e-5 \
  --checkpoint-every 64 --maximum-tokens 4096 --seed 20261025 \
  --wall-seconds 3600 --kernel-profile fla-prefill

python train_decisions.py \
  --base /models/pinned-base --initial-adapter /study/initial-sft/step-00512 \
  --data /study/reproduced-data/mixture/train.jsonl \
  --output /study/continued-sft --mode sft \
  --steps 8 --accumulation 4 --rank 16 --learning-rate 1e-5 \
  --checkpoint-every 8 --maximum-tokens 8192 --seed 20261025 \
  --wall-seconds 900 --kernel-profile fla-prefill
```

The original initial run selected step 512 using development evaluation.
The continued-SFT control uses eight additional supervised updates; it is not
the RL checkpoint. Initial and continued runs processed 2,048 and 32 examples,
respectively. Replaying these commands is not a claim of bitwise-deterministic
optimizer output across hardware or software changes; the distributed candidate
must retain the evaluated weight hash above.

## Portable export and inference

The generic `simjecture_monitor.adapter_export` command creates an independent
copy, verifies the original identities and preserves the entire 129,934,448-byte
weight file. It changes only two configuration fields: the base model reference
becomes the repository ID and `revision` becomes the immutable base commit.
The real candidate was exported successfully offhost, with the identities above.

The original `adapter_export.json` deliberately records
`runtime_reload_verified: false` for that preparation stage. The separate reload
receipt now records an actual fresh load: all 496 tensors (32,464,896 elements)
match exactly, and three base/SFT probability probes agree within `6.19e-8`.
The check ran after R7 collection was stopped and all native actors were closed,
before further timed assignments. It therefore did not compete with a measured
workflow. The historical export manifest is preserved rather than rewritten.

For inference, use the pinned base snapshot, Simjecture's scientific input
compiler and the tested `fla-prefill` profile. Temperature is 1 and the reported
workflow comparison uses the independent field decoder. Inputs are public
observations and questions; targets and future outcomes must not enter the model
view. The host remains responsible for freshness, admission, duplicate
suppression and permission boundaries. See the model card for the context limit,
general-decision regressions and unvalidated deployment settings.

### Inference recipe for the experimental release

The following recipe targets the tested A100/CUDA environment and the pinned
scientific scorer. It is not a validated CPU or quantized deployment recipe.
Run model loading on the intended GPU host. The published `v0.1` tag is pinned
to commit `90c57d47e26c012811c51312698ee41475b1baab`; future releases must use
new versions rather than moving that tag.

```bash
git clone https://github.com/tomzhu0225/simjecture.git
cd simjecture
git checkout 04f905c9f4538886a0713135bba29a1d4becea0b
python3.12 -m venv .inference-env
. .inference-env/bin/activate
python -m pip install -e './packages/simjecture-monitor[model]' \
  'flash-linear-attention==0.6.0' 'fla-core==0.6.0' 'pydantic==2.13.4'
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    'internlm/Intern-Decision-4B',
    revision='38c9dafbbef52dd04bae943c0c6ac918419adfd5',
    local_dir='models/intern-decision-4b', token=False)
snapshot_download(
    'tomzhu0225/Conjecture-1-4B', revision='v0.1',
    local_dir='models/conjecture-1', token=False)
PY
umask 077
mkdir -p conjecture-runtime
python - <<'PY'
from pathlib import Path
import secrets
Path('conjecture-runtime/token').write_text(secrets.token_hex(32))
PY
python -m simjecture_monitor.multiadapter_server \
  --checkpoint models/intern-decision-4b \
  --adapter conjecture1=models/conjecture-1 \
  --socket conjecture-runtime/model.sock \
  --status conjecture-runtime/status.json \
  --auth-token-file conjecture-runtime/token \
  --maximum-tokens 8192 --temperature 1 \
  --decision-distribution independent/v1 \
  --wall-seconds 3600 --idle-seconds 900 &
```

Once the status file reports `ready`, the included client checks the served
weight identity, compiled-input identity and all saved option probabilities:

```bash
python models/conjecture-1/release-operations/verify_model.py \
  --socket conjecture-runtime/model.sock \
  --auth-token-file conjecture-runtime/token \
  --policy conjecture1 \
  --probe models/conjecture-1/examples/reload-probe.json
```

The check uses a static commissioning observation and the original `1e-4`
probability tolerance. The client was checked against a retained real A100
response and rejects changed probabilities and a disabled adapter. This client
check itself has not started another inference run. The previously completed
portable-adapter reload is the actual GPU equivalence evidence. The static
observation is not a live dispatch request or a scientific performance test.
Live integration must construct fresh observations, apply host admission and
account for actual assistance separately.

## Notices and release gate

The exact upstream revision lists 21 files, including `LICENSE` and
`LICENSE-QWEN`, with no additional `NOTICE` or attribution file. Both license
texts and their original copyright notices are retained in
[the pinned license evidence](pinned-base-license-evidence.json). The source
checkout also supplies Simjecture's license and notices. Preserve these with
the model card and provenance when assembling a distribution.

Before uploading, include the completed registered workflow analysis and
infrastructure sensitivity, reconcile supported claims with the general-decision regressions,
include the portable reload proof, and verify the destination repository and
write access. Prepared files alone do not satisfy those release conditions.
