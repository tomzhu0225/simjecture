# Cylinder flow with Warp-LBM

Simjecture includes an optional 2D cylinder-flow research tool contributed by
[Zifei Meng](https://github.com/ZifeiMengSPH), under Apache-2.0. It uses NVIDIA
Warp's GPU/CPU kernels for D2Q9 MRT lattice-Boltzmann hydrodynamics with a smooth
partially saturated solid boundary. NVIDIA Warp and WarpX are separate projects.

## Install and run

In **Research tools**, select **Cylinder flow → Install**. When the numerical
readiness check passes, use **Run cylinder wake** for the starter simulation or
prepare a custom study in chat. The hosted workspace provides its installed
runtime; visitors use it without managing global installations.

The terminal equivalent is:

```bash
simjecture install warp-lbm
simjecture doctor --profile warp-lbm
```

The installer keeps the pinned Python packages, contributor source, license,
validation records and source/build hashes in `.runtime/warp-lbm-cylinder-1.0`.
Its generated capability descriptor detects CUDA devices and the WSL driver path.
CPU execution is available when a CUDA device is absent. Large CPU runs need their
own cost estimate; the GPU timing below does not apply to them.

For recorded minimal studies, copy `skills/warp-lbm/examples/run_cylinder.py` into
the research workspace and use `lab.run` with capability `warp-lbm-cylinder-1.0`.
The agent guide describes controls, arguments and read-only source inspection.
Project-owned modified source can be passed with `--solver-source` and retained
as an explicit experiment input.

## What the outputs mean

Each run retains its complete configuration, boundary choices, source identity,
force histories, a final wake-field crop and a plot. `summary.json` records units,
the completed interval and statistics over complete lift periods. `forces.npz`
and `forces.csv` retain the whole force history. `fields.npz` labels the cropped
field bounds and time; it is not a full-domain or time-mean field.

Time is `tU/D`; lengths are in cylinder diameters. Grid size is full domain length
and height multiplied by cells per diameter. The contributed reference case has
32 cells across D and an 80D×80D domain: 2560×2560 cells and 160,000 steps.
An independent run reproduced St≈0.164717, mean drag≈1.367441 and RMS lift≈0.238978,
in about 257 seconds on an RTX 4000 Ada. These are same-case reproduction results,
not an error bound for the continuum solution or a universal hardware estimate.

The supplied qualification is for stationary-circle Re=100 studies. New grids,
domains, rotation, shapes and Reynolds numbers remain available for investigation
and need relevant numerical controls. This is isothermal hydrodynamics; the solver
does not evolve magnetic fields or radiation. The distributed version performs
forward simulations and does not include the former autodiff optimization workflow.

## Research benchmark

**Prepare benchmark** opens a conversation containing the versioned
`cylinder-inlet-v1` task. It asks whether moving the inlet from 8D to 40D changes
mean drag or shedding frequency by more than 1%, while keeping the outlet,
height, Reynolds number and measurement definitions fixed. New simulations,
convergence controls, retained evidence and independent review determine success.

This task definition is separate from the published CSV/RZ diagnostic leaderboard.
No model ranking is implied until comparable model runs have been performed and
reported with hardware, time budget, tokens and inference cost.
