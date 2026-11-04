# Native RZ development and stochastic restart controls

Read for operator-supplied native RZ solver changes, axis anomalies or stochastic
restart comparisons. First identify the exact source revision, local changes,
binary, build dimensions, field layout and runtime dependencies. Native builds
can differ from the pinned PICMI capability; this guide advertises no additional
capability and supplies no physical parameters or acceptance thresholds.

## Localize the failing stage

Record actual native timestep/substep logs and the synchronized checkpoint time.
Separate explicit Hall/transport stages, implicit diffusion, particle motion and
diagnostic interpolation. Failure before the implicit solve does not identify
its linear solver as the failing stage; previous implicit evolution can still
affect the state entering the explicit operator.

Use frozen native-stage probes when a saved cell-centred plot cannot reveal the
staggered or ghost state consumed by an operator. Give a probe a default-off path,
then regress that path against the reference before interpreting probe outputs.
Keep a probe that exits before a physical step labelled as an operator diagnostic.

For an axisymmetric regularity check, establish the actual locations of the axis,
first positive-radius nodes/cells and allocated ghosts. In the regular m=0 case,
transverse vector components vanish on the axis and have odd radial parity;
axial components have even parity. Check derived velocity/current fields at the
stage where transport uses them, not just their source arrays before a later fill.
Other modes, bases and storage conventions need their own regularity contract.

Audit inactive dimensions when translating staggered interpolation. Three vector
components do not imply three active mesh directions in RZ. Match the native
index/stagger convention for the unused slot; a seemingly cell-centred temporary
can otherwise cause a generic interpolator to read a nonexistent extra plane.
Qualify a candidate implementation error separately from the original anomaly.

When examining Hall or ideal-work identities, use collocated quantities and the
realized cylindrical volume weights. A local zero-work identity, a manufactured
axis test and a global time-integrated energy ledger answer different questions.
Record stencil/projection changes as separate candidate methods; a better local
identity alone does not establish convergence or repair a complete trajectory.

## Control stochastic state across restarts

Compare an unchanged repeated restart, an extra split versus continuous evolution,
and a candidate change separately. Matching fields, particles and a seed does not
by itself establish matching RNG state after a restart. Identify the generators
used by actual particle loading, injection and collision paths in this build.

For a checkpoint-state implementation, use a newly generated complete checkpoint
with the intended RNG snapshot. Preserve generator/state-layout identity and
verify restoration before the first resumed physical step. Do not invent missing
legacy history or silently reseed a strict continuation. Exercise missing and
corrupted snapshot rejection on isolated copies and check that rejection occurs
before stepping. Preserve the original checkpoint.

Establish a short split/continuous control with matched physical times and all
relevant fields, particle IDs/weights, injected cohorts and source schedules.
Exclude any copied common anchor from independently evolved comparisons. Compare
actual newly injected attributes, not merely total particle count or final RNG
checksums: equal RNG endpoints alone cannot prove equal draw-to-particle mapping.
Disclose generators and execution paths the implementation does not serialize.

A bounded same-CP/same-RNG on/off comparison can then isolate a candidate's
effect within its tested window. Different evolved fields can legitimately
change trajectories, boundary losses and retained particle counts. Keep those
differences rather than forcing equal masses. Inspect all saved extrema and
spatial locations: a lower final peak can conceal a larger transient.

## Preserve the model boundary

Full-cell energy proxies around embedded boundaries are not exact cut-cell
budgets. Deposited velocity moments are not extrema of individual particle
velocities. An imposed conductivity-front schedule is not a self-consistent
ionization calculation; reflecting embedded electrodes do not resolve bulk metal
heating or ablation. Scope conclusions to the actual model and diagnostic.

Default-off regressions, native finite completion and short restart continuity
are commissioning results. A candidate still needs relevant spatial, timestep,
particle-statistics and physical controls before supporting a scientific claim.
