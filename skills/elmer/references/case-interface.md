# Optional conductor example, version 0.1

These commands belong to `$SIMJECTURE_ELMER_CONDUCTOR_DRIVER`. They are a
specialized starting point; the general Elmer tool accepts native SIF models.

`mesh CASE --config input.json --msh load.msh` creates a new case. It requires
positive first-order tetrahedra, physical material and boundary tags, SI meter
coordinates, and one conductor connected through tetrahedron faces. Generate
`load.msh` with Gmsh's MSH 2.2 format; Gmsh is installed in the runtime. Geometry
cutting and CAD-specific physical-group selection belong in the experiment's
mesh script. Preserve that script and all CAD inputs in the experiment record.
The wire demo is a runnable public geometry example in the installed driver.

Example configuration for a 20 mm long cylinder carrying 1 kA toward −z:

```json
{
  "schema_version": "0.1",
  "units": "SI",
  "dt_s": 0.001,
  "steps": 2,
  "linear_tolerance": 1e-10,
  "materials": [
    {"tag": 100, "conductivity_S_m": 58000000},
    {"tag": 101, "conductivity_S_m": 0}
  ],
  "boundaries": {"input": [300], "ground": [301], "outer": [200]},
  "driver": {"kind": "constant", "current_A": 1000, "provenance": "Analytic control"},
  "probes": [{"name": "side", "position_m": [0.002, 0, 0]}],
  "current_regions": [
    {"name": "wire", "tags": [100], "direction": [0, 0, -1], "length_m": 0.02}
  ],
  "current_balances": [["wire"]],
  "limits": {"current_relative": 0.0001, "energy_relative": 0.001, "circuit_relative": 0.000001}
}
```

Each material tag maps to an Elmer body, recorded in `body-map.json`. Zero
conductivity represents air; every material has μr = 1. Boundary groups are
disjoint and must account for all physical surface groups. The driven terminal
has W = 1, the return terminal W = 0, with A-edge = 0 on all external surfaces.
Both terminal roles may contain multiple electrically equipotential faces.
This is one massive component with one FEM port, not arbitrary circuit topology.

`current_regions` integrate **J · direction over the volume, divided by length**.
They must represent complete straight sections with constant axial extent and
no side-current leakage. They are not arbitrary branch volumes. A direction
sets the sign; a sum such as `["coil_pin", "shell"]` compares the two branch
currents with the port, while `["return_rods"]` provides a separate check.
The geometry definition must justify each length and orientation. The tool
cannot infer that geometric justification from a tag alone.

Drivers:

- `constant`: positive `current_A` switched on at t = 0.
- `sine`: positive `current_A` and `peak_time_s`, giving
  I(t) = current_A sin(πt / (2 peak_time_s)). It continues sinusoidally;
  the caller chooses the simulated interval.
- `rlc`: nonnegative `R_ohm`, positive `L_H`, `C_F`, `V0_V`, and `provenance`.
  The capacitor starts at V0 and current at zero. The implicit equations are
  L di/dt + R i + v_FEM + u = V0 and C du/dt = i, where u = V0 − Vcap.
  This transformation represents finite stored energy, not a replenished bank.

`solve CASE --timeout 900 --memory-gib 8` uses the prepared SIF and preserves
logs and per-step fields. Set optional `save_state: true` to retain native state
files; these can be large, and restart replay is not qualified. The memory limit is address space for
a single process; it is not a measured RAM requirement or a scheduler limit.
The fixed solver recipe uses Hypre for W and unpreconditioned BiCGStabL for A-v.
It is experimental and may fail on large or ill-conditioned meshes. Failed
trials are retained. To change the recipe, make a distinct, reviewed driver
version; there is no automatic solver retry or silent tolerance relaxation.

`audit CASE` records `audit.json` and exits nonzero on failed checks. Current
errors use max(|I_port|, 1 A) as the denominator. FEM energy errors use cumulative
absolute port work, and include backward-Euler numerical dissipation. The audit
also checks element-field energy against the solver scalar, every saved time,
and circuit KVL, capacitor charge and energy for an RLC driver. Non-finite data,
missing fields and out-of-mesh probes fail the stage.

`plot CASE` requires an unchanged passing audit and writes `results.png`,
`results.pdf`, and `field-slice.png`. The field slice is the xy plane through the
first probe at the last saved time. VTU files retain full 3D fields for PyVista
or ParaView. Plots state the limited qualification; passing checks alone does
not establish experimental accuracy.
