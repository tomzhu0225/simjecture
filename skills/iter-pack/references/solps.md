# SOLPS-ITER guided setup

Upstream: https://github.com/iterorganization/SOLPS-ITER
Inspected revision: `ca0d04d9b0b2d4887bd3262e4e867d471ba86d62`.
Tutorials: https://solps-tutorials.readthedocs.io/
Read installation/container instructions, first simulation, output processing,
convergence and common pitfalls. Reuse their structured `baserun/` and `run/`
workflow rather than inventing a new layout.

The checkout contains B2.5/EIRENE and geometry tools as submodules. Pin both the
superproject and submodules. At the inspected revision the ADAS submodule still
points to `ssh://git@git.iter.org/imex/amns-adas.git`; a public superproject alone
is not evidence that all rate data can be obtained anonymously. Inspect the
upstream public container/data route and record any unresolved requirement;
never replace missing atomic rates with fabricated values.

The non-graphical `setup.ksh` / `make nox` route can support headless operation.
Check the container runtime against the host: a restricted container may not
allow Apptainer/Docker namespaces. Native installation is an alternative.
Use upstream dependencies/setup instructions and record any configuration patch.

Full example cases are fetched separately; see `runs/examples/README.md` and its
Makefile's version-matched Zenodo record. Preserve archive checksums. A different
release's sample is not automatically compatible. Start with a supplied coupled
B2.5-EIRENE example, not an empty set of parameter stencils.

Treat equilibrium/wall geometry, plasma mesh and neutral mesh as different inputs.
Convergence assessment must include residual evolution, particle and power
balances, and sensitivity to neutral sampling. A zero exit code or one iteration
is not a converged divertor solution. Retain imposed cross-field transport
coefficients as model assumptions, not measured turbulent transport.

Register the actual runtime only after its bounded example and readers work.
The Research tools card offers **Install with agent**. Public SOLPS output loaded
through CHERAB-IMAS is an analysis demonstration, not a locally executed SOLPS run.

## Observed build boundary (2026-09-29)

The pinned public B2.5, EIRENE, CARRE and DivGeo submodules were fetched. EIRENE's
standalone executable and coupled libraries compiled with GNU Fortran. The full
`make nox` build remained unqualified: site configuration required LD_MSCL,
LD_NCARG, LD_NAG and LD_NETCDF setup. An empty `LD_NCARG=` did not satisfy the
upstream `ifndef` check. Installing tcsh only in PATH also does not fix scripts
with an absolute `/bin/csh` shebang. Use a supported native dependency recipe or
upstream container; do not call the partially built tree a working SOLPS runtime.
