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
Avoid sending FLASH source to a model or external service; expose only the
bounded executable interface, operator-owned inputs, and generated outputs
needed for the campaign.

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
