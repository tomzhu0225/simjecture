---
name: opacity
description: Commission, run, and assess user-installed opacity-table generators. Use when an installed opacity capability may provide absorption, scattering, or mean-opacity evidence; do not treat an opacity table as an equation of state.
---

# Opacity tables

Use this skill to operate an opacity-table generator that the operator obtained
and registered under an advertised capability. The skill describes the
instrument; it does not select the scientific hypothesis, composition,
frequency grid, acceptance thresholds, or conclusion.

Opacity and equation of state are different instruments. Opacity describes
coupling between matter and photons. An EOS describes thermodynamic state.
Optab **consumes** an externally supplied abundance or EOS table; it does not
solve chemical equilibrium or ionization.

Atomic-structure codes that emit bound levels, oscillator strengths, or rates
are not opacity-table generators. Do not register or interpret them as this
capability.

## Execution contract

- Use an opacity package only when the campaign advertises an installed
  capability whose manifest names this skill. Do not invent a capability name
  or assume that this skill includes an executable.
- Keep programs, inputs, analysis, and outputs in the writable workspace.
  Capability action paths are workspace-relative.
- Treat the exact executable identity, process switches, abundance table,
  atomic database, frequency grid, and analysis source as provenance.
- Use `stage=workbench` while repairing inputs or checking the interface.
  Workbench artifacts are permanently non-evidentiary. Use `stage=evidence`
  only with a frozen, prospectively commissioned program and command set.
- Treat a zero process exit status as execution success only. It does not
  establish physical validity or support for a claim.

## Installed capabilities

| Capability | Package | What it evaluates |
|---|---|---|
| `optab-1.3.1` | Optab 1.3.x | Monochromatic and mean opacities from user-supplied chemical abundances |

Execute workspace Python with `run_capability` on `optab-1.3.1`. The first argv
item is the workspace-relative program. There is no shell. Ordinary
`run_python` does not contain Optab.

Read [execution and output](references/execution-output.md) for launch
variables and output fields. Read
[local deployment](references/local-deployment.md) only when registering or
repairing a runtime.

## Limitations

### Optab

- Optab is an **ideal-gas astrophysical opacity synthesizer**. It does not
  solve Saha, Thomas–Fermi, or dense-plasma ionization. Species number
  densities must come from an external table whose assumptions are part of the
  evidence record.
- The published and coded atomic coverage for the free-free and bound-data
  loop is **hydrogen through zinc**. Extending array slots does not create a
  validated high-Z spectroscopic model.
- Bound-bound, bound-free, free-free, and scattering contributions are
  optional switches. A continuum-only run (free-free plus Thomson) is not a
  complete line-and-edge opacity. Record which processes were enabled.
- Line lists and photoionization databases are only as complete as the
  operator-installed files (NIST, Kurucz, HITRAN, ExoMol, TOPbase, and related
  tables). Missing databases silently omit processes; they do not justify
  treating the result as a full-spectrum table.
- Volume coefficients in the HDF5 output are in cm\(^{-1}\). Mass opacities
  require division by the stored mass density. Planck and Rosseland means use
  Optab's grid and weighting; do not relabel them as group opacities for a
  different frequency partition without a recorded rebinning.
- The physical assumptions target dilute to moderately dense astrophysical
  gas: no ion-sphere continuum lowering, no dense-plasma line broadening, and
  no relativistic high-Z bound structure. Do not present an Optab table as a
  warm-dense-matter opacity for conditions outside that model.

## Recommended use

1. Translate the active claim into an opacity observable: monochromatic
   absorption or scattering, a Planck or Rosseland mean, or a process-isolated
   comparison against an analytic limit.
2. Confirm that the advertised capability was built with the required databases
   and that the abundance table covers every species the claim needs.
3. Develop an inexpensive workbench case that exercises the intended process
   switches and writes a compact JSON summary with a top-level `checks`
   object. The capability smoke is a permanently non-evidentiary interface
   check.
4. Commission the representation: composition source, enabled processes,
   frequency grid, units, and mean definitions.
5. Freeze the program, input tree, and command. Analyze recorded HDF5 rather
   than terminal prose.

Official resources:

- Optab: <https://github.com/nombac/optab>
- Hirose et al., A&A 659 A87 (2022): <https://doi.org/10.1051/0004-6361/202141076>

## Boundaries

Do not infer that an installed opacity generator is adequate merely because it
is available. Do not treat Thomson-only or free-free-only output as a complete
opacity table. Never take compositions, grids, expected values, or acceptance
thresholds from this skill; derive them within the active campaign and preserve
their provenance. Do not silently change process switches, abundance tables, or
mean definitions after inspecting results.
