# Deployment

Run from a Simjecture source checkout on Linux or an existing WSL2 distribution:

```bash
uv sync --frozen
uv run simjecture install quantum-espresso --jobs 1
uv run simjecture doctor --profile quantum-espresso
```

On Windows, invoke these commands with `wsl -d <distribution> -- bash --noprofile
--norc`; use Linux paths. Existing Ubuntu shell profile hooks are not prerequisites.
The optional PowerShell wrapper `scripts/deploy_qe.ps1` converts the checkout path
and invokes the same installer. It requires an already installed Simjecture
application environment; it does not install WSL or change host configuration.

The official checksummed Micromamba bootstrap uses only conda-forge with strict
channel priority. QE is fixed at 7.4 build hac89879_0; dependency identities,
download URLs, hashes and binary hashes are recorded in share/build-record.json.
An unchanged healthy runtime is reused. Interrupted managed installs can resume;
unmanaged directories and mismatched package profiles are rejected.

Reserve at least 3 GiB before first installation and 1 GiB for repair. Actual
space depends on dependencies/cache/checkpoints. On WSL also check the Windows
volume holding the distribution VHD: virtual Linux free space is insufficient.
Keep TMPDIR and runtime/package-cache on a volume with adequate physical space.
A project-local .runtime symlink can point to a new isolated storage location.
Never move an existing environment as part of this procedure.

The first release uses a single-process CPU MPI build with OMP/BLAS threads set
to one; it does not require Docker. Existing Docker deployments need not start.
Installation is separate from qualification: doctor runs the declared preflight
through the chosen experiment backend. Missing isolation prerequisites are a
reported blocker, not a reason to silently weaken host security settings.


For a Windows checkout, the conditional setup wrapper selects a new Linux-native runtime
prefix when needed, preserves existing prefixes, and calls the same public
installer and doctor. Optional arguments are -RuntimeBase (absolute Linux path),
-Uv (Linux uv executable), and -ApplicationEnvironment (existing Linux application
environment), and -BubblewrapDirectory (existing Linux directory containing
bwrap when it is outside the default PATH). Missing Bubblewrap is a prerequisite
failure. It never migrates an existing runtime.


## Conditional setup and prerequisites

This is automated QE setup on supported Linux/x86_64 or already configured WSL2,
not a verified clean-machine one-click installation. The application environment,
working user namespaces/Bubblewrap, and an available Linux uv command (or configured
path) must already be usable. Docker is not required.

The public installer passes its running Python interpreter to the bootstrap;
a separate python3 on PATH is not required. An explicit
`SIMJECTURE_BOOTSTRAP_PYTHON` overrides that choice. When invoking bootstrap.sh
directly, set that variable if python3 is unavailable. The QE wrapper reports
missing uv with installation/configuration guidance before creating runtime
paths; use `--uv /absolute/path/to/uv` (PowerShell: `-Uv`) for an existing executable,
and `uv sync --frozen` to prepare the application environment.

Simjecture's base installation can prepare uv/Python and may prepare Bubblewrap
on supported Linux systems, but the QE wrappers do not install these prerequisites
or change host settings. A clean second-machine end-to-end deployment has not
been validated.
