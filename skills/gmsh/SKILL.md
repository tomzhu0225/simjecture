---
name: gmsh
description: Import or construct geometry, perform OpenCASCADE operations, define physical groups, and generate finite-element meshes using Gmsh's Python API or native command-line interface.
---

# Gmsh

Use `gmsh-4.15.2` with a Python script importing `gmsh`. Install with
`simjecture install gmsh`; check with `simjecture doctor --profile gmsh`.
The runtime includes Gmsh, its OpenCASCADE geometry support, meshio and the GLU
library needed by the headless wheel. It supports user-selected dimensions,
element types, algorithms and physical groups.

```python
import gmsh

gmsh.initialize()
try:
    gmsh.model.occ.importShapes("part.step")
    gmsh.model.occ.synchronize()
    # Inspect imported units, entities and interfaces before tagging/meshing.
    # Define physical groups for the downstream solver here.
    gmsh.model.mesh.generate(3)
    gmsh.write("part.msh")
finally:
    gmsh.finalize()
```

For native `.geo` input, run the installed entrypoint using the capability's
Python: `subprocess.run([sys.executable, os.environ['GMSH_EXECUTABLE'],
'part.geo', '-3', '-o', 'part.msh'], check=True)`.

Read [local meshing experience](references/local-experience.md) for CAD cuts,
refinement cost, connectivity and Elmer handoff. The example health check meshes
a perforated block and checks physical groups and positive element Jacobians.
These checks exercise the installation; choose quality and resolution criteria
for each model.
