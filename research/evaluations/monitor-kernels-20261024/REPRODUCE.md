# Reproduce the optional inference-runtime comparison

All paths below are relative to
`/home/tomzhu0225/src/simjecture-monitor-coprocessor`. This stage changes no base
or adapter weights and allocates no Colab runtime.

## Offline retained-packet benchmark

Raw record: `artifacts/inference-fast-20261024`. It contains the frozen gate,
eight exact observation packets and original reference predictions, installed
package/function metadata, benchmark wrappers/logs and the full per-call outputs.
`offline-audit.json` records the raw status/prediction file hashes and summaries.
`convolution-validation.json` preserves the actual sixteen-case CUDA check.
The rejected earlier fused-activation prototype is retained separately in the raw
record; the final adapter preserves the reference BF16 rounding before SiLU.

Reference Python is `artifacts/model-env/bin/python`; the isolated candidate is
`artifacts/model-fast-env/bin/python`. Both use Torch 2.11.0+cu130,
Transformers 5.20.1, PEFT 0.21.2 and the same pinned base directory
`artifacts/models/Decision-verified` (Intern-Decision-4B revision
`38c9dafbbef52dd04bae943c0c6ac918419adfd5`). The candidate adds
`flash-linear-attention==0.6.0`, `fla-core==0.6.0`, `einops==0.8.2` via isolated
`uv pip install --no-deps`; a `.pth` references the retained reference model
environment's site-packages. The reference environment was not modified.

The environment's actual gated-delta implementations are recorded rather than
assuming installation enables them. FLA supplies its Triton implementations;
`--kernel-profile fla-prefill` additionally adapts its dense convolution layout.
No incompatible locally compiled causal-conv1d extension or CUDA toolkit upgrade
was used. The hook's source hash is recorded with every explicit-profile result.
Its validated contract is single-pass inference, not policy-gradient training.

To rerun on the same retained packets, choose a new output directory. The
host-created wrapper caps Torch CPU threads at two, CUDA memory at 60%, and
requires more than 11 GiB free before loading; preserve these controls:

```bash
PYTHONPATH=packages/simjecture-monitor/src \
  artifacts/model-fast-env/bin/python \
  artifacts/inference-fast-20261024/benchmark-wrapper.py \
  --checkpoint artifacts/models/Decision-verified \
  --kernel-profile fla-prefill \
  --packets artifacts/inference-fast-20261024/packets.json \
  --reference artifacts/inference-fast-20261024/reference.json \
  --output artifacts/NEW-benchmark-fla-prefill
```

Repeat sequentially with the reference Python and without `--kernel-profile`.
Do not load two full models beside the unrelated GPU simulation. Both rounds
must use identical inputs and weights. `benchmark_local.py` verifies prompt,
checkpoint configuration and adapter identities. The second repetition supplies
warm latency; model loading and first-use compilation are retained separately.
This is a shared-GPU latency check, not isolated throughput or power measurement.
A fresh small CUDA check uses `scripts/validate_fla_prefill.py --output NEW.json`
under the candidate interpreter (script path under the monitor package).

## Fresh live runtime trajectories

Raw record: `artifacts/kernel-live-20261024`, with frozen `DESIGN.json`, four
sequential ABBA server blocks, excluded common warmup outputs, actual native
traces and per-trial `LIVE.json`, ledgers, report verification and saved plots.
Collection source was `c50e78c`; later commits add audits and an optional driver
argument without changing the runtime study's worker driver. The manifest source
revision and explicit runtime identity remain the collection provenance.

A fresh run uses `scripts/run_kernel_study.py --root NEW_ROOT --pilot PILOT_ROOT`
under the root `.venv`, with a newly prepared shared native lease/wrapper. It
requires actual native Astra access, retained scientific tools and verified model
weights. Never reuse the expired old lease or an existing study directory.
Recompute measured components without model inference:

```bash
.venv/bin/python packages/simjecture-monitor/scripts/audit_parked_study.py \
  --root artifacts/kernel-live-20261024 \
  --budget artifacts/paired-20261024/native-budget.json \
  --output research/evaluations/monitor-kernels-20261024
```

The later `replay_runtime_packets.py` is a post-hoc identical-packet numerical
check. It selects the first recorded parked contradiction per fault trial and
first parked healthy observation (first recorded healthy packet if none was
parked), retaining every missing selection. Its manifest hashes selected records.
It does not turn greedy live records into on-policy training data.

Primary implementation references: [FLA repository](https://github.com/fla-org/flash-linear-attention),
[causal-conv1d repository](https://github.com/Dao-AILab/causal-conv1d),
and [Transformers kernel integration](https://huggingface.co/docs/transformers/en/main_classes/kernels).
Installed versions and actual benchmark receipts establish what ran locally;
these moving documentation pages alone do not pin the local environment.
