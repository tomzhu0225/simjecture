# ITER ecosystem pack

Simjecture integrates open-source fusion tools without requiring a
particular model backend. Installation and numerical readiness are deterministic;
agent-guided preparation uses the user's selected model, including DeepSeek Flash.
This is a Simjecture integration, not an ITER-endorsed distribution.

## Install and run

In **Research tools**, select **ITER pack · diagnostics & data → Install**.
The installer creates a separate managed environment and runs its numerical
preflight through the configured execution backend. **Run demo** creates a
conversation and opens a monitored simulation with downloadable JSON, netCDF,
CSV and a three-panel figure. It does not consume LLM tokens.

Equivalent CLI commands, from a deployment checkout:

```bash
simjecture install iter-pack
simjecture doctor --profile iter-pack
```

The runtime includes CHERAB 1.5.0, compatible Raysect 0.8.1.post1, pinned
CHERAB-ITER and CHERAB-IMAS source revisions, IMAS-Python and IMAS-Validator.
Build records retain package versions, requirements and installation duration.
The older NumPy/Raysect dependencies stay outside Simjecture's Python environment.
On hosts without a supported system Python, the installer provisions a local
Python 3.12 environment with the existing Micromamba bootstrap. Git and a C
compiler are required for the CHERAB extensions. No GPU or scheduler is needed.

The offline example checks:

- Raysect integration through a uniform sphere against its analytic chord length.
- CHERAB free-free emission scaling with electron and ion density.
- IMAS schema validation and a netCDF profile round-trip with an explicit DD version.
- Construction of three five-channel bolometer cameras from upstream mock IDS data.
- The CHERAB-ITER compiled geometry helper against a finite-difference derivative.

These are bounded readiness checks. They do not validate actual ITER instruments,
line-emission atomic data, a plasma discharge, or an arbitrary reconstruction.

## Use with an agent

Choose your backend/model in the workspace and ask, for example:

> Use the ITER pack to compare two synthetic plasma emission profiles from
> different viewing angles. Start from the working demo, quantify which signals
> distinguish them, and retain the assumptions and output plots.

The `iter-pack` skill is available through `read_skill` to API agents and through
files to native CLI agents. It links focused references rather than duplicating
upstream manuals. It explains data dictionary compatibility, atomic-data needs,
ray sampling, geometry provenance and the distinction between measured signals
and reconstructed profiles. In minimal studies, the registered capability works
through the ordinary `lab.run` interface. Source packages remain readable.

## Separate solver integrations

| Tool | Workspace entry | Current qualification |
| --- | --- | --- |
| CHERAB / Raysect / IMAS | Install, Check readiness, Run demo | Automatic install and offline numerical demos verified |
| JOREK | Install with agent; check registered builds | A local GNU/MUMPS model600 build passed a three-step sandboxed example; fresh-machine setup remains guided |
| SOLPS-ITER | Install with agent | Public components inspected; EIRENE compiled, full coupled runtime not yet qualified |
| DINA-PS | Install with agent | Native core/controllers compiled and supplied magnetic-geometry component test passed; full IMAS scenario workflow not yet qualified |

The diagnostics pack does not contain these three solver binaries. A registered
JOREK build advertises its specific model and toroidal harmonics, not all JOREK
physics. Guided setup preserves source, build configuration, input identity and
logs before registering the actual working application.

See the [acceptance report](../testing/iter-pack-acceptance.md) for measured results,
remaining dependencies and the real DeepSeek Flash test. Reproduce the fresh
browser installation test with `python scripts/verify_iter_pack.py` after
installing the workspace dependencies and Playwright Chromium. It downloads into
a new `artifacts/iter-pack/oneclick-*` deployment and makes no model calls.
