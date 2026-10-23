---
name: elmer-em
description: Run experimental 3D transient conductor and circuit simulations with Elmer, including mesh preparation, prescribed-current or RLC drive, numerical checks, and field plots. Use when solid-conductor current division or eddy currents matter; use magnetic screening for inexpensive prescribed-filament field estimates.
---

# Elmer conductor and circuit workflow

One capability, `elmer-em-0.1`, provides mesh preparation, solve, audit and plot
stages over a shared case directory. It solves a connected, linear,
nonmagnetic conductor network in air with the A-v formulation. Conductivities
and geometry stay fixed. It does not model heating, plasma evolution, motion,
nonlinear magnetic materials or displacement-current waves.

Read [the case interface](references/case-interface.md) before preparing a
model. Read [installation](references/installation.md) when the capability is
missing. The installed driver is `$SIMJECTURE_ELMER_DRIVER`. Invoke it through
`lab.run` using the capability's Python executable:

```python
import os, subprocess, sys

subprocess.run(
    [sys.executable, os.environ["SIMJECTURE_ELMER_DRIVER"], "wire-demo", "wire-control"], check=True
)
```

For a custom case, use `mesh CASE --config input.json --msh load.msh`, then
`solve CASE`, `audit CASE`, and `plot CASE`. Mesh preparation converts and checks
an already generated Gmsh mesh. Gmsh is included for writing CAD-specific mesh
scripts; inspect physical tags and units before conversion. The bundled wire
demo generates its mesh and runs every stage. Add `--rlc` for the independent
synthetic discharge control. Keep trial directories distinct when changing a
mesh, time step, source or solver build.

The solver stage is bounded by elapsed time and per-process address space;
observed peak process RSS is recorded separately. It rejects known iterative
breakdown warnings even if Elmer exits zero. Audit requires every step's VTU,
independent current integrals and backward-Euler energy accounting. Plot refuses
failed or changed results. An interrupted solve must be rerun in a fresh case;
native state files are optional (`save_state: true`), and this interface has no
qualified restart.

Passing conservation checks is not a convergence study. Compare observables
across mesh size, time step, cut position and outer-air boundary as relevant.
Backward Euler's numerical energy dissipation can be large even when energy
closure passes. Do not quote a failed smaller-step run as convergence evidence.
The preflight's analytic wire check qualifies only that control on the supplied
build, not arbitrary CAD or driver parameters.

For a truncated load, retain connected feed/return paths and declare the two
terminal groups. The cut's magnetic-insulation boundary is an approximation;
check cut and outer-domain sensitivity. Source R/L values fitted to a complete
short-circuit fixture need that fixture's retained impedance removed before
being assigned upstream of the cut. Two pulse metrics do not identify R, L and
C uniquely. Record assumed capacitance, effective voltage, omitted prepulse and
source provenance. No machine-specific calibration is built in.

Known stock BiCGStabL builds can stop with negative Gram/residual norms while
reporting normal process completion. This tool detects the failure; it does not
silently install a numerical patch. If trying another build, preserve its
identity and independently rerun the controls before accepting new results.
