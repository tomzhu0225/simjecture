# WarpX hybrid PIC

Read this reference before using `picmi.HybridPICSolver`. It describes the
pinned WarpX 26.07 instrument, not a preferred scientific hypothesis or a set
of campaign parameters.

## Model boundary

WarpX hybrid PIC advances kinetic ion macroparticles while treating electrons
as a neutralizing, inertialess fluid. It obtains total current from Ampere's law
without displacement current, obtains electron current by subtracting kinetic
ion and external currents, computes the electric field from generalized Ohm's
law, and advances the magnetic field with Faraday's law. The implemented
closure is

```text
E = -(Je x B + grad(Pe)) / (e ne) + eta J - eta_h laplacian(J).
```

Use this model only when electron kinetics and electromagnetic waves are not
decisive to the claim. It can remove electron-Debye, electron-plasma-frequency,
and light-wave CFL costs, but it cannot resolve electron inertia, electron
distribution functions, or electron-scale diffusion-region physics. State
that boundary in the evidence contract and conclusion.

## PICMI construction and units

Construct the solver with `picmi.HybridPICSolver(grid=..., ...)` and add the
kinetic ion species to the simulation. Do not add a synthetic kinetic-electron
species to emulate the fluid closure.

The principal solver arguments are:

- `Te`: reference electron temperature in eV; required.
- `n0`: reference density in m^-3; specify it whenever `gamma != 1` and prefer
  making it explicit for auditability.
- `gamma`: electron pressure exponent; `1` is isothermal and the default is
  `5/3`.
- `n_floor`: density floor in m^-3 used in the `1/ne` terms. Qualify that it is
  not controlling the scientific region.
- `plasma_resistivity`: scalar or expression in ohm m, with expression
  variables `rho`, `J`, and `t`.
- `plasma_hyper_resistivity`: scalar or expression in ohm m^3.
- `substeps`: total magnetic-field RK4 substeps per particle timestep. It must
  be even; WarpX rounds an odd value upward.
- `use_rkf45` and its tolerance arguments: optional adaptive magnetic-field
  substepping. Treat the accepted substep behavior and tolerance as part of
  the realized numerical method.

WarpX recommends a collocated grid and linear particle shape for this solver.
Pass `warpx_grid_type="collocated"` through the PICMI simulation interface and
verify the corresponding native setting in the used-input record. Hybrid PIC
supports one mesh level only; do not design an AMR control for this instrument.

Initialize magnetic fields in a divergence-compatible form and verify their
compatibility with the realized field boundaries. For nontrivial equilibria,
measure initial force/current balance rather than inferring it from analytic
input expressions alone.

## Timestep and field substeps

The particle timestep is not constrained by the electromagnetic light-wave CFL
or electron plasma frequency, but it is not unrestricted. Prospectively qualify
the ion push, resistive diffusion, Hall/whistler field advance, and any imposed
source timescales. The magnetic field normally needs a smaller step than the
ions, so qualify `substeps` or RKF45 tolerances with a targeted convergence
control at the time interval used for scientific inference. A short startup
comparison is only a commissioning check, not a long-time numerical control.

Record both the particle timestep and the effective magnetic-field substep. A
stable completed run is insufficient if changing either value alters the
claimed observable beyond its uncertainty allowance.

## Diagnostics and interpretation

Inspect the realized input for the hybrid Maxwell solver, electron closure,
density floor, resistivity or hyper-resistivity, grid type, particle shape, and
field-substep policy. Preserve the used input with the run.

In hybrid mode, ordinary deposited `J` fields can represent kinetic-species
current rather than the total current used by Ohm's law. Do not label a current
diagnostic without checking its exact WarpX definition. Total current can be
derived from `curl(B)/mu0` with the realized discretization; WarpX's displacement
current diagnostic yields the electron current in this model. When a conclusion
depends on a topology-change or flux-transfer rate, triangulate compatible
estimators such as the relevant electric-field component and the time derivative
of magnetic flux rather than trusting a single ambiguous mesh record.

The presence of a nonzero `plasma_resistivity` is a constitutive closure, not by
itself proof that the simulated plasma is in a physically collisional regime.
Derive and report the relevant dimensionless ordering within the active
campaign. Likewise, a nominal dimensionless transport parameter is not realized
evidence until its length, field, density, characteristic speed, and resistivity
definitions have been fixed and checked from outputs.

## Minimum qualification record

In addition to the five-aspect WarpX commissioning contract, preserve:

- the exact WarpX release/capability and successful argv;
- realized hybrid-solver, closure, resistivity, grid, and substep settings;
- density-floor occupancy and initial equilibrium-error metrics;
- field/probe diagnostic readback with unambiguous component coordinates;
- timestep/substep and spatial/particle-statistics controls appropriate to the
  claimed observable;
- a statement of which electron-scale mechanisms the model excludes.

Do not copy numerical values, thresholds, expected scaling, or acceptance
windows from an earlier demonstration. Derive them prospectively from the
active claim, operator input, or campaign-retrieved sources.
