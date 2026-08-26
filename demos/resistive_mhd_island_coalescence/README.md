# Resistive-MHD island-coalescence campaign seed

This package is an experimental guided starting point for asking Simjecture to
rediscover a Sweet-Parker-like resistive-MHD branch and then look for its
boundary. It is intentionally one rung below the fully kinetic reconnection
demonstration: inexpensive fluid runs can establish the classical branch and
separate a numerical failure from a reason to commission Hall, hybrid, or
fully kinetic physics.

The package contains an independently authored controller and analyzer, a
known-runnable application anchor, an independent resistive-operator
validation summary, and concise literature context. The 21 MB raw anchor
output is ignored by Git. Every supplied result is permanently non-evidentiary;
only fresh outputs collected after prospective claim and instrument contracts
may affect the hypothesis tree.

The operator must obtain FLASH from the
[official FLASH distribution](https://flash.rochester.edu/site/flashcode/)
and accept its separate terms. Simjecture does not download or redistribute
FLASH source or binaries. After the local capability has been prepared:

```bash
uv run simjecture doctor --profile flash

uv run simjecture mvp \
  --hypothesis-file demos/resistive_mhd_island_coalescence/hypothesis.txt \
  --instruction-file demos/resistive_mhd_island_coalescence/campaign_instruction.txt \
  --guided-commission demos/resistive_mhd_island_coalescence/guided_commission.json \
  --output artifacts/resistive-mhd-island-coalescence \
  --ledger artifacts/resistive-mhd-island-coalescence/mvp_ledger.sqlite3 \
  --max-wall-seconds 14400 \
  --max-command-seconds 900 \
  --max-workspace-mb 4096 \
  --max-file-mb 128 \
  --max-memory-mb 16384
```

The autonomous campaign remains free to choose the resistivities, grids,
analysis implementation, fit rule, controls, and any sub-hypothesis. The
guided package supplies a working instrument, not the answer.
