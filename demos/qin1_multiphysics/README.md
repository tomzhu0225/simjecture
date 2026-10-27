# Qin-1: hardware design, circuits and 3D plasma

An operator-assisted local study on 23–24 October 2026 connected CAD changes,
Gmsh meshing, Elmer/circuit calculations, a checked static-field transfer, native
3D WarpX hybrid PIC and Python/PyVista visualization. Read the
[illustrated case study](../../docs/demos/qin1-hardware-plasma.md).

The selected cold-conductor design increases the sampled upstream transverse
field by 33–34% across matched numerical refinements while retaining about 97.8%
of the original array-branch current. The plasma simulations show a conditional
compression/deflection response. All five reference bulk-flux sensitivity checks
fail their 10% tolerance; density-edge shifts remain below 0.11 mm.

This was host execution using Simjecture's tools and skills, an operator-supplied
native WarpX build and custom scripts. It was **not a formal harness-adjudicated
campaign**, and it does not establish a verified bow shock, a complete
exploding-wire shot prediction or a fabrication-ready design.

## Inspect the retained excerpt

```bash
python demos/qin1_multiphysics/verify_record.py
```

Python 3.11+ and its standard library suffice. The verifier checks retained-file
hashes, recalculates the EM ratios and five plasma comparisons, checks execution
status consistency, and matches the viewer's 200 ns readouts to the numerical
record. It does not run a solver or verify raw fields that are not distributed.

- `record/study.json`: human framing, agent work, software identities and scope.
- `record/em.json`: sampled field/current histories and matched refinements.
- `record/plasma.json`: common-window measurements, profiles and sensitivity results.
- `record/model.json` and `comparison-plan.json`: assumed plasma, source,
  boundaries, observables and the dated evolution of the comparison plan.
- `record/checks.json`: CAD/EM/import checks and all nine production execution outcomes.
- `record/raw-source-identities.json`: identities of the original local 200 ns diagnostics.
- `record/provenance.json`: original source-file hashes and editorial changes.
- `../../docs/_static/demos/qin1/`: retained figures and the standalone viewer.

Seven plasma runs reached the requested 220 ns. The original-device run timed
out, and the fine-grid run was interrupted by the host shutdown; both retained
finite 200 ns outputs. A shared completed observation window does not relabel
those requests as successful full runs.

## Export and reproduction boundary

The public excerpt omits raw VTU/openPMD volumes, CAD files, installed solvers
and private host paths. The hash inventory identifies the local sources; their
absence prevents independent raw-output reanalysis from this checkout alone.
The original local campaign preserves the complete report and reproduction
scripts. This repository excerpt is not a turnkey solver rerun.

Maintainers with that campaign can regenerate the excerpt without launching
simulations:

```bash
python demos/qin1_multiphysics/export_record.py --campaign /path/to/overnight-campaign
python demos/qin1_multiphysics/verify_record.py
```

The exporter takes existing terminal records, copies the four selected figures,
removes absolute host paths from structured metadata, and changes only the
viewer's report link and label. Numerical arrays and figure content are retained.
Publishing an updated record does not make it a new numerical experiment.
