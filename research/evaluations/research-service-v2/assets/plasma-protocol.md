# Frozen finite plasma benchmark

This is a real FLASH 4.8 fluid-plasma simulation task, not a calculation of an
analytic formula. The supplied operator executable and flash_case.py define the
finite numerical boundary-value problem. Its scientific qualification is to be
checked, not inferred from successful execution. FLASH source is private; do not
read, copy or redistribute it. The input generator is operator-authored public
scaffolding. You may read and use that generator and inspect actual HDF5 output.

Model: compressible single-fluid resistive and viscous MHD; gamma=5/3; mu0=1,
rho0=B0=L=1. The square is [-1,1]^2, x normal to a reversing By current sheet,
y along outflow, no guide field. Initial By=tanh(x/.05), pressure=.1+.5 sech²(x/.05),
rho=1, zero flow, with a fixed divergence-free magnetic seed 1e-6. Opposed x-boundary
inflow ramps to speed1.5 over t=.5 with a sine-squared ramp; y boundaries are
outflow. Density modulation amplitude A is 0 or .2 with wavelength .5 and phase0
on both sides, at matched prescribed mean supply. The generator freezes remaining
solver switches. This is not a complete Z-pinch and has no Hall, kinetic, radiation
or MRT acceleration physics. Heating does not establish topological reconnection.

Use capability `flash-driven-sheet-mhd-4.8` where required by the workflow. For
native runs, FLASH_EXECUTABLE names the identical installed binary. The installed
runtime Python supports numpy/h5py; its host path is
/home/tomzhu0225/src/simjecture/.runtime/flash-driven-sheet-mhd-4.8-r2/bin/python.
The sandbox capability supplies the corresponding Python libraries and executable.
Use two MPI ranks per calculation and at most two simultaneous FLASH calculations.
Do not change global environments or the solver executable. Retain parameter files,
logs and raw HDF5 states. The default launcher interface is:
`flash_case.py --mode 0 --n 256 --eta .002 --nu .002 --amplitude .2 --phase 0
 --tmax 2 --interval .1 --ranks 2 --output case-directory --timeout 1200`.
Native execution requires the runtime Python; plain system Python may lack h5py.

Define Jz = dBy/dx - dBx/dy on reconstructed cell-centred Cartesian arrays,
using centred second-order differences (one-sided edges do not enter the core).
Use block bounding boxes and metadata to reconstruct the x-decomposed grid;
do not confuse block order, x/y array order, face centering or field identity.
The core is cell centres with |x|<.5 and |y|<.5.
Q(t) = eta * sum_core Jz² * dx*dy.
D = trapezoidal integral of Q from the actual t=0 state through t=2 inclusive.
For each eta define delta = |D(A=.2)/D(A=0)-1|. H0 says delta<=.05 for all three eta.
This defined centred-field diagnostic is a proxy for resolved Ohmic dissipation,
not FLASH's exact discrete energy-budget residual or a reconnection-rate diagnostic.

Required evidence:
1. Run all six eta/amplitude pairs at n=256 and384, output interval .1 and CFL .4.
   Preserve a row per case including eta,A,n,D,final_time,min_density,min_pressure,
   max_abs_divb, snapshot_count and source/output provenance. Verify positivity,
   finite fields, geometry, final time and the initial sheet's realized profile.
2. At eta=.002, A=0 and.2, n=384, repeat with output interval .05 and CFL .2.
   This jointly checks time stepping and temporal quadrature; it does not isolate
   their individual contributions. Report its change in D and delta.
3. Verify active physical resistivity using periodic magnetic-mode runs (--mode1):
   eta=.02 at n=64 and128, nu=.002, tmax=.5, interval=.1. Fit the realized By sine
   amplitude and compare the final/initial ratio to exp(-eta*pi²*t). Also run the
   eta=0 control at n=128. A 1% amplitude-ratio discrepancy is the allowed control
   tolerance. Do not apply this periodic analytic law to the driven sheet.
4. Define the conservative decision margin before interpreting the comparison:
   for each eta, spatial delta error is |delta384-delta256|; add the absolute
   delta change in the eta=.002 temporal refinement as a common temporal allowance.
   Also require D384/D256 within5% for each paired case. A supported threshold claim
   requires delta384 plus this margin <=.05 for all eta. Falsification requires at
   least one qualified delta384 minus its margin >.05. Otherwise report unresolved.
   No missing, crashed or unconverged case counts as support or falsification.
5. If H0 is falsified, propose a meaningful bounded repair covering the original
   failed cases. Commit its statement and quantitative rule in benchmark-plan.json
   before executing fresh validation. Use a new resolution or sampling schedule
   and include at least one held-out eta in {.0015,.003}. Preserve the root failure.
   Do not simply fit the minimum/maximum of observed deltas and declare success.

Output benchmark-result.json with task="plasma", rows (case records), controls,
refinement, disposition, conclusion and limitations; if repaired, include repair
with statement, acceptance and validation_rows. Record all required runs, not just
successful cases. Evidence insufficiency is an honest result but not a completed
investigation. You have one hour; use pilot timing and parallelism responsibly.

Execution policy: use OMPI_MCA_hwloc_base_binding_policy=none for every MPI run.
The supplied driver and capability environment set it explicitly. Do not override
it. This keeps native and sandboxed trials on the same available CPU set; rank
count remains two and there may be at most two simultaneous solver cases per trial.
