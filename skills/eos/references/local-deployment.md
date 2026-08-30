# Local deployment

This reference is for the operator installing or repairing a local EOS runtime.
It is not an autonomous campaign procedure.

## License boundary

atoMEC, Singularity-EOS, and M-ANEOS are optional packages. The installer clones
and builds pinned upstream revisions into a Git-ignored runtime. That does not
relicense those packages or copy them into the Simjecture source tree. Review
each upstream license before installing.

| Package | Upstream | Typical license |
|---|---|---|
| atoMEC | https://github.com/atomec-project/atoMEC | BSD-3-Clause |
| Singularity-EOS | https://github.com/lanl/singularity-eos | BSD-3-Clause |
| M-ANEOS | https://github.com/isale-code/M-ANEOS | MIT |

Bundled third-party numerical libraries retain their own notices. The public
Simjecture skill and capability metadata must remain independently written.

## Install with Simjecture

From a Simjecture checkout, with Git and Python 3.12 or 3.11 on `PATH`:

```bash
uv run simjecture install atomec
uv run simjecture install singularity-eos
uv run simjecture install m-aneos
```

Repeating a command against a healthy runtime performs no installation. An
unhealthy installer-managed prefix is left unchanged unless `--repair` is
explicit. `--dry-run` prints the bootstrap command without writing a runtime.
`--source` may point at an already cloned tree whose `HEAD` matches the pinned
revision; otherwise the bootstrap clones it. `--jobs` is passed to compilation
where relevant.

Singularity-EOS also needs `g++`. M-ANEOS needs `gfortran` and `make`.

Then verify:

```bash
uv run simjecture doctor --profile atomec
uv run simjecture doctor --profile singularity-eos
uv run simjecture doctor --profile m-aneos
```

The doctor probes are permanently non-evidentiary interface checks.

## Runtime layout

The installer writes:

```text
.runtime/<capability>/
  bin/python
  bin/eos-query          # Singularity-EOS
  bin/maneos-query       # M-ANEOS
  share/build-record.json
  share/preflight/ANEOS.INPUT   # M-ANEOS, upstream example deck
```

`bin/python` is the capability executable. Sibling scientific binaries are
declared in `identity_files` and hashed at discovery.

## What the installer builds

- **atoMEC 1.4.0:** a virtual environment with libxc 6.2.2 and the pinned
  atoMEC revision. The probe is a helium ion-sphere SCF.
- **Singularity-EOS 1.12.1:** a query driver compiled against the pinned source
  for `IdealGas` and `IdealElectrons`. The probe evaluates `IdealGas` only.
- **M-ANEOS 1.0:** `libaneos.a`, the query driver, and the upstream example
  `ANEOS.INPUT` as a non-evidentiary preflight deck. That deck does not
  qualify other materials.

Manual layouts remain valid if they match the capability descriptor. Rebuild
and requalify after compiler, Python, or upstream-revision changes.
