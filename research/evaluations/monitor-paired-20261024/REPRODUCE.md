# Reproducing the checkpoint pilot

The collection code was committed at `d5e0763`; the actor-facing provenance
amendment was `010a7d9`, before any cohort continuation. Later audit code adds
strict feedback-need checks without modifying the collected outcomes. Use an
isolated worktree when replaying an older collection revision; leave other work
and the original artifact directory intact.

## Audit retained data

On the original machine:

```bash
uv sync --frozen --extra workspace --group docs
uv pip install --python .venv/bin/python -e packages/simjecture-monitor
.venv/bin/pytest packages/simjecture-monitor/tests -q
.venv/bin/python packages/simjecture-monitor/scripts/analyze_paired.py \
  --root artifacts/paired-20261024 --output /tmp/paired-audit.json
.venv/bin/python - <<'PY'
import json
from pathlib import Path
from simjecture_monitor.events import digest
data = json.loads(Path('artifacts/paired-20261024/OUTCOMES.frozen.json').read_text())
print(digest(data))
PY
```

The canonical outcome digest is
`10a058b2d14434565cc3fc25229b8b1114f8e4f8ca713220cfd67b5c202848c2`.
It hashes canonical JSON values, not the indentation/newline bytes of the file.
`MEASUREMENTS.json`, `STOCK_SOURCE_AUDIT.json`, `DESIGN.json`, original per-branch
`OUTCOME.json`, `RESTORE.json`, `QUALITY.json` and the incident ledgers remain in
that local root. The raw plotfiles, native streams and excluded commissioning
trials are retained. None is reconstructed from the published summary.

## Fresh native collection

This driver requires an authenticated native `codex` executable and the solver
and scientific Python paths declared in `scripts/live_trials.py`. The retained
WarpX executable is 1D CUDA double precision, SHA256
`13a427a60b87efd24a420bfd82d5149be956f98c2ff7df0c8aa32db8655a6519`.
Read the original `artifacts/colab-smoke/20261020/REPORT.txt` and `REPRODUCE.txt`
in the main Simjecture checkout before changing solver assumptions. A separate
clone needs access to those local artifacts and its own environment bindings.

Create a **new** artifact root. Initialize its `native-budget.json` with an
absolute `deadline`, `maximum_starts=240`, `maximum_per_continuation=12`,
`maximum_concurrent=4`, the absolute native `executable` and `starts=[]`.
Create an executable `native-codex` wrapper with the repository environment's
absolute Python shebang and this body:

```python
from simjecture_monitor.native_guard import main
main()
```

The budget and wrapper are required, not optional accounting decorations. The
runner supplies each child its continuation identity and absolute deadline.
Avoid reusing the completed study's lease, process IDs or runtime roots.

Before cohort collection, use `run_paired_pilot.execute` on new opaque IDs to
run an excluded `prefix` with `kind="protected-adapter"`, then a `continue`
with `action="request_repair_judge"`. Check its actual quality, scoped deployment
and acknowledgment receipts. Only then write `COMMISSIONING_PASS.json` with the
checked evidence and excluded IDs. The original passing commissioning records
are local reference material, not permission to skip a new environment check.

Run the fixed design and the two collection phases:

```bash
.venv/bin/python packages/simjecture-monitor/scripts/run_paired_pilot.py \
  design --root /absolute/path/to/new-root
.venv/bin/python packages/simjecture-monitor/scripts/run_paired_pilot.py \
  prefixes --root /absolute/path/to/new-root
.venv/bin/python packages/simjecture-monitor/scripts/run_paired_pilot.py \
  collect --root /absolute/path/to/new-root
```

The design fixes eight checkpoint templates, two repetitions, a randomized
branch order and 32 continuation UUIDs. Branches use fresh native sessions on
verified copies of the same artifacts and public transcript. Provider sampling
is not deterministic or controlled with a shared seed. Failed native outcomes
and skipped incomplete roots remain visible. Do not overwrite or silently rerun
them until a desired score appears.

## Fixed model probes

The separate model environment is
`artifacts/model-env/bin/python`, with the pinned checkpoint under
`artifacts/models/Decision-verified`. The V1 adapter is
`artifacts/overnight-20261023/training/run-01/adapter`. Run
`scripts/probe_checkpoints.py` once for the base and once with `--adapter`, using
new output directories and the same checkpoint cohort root. Raw predictions,
exact model-view receipts and encoded-input hashes remain in `probe-base/` and
`probe-v1-adapter/`. This is replay, not a learned-policy worker rollout.

The original legacy episode-return learner is unchanged. These prespecified
paired actions must not be exported as sampled PPO decisions. Unacknowledged
helper results without a pre-result requirement declaration withhold strict
feedback measurement; they do not acquire a zero penalty through cancellation
or report modification time.
