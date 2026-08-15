# PICMI construction map

WarpX exposes the PICMI interface through `from pywarpx import picmi`. A usual
program constructs objects in this order:

1. A geometry-specific grid such as `Cartesian1DGrid`, `Cartesian2DGrid`,
   `Cartesian3DGrid`, or `CylindricalGrid`, with field and particle boundary
   conditions stated explicitly.
2. An electromagnetic or electrostatic solver compatible with that grid and
   the intended model.
3. One or more `Species` objects with explicit charge/mass or a recognized
   particle type, each connected to an initial distribution.
4. A particle layout for each species, such as `GriddedLayout` or
   `PseudoRandomLayout`.
5. A `Simulation` carrying timestep or CFL choice, maximum steps, particle
   shape, random-seed policy, and any WarpX-specific controls.
6. Applied fields, collisions, lasers, or other supported components only when
   demanded by the proposed experiment.
7. Diagnostics added to the simulation before `simulation.step()`.

`simulation.write_input_file(file_name=...)` is useful for inspecting the
compiled native input without running the calculation. When representation is
scientifically important, also request `warpx_used_inputs_file` and inspect the
realized native controls rather than trusting the frontend program alone.

PICMI uses physical units for dimensional inputs. Check dimensional
conversions explicitly. Parser expressions, velocity/momentum conventions,
thermal spreads, boundary names, and dimension-dependent component ordering
are common sources of plausible but incorrect initial states.

Despite their names, `AnalyticDistribution(momentum_expressions=...)` and
`momentum_spread_expressions=...` take proper velocity, `gamma*v`, in metres
per second in this runtime. They do **not** take mechanical momentum `m*gamma*v`.
For a nonrelativistic drift, supply the drift velocity itself; never multiply it
by particle mass. Thermal spread expressions likewise use a velocity spread.
Confirm the generated `*_u*_mean_function` and `*_u*_std_function` entries in
the used-inputs record. Parser keyword arguments must actually occur in at
least one expression consumed by that object; unused keywords are rejected by
PICMI, so pass only the constants used by each distribution or field.

For the pinned 26.07 runtime, use the concrete names implemented by the
installed interface. Important multidimensional entries include
`Cartesian2DGrid`, `AnalyticDistribution`, `AnalyticInitialField`,
`ConstantAppliedField`, `AnalyticAppliedField`, and `CoulombCollisions`. Do not
invent generic aliases such as `Grid` or `BinaryCollision`. Wire the objects
with the exact methods `simulation.add_species(species, layout=layout)`,
`simulation.add_applied_field(field)`, and
`simulation.add_diagnostic(diagnostic)`. In WarpX 26.07,
`CoulombCollisions` is not a standard PICMI interaction: pass a list through
`picmi.Simulation(..., warpx_collisions=[collision])`; do not use
`simulation.add_interaction(collision)`, which routes through the standard
interaction path. Construct it as
`picmi.CoulombCollisions(name="...", species=[species_a, species_b], ...)` in
this runtime. Its constructor requires the single `species` collection;
`species1=...` and `species2=...` without that collection are rejected. Use
`CoulombLog`, `ndt_supercycle`, or `ndt_subcycle` with the exact capitalization
shown by the runtime. If `CoulombLog` is omitted, WarpX calculates it locally;
if it is prescribed, justify its physical range and measure the realized
collision effect.

For `AnalyticInitialField`, provide explicit expressions for all three magnetic
components and all three electric components, using `"0.0"` for intended
zeros. The installed constructor keyword names are exactly
`Ex_expression`, `Ey_expression`, `Ez_expression`, `Bx_expression`,
`By_expression`, and `Bz_expression`. Do not pass `Ex`/`Ey`/`Ez`/`Bx`/`By`/`Bz`
or `E_x`/`B_x`-style aliases; those are rejected as unexpected keywords before
WarpX initializes. `ConstantAppliedField` is different: it takes numeric
`Ex`/`Ey`/`Ez`/`Bx`/`By`/`Bz` (not `E1`/`E2`/`E3` and not `*_expression`).
Supplying only one analytic component can reach WarpX initialization and then
abort when another external-grid parser entry is absent. Inspect the native
input for `B_ext_grid_init_style = parse_b_ext_grid_function` (and the analogous
electric entry when used); particle-applied external fields are a different
mechanism.

For a spatially varying thermal spread in `AnalyticDistribution`, the pinned
WarpX subclass consumes `warpx_momentum_spread_expressions`, not the generic
`momentum_spread_expressions` argument inherited from `picmistandard`. The
generic argument can be accepted while disappearing from the realized native
input, leaving only the directed momentum parser. Use numeric-literal strings
for constant spreads, or make every parser symbol part of an expression path
that the installed constructor actually registers. Verify native
`momentum_distribution_type = "maxwellian"`, all three
`u*_std_function(x,y,z)` expressions, and their `/c` normalization. A custom
keyword used only by the generic spread expressions can be rejected as an
unexpected keyword. For a spatially uniform Gaussian, `rms_velocity` is a
simpler standard interface; still inspect `ux_th`, `uy_th`, and `uz_th`.

The pinned Cartesian PICMI grid accepts field boundary strings `periodic`,
`open`, `dirichlet`, `neumann`, and `absorbing_silver_mueller`, subject to
solver compatibility. Particle boundary strings are `periodic`, `absorbing`,
`reflect`, and `thermal`. These are numerical boundary behaviors, not sources.
If the physics needs continuing material or flux injection, author and
commission an explicit supported injection/source mechanism; do not relabel an
open or absorbing boundary as inflow.

Call `simulation.write_input_file(file_name="inputs")` before stepping and set
`warpx_used_inputs_file` on `Simulation` when the realized controls matter.
Inspect both records. Do not repeatedly introspect the runtime for the wiring
listed here.

`PseudoRandomLayout(seed=...)` prints a warning because WarpX 26.07 does not
honor a layout-local seed. Use the simulation/runtime seed controls, retain the
warning, and verify stochastic reproducibility rather than assuming the
requested layout seed took effect.

Before a 2D Cartesian calculation, read `2d-xz-commissioning.md` in full.

## WarpX 1D coordinate mapping

`Cartesian1DGrid` uses `z` as its sole physical spatial axis. When using
`ParticleListDistribution`, supply longitudinal positions through `z` and
longitudinal proper velocities through `uz`; `x`, `y`, `ux`, and `uy` remain
transverse components. The longitudinal electric-field diagnostic is the `z`
component of the `E` mesh. Verify the mapping in `warpx_used_inputs_file` and
particle diagnostics when commissioning a new loading method.

Use `read_skill` on the smoke example only to learn object wiring. Select all
scientific values from the active hypothesis and commissioning reasoning.
