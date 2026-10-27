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


## Prerequisite checks and remedies

This is conditional automated QE setup on Linux x86_64 or an already configured
WSL2 x86_64 distribution. A second clean-machine end-to-end deployment has not
been validated. The wrappers diagnose prerequisites; they do not install WSL,
uv, application packages or operating-system packages, or change host policy.

Use the checked wrapper from a source checkout:

```bash
bash skills/quantum-espresso/scripts/deploy.sh --project-root "$PWD"
```

Before creating runtime directories/links or invoking the installer, it checks:

| Requirement | Remedy when missing or unusable |
|---|---|
| Linux x86_64, Bash, coreutils, util-linux (`findmnt`) | Use supported Linux/WSL2; install the distribution packages before retrying. The Windows wrapper checks for an existing WSL2 distribution and gives `wsl --list --verbose` / `-Distribution` guidance. |
| Working uv executable | Follow the Simjecture [base installation](../../../docs/getting-started/installation.md), add uv to PATH, or pass `--uv /absolute/path/to/uv` (PowerShell `-Uv`). |
| Existing application Python >=3.11 and locked packages | Prepare the application with `uv sync --frozen`. For an existing external environment set `UV_PROJECT_ENVIRONMENT=/absolute/environment/path` (PowerShell `-ApplicationEnvironment`). |
| Bubblewrap and working user namespaces | Install the distribution's `bubblewrap` package (Debian/Ubuntu: `sudo apt install bubblewrap`), or supply `--bubblewrap-dir /existing/bin`. The existing core doctor probes namespaces and checks application package versions. Ask your administrator about policy restrictions; the wrapper does not relax them. |
| Linux-native runtime filesystem and sufficient storage | Choose `--runtime-base /absolute/linux/path`, preserve the physical Windows reserves described above, and retry once adequate space is available. |

The application installer passes its running `sys.executable` to the QE bootstrap.
An explicit `SIMJECTURE_BOOTSTRAP_PYTHON=/absolute/application/python` overrides it;
an invalid override fails rather than silently choosing another interpreter.
For the internal bootstrap, selection is: explicit override, existing
`UV_PROJECT_ENVIRONMENT/bin/python` (or `.venv/bin/python`), then PATH `python3`.
A nonempty explicit `UV_PROJECT_ENVIRONMENT` must contain executable `bin/python`;
invalid targets are rejected even when another usable Python exists. Relative
paths are resolved against the checkout, normalized and passed unchanged in
meaning to uv. Empty values retain default selection.

The checked deployment wrapper requires an existing application environment.
It checks application packages/core doctor using the selected uv target's
`bin/python`, even if a separate bootstrap interpreter is configured. With no
explicit uv target, it binds uv to the selected existing application interpreter's
standard `ENV/bin/python` environment (including an explicit bootstrap path).
For other interpreter layouts, set `UV_PROJECT_ENVIRONMENT` explicitly. A PATH
Python alone does not validate an uncreated project environment: first prepare
that environment with `uv sync --frozen`.
An application launched with a valid interpreter no longer needs a separate
PATH `python3`. Quote paths containing spaces. The checked wrapper uses that
interpreter for the read-only core doctor before any QE provisioning, explicitly
probing Bubblewrap because the QE launcher requires it.

QE, OpenMPI, the runtime Python and its numerical libraries are **installer
outputs**, not prerequisites. The pinned dependency download still requires
network access to the official bootstrap/conda-forge sources and sufficient
cache space. Pseudopotentials remain a separate, licensed, hash-checked research
input. Prerequisite failures stop before QE installation; failures during a later
network/package install retain diagnostics and may leave managed partial state.
No clean-machine success guarantee follows from the isolated mock regression
tests or the earlier existing-environment deployment. Passing environment checks
does not approve scientific execution: the research-plan confirmation is still
required before running a calculation.
