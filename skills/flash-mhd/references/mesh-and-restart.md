# Prescribed refinement, source porting and checkpoint continuity

Read when changing a FLASH mesh, MPI decomposition or application overlay.
Use the active study to choose the domain, refinement placement and scientific
tolerances. A prior demonstration supplies debugging methods, not those choices.

## Inspect the realized mesh

Distinguish gradient-triggered adaptation, prescribed coordinate regions and
a fixed single-level grid. A multilevel initial picture proves neither dynamic
feature tracking nor stable transport across refinement interfaces.

For PARAMESH HDF5, select leaf blocks using `node type`, then inspect their
`refine level` and `bounding box` together with the actual field-array shape.
Derive each cell edge from its block extent divided by the number of interior
cells on that axis. Verify the axis/storage convention and guard-cell policy
against the exact output schema. Do not infer cell sizes from a requested
`lrefine_max` or count parent blocks as independent physical cells.

Check domain extents, leaf-cell totals and the realized finest/coarsest regions.
Overlay actual cell lines where a claim depends on a slit, curved electrode,
near-axis layer or material interface; label block boundaries separately.
Measure an inlet's discrete width from the realized coordinates. Check that
coarse/fine transitions do not erase narrow flow or forcing regions.

In a commissioning pilot, inspect initial and evolved thermodynamic fields,
species normalization and applicable fixed-solid velocities. A valid initial
state does not exclude a first-step reconstruction/EOS failure. A zero-field
loading test does not qualify nonzero-field magnetic diffusion across levels.
If block dimensions and refinement placement change together, keep that
confounding explicit; a passing combined change does not identify a sole cause.

## Qualify a restart before extending it

Freeze the executable, unit selection, parameter file and checkpoint identity.
Before changing MPI ranks, determine whether this build redistributes PARAMESH
blocks or reconstructs a fixed uniform decomposition. A different rank layout
can affect spatial interpretation; a successful checkpoint read is insufficient.

Compare a restarted initial output with its source checkpoint in physical
coordinates, not by block-index order. Check domain/material masks, field values,
particle-free source states where relevant and any intentionally changed regions.
Then advance a bounded interval and compare with an uninterrupted control when
restart equivalence matters. Preserve actual ranks, topology and CPU quota.
Qualify each new layout rather than extrapolating one successful redistribution.

Separate loading, discharge and other physical phases. An explicit stage
transition may reset a material or source once; an ordinary discharge continuation
must not silently reapply initialization. Preserve physical time, source schedule
and restart flags. A requested target is different from the last completed plot
or synchronized checkpoint; report both when an operator stops early.

## Port the active implementation

When moving an application to another FLASH version, trace the compiled caller
chain and inspect the selected object/symlink map. An old same-named boundary or
resistivity routine can remain present without being called by the active solver.
Verify coefficient units and activation in realized field data or a native probe.

Do not equate mechanical fixed-solid flags with magnetic or thermal boundary
conditions. Inspect each operator's internal-boundary treatment and distinguish
finite material diffusion from an imposed zero-field constraint. Keep experimental
overrides in the authorized application workspace and preserve the reference
installation. Source access does not authorize source redistribution.
