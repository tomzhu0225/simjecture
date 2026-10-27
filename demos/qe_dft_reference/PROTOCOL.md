# Si reference protocol (exploratory commissioning)

Question: does the newly integrated nonmagnetic QE instrument reproduce a stable
diamond-Si PBE semiconductor, independent DOS/PDOS and indexed band projections?

Run the generic instrument using case.json after deployment. First a small SCF
checks execution, then use the reference settings for the complete calculation.
The small profile is development only. Final acceptance is the actual configured
reference command through Simjecture, with the supplied source and input hashes.
No paid agent/provider calls are required for model-free guided readiness.

Model: two-atom diamond primitive cell, PBE, scalar relativistic GBRV Si v1 USPP
with NLCC and four valence electrons per atom. No spin, SOC, finite temperature,
defects or many-body correction. Initial conventional a=5.47 Angstrom; ideal
fractional diamond positions preserve symmetry. The full cell and ions relax
with cell_dofree=all. Report departure from the cubic diamond primitive metric.
All material settings and thresholds are in case.json.

Sequence: vc-relax -> final-cell SCF -> two independent checkpoint copies ->
12x12x12 uniform NSCF/DOS/PDOS and Gamma-X-W-K-Gamma-L bands/projections.
Occupied count derives from QE electrons. The path uses the supplied primitive
reciprocal basis. Its sampled gap is not proof of the global CBM. Validate
bands.x and atomic_proj.xml k-point/energy indices before plotting marker weights.

Prospective checks: BFGS finishes; electronic convergence; maximum force
<=2e-4 Ry/Bohr; sampled path gap 0.3-0.9 eV (broad sanity, not tight reproduction);
finite DOS/PDOS; preserved SCF checkpoint; independent branches; verified
projection dimensions/order. For cubic diamond report a=(4V)^(1/3). Compare PBE
lattice reference 5.466 Angstrom using the broad range 5.44-5.50 Angstrom.

Controls: at the final reference geometry run 40/200 and 60/300 Ry with the same
10x10x10 grid, plus 8x8x8 and 12x12x12 at 50/250 Ry. Report signed meV/atom,
force and pressure. Target <=2 meV/atom for 50->60 Ry and 10^3->12^3.
The initial 6^3->8^3 test failed this target (9.84 meV/atom); its unchanged raw
record remains local. The production grid was increased based on that result.
A failed target must stay failed. Pairwise energy checks do not bound complete
stress, lattice, DOS or band-extremum errors. New research needs its own checks.

Stop on hash mismatch, nonconvergence, solver error, unsupported spin, malformed
tables or index disagreement. Preserve failed outputs. Never compare reference
absolute energies across PPs/functionals. PBE gap underestimation is a method
limitation, not an installation failure. Supplied logs and readiness are context,
never fresh research evidence.
