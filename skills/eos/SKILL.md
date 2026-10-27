---
name: eos
description: Commission, run, and assess user-installed equation-of-state generators and evaluators. Use when an installed EOS capability may provide thermodynamic or ionization evidence; do not treat an EOS evaluation as radiation-transport or opacity evidence.
---

# Equation of state

Use this skill to operate an equation-of-state executable that the operator
obtained and registered under an advertised capability. The skill describes the
instruments; it does not select the scientific hypothesis, material, state
points, acceptance thresholds, or conclusion.

Equation of state and opacity are different instruments. An EOS returns
thermodynamic state and, when the model includes it, ionization. It does not
return frequency-dependent absorption, emission, or scattering. Do not use this
skill as a substitute for an opacity-table capability.

When atomic levels or charge-state populations are needed, the separate
`atomic-physics` skill describes FAC if that capability is advertised. Its
restricted LTE partition functions and line spectra are not a complete EOS;
reconcile binding-energy conventions before combining them with an EOS.

## Execution contract

- Use an EOS package only when the campaign advertises an installed capability
  whose manifest names this skill. Do not invent a capability name or assume
  that this skill includes an executable.
- Keep programs, inputs, analysis, and outputs in the writable workspace.
  Capability action paths are workspace-relative.
- Treat the exact executable identity, model name, material or composition
  input, units, and analysis source as provenance.
- In minimal mode use `lab.run(..., capability=NAME, stage="exploration")`
  while repairing inputs or checking the interface. Submit `lab.method` with
  the source, inputs, runtime and actual validation receipt IDs before decisive
  `stage="evidence"` runs. Use `lab.analyze` for exploratory postprocessing.
  In classic mode, use `run_capability` with `stage="workbench"` and the
  instrument's prospective evidence contract. Exploratory artifacts remain
  non-evidentiary; do not construct classic instrument claims in minimal mode.
- Treat a zero process exit status as execution success only. It does not
  establish physical validity, numerical convergence, or support for a claim.

## Installed capabilities

Each capability is a different code. Name the model that actually ran.

| Capability | Package | What it evaluates |
|---|---|---|
| `atomec-1.4.0` | atoMEC 1.4.x | Finite-temperature Kohn–Sham average-atom electron structure for one element |
| `singularity-eos-1.12.1` | Singularity-EOS 1.12.x | Named analytic or tabulated closures through a query driver or Python module |
| `m-aneos-1.0` | M-ANEOS 1.0.x | Semi-analytic total-material Helmholtz EOS from an operator-supplied parameter set |
| `feos-16.7` | Frankfurt FEOS 16.7 | QEOS electron/ion thermodynamics and charge state from a declared material database |
| `material-eos-0.1` | Material EOS builder | Explicit versioned model profiles, domain checks, and EOS table export |

Select the advertised capability through the active API above. With classic
`run_capability`, the first argv item is the workspace-relative Python program;
with minimal `lab.run`, it is the `source` argument. These launches have no shell.
The general Python runtime does not automatically contain the optional EOS package.

Read [execution and output](references/execution-output.md) for launch
variables, units, and the query JSON contract. Read
[local deployment](references/local-deployment.md) only when registering or
repairing a runtime; it is not a campaign procedure.

For table generation or a paper-specific model, read
[material models and export](references/material-models.md). The FEOS evaluator
and material builder are separate capabilities. A paper recipe is an explicit
profile input, never a replacement for the default model of another material.

## Limitations

### Material EOS builder

- Select a profile and density/temperature grid explicitly. Native FEOS also
  requires a material database and material ID. A paper-specific profile carries
  its parameter sources, modifications, and unresolved limitations.
- Distinguish native corrected electrons, which include bonding, from raw TF
  electrons and thermal increments. Combining a custom ion/bonding model with
  native total FEOS quantities can double-count the same contributions.
- A table that passes finite-value, component, and serialization checks has not
  thereby passed material validation or a full consuming-solver run.
- Keep numerical offsets and grid changes in the output record. Preserve
  failed domain checks in an explicitly requested research export; do not
  silently replace unstable states with another material model.
- Exported thermodynamics contain no opacity. The builder does not install
  FLASH or supply independently qualified material parameters for new elements.

### Frankfurt FEOS

- This is the Frankfurt high-energy-density FEOS package, not the unrelated
  Python/Rust fluid-thermodynamics package named `feos`.
- The model combines Thomas–Fermi electrons, Cowan ions and a bonding correction.
  `FEOS_Get_EOS_All` returns the corrected electron and ion contributions
  separately. They can be evaluated at different temperatures; this is an
  approximate model decomposition, not independent validation of a nonequilibrium state.
- The adapter evaluates the homogeneous EOS with Maxwell construction and
  soft-sphere replacement disabled. Do not label a subcritical expanded state
  as an equilibrium mixture. The upstream manual says the split quantities
  become physically meaningless inside a Maxwell two-phase mixture.
- The public source archive does not contain every material named in the paper.
  Supply and seal the actual material database; reference density, temperature
  and bulk modulus are model inputs, not predictions. Heat capacities and other
  derivatives require numerical assessment. Component energies use reference offsets.
- Thomas–Fermi ionization has no atomic shell structure and is unreliable for
  near-neutral dilute gases. The nonrelativistic model needs an explicit domain
  assessment at high electron temperatures. EOS evaluation supplies no opacity.
- Read [the FEOS interface](references/feos.md) for required workspace files,
  units, single-state and batch queries, and upstream error handling.

### atoMEC

- Solves a **single-element ion-sphere** average-atom problem with
  finite-temperature Kohn–Sham DFT. It is not a multi-species mixture solver
  and does not enforce a common electron chemical potential across elements.
- Returns electronic structure and electron thermodynamics. It is not a
  complete material EOS: there is no calibrated ion thermal model, cold curve,
  or multi-phase diagram.
- The published solver is **non-relativistic**. Do not treat deep-shell or
  high-Z states as relativistic without an independent assessment.
- Mean ionization and pressure depend on the exchange-correlation functional,
  boundary condition, unbound-electron treatment, orbital basis, and radial
  grid. Distinct pressure estimators (thermodynamic finite difference, virial,
  ideal continuum) can disagree; record which estimator was used.
- A completed SCF is not a converged result. Basis, grid, mixing, and
  estimator step size remain part of the numerical regime. Test radial and
  angular orbital cutoffs separately, and vary the finite-difference radius
  step at fixed basis. Record anomalous pressure estimates rather than
  selecting the estimator that best matches another model.

### Singularity-EOS

- This is a **runtime API and interpolator**, not an atomic-physics generator.
  Tabulated models only reproduce the table they were built from.
- `IdealGas` is a classical \(\gamma\)-law closure. It has no ionization,
  degeneracy, binding, or phase structure.
- `IdealElectrons` is a classical Boltzmann electron gas,
  \(P_e=\rho\,\bar{Z}\,k_B T/(\bar{A}\,m_p)\) in the library's default CGS
  units. \(\bar{Z}\) is an **input**, not a computed ionization state. The
  model omits Fermi degeneracy, exchange, correlation, and ionic structure.
- Other shipped closures (Grüneisen, JWL, Davis, Helmholtz, Vinet, stiff gas,
  noble-abel, Carnahan–Starling, Spiner tables, EOSPAC, stellar collapse, and
  modifiers such as scaled/shifted/relativistic) are valid only inside their
  documented constitutive assumptions. EOSPAC additionally requires a
  separately licensed SESAME library and data; do not assume it is present.
- Default units are CGS unless a unit-system modifier was applied. Do not mix
  unit systems across models or with atoMEC/M-ANEOS outputs without a recorded
  conversion.

### M-ANEOS

- Evaluates a **semi-analytic total-material** Helmholtz free energy. The
  result is only as valid as the operator-supplied `ANEOS.INPUT` parameter set.
- Upstream example materials are geologic calibrations. An input that was not
  calibrated and reviewed for the claimed species and phase region is not a
  predictive material table.
- The supported public thermodynamic result is total pressure, energy, entropy,
  heat capacity, sound speed, phase flag, and mean ionization. Legacy electron
  common-block fields are not a stable electron-EOS API.
- The bundled Rosseland-plus-conduction estimate is an old analytic opacity
  surrogate. It is not an opacity table and must not be used as opacity
  evidence.
- Total M-ANEOS energy already includes ionic contributions. Do not add it to a
  separately evolved ion kinetic energy without a recorded double-counting
  analysis.

## Recommended use

1. Translate the active claim into an EOS observable: pressure, energy, heat
   capacity, ionization, or a comparison of two named models at the same state.
2. Confirm that the advertised capability actually implements the named model,
   composition, and unit system. Runtime flags cannot create a model omitted
   from the build or input deck.
3. Develop an inexpensive workbench evaluation that writes a compact JSON
   summary with a top-level `checks` object. The capability smokes are
   permanently non-evidentiary interface checks.
4. Commission the representation before evidence: model name, composition,
   independent variables, units, estimator, and numerical parameters.
5. Freeze the program and command. Generate fresh evidence from that identity.
   Compare independent codes only at a prospectively declared state and
   conversion.

Official resources:

- atoMEC: <https://github.com/atomec-project/atoMEC>
- Singularity-EOS: <https://github.com/lanl/singularity-eos>
- M-ANEOS: <https://github.com/isale-code/M-ANEOS>
- Frankfurt FEOS: <https://data.mendeley.com/datasets/6vjsv6v48p/1>

## Boundaries

Do not infer that one installed EOS package is adequate merely because it is
available. Do not treat a runtime smoke, a single state point, or agreement
between two ideal-gas formulas as material qualification. Never take materials,
state points, expected values, or acceptance thresholds from this skill; derive
them within the active campaign and preserve their provenance. Do not silently
change the model, estimator, units, or composition after inspecting results.
