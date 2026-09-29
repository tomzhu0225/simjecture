# JOREK guided setup

Upstream: https://github.com/iterorganization/JOREK
Inspected revision: `4e79ba70cd2a910f9f2a792c9ffb4f074ab8fe90`.
Read the checkout's `docs/howto/running_jorek_for_the_first_time.md`,
`docs/compiling/compilation_and_libraries/`, `docs/diagnostics/`, and `reg_tests/`.
These source documentation files work even if the rendered website is unavailable.

JOREK is a family of compiled models, not one universal binary. Preserve
`Makefile.inc`, the chosen model and `models/mod_settings` / model settings.
Toroidal harmonics and planes are build parameters; a one-harmonic equilibrium
run is not a resolved 3D instability. `util/config.sh` describes these settings.

Inspect GNU/Intel compiler and MPI compatibility, HDF5 Fortran, BLAS/LAPACK,
ScaLAPACK and the selected sparse solver (MUMPS or PaStiX) before compiling.
Do not blindly copy an HPC configuration containing site-specific paths.
Use the upstream GNU/MUMPS instructions when appropriate. Avoid changing global
shell startup files: scope the toolchain environment to the build/launcher.

Start from an upstream small regression or `intear` example matching the build.
Confirm MPI rank/harmonic compatibility from its documentation. Record actual
mesh, harmonics, timesteps, solver convergence, energy diagnostics, peak RSS and
wall time. A completed initialization is not a nonlinear instability simulation.
No measured single-node production envelope is claimed by this integration yet.

Register only the working build, with executable and configuration hashes,
read-only source access, an inexpensive numerical preflight and analysis readers.
The Research tools card intentionally offers **Install with agent** until a
verified application is registered. CHERAB-ITER's JOREK reader is not JOREK itself.

## Measured local commissioning (2026-09-29)

A GNU/OpenMPI/MUMPS model600 build passed `examples/jorek_demo.py` through
Bubblewrap. It used 256 poloidal elements, n_tor=3, n_period=6, n_plane=4,
two MPI ranks and two OpenMP threads. The three components are n=0 and the
sine/cosine n=6 pair, not three arbitrary physical mode numbers. Three normalized
time steps completed with finite HDF5 values; the circular cross-section area
was 3.1413801885 m² against π m². This does not establish mode growth or convergence.

A singleton rank failed with MPI_ERR_RANK for this build; use the measured two
ranks. In the sandbox, `/usr/bin/mpirun` can resolve through an absent `/etc`
alternatives link: put the resolved MPI launcher inside the runtime. Shell
launchers need `#!/usr/bin/sh`, since `/bin` is not part of the isolated view.
Keep dependency libraries in the runtime and set its sandbox LD_LIBRARY_PATH;
linking host paths alone is insufficient. GNU link setup needed OpenBLAS's
`daxpby` and HDF5's high-level Fortran library, not just generic BLAS and HDF5.

The example emitted two HDF5 metadata string-size warnings during initialization;
all four restart outputs were readable. These warnings are recorded rather than
hidden. Qualification of restart metadata and a real instability remains open.
