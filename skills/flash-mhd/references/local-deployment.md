# Local deployment

This reference is for the operator installing or repairing a local FLASH
runtime. It is not an autonomous campaign procedure.

## License boundary

FLASH is publicly available after registration, but its license restricts
redistribution. Obtain it from the
[official code-request page](https://flash.rochester.edu/site/flashcode/coderequest.html)
and review the current license before use. Do not commit or publish FLASH source,
binaries, modified source, or simulation units derived from FLASH. Commercial
use requires the upstream permission described by the current license.

The public Simjecture skill and capability metadata must remain independently
written. Keep the acquired source and built runtime outside version control.
Configure source access according to the operator's authorization, including use
through the selected model provider. Authorized agents can inspect a read-only
reference tree and full compiler diagnostics while writing problem files separately.
Enforce reference permissions at the filesystem, and record source/build provenance.
This does not authorize publication or redistribution of the acquired source.

## Agent-assisted preparation on a fresh machine

Read this section before inspecting platform-specific site files. The user should
provide their licensed source and choose the intended application/physics and
geometry. Choose routine compiler settings yourself; do not ask the user to write
Makefile.h, environment variables, or a capability descriptor.

Prepare a compatible, non-root toolchain with the application's Python:

```bash
python scripts/prepare_runtime.py flash /absolute/path/to/.runtime/flash-toolchain
```

This installs Python, C/Fortran compilers, OpenMPI, parallel HDF5, NumPy and h5py
from conda-forge into that prefix. Its package cache is shared with other tool
installations; no apt/sudo or preinstalled compiler is required. Source
`scripts/runtime_environment.sh` with `project_root`, `prefix`, and
`runtime_profile=flash` set to activate the compiler toolchain. Use that prefix's
MPI compiler wrappers and HDF5 headers/libraries in the generated local site
Makefile; keep compiler, MPI and HDF5 from the same environment. On modern
GFortran, legacy argument interfaces may require `-fallow-argument-mismatch`.

Copy/extract source into a named build directory. Read the chosen upstream
application's Config and setup help, prepare its site file, then run setup and
make. Run long builds with the `run_command` tool (foreground shell command),
then poll `simulation_status`. Do not use `nohup ... &` inside `terminal`: the
command monitor cleans up descendant processes when the shell finishes.

A single binary is application-specific. Build and register the requested unit,
not a claim that all FLASH modules or dimensions are installed. Place the actual
runtime and its custom descriptor in persistent folders. Verify the descriptor
with the same execution backend the user will use; a host-shell-only run is not
a completed installation. Use `research_tools(action="register", ...)` to make
that capability appear in the catalogue.

## Known installation smoke case: 2D ideal-MHD Orszag–Tang

When the user requests this particular application, start with the upstream
uniform-grid test instead of reverse-engineering all FLASH setup shortcuts:

```bash
./setup magnetoHD/OrszagTang -2d -auto -nxb=16 -nyb=16 \
  +ug +usm +parallelIO +hdf5 -parfile=test_UG_2p_2d.par \
  -site=YOUR_GENERATED_GNU_MPI_SITE -objdir=object_orszag_tang_2d
make -C object_orszag_tang_2d -j 4
```

Generate the local site file using the upstream GNU/Linux site as a template,
with the managed environment's `mpif90`, `mpicc`, and parallel HDF5 prefix.
This setup command is a tested starting point; other requested physics or
dimensions require their own unit selection. For this smoke, use the supplied
2-rank parameter deck, shorten its end time/step limit, and retain its matching
`iProcs=2, jProcs=1`. Check the produced HDF5 files using the bundled smoke.
Keep the source archive pristine, and write site/build adjustments only in the
build copy. Record the full setup command and compiler flags.

## Build and verify locally

1. Install a compatible Fortran/C compiler, MPI implementation, and parallel
   HDF5 stack. Keep compiler, MPI, and HDF5 from mutually compatible toolchains.
2. Configure the operator-selected FLASH simulation unit and required physics
   through the upstream `setup` command. Record the complete setup command and
   generated build metadata.
3. Build with the upstream makefiles. Store the resulting executable in a
   gitignored local runtime directory and record its SHA-256 digest.
4. Run upstream tests for every non-ideal path intended for exposure. For Hall
   work, include the supplied Hall-wave tests; for resistive work, include a
   diffusion/operator test. A successful unrelated MHD problem is not enough.
5. Run a small MPI/HDF5 write-and-read round trip with the exact launcher that
   the capability will use. Verify that all ranks terminate and that the output
   metadata can be read independently.
6. Benchmark a representative non-evidentiary problem at several process
   topologies. Start with one rank and several counts no larger than the
   available physical cores. If simultaneous multithreading is available, test
   higher logical-thread counts separately; use them only when measured
   end-to-end wall time improves. Record MPI rank count, process grid, OpenMP
   thread count, CPU binding, elapsed time, and peak workspace growth. A host
   advertising 20 logical threads does not establish that a 20-rank FLASH run
   is faster or even launcher-valid.
7. Expose the runtime to Simjecture only through a local capability descriptor
   that identifies this skill, pins the executable and relevant identity files,
   declares required mounts and environment, and has no network or credentials.

If you keep a licensed FLASH tree in a Git remote you control, install it
without embedding that URL in Simjecture:

```bash
uv run simjecture install flash --repository git@github.com:<you>/<private-flash>.git
```

Set `FLASH_SETUP_ARGS`, `FLASH_OBJDIR`, and `FLASH_PREFLIGHT_PARFILE` in the
environment. For a reusable local default, attach an overlay as described in
[private-install.md](private-install.md). Simjecture still has no built-in
FLASH download.

Do not make a generic capability claim for a binary whose initialization is
compiled for one fixed problem. Name such a capability after what it can
actually execute. Rebuild and requalify after compiler, MPI, HDF5, FLASH source,
setup-unit, or relevant source changes. Keep machine-specific rank and binding
choices in local deployment records or capability metadata, not in the
scientific skill or hypothesis.

Official references:

- <https://flash.rochester.edu/site/flashcode/>
- <https://flash.rochester.edu/site/flashcode/user_support.html>
- <https://flash.rochester.edu/site/flashcode/user_support/rpDoc_4p8.py>

## Complete the browser handoff

After registering the descriptor, call `research_tools(action="check", name=ID)`
with the returned catalogue ID, then `research_tools(action="list")` until that
check completes. Verify the actual selected descriptor under the configured
execution backend. A manual host-shell run or relocated copy is insufficient.
If readiness is failed, inspect the reported error, repair and rerun this check.
Do not call it a stale UI error or report success while the card is failed.
The CLI's generic `doctor flash` refers to its pinned application, so a custom
application should be checked through its own registered catalogue ID.

## Descriptor path mapping

Capability execution mounts the runtime at `/opt/acs-capabilities/<manifest.name>`.
Use that path, **not the host installation path**, in `FLASH_EXECUTABLE` and
`FLASH_PREFLIGHT_PARFILE`. For example, for name `flash-orszag-tang-2d-4.8`:

```json
{
  "FLASH_EXECUTABLE": "/opt/acs-capabilities/flash-orszag-tang-2d-4.8/bin/flash4",
  "FLASH_PREFLIGHT_PARFILE": "/opt/acs-capabilities/flash-orszag-tang-2d-4.8/share/preflight/flash.par"
}
```

The descriptor's `runtime_root` is the host path (absolute, or relative to the
JSON file). The executable is relative to that root. A managed MPI launcher
inside the runtime must also use the mounted path; a compatible system launcher
can use `/usr/bin/mpirun`. Use the existing FLASH descriptor as a schema template,
but replace its application name, runtime and physics description accurately.

FLASH 4.8's generated dependency machinery may create an empty `iso_c_binding.mod`
that shadows GFortran's intrinsic module. If the compiler reports `Unexpected EOF`
for that file, remove the generated empty file and its generated make dependency
rule; do not replace intrinsic modules with empty stubs or modify the pristine
reference source. Record this build-directory compatibility adjustment.

## Building from read-only source in a hosted job

FLASH setup normally links files from the reference source. Its generated build
may `touch` those headers; `-portable` can also copy read-only modes onto files
that setup subsequently rewrites. Build in a private writable source copy instead:

```bash
simjecture_case_dir=$PWD
mkdir flash-source
for folder in bin source sites lib; do
  cp -RL "$FLASH_SOURCE/$folder" flash-source/
done
chmod -R u+rwX flash-source
cd flash-source
SETUP_SHORTCUTS=$PWD/bin/setup_shortcuts.txt python3 bin/setup.py \
  magnetoHD/IslandCoalescence -auto -opt -2d +cartesian +ug -nofbs +usm \
  +hdf5typeio -site="$FLASH_SITE" -objdir="$simjecture_case_dir/build"
cd "$simjecture_case_dir/build"
make -j4
```

Use the operator's actual source/site paths and compatible toolchain. Preserve the
setup command, build log, compiled executable and relevant initialization source
as declared outputs. Do not alter the installed reference tree. In the hosted
executor, declare those outputs explicitly so the build survives the command's
temporary working directory; executable modes are preserved for subsequent runs.
General inspection commands may use an empty output list: their console is still
recorded. Native examples return `project_outputs`, including a raw-output archive,
for follow-up Python/HDF5 analysis. Read snapshot times from `real scalars` and
do not assume every application uses the `native_` plotfile prefix.
