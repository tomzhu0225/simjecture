# Lessons from the local conductor study

These observations come from a fixed-geometry A-v/circuit study using Elmer
26.2.1. They are useful diagnostics and model choices, not universal Elmer rules.

- A zero exit code did not always mean the iterative solve succeeded. BiCGStabL
  printed `Iteration halted due to problem in algorithm` after negative squared
  residual or Gram norms, then continued to normal program termination. Keep the
  log and inspect these markers. An echoed option named `Linear System Abort
  Not Converged` is not itself a solver failure. The optional launcher flags them; raw native
  execution remains available for diagnosis.
- An isolated residual-vector-norm patch fixed one cancellation path, but a
  separate Gram-norm breakdown remained in a smaller-time-step run. Record the
  actual loaded core and solver modules when comparing builds. This package
  applies no patch automatically.
- Current integrals through independent straight conductor sections exposed a
  bad solution that field plots alone looked plausible enough to hide. For a
  constant-length section without side leakage, integrate J along the section
  direction over volume and divide by axial length. Check orientation and units.
- Circuit KVL and capacitor charge checks could pass while the FEM current and
  field-energy checks failed. Coupled systems need checks on both subsystems.
- Backward Euler has numerical energy dissipation. Include it in a discrete
  energy balance, then study time-step sensitivity separately; conservation
  does not guarantee an accurate pulse peak.
- Mesh cost was dominated by lower hardware and unnecessary fine air. Retaining
  the load and connected feed/return stubs reduced the mesh substantially. A cut
  plane with magnetic insulation is an approximation; vary cut location and
  outer air size. Removing hardware may change circuit inductance/resistance.
- A source fit to a short-circuit fixture includes fixture impedance. De-embed
  retained geometry before assigning that entire fit upstream of a CAD cut.
  Two pulse metrics do not uniquely identify R, L and C; declare assumptions.
- A timeout during assembly was not an out-of-memory event. Record elapsed time,
  observed RSS and imposed address-space limits separately before diagnosing RAM.

The optional conductor example uses W potential, a massive conductor component,
A-v fields and an implicit circuit. `Export Lagrange Multiplier = True` mattered
for that formulation. Its use of a fixed BiCGStabL/Hypre recipe is an example;
other Elmer models can use different equations, solvers and preconditioners.

## Design changes and downstream field use

The later Qin-1 extension compared actual winding and feed geometries with the
same provisional source. Changing a feed path changed the current split as well
as the field direction. Re-solve the coupled circuit and conductors after such a
change; mirrored field arithmetic does not represent the redistributed current.
Compare the original and candidate at matched mesh/time settings, and keep the
source/load assumptions fixed unless changing them is the intended control.

Deleting a remote conductor and replacing its impedance with R/L does not retain
its spatial magnetic field. Decide separately which current paths must remain in
the field model. A field decomposition from element currents can help identify
them, provided its sum is checked against the FEM field before interpreting parts.

Recovered nodal vector potential did not reproduce the required curl in this
study's Cartesian transfer. A source-space plot or small circuit residual did not
qualify the imported field. Check the receiving solver's discrete curl, averaging,
coordinate rotation and inference region. The WarpX skill's `references/external-fem-fields.md` (`skills/warpx/references/external-fem-fields.md`, or `read_skill(name="warpx", path="references/external-fem-fields.md")` for API agents) covers that receiving-side workflow when a plasma follow-up is wanted.
For another receiving solver, use its own discretization and checks.

The extended study used a separately recorded residual-Gram stability patch and
retained the earlier failed run. The general Elmer capability still does not
apply that patch automatically. A successful patched build requires its own
numerical controls; do not hide a failure by relaxing a current-balance criterion.
