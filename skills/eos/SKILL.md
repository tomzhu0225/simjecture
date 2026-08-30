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

## Execution contract

- Use an EOS package only when the campaign advertises an installed capability
  whose manifest names this skill. Do not invent a capability name or assume
  that this skill includes an executable.
- Keep programs, inputs, analysis, and outputs in the writable workspace.
  Capability action paths are workspace-relative.
- Treat the exact executable identity, model name, material or composition
  input, units, and analysis source as provenance.
- Use `stage=workbench` while repairing inputs or checking the interface.
  Workbench artifacts are permanently non-evidentiary. Use `stage=evidence`
  only with a frozen, prospectively commissioned program and command set.
- Treat a zero process exit status as execution success only. It does not
  establish physical validity, numerical convergence, or support for a claim.

## Installed capabilities

Each capability is a different code. Name the model that actually ran.

| Capability | Package | What it evaluates |
|---|---|---|
| `atomec-1.4.0` | atoMEC 1.4.x | Finite-temperature Kohn–Sham average-atom electron structure for one element |
| `singularity-eos-1.12.1` | Singularity-EOS 1.12.x | Named analytic or tabulated closures through a query driver or Python module |
| `m-aneos-1.0` | M-ANEOS 1.0.x | Semi-analytic total-material Helmholtz EOS from an operator-supplied parameter set |

Execute workspace Python with `run_capability`, selecting the advertised
capability. The first argv item is the workspace-relative program. There is no
shell. Ordinary `run_python` does not contain these packages.

Read [execution and output](references/execution-output.md) for launch
variables, units, and the query JSON contract. Read
[local deployment](references/local-deployment.md) only when registering or
repairing a runtime; it is not a campaign procedure.

## Limitations

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
  estimator step size remain part of the numerical regime.

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

## Boundaries

Do not infer that one installed EOS package is adequate merely because it is
available. Do not treat a runtime smoke, a single state point, or agreement
between two ideal-gas formulas as material qualification. Never take materials,
state points, expected values, or acceptance thresholds from this skill; derive
them within the active campaign and preserve their provenance. Do not silently
change the model, estimator, units, or composition after inspecting results.
