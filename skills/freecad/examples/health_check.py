"""Headless CAD Boolean and STEP export/import with volume and units checks."""

import json
from pathlib import Path

import FreeCAD as App
import Part

# FreeCAD's geometry API uses millimeters here.
shape = Part.makeBox(20, 10, 5).cut(Part.makeCylinder(2, 5, App.Vector(10, 5, 0)))
assert shape.isValid() and len(shape.Solids) == 1
expected = 1000 - 20 * 3.141592653589793
shape.exportStep(str(Path("part.step").resolve()))
restored = Part.Shape()
restored.read(str(Path("part.step").resolve()))
checks = {
    "valid_solid": restored.isValid() and len(restored.Solids) == 1,
    "volume": abs(restored.Volume - expected) < 1e-6,
    "units": abs(restored.BoundBox.XLength - 20) < 1e-8,
}
Path("freecad_health.json").write_text(
    json.dumps(
        {"checks": checks, "volume_mm3": restored.Volume, "version": App.Version()[:3]}, indent=2
    )
    + "\n"
)
assert all(checks.values()), checks
