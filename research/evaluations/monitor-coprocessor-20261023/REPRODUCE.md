# Reproduce the monitoring exploration

Start from research branch `research/monitor-coprocessor`. Production helper
support comes from main commit `f35082bb2c406c6c9cab5deb7b9409714efc5b35`.
The clean learning collection was launched from `1360764`; the training source
bundle was prepared at `e3e07d3`. Fresh base/adapter evaluation uses `76b2bb3`.
Each cohort also retains its own revision and exact artifact hashes.

## Existing evidence on this host

```bash
cd /home/tomzhu0225/src/simjecture-monitor-coprocessor
.venv/bin/python packages/simjecture-monitor/scripts/analyze.py \
  --root artifacts/overnight-20261023/comparison-v2 \
  --output artifacts/overnight-20261023/comparison-v2/ANALYSIS.json
.venv/bin/python packages/simjecture-monitor/scripts/export_returns.py \
  --root artifacts/overnight-20261023/rl-clean \
  --output /tmp/monitor-returns-recomputed.json
```

The original learning dataset is `artifacts/overnight-20261023/returns.json`,
SHA-256 `5389a307bb29754dee5e2391b4ff7946683d01cb60815a305d80147a60abedfa`.
Dataset serialization includes wall-clock timestamps and artifact modification
times, so copying a study without preserving timestamps changes its measured
time and feedback-closure assessment. Preserve the original files and metadata.
Use the retained dataset for exact replay of the training update.

Key evidence directories:

| Directory or file | Contents |
| --- | --- |
| `comparison-v2/` | Twelve initial trajectories, known confounds retained |
| `rl-collection/` | Two excluded commissioning pilots, retained together |
| `rl-clean/` | Four eligible sampled real-worker episodes |
| `adapter-evaluation/` | Fresh base and adapted-policy continuations |
| `repair-trials/` | Standalone real-judge grant/deny and tested repair |
| `replay-01/`, `replay-02/` | Historical trace replay; no downstream live benefit claim |
| `training/run-01/` | Adapter, optimizer/RNG state, status, history, reload check |
| `training/remote-manifest.json` | Hashes verified after retrieval from Colab |
| `learning-package.tar.gz` | Actual source bundle sent to the training runtime |
| `stream-timing-audit.json` | Live diagnostic observation versus process completion |
| `COMMISSIONING.json` | Initial setup exclusions and reasons |

These directories are relative to `artifacts/overnight-20261023/`, are ignored
by Git, and are local to this machine. A separate checkout needs these retained
artifacts or equivalent configured dependencies. Do not assume an old Colab
session or historic balance is still live.

## Environment and checks

```bash
uv sync --frozen --extra workspace --group docs
uv pip install --python .venv/bin/python -e packages/simjecture-monitor
.venv/bin/ruff check .
.venv/bin/pytest packages/simjecture-monitor/tests -q
```

Bubblewrap and working unprivileged namespaces are required for actual isolated
repair checks. The unit suite does not load a model or call native agents.
Native-worker trials require this host's configured Codex execution transport.

The live task script uses the existing scientific environment
`/home/tomzhu0225/src/simjecture-rl-harness/.venv-plasma/bin/python`, the analysis
and bounded-launch scripts under that checkout, and the retained solver under
`/home/tomzhu0225/src/simjecture/artifacts/colab-smoke/20261020/results/`.
The WarpX executable SHA-256 is
`13a427a60b87efd24a420bfd82d5149be956f98c2ff7df0c8aa32db8655a6519`.
Read that setup's `REPORT.txt` and `REPRODUCE.txt` before rebuilding or changing
solver assumptions. Do not substitute a mocked solver result.

## Model and training

Use the original `internlm/Intern-Decision-4B` checkpoint pinned to
`38c9dafbbef52dd04bae943c0c6ac918419adfd5`. The model environment uses PyTorch
2.11.0/CUDA 13.0, Transformers 5.20.1, PEFT 0.21.2 and huggingface-hub 1.33.0.
The experimental package's `model` extra records those versions. The local
model environment is `artifacts/model-env/bin/python`.

```bash
MODEL_PYTHON=/path/to/model-environment/bin/python
MODEL_CHECKPOINT=/path/to/verified/pinned/checkpoint
PYTHONPATH=packages/simjecture-monitor/src "$MODEL_PYTHON" \
  -m simjecture_monitor.server --checkpoint "$MODEL_CHECKPOINT" \
  --socket /tmp/monitor-replay.sock --status /tmp/monitor-replay-status.json \
  --wall-seconds 3600 --idle-seconds 900
```

In a second terminal, use a new root for each trial/collection:

```bash
.venv/bin/python packages/simjecture-monitor/scripts/collect_sampled.py \
  --root /path/to/new-collection --socket /tmp/monitor-replay.sock
.venv/bin/python packages/simjecture-monitor/scripts/export_returns.py \
  --root /path/to/new-collection --output /path/to/new-returns.json
PYTHONPATH=packages/simjecture-monitor/src "$MODEL_PYTHON" \
  packages/simjecture-monitor/scripts/train_returns.py \
  --base "$MODEL_CHECKPOINT" --data /path/to/new-returns.json \
  --output /path/to/new-training-output
```

The collection is stochastic even with fixed action-sampling seeds, because
native worker continuations can differ. Exact prompt and initial probability
checks are required before optimization. Preserve negative episodes and model
coverage failures; do not replace them with invented reward labels.

To evaluate, start separate base and adapted servers (add `--adapter` to the
second), then run:

```bash
.venv/bin/python packages/simjecture-monitor/scripts/evaluate_adapter.py \
  --root /path/to/new-evaluation --base-socket /tmp/base.sock \
  --adapter-socket /tmp/adapted.sock --probe-data /path/to/returns.json
```

The script checks that the two endpoints expose the same checkpoint
configuration, that only one has adapter weights, and records their hashes.
It runs paired contemporary base/adapter trajectories, with at most two parent
workers active. Agent/director/helper activity can add concurrent child roles.
The runtime and compute lease must be managed separately; these scripts do not
allocate Colab or authorize unbounded compute.
