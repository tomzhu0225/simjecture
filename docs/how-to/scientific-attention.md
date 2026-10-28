# Optional scientific attention with Conjecture 1

Conjecture 1 is an experimental coprocessor that proposes when a research worker
or diagnostic stream may need attention. It is an optional tool in **Research
tools → Workflow assistance**. The catalogue opens this setup guide; it does
not install GPU software, allocate compute or enable observation automatically.
Normal studies remain disabled until an operator supplies an attention config.

The published model has not established a repeatable overall workflow advantage.
In the latest integration pilot the host blocked unnecessary healthy-case wake
proposals. Keep shadow mode for initial qualification on your own workloads.

## Connect the lightweight client

From a checkout containing the optional package:

```bash
uv pip install --python .venv/bin/python -e packages/simjecture-monitor
.venv/bin/simjecture attention status
.venv/bin/simjecture attention example-config --output /absolute/path/attention.json
```

Edit `socket` and `auth_token_file` to absolute paths for a separately managed
model service. The token is read when calling the service and is never included
in observation logs. A Unix socket can be forwarded from an authorized remote
GPU host. This client does not own the model runtime or its compute lease.

The generated configuration pins the published adapter SHA-256 and base-config
SHA-256, policy `conjecture1`, and the v0.1 independent decoder. It defaults to
`shadow`, a five-second cadence, one in-flight request, a ten-second client timeout,
720 requests and one automatic attention attempt per study. Service readiness is
an operational check, not scientific validation:

```bash
.venv/bin/simjecture attention check --config /absolute/path/attention.json
```

## Opt in for a study

Add this option to the ordinary [headless study command](headless-studies.md):

```text
--attention-config /absolute/path/attention.json
```

Shadow mode records proposals and admission results under the study's
`attention/` directory without waking anyone. To permit actual requests, create
a new study with `"mode": "alerts"` and an enabled director. The default study
command already enables the director. Configurations are immutable on resume;
changing a config file cannot silently turn a shadow study into an alert study.
Request counts, attempt reservations and cooldowns persist across restarts.

The host checks freshness, packet/evidence binding, persistence, current help,
incident duplication and the explicit attempt allowance. An admitted help or
director proposal can request the existing director, which decides whether to
help, launch temporary workers or continue normally. The model does not directly
interrupt the main worker, change scientific requirements, stop a solver,
approve a claim or grant code-repair authority. Repair-judge and knowledge-support
proposals are logged as unsupported host actions in this first integration.

The generic study adapter reads bounded public worker messages/tool results,
progress records and experiment metadata. Private reasoning and numerical arrays
are excluded. Unknown scientific progress timing stays unknown. Domain-specific
observations should use the typed observation contract rather than assuming that
ordinary process status measures scientific health. The integration is separate
from the historical WarpX evaluation driver and does not inherit its accuracy
or timing results.

`state.json` records budgets and host action attempts. Each `decision-*.json`
records the submitted observation, returned model decision, refreshed host state,
admission result and actual dispatch separately. A failed or late prediction
never becomes an invented `observe` decision. If a crash leaves dispatch uncertain,
its reservation is retained rather than automatically replayed. Ordinary worker
help, terminal events, fallback scheduling, scientific review and deadlines stay
under normal host control.

## Run the model service on a GPU host

Use a separate environment on the intended inference host. The tested A100
runtime uses Python 3.12; CPU, P40 and quantized performance are not qualified by
this recipe. Do not install model dependencies in the ordinary client environment.

```bash
python3.12 -m venv .attention-model-env
. .attention-model-env/bin/activate
python -m pip install './packages/simjecture-monitor[model]' \
  'flash-linear-attention==0.6.0' 'fla-core==0.6.0'
python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download('internlm/Intern-Decision-4B',
    revision='38c9dafbbef52dd04bae943c0c6ac918419adfd5',
    local_dir='models/intern-decision-4b', token=False)
snapshot_download('tomzhu0225/Conjecture-1-4B', revision='v0.1',
    local_dir='models/conjecture-1', token=False)
PY
umask 077
mkdir -p attention-runtime
python - <<'PY'
from pathlib import Path
import secrets
with Path('attention-runtime/token').open('x') as stream:
    stream.write(secrets.token_hex(32))
PY
python -m simjecture_monitor.multiadapter_server \
  --checkpoint models/intern-decision-4b \
  --adapter conjecture1=models/conjecture-1 \
  --socket attention-runtime/model.sock --status attention-runtime/status.json \
  --auth-token-file attention-runtime/token --maximum-tokens 8192 \
  --temperature 1 --decision-distribution independent/v1 \
  --wall-seconds 3600 --idle-seconds 900
```

The immutable model tag resolves to commit
`90c57d47e26c012811c51312698ee41475b1baab`. The service accepts only typed public
observations and returns attention proposals. It executes no tools or repairs.
Manage allocation/release and any authorized SSH forwarding separately.

For instrument integration, score an already assembled observation without any
host action:

```bash
simjecture attention score --config /absolute/path/attention.json \
  --observation observation.json --output new-decision.json
```

The observation format is `scientific-attention/0.2-draft`. Its draft version is
independent of model release v0.1. Exact runtime/compiler identities and the
[model card](https://huggingface.co/tomzhu0225/Conjecture-1-4B/tree/v0.1) describe
training provenance, evaluation limits and general-decision regressions.


## Train or evaluate a candidate separately

Training is an explicit offline tool, never part of starting a study. The
separately installable package includes these commands:

- `simjecture-attention-train`: supervised LoRA or policy-gradient updates from
  verified measured-return data.
- `simjecture-attention-evaluate`: frozen scientific decision evaluation, with
  prediction and model-identity records.
- `python -m simjecture_monitor.adapter_export`: portable adapter export that
  verifies input file identities and retains the weight bytes.

A CPU-only preflight can reject invalid input before spending GPU time:

```bash
simjecture-attention-train --mode sft --base /models/pinned-base \
  --data /data/train.jsonl --output /outputs/new-adapter --validate-only
```

It does not load a model, update weights or check tokenizer-specific token limits.
Run actual training only in the intended GPU environment with the model extra:

```bash
simjecture-attention-train --mode sft --base /models/pinned-base \
  --data /data/train.jsonl --output /outputs/new-adapter \
  --steps 128 --accumulation 4 --rank 16 --learning-rate 1e-5 \
  --maximum-tokens 8192 --wall-seconds 1800 --kernel-profile fla-prefill
```

These are example settings, not a demonstrated improved checkpoint. Version and
publish a new candidate separately; never overwrite Conjecture 1's immutable
`v0.1` release.

For RL, `--mode policy-gradient --advantage-baseline workflow-wait` requires
complete actual-workflow returns, repeated waiting controls, exact behavior
weights/probabilities and a training-only split. The alternate `measured-wait`
baseline uses independently executed checkpoint continuations. Neither scripted
preferences nor ordinary observation logs establish intervention utility. The
machine-specific research collectors remain in their pinned research branches;
no automatic collector deployment, GPU allocation or optimizer runs in a normal
study. Commissioning, development and test data remain excluded from training.

Always report quality, time, native invocations, model cost and unnecessary
attention separately. Authored decision accuracy and valid citations do not
establish a workflow improvement. Retain prospective scientific tasks and general
decision checks for candidate evaluation.
