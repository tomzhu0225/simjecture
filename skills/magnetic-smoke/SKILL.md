---
name: magnetic-smoke
description: Run inexpensive three-dimensional Biot-Savart checks on prescribed-current coil and return-path centerlines. Use for geometry screening and independent field checks, not for solving driver/load currents, skin effects or plasma evolution.
---

# Prescribed-current magnetic screening

The `magnetic-smoke-1.0` capability is a Python runtime with NumPy and an
identity-bound driver at `$SIMJECTURE_MAGNETIC_DRIVER`. Load that file with
`importlib.util.spec_from_file_location`, then call `run_case(case)` or
`polyline_field(points_m, vertices_m, current_a, exclusion_radius_m=...)`.
The driver also accepts `--case input.json --output result.json`.

Use the advertised capability with `lab.run` and keep the case and outputs
inside the experiment workspace. A source program can launch the driver with
`subprocess.run([sys.executable, os.environ["SIMJECTURE_MAGNETIC_DRIVER"],
"--case", "input.json", "--output", "field.json"], check=True)`.
This CLI route records input and driver hashes; callers of the Python functions
must retain their inputs and source identity in the experiment record.

Inputs use `schema_version: "1.0"`, `units: "SI"`, `probes` containing unique
`name` and `position_m`, and `paths` containing unique `name`, `vertices_m`,
`current_a` and optional `exclusion_radius_m`. Current follows vertex order.
The field is the exact sum of finite straight-segment integrals. A helix is
still a polygonal approximation; repeat with more vertices to check resolution.
Probe points on or inside a path's exclusion radius are rejected. This radius
does not model a solid conductor or regularize its field.

Record where each current came from. If it came from another solver or a
measurement, any agreement tests the geometry-to-field conversion only.
Report field vectors as well as magnitudes, and identify omitted return paths.
Open paths represent contributions from part of a circuit; close the physical
current network before treating the sum as a complete assembly field.

This tool assumes linear free space and prescribed, instantaneous currents.
It cannot predict load-dependent pulse shapes, branch-current redistribution,
skin/proximity effects, heating, mechanical motion, or plasma behavior. Those
require a separately qualified field/circuit solver. A passing circular-loop
health check does not qualify this approximation for an experiment or optimizer.
