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

Prerequisites on `PATH`: Git, Python 3.12 or 3.11, an MPI Fortran HDF5 wrapper
(`h5pfc`), and `mpirun` / `orterun` / `mpiexec`.

```bash
uv run simjecture install optab
uv run simjecture doctor --profile optab
```

Repeating the command against a healthy runtime performs no installation. An
unhealthy installer-managed prefix is left unchanged unless `--repair` is
explicit. `--dry-run` prints the bootstrap command. `--source` may point at an
already cloned tree whose `HEAD` matches the pinned revision.

The bootstrap compiles Optab, downloads the van Hoof free-free Gaunt-factor
table and the NIST level database used by Optab, and writes a one-zone
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

`bin/python` must provide `h5py`. `bin/mpi-launcher` wraps the host MPI
launcher discovered at install time.

Capability environment (sandbox paths):

- `OPTAB_EXECUTABLE=/opt/acs-capabilities/optab-1.3.1/bin/optab`
- `OPTAB_MPI_LAUNCHER=/opt/acs-capabilities/optab-1.3.1/bin/mpi-launcher`
- `OPTAB_PREFLIGHT_INPUT=/opt/acs-capabilities/optab-1.3.1/share/preflight`
- `OPTAB_MPI_RANKS=1`

Manual layouts remain valid if they match the capability descriptor. Rebuild
and requalify after compiler, MPI, HDF5, Optab source, or database changes.
