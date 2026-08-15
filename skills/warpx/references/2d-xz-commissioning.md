# Cartesian 2D XZ commissioning

Read this resource before authoring any two-dimensional Cartesian WarpX run.
It records instrument semantics and generic validity checks; it does not choose
an equilibrium, experiment, or conclusion.

## Coordinate contract

- Treat `Cartesian2DGrid` vectors as `[x, z]`: `number_of_cells=[Nx,Nz]`,
  `lower_bound=[xmin,zmin]`, and `upper_bound=[xmax,zmax]`. The second physical
  axis is `z`, even though some inherited PICMI signatures and internal WarpX
  controls call their second array entry `y`.
- Use physical parser variables `x` and `z` in 2D analytic distributions and
  fields. Retain three velocity and vector components `x,y,z`; `y` is the
  ignorable spatial direction, not the second grid coordinate.
- Never infer the physical location of a feature from an array index alone.
  Obtain coordinate meshes with `mf.mesh("x")` and `mf.mesh("z")`, inspect
  centering and ghost cells for each component, and test the extraction on an
  asymmetric analytic field whose expected axis dependence is known.
- MultiFab vector directions remain physical component directions `x=0`,
  `y=1`, `z=2`; they are not array-axis numbers. Use the runtime's `Direction`
  enum when available.
- `MultiFabWrapper.to_numpy()` returns a list, one array per local box, and can
  include guard cells and singleton component dimensions. Do not assume a
  global contiguous array, silently select box zero, or reuse one component's
  slice for another staggered component. Record box bounds, meshes, shapes,
  centering, and the interior slice used by every estimator.

## Preflight the represented object

Derive checks from the active claim and emit them in a small JSON summary.
Evaluate the analytic initialization independently before stepping, then
confirm the realized WarpX state after initialization. Include the checks that
can invalidate the proposed observable, such as:

- every required zero, reversal, extremum, interface, resonance, or source lies
  strictly inside the intended domain with stated boundary clearance;
- all required regions exist on both sides of an interior structure;
- sampled signs and extrema have the intended ordering, rather than merely
  matching a plotted shape;
- discrete divergence, charge neutrality, current balance, force or pressure
  balance, and boundary compatibility meet prospectively chosen tolerances;
- component orientation and current/drift signs satisfy the governing
  equations under the chosen coordinate convention;
- every density is reported in SI units and labeled as electron, ion,
  per-species, or total density. Convert a supplied density in `cm^-3` to
  `m^-3` exactly once by multiplying by `1e6`; do not silently reinterpret its
  population meaning;
- every parser-function argument is dimensionless where required. Independently
  check the dimensions of every expression and the physical scale represented
  by any normalized coordinate or wave number;
- every field assigned a periodic boundary has matching values and required
  derivatives on paired faces. A profile with unequal limiting values cannot
  be made periodic merely by moving its transition away from the seam. Select
  a compatible topology or nonperiodic boundary and independently check paired
  faces, interior structures, and applicable integral constraints;
- the realized species proper velocities reproduce both the sign and magnitude
  of any required current. Evaluate `curl(B)/mu0` under the declared coordinate
  and sign convention and compare it with `sum_s(q_s n_s v_s)`. Remember that
  PICMI analytic momentum expressions are `gamma*v`, not `m*gamma*v`. First
  derive the physical drift `v` required by the represented state and reject it
  if `abs(v) >= c`; only then convert it to proper velocity `gamma*v` for a
  relativistic distribution;
- pressure or force balance sums the pressure of every represented species.
  Do not use a one-species pressure coefficient for a pair or electron-ion
  population without showing why;
- temperature, energy, velocity, and field conversions are dimensionally
  checked and preserved as metrics. Do not divide a temperature in kelvin by
  elementary charge and label the result electron-volts; convert its energy
  `k_B*T` to eV, or compute the kinetic-energy convention directly in joules
  before dividing by `e`;
- the smallest relevant scale spans a prospectively chosen number of cells and
  particles, with the diagnostic estimator operating above its grid and noise
  floors; and
- the realized native input contains the intended geometry, boundary strings,
  distributions, fields, collisions, diagnostics, timestep, and seed policy.

When collisions, drive, injection, external forcing, or another physical
mechanism is essential to the claim, register at least one
`physics_controls` validation check. Verify both the realized native control
and a quantitative consequence when feasible (for example measured collision
rate, momentum relaxation, injected flux, or maintained field). A collision
object in source code, an arbitrary `CoulombLog`, an initial perturbation, or a
periodic/open boundary label is not by itself evidence that the required
collisional or driven regime exists.

For threshold rules, write both the metric and a named boolean, for example
`{"metrics":{"boundary_clearance_cells":8.0},"checks":{"interior":true}}`.
Register an exact validation check on `checks.interior`. The harness checks the
JSON value; preserve the code that computed it so the calculation remains
auditable.

Do not qualify an experiment when a required structure touches a lossy
boundary, a one-sided profile substitutes for a two-sided object, a width is at
the grid floor, or the diagnostic selects an unconstrained global noise
maximum. Close commissioning as unresolved or instrument-limited and redesign.

## Field-source distinctions

- `AnalyticInitialField` initializes grid fields through WarpX external-grid
  initialization controls. Use it for an initial mesh field and inspect the
  realized native input. Pass component strings as `Ex_expression`,
  `Ey_expression`, `Ez_expression`, `Bx_expression`, `By_expression`, and
  `Bz_expression` only. In the pinned runtime this path invokes initial
  divergence cleaning; the observed MLMG projection rejects `open` field
  boundaries, and the PICMI `AnalyticInitialField` constructor does not expose
  a `do_initial_div_cleaning` keyword (use `warpx_do_initial_div_cleaning` when
  needed). Do not respond by silently switching to periodic boundaries. Select
  a boundary-compatible field topology or another supported initialization
  path, then recommission the changed model under a new prospective evidence
  contract.
- `ConstantAppliedField` and `AnalyticAppliedField` configure external fields
  gathered by particles (`E_ext_particle_*` and `B_ext_particle_*`). Use numeric
  `Ex`/`Ey`/`Ez`/`Bx`/`By`/`Bz` for constants and `*_expression` strings for
  analytic applied fields. Their bounds are ignored by this WarpX
  implementation. They are not automatically part of the self-consistent mesh
  field and are not equivalent to a boundary inflow or boundary electromotive
  force.
- A particle-applied field may directly drive the current being measured. If
  it is used, define whether the observable requires the self-consistent field,
  applied field, or their total, and obtain both contributions consistently.
- Do not describe periodic, reflecting, absorbing, open, or Silver-Mueller
  boundaries as a physical drive. Demonstrate the actual flux, source, or
  boundary mechanism that maintains the proposed state.
- Do not describe an initial seed perturbation as continuing drive. If the
  hypothesis requires a driven state, commission an actual sustained source or
  bound the tested claim to freely evolving initial-value dynamics.

## Diagnostic triangulation

For an evidentiary multidimensional run, derive the primary observable by two
independent paths when feasible. Examples include a local field estimator and
a time derivative of an integral or flux. Commission their sign, units,
normalization, coordinates, time alignment, and agreement before interpreting
the physics. Track a structure continuously from its commissioned location;
do not redefine its position independently at every output by a global maximum.

## Numerical comparisons

Change one fidelity axis at a time. A resolution comparison is not a convergence
test if physical parameters, forcing, perturbation, particle count, collision
strength, estimator, or runtime also change. Measure realized collisionality,
resistivity, temperature, density, and characteristic times when they enter the
hypothesis; input labels such as a nominal dimensionless number are not measured
controls.
