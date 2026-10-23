# Experimental conductor and circuit simulation with Elmer

The **Elmer 3D electromagnetics** tool adds a single workflow for mesh preparation,
transient conductor solves, current/energy checks and plots. A prescribed-current
filament screening tool answers a cheaper geometry question; Elmer solves how
current divides inside solid conductors, including transient eddy currents and
an optional finite-capacitor RLC discharge.

The first release adopts an operator-supplied Linux Elmer installation:

```bash
SIMJECTURE_BOOTSTRAP_PYTHON=/path/to/python3.12 \
  simjecture install elmer-em --source /path/to/elmer-install
simjecture doctor --profile elmer-em
```

The [elmer-em skill](https://github.com/tomzhu0225/simjecture/blob/main/skills/elmer-em/SKILL.md)
provides the agent interface and links to the case schema and installation
requirements. The public `wire-demo` creates a Gmsh mesh, solves, checks an
analytic field and plots the result. Add `--rlc` for a synthetic circuit control.
Custom CAD models supply an MSH2 mesh plus named materials, terminals, probes and
straight current-integration regions. Mesh, solve, audit and plot are stages of
one case record rather than separate tool-library entries.

This is an experimental, single-process A-v workflow for fixed, nonmagnetic
conductors in air. It does not model plasma, heating or mechanics. A zero solver
exit is insufficient: known iterative breakdowns, missing steps, failed current
balance or failed discrete energy balance reject the case. Backward-Euler
numerical dissipation is recorded explicitly. Mesh, time-step and boundary
sensitivity still need separate studies, and the RLC source needs independent
calibration. The package includes neither private coil CAD nor machine-specific
source fits, and applies no local Elmer patch automatically.
