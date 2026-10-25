# Reproducing the raw-observation comparison

The comparative collector includes the scheduling and receipt-consumption corrections
recorded in the final cohort's `DESIGN.json`. The baseline, model prompt,
actor task and scientific fixtures remain unchanged from the pre-main
`8227075` freeze. Later changes correct scheduling of explicit helper waits, already acknowledged feedback
and readiness of the private model socket; see [protocol](PROTOCOL.md).
Use an isolated checkout when replaying that revision. Do not change the source
files listed in a running cohort's `DESIGN.json`; the controller checks their
hashes before every assignment.

## Retained local artifacts

The local research worktree is
`/home/tomzhu0225/src/simjecture-monitor-coprocessor` and the experiment root is
`artifacts/generalization-20261025`. Raw physical outputs, native transcripts,
observations, independent measurement receipts and process identities remain
there; compact exports do not replace those records.

- `POLICY_FREEZE.json`: original operational comparator and model/action-code freeze.
- `FINAL_POLICY_FREEZE.json`: pre-main scientific-check composition, absolute
  quantity contract and complete task/source hashes.
- `V2_POLICY_FREEZE.json` and `V3_POLICY_FREEZE.json`: scheduling/startup amendments;
  immutable policy/task/scientific-fixture identities are checked against the original.
- `commissioning-v1` and `commissioning-v2`: four excluded setup runs each. Their
  scientific contracts differ; do not pool their results.
- `main-v1`: discarded scheduling-defect cohort. Eight assignments started, six
  ended and two were interrupted; the other 56 never started. Preserve
  `COLLECTION_INTERRUPTED.json`, the original 64-assignment manifest and every trace.
- `scheduler-check-v1`: excluded real required-helper scheduling check; the
  helper returned actual scalar calculations, the parent acknowledged them, and
  the independent final numerical/quantity checks passed. `scheduler-check-v2`
  repeats this check after the receipt-consumption correction; the main phase
  requires it to pass before any comparative assignment.
- `main-v2`: startup-only failure between socket bind and listen, with zero native
  assignments and zero model inferences.
- `main-v3`: discarded receipt-consumption race, with 10 ended and two interrupted
  trajectories; all 64 assignments remain recorded.
- `main-v4`: the 64-assignment comparative cohort after those corrections.
- `replay-v1`: prespecified matched-input replay from the observation-only arm.
- `native-budget.json`: all stages share one metered lease. Its original absolute
  expiry, ten starts per trajectory and four simultaneous native roles are retained.

## Audit and exact-input replay

In the original worktree, the existing `.venv` has the experimental package
installed. Recompute the audit without launching any native worker or model:

```bash
.venv/bin/python packages/simjecture-monitor/scripts/audit_generalization.py \
  --root artifacts/generalization-20261025/main-v4 \
  --budget artifacts/generalization-20261025/native-budget.json \
  --output /tmp/generalization-audit
```

The audit retains every assigned row, including failed, incomplete and never-started
rows. It reconciles immutable report/result hashes, observed packet hashes,
quality receipts, actual native starts and source files at the collection commit.
It exports correctness components separately; an incorrect or stale pipeline
quantity is distinguishable from a correctly reported final quantity.

The additional evidence tags describe published raw source identity, absolute
quantity, input-pattern or loss-history discrepancies. They are post-collection
measurements. They were never supplied as labels to a monitor or worker, and
are not independently validated ground-truth action labels.

After all main processes and the model server have stopped, an optional new
replay directory can be generated with:

```bash
.venv/bin/python packages/simjecture-monitor/scripts/replay_generalization.py \
  --source artifacts/generalization-20261025/main-v4 \
  --output /absolute/path/to/new-replay-directory
```

Selection uses only the first parking interval of each observation-only
trajectory: first snapshot at or after 10, 25, 40 seconds and strictly before that
interval ends. Missing snapshots remain missing; no later interval substitutes.
All policies receive the exact selected packet. The hybrid reuses the same
unchanged greedy model prediction only when the scientific-check-aware rule
policy defers. The archived operational-only comparator is also reported.
Packet, rendered-prompt and model-view identities remain in the replay receipts.

## Fresh collection

A fresh experiment requires an authenticated native Codex CLI and the exact
scientific resources configured in `scripts/live_trials.py`. Read the original
WarpX setup record in the main checkout's
`artifacts/colab-smoke/20261020/REPORT.txt` and `REPRODUCE.txt` before changing
build assumptions. The actual controls use 64 cells/40 steps and 128 cells/80 steps,
with independently measured saved fields. Diagnostic/publication delays are
controlled experimental pacing, not natural simulation runtime.

The pinned base is `internlm/Intern-Decision-4B` revision
`38c9dafbbef52dd04bae943c0c6ac918419adfd5`, locally under
`artifacts/models/Decision-verified`. The optional validated FLA prefill runtime
is in `artifacts/model-fast-env`. No adapter is loaded. The model server enforces
60% of local GPU memory, a six-hour wall limit and a 30-minute idle limit. Separately recorded archived warmups keep the model resident across long rule-only
blocks; they do not use study inputs or dispatch actions, and retain the absolute
six-hour bound. Never stop unrelated GPU processes to make room.

Create a new shared root and record a new `POLICY_FREEZE.json` containing
`frozen_at`, `source_revision`, `scope` and a `files` mapping of these relative
paths to their SHA256 byte digests: `generic_policy.py`, `model.py`, and
`policy.py` under `packages/simjecture-monitor/src/simjecture_monitor/`.
Use the pinned original policies; changing them constitutes a new study.
The runner creates a native executable wrapper and, if absent, a six-hour lease
with 288 starts, ten per trajectory and four simultaneous native roles. The
historical 512-start amendment covered discarded runs and is not a requirement
to reopen an old lease. Retain any resource-censored assignments if a fresh
study reaches its declared cap.

Run each phase with a new root and inspect its results before proceeding:

```bash
.venv/bin/python packages/simjecture-monitor/scripts/run_generalization_study.py \
  --shared /absolute/new-shared-root \
  --root /absolute/new-shared-root/commission --phase commissioning
.venv/bin/python packages/simjecture-monitor/scripts/run_generalization_study.py \
  --shared /absolute/new-shared-root \
  --root /absolute/new-shared-root/scheduling --phase scheduler-check
.venv/bin/python packages/simjecture-monitor/scripts/run_generalization_study.py \
  --shared /absolute/new-shared-root \
  --root /absolute/new-shared-root/main --phase main \
  --commission /absolute/new-shared-root/commission \
  --scheduler-check /absolute/new-shared-root/scheduling
```

The main phase requires passing scientific commissioning and actual returned,
acknowledged required help. Its design records all64 assignments, counterbalanced
arm blocks, two simultaneous parent controllers, source hashes and native lease.
Provider histories are fresh; equal physical seeds do not clone private agent
state or control future model sampling. All failures remain part of the cohort.

These fixed greedy observations are evaluation records, not sampled PPO data.
No training or test-driven reward-weight search belongs in this comparison.
