---
name: atomic-physics
description: Generate and assess atomic levels, transition strengths, and rates with an installed FAC capability, including restricted LTE line-opacity diagnostics. Use for atomic-structure or charge-population evidence; a partial line spectrum is not a complete EOS or opacity table.
---

# Atomic physics

Use `fac-1.1.5` only when it is advertised by the active campaign. It provides
FAC's `sfac`, `scrm`, and `spol` command-line interfaces through a Python
runtime with NumPy and SciPy. PFAC is not installed by this profile.

In minimal mode launch a workspace-relative Python program with
`lab.run(..., capability="fac-1.1.5", stage="exploration")`. In classic mode
use `run_capability` with `stage="workbench"`. Python launches the appropriate
executable from its environment. Keep inputs, logs, and generated data in the
workspace. Read [execution and output](references/execution-output.md) for
the environment, FAC formats, and the optional LTE helper.

The campaign determines composition, states, configurations, processes,
observables, and acceptance criteria. Commission those choices before decisive
runs, preserving the input source, runtime identity, and actual validation
receipts. A successful doctor probe checks execution, not material accuracy.

## Model decisions

- Distinguish detailed fine-structure calculations from FAC's statistical
  UTA/SOSA mode. Configuration and charge-state truncation are model choices,
  not merely numerical tolerances. Assess omitted shells as well as ion stages.
- Keep each ion's potential optimization and generation in a fresh process
  unless a reviewed multi-ion procedure is required. FAC's mutable atomic state
  and potential ordering can change cross-sections.
- Match the electron-energy distribution, density effects, and population
  model to the claim. Isolated-ion energies and Saha populations alone do not
  include continuum lowering or time-dependent non-LTE kinetics.
- Separate abundance/charge balance from within-ion populations. A normalized
  truncated distribution can still omit substantial populations outside its
  boundaries. Compare expanded charge and configuration windows.
- An EOS must account for ionic, electronic, and binding-energy contributions
  consistently. Atomic partition functions and line spectra are ingredients;
  they do not constitute a complete thermodynamic closure.

## FAC output details

- Use `PrintTable(..., 1)` for verbose output: energies are eV and radiative
  rates are s⁻¹. The underlying binary values have different conventions.
- FAC permits one filename per database type in a session. Write E1 and M1
  blocks to a single transition file; different transition filenames can abort
  an otherwise successful structure run.
- In detailed mode, `2J + 1` is the level degeneracy. In UTA output, the same
  column encodes the statistical configuration weight minus one.
- Verbose transition tables contain weighted oscillator strength `gf`;
  divide by the lower-state weight when an unweighted absorption strength is
  required. UTA rows also contain a standard deviation and a separate
  configuration-interaction multiplier. The pinned FAC text printer does not
  apply that multiplier to its printed `gf`.
- Preserve integrated line strength when spectral bins are wider than a line.
  Point sampling can lose a line entirely. Rebinning must conserve integrals.

## Restricted LTE diagnostic

`FAC_LTE_HELPER` identifies the installed `fac_lte.py` helper. It accepts
single-element, adjacent-ion EN/TR files and produces a normalized
Saha–Boltzmann distribution plus binned E1/M1 absorption. See the reference
for its explicit input contract and omitted physics.

This helper uses Gaussian UTA and Doppler profiles, with optional instrumental
broadening. It omits natural/Stark wings, continua, scattering, continuum
lowering, and non-LTE evolution. Its output is a **restricted line spectrum**.
Do not export it as total material opacity or use its empty spectral windows
to establish a physical Rosseland mean. Invoke the `opacity` skill when an
actual complete opacity-table provider is available.

Read [plasma validation lessons](references/plasma-validation.md) when moving
from atomic calculations to material modeling, and
[local deployment](references/local-deployment.md) only for installation or repair.

Upstream: <https://github.com/flexible-atomic-code/fac>.
