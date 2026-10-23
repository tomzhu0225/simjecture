# Install and qualify a local runtime

This first experimental release adopts an existing **Linux Elmer installation**
with `bin`, `lib/elmersolver`, and `share/elmersolver`. It copies that installation
into a managed runtime, adds pinned Python mesh/analysis packages, and records
binaries, solver modules and resolved non-system libraries. The original is
unchanged. It does not compile Elmer or install a local solver patch.

The exercised upstream build is Elmer 26.2.1, source revision
`a19504ac53ec222e3355e182b08f2ff280c2203a`, with MPI and Hypre enabled; computation
uses a single process. The source is available from
[CSC's Elmer repository](https://github.com/ElmerCSC/elmerfem).
A different build must pass the same controls. Gmsh's wheel needs the host GLU
library even for headless meshing. Dependencies installed outside standard host
library paths must be resolvable in `LD_LIBRARY_PATH` during installation.

```bash
SIMJECTURE_BOOTSTRAP_PYTHON=/path/to/python3.12 \
  simjecture install elmer-em --source /path/to/elmer-install
simjecture doctor --profile elmer-em
```

The tool-library entry uses agent-assisted setup because the installer needs a
prebuilt Elmer directory. Python 3.12+ is required by the pinned scientific
packages. The packaged Python has its own standard library so the driver can
run inside Simjecture's capability namespace. System libraries remain tied to
the host; this is a local installation bundle, not a portable binary release.
Preserve upstream license texts included with the supplied installation.

Standalone invocation from a source checkout:

```bash
export SIMJECTURE_ELMER_HOME="$PWD/.runtime/elmer-em-0.1/elmer"
export LD_LIBRARY_PATH="$SIMJECTURE_ELMER_HOME/deps"
.runtime/elmer-em-0.1/bin/python \
  .runtime/elmer-em-0.1/share/elmer_em.py wire-demo /tmp/wire-control
```

Run a second fresh directory with `wire-demo /tmp/rlc-control --rlc` to check
coupled RLC equations against an independent backward-Euler solution. This
longer control is separate from the installation preflight. No private CAD,
reference solver data or experimental machine specification is distributed.
