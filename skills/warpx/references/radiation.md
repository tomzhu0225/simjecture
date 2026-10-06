# WarpX photon radiation

WarpX supports collisional bremsstrahlung photon production and inverse
bremsstrahlung absorption. These are separate from quantum synchrotron emission,
which requires a QED build and its lookup tables. Inspect the installed binary's
features and source; do not infer its full capabilities from a Langmuir preset.

In a general hosted workspace, `list_native_tools` gives the binary and source
paths. Use `read_file` to inspect `Examples/Tests/collision/` and prepare your own
input with `write_file`. Execute the standalone binary through
`run_command(kind="simulation")`; run diagnostics as `kind="command"`. Preserve
the realized input, reduced diagnostics, particle outputs when needed, and the
analysis source. Create output directories and declare files to retain between
fresh scratch runs.

The hosted CUDA binaries were tested through the confined launcher with the
upstream boron collision inputs on 2026-10-06. Both emission and absorption ran
for 100 steps and produced nonzero photon energy. The reduced electron, ion and
photon energy sum drifted by less than 1e-10 in each case. These are collision
operator checks: periodic geometry, a hot electron population and no evolving
Maxwell fields. They do not establish global device validity.

For a controlled absorption comparison, keep the same species distributions,
seed, density, grid and timestep, and change only the enabled collision operator.
Separate photon creation, absorption, retained photon energy and escaped energy.
Read the actual `ParticleEnergy` headers: total columns already include species
columns, and mean-energy columns are a different quantity. In 1D, report the
transverse-area normalization rather than quoting an absolute device yield.
Open boundaries also require an escaped-photon budget.

The currently installed bremsstrahlung source supplies Seltzer–Berger tables for
atomic numbers 1, 2, 5 and 6, with electron energies tabulated from 1 keV to 2 MeV.
It does not supply the aluminium Z=13 table. Do not silently substitute boron or
carbon, invent a table, or extrapolate below the tabulated regime for an aluminium
claim. A private application build can add independently sourced and validated
material data; preserve their provenance and commission the changed operator.

References: [WarpX collision and QED parameters](https://warpx.readthedocs.io/en/latest/usage/parameters.html),
and the installed `Source/Particles/Collision/BinaryCollision/Bremsstrahlung/`
and `Source/Particles/Collision/InverseBremsstrahlung/` implementations.
