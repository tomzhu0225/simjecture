# Diagnostics and data

## Install and repeat the demo

From a Simjecture deployment checkout:

```sh
simjecture install iter-pack
simjecture doctor --profile iter-pack
```

The GUI provides **Research tools → ITER pack · diagnostics & data → Install**.
Installation is deterministic operator tooling, independent of the chosen LLM.
The readiness check runs in the selected execution backend and retains plots and
JSON beneath `.runtime/deployment/preflights/iter-pack-1.0/`. The **Run demo** GUI
button repeats it. The selected DeepSeek Flash agent can then prepare studies.

Prerequisites: Linux, git, and a C compiler for the two pinned CHERAB extensions.
System Python 3.11/3.12 with venv/pip is used when available; otherwise the
existing Micromamba bootstrap provisions a project-local Python 3.12. No root, GPU, cluster scheduler or ITER account
is required for the offline demo. The separate runtime is
`.runtime/iter-pack-1.0`; never install these older numerical dependencies into
Simjecture's own Python environment. Existing unmanaged directories are preserved.
An interrupted managed install may be retried; `--repair` repairs a managed prefix.

CHERAB 1.5.0 requires Raysect 0.8.1.post1 and NumPy 1.x. Do not independently upgrade
Raysect to 0.9. Pinned direct dependencies and source revisions are in
`../scripts/requirements.txt` relative to the skill root's references directory.
The build record and installed-requirements file record the resolved environment.

To run manually on the host, change to a fresh output directory and execute:

```sh
/path/to/.runtime/iter-pack-1.0/bin/python /path/to/skills/iter-pack/examples/diagnostics_demo.py
```

## Interfaces and known boundaries

- CHERAB represents distributions, emitting plasma, atomic models and observers.
  Raysect traces light through geometry. A density/temperature array alone is not
  a camera signal: supply spatial interpolation, emission physics and optics.
- The offline continuum example uses CHERAB's free-free model. Line radiation,
  charge exchange and other ADAS-dependent models require the relevant atomic
  data. Fetch and record them during preparation; do not assume a network-enabled
  research sandbox or silently replace missing line emission by continuum.
- `imas.IDSFactory('3.39.0')` builds DD3 structures; open **both** writer and reader
  `imas.DBEntry(..., dd_version='3.39.0')` with that version. DD4 defaults do not
  automatically convert DD3 data across the major version boundary.
- CHERAB-IMAS bolometer geometry needs DD4.1+. `datasets.bolometer_moc()` creates
  upstream mock data offline; `load_bolometers(path, parent=world)` constructs its
  three five-channel cameras. This is not ITER's actual instrument geometry.
- CHERAB-ITER has compiled JOREK geometry functions. `py_fourier_mode` accepts
  **degrees**, unlike many NumPy trigonometric functions. Its database examples
  default to `/work/imas/shared/...` or UDA: public source does not grant database
  access. Use explicitly available datasets and geometry.
- IMAS structural validation does not certify physics. `imas-validator` supports
  configurable validation rules; use only rules relevant to the chosen IDS/model.
- For stochastic camera/tomography work, vary ray samples and report uncertainty;
  preserve the observation matrix and reconstruction regularization. A visually
  convincing reconstruction is not evidence of uniqueness.

## Upstream material

- https://www.cherab.info/ (models, observers, demonstrations)
- https://www.raysect.org/ (optics, ray tracing, multicore execution)
- https://github.com/cherab/imas (public sample datasets and adapters)
- https://github.com/cherab/iter (ITER-specific source and demos)
- https://github.com/iterorganization/IMAS-Python
- https://github.com/iterorganization/IMAS-Validator

CHERAB-IMAS exposes public sample datasets through `datasets.iter_solps()`,
`iter_jorek()`, and `iter_jintrac()`. These fetch files from Zenodo and cache them;
check size and provenance first. Analysing these files does not mean we ran their
originating solvers. Upstream public APIs, docstrings and examples are the agent
interface; no dedicated solver-agent MCP integration was found in this inspection.
