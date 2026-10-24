# Importing fields from a CAD/FEM device model

Use this reference when a WarpX problem depends on fields computed by an external
device solver. It records transferable lessons from the October 2026 Qin-1 study.
That study used an operator-supplied native **3D** CUDA build; it does not add 3D
support or that build's extensions to the packaged 2D WarpX 26.07 PICMI runtime.
Inspect the receiving executable, input interface and diagnostics actually used.

## Define what is being coupled

Choose the transfer needed by the question: an initial plasma state, a maintained
static field, a time-dependent drive, or feedback between plasma and conductors.
A held FEM snapshot cannot substitute for a pulse when pulse timing is decisive.
Record separate device and plasma clocks, source time, source/load assumptions,
and which current paths contribute. The full device field can include array,
feed and return currents; removing all of it is not a coil-only-off experiment.

FEM circuit coupling does not imply downstream plasma-to-circuit feedback.
Likewise, drawing a conductor in a plasma figure does not instantiate a solid
boundary in WarpX. State whether particle absorption, induced conductor response
and the source's evolution are present. Establish the available plasma model's
collisional, electron-closure and ion-scale limits before choosing the transfer.

## Check the receiving discrete field

Preserve coordinate origin, a right-handed basis, array order, component order,
units and staggering explicitly. Magnetic field is in tesla; SI vector potential
is in Wb/m. Rotate vector components as well as point coordinates. Store source
file and exported-file identities with the geometry/time selection.

A divergence-compatible vector potential is useful only if its **receiving
discrete curl** yields the intended field. Recovered FEM nodal A, elemental B and
interpolated B need not commute with a Cartesian curl. The local study rejected
direct recovered-A transfer after measuring that discrepancy.

One successful static route sampled face fluxes, projected them to a compatible
divergence-free field, reconstructed edge A, then exported nodal A for the native
importer. This is an example algorithm, not a required gauge or universal recipe.
Quantify what projection/reconstruction changes and check the actual imported
field with the receiving code's curl/averaging operator.

Use a small empty-domain native run to separate import/interface effects from
plasma evolution. Inspect the initial and first evolved diagnostics: some native
paths write the initial diagnostic before adding the external source. Compare
vectors and field direction, not only magnitudes, at the relevant inference
region and a wider air region. Identify unresolved near-conductor cells and the
distance/exclusion rule; an excluded region is unqualified, not error-free.

A maintained static source should remain stationary in the empty-domain control.
For a time-dependent transfer, also qualify the inductive electric field and
potential/gauge treatment. An analytic ramp can check units and source timing,
but does not qualify an arbitrary evolving 3D FEM field or conductor response.

## Qualify the plasma comparison separately

Fix observables, physical measurement regions, observation windows and tolerances
for the question. Compare like source states and numerical settings. A changed
device geometry needs its own plasma checks; convergence of a reference is not
automatically inherited. Keep field-import, source-off, timestep/substep, grid,
particle-count, density-floor and domain checks distinct.

Record density-floor occupancy in the scientific region. A tiny flux where the
density is below that floor is not a reliable leakage or shielding estimate.
A robust density-edge position does not repair a failed flux criterion. A
falling density-profile crossing or bright compressed layer alone does not
identify a magnetopause or bow shock. The Qin-1 dimensions, thresholds and plasma
parameters are case-specific examples, not defaults for another investigation.

If plasma reaches excluded near-metal cells, report that overlap and its spatial
location. Whole-cell mass/energy fractions based on sampled material corners are
instantaneous proxies; they are not exact particle-solid impacts, absorbed energy
or a bound on physical model error. Add the needed boundary physics before making
a hardware-resolved global-flow claim.

Check diagnostic semantics against the actual native build. In the tested build,
the openPMD iteration time was physical while the default `dt` attribute was not;
do not apply that observation blindly to every version. Native particle-moment
functions can use normalized momentum, and cell-binned particle moments can use a
different spatial averaging from deposited charge. Validate units and mappings
before multiplying separately averaged density and velocity to infer flux.

## Keep interrupted runs and reused results distinguishable

Record a requested duration separately from the last complete saved diagnostic.
A common completed window does not turn an interrupted longer request into a
successful full run. Preserve unknown exit codes after a host shutdown.
Reconcile the actual process, durable job/exec handle and checkpoint state before
retrying; an observation timeout is not a solver failure. Use fresh case identities
for changed inputs and keep rejected outputs. A small JSON source/metric record
and input/output hashes make later comparisons possible without repeatedly
loading every raw volume.
