# Magnetic geometry screening without commercial software

`magnetic-smoke` evaluates three-dimensional fields from prescribed polyline
currents using the finite-segment Biot–Savart integral. It is useful for checking
coil dimensions, orientation, units and return-path contributions before a
larger field solve. It is an optional NumPy capability, with no commercial
software or graphics dependency.

Install with Python 3.12 or later available to the bootstrap:

```bash
SIMJECTURE_BOOTSTRAP_PYTHON=/path/to/python3.12 simjecture install magnetic-smoke
simjecture doctor --profile magnetic-smoke
```

It also appears as **Magnetic geometry screening** in the workspace tool library.
Read the `magnetic-smoke` skill for the capability interface. A standalone case
can be run from a source checkout with:

```bash
python -m conjecture_solver.magnetic_smoke --case case.json --output field.json
```

For example, this square loop carries 1 kA counterclockwise when viewed from +z:

```json
{
  "schema_version": "1.0",
  "units": "SI",
  "probes": [{"name": "center", "position_m": [0, 0, 0]}],
  "paths": [{
    "name": "loop",
    "current_a": 1000,
    "exclusion_radius_m": 0.001,
    "vertices_m": [
      [-0.01, -0.01, 0], [0.01, -0.01, 0],
      [0.01, 0.01, 0], [-0.01, 0.01, 0], [-0.01, -0.01, 0]
    ]
  }]
}
```

The output contains each field vector, its magnitude, each path's contribution,
and hashes of the input and driver. The loop above gives about 0.05657 T along
+z. Refine curved centerlines, compare vectors as well as magnitudes, and record
the origin of every prescribed current. Open paths are partial circuit
contributions; identify omitted returns when interpreting their sum.

The installer binds the driver, dependency record and requirements into the
capability identity. The health probe checks a circular loop and finite wire
against analytic solutions. Normal methods review, source sealing and
commissioning gates still apply before scientific evidence can be recorded.

This capability does not replace a transient solid-conductor solver. A matching
field obtained using another solver's branch currents does not independently
validate those currents or a load-dependent pulse. Driver/load coupling,
skin/proximity effects, heating and plasma evolution need a separately
qualified model. Gmsh/GetDP or Elmer may provide that next stage; this capability
does not install or claim qualification of either solver.
