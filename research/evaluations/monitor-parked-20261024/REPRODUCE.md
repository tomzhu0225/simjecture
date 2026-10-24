# Replay the parked-worker study

Raw local record:
`/home/tomzhu0225/src/simjecture-monitor-coprocessor/artifacts/parked-20261024`.
`DESIGN.json` freezes cohort assignments, excluded commissioning and source
revision. Collection was prepared at `c0ec726`, with the public-event polling
amendment committed as `15df989` before any commissioning trial. Replay that
amended collector to reproduce the original worker prompt/API, rather than
silently substituting later helper-interface changes.

Each `trial-*/LIVE.json` contains measured state/times, verification, usage and
ledger counts; `research/` retains the native worker's files and actual plot
files/solver receipts; `supervisor/` retains public native events;
`monitor/decision-*.json` retains exact packets/actions;
`monitor_authority/` and `repair-authority/` retain judge, proposer and applied
grants. `COMMISSIONING.json` is excluded from `RESULTS.json`. Global native-role
start records are in sibling `paired-20261024/native-budget.json`.

From the research worktree, recompute the compact audit without launching models
or workers:

```bash
.venv/bin/python packages/simjecture-monitor/scripts/audit_parked_study.py \
  --root artifacts/parked-20261024 \
  --budget artifacts/paired-20261024/native-budget.json \
  --output research/evaluations/monitor-parked-20261024
```

This checks assignments, completion/start accounting, saved quality receipts,
canonical report/result digests, feedback declarations and timestamp provenance.
The original independent scientific verifier analyzed every saved successful
control rather than trusting worker claims. Root-level artifact digests remain
in the compact audit; these raw plots and provider traces are local, not in Git.

A fresh collection uses `run_parked_study.py --root NEW_ROOT --pilot PILOT_ROOT`
with a newly prepared bounded native lease/wrapper, native Astra credentials,
the pinned base model and its isolated model environment. Never reuse an expired
lease or existing output root. The runner uses two parent controllers, four
native roles globally and one local resident model, with server idle/wall bounds.
The common CUDA executable and scientific Python environment are identified in
`../monitor-paired-20261024/REPRODUCE.md`; the earlier local Colab setup is
`/home/tomzhu0225/src/simjecture/artifacts/colab-smoke/20261020/REPORT.txt`.
No Colab runtime was allocated for this follow-up.

The Git records alone do not bundle the model, native authentication, executable,
scientific environment or raw plots. Fresh stochastic native sessions will not
reproduce exact timings or wording. These are fresh trajectories, not forks of
private reasoning/provider state or randomized common-seed pairs.
