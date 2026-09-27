# Local deployment

This reference is for the operator installing or repairing a local Optab
runtime. It is not an autonomous campaign procedure.

## License boundary

Optab is an optional package distributed under GPL-3.0. The installer clones
and builds a pinned upstream revision into a Git-ignored runtime. That does not
relicense Optab or copy it into the Simjecture source tree. Review the upstream
license before installing. The public Simjecture skill and capability metadata
must remain independently written.

Upstream: https://github.com/nombac/optab

## Install with Simjecture

Click Install in Research tools. The installer provisions a compatible Fortran
compiler, MPI-enabled HDF5, OpenMPI, Python and data-download dependencies into
a managed environment. No system scientific libraries or sudo are needed.
The equivalent CLI commands are:

```bash
uv run simjecture install optab
uv run simjecture doctor --profile optab
```

Repeating the command against a healthy runtime performs no installation. An
interrupted managed installation resumes on another Install click. Unmanaged
directories are left untouched. `--dry-run` prints the bootstrap command. `--source` may point at an
already cloned tree whose `HEAD` matches the pinned revision.

The bootstrap compiles Optab, downloads the van Hoof free-free Gaunt-factor
table and the NIST level database used by Optab, verifies all 4,278 expected
ion groups, and writes a one-zone
continuum hydrogen preflight input. That preflight is an interface check, not a
production opacity table.

## Runtime layout

```text
.runtime/optab-1.3.1/
  bin/python
  bin/optab
  bin/mpi-launcher
  share/build-record.json
  share/preflight/          # complete Optab input/ tree for the doctor probe
```

`bin/python` provides `h5py`. `bin/mpi-launcher` uses the matching managed MPI
launcher with paths that work inside capability execution. Failed readiness
outputs remain in `.runtime/deployment/preflights/`.

Capability environment (sandbox paths):

- `OPTAB_EXECUTABLE=/opt/acs-capabilities/optab-1.3.1/bin/optab`
- `OPTAB_MPI_LAUNCHER=/opt/acs-capabilities/optab-1.3.1/bin/mpi-launcher`
- `OPTAB_PREFLIGHT_INPUT=/opt/acs-capabilities/optab-1.3.1/share/preflight`
- `OPTAB_MPI_RANKS=1`

Manual layouts remain valid if they match the capability descriptor. Rebuild
and requalify after compiler, MPI, HDF5, Optab source, or database changes.
