# FuZE: prescribed refinement and controlled solver development

This is a retrospective excerpt of LCB119's operator-assisted FLASH and WarpX
experiments, retained on 4 November 2026. Read the
[illustrated walkthrough](../../docs/demos/fuze-mesh-solver-diagnostics.md).

- FLASH 4.8 gas loading reached **43.219701 µs** on a prescribed five-level
  PARAMESH mesh: **199,800 leaf cells**, with cell edges from 2 to 0.125 mm.
- A modified native WarpX RNG checkpoint candidate reproduced five resumed
  frames of a short continuous trajectory with maximum recorded relative L2
  **1.67869e-12** across 13 fields, below the study's 1e-10 regression criterion.
- With the starting checkpoint and RNG state controlled, enabling the candidate
  QDSMC axis boundary still produced near-axis transients. The candidate was
  **not adopted as a repair**.

These are separate development branches, not a coupled FLASH–WarpX simulation
or a formally adjudicated scientific campaign. Neither a complete FuZE discharge
nor convergence or experimental agreement is established.

## Verify the excerpt without solvers or credentials

```bash
python3 demos/fuze_mesh_solver_diagnostics/verify_record.py
```

Python 3.11+ and its standard library suffice. Verification checks retained
hashes, mesh/partition accounting, the reported 13-field regression arithmetic,
RNG identities, rejection controls, matched times and checkpoint particle mass.
It preserves the rejected axis-candidate decision. It does **not** recompute
field norms or RNG restoration from raw outputs that are not distributed.

| Retained file | Contents |
|---|---|
| `record/study.json` | Human framing, agent work, review scope, software and build identities |
| `record/flash.json` | Actual mesh, paused checkpoint audit, launcher tail and 8-to-20-rank probe |
| `record/restart.json` | Default-off regression, split/continuous norms, RNG identities and rejection controls |
| `record/axis.json` | Same-state axis on/off control, 30 saved-frame summaries and rejected-candidate decision |
| `record/provenance.json` | Relative source-file identities, original hashes and editorial transformations |
| `manifest.json` | SHA-256 inventory of the five public records and two unmodified figures |

The base WarpX commit identifies an already modified native development build;
the v7/v8 executable hashes distinguish local candidates. This case does not
extend the advertised dimensionality or physics of Simjecture's packaged WarpX
26.07 capability. The exact Simjecture application Git commit was not retained;
the installed version was 0.7.0.

## Regenerate from the original local records

```bash
python3 demos/fuze_mesh_solver_diagnostics/export_record.py \
  --flash /path/to/flash_AMR \
  --warpx /path/to/case_015_prescribed_CS3 \
  --warpx-project /path/to/install-warpx-cuda/files
python3 demos/fuze_mesh_solver_diagnostics/verify_record.py
```

The exporter reads the specific completed audits identified by run numbers and
copies two figures without alteration. It whitelists JSON fields and removes
host paths and resource samples. It neither launches simulations nor modifies
the original campaign. Use `--repository` to export into a separate directory.

Original HDF5/AMReX fields, particles, RNG sidecars, binaries, full inputs and
solver source are not included. Source hashes bind this excerpt to local audit
files; they do not enable raw-data reanalysis or a turnkey solver rerun. Some
older FLASH trials were cleaned up in the original project; this excerpt uses
the retained V5 archive, not deleted trial outputs. FLASH-owned code, material
tables and third-party paper PDFs are excluded.

Human framing, steering and the contribution are credited to **LCB119**. Agents
performed local development, simulations and working-assistant audits; this
export and walkthrough are later editorial work. No independent formal
scientific acceptance is claimed.
