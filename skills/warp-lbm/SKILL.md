---
name: warp-lbm
description: Install and use the contributed NVIDIA Warp D2Q9 MRT lattice-Boltzmann cylinder-flow solver for 2D fluid wakes, force measurements and controlled rotation or stationary shape studies.
---

# Cylinder flow with Warp-LBM

Zifei Meng contributed this solver and its Re=100 validation records under
Apache-2.0. NVIDIA Warp compiles its Python kernels for CUDA or CPU execution.
This capability models isothermal, weakly compressible 2D hydrodynamics.

Use `simjecture install warp-lbm`, then `simjecture doctor --profile warp-lbm`.
The managed capability is `warp-lbm-cylinder-1.0`. Its source and validation records
are read-only under `share/source`; the build record identifies the actual source
and pinned Warp/NumPy versions. A working installation establishes execution
readiness, not the accuracy of a new scientific setup.

## Execution and measurements

Copy `examples/run_cylinder.py` into the project and execute it with this
capability, following the generated `lab.py` guide. The script accepts parameters
documented in [the interface guide](references/interface.md), including Reynolds
number, grid, physical domain, rotation, shape, boundary choice and output folder.
Ordinary project Python does not automatically contain the optional Warp runtime.
In chat, label solver runs as simulations and postprocessing as commands.

The driver writes `summary.json`, `forces.npz`, `forces.csv`, `fields.npz` and
`evolution.png`. Use a fresh output folder for each experiment. Read NPZ arrays
with NumPy rather than placing a complete force history in model context.
The summary records source hashes, configuration, boundaries, time convention,
precision, units and the statistical window. Field output is a labelled final
wake crop; it is not the whole domain or a time-averaged field.

Time is `tU/D`, distances are cylinder diameters, and lift/drag are normalized
by `0.5*rho0*U^2*D` per unit span. Rotation is surface speed divided by inflow
speed. Statistics use complete lift periods; insufficient or undetectable periods
are recorded explicitly. Steady flow need not have a shedding frequency.

For quantitative claims, choose relevant grid, domain, low-Mach and averaging
controls. Changing upstream distance while holding the outlet fixed requires
changing total domain length too. A small change between two grids does not
establish an error bound relative to the continuum solution. Read
[the validation and scope notes](references/validation.md) when choosing controls.
Use exploratory execution for commissioning and the existing source-bound methods
and claim review for research evidence. Modified solver copies are allowed in the
project; retain their source identity and qualify the changed numerical method.
