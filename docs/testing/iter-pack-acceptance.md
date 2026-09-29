# ITER pack acceptance — 2026-09-29

This records real execution on Linux x86-64, not simulated solver or model
responses. The pack is part of the unpublished 0.5.2rc3 development preview.

## Automatic installation and GUI

A fresh deployment directory was created with no runtime. A real Chromium browser
clicked **Research tools → ITER pack → Install**, waited for the numerical
readiness report, then clicked **Run demo**. The application spawned its ordinary
installer and monitored simulation jobs. All six checks passed and no browser
JavaScript errors were observed. The final repeat took 24.93 seconds with warm
package/build caches; this is not a cold-download installation benchmark.

The local runtime occupies approximately 0.9 GB. The demo produces a figure,
spectra CSV, IMAS netCDF and JSON. The installer was also run through the CLI,
and its numerical preflight executed through Bubblewrap. Repeated installation
checks an existing healthy runtime instead of reinstalling it.

On the dedicated remote host, the same pack installed under a non-root account
with `proot-cooperative`, using the managed Python 3.12 fallback because system
Python is 3.10. Its numerical preflight and browser-launched demo also passed.
This installation lives separately from the active research campaign. PRoot
retains its existing cooperative-execution semantics; it is not namespace isolation.

Reproducer: `python scripts/verify_iter_pack.py` (requires workspace dependencies
and Playwright Chromium). Artifacts live under `artifacts/iter-pack/`, including
`oneclick-result.json`, screenshots, install logs and per-run JSON.

## Numerical results

| Check | Observed result | Qualification |
| --- | --- | --- |
| Uniform-sphere ray integral | Maximum absolute chord error 2.5781e-9 m | Analytic geometric integration |
| CHERAB free-free continuum | Density ×2 produced radiance ×4 | Fixed-temperature, fixed-composition scaling |
| IMAS DD3.39 profile | Exact temperature-array netCDF round-trip | Schema and I/O only |
| CHERAB-IMAS mock bolometers | Three cameras, five channels each | Mock IDS-to-optics construction |
| CHERAB-ITER geometry extension | Bézier derivative matched finite difference; Fourier degree convention checked | Compiled helper arithmetic, not a JOREK simulation |

No ADAS line-emission tables, ITER internal database or actual instrument CAD was
required. Machine-specific applications need separately available data and their
own validation. The generated figure is labelled synthetic readiness, not an
experimental result.

## Real DeepSeek Flash agent acceptance

The final run used Simjecture's built-in agent transport and the provider model ID
`deepseek-flash`, selected for the user's DeepSeek V4.1 Flash backend. The dated
provider revision was not independently verified. It was given the normal skill
catalogue, read `iter-pack/SKILL.md` and the diagnostics reference using `read_skill`,
ran the actual installed capability environment, and authored another CHERAB test.

- Completed in 68.73 seconds, within the 480-second bound.
- Reported input tokens: 336,440; output tokens: 12,853.
- These are sums across provider calls, including repeated context, not unique
  text or an estimate of charged credits.
- A density ratio of 3 produced a radiance ratio of 9.000000000000002.
- Its six-point density scan recovered a fitted exponent of 2.0000000000000004.
- It retained scripts, plots, JSON and a written report in its project workspace.

This validates task execution and tool use, not novel science or a comparison
between model providers. The agent's prose described the Fourier helper check as
“sin 30°”; the actual checked call was `py_fourier_mode(30, 1, 2)`, corresponding
to cos(2 × 30°). The numerical test is correct; that prose explanation is not.

Earlier preliminary probes exposed a missing skill manifest: the model fell back
to filesystem discovery. That was fixed by shipping `manifest.json`, then the
final test above confirmed direct `read_skill` use. Preliminary attempts are
retained separately and excluded from the final-run token figures.

## Solver commissioning

**JOREK:** public revision `4e79ba70cd2a910f9f2a792c9ffb4f074ab8fe90` built locally
with GNU Fortran, OpenMPI, MUMPS and HDF5. The bounded model600 example used 256
poloidal elements, n_tor=3, n_period=6 and n_plane=4: an axisymmetric component and
an n=6 sine/cosine pair. Two MPI ranks × two threads completed three normalized
time steps. The same runtime passed four checks through Bubblewrap: process and
step completion, finite HDF5 solution, final normalized time 3 and cross-section
area 3.1413801885 m² against π m². It is discoverable as a local registered-build
variant; fresh machines still require guided setup. Source/configuration/library
copies are preserved in the local `.runtime` tree.

This is not a converged tearing-mode or disruption calculation. The one-rank
attempt failed with MPI_ERR_RANK. Two HDF5 string-size metadata warnings occurred
during initialization; all four numbered restart outputs were readable. They are
recorded in the report, not suppressed. No remote JOREK solver build is claimed.

**DINA-PS:** public revision `5c04815895832b55cf13527a86bec7c4ad5f9065` compiled its
native core and controllers. Its upstream GREEN component test with supplied ITER
configuration completed: 102 passive structures, 12 active coils, 24 loops,
48 probes and 8385 grid points. Full IMAS/iWrap/XMLlib scenario integration was
not completed. The GUI keeps DINA as guided setup, not a qualified full solver.

**SOLPS-ITER:** public revision `ca0d04d9b0b2d4887bd3262e4e867d471ba86d62` and its
public B2.5/EIRENE/CARRE/DivGeo submodules were inspected. EIRENE standalone and
coupled libraries compiled. The complete headless build remained blocked by site
library configuration (MSCL/NCARG/NAG-or-BLAS/netCDF) and legacy shell assumptions.
The ADAS submodule still references an ITER SSH repository. No coupled divertor
simulation or converged SOLPS result is claimed. Its card remains guided setup.

## Integration decisions learned from upstream

Use supplied cases, native data layouts and documented readers; do not replace a
solver when setup fails. Preserve compiled model choices and data dictionary
versions. Public source access does not imply access to all machine data or
atomic databases. Skills route to focused upstream material and record tested
pitfalls; optional helpers do not prescribe an entire research strategy.

IMAS-Codex is an existing schema-oriented MCP interface, separate from these
solver workflows. This pack uses the local IMAS APIs and skill interface; it does
not silently connect an agent to a hosted service or claim an upstream solver
agent interface that was not found.

## Repository checks

The full suite passed: **748 passed, 7 skipped** in 181.44 seconds. Skips cover
optional unavailable runtimes and local PRoot requirements; the remote PRoot
pack demo was exercised separately. Changed Python files pass Ruff, JavaScript
syntax checks pass, and documentation builds with warnings treated as errors.
The skill frontmatter validator also passes.
