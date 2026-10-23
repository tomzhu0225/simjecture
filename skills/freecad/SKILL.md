---
name: freecad
description: Create and edit parametric CAD, perform solid Boolean operations, and exchange STEP or BREP geometry using headless FreeCAD Python. Use for geometry design before meshing or simulation.
---

# FreeCAD

The `freecad-1.1.3` capability runs Python with `FreeCAD` and `Part` available.
Use ordinary FreeCAD APIs and user-authored scripts through `lab.run`. The
runtime supports general CAD work; no coil geometry or FEM topology is assumed.
Install with `simjecture install freecad`; check with
`simjecture doctor --profile freecad`. The managed Conda environment supplies
FreeCAD's matching Python and native libraries; do not import its extensions
into the application's unrelated Python interpreter.

```python
import FreeCAD as App
import Part

doc = App.newDocument("part")
body = doc.addObject("PartDesign::Body", "Body")
# For parametric history, create sketches/features in the document.
# For a scripted solid operation:
shape = Part.makeBox(20, 10, 5).cut(Part.makeCylinder(2, 5, App.Vector(10, 5, 0)))
assert shape.isValid()
shape.exportStep("part.step")
```

`FreeCAD`/`Part` work without the GUI. Avoid importing `FreeCADGui` in a headless
batch job unless a display and GUI application were explicitly arranged. Save
`.FCStd` when editable feature history matters; STEP preserves geometry for
exchange, not the original sketch/feature history.

Read [geometry handoff](references/geometry-handoff.md) when passing CAD to Gmsh
or a solver. The bundled `examples/health_check.py` checks a Boolean solid and
STEP round trip with volume and dimensions. FreeCAD was added after the local
coil study; those original cuts were made through Gmsh/OpenCASCADE, not FreeCAD.
