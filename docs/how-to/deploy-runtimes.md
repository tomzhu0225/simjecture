# Deploy runtime profiles

Deployment is an operator action, not an authority granted to the autonomous
agent. All profiles use project-local, Git-ignored runtime paths, after which the
harness mounts one selected instrument read-only into the agent sandbox.

## Core

From a source checkout, synchronize the locked Python environment and verify the
scientific packages plus Bubblewrap namespace isolation:

```bash
uv sync --frozen
uv run simjecture install core
```

Python 3.11 or newer, `uv`, and the operating-system Bubblewrap package remain
host prerequisites. The package manager installs NumPy, SciPy, Matplotlib,
pandas, HTTPX, and Pydantic from the project lock.

## WarpX CPU

Install the pinned Conda environment at `.runtime/warpx-cpu` and execute its
one-step 2D openPMD field preflight:

```bash
uv run simjecture install warpx-cpu
```

The installer discovers Micromamba or Mamba, consumes
`environments/warpx-cpu.yml`, loads the versioned capability manifest, and runs
the manifest-declared program through Bubblewrap. Repeating the command against
a healthy runtime performs no installation. It will not overwrite an unhealthy
existing directory; `--repair` is accepted only for an identifiable
Conda-managed CPU prefix.

## WarpX CUDA/openPMD

CUDA deployment compiles an audited WarpX checkout for the local GPU and is
therefore more expensive and hardware-specific:

```bash
uv run simjecture install warpx-cuda \
  --source /absolute/path/to/pinned/warpx-26.07 \
  --jobs 8
```

The installer requires the exact source revision declared by the deployment
skill before invoking its pinned bootstrap. The bootstrap verifies the CUDA
backend and an HDF5 openPMD round trip; the capability doctor then executes the
manifest's field-diagnostic smoke inside the sandbox. `--arch 89` can override
GPU architecture detection when necessary.

CUDA repair is deliberately not performed in place. Move an unhealthy runtime
and its dependency prefixes aside so their previous identity remains available
for audit, then perform a fresh build.

## FLASH MHD

FLASH is operator-supplied. Obtain the source from the
[official FLASH Center](https://flash.rochester.edu/site/flashcode/coderequest.html),
review its license, and build the required application outside the Simjecture
repository. Simjecture does not download FLASH or redistribute its source,
modified units, or binaries.

Register the local application-specific executable under the Git-ignored
runtime path named by its capability descriptor. Include a build record, an
operator-prepared inexpensive parameter file, and all sibling binaries or
records in `identity_files`. The generic deployment procedure and required
operator tests are documented in
`skills/flash-mhd/references/local-deployment.md`.

Once the local runtime exists, verify it without changing it:

```bash
uv run simjecture doctor --profile flash
```

`simjecture install flash` never contains a FLASH download URL. Pass **your**
licensed copy:

```bash
uv run simjecture install flash \
  --repository git@github.com:<you>/<your-private-flash>.git \
  --git-ref <tag-or-commit>
```

or `--source /absolute/path/to/FLASH`. Set `FLASH_SETUP_ARGS`, `FLASH_OBJDIR`,
and `FLASH_PREFLIGHT_PARFILE` in the environment. A Git-ignored overlay can
store those defaults. See `skills/flash-mhd/references/private-install.md`.

The cached probe exercises the exact MPI launcher and reads a fresh HDF5 file.
It is permanently non-evidentiary. The campaign must still commission its
actual compiled model, initial state, boundaries, diagnostics, and numerical
regime prospectively.

## Equation of state

atoMEC, Singularity-EOS, and M-ANEOS are optional instruments. The installer
clones the pinned upstream revision into a Git-ignored runtime, compiles any
query driver, and runs a non-evidentiary probe. Host prerequisites are Git and
Python 3.12 or 3.11; Singularity-EOS also needs `g++`, and M-ANEOS needs
`gfortran` and `make`.

```bash
uv run simjecture install atomec
uv run simjecture install singularity-eos
uv run simjecture install m-aneos
```

Repeating a command against a healthy runtime performs no installation. It will
not overwrite an unhealthy existing directory; `--repair` is accepted only for
an installer-managed prefix. `--source` may supply an already cloned tree at
the pinned revision. The generic procedure is documented in
`skills/eos/references/local-deployment.md`. A campaign must still commission
the named model, composition, units, and estimator.

## Opacity tables

Optab is optional and GPL-3.0 licensed. The installer clones the pinned
revision, builds the MPI/HDF5 executable, fetches the Gaunt-factor and NIST
databases required by the doctor probe, and writes a one-zone continuum
hydrogen input. Host prerequisites are Git, Python 3.12 or 3.11, `h5pfc`, and
an MPI launcher.

```bash
uv run simjecture install optab
```

The probe copies the prepared input tree, launches Optab, and reads HDF5. It
does not qualify a production opacity table. Optab consumes an external
abundance file; it is not an equation-of-state solver. See
`skills/opacity/references/local-deployment.md`.

## Inspect without installing

```bash
uv run simjecture doctor
uv run simjecture doctor --profile warpx-cpu
uv run simjecture doctor --profile warpx-cuda --json
uv run simjecture doctor --profile flash --json
uv run simjecture doctor --profile atomec --json
uv run simjecture doctor --profile optab --json
uv run simjecture install warpx-cpu --dry-run
```

The default doctor treats missing optional profiles as warnings and fails
only when the core is unusable. Selecting a profile makes that capability
required. `--skip-probes` checks files, manifests, devices, and runtime identity
without executing the declared smoke programs.

An installation report is recorded under `.runtime/deployment/`. A doctor run
writes only to a temporary sandbox and does not modify an installed runtime.
