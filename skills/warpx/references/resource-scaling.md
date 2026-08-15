# Resource scaling

Estimate cost before launching a calculation. For explicit PIC, particle work
typically grows with cells times macroparticles per cell times species times
steps. Field work grows with cells, components, solver iterations, and steps.
Diagnostics can dominate storage when full particles or frequent mesh dumps
are requested.

Start commissioning with the smallest case that exercises the intended
geometry, species, solver, boundaries, and diagnostic path. Increase one
relevant fidelity axis at a time. Keep heavy raw output sparse unless the
observable requires it; use reduced diagnostics for inexpensive monitoring,
but retain enough raw information to challenge the estimator.

The sandbox exposes two distinct instruments: `warpx-cpu-26.07` is a bounded
eight-thread OpenMP CPU profile, while `warpx-cuda-openpmd-26.07` is a
non-MPI, 2D CUDA profile with HDF5 openPMD output. Read `cpu-launch-tuning.md`
or `gpu-launch-tuning.md` before a long campaign. Do not assume the GPU is
faster: run a bounded commissioning case with the actual workload, then spend
its measured throughput on the fidelity axis that most limits the intended
inference. Large multidimensional, high-particle, or long-duration proposals
may still be unreachable even though WarpX supports them on other machines.
An honest instrument-unreachable result is preferable to silently weakening
the physical question.
