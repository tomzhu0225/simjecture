# Supplied qualification and scientific scope

The contributor supplied domain/grid studies for a stationary circular cylinder
at Re=100. The source and their reports are preserved under `share/source/docs`.
An independent 2560×2560, 160,000-step run reproduced their H=L=80D, upstream=40D
case: St=0.164717, mean Cd=1.367441 and RMS lift=0.238978. This run took about
257 seconds on an RTX 4000 Ada. Throughput is a machine-specific measurement.

The supplied grids have 32/48/64/80 cells across D. The two finest grids change
the four reported observables by less than 1%, but the supplied report explicitly
does not establish a strict 1% continuum error bound. Lift's extrapolated
convergence order is low and unstable. Absolute force coefficients still differ
from the cited low-blockage literature benchmark.

High-Re configurations, shape changes, surface jets and rotation need their own
qualification. Real high-Re cylinder wakes can be three dimensional. This
forward solver has no radiation or magnetic-field evolution, and the supplied
package has removed its former optimization/automatic-differentiation workflow.

Independent research can use these records as background. Benchmark tasks require
new recorded executions; copying these statistics does not establish a new test.
