---
name: elmer
description: Run Elmer finite-element and multiphysics models from user-authored SIF files, convert meshes with ElmerGrid, and inspect solver output. Includes optional conductor and RLC examples from local experience.
---

# Elmer

Use `elmer-0.1` for the installed Elmer runtime. Users choose the physics,
materials, boundary conditions, solver modules, time integration and mesh in
ordinary Elmer input files. The capability does not require the conductor
example's JSON schema or numerical method.

The native executables are `$ELMER_SOLVER` and `$ELMER_GRID`;
`$ELMER_HOME` locates modules and resources. In a capability Python program:

```python
import os, subprocess

subprocess.run([os.environ["ELMER_SOLVER"], "case.sif"], cwd="case", check=True)
```

An optional launcher at `$SIMJECTURE_ELMER_DRIVER` records logs, resource limits
and runtime identity. Invoke with the capability Python:

```text
$SIMJECTURE_ELMER_DRIVER grid case -- 14 2 load.msh -out mesh
$SIMJECTURE_ELMER_DRIVER solver case --timeout 900 --memory-gib 8 -- case.sif
```

Everything after `--` passes to Elmer unchanged. Native launch remains available
for other launch arrangements, including MPI builds with a configured launcher.
The recorded helper runs a single process, with configurable OpenMP threads.
It never rewrites the SIF or requires a model-specific audit. Process success
and physics validation are separate; choose physical controls for the question.

Read [installation](references/installation.md) for setup and
[local solver experience](references/local-experience.md) when investigating
convergence, memory or reduced conductor models. The installation smoke test is
a small **heat-conduction** problem, independent of the EM example.

The same reference covers feed/current-path redesign and exporting fields to
another solver: circuit agreement alone does not qualify the spatial handoff.

For a ready-made cold-conductor A-v or finite-capacitor RLC starting point, read
[the optional conductor interface](references/case-interface.md) and use
`$SIMJECTURE_ELMER_CONDUCTOR_DRIVER`. Its mesh, solve, audit and plot stages have
specific physical assumptions documented there. Those assumptions apply to that
example, not to Elmer as a whole. Shared output can be inspected with ordinary
Python/PyVista; see the `python-experiment` visualization reference.
